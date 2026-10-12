# Tradewind TW-1 — design specification (source of truth)

Solar-powered LoRaWAN field sensor for farms, nurseries and remote sites in Hawaiʻi.
Every number used by the schematic, simulations, firmware, test plans and report comes from here.
If a value changes, change it here first.

## 1. What it does

Measures air temperature and humidity (in a radiation shield), soil moisture (capacitive probe),
rainfall (tipping-bucket gauge), and its own health (battery, solar, enclosure temperature/humidity),
then sends a compact LoRaWAN uplink. Default every **5 min**; **rapid mode 1 min** (irrigation, frost,
storm). Sealed: no buttons outside. A magnet tapped on the lid logo wakes it / forces a join / sends now.

## 2. Requirements (targets)

| ID | Requirement | Target |
|---|---|---|
| R1 | Uplink interval | 5 min default, 1 min rapid, US915 sub-band 2, SF7–SF10 (ADR) |
| R2 | Sleep current (whole board, at battery, 3.7 V) | ≤ 10 µA |
| R3 | Average current, 5-min interval, SF9 | ≤ 100 µA |
| R4 | Dark autonomy (no sun, 1-min rapid mode) | ≥ 60 days |
| R5 | Energy-positive every month in Honolulu, incl. a 7-day overcast run | yes |
| R6 | Battery charging only inside 0–50 °C (cell spec 0–45 °C preferred) | NTC-qualified |
| R7 | Air temperature accuracy (external probe, 0–50 °C) | ±0.3 °C |
| R8 | Humidity accuracy (external probe, 10–90 %RH) | ±2 %RH |
| R9 | Radio range, line of sight, SF10 | ≥ 5 km |
| R10 | Ingress protection | IP66 (target), dunk 30 min at 1 m (IP67-style) as stretch |
| R11 | Operating temperature | −10 to +60 °C (electronics), enclosure in direct sun |
| R12 | ESD on all external connectors | ±8 kV contact (IEC 61000-4-2 level 4) |
| R13 | Conducted TX power at U.FL | +20 dBm ±1 dB, 902.3–914.9 MHz |
| R14 | BOM cost (electronics, 1k units) | ≤ $25 |
| R15 | Rain gauge counting | no double counts from reed bounce; counts while asleep |

## 3. Architecture

```
 Solar panel 5 V / 2 W ──J1──▶ TVS D1 + reverse-FET Q1 ──VIN_SOLAR──▶ BQ24074 (U2) linear charger + power path
                                                                         │ OUT = VSYS (4.4 V regulated when sun, = VBAT when dark)
                                         Protected 18650 Li-ion BT1 ◀────┤ BAT (NTC RT1 on TS)
                                                                         ▼
                                                   TPS63900 (U3) buck-boost, 75 nA Iq ──▶ +3V3
   +3V3 ─▶ RAK3172 (U1, STM32WLE5 + SX126x radio) ── RF ── π-match ── U.FL (J5) ── pigtail ── SMA bulkhead ── 915 MHz whip
   +3V3 ─▶ SHT40-BD1B (U5, internal T/RH, I2C 0x45)
   +3V3 ─▶ F1 PTC ─▶ +3V3_EXT ─▶ J4 external SHT45-AD1B probe (I2C 0x44) in radiation shield (always powered, 80 nA idle)
   +3V3 ─▶ TPS22917 (U7) load switch ─▶ +3V3_SW ─▶ J3 capacitive soil probe (powered only while sampling)
   J2 rain-gauge reed ─▶ 1 MΩ pull-up + 10 kΩ / 22 nF debounce ─▶ PA0 (EXTI wake, counts in sleep)
   DRV5032FB (U4) hall switch ─▶ PA1 (magnet tap = wake)
   TPD4E02B04 (U6) ESD on SDA_EXT, SCL_EXT, SOIL_EXT, RAIN_EXT
```

## 4. Key component choices and values

### Solar input
- Panel: 5 V nominal, 2 W mono, 136 × 110 × 3 mm, Vmp 5.0 V, Imp 400 mA, Voc 6.0 V, Isc 440 mA at STC (25 °C cell).
  Temp coefficients: Voc −0.33 %/°C, Isc +0.05 %/°C, Pmax −0.40 %/°C. Cell ~ +25 °C over ambient at 1000 W/m².
- D1 SMAJ12A TVS at J1. Q1 DMP3099L P-FET reverse-polarity protection (Vgs ±20 V), R1 100 kΩ gate to GND.
- C1 10 µF/25 V, C2 1 µF/25 V on VIN_SOLAR.
- Solar sense: R2 1 MΩ / R3 330 kΩ, C3 100 nF → SOLAR_SENSE (ratio 0.2481).

### Charger U2 BQ24074RGT (VQFN-16 3×3)
- Mode: EN2 = LO, EN1 = HI → **USB500: input limit 475 mA, VIN-DPM active at 4.5 V (4.35–4.63)**.
  VIN-DPM is what makes it solar-friendly: input current is cut back so the panel never collapses below 4.5 V.
  (VIN-DPM is NOT active in the resistor-ILIM mode, which is why that mode is not used.)
- OVP 10.5 V (panel Voc 6.0 V, safe). VO(REG) 4.4 V on OUT/VSYS.
- RISET = 1.78 kΩ → ICHG = 890 AΩ / 1.78 kΩ = 500 mA (input-limited to ~470 mA in practice).
- RILIM = 1.62 kΩ (unused in USB500, populated per datasheet guidance).
- TMR → GND: safety timers disabled (slow solar charging would otherwise time out).
- ITERM open → 10 % termination. ~CE → GND. EN1 → VSYS. EN2 → GND.
- TS: 10 kΩ NTC (B 3435, 103AT-type), ITS 75 µA, VHOT 0.30 V, VCOLD 2.10 V → charge window ≈ 0 to 50 °C.
- IBAT(PDWN) (battery drain with no input) 4.3 µA typ / 6 µA max — the largest single sleep load.
- C4 4.7 µF on VSYS (OUT), C5 4.7 µF on VBAT.
- ~PGOOD → PA4, ~CHG → PB12 (100 kΩ pull-ups to +3V3: R15, R16).

### Battery BT1
- Protected 18650 Li-ion, 3 350 mAh, 3.0–4.2 V (PCM cut-off 2.5 V), Keystone 1042 holder. RT1 NTC next to the cell.
- Battery sense (high-side switched — see sim "vbat_sense"): Q2 AO3401A P-FET (S = VBAT), R9 1 MΩ gate pull-up,
  Q3 BSS138 driven by VBAT_SENSE_EN (PA9, R10 1 MΩ pull-down), divider R11 100 kΩ / R12 100 kΩ, C10 10 nF → VBAT_ADC (PB3).
  Rev A used a low-side switch; VBAT leaked through the ADC pin's clamp diode (27 µA at 4.05 V, 40 µA at 4.2 V). Rev B: 3 nA.

### Regulator U3 TPS63900 (WSON-10 2.5×2.5)
- VIN = VSYS (2.5–4.5 V), VOUT = +3V3. EN tied to VSYS. SEL → GND.
- RCFG3 (R8) = 16.2 kΩ → VO(1) = 3.3 V. RCFG1 (R6) = 36.5 kΩ, RCFG2 (R7) = 0 Ω → VO(2) = 3.3 V, input current unlimited.
- L1 2.2 µH Coilcraft XFL4020-222 (23 mΩ, 3.5 A). CIN C6 10 µF/10 V 0603 ; COUT C7, C8 22 µF/10 V 0805 (C9 100 nF HF).
- Iq 75 nA, >90 % efficiency at 10 µA load, ~93–95 % at 10–100 mA.

### MCU/radio U1 RAK3172 (STM32WLE5CC + SX126x-class radio, US915 "-SM" variant, pad antenna)
- Sleep (STOP2, RTC on) 1.69 µA. TX +20 dBm: 87 mA. RX: 5.2 mA. Run (sensing): ~4 mA at 3.3 V.
- Pin map: PB3/A0 VBAT_ADC · PB4/A1 SOIL_ADC · PB2/A2 SOLAR_SENSE · PA10/A3 AUX_ADC (test pad) · PA0 RAIN_IN ·
  PA1 HALL_N · PA8 SENSOR_EN · PA9 VBAT_SENSE_EN · PB5 LED · PB12 CHG_N · PA4 PGOOD_N · PA11 SDA · PA12 SCL ·
  PA13 SWDIO · PA14 SWCLK · PA2 UART2_TX · PA3 UART2_RX · BOOT0 (R13 10 kΩ pull-down + pad) · NRST (C11 100 nF, SW1).
- Decoupling: C12 10 µF + C13 100 nF at VDD.
- RF: π-network C14 (shunt, module side) – L2 (series) – C15 (shunt, connector side) → J5 U.FL.
  Rev A: 0 Ω / DNP. Rev B tuned in the enclosure (antenna ≈ 38 − j22 Ω at 915 MHz once detuned by the case):
  C14 1.8 pF, L2 7.5 nH, C15 DNP → −42.7 dB at 915 MHz, ≤ −21 dB across 902–928 MHz (sim/rf_match.py).
  50 Ω coplanar waveguide on L1 over L2 ground (JLC 4-layer 1.6 mm, 7628: L1–L2 dielectric 0.2104 mm, εr 4.4):
  trace 0.35 mm, gap 0.20 mm.
- J6 Tag-Connect TC2030-NL (SWD), J7 1.27 mm 4-pin UART pads (DNP header), SW1 reset.
- D3 green LED via R14 2.2 kΩ from PB5 (~0.5 mA).
- U4 DRV5032FB hall switch (omnipolar, push-pull, 5 Hz, 0.54 µA), C16 100 nF.

### Sensors & I/O
- U5 SHT40-BD1B internal T/RH (0x45), C17 100 nF. Sits on a slotted "island" so board heat doesn't reach it.
- I2C pull-ups R17, R18 4.7 kΩ to +3V3. External bus: R19, R20 100 Ω series (SDA_EXT/SCL_EXT).
- J4 external probe (JST PH 4): 1 +3V3_EXT · 2 GND · 3 SDA_EXT · 4 SCL_EXT. F1 PTC 100 mA hold.
- U7 TPS22917DBV load switch: VIN +3V3, VOUT +3V3_SW, ON = SENSOR_EN, CT 1 nF (C18), QOD tied to VOUT. C19 1 µF in, C20 1 µF out.
- J3 soil probe (JST PH 3): 1 +3V3_SW · 2 GND · 3 SOIL_EXT. R21 1 MΩ pull-down, R22 1 kΩ series, C21 100 nF → SOIL_ADC. Probe warm-up 100 ms, ~5 mA.
- J2 rain gauge (JST PH 2): 1 RAIN_EXT · 2 GND. R23 1 MΩ pull-up (to +3V3), R24 10 kΩ series, C22 22 nF → RAIN_IN.
  Fall τ = 0.22 ms, rise τ ≈ 22 ms; STM32 Schmitt input thresholds 0.3/0.7 VDD.
- U6 TPD4E02B04DQA (4-ch, 0.25 pF) on SDA_EXT, SCL_EXT, SOIL_EXT, RAIN_EXT.
- J1 solar (JST PH 2): 1 SOLAR_RAW · 2 GND.
- Test points: TP1 +3V3, TP2 VSYS, TP3 VBAT, TP4 GND, TP5 VIN_SOLAR, TP6 AUX_ADC.
- 3 fiducials, 4 × M3 mounting holes.

## 5. Power budget (at the battery, 3.7 V, buck-boost 90 % at light load)

| State | Current @ 3.3 V | Duration per uplink | Charge |
|---|---|---|---|
| Sleep (board) | — | — | 6.9 µA at battery (charger 4.3 + RAK 1.69·k + hall 0.54 + others) |
| Wake + sense (soil probe on) | 9 mA | 150 ms | 1.35 mC |
| TX SF9, 24-byte frame, +20 dBm | 87 mA | 206 ms | 17.9 mC |
| RX1 + RX2 windows | 5.2 mA | 2 × 25 ms | 0.26 mC |
| Waits between TX and RX windows (MCU low-power run) | 1.0 mA | 2.0 s | 2.0 mC |
| **Per uplink at 3.3 V** | | | **≈ 21.5 mC** |

5-min interval: 21.5 mC / 300 s = 72 µA @3.3 V → ~71 µA at battery + 6.9 µA sleep ≈ **78 µA** (1.9 mAh/day).
1-min interval: ≈ 365 µA (8.8 mAh/day). SF7 TX airtime 62 ms (5.4 mC).
Li-ion self-discharge ~2–3 %/month at 25–35 °C (≈ 3 mAh/day) — larger than the 5-min load.
Dark autonomy (80 % usable = 2 680 mAh): 1-min ≈ 228 days, 5-min ≈ 550 days (incl. self-discharge).

## 6. Mechanical (summary; details in mechanical/README.md)
- PCB 96 × 70 mm, 4-layer 1.6 mm, 4 × M3 holes at (4,4), (92,4), (4,66), (92,66) mm from top-left.
  All parts on top. 18650 holder across the top band; power bottom-left; sensor I/O bottom-middle; RF bottom-right.
- Enclosure: ASA (UV-stable) printed prototypes; design-for-molding later (draft angles kept ≥ 1°).
  Box + lid with silicone gasket cord, 4 × M4 stainless captive lid screws into brass heat-set inserts,
  4 × M3 PCB screws into heat-set inserts. Bottom wall: 4 × PG7 (M12) cable glands + SMA bulkhead (antenna points down).
  Side wall: M12 protective vent (ePTFE) against pressure/condensation.
- Solar panel on a ventilated sun roof (25 mm air gap) above the box: the panel is also the box's sunshade.
  Roof tilted 20° (Honolulu latitude 21.3° N), facing south.
- Radiation shield (stacked louvred plates, white ASA) on an arm, holds the SHT45 probe.
- Pole mount: bracket + two stainless hose clamps / U-bolts for 25–50 mm poles.

## 7. Brand / style
- Colors: teal #1d3f47, teal2 #26545a, orange #f08a3c / ink #c4621b, gold #fbbf4a, cream #fdf6e3.
- Chart palette (validated colorblind-safe, light surface): #00909a, #d9622a, #3d6ad0, #a87800, #9558c2 (fixed order).
  Status: good #1d7349, bad #b0322a. Spec limits drawn in muted dashed gray #5d6670. Use tools/plotstyle.py.
