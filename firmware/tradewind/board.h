// Tradewind TW-1 rev B — RAK3172 pin map. Matches docs/design-spec.md §4 and the schematic.
#pragma once

// Analog inputs
#define PIN_VBAT_ADC       PB3   // A0: VBAT / 2 through the high-side switched divider (R11/R12, C10)
#define PIN_SOIL_ADC       PB4   // A1: soil probe output (R22 1 k / C21 100 nF)
#define PIN_SOLAR_SENSE    PB2   // A2: VIN_SOLAR x 0.2481 (R2 1 M / R3 330 k, C3 100 nF)
#define PIN_AUX_ADC        PA10  // A3: test pad TP6, unused in firmware

// Digital
#define PIN_RAIN_IN        PA0   // tipping-bucket reed, active low, RC-debounced (R23/R24/C22)
#define PIN_HALL_N         PA1   // DRV5032FB push-pull, low while a magnet is near the lid logo
#define PIN_SENSOR_EN      PA8   // TPS22917 ON -> +3V3_SW (soil probe power)
#define PIN_VBAT_SENSE_EN  PA9   // BSS138 gate -> AO3401A high-side switch on the VBAT divider
#define PIN_LED            PB5   // green LED via 2.2 k (~0.5 mA)
#define PIN_CHG_N          PB12  // BQ24074 ~CHG, open drain, 100 k pull-up
#define PIN_PGOOD_N        PA4   // BQ24074 ~PGOOD, open drain, 100 k pull-up
// I2C (Wire): PA11 SDA, PA12 SCL, 4.7 k pull-ups. Internal SHT40 0x45, external SHT45 probe 0x44.
// SWD on PA13/PA14 (Tag-Connect J6). UART2 PA2/PA3 is the RUI3 AT/flash port (J7).

// Analog scaling
#define ADC_BITS           12
#define ADC_FULL_SCALE_MV  3300.0f     // analogReference(RAK_ADC_MODE_DEFAULT): VDD = 3.3 V; confirm at bring-up
#define VBAT_DIVIDER       2.0f        // 100 k / 100 k
#define SOLAR_DIVIDER      (1.0f / 0.2481f)

// Timings. VBAT divider: tau = 0.5 ms, 12-bit settling (½ LSB) needs 4.5 ms (sim/board_si.py; was 3 ms in the
// pilot firmware, 0.25 % low). Probe warm-up per vendor.
#define VBAT_SETTLE_MS     5
#define SOIL_WARMUP_MS     100

// I2C addresses
#define SHT_EXT_ADDR       0x44        // SHT45-AD1B in the radiation shield
#define SHT_INT_ADDR       0x45        // SHT40-BD1B on the board island
