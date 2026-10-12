"""Layout figures for the report, drawn from the routed board (hardware/fab/layout_geometry.json).

python tools/layout_figs.py   (after tools/layout_audit.py)
Writes docs/figures/layout_map.png (whole board, copper colored by electrical role),
layout_power.png (charger + buck-boost close-up with the hot loops) and layout_rf.png (RF line close-up).
"""
import json
import logging
import os
import sys

import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection, PatchCollection  # noqa: E402
from matplotlib.patches import Circle, Polygon, Patch  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from plotstyle import apply, C, save  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
G = json.load(open(os.path.join(ROOT, "hardware", "fab", "layout_geometry.json")))
A = json.load(open(os.path.join(ROOT, "hardware", "fab", "layout_audit.json")))
FIG = os.path.join(ROOT, "docs", "figures")
apply()

ROLE = [  # (name, color, nets) — fixed categorical order
    ("RF (50 Ω CPWG)", C.series[0], {"RF_MOD", "RF_ANT"}),
    ("Power / high current", C.series[1], {"SOLAR_RAW", "VIN_SOLAR", "VBAT", "VSYS"}),
    ("Sensitive analog / config", C.series[2], {"VBAT_ADC", "SOIL_ADC", "SOLAR_SENSE", "AUX_ADC", "TS", "ISET", "ILIM",
                                               "CFG1", "CFG2", "CFG3", "VBAT_SW", "VBAT_GATE"}),
    ("Leaves the box (ESD-protected)", C.series[3], {"SDA_EXT", "SCL_EXT", "SOIL_EXT", "RAIN_EXT", "+3V3_EXT", "+3V3_SW"}),
    ("Switch node", C.series[4], {"LX1", "LX2"}),
]
P3V3, GND_C, DIG, POUR, EDGE = "#4f5a64", "#c3c9ce", "#9aa3ab", "#e9eef0", "#1f2328"


def color(net):
    for _, c, s in ROLE:
        if net in s:
            return c
    return {"+3V3": P3V3, "GND": GND_C}.get(net, DIG)


def draw(ax, x0, x1, y0, y1, pour=True, refs=(), ref_size=7, bottom=True):
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.figure.canvas.draw()
    ppm = ax.get_window_extent().width / (x1 - x0) * 72 / ax.figure.dpi      # points per mm
    if pour:
        ax.add_collection(PatchCollection([Polygon(p) for p in G["pour_f"] if len(p) > 2], facecolor=POUR, edgecolor="none",
                                          zorder=0))
    for o in G["outline"]:
        xs, ys = zip(*o)
        ax.plot(xs, ys, color=EDGE, lw=0.9, zorder=6)
    if bottom:
        bt = [t for t in G["tracks"] if t["layer"] == "B.Cu"]
        ax.add_collection(LineCollection([(t["a"], t["b"]) for t in bt], linewidths=[t["w"] * ppm for t in bt],
                                         colors=[color(t["net"]) for t in bt], alpha=0.35, capstyle="round", zorder=1))
    ft = [t for t in G["tracks"] if t["layer"] == "F.Cu"]
    ax.add_collection(LineCollection([(t["a"], t["b"]) for t in ft], linewidths=[t["w"] * ppm for t in ft],
                                     colors=[color(t["net"]) for t in ft], capstyle="round", zorder=3))
    pads = [p for p in G["pads"] if len(p["poly"]) > 2]
    ax.add_collection(PatchCollection([Polygon(p["poly"]) for p in pads], facecolor=[color(p["net"]) for p in pads],
                                      edgecolor="none", zorder=4))
    ax.add_collection(PatchCollection([Circle(v["p"], v["d"] / 2) for v in G["vias"]],
                                      facecolor=[color(v["net"]) for v in G["vias"]], edgecolor="white", linewidth=0.3, zorder=5))
    at = {f["ref"]: f["p"] for f in G["footprints"]}
    for ref, dx, dy in refs:
        x, y = at[ref]
        ax.text(x + dx, y + dy, ref, fontsize=ref_size, color=C.ink, ha="center", va="center", zorder=8, weight="semibold",
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    return ppm


def legend(ax, **kw):
    h = [Patch(color=c, label=n) for n, c, _ in ROLE] + [Patch(color=P3V3, label="+3V3"), Patch(color=GND_C, label="GND"),
                                                          Patch(color=DIG, label="Digital / slow")]
    ax.legend(handles=h, fontsize=7, frameon=False, **kw)


def note(ax, xy, text, xytext, ha="left"):
    ax.annotate(text, xy, xytext=xytext, textcoords="data", fontsize=7, color=C.ink, ha=ha, va="center", zorder=9,
                arrowprops=dict(arrowstyle="-", color=C.mute, lw=0.6, shrinkA=1, shrinkB=1),
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=C.line, lw=0.5))


# ---------------------------------------------------------------- whole board
fig, ax = plt.subplots(figsize=(6.8, 5.15))
draw(ax, -1, 97, -1, 71, refs=[("U1", 0, 0), ("U2", 0, -2.6), ("U3", 0, -2.6), ("L1", 1.6, 0), ("Q1", 0, -1.8), ("D1", -1.9, 0),
                               ("U5", 0, -2.2), ("U6", 0, 1.8), ("U7", 0, -2.2), ("J1", 0, 0), ("J2", 0, 0), ("J3", 0, 0),
                               ("J4", 0, 0), ("J5", 2.4, 0), ("C5", 0, -1.6), ("U4", 0, -1.8), ("Q2", -2, 0)])
ax.text(48, 12.5, "BT1: 18650 cell holder (through-hole), top band", ha="center", fontsize=7.5, color=C.mute, zorder=8)
ax.set_title("TW-1 rev B copper by electrical role (top layer solid, bottom layer faint)")
legend(ax, loc="upper center", bbox_to_anchor=(0.5, -0.0), ncol=4)
save(fig, os.path.join(FIG, "layout_map"))

# ---------------------------------------------------------------- power close-up
fig, ax = plt.subplots(figsize=(6.8, 4.1))
draw(ax, 3, 41, 41.5, 62.5, refs=[("U2", 0, -2.6), ("U3", -0.2, -2.2), ("L1", 2.0, 0), ("C6", 0, -1.3), ("C7", 1.9, 0),
                                  ("C8", 1.9, 0), ("C4", 1.5, 0), ("Q1", 0, -1.8), ("D1", -2.3, 0), ("C1", 0, 1.9),
                                  ("C2", 0, 1.9), ("R4", -1.6, 0), ("R5", -1.6, 0), ("U7", 0, -2.2)], ref_size=7.5)
pad = {(p["ref"], p["num"]): p["c"] for p in G["pads"]}
padn = {}
for p in G["pads"]:
    padn.setdefault((p["ref"], p["net"]), p["c"])
loops = [("input loop", [padn[("C6", "VSYS")], pad[("U3", "10")], pad[("U3", "8")], padn[("C6", "GND")]], C.series[4]),
         ("output loop", [pad[("U3", "6")], padn[("C7", "+3V3")], padn[("C7", "GND")], pad[("U3", "8")]], C.series[4])]
for name, pts, c in loops:
    ax.add_patch(Polygon(pts, closed=True, fc=c, alpha=0.18, ec=c, lw=1.0, ls="--", zorder=7))
lm = A["loops_mm2"]
note(ax, (27.4, 45.6), "Buck-boost input loop C6 → VIN → PGND\n%.1f mm²" % lm["Buck-boost input (C6 → VIN → PGND)"], (33.6, 42.6))
note(ax, (29.4, 50.0), "Output loop VOUT → C7/C8 → PGND\n%.1f mm²" % lm["Buck-boost output (VOUT → C7 → PGND)"], (33.4, 56.6))
note(ax, (30.6, 47.4), "Switch node LX1/LX2: %.1f mm² of copper,\nall on L1 over the solid L2 ground" % A["switch_node_copper_mm2"],
     (35.2, 49.6))
pp = {p["net"]: p for p in A["paths"] if p["current_A"]}
note(ax, (17.0, 53.0), "VIN_SOLAR 0.3 mm, %.0f mA max\n%.0f mΩ, %.0f mV, +%.0f °C" % (
    pp["VIN_SOLAR"]["current_A"] * 1e3, pp["VIN_SOLAR"]["r_mohm"], pp["VIN_SOLAR"]["drop_mV"], pp["VIN_SOLAR"]["dT_C"]), (4.6, 60.6))
note(ax, (16.0, 47.6), "U2 pad: 4 thermal vias to L2", (4.4, 43.6))
ax.set_title("Power stage: charger U2, buck-boost U3 and the solar input")
legend(ax, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=4)
save(fig, os.path.join(FIG, "layout_power"))

# ---------------------------------------------------------------- RF close-up
fig, ax = plt.subplots(figsize=(6.8, 4.9))
draw(ax, 51, 83, 46.4, 67.4, refs=[("C14", 2.0, 0), ("L2", 2.0, 0), ("C15", 2.6, 0), ("J5", 3.4, 0)], ref_size=7.5)
rf = A["rf"]
note(ax, (68.6, 51.7), "From the RAK3172 RF pad: %.1f mm in all,\n%.0f° of line at 915 MHz, one bend" % (rf["length_mm"], rf["electrical_length_deg"]), (51.6, 48.0))
note(ax, (67.4, 52.6), "CPWG: %.2f mm trace, 0.20 mm gap to the\nL1 pour, 0.21 mm over solid L2 (Z₀ ≈ 50 Ω)" % rf["width_mm"][0], (51.6, 52.4))
note(ax, (65.6, 57.6), "GND via fence, %.1f mm pitch\n(%s at 915 MHz)" % (rf["fence_pitch_mm"], rf["fence_pitch_vs_lambda_g"]), (51.6, 57.6))
note(ax, (67.4, 54.0), "C14 1.8 pF shunt (module side)", (72.0, 52.4))
note(ax, (66.9, 57.0), "L2 7.5 nH series", (72.0, 56.4))
note(ax, (67.4, 60.0), "C15 not fitted (tuning spare)", (72.0, 60.4))
note(ax, (67.9, 64.2), "U.FL → 150 mm pigtail → SMA bulkhead", (72.0, 65.2))
ax.set_title("RF feed: module to U.FL")
save(fig, os.path.join(FIG, "layout_rf"))
print("layout figures written")
