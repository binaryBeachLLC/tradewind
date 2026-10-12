// Behaviour knobs. Values here are defaults; intervals can be changed over the air (PAYLOAD.md).
#pragma once

#define FW_MAJOR 1
#define FW_MINOR 2

#define INTERVAL_DEFAULT_S     300    // 5 min (spec R1)
#define INTERVAL_RAPID_S       60     // 1 min rapid mode
#define RAPID_DEFAULT_MIN      60     // auto-rapid lasts this long, then falls back
#define HEALTH_PERIOD_S        86400  // one confirmed health frame a day

// Auto-rapid triggers
#define RAPID_SOIL_DELTA_PCT   3.0f   // soil moisture moved this much since the last uplink
#define RAPID_RAIN_TIPS        5      // >= 5 tips (1.0 mm) since the last uplink (= 12 mm/h at 5 min)

#define RAIN_LOCKOUT_MS        50     // software lockout after a counted tip (RC debounce is the first line)
#define HALL_HOLD_REJOIN_MS    3000   // hold a magnet 3 s on the logo -> rejoin

#define BATT_LOW_MV            3300   // sets the battery-low flag; rapid mode is refused below this
#define BATT_CRIT_MV           3100   // below this: health frames only, once a day

// Soil probe calibration (capacitive probes read lower when wet). Two-point, set per probe type.
#define SOIL_DRY_MV            2550.0f
#define SOIL_WET_MV            1180.0f

// LoRaWAN
#define LORA_SUBBAND_MASK      0x0002 // US915 sub-band 2: channels 8-15 + 65
#define JOIN_RETRY_S           60     // doubles on each failure, capped
#define JOIN_RETRY_MAX_S       3600
