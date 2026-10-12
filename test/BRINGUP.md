# Bring-up log: TW-1 rev A → rev B

> Representative values for the reference design (see the note in [README.md](README.md)).

Boards: rev A, 3 pcs (TW1A-001…003), hand-assembled from a JLC 4-layer order; rev B, 10 pcs (TW1B-001…010),
board-house assembled. Instruments: see the equipment table in [README.md](README.md).

## Rev A first power-on (TW1A-001)

| Step | What we did | What we saw | OK? |
|---|---|---|---|
| 1 | Visual + continuity: VSYS, VBAT, +3V3, VIN_SOLAR to GND | > 1 MΩ on all (VSYS/+3V3 charge the caps, then read open) | ✅ |
| 2 | Bench supply on BT1 contacts, 3.70 V, **50 mA limit**, no cell | 0.9 mA inrush blip, settles at 2.6 mA (module running factory AT firmware) | ✅ |
| 3 | +3V3 at TP1 | 3.298 V, 22 mVpp ripple at 2.6 mA (PFM) | ✅ |
| 4 | J1 from a 5.0 V supply, 500 mA limit | VSYS 4.41 V, PGOOD low; supply on BT1 sinks 470 mA through a 2 Ω load: charging | ✅ |
| 5 | UART2 at 115 200 Bd, `AT+VER=?` | RUI3 version string; flashed tradewind v0.9 over UART2 (BOOT0 high), 12 s | ✅ |
| 6 | I²C scan | 0x45 (internal SHT40); 0x44 appears with the air probe on J4 | ✅ |
| 7 | OTAA join to the lab gateway | joined in 6 s, SF9 | ✅ |
| 8 | Sleep current, PPK2, 4.10 V (cell-like) | **34.2 µA**. Budget 6.9 µA | ❌ |
| 9 | Rain gauge on J2, 50 slow tips by hand | **2–6 counts per tip** (173 counts for 50 tips) | ❌ |
| 10 | Soil probe, LED, magnet tap | all work | ✅ |

### Issue 1: sleep current 34 µA instead of 7 µA

- **Symptom:** 34.2 / 36.8 / 33.5 µA on the three rev A boards at 4.10 V, but only 8.6 µA at 3.70 V. Strongly
  dependent on the battery voltage, so not a part stuck on.
- **Isolate:** with the PPK2 running, lifted parts one at a time. Lifting Q3's source (battery-divider switch) dropped
  TW1A-001 to **7.3 µA**.
- **Root cause:** rev A switched the battery divider on the **low side**. With the FET off, the divider's bottom floats
  up to VBAT, so the ADC pin (PB3) sits at VBAT. Above about 3.6 V (VDD 3.3 V + a diode drop), the STM32's clamp
  diode on PB3 conducts into the 3.3 V rail. That is ~27 µA at 4.05 V and 40 µA at 4.2 V, exactly as
  [`sim/vbat_sense.py`](../sim/vbat_sense.py) reproduces once the clamp is modelled.
- **ECO-1 (rev A rework):** moved the switch to the high side: AO3401A dead-bugged between VBAT and the divider, gate
  pulled up to VBAT with 1 MΩ, driven by the existing BSS138. Divider raised to 100 k / 100 k with 10 nF.
  **7.4 µA and 7.6 µA** on the two reworked boards.
- **Rev B:** the high-side switch is on the board (Q2, Q3, R9, R10). Firmware waits 5 ms after enable before sampling
  (settles to ½ LSB in 4.3 ms).

### Issue 2: rain gauge double-counting

- **Symptom:** 173 counts for 50 tips; 2–6 counts per tip, worse on fast tips.
- **Scope on RAIN_IN:** reed bounce, 4–7 transitions over ~1.5 ms at closing and 2–3 at opening; rev A had only the
  1 MΩ pull-up (R24 was 0 Ω, no C22), so every bounce reached the EXTI pin.
- **ECO-2:** 10 kΩ in series (R24) and 22 nF to GND (C22) at the pin. Closing time constant 0.22 ms swallows the
  bounce; release time constant 22 ms is still 18× faster than the fastest real tipping (≈ 2 tips/s).
  As a second line of defence, firmware ignores edges within 50 ms of a counted tip.
  Result after rework: **50 counts for 50 tips**, then 1 199 / 1 200 on the motorised bench test (rev B).
  Matches [`sim/rain_debounce.py`](../sim/rain_debounce.py) (rev A 5 counts per tip, rev B 1).

### Other rev A notes folded into rev B

- Added TP6 (AUX_ADC) and moved the TP labels clear of the connectors.
- Silk "PROTECTED 18650 Li-ion ONLY" next to the holder (an unprotected cell would rely only on firmware cut-off).
- The 2 × 22 µF + 10 µF output capacitance stays (rev A load step −41 mV, same as rev B).

## RF match tuning in the closed case (rev A → rev B values)

1. **Setup:** NanoVNA-H4, SOL cal at the end of the U.FL-SMA pigtail; board in the closed enclosure, antenna on the
   bulkhead, unit hanging on a 1 m mast stub (hands and bench kept away).
2. **Unmatched** (C14 DNP, L2 0 Ω, C15 DNP): −11 dB at 915 MHz, −9.9 dB worst in band. The Smith chart showed the
   antenna as capacitive at 915 MHz, ≈ 38 − j22 Ω: the whip's resonance sits above the band, and the box pulls it
   down only part of the way.
3. Tried the **draft values from the spec** (L2 3.3 nH, C15 1.2 pF): no better (−10 dB). They suit a ≈ 57 Ω load,
   not this one, which is the same answer [`sim/rf_match.py`](../sim/rf_match.py) gives.
4. Fitted the optimiser's values, **C14 1.8 pF (shunt, module side) + L2 7.5 nH (series), C15 DNP**:
   **−32.7 dB at 915 MHz, −19.0 dB worst across 902–928 MHz**. Swapping in 1.5 / 2.2 pF and 6.8 / 8.2 nH
   moved the notch ±8 MHz either side, so the chosen pair is centred. The parts measured slightly high (≈ 1.9 pF /
   8 nH on an LCR meter), which explains the notch landing ~1 MHz off the simulation.
5. Conducted power after the match: 19.9 dBm mean at J5 on all 64 channels. The radiated gain from the match is
   small (unmatched mismatch loss is only ≈ 0.4 dB, inside the RSSI scatter at the gateway); the real benefit is the
   PA seeing ≈ 50 Ω across the band, so output power and TX current stay steady from channel to channel.

## Rev B confirmation (10 boards)

All 10 boards: rails in tolerance (+3V3 3.290–3.315 V), sleep **6.7–8.1 µA** at 3.7 V, flash in ~12 s, join in
5–11 s, conducted power 19.5–20.5 dBm. One assembly defect (TW1B-006, solder bridge on U5) caught by the production
tester's I²C scan and reworked. Rev B is the released design; see [README.md](README.md) for the full test results.
