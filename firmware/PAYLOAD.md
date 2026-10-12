# Tradewind TW-1 payload format

All multi-byte fields are **big-endian**. Signed fields are two's complement.
Packer: `tradewind/payload.cpp`. Decoder for The Things Stack / ChirpStack v4: `decoder/ttn_decoder.js`.
Both are tested against the same hand-worked bytes in `test/golden_vectors.json` (`make test`).

## fPort 1: measurement (11 bytes, unconfirmed, every 5 min or 1 min in rapid mode)

| Byte | Field | Type | Scale | Range | Missing sensor |
|---|---|---|---|---|---|
| 0 | flags | u8 | bit field, below | | |
| 1–2 | air temperature (external SHT45) | s16 | 0.01 °C | −327.68 … 327.66 °C | `0x7FFF` |
| 3 | air humidity (external SHT45) | u8 | 0.5 %RH | 0 … 100 % | `0xFF` |
| 4 | soil moisture | u8 | 0.5 % | 0 … 100 % | `0xFF` |
| 5–6 | rain tips, cumulative | u16 | 1 tip (0.2 mm) | wraps at 65 536 | |
| 7 | battery voltage | u8 | 2500 mV + 10 mV × code | 2.50 … 5.04 V | |
| 8 | internal temperature (SHT40) | s8 | 0.5 °C | −64.0 … 63.0 °C | `0x7F` |
| 9 | internal humidity (SHT40) | u8 | 0.5 %RH | 0 … 100 % | `0xFF` |
| 10 | solar panel voltage | u8 | 25 mV | 0 … 6.375 V | |

Flags (byte 0):

| Bit | Meaning |
|---|---|
| 0 | rapid (1-min) mode active |
| 1 | charging (BQ24074 ~CHG low) |
| 2 | power good (panel above the charger's UVLO) |
| 3 | battery low (< 3.30 V) |
| 4 | external air probe answered with a valid CRC |
| 5 | soil probe reading plausible (0.3–3.1 V) |
| 6 | internal SHT40 answered with a valid CRC |
| 7 | reserved, 0 |

The rain counter is cumulative on purpose: a lost uplink loses no rain, the server subtracts
consecutive values (mod 65 536).

Example (`golden_vectors.json`, "typical sunny afternoon"):
`76 09 85 7B 45 04 D2 95 3F 60 C3` → charging, power good, all sensors OK, 24.37 °C, 61.5 %RH,
soil 34.5 %, 1 234 tips (246.8 mm), battery 3.99 V, inside 31.5 °C / 48 %RH, panel 4.875 V.

## fPort 2: daily health (14 bytes, confirmed, once a day and on request)

| Byte | Field | Type | Scale |
|---|---|---|---|
| 0 | firmware major | u8 | |
| 1 | firmware minor | u8 | |
| 2–3 | uptime | u16 | days |
| 4–5 | uplinks sent | u16 | count, wraps |
| 6 | rejoins (magnet hold) | u8 | count |
| 7 | RSSI of the last downlink | s8 | 1 dBm |
| 8 | SNR of the last downlink | s8 | 0.25 dB |
| 9 | lowest battery voltage, last 24 h | u8 | as byte 7 above |
| 10 | highest internal temperature, last 24 h | s8 | 0.5 °C |
| 11 | minutes spent charging, last 24 h | u8 | 10 min |
| 12 | current uplink interval | u8 | minutes |
| 13 | reset reason | u8 | 0 power-on / other, 1 rebooted by downlink |

Byte 10 and byte 11 together show the thermal story in the field: a hot box (> 50 °C) with sun on the
panel but few charging minutes means the battery NTC is holding off the charge.

## fPort 10: downlink commands

| Bytes | Command | Notes |
|---|---|---|
| `01 HH LL` | set uplink interval, seconds | 60 … 3600, otherwise ignored |
| `02 MM` | rapid mode for MM minutes | `02 00` turns it off. Refused while the battery is low |
| `03` | send a health frame now | |
| `04 B0 07` | reboot | the two magic bytes stop a stray byte from rebooting a field unit |

JSON for the network server's encoder: `{"set_interval_s": 600}`, `{"rapid_minutes": 30}`,
`{"health_now": true}`, `{"reboot": true}`.
