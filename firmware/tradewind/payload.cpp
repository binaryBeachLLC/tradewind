#include "payload.h"
#include <math.h>

namespace payload {
namespace {

long clampl(long v, long lo, long hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Round half away from zero, then clamp: deterministic on host and target.
long q(float v, float step, long lo, long hi) { return clampl(lroundf(v / step), lo, hi); }

void put16(uint8_t* p, uint16_t v) { p[0] = v >> 8; p[1] = v & 0xFF; }  // big-endian

uint8_t vbat_code(uint16_t mv) { return (uint8_t)clampl(lroundf((mv - 2500) / 10.0f), 0, 254); }

}  // namespace

size_t pack_measurement(const Measurement& m, uint8_t* out) {
  out[0] = m.flags;
  int16_t t = (m.flags & F_AIR_OK) ? (int16_t)q(m.air_t_c, 0.01f, -32768, 32766) : AIR_T_INVALID;
  put16(&out[1], (uint16_t)t);
  out[3] = (m.flags & F_AIR_OK) ? (uint8_t)q(m.air_rh, 0.5f, 0, 200) : U8_INVALID;
  out[4] = (m.flags & F_SOIL_OK) ? (uint8_t)q(m.soil_pct, 0.5f, 0, 200) : U8_INVALID;
  put16(&out[5], m.rain_tips);
  out[7] = vbat_code(m.vbat_mv);
  out[8] = (m.flags & F_INT_OK) ? (uint8_t)(int8_t)q(m.int_t_c, 0.5f, -128, 126) : (uint8_t)I8_INVALID;
  out[9] = (m.flags & F_INT_OK) ? (uint8_t)q(m.int_rh, 0.5f, 0, 200) : U8_INVALID;
  out[10] = (uint8_t)q((float)m.vsolar_mv, 25.0f, 0, 255);
  return MEASUREMENT_LEN;
}

size_t pack_health(const Health& h, uint8_t* out) {
  out[0] = h.fw_major;
  out[1] = h.fw_minor;
  put16(&out[2], h.uptime_days);
  put16(&out[4], h.uplinks);
  out[6] = h.rejoins;
  out[7] = (uint8_t)(int8_t)clampl(h.last_rssi_dbm, -128, 127);
  out[8] = (uint8_t)(int8_t)q(h.last_snr_db, 0.25f, -128, 127);
  out[9] = vbat_code(h.vbat_min_mv);
  out[10] = (uint8_t)(int8_t)q(h.int_t_max_c, 0.5f, -128, 127);
  out[11] = (uint8_t)clampl((h.charge_minutes + 5) / 10, 0, 255);
  out[12] = h.interval_min;
  out[13] = h.reset_reason;
  return HEALTH_LEN;
}

bool parse_downlink(const uint8_t* b, size_t len, Downlink& dl) {
  if (len == 0) return false;
  switch (b[0]) {
    case DL_SET_INTERVAL: {
      if (len != 3) return false;
      uint16_t s = (uint16_t)((b[1] << 8) | b[2]);  // big-endian, like the uplinks
      if (s < 60 || s > 3600) return false;
      dl = {DL_SET_INTERVAL, s};
      return true;
    }
    case DL_RAPID:
      if (len != 2) return false;
      dl = {DL_RAPID, b[1]};
      return true;
    case DL_HEALTH_NOW:
      if (len != 1) return false;
      dl = {DL_HEALTH_NOW, 0};
      return true;
    case DL_REBOOT:
      if (len != 3 || b[1] != 0xB0 || b[2] != 0x07) return false;
      dl = {DL_REBOOT, 0};
      return true;
  }
  return false;
}

}  // namespace payload
