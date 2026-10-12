// Tradewind TW-1 — solar LoRaWAN field sensor firmware (RAK3172, RAKwireless RUI3 v4.x).
//
// One cooperative loop: handle input events, send what is due, then sleep until the next deadline
// (or until the rain gauge / magnet interrupt wakes us). Everything time-based uses millis(),
// which RUI3 keeps counting through api.system.sleep.all().
//
// Uplinks: fport 1 measurement (11 B, unconfirmed), fport 2 daily health (14 B, confirmed).
// Downlinks: fport 10 commands. Formats: ../PAYLOAD.md.

#include "board.h"
#include "config.h"
#include "inputs.h"
#include "payload.h"
#include "sensors.h"
#include "secrets.h"   // copy secrets.h.example -> secrets.h

// ---------- state ----------
static bool     joined = false;
static uint32_t join_backoff_s = JOIN_RETRY_S;
static uint32_t next_join_ms = 0;

static volatile bool tx_busy = false;   // between send() and the send callback (RX windows closed)
static uint32_t interval_s = INTERVAL_DEFAULT_S;
static uint32_t rapid_until_ms = 0;     // 0 = rapid mode off
static uint32_t next_uplink_ms = 0;
static uint32_t next_health_ms = 0;
static bool     send_now = false, health_now = false;

static float    last_soil_pct = -1;
static uint16_t last_rain_tips = 0;

// 24 h statistics for the health frame
static uint16_t uplinks = 0, vbat_min_mv = 0xFFFF, charge_minutes = 0, uptime_days = 0;
static float    int_t_max_c = -100;
static uint8_t  rejoins = 0;
static uint32_t health_frames = 0;
static int16_t  last_rssi = 0;
static float    last_snr = 0;

// Survives a software reset, so the health frame can say "rebooted by command".
static uint32_t reboot_magic __attribute__((section(".noinit")));
static uint8_t  reset_reason = 0;       // 0 power-on/other, 1 downlink reboot

// ---------- helpers ----------
static bool due(uint32_t now, uint32_t t) { return (int32_t)(now - t) >= 0; }
static bool rapid(uint32_t now) { return rapid_until_ms != 0 && !due(now, rapid_until_ms); }
static uint32_t current_interval_s(uint32_t now) { return rapid(now) ? INTERVAL_RAPID_S : interval_s; }

static void set_rapid(uint32_t now, uint16_t minutes, uint16_t vbat_mv) {
  if (minutes == 0 || vbat_mv < BATT_LOW_MV) {        // refuse rapid mode on a low battery
    rapid_until_ms = 0;
    return;
  }
  rapid_until_ms = now + minutes * 60000UL;
  if (rapid_until_ms == 0) rapid_until_ms = 1;
  next_uplink_ms = now + INTERVAL_RAPID_S * 1000UL;  // pull the next uplink in
}

static bool lora_send(uint8_t port, uint8_t* buf, uint8_t len, bool confirmed) {
  tx_busy = true;
  if (!api.lorawan.send(len, buf, port, confirmed, confirmed ? 2 : 0)) {
    tx_busy = false;
    return false;
  }
  return true;
}

// ---------- RUI3 callbacks ----------
static void on_join(int32_t status) {
  if (status == RAK_LORAMAC_STATUS_OK) {
    joined = true;
    join_backoff_s = JOIN_RETRY_S;
    led_joined();
  } else {
    joined = false;
    next_join_ms = millis() + join_backoff_s * 1000UL;
    join_backoff_s = (join_backoff_s * 2 > JOIN_RETRY_MAX_S) ? JOIN_RETRY_MAX_S : join_backoff_s * 2;
    led_error();
  }
}

static void on_send(int32_t status) {
  (void)status;   // failures show up as missing frames; the rain counter is cumulative so nothing is lost
  tx_busy = false;
}

static void on_receive(SERVICE_LORA_RECEIVE_T* d) {
  last_rssi = d->Rssi;
  last_snr = d->Snr;
  if (d->Port != payload::PORT_DOWNLINK) return;
  payload::Downlink dl;
  if (!payload::parse_downlink(d->Buffer, d->BufferSize, dl)) return;
  uint32_t now = millis();
  switch (dl.cmd) {
    case payload::DL_SET_INTERVAL:
      interval_s = dl.value;
      next_uplink_ms = now + current_interval_s(now) * 1000UL;
      break;
    case payload::DL_RAPID:
      set_rapid(now, dl.value, vbat_read_mv());
      break;
    case payload::DL_HEALTH_NOW:
      health_now = true;
      break;
    case payload::DL_REBOOT:
      reboot_magic = 0xB007B007;
      api.system.reboot();
      break;
  }
}

// ---------- LoRaWAN ----------
static void lora_setup() {
  api.lorawan.nwm.set();                       // LoRaWAN mode (not P2P)
  api.lorawan.deui.set(DEV_EUI, 8);
  api.lorawan.appeui.set(JOIN_EUI, 8);
  api.lorawan.appkey.set(APP_KEY, 16);
  api.lorawan.band.set(RAK_REGION_US915);
  uint16_t mask = LORA_SUBBAND_MASK;
  api.lorawan.mask.set(&mask);
  api.lorawan.njm.set(RAK_LORA_OTAA);
  api.lorawan.adr.set(true);
  api.lorawan.rety.set(0);
  api.lorawan.registerJoinCallback(on_join);
  api.lorawan.registerSendCallback(on_send);
  api.lorawan.registerRecvCallback(on_receive);
}

static void start_join(uint32_t now) {
  led_joining();
  api.lorawan.join();                          // result arrives in on_join
  next_join_ms = now + JOIN_RETRY_MAX_S * 1000UL;  // guard; on_join reschedules on failure
}

// ---------- uplinks ----------
static void do_measurement_uplink(uint32_t now) {
  ShtReading air = sht4x_read(SHT_EXT_ADDR);
  ShtReading in = sht4x_read(SHT_INT_ADDR);
  bool soil_ok;
  float soil = soil_read_pct(soil_ok);
  uint16_t vbat = vbat_read_mv();
  uint16_t vsol = vsolar_read_mv();
  uint16_t tips = rain_tips_total();
  bool chg = charger_charging();

  // Auto rapid mode: soil moving fast or real rain falling.
  uint16_t new_tips = (uint16_t)(tips - last_rain_tips);
  if ((soil_ok && last_soil_pct >= 0 && fabsf(soil - last_soil_pct) >= RAPID_SOIL_DELTA_PCT) ||
      new_tips >= RAPID_RAIN_TIPS) {
    if (!rapid(now)) set_rapid(now, RAPID_DEFAULT_MIN, vbat);
  }
  if (soil_ok) last_soil_pct = soil;
  last_rain_tips = tips;

  payload::Measurement m{};
  m.flags = (rapid(now) ? payload::F_RAPID : 0) | (chg ? payload::F_CHARGING : 0) |
            (charger_power_good() ? payload::F_PGOOD : 0) | (vbat < BATT_LOW_MV ? payload::F_BATT_LOW : 0) |
            (air.ok ? payload::F_AIR_OK : 0) | (soil_ok ? payload::F_SOIL_OK : 0) | (in.ok ? payload::F_INT_OK : 0);
  m.air_t_c = air.t_c;
  m.air_rh = air.rh;
  m.soil_pct = soil;
  m.rain_tips = tips;
  m.vbat_mv = vbat;
  m.int_t_c = in.t_c;
  m.int_rh = in.rh;
  m.vsolar_mv = vsol;

  // statistics for the daily health frame
  if (vbat < vbat_min_mv) vbat_min_mv = vbat;
  if (in.ok && in.t_c > int_t_max_c) int_t_max_c = in.t_c;
  if (chg) charge_minutes += current_interval_s(now) / 60;

  uint8_t buf[payload::MEASUREMENT_LEN];
  uint8_t n = payload::pack_measurement(m, buf);
  if (vbat >= BATT_CRIT_MV && lora_send(payload::PORT_MEASUREMENT, buf, n, false)) uplinks++;
}

static void do_health_uplink() {
  payload::Health h{};
  h.fw_major = FW_MAJOR;
  h.fw_minor = FW_MINOR;
  h.uptime_days = uptime_days;
  h.uplinks = uplinks;
  h.rejoins = rejoins;
  h.last_rssi_dbm = last_rssi;
  h.last_snr_db = last_snr;
  h.vbat_min_mv = vbat_min_mv == 0xFFFF ? vbat_read_mv() : vbat_min_mv;
  h.int_t_max_c = int_t_max_c;
  h.charge_minutes = charge_minutes;
  h.interval_min = (uint8_t)(current_interval_s(millis()) / 60);
  h.reset_reason = reset_reason;
  uint8_t buf[payload::HEALTH_LEN];
  uint8_t n = payload::pack_health(h, buf);
  lora_send(payload::PORT_HEALTH, buf, n, true);
  vbat_min_mv = 0xFFFF;                         // start a new 24 h window
  int_t_max_c = -100;
  charge_minutes = 0;
}

// ---------- Arduino entry points ----------
void setup() {
  reset_reason = (reboot_magic == 0xB007B007) ? 1 : 0;
  reboot_magic = 0;
  Serial.begin(115200);
  sensors_init();
  inputs_init();
  lora_setup();
  uint32_t now = millis();
  next_join_ms = now;
  next_health_ms = now + 60000UL;               // first health frame a minute after joining
}

void loop() {
  uint32_t now = millis();

  switch (hall_take_event()) {
    case HALL_TAP:                              // magnet tap: send now (or retry the join)
      led_ack();
      if (joined) send_now = true; else next_join_ms = now;
      break;
    case HALL_HOLD:                             // 3 s hold: forget the session and join again
      led_ack();
      joined = false;
      rejoins++;
      next_join_ms = now;
      break;
    default:
      break;
  }

  if (tx_busy) {                                // RX1/RX2 still open: idle lightly, don't deep-sleep
    delay(20);
    return;
  }

  if (!joined) {
    if (due(now, next_join_ms)) start_join(now);
  } else if (health_now || due(now, next_health_ms)) {
    if (!health_now && health_frames++ > 0) uptime_days++;   // the first scheduled frame is day 0
    health_now = false;
    next_health_ms = now + HEALTH_PERIOD_S * 1000UL;
    do_health_uplink();
  } else if (send_now || due(now, next_uplink_ms)) {
    send_now = false;
    do_measurement_uplink(now);
    next_uplink_ms = now + current_interval_s(now) * 1000UL;
  }
  if (rapid_until_ms && due(now, rapid_until_ms)) rapid_until_ms = 0;
  if (tx_busy) return;

  // Sleep until the next deadline; the rain gauge or the magnet wake us early.
  uint32_t next = joined ? next_uplink_ms : next_join_ms;
  if (joined && (int32_t)(next_health_ms - next) < 0) next = next_health_ms;
  int32_t ms = (int32_t)(next - millis());
  if (ms > 5) api.system.sleep.all(ms);
}
