// Sensor reads. Every function powers what it needs, reads, and powers it back down.
#pragma once
#include <stdint.h>

struct ShtReading {
  bool  ok;      // device answered and both CRCs matched
  float t_c;
  float rh;
};

void     sensors_init();
ShtReading sht4x_read(uint8_t addr);   // high-precision single shot (0xFD), ~8.3 ms
float    soil_read_pct(bool& ok);      // switches +3V3_SW on for SOIL_WARMUP_MS
uint16_t vbat_read_mv();               // switches the high-side divider on for VBAT_SETTLE_MS
uint16_t vsolar_read_mv();             // always-on divider from the panel side (no battery drain)
bool     charger_charging();           // ~CHG low
bool     charger_power_good();         // ~PGOOD low

// Exposed for the host test.
uint8_t  sht_crc8(const uint8_t* data, int len);
