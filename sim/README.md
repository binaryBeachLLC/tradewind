# Simulations

Every design decision on the TW-1 that can be checked before building hardware is checked here.
Each script answers one question, prints its numbers, writes a figure to `docs/figures/sim_*.{svg,png}`
and merges its headline numbers into [`results.json`](results.json). All inputs come from
[`docs/design-spec.md`](../docs/design-spec.md).

```bash
./run_all.sh          # ~20 s: regenerates every figure and results.json
```

Needs the `hwdesign` conda env (Python 3.11, numpy, scipy, matplotlib, **ngspice 41**). SPICE decks live
in [`spice/`](spice/) (shared device models in `spice/models.lib`); expanded decks, raw data and logs are
written to `out/`. Plot style: `tools/plotstyle.py`.

| Script | Question | Figure |
|---|---|---|
| `solar_iv.py` | How much panel power does the charger's fixed 4.5 V VIN-DPM capture? | `sim_solar_iv` |
| `thermal_enclosure.py` | Does the cell stay inside its charge window in the sun? | `sim_thermal_enclosure` |
| `energy_year.py` | Is it energy-positive all year, through a stormy week? | `sim_energy_year` |
| `power_budget.py` | Where does the charge go; average current per mode | `sim_power_budget` |
| `link_budget.py` | Range per spreading factor; time on air | `sim_link_budget` |
| `vbat_sense.py` (ngspice) | Why a high-side switch on the battery divider; ADC settle time | `sim_vbat_sense` |
| `tx_droop.py` (ngspice) | Does +3V3 hold ±3 % when the radio keys up? Which COUT? | `sim_tx_droop` |
| `rain_debounce.py` (ngspice) | One bucket tip = exactly one count? | `sim_rain_debounce` |
| `rf_match.py` | Antenna match in the enclosure; 50 Ω coplanar trace width | `sim_rf_match`, `sim_cpwg` |

## Results

**solar_iv.** Single-diode model of the 5 V / 2 W panel (10 cells, fitted to Voc 6.0 V, Isc 0.44 A,
Vmp 5.0 V, Imp 0.40 A; n = 1.52, Rsh 800 Ω; Pmax tempco −0.41 %/°C). The panel's Isc is below the
charger's 475 mA USB500 limit, so in sun the input sits at VIN-DPM = 4.5 V and the charge current equals
the panel current at 4.5 V. Fixed 4.5 V captures **96 % of MPP at 25 °C and 99 % with the cell at 55 °C**
(the normal case in sun, Vmp drops to 4.37 V); the 4.35–4.63 V part tolerance spans 93–100 %.
At 100 W/m² capture falls to 85–90 %, which doesn't matter (see energy_year). No MPPT chip needed.

**thermal_enclosure.** Two-node RC model (shell 260 J/K, cell+PCB+air 95 J/K) with real sun geometry for
Honolulu on 15 Aug, and the linear charger's own loss heating the cell. Design case is a calm, hot
**Kona-wind day** (25→32 °C, wind < 1.2 m/s): peak cell temperature is **51 °C for a grey box** (2.8 h
above the 50 °C TS cutoff), **55 °C if the panel is glued to the lid** (5.4 h of charging lost),
**39 °C for a white box** and **35 °C under the ventilated solar roof** (0 h). On a normal trade-wind day
the same cases peak at 45 / 49 / 36 / 33 °C. Colour is the biggest lever; the roof lets the panel sit on
the box without heating it and adds 3–4 K of margin.

**energy_year.** 8 760-hour run (seeded weather, monthly GHI 4.2–6.6 kWh/m²/day, a forced 7-day overcast
run in December, charging blocked outside 0–50 °C). The 2 W panel harvests a median **2 300 mAh/day**;
the worst day of the year (overcast) still delivers **158 mAh**, 13× the 1-min rapid-mode use
(11.7 mAh/day incl. self-discharge). From the 30 % air-shipping charge the cell is full in **1.4 days**.
SoC never drops below 99.7 % after the first two weeks in either mode. With no sun at all: **230 days**
(1-min) / **551 days** (5-min) to a 20 % reserve. Charge-inhibit hours per year: 0 with the roof,
161 with the panel glued to the lid.

**power_budget.** Per uplink at 3.3 V: 9.0 mC (SF7), 21.5 mC (SF9), 35.9 mC (SF10); TX is 60–90 % of it.
Average current at the battery: **78 µA at 5-min SF9** (R3 target ≤ 100 µA ✔), 37 µA at SF7, 125 µA at
SF10; 1-min rapid: 155 / 362 / 599 µA. Sleep (6.9 µA) is only 9 % of the 5-min SF9 budget.

**link_budget.** Okumura–Hata open area + 5 dB agricultural clutter, 10 m gateway mast, +20 dBm,
2 dBi / 5 dBi antennas. With a 10 dB fade margin: **SF7 5.7 km, SF8 6.8 km, SF9 8.1 km, SF10 9.7 km**
(R9 ≥ 5 km at SF10 ✔, met even at SF7). Time on air for the 24-byte frame: 62 / 113 / 206 / 371 ms.

**vbat_sense.** Rev A switched a 10 k/10 k divider on the low side: with the FET off the ADC pin is pulled
to VBAT and the STM32 clamp diode conducts into the 3.3 V rail — **27 µA at 4.05 V, 40 µA at 4.2 V**
(1.3 µA at 3.7 V), i.e. 4–6× the whole sleep budget whenever the cell is well charged. Rev B (high-side
AO3401A, 100 k/100 k): **3 nA**. After enable the ADC node settles to ½ LSB (12-bit) in **4.3 ms**;
firmware samples at 5 ms.

**tx_droop.** Averaged buck-boost model (PI loop + 8 µs lag; behavioural, ±30 % on absolute mV) with a
3.6 V cell. 5→87 mA step: **45 mV dip with 1×22 µF, 35 mV with 2×22 µF, 33 mV with 2×22 µF + 10 µF at
the module** — all inside ±3 % (±99 mV); 1×22 µF rings. Load release overshoots by the same amount.
The cell sags 12 mV during TX (87 mA through 0.15 Ω + contacts). Rev B uses 2×22 µF + 10 µF.

**rain_debounce.** With the rev B 10 kΩ / 22 nF filter the reed's bounce is invisible: **1 count per
tip; rev A (no cap) counted 5** (3 at closure, 2 at release). The slow 22 ms release τ is the price: the
pin is back above VIH 27 ms after the reed opens, so the input supports **13 tips/s** — the gauge's
real maximum is ~2 tips/s (200 mm/h, 0.2 mm bucket). If a reed sticks closed the pull-up draws 3.3 µA.

**rf_match.** Antenna at the U.FL modelled as a detuned resonator (Z ≈ 37.5 − j21.4 Ω at 915 MHz, in the
closed box). Unmatched: −10.4 dB at 915, −8.9 dB worst in band (0.4 dB mismatch loss). An optimiser over
standard 0402 values (with parasitics) picks **C14 = 1.8 pF (shunt, module side) + L2 = 7.5 nH (series),
C15 DNP: −42.7 dB at 915, ≤ −21 dB across 902–928 MHz.** CPWG: 0.35 mm trace with 0.20 mm gaps is
**48–52 Ω** (thick/thin conformal-mapping models; 50 Ω at 0.32–0.38 mm). The RF trace is ~6 mm, λ/50 at
915 MHz: even a 45 Ω section would only add −41 dB of reflection.

## Findings for the designer

1. **RF match values in the spec don't match the antenna model.** The spec's rev B network
   (L2 3.3 nH series, C15 1.2 pF shunt at the connector, C14 DNP) only transforms a load of ≈ 57 + j1 Ω
   to 50 Ω. For a detuned, capacitive antenna like the one modelled (38 − j22 Ω) it gives −10.1 dB at
   915 MHz, no better than no match (−10.4 dB). Recommended rev B values: **C14 = 1.8 pF, L2 = 7.5 nH,
   C15 DNP** (−42.7 dB at 915, ≤ −21 dB in band). Either update the spec / schematic / test data to
   these, or keep 3.3 nH / 1.2 pF and describe the measured antenna as ≈ 57 Ω (a mild correction).
   The π footprint supports both.
2. **Rev A battery-sense leakage** comes out at 27 µA at 4.05 V and 31 µA at 4.1 V (spec says +24 µA):
   consistent if quoted at ~4.0 V; say "≈ 25–40 µA when the cell is above 4 V".
3. **The 2 W panel is oversized for energy**: the worst overcast day still gives 13× the 1-min use and
   ~100× on a typical day. That's fine because the panel doubles as the sun roof (its area does the
   shading); a 1 W panel would still be energy-positive with ~7× margin on the worst day. Keep 2 W for
   shade, future sensors and soiling margin.
4. **A white box alone already keeps the cell at 39 °C** on the calm design day; the roof's real value is
   letting the panel ride on the box without the 55 °C / 5.4 h-lost penalty of gluing it to the lid.
   Don't ship a dark grey housing (51 °C, 2.8 h lost).
5. CPWG geometry (0.35 / 0.20 mm) is fine; confirm with the fab's impedance calculator when ordering.
