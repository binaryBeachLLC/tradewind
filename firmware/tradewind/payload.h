// Tradewind TW-1 uplink/downlink payload format. Plain C++, no Arduino headers,
// so the same file is compiled into the firmware and into the host unit test.
// Byte layout: firmware/PAYLOAD.md. Decoder: firmware/decoder/ttn_decoder.js.
#pragma once
#include <stdint.h>
#include <stddef.h>

namespace payload {

constexpr uint8_t PORT_MEASUREMENT = 1;
constexpr uint8_t PORT_HEALTH      = 2;
constexpr uint8_t PORT_DOWNLINK    = 10;

constexpr size_t MEASUREMENT_LEN = 11;
constexpr size_t HEALTH_LEN      = 14;

// flags byte (measurement byte 0)
enum : uint8_t {
  F_RAPID     = 1 << 0,  // rapid (1-min) mode active
  F_CHARGING  = 1 << 1,  // BQ24074 ~CHG low
  F_PGOOD     = 1 << 2,  // BQ24074 ~PGOOD low (panel above UVLO)
  F_BATT_LOW  = 1 << 3,  // VBAT < BATT_LOW_MV
  F_AIR_OK    = 1 << 4,  // external SHT45 answered with a good CRC
  F_SOIL_OK   = 1 << 5,  // soil probe reading in a plausible range
  F_INT_OK    = 1 << 6,  // internal SHT40 answered with a good CRC
};

// Sentinel values sent when a sensor is missing.
constexpr int16_t  AIR_T_INVALID = 0x7FFF;
constexpr uint8_t  U8_INVALID    = 0xFF;
constexpr int8_t   I8_INVALID    = 0x7F;

struct Measurement {
  uint8_t  flags;
  float    air_t_c;      // external probe, °C       -> int16, 0.01 °C
  float    air_rh;       // external probe, %RH      -> uint8, 0.5 %RH
  float    soil_pct;     // volumetric-ish, 0..100 % -> uint8, 0.5 %
  uint16_t rain_tips;    // cumulative tip counter, wraps at 65536
  uint16_t vbat_mv;      // battery                  -> uint8, (mV-2500)/10
  float    int_t_c;      // internal SHT40, °C       -> int8, 0.5 °C
  float    int_rh;       // internal SHT40, %RH      -> uint8, 0.5 %RH
  uint16_t vsolar_mv;    // panel voltage            -> uint8, 25 mV
};

struct Health {
  uint8_t  fw_major, fw_minor;
  uint16_t uptime_days;
  uint16_t uplinks;          // total uplinks, wraps
  uint8_t  rejoins;
  int16_t  last_rssi_dbm;    // -> int8, 1 dBm (clamped -128..127)
  float    last_snr_db;      // -> int8, 0.25 dB
  uint16_t vbat_min_mv;      // min VBAT in the last 24 h, same coding as Measurement
  float    int_t_max_c;      // max internal temperature in the last 24 h, 0.5 °C
  uint16_t charge_minutes;   // minutes with ~CHG low in the last 24 h -> uint8, 10 min
  uint8_t  interval_min;     // current uplink interval, minutes
  uint8_t  reset_reason;
};

size_t pack_measurement(const Measurement& m, uint8_t* out);  // returns MEASUREMENT_LEN
size_t pack_health(const Health& h, uint8_t* out);            // returns HEALTH_LEN

// Downlinks on PORT_DOWNLINK.
enum DownlinkCmd : uint8_t {
  DL_SET_INTERVAL = 0x01,  // 01 <u16 seconds, big-endian>, 60..3600
  DL_RAPID        = 0x02,  // 02 <u8 minutes>, 0 = off
  DL_HEALTH_NOW   = 0x03,  // 03
  DL_REBOOT       = 0x04,  // 04 B0 07  (magic so a stray byte can't reboot a field unit)
};

struct Downlink {
  DownlinkCmd cmd;
  uint16_t    value;  // seconds for SET_INTERVAL, minutes for RAPID
};

// Returns true and fills `dl` if the bytes are a valid command.
bool parse_downlink(const uint8_t* buf, size_t len, Downlink& dl);

}  // namespace payload
