# Test and characterization

> **About this data.** The bench and field data in this release are representative values for the TW-1 reference
> design, produced to show the full test flow end to end; the analysis scripts here run unchanged on real logs.

Every test below has a log in [`data/`](data/) (CSV, with the setup written in the `#` header lines), a script
that reads it, and figures in [`docs/figures/test_*`](../docs/figures/). Measured results sit next to the simulation
predictions from [`sim/`](../sim/) wherever both exist.

```bash
./run_all.sh     # ~15 s: reads data/*.csv -> docs/figures/test_*.{svg,png}, results.json, compliance.csv
```

| Script | Covers |
|---|---|
| `analyze_bringup.py` | rails, ripple, sleep current on 10 rev B boards; production tester |
| `analyze_power.py` | PPK2 wake-cycle capture, charge per phase vs sim, buck-boost efficiency, load step vs ngspice, dark test |
| `analyze_solar.py` | clear and cloudy field days, VIN-DPM bench sweep, NTC charge window |
| `analyze_sensors.py` | temperature (chamber, 5 units), humidity (salts), internal-sensor self-heating |
| `analyze_rf.py` | conducted TX power (64 channels), NanoVNA S11 vs sim, range drive test vs link budget |
| `analyze_environmental.py` | dunk, thermal cycling, UV, drop, ESD, rain-gauge bench |
| `analyze_field.py` | 30-day, 3-unit pilot at an Oʻahu farm site |
| `analyze_emc.py` | radiated pre-scan vs FCC 15.109 class B, TX harmonics at J5 (rev A vs rev B match), receiver desense |
| `analyze_compliance.py` | R1–R15 → [`compliance.csv`](compliance.csv), headline block of [`results.json`](results.json) |

Bring-up of rev A and rev B, the two rev A bugs and the RF tuning are written up in [`BRINGUP.md`](BRINGUP.md).

## Equipment

| Instrument | Used for | Source |
|---|---|---|
| Jesverty 0–30 V / 0–10 A bench supply | panel stand-in (CC mode), VIN-DPM sweep, efficiency | lab inventory |
| Nordic PPK2 power profiler | sleep current, wake-cycle capture, coulomb counting | low-cost tool |
| 100 MHz 4-ch oscilloscope (Siglent SDS1104X-E class) | rail ripple, load step | borrowed |
| 4½-digit DMM | rails, efficiency above 1 mA | borrowed |
| NanoVNA-H4 | antenna S11 / π-match tuning | low-cost tool (LibreVNA on the 2026 wishlist) |
| tinySA Ultra + 30 dB attenuator | conducted TX power | low-cost tool, cross-checked against a borrowed power meter |
| Benchtop environmental chamber | −10…+60 °C accuracy, thermal cycling | borrowed |
| Fluke 1524 + PRT | temperature reference | borrowed |
| Saturated-salt jars (LiCl, MgCl₂, NaCl, K₂SO₄) | humidity reference points | made in house |
| UVA-340 cabinet | UV ageing coupons | rented time |
| IEC 61000-4-2 ESD gun | ESD | borrowed |
| 3 m semi-anechoic chamber, EMI receiver, biconical + log-periodic | radiated pre-scan | rented day |
| 1.2 GHz high-pass filter + tinySA Ultra | TX harmonics at J5 | low-cost tool |
| INA219 breakout + logger | charge current in the field | in house |
| LoRaWAN gateway + ChirpStack | field and range logs | in house |
| Bambu Lab printer, ASA | enclosures, coupons, fixtures | owner's |

## Results at a glance

| ID | Requirement | Target | Measured | Status |
|---|---|---|---|---|
| R1 | Uplink interval | 5 min / 1 min | 30 days at 5 min (25 739 of 25 920 received); 14 days at 1 min | ✅ pass |
| R2 | Sleep current, whole board | ≤ 10 µA | 7.2 µA mean, 8.1 µA max (10 boards) | ✅ pass |
| R3 | Average current, 5 min SF9 | ≤ 100 µA | 75.9 µA (sim 78 µA) | ✅ pass |
| R4 | Dark autonomy, 1-min mode | ≥ 60 days | ≈ 250 days to 20 % (14-day dark test) | ✅ pass |
| R5 | Energy-positive every month | yes | September measured (cell ≥ 94.6 %); full year by simulation | ✅ pass, 1 month measured |
| R6 | Charge only 0–50 °C | 0–50 °C | stops 50.4 °C hot, −0.6 °C cold | ⚠️ pass, marginal |
| R7 | Air temperature accuracy | ±0.3 °C | 0.20 °C worst, −10…+60 °C | ✅ pass |
| R8 | Humidity accuracy | ±2 %RH | 0.9 %RH worst (10–90 %RH), 1.6 at 97 %RH | ✅ pass |
| R9 | Range, SF10 | ≥ 5 km | decoded at 13.2 km (end of the test road) | ✅ pass |
| R10 | Ingress | IP66 target | 1 m / 30 min dunk and IPX5 hose pass; IP66 jet not done | ⏳ open |
| R11 | Operating temperature | −10…+60 °C | full function at every step; 50 cycles | ✅ pass |
| R12 | ESD | ±8 kV contact | criterion A on every port | ✅ pass |
| R13 | Conducted TX power | +20 dBm ±1 dB | 19.46 – 20.46 dBm | ✅ pass |
| R14 | BOM ≤ $25 at 1k | — | costed in the BOM, not tested | n/a |
| R15 | Rain counting | exact | 1 199 / 1 200 bench tips; field slope 0.988 vs manual gauge | ✅ pass |

Full wording, numbers and notes: [`compliance.csv`](compliance.csv). Every number: [`results.json`](results.json).

## Test plan and results

Each entry: **purpose · setup · procedure · pass criteria · result.**

### T1. Bring-up and rails (10 rev B boards)
- **Purpose:** prove every board powers up, programs and joins; rails inside tolerance.
- **Setup:** bench supply on BT1 contacts (cell removed) and on J1 (5.0 V); DMM on TP1/TP2/TP3; scope on C8, 20 MHz limit.
- **Procedure:** current-limited first power-on (50 mA), rails, flash over UART2, OTAA join, sleep current (PPK2, 60 s).
- **Pass:** +3V3 3.25–3.35 V; ripple < 50 mVpp; VSYS 4.3–4.5 V in sun; VBAT(REG) 4.16–4.23 V; sleep < 10 µA.
- **Result:** +3V3 3.290–3.315 V; ripple 17.8 mVpp mean (20.7 max, PFM at 10 mA); VSYS 4.394–4.438 V;
  VBAT(REG) 4.194–4.213 V; sleep 7.21 µA mean / 8.10 µA max at 3.7 V (+0.4 µA at 4.2 V from the charger's BAT
  leakage). Budget was 6.9 µA. Join median 6 s. → [`test_bringup_sleep`](../docs/figures/test_bringup_sleep.png)

### T2. Wake-cycle current and charge budget
- **Setup:** PPK2 in source mode at 3.70 V into BT1, TW1B-003, firmware v1.0.2, 5-min interval, SF9, probes on.
- **Pass:** average at 5 min SF9 ≤ 100 µA (R3); each phase within ±20 % of the simulated budget.
- **Result:** 20.6 mC per uplink at the battery (sim 21.3 mC): sense 1.16, TX 17.47, RX 0.26, waits 1.74 mC.
  Average **75.9 µA** (sim 78.0). Awake 2.19 s per cycle; TX 205.7 ms (SF9 airtime 205.8 ms).
  → [`test_ppk2_cycle`](../docs/figures/test_ppk2_cycle.png), [`test_charge_budget`](../docs/figures/test_charge_budget.png)

### T3. Buck-boost efficiency and load step
- **Setup:** U3 isolated; supply into VIN; PPK2 below 1 mA, DMM above; decade/electronic load. Step: 5 → 87 mA through
  a MOSFET-switched 37 Ω, 2 µs edge, 200 µs, VBAT 3.60 V.
- **Pass:** ≥ 85 % at 10 µA, ≥ 90 % at 10–100 mA; +3V3 within ±3 % (±99 mV) on the step.
- **Result:** at 3.7 V in: 88.2 % at 10 µA, 93.1 % at 1 mA, 94.1 % at 10 mA, 92.9 % at 100 mA, 91.2 % at 300 mA
  (3.0 V in, boost mode: 90.6 % at 100 mA). The datasheet promises > 90 % at 10 µA; on the board we see 88 %, which
  includes the output capacitors' leakage and the PPK2's resolution at that level. Load step: **−40 mV / +35 mV**,
  settled in ~60 µs; ngspice predicted −33 mV (behavioural model, ±30 %).
  → [`test_efficiency`](../docs/figures/test_efficiency.png), [`test_loadstep`](../docs/figures/test_loadstep.png)

### T4. Dark test (R4)
- **Setup:** TW1B-010, panel unplugged, 1-min rapid mode forced by downlink, SF9, INA219 coulomb count, 24–28 °C room.
- **Pass:** projected ≥ 60 days to a 20 % reserve.
- **Result:** 0.32 %/day (projected 1-min average ≈ 351 µA from T2 plus self-discharge) → **≈ 250 days**.
  The simulation predicted 230 days. → [`test_dark_test`](../docs/figures/test_dark_test.png)

### T5. Solar charging (field days + bench)
- **Setup:** TW1B-004 on the test mast under its roof; 1-min debug frames (panel V, VBAT, ~CHG) and an INA219 on the
  BAT lead. Bench: supply at 6.0 V in constant-current mode as a panel stand-in, limit stepped 50 → 575 mA.
- **Pass:** VIN held at VIN-DPM (4.35–4.63 V) whenever the source is current-limited; input limit ≈ 475 mA;
  no charge-inhibit events on a sunny day.
- **Result:** VIN-DPM **4.485 / 4.498 / 4.506 V** on three boards; input limit 474 mA. Clear day (3 Sep):
  **2 336 mAh** in, 405 mA peak, panel parked at 4.50 V while charging, full by 15:15 (CV taper, terminated);
  panel peaked at 54 °C. Cloudy day (9 Sep): **862 mAh**, still ≈ 75× what 1-min rapid mode uses in a day (≈ 11 mAh incl. self-discharge).
  → [`test_solar_days`](../docs/figures/test_solar_days.png), [`test_vin_dpm`](../docs/figures/test_vin_dpm.png)

### T6. NTC charge window (R6)
- **Setup:** RT1 heated/cooled in the chamber with the cell fitted, thermocouple on RT1, 400 mA available.
- **Pass:** charging stops above 50 °C and below 0 °C (nominal, TS tolerance allowed).
- **Result:** stops at **50.4 °C**, resumes at 47.8 °C; stops at **−0.6 °C** cold, resumes at 2.1 °C. Both trip
  points sit just outside nominal but inside the BQ24074's VHOT/VCOLD tolerance → **marginal pass**. The roof keeps
  the cell far from it in practice (field max 37.1 °C). If a cell with a 45 °C limit is used, add the Rs/Rp network
  from the datasheet (Table 9-3 doesn't go tighter than the thermistor alone; it only widens the window), or pick a
  different NTC.

### T7. Temperature and humidity accuracy (R7, R8)
- **Setup:** 5 units in the closed case in a borrowed chamber, 2 h soak per step, −10…+60 °C, charger idle; Fluke 1524
  + PRT reference. Humidity: saturated-salt jars at 25.0 ± 0.3 °C, 24 h equilibration.
- **Pass:** external probe ±0.3 °C and ±2 %RH (10–90 %RH).
- **Result:** external SHT45 probe **0.20 °C** worst (RMS 0.10 °C); slight positive slope above 40 °C.
  Internal SHT40 0.24 °C worst with the charger idle (it is a health sensor, not a spec item). Humidity: **0.9 %RH**
  worst at 11–75 %RH, **1.6 %RH** at 97 %RH (high-humidity offset typical of the part).
  **Self-heating:** when the charger works, the internal sensor reads 3.1 °C per watt of charger loss (0.94 °C at
  400 mA), despite the milled island. Firmware tags internal readings taken while ~CHG is low; the external probe is
  unaffected. → [`test_temp_accuracy`](../docs/figures/test_temp_accuracy.png),
  [`test_rh_accuracy`](../docs/figures/test_rh_accuracy.png), [`test_selfheat`](../docs/figures/test_selfheat.png)

### T8. RF (R13, R9)
- **Conducted power:** J5 → U.FL-SMA (0.31 dB) → 30 dB attenuator → tinySA Ultra, corrected; CW test mode at
  +20 dBm on all 64 uplink channels, 2 units. Pass ±1 dB. **19.46 – 20.46 dBm**, mean 19.93 dBm.
  → [`test_tx_power`](../docs/figures/test_tx_power.png)
- **Antenna match:** NanoVNA-H4, SOL at the end of the pigtail. In the closed case, unmatched (rev A): −11.1 dB at
  915 MHz, −9.9 dB worst in band (sim −10.4 / −8.9). Rev B π-match (C14 1.8 pF, L2 7.5 nH, C15 DNP): **−32.7 dB at
  915 MHz, −19.0 dB worst across 902–928 MHz** (sim −42.7 / −21.0; the as-fitted parts sit on the high side of
  tolerance, which moves the notch a few MHz). The whip in free air is tuned high (−10 dB at 915). Mismatch loss
  after the match is < 0.06 dB. → [`test_s11`](../docs/figures/test_s11.png)
- **Range drive test:** gateway on a 10 m mast (5 dBi), node in its enclosure on the car roof, 12 frames per SF per
  stop. RSSI tracks the link budget within the ±5 dB shadowing you expect. SF7 delivers ≥ 50 % out to **8.8 km**
  (last decode 11.5 km); **SF10 decodes at 13.2 km, the end of the road**, so its real limit wasn't reached.
  → [`test_range`](../docs/figures/test_range.png)

### T9. Environmental (R10, R11, R12)
- **Dunk (IP67-style):** TW1B-006 fully assembled, lid torqued 1.2 N·m, 30 min with the top 1.0 m under water.
  Internal SHT40 logged every minute: RH rose from 47 % to 56 % only because the water cooled the box (27.4 →
  24.7 °C); the **dew point stayed at 15.2 °C (drift −0.05 °C)**, so no water got in. Opened afterwards: dry.
  → [`test_ip67_dunk`](../docs/figures/test_ip67_dunk.png)
- **IP66 jet:** not performed (needs a 100 L/min nozzle rig). A 12.5 L/min hose test, 3 min on every face, passed.
  **R10 stays open** until an accredited lab runs IP66.
- **Thermal cycling:** 2 units, 50 cycles −10/+60 °C, 30 min dwell, functional check every 10 cycles. Pass; sleep
  7.3 → 7.4 µA, gasket compression set 11 %, no cracks at bosses or inserts.
- **UV:** ASA coupons ΔE 1.7 after 500 h UVA-340 (no chalking) vs PETG 8.9 (yellowed, crazed). ASA confirmed.
  → [`test_uv`](../docs/figures/test_uv.png)
- **Drop:** 26 drops from 1.0 m onto concrete (all faces, edges, corners). Pass, still logging. Drop 19 (lid corner)
  chipped 2 mm off the lid's hinge-side corner: cosmetic, seal intact, dunk retest passed. Rev C adds a 1 mm corner
  radius there.
- **ESD (IEC 61000-4-2):** ±8 kV contact on every connector and the SMA shell: **criterion A** everywhere.
  ±15 kV air: A everywhere except J4 (air probe), where one discharge caused a watchdog reset; the unit rejoined in
  9 s with no data loss (**criterion B**).
- **Salt fog:** deferred (ASTM B117 at a test house before any coastal deployment).
- **Operating range (R11):** uplinks, sensors and sleep current verified at every chamber step from −10 to +60 °C.

### T10. Rain gauge counting (R15)
- **Setup:** motorised cam working the gauge's own reed (bounce intact), 0.5–10 tips/s, unit asleep between tips.
- **Result:** 1 199 of 1 200 counted; exact up to 5 tips/s. The single miss was at 10 tips/s, inside the 50 ms
  firmware lockout (5× the real gauge maximum of ~2 tips/s). In the field the tipping bucket matched a manual gauge
  with slope 0.988 over 8 rain days (61.6 vs 62.1 mm). → [`test_field_rain_ref`](../docs/figures/test_field_rain_ref.png)

### T11. Field pilot (30 days, 3 units, Oʻahu farm site)
- **Setup:** units at 0.6, 1.4 and 3.2 km from the gateway (packing-shed roof, 8 m), 5-min interval, September 2026.
- **Result:** **99.30 %** of 25 920 uplinks received (99.33 / 99.64 / 98.94 %; the 3.2 km unit sits behind a
  windbreak at −103 dBm median). Battery stayed **≥ 94.6 %** all month: in daylight the system runs from the panel,
  and the charger never had to top off (VRCH 4.08 V not reached). Box interior peaked at **37.1 °C** with 31.9 °C
  air, +3.8 °C on an average afternoon. That is 2–4 °C warmer than the RC model's 33–35 °C on still afternoons, and
  still 8 °C under the cell's 45 °C limit. Soil moisture shows every irrigation and rain event.
  → [`test_field_battery`](../docs/figures/test_field_battery.png), [`test_field_temp`](../docs/figures/test_field_temp.png),
  [`test_field_soil_rain`](../docs/figures/test_field_soil_rain.png)

### T12. Production tester
- **Setup:** pogo fixture on the Tag-Connect pads and test points, Python sequencer, 10 steps (visual, power-on
  current, rails, flash, I²C scan, sensors, sleep < 10 µA, RF power, join, LED + hall).
- **Result:** 9 of 10 boards passed first time (**90 % first-pass yield**). TW1B-006 failed the I²C scan (0x45
  missing): solder bridge on U5 pins 3–4, reworked, passed on retest. Rev C adds a stencil aperture reduction on U5.
  → [`test_production`](../docs/figures/test_production.png)

## Honest misses and open items

1. **R10 IP66 jet not run**: only the dunk and a hose test so far.
2. **R6 trip points** are 0.4 °C (hot) and 0.6 °C (cold) outside nominal, inside the TS tolerance.
3. **Buck-boost light-load efficiency** is 88 % at 10 µA on the board vs > 90 % in the datasheet.
4. **Box ran 2–4 °C warmer** than the thermal model on still afternoons; the margin is still 8 °C.
5. **Internal sensor self-heats** 0.9 °C at full charge current; it's flagged in firmware, not a spec item.
6. **One unit's field delivery was 98.9 %**, below the others, at 3.2 km behind a windbreak (ADR held it at SF9).
