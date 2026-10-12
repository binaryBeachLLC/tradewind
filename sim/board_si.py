"""board_si — Signal and power integrity checks on the routed rev B board.

Reads hardware/fab/layout_audit.json (written by tools/layout_audit.py from the .kicad_pcb), so the
lengths and widths are the real ones, not estimates.

1. DC drop and temperature rise on every current path (copper resistance from length, width and the
   35 µm outer copper; IPC-2221 external-layer curve for the temperature rise).
2. I²C rise time on the internal bus and on the external bus through the air-probe cable
   (0.8473·Rp·C, 30 %→70 %), against the 1000 ns (100 kHz) and 300 ns (400 kHz) limits.
   Trace capacitance from the microstrip formula for 0.2 mm on L1 over L2 (0.21 mm 7628, εr 4.4).
   Assumed: 5 pF per MCU pin, 10 pF per SHT4x, 0.25 pF per TPD4E02B04 line, cable 100 pF/m per
   conductor (unshielded 4-core PUR, typical); measure the real cable before raising the clock.
3. How much the rev B π-match (C14 shunt + L2 series) attenuates the radio's 2nd and 3rd harmonics,
   between 50 Ω ports. The 3rd harmonic of 902–915 MHz lands in the 2690–2900 MHz restricted band.
4. ADC settling after each sense switch turns on, against the firmware delays in firmware/tradewind/board.h.
"""
import json
import os
import re

import numpy as np
import matplotlib.pyplot as plt

from common import ROOT, apply, C, save, fig_path, record, FIG_W, FIG_HALF, limit_line, label_end

apply()
A = json.load(open(os.path.join(ROOT, "hardware", "fab", "layout_audit.json")))
BOARD_H = open(os.path.join(ROOT, "firmware", "tradewind", "board.h")).read()


def fw(name):
    return float(re.search(r"#define\s+%s\s+([\d.]+)" % name, BOARD_H).group(1))


out = {}

# ---------------------------------------------------------------- 1. DC paths
RHO, T = 1.72e-8, 35e-6
paths = []
for p in A["paths"]:
    if not p["current_A"]:
        continue
    q = dict(label=p["label"], net=p["net"], length_mm=p["length_mm"], width_mm=p["min_width_mm"], r_mohm=p["r_mohm"],
             current_A=p["current_A"], drop_mV=p["drop_mV"], dT_C=p["dT_C"], ampacity_10C_A=p["ampacity_10C_A"])
    # copper at 60 °C (enclosure in the sun): +15.7 %
    q["drop_mV_60C"] = round(p["drop_mV"] * (1 + 0.00393 * 40), 1)
    paths.append(q)
vb = next(p for p in paths if p["net"] == "VBAT")
out["dc_paths"] = paths
out["vbat_revC_1mm"] = dict(r_mohm=round(vb["r_mohm"] * vb["width_mm"] / 1.0, 1),
                            drop_mV=round(vb["drop_mV"] * vb["width_mm"] / 1.0, 1))
cap5 = next(p for p in A["paths"] if "C5" in p["label"])
out["c5_from_U2_mm"] = cap5["length_mm"]
out["c5_loop_nH_est"] = round(cap5["length_mm"] * 1.0, 0)   # ~1 nH/mm for a thin trace over a plane 0.2 mm below (upper bound)

# ---------------------------------------------------------------- 2. I²C
def microstrip(w, h=0.2104, er=4.4, t=0.035):
    we = w + t / np.pi * (1 + np.log(2 * h / t))
    u = we / h
    ee = (er + 1) / 2 + (er - 1) / 2 / np.sqrt(1 + 12 / u)
    z0 = 120 * np.pi / np.sqrt(ee) / (u + 1.393 + 0.667 * np.log(u + 1.444))
    return z0, ee


z0, ee = microstrip(0.2)
c_per_mm = np.sqrt(ee) / (299792458 * z0) * 1e-3 * 1e12        # pF/mm
n = A["nets"]
L = lambda net: sum(n[net]["length_mm"].values())
C_PIN_MCU, C_SHT, C_ESD, C_CABLE = 5.0, 10.0, 0.25, 100.0
c_int = max(L("SDA"), L("SCL")) * c_per_mm + C_PIN_MCU + C_SHT
c_ext_board = max(L("SDA_EXT"), L("SCL_EXT")) * c_per_mm + C_ESD
RP = 4700


def rise(rp, cable_m):
    return 0.8473 * rp * (c_int + c_ext_board + C_CABLE * cable_m + C_SHT) * 1e-12 * 1e9


m = np.linspace(0, 5, 101)
out["i2c"] = dict(trace_pF_per_mm=round(c_per_mm, 3), trace_z0_ohm=round(z0, 1), c_internal_pF=round(c_int, 1),
                  c_total_1m_pF=round(c_int + c_ext_board + C_CABLE + C_SHT, 1),
                  rise_ns_no_probe=round(0.8473 * RP * c_int * 1e-3, 0), rise_ns_1m=round(rise(RP, 1.0), 0),
                  max_cable_m_100k_4k7=round(float(m[rise(RP, m) <= 1000].max()), 2),
                  max_cable_m_400k_2k2=round(float(m[rise(2200, m) <= 300].max()), 2),
                  max_cable_m_400k_4k7=round(float(m[rise(RP, m) <= 300].max()), 2) if (rise(RP, m) <= 300).any() else 0,
                  sink_mA_4k7=round(3.3 / RP * 1e3, 2), clock_hz_firmware=100000,
                  assumptions="5 pF/MCU pin, 10 pF/SHT4x, 0.25 pF ESD, cable 100 pF/m")

fig, ax = plt.subplots(figsize=FIG_W)
for k, rp in enumerate([4700, 2200]):
    ax.plot(m, rise(rp, m), color=C.series[k], lw=1.6, label="Rp = %.1f kΩ%s" % (rp / 1e3, " (rev B)" if rp == RP else ""))
    label_end(ax, m[-1], rise(rp, m)[-1], "%.1f kΩ" % (rp / 1e3), color=C.series[k])
ax.set_xlim(0, 5)
ax.set_ylim(0, 2200)
limit_line(ax, y=1000)
limit_line(ax, y=300)
ax.text(2.45, 1000 - 30, "100 kHz limit 1000 ns", color=C.mute, va="top")
ax.text(1.6, 300 - 30, "400 kHz limit 300 ns", color=C.mute, va="top")
ax.axvline(1.0, color=C.mute, lw=0.8, ls=":")
ax.text(1.03, 2100, "TW-1 probe cable 1 m", fontsize=7.5, color=C.mute, va="top")
ax.set_xlabel("Air-probe cable length (m)")
ax.set_ylabel("SDA/SCL rise time, 30→70 % (ns)")
ax.set_title("External I²C bus: rise time vs probe cable length")
ax.legend(loc="upper right", bbox_to_anchor=(0.9, 1.0))
save(fig, fig_path("i2c_rise"))

# ---------------------------------------------------------------- 3. harmonics through the π-match
def s21_db(f, c14, l2, pad=0.1e-12, z0=50.0):
    w = 2 * np.pi * f
    y1 = 1j * w * (c14 + pad)            # shunt at the module side
    zs = 1j * w * l2 + (w * l2 / 30 if l2 else 0)
    y2 = 1j * w * pad                    # C15 DNP: pad capacitance only
    # ABCD = shunt(y1) · series(zs) · shunt(y2)
    Am = 1 + zs * y2
    Bm = zs
    Cm = y1 + y2 + y1 * zs * y2
    Dm = 1 + zs * y1
    return 20 * np.log10(np.abs(2 / (Am + Bm / z0 + Cm * z0 + Dm)))


f = np.linspace(0.5e9, 3.2e9, 541)
s_b = s21_db(f, 1.8e-12, 7.5e-9)
s_a = s21_db(f, 0.0, 0.0)
H = {}
for name, fx in (("f0", 915e6), ("2f0", 1830e6), ("3f0", 2745e6)):
    H[name] = round(float(s21_db(np.array([fx]), 1.8e-12, 7.5e-9)[0] - s21_db(np.array([fx]), 0, 0)[0]), 1)
out["harmonics"] = dict(rel_attenuation_dB=H, restricted_band_MHz=[2690, 2900], third_harmonic_MHz=[2706.9, 2744.7],
                        note="50 Ω-terminated estimate with ideal parts (L Q = 30, 0.1 pF pads)")
fig, ax = plt.subplots(figsize=FIG_W)
ax.axvspan(2690, 2900, color=C.band, zorder=0)
ax.text(2795, -1.2, "restricted band\n2690–2900 MHz", ha="center", va="top", fontsize=7, color=C.mute)
ax.plot(f / 1e6, s_a, color=C.series[2], lw=1.4, label="Rev A (0 Ω, no match)")
ax.plot(f / 1e6, s_b, color=C.series[0], lw=1.6, label="Rev B π-match (C14 1.8 pF, L2 7.5 nH)")
for name, fx in (("f0", 915), ("2f0", 1830), ("3f0", 2745)):
    v = float(s21_db(np.array([fx * 1e6]), 1.8e-12, 7.5e-9)[0])
    ax.plot([fx], [v], "o", ms=4, color=C.series[0], zorder=5)
    ax.annotate(("%s  %.1f dB" % (name.replace("f0", "f₀"), v)).replace("-", "−"), (fx, v), xytext=(-8, -4), textcoords="offset points", va="top",
                ha="right", color=C.ink)
ax.set_xlim(500, 3200)
ax.set_ylim(-14, 0.5)
ax.set_xlabel("Frequency (MHz)")
ax.set_ylabel("|S21| between 50 Ω ports (dB)")
ax.set_title("The antenna match is also a low-pass at the radio's harmonics")
ax.legend(loc="lower left")
save(fig, fig_path("rf_harmonics"))

# ---------------------------------------------------------------- 4. ADC settling
LSB12 = 1 / 4096
settle = []
for name, rth, c, wait_ms, note in (
        ("VBAT_ADC", 50e3, 10e-9, fw("VBAT_SETTLE_MS"), "R11 ‖ R12 into C10, after Q2 turns on"),
        ("SOIL_ADC", 1e3, 100e-9, fw("SOIL_WARMUP_MS"), "R22 into C21; probe output settles first (100 ms warm-up)"),
        ("SOLAR_SENSE", 1e6 * 330e3 / 1.33e6, 100e-9, None, "always connected, no switch to settle")):
    tau = rth * c
    row = dict(net=name, r_source_kohm=round(rth / 1e3, 1), c_nF=round(c * 1e9, 0), tau_ms=round(tau * 1e3, 2),
               need_ms_half_lsb=round(tau * np.log(2 / LSB12) * 1e3, 2), wait_ms=wait_ms, note=note)
    if wait_ms is not None:
        err = np.exp(-wait_ms * 1e-3 / tau)
        row["error_pct_at_wait"] = round(float(err * 100), 4)
        row["ok"] = bool(wait_ms * 1e-3 >= tau * np.log(2 / LSB12))
        if name == "VBAT_ADC":
            row["error_pct_at_3ms_pilot_fw"] = round(float(np.exp(-3e-3 / tau) * 100), 3)
    # sampling-cap kickback (STM32WL ADC ~5 pF): share charge with the filter cap
    row["kickback_pct"] = round(5e-12 / c * 100, 3)
    settle.append(row)
out["adc_settling"] = settle

# ---------------------------------------------------------------- 5. plane pair
area = 96 * 70 * 1e-6 * 0.94
out["plane_pair_pF"] = round(8.854e-12 * 4.6 * area / 1.065e-3 * 1e12, 0)

record("board_si", out)
print(json.dumps(out, indent=1, ensure_ascii=False))
