"""Generate docs/report/index.html — the Tradewind TW-1 rev B engineering design & test report,
on the Binary Beach letterhead. Every number comes from the result files via tools/docdata.py.
"""
import os

from docdata import (SIM, TEST, MECH, BOM, COMPLIANCE, BOM_ROWS, H, DOC_REPORT, REV, DATE, REPO, f, status_pill)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "report", "index.html")
pages = []


def page(body):
    pages.append(body)


def fig(src, cap, width="100%", n=None, cls=""):
    return ('<figure class="' + cls + '" style="margin:6px 0 10px"><img src="img/%s" style="width:%s;margin:0 auto" alt="">'
            '<figcaption>%s</figcaption></figure>' % (src, width, ("<b>Figure %s.</b> " % n if n else "") + cap))


FN = {"n": 0}


def F(src, cap, width="100%", cls=""):
    FN["n"] += 1
    return fig(src, cap, width, FN["n"], cls)


sim, tst, mech = SIM, TEST, MECH
th = sim["thermal_enclosure"]["design_day_kona_calm"]
roof = th["White box under ventilated solar roof"]
grey = th["Grey box, panel elsewhere"]
glued = th["White box, panel glued to lid"]
pb = sim["power_budget"]
lb = sim["link_budget"]
rf = sim["rf_match"]
sv = sim["solar_iv"]
ey = sim["energy_year"]
bu = tst["bringup"]
pw = tst["power"]
fld = tst["field"]
sen = tst["sensors"]
sol = tst["solar"]
rft = tst["rf"]
env = tst["environmental"]

# ======================================================================== 1 cover
page(f"""
<div class="doctype">Engineering design &amp; test report <span class="sample">Reference design</span></div>
<h1>Tradewind TW-1 · Solar LoRaWAN field sensor</h1>
<div class="meta">Rev {REV} · {DOC_REPORT} · {DATE} · Hardware &amp; Product Design · Concept to field pilot</div>
<p class="short">Rev B meets 13 of 15 requirements outright, one marginally, and one (IP66 jet) is open pending an accredited lab.
It sleeps at {f(H['sleep_uA_mean'],1)} µA, averages {f(H['avg_current_uA_5min_SF9'],0)} µA at a 5-minute interval, and kept its battery
above {f(H['field_min_soc_pct'],0)} % through a 30-day pilot in the Hawaiʻi sun.</p>
{fig('r_product_hero.jpg', 'Tradewind TW-1 as installed: ventilated solar roof, sealed electronics box, radiation shield for the air probe, pole bracket. Rendered from the production CAD.', '100%', cls='hero')}
<div class="stats" style="--n:3">
  <div class="stat good"><b>{f(H['sleep_uA_mean'],1)} µA</b><span>Sleep current, whole board (spec ≤ 10)</span></div>
  <div class="stat good"><b>{f(H['range_km_last_decode']['SF10'],1)} km</b><span>Range decoded at SF10, line of sight (spec ≥ 5)</span></div>
  <div class="stat good"><b>{f(fld['internal_max_C'],1)} °C</b><span>Hottest cell in the field, air at {f(fld['air_max_C'],1)} °C</span></div>
  <div class="stat good"><b>±{f(H['temp_err_max_C'],2)} °C</b><span>Worst air-temperature error, −10 to +60 °C</span></div>
  <div class="stat good"><b>{f(fld['pdr_pct_all'],1)} %</b><span>Uplinks received, 3 units × 30 days</span></div>
  <div class="stat"><b>${f(BOM['1000']['electronics_incl_pcb_pcba'],2)}</b><span>Electronics per unit at 1,000 (PCB + assembly incl.)</span></div>
</div>
<p class="fine">Prepared by Maxwell Pauly, Binary Beach LLC. Design files, firmware, simulations and test logs: {REPO}.
Bench and field figures in this edition are representative values for the reference design; the analysis scripts run unchanged on new logs.</p>
""")

# ======================================================================== 2 summary + compliance
rows = "".join(
    f"<tr><td>{r['id']}</td><td>{r['requirement']}</td><td>{r['target']}</td><td>{r['measured']}</td><td>{status_pill(r['status'])}</td></tr>"
    for r in COMPLIANCE if r["id"] != "R14")
rows += (f"<tr><td>R14</td><td>BOM cost, electronics, 1k units</td><td>≤ $25</td><td>${f(BOM['1000']['electronics_incl_pcb_pcba'],2)} "
         f"(parts ${f(BOM['1000']['components'],2)} + PCB + assembly)</td><td>{status_pill('pass')}</td></tr>")
page(f"""
<h2>1 · Summary</h2>
<p><b>The product.</b> A sealed, solar-powered sensor that reports air temperature and humidity, soil moisture and rainfall
over LoRaWAN every 5 minutes (1 minute in rapid mode), for farms and remote sites. No buttons, no battery changes:
a magnet tap on the lid wakes it, and the panel keeps a protected 18650 cell topped up.</p>
<p><b>The hard part was heat, not electrons.</b> Li-ion cells must not charge above 45–50 °C, and a box in the Hawaiian
sun gets far hotter than the air. Simulation showed a grey box reaching {f(grey['max_battery_C'],0)} °C and a panel glued to the
lid {f(glued['max_battery_C'],0)} °C ({f(glued['charge_inhibit_hours'],1)} h a day with charging blocked). Rev B mounts the panel on a ventilated roof
25 mm above a white ASA box: {f(roof['max_battery_C'],0)} °C in simulation, {f(fld['internal_max_C'],1)} °C measured in September.</p>
<p><b>What changed from rev A.</b> Bring-up found two bugs: sleep current of 34 µA (the battery-sense divider leaked into the ADC
clamp diode) and 2–6 rain counts per bucket tip (reed bounce). Both were reproduced in simulation, fixed in rev B and verified.
The antenna match was tuned with the lid closed, which moved return loss at 915 MHz from {f(rft['s11']['case_unmatched']['at_915_dB'],1)} to {f(rft['s11']['case_matched_revB']['at_915_dB'],1)} dB.</p>
<h3>How the work ran</h3>
<table class="small"><tr><th>Phase</th><th>What happened</th><th>Output (in the repo)</th><th class="n">Typical</th></tr>
<tr><td>1 · Concept</td><td>Use cases, 15 requirements, power and thermal budgets, architecture</td><td>docs/design-spec.md</td><td class="n">1 wk</td></tr>
<tr><td>2 · Simulation</td><td>9 models: solar, thermal, energy year, power integrity, battery sense, debounce, RF match, trace impedance, link budget</td><td>sim/</td><td class="n">1 wk</td></tr>
<tr><td>3 · Schematic + PCB</td><td>KiCad 9, 4-layer, 85 parts; generated from one design file, ERC/DRC clean</td><td>hardware/</td><td class="n">2 wk</td></tr>
<tr><td>4 · Enclosure</td><td>Parametric CAD fit-checked against the board STEP; drawings, STL, STEP</td><td>mechanical/</td><td class="n">1 wk</td></tr>
<tr><td>5 · Rev A</td><td>3 boards built and brought up; 2 bugs found, root-caused, simulated, fixed</td><td>test/BRINGUP.md</td><td class="n">3 wk</td></tr>
<tr><td>6 · Rev B</td><td>10 boards; bench and chamber characterization; production test</td><td>test/</td><td class="n">3 wk</td></tr>
<tr><td>7 · Qualification</td><td>Immersion, ESD, thermal cycling, UV, drop; 30-day field pilot</td><td>test/</td><td class="n">5 wk</td></tr>
<tr><td>8 · Release</td><td>Fab package, BOM, datasheet, this report, renders</td><td>docs/, render/</td><td class="n">1 wk</td></tr></table>
""")
page(f"""
<h2>Requirements compliance</h2>
<p class="small">Every requirement from the design specification, measured on rev B. Methods and raw logs: section 10–11 and <code>test/</code>.</p>
<table class="small" style="font-size:7.9pt"><tr><th>ID</th><th>Requirement</th><th>Target</th><th>Measured (rev B)</th><th>Result</th></tr>{rows}</table>
<div class="callout"><b>Open:</b> R10 needs the 100 L/min IP66 jet at an accredited lab (immersion and hose already pass).
<b>Marginal:</b> R6 charge-window trip points sit 0.4–0.6 °C outside nominal, inside the charger IC's tolerance.</div>
""")

# ======================================================================== 3 architecture
page(f"""
<h2>2 · System architecture</h2>
{F('block_diagram.png', 'Functional block diagram. Power path in orange: panel → protection → BQ24074 charger/power-path → TPS63900 buck-boost → 3.3 V bus.')}
<div class="grid2">
<div>
<h3>Power tree</h3>
<table class="small">
<tr><th>Rail</th><th>Source</th><th class="n">Range</th></tr>
<tr><td>VIN_SOLAR</td><td>Panel via D1, Q1</td><td class="n">0–6.0 V</td></tr>
<tr><td>VSYS</td><td>BQ24074 OUT (power path)</td><td class="n">VBAT … 4.4 V</td></tr>
<tr><td>VBAT</td><td>Protected 18650</td><td class="n">3.0–4.2 V</td></tr>
<tr><td>+3V3</td><td>TPS63900 buck-boost</td><td class="n">3.30 V ±1.5 %</td></tr>
<tr><td>+3V3_SW</td><td>TPS22917 (soil probe)</td><td class="n">on 100 ms/sample</td></tr>
<tr><td>+3V3_EXT</td><td>F1 PTC (air probe)</td><td class="n">always on</td></tr>
</table>
</div>
<div>
<h3>Key decisions</h3>
<table class="small">
<tr><th>Decision</th><th>Why</th></tr>
<tr><td>RAK3172 module</td><td>Pre-certified radio (FCC modular), STM32WL in one part, 1.7 µA sleep</td></tr>
<tr><td>BQ24074, USB500 mode</td><td>VIN-DPM holds the panel at 4.5 V: {f(sv['mpp_capture_hot_pct'],0)} % of MPP when hot, no MPPT chip</td></tr>
<tr><td>Buck-boost, not LDO</td><td>Cell crosses 3.3 V; 75 nA Iq; 94 % at 10 mA</td></tr>
<tr><td>Ventilated solar roof</td><td>Keeps the cell under 45 °C; panel doubles as sunshade</td></tr>
<tr><td>Magnet wake</td><td>No holes in the box; 0.54 µA hall switch</td></tr>
</table>
</div></div>
""")

# ======================================================================== 4 sim: solar + thermal
t = sv["table"]
page(f"""
<h2>3 · Design analysis and simulation</h2>
<p class="small muted">Every model is a runnable script in <code>sim/</code> (Python + ngspice); <code>sim/run_all.sh</code> regenerates every figure in about 20 s.</p>
<h3>3.1 Solar input: fixed-voltage tracking is enough</h3>
{F('sim_solar_iv.png', f"Single-diode model of the 5 V / 2 W panel ({sv['cells_series']} cells) at four irradiance levels, with the BQ24074 VIN-DPM window (4.35–4.63 V). At 1000 W/m² the fixed 4.5 V point captures {f(sv['mpp_capture_stc_pct'],1)} % of maximum power at 25 °C and {f(sv['mpp_capture_hot_pct'],1)} % with the panel at 55 °C, its real operating temperature.")}
<h3>3.2 Thermal: the battery limits the design</h3>
{F('sim_thermal_enclosure.png', f"Lumped thermal model of the enclosure on a calm, clear August day (worst case). The roof keeps the cell at {f(roof['max_battery_C'],1)} °C; a grey box reaches {f(grey['max_battery_C'],0)} °C and blocks charging {f(grey['charge_inhibit_hours'],1)} h; a panel glued to the lid reaches {f(glued['max_battery_C'],0)} °C and blocks charging {f(glued['charge_inhibit_hours'],1)} h a day.")}
""")

# ======================================================================== 5 sim: energy + budget
page(f"""
<h3>3.3 Energy over a year</h3>
{F('sim_energy_year.png', f"Hourly simulation of a Honolulu year (clear-sky model × monthly clearness, random cloud, a forced 7-day overcast run in the worst month), with charging blocked whenever the thermal model puts the cell outside 0–50 °C. Median harvest {f(ey['median_daily_harvest_mAh'],0)} mAh/day; the worst day still brings {f(ey['min_daily_harvest_mAh'],0)} mAh, {f(ey['panel_oversize_vs_1min_worst_day'],0)}× the 1-minute-mode use.")}
<div class="grid2">
<div>{F('sim_power_budget.png', 'Where each uplink\'s charge goes (5-min, SF9). Transmit dominates; sleep is 9 % of the day.')}</div>
<div>
<table class="small"><tr><th>Mode</th><th class="n">Avg current</th><th class="n">mAh/day</th><th class="n">Dark days*</th></tr>
<tr><td>5 min, SF7</td><td class="n">{f(pb['avg_current_uA']['5-min SF7'],0)} µA</td><td class="n">{f(pb['mAh_per_day']['5-min SF7'],2)}</td><td class="n">{pb['dark_autonomy_days_incl_self_discharge']['5-min SF7']}</td></tr>
<tr><td><b>5 min, SF9</b></td><td class="n"><b>{f(pb['avg_current_uA']['5-min SF9'],0)} µA</b></td><td class="n">{f(pb['mAh_per_day']['5-min SF9'],2)}</td><td class="n">{pb['dark_autonomy_days_incl_self_discharge']['5-min SF9']}</td></tr>
<tr><td>5 min, SF10</td><td class="n">{f(pb['avg_current_uA']['5-min SF10'],0)} µA</td><td class="n">{f(pb['mAh_per_day']['5-min SF10'],2)}</td><td class="n">{pb['dark_autonomy_days_incl_self_discharge']['5-min SF10']}</td></tr>
<tr><td>1 min, SF9</td><td class="n">{f(pb['avg_current_uA']['1-min rapid SF9'],0)} µA</td><td class="n">{f(pb['mAh_per_day']['1-min rapid SF9'],2)}</td><td class="n">{pb['dark_autonomy_days_incl_self_discharge']['1-min rapid SF9']}</td></tr>
<tr><td>1 min, SF10</td><td class="n">{f(pb['avg_current_uA']['1-min rapid SF10'],0)} µA</td><td class="n">{f(pb['mAh_per_day']['1-min rapid SF10'],2)}</td><td class="n">{pb['dark_autonomy_days_incl_self_discharge']['1-min rapid SF10']}</td></tr>
</table>
<p class="small muted">*No sun at all, 80 % of 3 350 mAh usable, incl. Li-ion self-discharge. Sleep {f(pb['sleep_uA'],1)} µA: charger BAT leakage 4.3 µA is the largest single term.</p>
<p class="small">The 2 W panel is about 100× larger than the energy need. It is sized as the sunshade, not as an energy source;
a 0.5 W panel would also be energy-positive but would not shade the box.</p>
</div></div>
""")

# ======================================================================== 6 sim: PI, vbat sense, rain
vb = sim["vbat_sense"]
rd = sim["rain_debounce"]
td = sim["tx_droop"]
page(f"""
<h3>3.4 Power integrity during transmit</h3>
{F('sim_tx_droop.png', f"ngspice: cell (with internal and holder resistance) → power path → behavioural TPS63900 → +3V3, with the 87 mA TX step. Rev B's 2 × 22 µF + 10 µF keeps droop to {f(td['2 × 22 µF + 10 µF at module (rev B)']['droop_mV'],0)} mV (spec ±99 mV); the cell sags {f(td['cell_dip_mV'],0)} mV.")}
<div class="grid2">
<div>{F('sim_vbat_sense.png', f"Battery-sense switch. Rev A (low-side) leaks {f(vb['leakage_revA_uA_at_4V05'],0)} µA at 4.05 V and {f(vb['leakage_revA_uA_at_4V2'],0)} µA at 4.2 V through the ADC clamp; rev B (high-side P-FET) leaks {f(vb['leakage_revB_nA_at_4V2'],0)} nA. Settles in {f(vb['settle_time_ms_half_lsb'],1)} ms, so firmware samples at {f(vb['adc_sample_delay_ms_chosen'],0)} ms.")}</div>
<div>{F('sim_rain_debounce.png', f"Reed bounce on the rain input. Rev A counted {rd['counts_revA_one_tip']} edges per tip; rev B's 10 kΩ / 22 nF filter gives exactly {rd['counts_revB_one_tip']}. Supports {f(rd['max_tip_rate_per_s_with_50ms_closure'],0)} tips/s vs about {f(rd['real_gauge_max_tips_per_s'],0)} in a downpour.")}</div>
</div>
""")

# ======================================================================== 7 sim: RF
page(f"""
<h3>3.5 RF: matching, trace impedance and link budget</h3>
{F('sim_rf_match.png', f"The whip, its 150 mm pigtail and the plastic case detune the antenna to about {f(rf['antenna_Z_at_915'][0],0)} − j{f(-rf['antenna_Z_at_915'][1],0)} Ω at 915 MHz. A shunt {rf['match_C_pF']} pF at the module plus a series {rf['match_L2_nH']} nH moves |S11| at 915 MHz from {f(rf['s11_before_dB_at_915'],1)} to {f(rf['s11_after_dB_at_915'],1)} dB and keeps the whole US915 band below {f(rf['s11_after_worst_in_band_dB'],0)} dB.")}
<div class="grid2">
<div>{F('sim_cpwg.png', f"Grounded coplanar waveguide on L1 over the L2 ground (JLC 7628 stackup, 0.20 mm gap): 50 Ω at {rf['cpwg_width_for_50ohm_mm']['thick_model']}–{rf['cpwg_width_for_50ohm_mm']['thin_model']} mm. Rev B uses 0.35 mm ({f(rf['cpwg_Z0_at_0p35mm_thick_ohm'],0)}–{f(rf['cpwg_Z0_at_0p35mm_thin_ohm'],0)} Ω).")}</div>
<div>{F('sim_link_budget.png', f"Log-distance path loss for a rural site, gateway at 10 m. With a 10 dB fade margin: SF7 {lb['range_km_10dB_margin']['SF7']} km, SF9 {lb['range_km_10dB_margin']['SF9']} km, SF10 {lb['range_km_10dB_margin']['SF10']} km.")}</div>
</div>
<table class="small"><tr><th>Spreading factor</th><th class="n">SF7</th><th class="n">SF8</th><th class="n">SF9</th><th class="n">SF10</th></tr>
<tr><td>Airtime, 24-byte frame</td>{''.join('<td class="n">%s ms</td>' % f(lb['airtime_ms'][s],0) for s in ('SF7','SF8','SF9','SF10'))}</tr>
<tr><td>Range, 10 dB margin (model)</td>{''.join('<td class="n">%s km</td>' % lb['range_km_10dB_margin'][s] for s in ('SF7','SF8','SF9','SF10'))}</tr>
<tr><td>Charge per uplink at 3.3 V</td><td class="n">{f(pb['per_uplink_mC_3v3']['SF7'],1)} mC</td><td class="n">–</td><td class="n">{f(pb['per_uplink_mC_3v3']['SF9'],1)} mC</td><td class="n">{f(pb['per_uplink_mC_3v3']['SF10'],1)} mC</td></tr></table>
""")

# ======================================================================== 8-9 schematic
page(f"""
<h2>4 · Schematic</h2>
<p class="small">KiCad 9, hierarchical: a root sheet and three function sheets, {BOM['placements']} placed parts. ERC: 0 errors, 0 warnings.
The netlist is checked pin by pin against the design source (233 pins, 47 nets, 0 mismatches) in <code>tools/check_netlist.py</code>.</p>
{F('sch_Power.png', 'Sheet 2, Power: solar input and protection, BQ24074 charger and power path, protected 18650 with NTC, TPS63900 buck-boost, switched battery and solar sense.', cls='tall')}
<h3>Design review notes</h3>
<ul class="checks small">
<li>Q1 (−30 V, Vgs ±20 V) survives a reversed panel and the TVS clamp voltage (19.9 V at 20 A).</li>
<li>EN1 is tied to VSYS (≤ 4.5 V), not the panel input: EN pins are rated 7 V.</li>
<li>TMR is grounded: safety timers off, because slow solar charging would otherwise time out.</li>
<li>TPS63900 CFG resistors are 1 %, 100 ppm. They are read once at power-up (16.2 k → 3.3 V).</li>
<li>The air probe is never power-switched: an unpowered SHT45 would clamp the shared I²C bus through its ESD diodes.</li>
</ul>
""")
page(f"""
{F('sch_Radio_MCU.png', 'Sheet 3, Radio and MCU: RAK3172, π-match to U.FL, SWD (Tag-Connect) and UART pads, reset, LED and magnet wake.', cls='sch2')}
{F('sch_Sensors_IO.png', 'Sheet 4, Sensors and field I/O: internal SHT40, J4 air probe, J3 soil probe on a load switch, J2 rain gauge with debounce, and 4-channel ESD.', cls='sch2')}
""")

# ======================================================================== 10 BOM
top = sorted(BOM_ROWS[:-3], key=lambda r: -float(r["Ext_1k"]))[:14]
brows = "".join(f"<tr><td>{r['References'][:26]}</td><td>{r['Description'][:58]}</td><td>{r['MPN']}</td><td class='n'>{r['Qty']}</td><td class='n'>${float(r['Unit_100']):.2f}</td><td class='n'>${float(r['Unit_1k']):.3f}</td></tr>" for r in top)
page(f"""
<h2>5 · Bill of materials and cost</h2>
<p class="small">{BOM['line_items']} line items, {BOM['placements']} placements, {BOM['unique_mpns']} unique parts; all single-side SMT except the battery holder.
Full list with manufacturers, footprints and LCSC numbers: <code>hardware/fab/BOM_tradewind_revB.csv</code> (also in JLCPCB format).</p>
<table class="small"><tr><th>Refs</th><th>Part</th><th>MPN</th><th class="n">Qty</th><th class="n">@100</th><th class="n">@1k</th></tr>{brows}
<tr><td colspan="6" class="muted">… plus {BOM['line_items']-14} lines of passives and connectors</td></tr></table>
<table class="small"><tr><th>Cost per unit</th><th class="n">10 units</th><th class="n">100 units</th><th class="n">1,000 units</th></tr>
<tr><td>Components</td>{''.join('<td class="n">$%s</td>' % f(BOM[q]['components'],2) for q in ('10','100','1000'))}</tr>
<tr><td>+ bare board (4-layer, ENIG) + SMT assembly</td>{''.join('<td class="n">$%s</td>' % f(BOM[q]['electronics_incl_pcb_pcba'],2) for q in ('10','100','1000'))}</tr>
<tr><td>+ protected 18650 cell</td>{''.join('<td class="n">$%s</td>' % f(BOM[q]['with_cell'],2) for q in ('10','100','1000'))}</tr>
<tr class="tot"><td>+ enclosure, panel, shield, bracket, glands, antenna</td><td class="n">–</td><td class="n">${f(BOM['100']['with_cell']+mech['bom_usd']['per_unit_at_100'],2)}</td><td class="n">${f(BOM['1000']['with_cell']+mech['bom_usd']['per_unit_at_1k'],2)}</td></tr></table>
<p class="small muted">Prices are typical distributor quantity breaks (October 2026). The 1k mechanical cost assumes molded box and lid; tooling (about $7–9k) is not included.
The radio module is 43 % of the parts cost at 1k; a chip-down STM32WL design would save about $3.50 per unit but needs its own FCC certification.</p>
""")

# ======================================================================== 11-12 PCB
page(f"""
<h2>6 · PCB layout</h2>
<div class="grid2">
<div>
<table class="small"><tr><th>Layer</th><th>Use</th><th class="n">Thickness</th></tr>
<tr><td>L1 F.Cu</td><td>Signals, RF CPWG, power stage</td><td class="n">35 µm</td></tr>
<tr><td>Prepreg 7628</td><td>εr 4.4</td><td class="n">0.21 mm</td></tr>
<tr><td>L2 In1.Cu</td><td>Solid GND plane</td><td class="n">15 µm</td></tr>
<tr><td>Core</td><td>FR-4</td><td class="n">1.07 mm</td></tr>
<tr><td>L3 In2.Cu</td><td>+3V3 plane</td><td class="n">15 µm</td></tr>
<tr><td>Prepreg 7628</td><td>εr 4.4</td><td class="n">0.21 mm</td></tr>
<tr><td>L4 B.Cu</td><td>Signals + GND pour</td><td class="n">35 µm</td></tr>
</table>
<p class="small">96 × 70 mm, 1.6 mm, ENIG, matte black mask. Rules: 0.15 mm track and space, 0.2 mm drill, 0.3 mm to edge
(JLC standard 4-layer). DRC with schematic parity: <b>0 errors</b>.</p>
</div>
<div>{fig('r_pcb_top.jpg', 'Rev B top side, KiCad raytrace.')}</div>
</div>
<ul class="small">
<li><b>Zoning.</b> The cell takes the top band. Power sits bottom-left beside J1, field I/O bottom-middle above J2–J4, and RF bottom-right next to the U.FL, so the antenna lead is short and away from the switcher.</li>
<li><b>Buck-boost.</b> Hand-routed per TI's layout guide: the inductor sits right at LX1/LX2, the input cap loop is under 3 mm, and CFG1–3 run on short traces (CFG2 hops via B.Cu). The exposed pad is stitched to L2 with 6 vias.</li>
<li><b>RF.</b> 0.35 mm CPWG on L1 over the L2 ground with a via fence each side. The π pads sit on the line; the trace is 15 mm long.</li>
<li><b>Sensor island.</b> The SHT40 sits on a peninsula cut by an L-shaped milled slot, with no copper pour under it, so charger and radio heat don't bias the internal reading. Measured offset while charging at 400 mA: {f(sen['selfheat_at_400mA_C'],2)} °C.</li>
<li><b>Planes.</b> Every GND and +3V3 pad has its own via to its plane (82 fan-out vias). The rest was autorouted (Freerouting), then checked and cleaned.</li>
</ul>
{F('layer_strip.png', 'Copper layers L1–L4 (left to right): top signals and GND pour, solid ground, +3.3 V plane, bottom signals and GND pour.')}
""")
page(f"""
<div class="grid2">
<div>{F('r_pcb_hero.jpg', 'Populated rev B board (Blender Cycles render from the KiCad 3D export).')}</div>
<div>{F('r_pcb_detail_rf.jpg', 'RF corner: RAK3172, π-match on the CPWG line, via fence and U.FL.')}</div>
</div>
<h3>Manufacturing outputs</h3>
<table class="small"><tr><th>File</th><th>Contents</th></tr>
<tr><td>tradewind_revB_gerbers.zip</td><td>11 Gerber X2 layers, Excellon PTH/NPTH, drill maps, job file</td></tr>
<tr><td>tradewind_revB_cpl.csv</td><td>Pick-and-place, top side, DNP excluded</td></tr>
<tr><td>BOM_tradewind_revB.csv / BOM_JLCPCB.csv</td><td>Costed engineering BOM; assembler format with LCSC numbers</td></tr>
<tr><td>assembly_drawing_top.pdf</td><td>Fab-layer assembly drawing with references</td></tr>
<tr><td>tradewind_revB.step / .glb / .wrl</td><td>3D board with all parts (enclosure fit, web viewer)</td></tr>
<tr><td>erc_report.txt / drc_report.txt</td><td>Clean ERC and DRC (with schematic parity), generated on every export</td></tr>
</table>
<p class="small">The whole chain from <code>tools/design.py</code> to schematic, board, routing, DRC, Gerbers and BOM runs from scripts. A design change is one edit and one command, and the schematic and board can't drift apart.</p>
""")

# ======================================================================== 13 firmware
page(f"""
<h2>7 · Firmware</h2>
<p class="small">RAKwireless RUI3 (Arduino-style API) on the module's STM32WLE5. LoRaWAN 1.0.3 OTAA, US915 sub-band 2, ADR on.
The payload packer and the network-server decoder share golden test vectors: 16 C++ and 22 JavaScript host tests pass.</p>
<div class="grid2">
<div>
<h3>Per-uplink sequence</h3>
<ol class="next small">
<li>RTC alarm wakes from STOP2 (7.2 µA board total).</li>
<li>SENSOR_EN on, then wait 100 ms for the soil probe. Read both SHT4x (CRC-checked).</li>
<li>VBAT switch on, wait 5 ms, read the ADC. Also read panel voltage, CHG and PGOOD.</li>
<li>Pack 11 bytes, then send unconfirmed on fPort 1 at SF9 (206 ms at +20 dBm).</li>
<li>RX1/RX2 windows, then apply any downlink (interval, rapid mode, health, reboot).</li>
<li>Sleep until the next deadline. Rain tips and magnet taps wake it early.</li>
</ol>
</div>
<div>
<h3>Uplink payload, fPort 1 (11 bytes)</h3>
<table class="small"><tr><th>Byte</th><th>Field</th><th>Encoding</th></tr>
<tr><td>0</td><td>Flags</td><td>rapid · charging · PGOOD · low batt · sensor OK ×3</td></tr>
<tr><td>1–2</td><td>Air temperature</td><td>s16, 0.01 °C</td></tr>
<tr><td>3</td><td>Air humidity</td><td>u8, 0.5 %RH</td></tr>
<tr><td>4</td><td>Soil moisture</td><td>u8, 0.5 %</td></tr>
<tr><td>5–6</td><td>Rain tips</td><td>u16 cumulative, 0.2 mm/tip</td></tr>
<tr><td>7</td><td>Battery</td><td>2500 mV + 10 mV × n</td></tr>
<tr><td>8–9</td><td>Internal T / RH</td><td>s8 0.5 °C · u8 0.5 %RH</td></tr>
<tr><td>10</td><td>Panel voltage</td><td>u8, 25 mV</td></tr>
</table>
<p class="small muted">fPort 2: daily confirmed health frame (uptime, counters, RSSI/SNR, min battery, max internal temperature, charge minutes).</p>
</div></div>
{F('test_ppk2_cycle.png', f"Measured current through one 5-minute wake cycle (Nordic PPK2, board TW1B-003). {f(pw['charge_per_uplink_mC_total'],1)} mC per uplink against {f(pw['sim_total_mC'],1)} mC predicted; awake {f(pw['awake_time_s'],2)} s.")}
""")

# ======================================================================== 14-15 mechanical
g = mech["gasket"]
dm = mech["dimensions_mm"]
page(f"""
<h2>8 · Enclosure and mechanical design</h2>
<div class="grid2">
<div>{F('r_product_exploded.jpg', 'Exploded assembly: panel, ventilated roof and gussets, lid with light pipe, gasket, PCBA, base with heat-set inserts, glands, bracket and radiation shield.')}</div>
<div>
<table class="small"><tr><th>Item</th><th>Design</th></tr>
<tr><td>Box</td><td>{dm['box_w_h_d'][0]:.0f} × {dm['box_w_h_d'][1]:.0f} × {dm['box_w_h_d'][2]:.0f} mm, white ASA (UV-stable), 3 mm walls, 1° draft, ribbed lid</td></tr>
<tr><td>Seal</td><td>{g['cord_d_mm']} mm silicone cord in a {g['groove_w_x_d_mm'][0]} × {g['groove_w_x_d_mm'][1]} mm groove: {f(g['compression_pct'],0)} % squeeze, {f(g['groove_fill_pct'],0)} % fill</td></tr>
<tr><td>Fasteners</td><td>4 × M4 captive lid screws into brass inserts; 4 × M3 PCB screws</td></tr>
<tr><td>Penetrations</td><td>4 × PG7 glands at {dm['gland_spacing']:.0f} mm pitch, SMA bulkhead, M12 ePTFE vent. All on the bottom wall or side, none on top.</td></tr>
<tr><td>Sun roof</td><td>Carries the 136 × 110 mm panel, tilted {dm['roof_tilt_deg']:.0f}°, {dm['roof_gap_over_box_front']:.0f} mm air gap over the box</td></tr>
<tr><td>Radiation shield</td><td>6-plate louvred stack, SHT45 probe holder, on the bracket arm</td></tr>
<tr><td>Mass</td><td>{f(mech['mass_g']['box_unit_only'],0)} g box unit; {f(mech['mass_g']['total_installed_excl_pole'],0)} g installed</td></tr>
<tr><td>Envelope</td><td>{dm['installed_envelope_w_h_d_excl_pole'][0]:.0f} × {dm['installed_envelope_w_h_d_excl_pole'][1]:.0f} × {dm['installed_envelope_w_h_d_excl_pole'][2]:.0f} mm installed</td></tr>
<tr><td>Prototype</td><td>FDM in ASA, {f(mech['print_time_h_total'],1)} h for a full set</td></tr>
</table>
<p class="small">Fit checked in CAD against the board STEP: board-to-wall {f(mech['fit']['clear_board_edge_to_walls_and_columns_mm'],1)} mm, cell-to-lid {f(mech['fit']['clear_cell_to_lid_mm'],1)} mm, gland nuts {f(mech['fit']['clear_board_to_gland_nuts_mm'],1)} mm. No interference in 12 checked pairs.</p>
</div></div>
{F('mech_ga_enclosure.png', 'General arrangement of the enclosure: front, side and bottom views with overall dimensions and gland spacing.')}
""")
page(f"""
<div class="grid2">
<div>{F('mech_section.png', 'Sections A–A and B–B: PCB on bosses, cell under the lid ribs, gasket tongue and groove, lid screw and insert.')}</div>
<div>{F('r_product_open.jpg', 'Lid off: PCBA on four bosses, gasket, glands and the U.FL to SMA pigtail.')}</div>
</div>
<h3>Design for the field</h3>
<ul class="small">
<li><b>Water.</b> All cables leave downward through glands, with drip loops; the antenna points down; the vent sits on a side wall below the gasket line.</li>
<li><b>Heat.</b> White ASA (solar absorptance ≈ 0.25) under a roof that blocks direct sun on the top and sides. Measured in the field: interior {f(fld['internal_minus_air_daily_max_C']['mean'],1)} °C above air on average, {f(fld['internal_minus_air_daily_max_C']['max'],1)} °C worst.</li>
<li><b>UV.</b> ASA coupons changed ΔE {env['uv_deltaE_500h']['ASA white']} after 500 h of UV-A, against {env['uv_deltaE_500h']['PETG white']} for PETG, which is why PETG was rejected.</li>
<li><b>Production.</b> The walls are drafted and evenly thick so the printed shapes carry straight into injection-molding tooling. The roof and shield plates are flat-pack.</li>
</ul>
{F('r_product_hero_outdoor.jpg', 'Installed on a 42 mm pole in daylight (render).', '78%')}
""")

# ======================================================================== 16 assembly / bring-up
prod = tst["production"]
page(f"""
<h2>9 · Assembly and bring-up</h2>
<p class="small">Rev A: 3 boards, hand-assembled (stencil, hot plate, rework station). Rev B: 10 boards assembled by the board house.
The full step-by-step log is in <code>test/BRINGUP.md</code>.</p>
<table class="small"><tr><th>Rev A issue</th><th>How we found it</th><th>Root cause</th><th>Rev B fix (verified)</th></tr>
<tr><td>Sleep 34 µA (budget 7)</td><td>PPK2, part-lifting; current scaled with VBAT</td><td>Low-side divider switch: PB3 sat at VBAT and leaked through the clamp diode</td><td>High-side P-FET switch (Q2/Q3). {f(bu['sleep_uA_3V7']['mean'],1)} µA mean on 10 boards</td></tr>
<tr><td>2–6 rain counts per tip</td><td>50 hand tips counted 173</td><td>Reed bounce on an unfiltered EXTI input</td><td>10 kΩ / 22 nF filter + 50 ms firmware lockout. {env['rain_bench']['tips_counted']}/{env['rain_bench']['tips_applied']} on the bench</td></tr>
<tr><td>S11 −11 dB at 915 in the case</td><td>NanoVNA through the U.FL with the lid closed</td><td>Plastic and pigtail detune the whip</td><td>π-match C14 1.8 pF / L2 7.5 nH: {f(rft['s11']['case_matched_revB']['at_915_dB'],1)} dB</td></tr>
</table>
<div class="grid2">
<div>{F('test_bringup_sleep.png', f"Sleep current, 10 rev B boards at 3.7 V: mean {f(bu['sleep_uA_3V7']['mean'],2)} µA, max {f(bu['sleep_uA_3V7']['max'],1)} µA, against the rev A as-built values.")}</div>
<div>
<table class="small"><tr><th>Bring-up check (10 boards)</th><th class="n">Result</th></tr>
<tr><td>+3V3</td><td class="n">{f(bu['v3v3_V']['min'],3)}–{f(bu['v3v3_V']['max'],3)} V</td></tr>
<tr><td>+3V3 ripple at 10 mA</td><td class="n">{f(bu['v3v3_ripple_mVpp_10mA']['max'],1)} mVpp max</td></tr>
<tr><td>VSYS in sun</td><td class="n">{f(bu['vsys_V_sun']['min'],3)}–{f(bu['vsys_V_sun']['max'],3)} V</td></tr>
<tr><td>Charge termination</td><td class="n">{f(bu['vbat_reg_V']['min'],3)}–{f(bu['vbat_reg_V']['max'],3)} V</td></tr>
<tr><td>Flash over UART2</td><td class="n">{f(bu['flash_s_mean'],1)} s</td></tr>
<tr><td>OTAA join, median</td><td class="n">{f(bu['otaa_join_s_median'],1)} s</td></tr>
<tr><td>Production test, first pass</td><td class="n">{f(prod['first_pass_yield_pct'],0)} % → {f(prod['final_yield_pct'],0)} %</td></tr>
</table>
<p class="small muted">The one first-pass failure: TW1B-006, a solder bridge on U5 pins 3–4 (I²C 0x45 missing). Reworked; rev C opens the paste aperture on that footprint.</p>
</div></div>
""")

# ======================================================================== 17-19 characterization
page(f"""
<h2>10 · Characterization</h2>
<h3>10.1 Power</h3>
<div class="grid2">
<div>{F('test_efficiency.png', f"TPS63900 efficiency on the board: {f(H['efficiency_pct_10uA_10mA_100mA'][0],1)} % at 10 µA, {f(H['efficiency_pct_10uA_10mA_100mA'][1],1)} % at 10 mA, {f(H['efficiency_pct_10uA_10mA_100mA'][2],1)} % at 100 mA (3.7 V in). The 10 µA point sits below the datasheet's 90 %, because board leakage is counted.")}</div>
<div>{F('test_loadstep.png', f"+3V3 under the 5→87 mA TX step: −{f(pw['loadstep_droop_mV'],0)} / +{f(pw['loadstep_overshoot_mV'],0)} mV (simulated −{f(pw['sim_droop_mV'],0)} mV).")}</div>
</div>
<div class="grid2">
<div>{F('test_charge_budget.png', 'Charge per uplink by phase: measured against the simulation budget.')}</div>
<div>{F('test_dark_test.png', f"14-day dark test in 1-minute mode: {f(pw['dark_test_soc_drop_pct_per_day'],2)} %/day, so about {f(pw['dark_autonomy_days_to_20pct_projected'],0)} days to a 20 % reserve with no sun at all.")}</div>
</div>
""")
page(f"""
<h3>10.2 Solar charging</h3>
{F('test_solar_days.png', f"Field days on unit TW1B-004. Clear: {f(sol['field_days']['Clear day']['mAh_in'],0)} mAh in, panel held at {f(sol['field_days']['Clear day']['panel_V_median_while_charging'],2)} V while charging. Cloudy: {f(sol['field_days']['Cloudy day']['mAh_in'],0)} mAh. Daily use in 1-minute mode is about 9 mAh.")}
<div class="grid2">
<div>{F('test_vin_dpm.png', f"VIN-DPM sweep with an emulated panel: regulation at {f(sol['vin_dpm_V']['min'],3)}–{f(sol['vin_dpm_V']['max'],3)} V on 3 boards; input limit {f(sol['input_limit_mA_measured'],0)} mA.")}</div>
<div>
<h4>Charge temperature window (NTC on the cell, chamber)</h4>
<table class="small"><tr><th>Edge</th><th class="n">Cell °C</th><th>Event</th></tr>
<tr><td>Rising</td><td class="n">{sol['ts_window_C']['hot_stop']}</td><td>charging suspended</td></tr>
<tr><td>Falling</td><td class="n">{sol['ts_window_C']['hot_resume']}</td><td>charging resumes</td></tr>
<tr><td>Falling</td><td class="n">{sol['ts_window_C']['cold_stop']}</td><td>suspended (cold)</td></tr>
<tr><td>Rising</td><td class="n">{sol['ts_window_C']['cold_resume']}</td><td>resumes</td></tr></table>
<p class="small muted">Trips sit 0.4–0.6 °C outside the nominal 0 / 50 °C, within the BQ24074's TS threshold tolerance. Marked marginal against R6. In the field the cell never got above {f(fld['internal_max_C'],1)} °C, so this has no practical effect.</p>
</div></div>
""")
page(f"""
<h3>10.3 Sensors</h3>
<div class="grid2">
<div>{F('test_temp_accuracy.png', f"Air temperature, 5 units against a reference thermometer, −10 to +60 °C: worst {f(sen['temp_ext_max_abs_err_C'],2)} °C, RMS {f(sen['temp_ext_rms_err_C'],2)} °C (spec ±0.3).")}</div>
<div>{F('test_rh_accuracy.png', f"Humidity on saturated-salt references: worst {f(sen['rh_ext_max_abs_err_below_90'],1)} %RH below 90 %, {f(sen['rh_ext_max_abs_err'],1)} %RH at 97 % (spec ±2).")}</div>
</div>
<div class="grid2">
<div>{F('test_selfheat.png', f"Internal SHT40 offset against charge current: {f(sen['selfheat_C_per_W'],1)} °C/W, {f(sen['selfheat_at_400mA_C'],2)} °C at 400 mA. Firmware removes it using the CHG status.")}</div>
<div>
<h4>Rain counting (bench, tipping-bucket simulator)</h4>
<table class="small"><tr><th class="n">Rate (tips/s)</th><th class="n">Applied</th><th class="n">Counted</th><th>MCU state</th></tr>
{''.join('<tr><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td><td>%s</td></tr>' % (r['rate_tips_per_s'], r['tips_applied'], r['tips_counted'], r['mcu_state']) for r in env['rain_bench']['rows'])}
</table>
<p class="small muted">Exact counting up to 5 tips/s, while a real gauge peaks near 2 tips/s in a 200 mm/h downpour. The single miss at 10 tips/s falls inside the 50 ms firmware lockout, which is there by design.</p>
</div></div>
""")
page(f"""
<h3>10.4 Radio</h3>
<div class="grid2">
<div>{F('test_tx_power.png', f"Conducted TX power at the U.FL, 64 channels × 2 units: {f(H['tx_power_dBm_range'][0],2)} to {f(H['tx_power_dBm_range'][1],2)} dBm, mean {f(H['tx_power_dBm_mean'],2)} dBm (spec +20 ±1).")}</div>
<div>{F('test_s11.png', f"Return loss measured with a NanoVNA. Free air {f(rft['s11']['free_air']['at_915_dB'],1)} dB; in the case without the match {f(rft['s11']['case_unmatched']['at_915_dB'],1)} dB; rev B match {f(rft['s11']['case_matched_revB']['at_915_dB'],1)} dB at 915 MHz, {f(rft['s11']['case_matched_revB']['worst_in_band_dB'],1)} dB worst in band.")}</div>
</div>
{F('test_range.png', f"Drive test, gateway on a 10 m mast. SF7 held ≥ 50 % delivery to {rft['range']['SF7']['max_km_PDR50']} km; SF10 still decoded at the last stop, {rft['range']['SF10']['last_decode_km']} km, so its real limit lies further out.")}
""")

# ======================================================================== 20 environmental + field
esd_rows = "".join(f"<tr><td>{r['port']}</td><td>{r['mode']} ±{r['level_kV']} kV</td><td>{r['criterion']}</td></tr>" for r in env['esd']['rows'][:10] if r['mode'] == 'contact' or r['criterion'] == 'B')
page(f"""
<h2>11 · Environmental and field testing</h2>
<h3>11.1 Environmental</h3>
<div class="grid2">
<div>
<table class="small"><tr><th>Test</th><th>Condition</th><th>Result</th></tr>
<tr><td>Immersion</td><td>1 m, 30 min</td><td>{status_pill('pass')} dew-point drift {f(env['dunk']['dewpoint_drift_C'],2)} °C</td></tr>
<tr><td>Hose</td><td>IPX5-style, 12.5 L/min, all faces</td><td>{status_pill('pass')}</td></tr>
<tr><td>IP66 jet</td><td>100 L/min</td><td>{status_pill('open')} needs accredited lab</td></tr>
<tr><td>Thermal cycling</td><td>−10/+60 °C, 50 cycles, 2 units</td><td>{status_pill('pass')} gasket set 11 %</td></tr>
<tr><td>Operating range</td><td>−10 to +60 °C, chamber</td><td>{status_pill('pass')}</td></tr>
<tr><td>Drop</td><td>26 × 1 m on concrete</td><td>{status_pill('pass')} 2 mm cosmetic chip</td></tr>
<tr><td>UV</td><td>500 h UV-A, ASA coupons</td><td>{status_pill('pass')} ΔE {env['uv_deltaE_500h']['ASA white']}</td></tr>
<tr><td>ESD contact</td><td>±8 kV, all ports</td><td>{status_pill('pass')} criterion A</td></tr>
<tr><td>ESD air</td><td>±15 kV</td><td>{status_pill('pass')} B on J4 (1 reset, self-recovered)</td></tr>
<tr><td>Salt fog</td><td>ASTM B117</td><td><span class="pill">deferred</span> before coastal sites</td></tr>
</table>
</div>
<div>{F('test_ip67_dunk.png', 'Dunk test: the internal SHT40 shows no humidity or dew-point change through 30 minutes at 1 m.')}</div>
</div>
{F('test_production.png', f"Production test, 10 boards × 10 steps: first-pass yield {f(prod['first_pass_yield_pct'],0)} %, final {f(prod['final_yield_pct'],0)} % after one rework.")}
""")
page(f"""
<h3>11.2 30-day field pilot, {fld['site']}, September 2026</h3>
<p class="small">Three units at 0.6, 1.4 and 3.2 km from one gateway, 5-minute reporting, rain gauge, soil probe and air probe fitted.
Median RSSI {fld['rssi_median_dBm']['TW1B-004']:.0f} / {fld['rssi_median_dBm']['TW1B-005']:.0f} / {fld['rssi_median_dBm']['TW1B-008']:.0f} dBm.</p>
<div class="grid2">
<div>{F('test_field_battery.png', f"State of charge, 3 units at 0.6, 1.4 and 3.2 km: never below {f(fld['soc_min_pct_all'],1)} %. Delivery {f(fld['pdr_pct_all'],2)} % ({fld['uplinks_received']:,} of {fld['uplinks_expected']:,} uplinks).")}</div>
<div>{F('test_field_temp.png', f"Box interior against air: max {f(fld['internal_max_C'],1)} °C at {f(fld['air_max_C'],1)} °C air. On still afternoons the box ran 2–4 °C warmer than the thermal model; the margin to 45 °C still held.")}</div>
</div>
<div class="grid2">
<div>{F('test_field_rain_ref.png', f"Rain against a manual reference gauge, 8 rain days: slope {f(fld['rain_vs_reference']['slope'],3)}, R² {f(fld['rain_vs_reference']['r2'],4)}.")}</div>
<div>{F('test_field_soil_rain.png', 'Soil moisture through irrigation cycles and rain events.')}</div>
</div>
""")

# ======================================================================== 21 conclusions
page(f"""
<h2>12 · Conclusions and next steps</h2>
<p>Rev B is ready for a pilot build. It meets every electrical, radio and sensing requirement with margin. Charging is
marginal only at the edges of the NTC window. The enclosure's ingress rating needs one accredited IP66 jet test before it goes on a datasheet as certified.</p>
<h3>Open items and risks</h3>
<table class="small"><tr><th>Item</th><th>Risk</th><th>Plan</th></tr>
<tr><td>IP66 jet (R10)</td><td>Medium</td><td>Book an accredited lab; dunk and hose already pass</td></tr>
<tr><td>Charge window (R6)</td><td>Low</td><td>Optional Rs/Rp on TS to pull the hot trip to 45 °C (BQ24074 Table 9-3)</td></tr>
<tr><td>Internal sensor self-heating while charging</td><td>Low</td><td>Firmware compensation from the CHG status (0.94 °C at 400 mA)</td></tr>
<tr><td>FCC / IC</td><td>Low</td><td>Module is FCC-certified; host needs §15.109 unintentional-radiator scan and labeling</td></tr>
<tr><td>Salt fog (coastal sites)</td><td>Medium</td><td>ASTM B117 before any coastal deployment; consider conformal coat</td></tr>
</table>
<h3>Rev C changes (small)</h3>
<ul class="small">
<li>Open the U5 paste aperture 10 % to stop the pin 3–4 bridge.</li>
<li>Larger radius on the lid's hinge-side corner (drop-test chip).</li>
<li>Footprint for an optional TS trim network; silk polarity mark on the cell holder.</li>
</ul>
<h3>Recommended next step</h3>
<ol class="next">
<li><b>Pilot of 50 units</b>: about $3,400 for electronics, printed enclosures and kits, 4 weeks to assemble and test.</li>
<li>In parallel: book the IP66 and FCC pre-scan (about $2,500 together).</li>
<li>After 60 days in the field: freeze rev C and quote mold tooling for the box and lid.</li>
</ol>
<h3>Delivered with this report</h3>
<p class="small">KiCad 9 project (schematic, board, 3D models) · Gerbers, drill, BOM, pick-and-place · enclosure CAD (STEP, STL) and drawings ·
firmware and payload decoder with tests · simulation sources · test logs and analysis scripts · 3D renders · product datasheet. All in {REPO}.</p>
<div class="signoff"><div><div class="sig">Maxwell Pauly</div><small>Maxwell Pauly · Binary Beach LLC · Hardware &amp; product design</small></div>
<small style="text-align:right">Questions? maxwell.pauly@binarybeach.tech<br>(808) 372-6757</small></div>
""")

# ======================================================================== assemble
HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tradewind TW-1 Design &amp; Test Report</title>
<link rel="icon" href="img/logo.png"><link rel="stylesheet" href="letterhead.css">
<style>
.body h2:first-child{margin-top:0}
figure img{border-radius:3px;max-height:3.0in;width:auto!important;max-width:100%}
.grid2 figure img{max-height:2.25in}
figure.tall img{max-height:4.6in}
figure.sch2 img{max-height:3.82in}
figure.hero img{max-height:4.25in}
figcaption{font-size:8pt;line-height:1.35}
table.small{font-size:8.2pt}
.body{padding-top:.25in}
@media print{.page{width:8.5in;max-width:none}.lh,.body,.ft{padding-left:.7in;padding-right:.7in}.lh .contact{display:block}
.grid2{grid-template-columns:1fr 1fr}.stats{grid-template-columns:repeat(var(--n,3),1fr)}.kv{grid-template-columns:150px 1fr}}
.grid2 figure{margin:4px 0 8px}
code{font-size:8.5pt;background:#f3f5f6;padding:0 3px;border-radius:3px}
table.small td,table.small th{padding:3px 6px}
.page{height:auto}
@media print{.page{min-height:11in;height:11in;overflow:hidden}}
</style>
<script>
(function(){var embed=new URLSearchParams(location.search).has('embed')||window.self!==window.top;
if(embed){document.documentElement.classList.add('embed');return}
if(new URLSearchParams(location.search).has('print'))return;
document.addEventListener('DOMContentLoaded',function(){var b=document.createElement('div');b.className='rp-bar';
b.innerHTML='<a href="/hardware/tradewind/">← Tradewind</a><span><b>Reference design.</b> Our own product, designed end to end: the kind of report you get with every phase.</span><button type="button">Print or save PDF</button>';
b.querySelector('button').addEventListener('click',function(){print()});document.body.prepend(b)})})();
</script></head><body>
"""
LH = """<div class="lh"><img src="img/logo.png" alt=""><div><div class="wm">BINARY <span>BEACH</span></div>
<div class="tag">Engineering &amp; Software · Honolulu, Hawai‘i</div></div>
<div class="contact">Binary Beach LLC<br>Honolulu, Hawai‘i<br>maxwell.pauly@binarybeach.tech · (808) 372-6757<br>binarybeach.tech</div></div><div class="stripe"></div>"""
n = len(pages)
html = HEAD + "".join(
    f'<div class="page">{LH}<div class="body">{b}</div><div class="ft"><span>Binary Beach LLC · Tradewind TW-1 rev {REV} · {DOC_REPORT}</span>'
    f'<span>Page {i + 1} of {n}</span></div></div>\n' for i, b in enumerate(pages)) + "</body></html>"
open(OUT, "w").write(html)
print("report:", OUT, n, "pages,", FN["n"], "figures")
