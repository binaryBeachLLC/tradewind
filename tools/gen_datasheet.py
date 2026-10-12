"""Generate docs/datasheet/index.html — Tradewind TW-1 product datasheet in the Binary Beach datasheet format
(docs/datasheet/datasheet.css). Numbers come from the result files via tools/docdata.py.
"""
import os

from docdata import SIM, TEST, MECH, BOM, H, DOC_DS, REPO, f

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "datasheet", "index.html")
pages = []
FIGN = {}


def page(body):
    pages.append(body)


def fig(src, cap, sec, h=None, cond=""):
    FIGN[sec] = FIGN.get(sec, 0) + 1
    st = ' style="max-height:%s"' % h if h else ""
    c = '<div class="fig-cond">%s</div>' % cond if cond else ""
    return ('<figure class="ds"><img src="img/%s"%s alt=""><figcaption><span class="fn">Figure %s-%d.</span> %s</figcaption></figure>%s'
            % (src, st, sec, FIGN[sec], cap, c))


TN = {}


def cap(sec, text):
    TN[sec] = TN.get(sec, 0) + 1
    return '<caption>Table %s-%d. %s</caption>' % (sec, TN[sec], text)


bu, pw, sol, sen, rft, env, fld = (TEST[k] for k in ("bringup", "power", "solar", "sensors", "rf", "environmental", "field"))
pb, lb, rf, sv, ey, th = (SIM[k] for k in ("power_budget", "link_budget", "rf_match", "solar_iv", "energy_year", "thermal_enclosure"))
dm = MECH["dimensions_mm"]


def row(param, cond, mn, typ, mx, unit, sym=""):
    return (f'<tr><td class="p">{param}</td><td>{cond}</td><td class="num">{mn}</td><td class="num">{typ}</td>'
            f'<td class="num">{mx}</td><td class="u">{unit}</td></tr>')


def sect(name, cols=6):
    return f'<tr class="sect"><td colspan="{cols}">{name}</td></tr>'


EC_HEAD = '<tr><th>Parameter</th><th>Test conditions</th><th class="num">Min</th><th class="num">Typ</th><th class="num">Max</th><th>Unit</th></tr>'

# ============================================================================ page 1
page(f"""
<div class="ds-title">TW-1 Solar-Powered LoRaWAN<sup style="font-size:9pt">®</sup> Field Sensor with Air, Soil and Rain Inputs</div>
<div class="ds-cols one-two">
<div>
<h2 class="ds"><span class="n">1</span>Features</h2>
<ul class="ds">
<li><b>Maintenance-free solar power</b>
  <ul><li>2 W panel on a ventilated sun roof</li><li>Protected 18650 Li-ion, 3 350 mAh</li>
  <li>{f(H['dark_autonomy_days_1min'],0)} days with no sun (1-min reporting)</li></ul></li>
<li><b>Ultra-low power</b>
  <ul><li>{f(bu['sleep_uA_3V7']['mean'],1)} µA sleep, whole system (typ)</li>
  <li>{f(H['avg_current_uA_5min_SF9'],0)} µA average at 5-min / SF9</li></ul></li>
<li><b>LoRaWAN 1.0.3 Class A</b>, US915 sub-band 2
  <ul><li>+20 dBm conducted, tuned π-match</li><li>{f(H['range_km_last_decode']['SF10'],1)} km line of sight at SF10 (tested)</li></ul></li>
<li><b>Sensors</b>
  <ul><li>Air temperature ±{f(H['temp_err_max_C'],1)} °C, humidity ±{f(sen['rh_ext_max_abs_err_below_90'],0)} %RH</li>
  <li>Capacitive soil moisture, 0.2 mm tipping-bucket rain</li>
  <li>Internal T/RH for leak and condensation alerts</li></ul></li>
<li><b>Built for sun and rain</b>
  <ul><li>Cell ≤ {f(fld['internal_max_C'],0)} °C in Hawaiʻi sun (measured)</li><li>1 m / 30 min immersion; UV-stable ASA</li>
  <li>±8 kV contact ESD on every field port</li></ul></li>
<li>Sealed, magnet-tap wake; open KiCad, firmware and CAD</li>
</ul>
<h2 class="ds"><span class="n">2</span>Applications</h2>
<ul class="ds">
<li>Irrigation scheduling and soil-moisture networks</li>
<li>Frost and heat alerts for nurseries and orchards</li>
<li>Rainfall networks and watershed monitoring</li>
<li>Remote-site and shade-house environment logging</li>
</ul>
</div>
<div>
<h2 class="ds"><span class="n">3</span>Description</h2>
<p>The TW-1 is a complete, pole-mounted field sensor. It measures air temperature and humidity inside a louvred radiation shield,
soil moisture and rainfall, and its own battery, solar and enclosure health. It reports over LoRaWAN every 5 minutes, or every minute
in rapid mode, to any LoRaWAN 1.0.3 network server.</p>
<p>A linear charger with input-voltage regulation holds the 5 V panel near its maximum power point without an MPPT controller.
A 75 nA buck-boost converter supplies the 3.3 V bus across the full Li-ion range. The panel mounts on a roof 25 mm above the
white ASA enclosure and shades it, so the cell stays well inside its charging temperature range in tropical sun.</p>
<div class="ds-info"><table class="ds compact">{cap('3', 'Device Information')}
<tr><th>Part number</th><th>Enclosure</th><th>Body size (nom)</th></tr>
<tr><td>TW-1-US915</td><td>Pole-mount, IP67-tested</td><td>{dm['box_w_h_d'][0]:.0f} × {dm['box_w_h_d'][1]:.0f} × {dm['box_w_h_d'][2]:.0f} mm</td></tr>
<tr><td>TW-1-US915-PCBA</td><td>Board only</td><td>96 × 70 × 23 mm</td></tr></table></div>
<figure class="ds" style="margin-top:.06in"><img src="img/r_product_hero.jpg" style="max-height:1.85in" alt="">
<figcaption>TW-1 installed (sun roof, enclosure, radiation shield)</figcaption></figure>
</div></div>
{fig('block_diagram.png', 'Simplified Block Diagram', '3', h='2.6in')}
""")

# ============================================================================ page 2: TOC, revision, comparison
toc = [("1", "Features", 1), ("2", "Applications", 1), ("3", "Description", 1), ("4", "Device Comparison", 2),
       ("5", "Connector Configuration and Functions", 3), ("6", "Specifications", 4), ("6.1", "Absolute Maximum Ratings", 4),
       ("6.2", "ESD Ratings", 4), ("6.3", "Recommended Operating Conditions", 4), ("6.4", "Environmental and Mechanical", 4),
       ("6.5", "Electrical Characteristics", 5), ("6.6", "Typical Characteristics", 7), ("7", "Detailed Description", 9),
       ("7.1", "Overview", 9), ("7.2", "Functional Block Diagram", 9), ("7.3", "Feature Description", 9),
       ("7.4", "Device Functional Modes", 10), ("7.5", "Programming", 10), ("8", "Application and Implementation", 11),
       ("9", "Power Supply Recommendations", 12), ("10", "Installation", 12), ("11", "Mechanical, Packaging, and Orderable Information", 13),
       ("12", "Device and Documentation Support", 14)]
toc_html = "".join(f'<a class="{"l2" if "." in n else ""}" href="#s{n}"><span>{n} {t}</span><span class="pg">{p}</span></a>' for n, t, p in toc)
page(f"""
<h2 class="ds">Table of Contents</h2>
<div class="toc">{toc_html}</div>
<h2 class="ds">Revision History</h2>
<table class="ds">{cap('R', 'Revision History')}<tr><th>Date</th><th>Revision</th><th>Notes</th></tr>
<tr><td>October 2026</td><td>*</td><td>Advance information. Hardware rev B, firmware v1.0.</td></tr></table>
<h2 class="ds" id="s4"><span class="n">4</span>Device Comparison</h2>
<table class="ds">{cap('4', 'Device Comparison')}
<tr><th>Orderable</th><th>Region / band</th><th>Contents</th><th>Max TX</th><th>Status</th></tr>
<tr><td>TW-1-US915-K</td><td>US915, sub-band 2</td><td>Sensor, roof + 2 W panel, radiation shield + SHT45 probe, soil probe, bracket</td><td class="num">+20 dBm</td><td>Pilot</td></tr>
<tr><td>TW-1-US915</td><td>US915</td><td>Sensor, roof + panel, bracket (bring your own probes)</td><td class="num">+20 dBm</td><td>Pilot</td></tr>
<tr><td>TW-1-US915-PCBA</td><td>US915</td><td>Assembled, tested board with cell holder</td><td class="num">+20 dBm</td><td>Pilot</td></tr>
<tr><td>TW-1-AU915</td><td>AU915</td><td>As -K</td><td class="num">+20 dBm</td><td>Planned</td></tr>
<tr><td>TW-1-EU868</td><td>EU868 (1 % duty cycle)</td><td>As -K</td><td class="num">+14 dBm</td><td>Planned</td></tr></table>
<div class="ds-note"><b>ADVANCE INFORMATION.</b> This document describes a product in pilot production. Characteristic data are
representative values from the reference-design build and are subject to change without notice.</div>
<h3 class="ds"><span class="n"></span>Supply and inputs at a glance</h3>
<table class="ds">{cap('4', 'Key Specifications')}
<tr><th>Parameter</th><th class="num">Value</th><th>Parameter</th><th class="num">Value</th></tr>
<tr><td>Sleep current (typ)</td><td class="num">{f(bu['sleep_uA_3V7']['mean'],1)} µA</td><td>Air temperature accuracy</td><td class="num">±{f(H['temp_err_max_C'],1)} °C</td></tr>
<tr><td>Average, 5 min SF9</td><td class="num">{f(H['avg_current_uA_5min_SF9'],0)} µA</td><td>RH accuracy (10–90 %)</td><td class="num">±{f(sen['rh_ext_max_abs_err_below_90'],0)} %RH</td></tr>
<tr><td>Dark autonomy (1 min)</td><td class="num">{f(H['dark_autonomy_days_1min'],0)} d</td><td>Rain resolution</td><td class="num">0.2 mm</td></tr>
<tr><td>TX power (conducted)</td><td class="num">+{f(H['tx_power_dBm_mean'],1)} dBm</td><td>Operating temperature</td><td class="num">−10 to +60 °C</td></tr>
<tr><td>Range, SF10, LOS</td><td class="num">≥ {f(H['range_km_last_decode']['SF10'],0)} km</td><td>Mass, box unit</td><td class="num">{f(MECH['mass_g']['box_unit_only'],0)} g</td></tr></table>
""")

# ============================================================================ page 3: connectors
pins = [
    ("J1", "1", "SOLAR+", "P", "Panel positive, 0–10 V. Reverse-polarity protected (Q1), TVS clamped (D1)."),
    ("J1", "2", "GND", "G", "Panel return"),
    ("J2", "1", "RAIN", "I", "Rain-gauge reed to GND. 1 MΩ pull-up to 3.3 V, 10 kΩ / 22 nF debounce. Counted in sleep."),
    ("J2", "2", "GND", "G", "Ground"),
    ("J3", "1", "3V3_SW", "O", "Switched 3.3 V for the soil probe, on 100 ms per sample. TPS22917 load switch."),
    ("J3", "2", "GND", "G", "Ground"),
    ("J3", "3", "SOIL", "AI", "Probe output 0–3.0 V to 12-bit ADC (1 kΩ / 100 nF); 1 MΩ pull-down when unplugged"),
    ("J4", "1", "3V3_EXT", "O", "Always-on 3.3 V for the air probe; 100 mA PTC (F1)"),
    ("J4", "2", "GND", "G", "Ground"),
    ("J4", "3", "SDA", "I/O", "I²C data (probe 0x44); 100 Ω series, ESD-protected"),
    ("J4", "4", "SCL", "I/O", "I²C clock; 100 Ω series, ESD-protected"),
    ("J5", "—", "RF", "RF", "U.FL, 50 Ω, to the SMA bulkhead and 915 MHz whip antenna"),
    ("J6", "1–6", "SWD", "I/O", "Tag-Connect TC2030-NL: VCC, SWDIO, NRST, SWCLK, GND (pin 6 NC)"),
    ("J7", "1–4", "UART", "I/O", "1.27 mm pads: GND, RX, TX, 3V3. AT commands and bootloader (BOOT0 high)"),
    ("BT1", "+/−", "VBAT", "P", "Protected 18650 Li-ion only, 3.0–4.2 V"),
    ("SW1", "—", "RESET", "I", "Reset button (inside the case)"),
]
prow = "".join(f"<tr><td>{a}</td><td class='num'>{b}</td><td class='mono'>{c}</td><td class='num'>{d}</td><td>{e}</td></tr>" for a, b, c, d, e in pins)
page(f"""
<h2 class="ds" id="s5"><span class="n">5</span>Connector Configuration and Functions</h2>
{fig('r_pcb_top.jpg', 'TW-1 PCBA, Top View (J1–J4 face the gland wall)', '5', h='3.2in')}
<table class="ds">{cap('5', 'Connector Functions')}
<tr><th>Ref</th><th>Pin</th><th>Name</th><th>Type<sup>(1)</sup></th><th>Description</th></tr>{prow}</table>
<div class="tnotes"><p>(1) P = power, G = ground, I = input, O = output, AI = analog input, I/O = bidirectional, RF = radio frequency.</p>
<p>J1–J4: JST PH 2.0 mm side-entry. Mating cables pass through PG7 glands (cable Ø 3–6.5 mm).</p></div>
""")

# ============================================================================ page 4: abs max, ESD, ROC, env
page(f"""
<h2 class="ds" id="s6"><span class="n">6</span>Specifications</h2>
<h3 class="ds" id="s6.1"><span class="n">6.1</span>Absolute Maximum Ratings</h3>
<table class="ds">{cap('6', 'Absolute Maximum Ratings')}<tr><th></th><th></th><th class="num">Min</th><th class="num">Max</th><th>Unit</th></tr>
<tr><td class="p" rowspan="2">Solar input</td><td>J1 voltage (continuous)</td><td class="num">−20</td><td class="num">28</td><td class="u">V</td></tr>
<tr><td>J1 surge (8/20 µs)</td><td class="num"></td><td class="num">±400</td><td class="u">W</td></tr>
<tr><td class="p">Battery</td><td>BT1 voltage</td><td class="num">0</td><td class="num">4.3</td><td class="u">V</td></tr>
<tr><td class="p">Field I/O</td><td>RAIN, SOIL, SDA, SCL</td><td class="num">−0.3</td><td class="num">3.6</td><td class="u">V</td></tr>
<tr><td class="p">Outputs</td><td>3V3_EXT + 3V3_SW load</td><td class="num"></td><td class="num">100</td><td class="u">mA</td></tr>
<tr><td class="p">Temperature</td><td>Storage (Li-ion limited)</td><td class="num">−20</td><td class="num">60</td><td class="u">°C</td></tr></table>
<div class="tnotes"><p>Stresses beyond those listed may cause permanent damage. These are stress ratings only; functional operation at these conditions is not implied.</p></div>
<h3 class="ds" id="s6.2"><span class="n">6.2</span>ESD Ratings</h3>
<table class="ds">{cap('6', 'ESD Ratings')}<tr><th></th><th>Standard</th><th class="num">Value</th><th>Unit</th></tr>
<tr><td class="p" rowspan="2">V<sub>(ESD)</sub> on J1–J5</td><td>IEC 61000-4-2 contact discharge (criterion A)</td><td class="num">±8 000</td><td class="u">V</td></tr>
<tr><td>IEC 61000-4-2 air discharge (criterion B on J4)<sup>(1)</sup></td><td class="num">±15 000</td><td class="u">V</td></tr></table>
<div class="tnotes"><p>(1) One self-recovering reset at ±15 kV air on J4 (9 s to rejoin, no data loss). All other ports met criterion A.</p></div>
<h3 class="ds" id="s6.3"><span class="n">6.3</span>Recommended Operating Conditions</h3>
<table class="ds">{cap('6', 'Recommended Operating Conditions')}<tr><th></th><th></th><th class="num">Min</th><th class="num">Nom</th><th class="num">Max</th><th>Unit</th></tr>
<tr><td class="p">Panel</td><td>Open-circuit voltage at 0 °C</td><td class="num">5.0</td><td class="num">6.0</td><td class="num">10</td><td class="u">V</td></tr>
<tr><td class="p"></td><td>Rated power</td><td class="num">0.5</td><td class="num">2</td><td class="num">5</td><td class="u">W</td></tr>
<tr><td class="p">Cell</td><td>Protected 18650 Li-ion capacity</td><td class="num">2 000</td><td class="num">3 350</td><td class="num">3 500</td><td class="u">mAh</td></tr>
<tr><td class="p">T<sub>A</sub></td><td>Ambient, operating</td><td class="num">−10</td><td class="num">25</td><td class="num">55</td><td class="u">°C</td></tr>
<tr><td class="p">Interval</td><td>Uplink period (US915, SF7–SF10)</td><td class="num">1</td><td class="num">5</td><td class="num">60</td><td class="u">min</td></tr></table>
<h3 class="ds" id="s6.4"><span class="n">6.4</span>Environmental and Mechanical Characteristics</h3>
<table class="ds">{cap('6', 'Environmental and Mechanical')}<tr><th>Parameter</th><th>Test conditions</th><th>Value</th></tr>
<tr><td class="p">Ingress</td><td>Immersion 1 m, 30 min / IPX5 hose</td><td>No ingress / pass (IP66 jet pending)</td></tr>
<tr><td class="p">Thermal cycling</td><td>−10 ↔ +60 °C, 50 cycles</td><td>Pass, gasket set 11 %</td></tr>
<tr><td class="p">UV resistance</td><td>500 h UV-A, white ASA</td><td>ΔE {env['uv_deltaE_500h']['ASA white']}</td></tr>
<tr><td class="p">Drop</td><td>26 × 1 m on concrete</td><td>Pass (cosmetic only)</td></tr>
<tr><td class="p">Cell temperature in sun</td><td>Field, Sept, air max {f(fld['air_max_C'],1)} °C</td><td>{f(fld['internal_max_C'],1)} °C max</td></tr>
<tr><td class="p">Enclosure</td><td>Box W × H × D / installed envelope</td><td>{dm['box_w_h_d'][0]:.0f} × {dm['box_w_h_d'][1]:.0f} × {dm['box_w_h_d'][2]:.0f} mm / {dm['installed_envelope_w_h_d_excl_pole'][0]:.0f} × {dm['installed_envelope_w_h_d_excl_pole'][1]:.0f} × {dm['installed_envelope_w_h_d_excl_pole'][2]:.0f} mm</td></tr>
<tr><td class="p">Mass</td><td>Box unit / installed</td><td>{f(MECH['mass_g']['box_unit_only'],0)} g / {f(MECH['mass_g']['total_installed_excl_pole'],0)} g</td></tr></table>
""")

# ============================================================================ page 5-6: electrical characteristics
ec1 = (EC_HEAD
       + sect("System supply")
       + row("Sleep current, whole system", "VBAT = 3.7 V, no sun, RTC running", "", f(bu['sleep_uA_3V7']['mean'], 1), "10", "µA")
       + row("", "VBAT = 4.2 V", "", f(bu['sleep_uA_4V2']['mean'], 1), f(bu['sleep_uA_4V2']['max'], 1), "µA")
       + row("Average current", "5-min interval, SF9, +20 dBm", "", f(H['avg_current_uA_5min_SF9'], 0), "100", "µA")
       + row("", "1-min interval, SF9", "", f(pw['avg_current_uA_1min_SF9_projected'], 0), "", "µA")
       + row("Charge per uplink", "SF9, 11-byte payload, incl. RX windows", "", f(pw['charge_per_uplink_mC_total'], 1), "", "mC")
       + row("+3V3 output voltage", "I<sub>LOAD</sub> = 10 mA", f(bu['v3v3_V']['min'], 3), "3.300", f(bu['v3v3_V']['max'], 3), "V")
       + row("+3V3 ripple", "I<sub>LOAD</sub> = 10 mA, 20 MHz BW", "", f(bu['v3v3_ripple_mVpp_10mA']['mean'], 0), f(bu['v3v3_ripple_mVpp_10mA']['max'], 0), "mV<sub>PP</sub>")
       + row("+3V3 transient", "5 → 87 mA step (TX start)", "", "−" + f(pw['loadstep_droop_mV'], 0), "±99", "mV")
       + row("Converter efficiency", "VIN 3.7 V, I<sub>OUT</sub> = 10 µA", "", f(pw['efficiency_pct']['VIN3.7_10uA'], 0), "", "%")
       + row("", "I<sub>OUT</sub> = 10 mA", "", f(pw['efficiency_pct']['VIN3.7_10mA'], 0), "", "%")
       + row("", "I<sub>OUT</sub> = 100 mA", "", f(pw['efficiency_pct']['VIN3.7_100mA'], 0), "", "%")
       + sect("Solar charger")
       + row("Input regulation (VIN-DPM)", "Panel current-limited", "4.35", f(sol['vin_dpm_V']['mean'], 2), "4.63", "V")
       + row("Input current limit", "USB500 mode", "450", f(sol['input_limit_mA_measured'], 0), "500", "mA")
       + row("Charge regulation voltage", "", "4.18", f(bu['vbat_reg_V']['mean'], 2), "4.22", "V")
       + row("Termination current", "", "", "10", "", "% I<sub>CHG</sub>")
       + row("Charge window, hot", "Cell temperature rising", "", f(sol['ts_window_C']['hot_stop'], 1), "", "°C")
       + row("Charge window, cold", "Cell temperature falling", "", f(sol['ts_window_C']['cold_stop'], 1), "", "°C")
       + row("Input overvoltage", "J1 rising", "10.2", "10.5", "10.8", "V")
       + row("Battery drain, no sun", "BQ24074 BAT leakage", "", "4.3", "6", "µA")
       + row("Daily harvest", "Clear / cloudy September day", "", f"{f(sol['field_days']['Clear day']['mAh_in'],0)} / {f(sol['field_days']['Cloudy day']['mAh_in'],0)}", "", "mAh"))
page(f"""
<h3 class="ds" id="s6.5"><span class="n">6.5</span>Electrical Characteristics</h3>
<p class="small">T<sub>A</sub> = 25 °C, VBAT = 3.7 V, 2 W panel, firmware v1.0, unless otherwise noted. Typical values are means of 10 rev B units.</p>
<table class="ds">{cap('6', 'Electrical Characteristics')}{ec1}</table>
""")
ec2 = (EC_HEAD
       + sect("Radio")
       + row("Uplink frequency", "US915 sub-band 2, 125 kHz", "902.3", "", "914.9", "MHz")
       + row("Conducted TX power", "At J5, 64 channels, 2 units", f(H['tx_power_dBm_range'][0], 1), f(H['tx_power_dBm_mean'], 1), f(H['tx_power_dBm_range'][1], 1), "dBm")
       + row("Return loss at J5 (installed)", "915 MHz, lid closed, rev B match", "", f(rft['s11']['case_matched_revB']['at_915_dB'], 0), "−15", "dB")
       + row("", "Worst case 902–928 MHz", "", f(rft['s11']['case_matched_revB']['worst_in_band_dB'], 0), "−10", "dB")
       + row("Airtime, 24-byte frame", "SF7 / SF9 / SF10, BW 125 kHz", "", f"{f(lb['airtime_ms']['SF7'],0)} / {f(lb['airtime_ms']['SF9'],0)} / {f(lb['airtime_ms']['SF10'],0)}", "", "ms")
       + row("Range, line of sight", "Gateway at 10 m, ≥ 50 % PDR, SF7", "", f(rft['range']['SF7']['max_km_PDR50'], 1), "", "km")
       + row("", "SF10 (last test point)", f(rft['range']['SF10']['last_decode_km'], 1), "", "", "km")
       + row("OTAA join time", "Median, SF9", "", f(bu['otaa_join_s_median'], 1), "", "s")
       + sect("Sensors")
       + row("Air temperature accuracy", "External SHT45 probe, −10 to +60 °C", "−0.3", f"±{f(sen['temp_ext_rms_err_C'],1)}", "0.3", "°C")
       + row("Air humidity accuracy", "10–90 %RH, 25 °C", "−2", "±" + f(TEST['sensors']['rh_ext_rms_err'], 1), "2", "%RH")
       + row("Internal temperature offset", "Charging at 400 mA (self-heating)", "", f(sen['selfheat_at_400mA_C'], 2), "", "°C")
       + row("Soil input range", "J3 pin 3", "0", "", "3.0", "V")
       + row("Soil ADC resolution", "", "", "12", "", "bit")
       + row("Probe warm-up", "3V3_SW on before sampling", "", "100", "", "ms")
       + row("Rain pulse width", "Reed closure", "10", "", "", "ms")
       + row("Rain count rate, exact", "", "", "", "5", "tips/s")
       + row("Battery voltage accuracy", "ADC via 1:2 divider, 3.0–4.2 V", "", "±15", "", "mV")
       + sect("Timing")
       + row("Awake time per uplink", "Sense + TX + RX windows, SF9", "", f(pw['awake_time_s'], 2), "", "s")
       + row("Magnet wake", "Tap (send now) / hold (rejoin)", "", "0.2 / 3", "", "s")
       + row("Hall sensor sampling", "DRV5032FB", "", "5", "", "Hz"))
page(f"""
<table class="ds">{cap('6', 'Electrical Characteristics (continued)')}{ec2}</table>
<div class="tnotes"><p>Accuracy figures include the probe and the reading chain, measured against reference instruments (see the engineering report, section 10).</p></div>
""")

# ============================================================================ page 7-8: typical characteristics
tc = [("test_bringup_sleep.png", "Sleep Current, 10 Units"), ("test_ppk2_cycle.png", "Supply Current Through One Uplink"),
      ("test_efficiency.png", "Converter Efficiency vs Load"), ("test_loadstep.png", "+3V3 Response to TX Load Step"),
      ("test_solar_days.png", "Solar Charging, Clear and Cloudy Days"), ("test_vin_dpm.png", "Input Regulation vs Panel Current"),
      ("test_temp_accuracy.png", "Air Temperature Error vs Temperature"), ("test_rh_accuracy.png", "Humidity Error at Reference Points")]
tc2 = [("test_tx_power.png", "Conducted TX Power vs Channel"), ("test_s11.png", "Return Loss at J5, Installed"),
       ("test_range.png", "Packet Delivery vs Distance"), ("test_dark_test.png", "Battery State, No Sun, 1-Min Mode"),
       ("test_field_temp.png", "Enclosure vs Air Temperature, Field"), ("sim_thermal_enclosure.png", "Cell Temperature vs Mounting (Model)"),
       ("sim_energy_year.png", "Battery State over a Year (Model)"), ("test_field_rain_ref.png", "Rainfall vs Reference Gauge")]


def grid(items):
    return '<div class="figgrid">' + "".join(fig(s, c, '6') for s, c in items) + '</div>'


page(f"""<h3 class="ds" id="s6.6"><span class="n">6.6</span>Typical Characteristics</h3>
<p class="small">At T<sub>A</sub> = 25 °C, VBAT = 3.7 V, unless otherwise noted.</p>{grid(tc)}""")
page(grid(tc2))

# ============================================================================ page 9: detailed description
page(f"""
<h2 class="ds" id="s7"><span class="n">7</span>Detailed Description</h2>
<h3 class="ds" id="s7.1"><span class="n">7.1</span>Overview</h3>
<p>The TW-1 combines a RAK3172 LoRaWAN module (STM32WLE5CC with a sub-GHz radio), a BQ24074 linear charger with power path, a
TPS63900 buck-boost converter, a protected 18650 Li-ion cell and four field inputs on one 4-layer board inside a sealed ASA
enclosure. Firmware runs on the module (RAKwireless RUI3). The device sleeps in STOP2 between scheduled uplinks and wakes early on
rain-gauge pulses and magnet taps.</p>
<h3 class="ds" id="s7.2"><span class="n">7.2</span>Functional Block Diagram</h3>
{fig('block_diagram.png', 'Functional Block Diagram', '7', h='3.6in')}
<h3 class="ds" id="s7.3"><span class="n">7.3</span>Feature Description</h3>
<h4 class="ds">7.3.1 Solar Power Path</h4>
<p>The charger runs in USB500 mode, so its input-voltage loop (VIN-DPM, {f(sol['vin_dpm_V']['mean'],2)} V typ) cuts the charge current
before the panel collapses. A 5 V panel's maximum-power voltage falls to about {f(sv['vmp_hot_V'],2)} V at a working temperature of 55 °C, so this
fixed point captures {f(sv['mpp_capture_hot_pct'],0)} % of the available power without an MPPT controller. The system load always runs from VSYS;
the cell supplies only the shortfall.</p>
<h4 class="ds">7.3.2 Temperature-Qualified Charging</h4>
<p>A 10 kΩ NTC against the cell stops charging outside about 0 to 50 °C. The ventilated roof keeps the cell well below the hot limit:
{f(th['design_day_kona_calm']['White box under ventilated solar roof']['max_battery_C'],0)} °C modelled on a calm August day, {f(fld['internal_max_C'],0)} °C measured in the field.</p>
<h4 class="ds">7.3.3 Low-Power Sensing</h4>
<p>The soil probe is powered only while sampling. The battery divider uses a high-side switch that leaks 3 nA when off. The rain input
is filtered in hardware (τ 0.22 ms on close, 22 ms on release) and counted by interrupt while the MCU sleeps.</p>
""")

# ============================================================================ page 10: modes + programming
page(f"""
<h3 class="ds" id="s7.4"><span class="n">7.4</span>Device Functional Modes</h3>
<table class="ds">{cap('7', 'Functional Modes')}<tr><th>Mode</th><th>Entered by</th><th class="num">Supply current</th><th>Duration</th></tr>
<tr><td class="p">Sleep</td><td>End of an uplink cycle</td><td class="num">{f(bu['sleep_uA_3V7']['mean'],1)} µA</td><td>Until the next deadline or an interrupt</td></tr>
<tr><td class="p">Measure</td><td>RTC alarm</td><td class="num">≈ 9 mA</td><td>150 ms (incl. 100 ms probe warm-up)</td></tr>
<tr><td class="p">Transmit</td><td>After measure</td><td class="num">87 mA</td><td>62–371 ms (SF7–SF10)</td></tr>
<tr><td class="p">Receive</td><td>RX1 / RX2 windows</td><td class="num">5.2 mA</td><td>2 × ≈ 25 ms</td></tr>
<tr><td class="p">Rapid</td><td>Downlink 0x02, rain rate or soil change</td><td class="num">{f(pw['avg_current_uA_1min_SF9_projected'],0)} µA avg</td><td>1-min interval, timed</td></tr>
<tr><td class="p">Join</td><td>First boot, or magnet held 3 s</td><td class="num">—</td><td>{f(bu['otaa_join_s_median'],0)} s median, exponential back-off</td></tr></table>
<h3 class="ds" id="s7.5"><span class="n">7.5</span>Programming</h3>
<h4 class="ds">7.5.1 Uplink Format</h4>
<table class="ds">{cap('7', 'fPort 1 Measurement Frame (11 bytes, big-endian)')}<tr><th>Byte</th><th>Field</th><th>Type</th><th>Scale</th><th>Range</th></tr>
<tr><td class="num">0</td><td>Flags</td><td>u8</td><td colspan="2">b0 rapid, b1 charging, b2 power good, b3 battery low, b4 air OK, b5 soil OK, b6 internal OK</td></tr>
<tr><td class="num">1–2</td><td>Air temperature</td><td>s16</td><td>0.01 °C</td><td>0x7FFF = missing</td></tr>
<tr><td class="num">3</td><td>Air humidity</td><td>u8</td><td>0.5 %RH</td><td>0–100 %</td></tr>
<tr><td class="num">4</td><td>Soil moisture</td><td>u8</td><td>0.5 %</td><td>0–100 %</td></tr>
<tr><td class="num">5–6</td><td>Rain tips</td><td>u16</td><td>0.2 mm / tip</td><td>Cumulative, wraps</td></tr>
<tr><td class="num">7</td><td>Battery</td><td>u8</td><td>2 500 mV + 10 mV·n</td><td>2.50–5.05 V</td></tr>
<tr><td class="num">8</td><td>Internal temperature</td><td>s8</td><td>0.5 °C</td><td>0x7F = missing</td></tr>
<tr><td class="num">9</td><td>Internal humidity</td><td>u8</td><td>0.5 %RH</td><td></td></tr>
<tr><td class="num">10</td><td>Panel voltage</td><td>u8</td><td>25 mV</td><td>0–6.37 V</td></tr></table>
<h4 class="ds">7.5.2 Downlink Commands (fPort 10)</h4>
<table class="ds">{cap('7', 'Downlink Commands')}<tr><th>Bytes</th><th>Command</th><th>Notes</th></tr>
<tr><td class="mono">01 HH LL</td><td>Set interval (s)</td><td>60–3 600 s</td></tr>
<tr><td class="mono">02 MM</td><td>Rapid mode for MM minutes</td><td>02 00 ends rapid mode</td></tr>
<tr><td class="mono">03</td><td>Send health frame now</td><td>fPort 2, confirmed</td></tr>
<tr><td class="mono">04 B0 07</td><td>Reboot</td><td>Two-byte key guards against stray bytes</td></tr></table>
<p class="small">Decoders for The Things Stack and ChirpStack v4: <span class="mono">firmware/decoder/ttn_decoder.js</span>.</p>
""")

# ============================================================================ page 11: application
page(f"""
<h2 class="ds" id="s8"><span class="n">8</span>Application and Implementation</h2>
<div class="ds-caution"><b>Note:</b> Information in the following application sections is not part of the specification. Customers validate and test their own installation.</div>
<h3 class="ds"><span class="n">8.1</span>Typical Application: Irrigation and Frost Monitoring</h3>
<div class="ds-cols">
<div>{fig('r_product_hero_outdoor.jpg', 'Typical Installation', '8')}</div>
<div>
<table class="ds">{cap('8', 'Design Requirements')}<tr><th>Parameter</th><th>Example value</th></tr>
<tr><td>Reporting</td><td>5 min; rapid 1 min during irrigation</td></tr>
<tr><td>Gateway distance</td><td>0.5–5 km, one gateway per farm</td></tr>
<tr><td>Probe height</td><td>1.5–2 m air; soil probe at root depth</td></tr>
<tr><td>Panel orientation</td><td>Facing south, 20° tilt (Hawaiʻi)</td></tr>
<tr><td>Network</td><td>ChirpStack or The Things Stack</td></tr></table>
</div></div>
<h3 class="ds"><span class="n">8.2</span>Detailed Installation Procedure</h3>
<ol class="ds">
<li>Mount the bracket on a 25–50 mm pole, box 1.5–2 m above ground. Keep it 3 m or more from metal roofs and water tanks to limit RF shadow.</li>
<li>Fit the probe cables through the PG7 glands with a drip loop below each gland, then torque the gland domes to 2.5 N·m.</li>
<li>Insert a protected 18650 (ships at about 30 % charge), close the lid and torque the M4 screws to 1.2 N·m in a cross pattern.</li>
<li>Tap the magnet on the lid logo. The LED blinks while joining and holds solid for 2 s when joined.</li>
<li>Check the first uplinks in the network server: RSSI above −115 dBm at SF9 gives about 10 dB of fade margin.</li>
</ol>
<h3 class="ds"><span class="n">8.3</span>Application Curves</h3>
<div class="figgrid">{fig('test_field_battery.png', 'Battery State, 30-Day Pilot (3 Units)', '8')}{fig('test_field_soil_rain.png', 'Soil Moisture and Rain, Pilot Site', '8')}</div>
""")

# ============================================================================ page 12: power supply + installation
page(f"""
<h2 class="ds" id="s9"><span class="n">9</span>Power Supply Recommendations</h2>
<ul class="ds">
<li><b>Panel:</b> 5 V class (10 series cells), V<sub>OC</sub> ≤ 6.5 V at 0 °C, 0.5–5 W. A 6 V class panel works, but wastes 10–20 % of its power, because input regulation holds it at 4.5 V.</li>
<li><b>Cell:</b> protected 18650 Li-ion only (PCM cut-off ≥ 2.5 V). Unprotected cells can be deep-discharged after very long dark periods.</li>
<li><b>Energy margin:</b> on the worst simulated day in Honolulu the panel still delivers {f(ey['min_daily_harvest_mAh'],0)} mAh, {f(ey['panel_oversize_vs_1min_worst_day'],0)}× the
1-minute-mode use. With no sun at all, a full cell lasts {f(H['dark_autonomy_days_1min'],0)} days in rapid mode and about {SIM['energy_year']['dark_autonomy_days_to_20pct']['5-min']} days at 5 minutes.</li>
<li><b>Storage:</b> ship and store at 30–50 % charge, 10–25 °C. The device stays joined to the network while stored, so expect one uplink per interval.</li>
</ul>
<h2 class="ds" id="s10"><span class="n">10</span>Installation</h2>
<h3 class="ds"><span class="n">10.1</span>Guidelines</h3>
<ul class="ds">
<li>Antenna vertical, pointing down (as shipped), clear of the pole by 40 mm or more. Do not paint the antenna or the lid.</li>
<li>Radiation shield in free air: not over pavement or above a roof, and 1 m or more from walls.</li>
<li>Keep the panel unshaded from 9 am to 3 pm. In shade the device still runs for months on the cell, but charges slowly.</li>
<li>Coastal sites (within about 200 m of surf): use the stainless hardware kit and inspect the glands yearly. Salt-fog qualification is pending.</li>
</ul>
<h3 class="ds"><span class="n">10.2</span>Layout Example (PCBA)</h3>
{fig('layer_strip.png', 'Copper Layers L1–L4: Signals, GND Plane, 3.3 V Plane, Signals', '10')}
<p class="small">The PCB is 4-layer, 1.6 mm (JLC 7628 stackup), with 50 Ω CPWG on L1 (0.35 mm trace, 0.20 mm gap) and a fenced RF path. The SHT40 sits on a slotted
thermal island. KiCad 9 source, Gerbers and BOM: {REPO}.</p>
""")

# ============================================================================ page 13: mechanical / orderable
page(f"""
<h2 class="ds" id="s11"><span class="n">11</span>Mechanical, Packaging, and Orderable Information</h2>
{fig('mech_ga_enclosure.png', 'Enclosure Outline Drawing (dimensions in mm)', '11', h='4.1in')}
<table class="ds">{cap('11', 'Orderable Information')}<tr><th>Orderable part</th><th>Status</th><th>Package</th><th class="num">Pack qty</th><th>Contents</th></tr>
<tr><td>TW-1-US915-K</td><td>PILOT</td><td>Kit box</td><td class="num">1</td><td>Sensor, roof + panel, shield + probe, soil probe, bracket, 2 × U-bolt, magnet key</td></tr>
<tr><td>TW-1-US915</td><td>PILOT</td><td>Kit box</td><td class="num">1</td><td>Sensor, roof + panel, bracket, magnet key</td></tr>
<tr><td>TW-1-US915-PCBA</td><td>PILOT</td><td>ESD bag</td><td class="num">10</td><td>Tested boards (no cell)</td></tr></table>
<table class="ds">{cap('11', 'Mechanical Data')}<tr><th>Item</th><th>Material / finish</th><th>Value</th></tr>
<tr><td>Box and lid</td><td>ASA, white, UV-stabilized</td><td>3 mm wall, 1° draft</td></tr>
<tr><td>Seal</td><td>Silicone cord, 2.5 mm</td><td>{f(MECH['gasket']['compression_pct'],0)} % compression</td></tr>
<tr><td>Hardware</td><td>A2 stainless; brass inserts</td><td>M4 lid, M3 PCB</td></tr>
<tr><td>Cable entries</td><td>PG7 glands, PA66</td><td>4 × (Ø 3–6.5 mm)</td></tr>
<tr><td>Antenna</td><td>915 MHz whip, SMA</td><td>2 dBi, about 195 mm</td></tr></table>
""")

# ============================================================================ page 14: doc support
page(f"""
<h2 class="ds" id="s12"><span class="n">12</span>Device and Documentation Support</h2>
<h3 class="ds"><span class="n">12.1</span>Documentation</h3>
<ul class="ds">
<li><i>Tradewind TW-1 Engineering Design &amp; Test Report</i>, BB-ENG-2026-014: design analysis, simulation, layout, bring-up and characterization.</li>
<li>Design files: KiCad 9 project, Gerbers, BOM, enclosure CAD (STEP/STL), firmware, decoders and test logs: {REPO}.</li>
<li>Datasheets of the main components: RAK3172 (RAKwireless), BQ24074, TPS63900, TPS22917, TPD4E02B04, DRV5032 (Texas Instruments), SHT4x (Sensirion).</li>
</ul>
<h3 class="ds"><span class="n">12.2</span>Regulatory</h3>
<p>The radio is a modular-certified RAK3172 (contains FCC ID and IC as marked on the module). The host product requires
FCC Part 15 Subpart B verification and labeling before sale; a pre-scan is planned with the pilot build.</p>
<h3 class="ds"><span class="n">12.3</span>Trademarks</h3>
<p class="small">LoRa® and LoRaWAN® are trademarks of Semtech Corporation or its subsidiaries. All other trademarks are the property of their respective owners.</p>
<h3 class="ds"><span class="n">12.4</span>Electrostatic Discharge Caution</h3>
<div class="ds-caution">The bare PCBA can be damaged by ESD. Handle it at a grounded workstation; the field ports are protected only once the board is installed in the enclosure.</div>
<h3 class="ds"><span class="n">12.5</span>Glossary</h3>
<table class="ds compact"><tr><th>Term</th><th>Meaning</th></tr>
<tr><td>VIN-DPM</td><td>Input-voltage dynamic power management: the charger reduces its input current to hold the panel voltage</td></tr>
<tr><td>SF</td><td>LoRa spreading factor (higher means longer range, longer airtime)</td></tr>
<tr><td>PDR</td><td>Packet delivery ratio</td></tr>
<tr><td>CPWG</td><td>Grounded coplanar waveguide</td></tr>
<tr><td>OTAA</td><td>Over-the-air activation (LoRaWAN join)</td></tr></table>
<h3 class="ds"><span class="n">12.6</span>Important Notice</h3>
<p class="small mute">Binary Beach LLC provides this datasheet and the reference design "as is", for evaluation and engineering use. Advance-information data
are representative of the rev B pilot build and are subject to change. Binary Beach makes no warranty of fitness for a particular purpose; users
are responsible for validating the design in their application and for meeting the regulations that apply where it is used. Hardware design files are
licensed under CERN-OHL-P-2.0 and firmware under the MIT License.</p>
""")

# ============================================================================ assemble
HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TW-1 Datasheet</title><link rel="icon" href="img/logo.png"><link rel="stylesheet" href="datasheet.css">
<script>(function(){var q=new URLSearchParams(location.search);if(q.has('embed')||window.self!==window.top){document.documentElement.classList.add('embed')}})();</script>
</head><body>
<div class="ds-bar-screen"><a href="/hardware/tradewind/">← Tradewind</a><span>TW-1 datasheet · advance information</span><button type="button" onclick="print()">Print or save PDF</button></div>
"""
n = len(pages)
out = HEAD
for i, b in enumerate(pages):
    out += (f'<div class="ds-page"><div class="ds-hd"><div class="brand"><img src="img/logo.png" alt=""><div class="wm">BINARY <span>BEACH</span></div></div>'
            f'<div class="pn"><b>TW-1</b><small>{DOC_DS} · ADVANCE INFORMATION</small></div></div><div class="ds-bar"></div>'
            f'<div class="ds-body">{b}</div><div class="ds-ft"><span>Copyright © 2026 Binary Beach LLC</span>'
            f'<span class="c">Submit document feedback: maxwell.pauly@binarybeach.tech</span><span class="r">TW-1<b>{i + 1}</b></span>'
            f'<div class="links">Product folder links: TW-1 · binarybeach.tech/hardware/tradewind</div></div></div>\n')
out += "</body></html>"
open(OUT, "w").write(out)
print("datasheet:", OUT, n, "pages")
