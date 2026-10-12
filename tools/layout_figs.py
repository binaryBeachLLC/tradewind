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
from matplotlib.patches import Circle, Polygon, Patch, Rectangle  # noqa: E402
import matplotlib.patheffects as pe  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from plotstyle import apply, C, save  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
G = json.load(open(os.path.join(ROOT, "hardware", "fab", "layout_geometry.json")))
A = json.load(open(os.path.join(ROOT, "hardware", "fab", "layout_audit.json")))
FIG = os.path.join(ROOT, "docs", "figures")
apply()

ROLE = [  # (name, color, nets) — fixed categorical order
    ("RF, 50 Ω", C.series[0], {"RF_MOD", "RF_ANT"}),
    ("Power, high current", C.series[1], {"SOLAR_RAW", "VIN_SOLAR", "VBAT", "VSYS"}),
    ("Analog, config", C.series[2], {"VBAT_ADC", "SOIL_ADC", "SOLAR_SENSE", "AUX_ADC", "TS", "ISET", "ILIM",
                                               "CFG1", "CFG2", "CFG3", "VBAT_SW", "VBAT_GATE"}),
    ("Off-board, ESD", C.series[3], {"SDA_EXT", "SCL_EXT", "SOIL_EXT", "RAIN_EXT", "+3V3_EXT", "+3V3_SW"}),
    ("Switch node", C.series[4], {"LX1", "LX2"}),
]
P3V3, GND_C, DIG, POUR, EDGE = "#4f5a64", "#c3c9ce", "#9aa3ab", "#e9eef0", "#1f2328"


def color(net):
    for _, c, s in ROLE:
        if net in s:
            return c
    return {"+3V3": P3V3, "GND": GND_C}.get(net, DIG)


def draw(ax, x0, x1, y0, y1, pour=True, bottom=True):
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
    return ppm


def legend(ax, **kw):
    h = [Patch(color=c, label=n) for n, c, _ in ROLE] + [Patch(color=P3V3, label="+3V3"), Patch(color=GND_C, label="GND"),
                                                          Patch(color=DIG, label="Digital, slow")]
    ax.figure.legend(handles=h, fontsize=9, frameon=False, ncol=4, handlelength=1.4, columnspacing=1.2, **kw)


# Part outlines come from the pad extents in the board file, so a label always sits on the part it names.
BB = {}
for _p in G["pads"]:
    _b = BB.setdefault(_p["ref"], [1e9, 1e9, -1e9, -1e9])
    for _x, _y in _p["poly"]:
        _b[:] = [min(_b[0], _x), min(_b[1], _y), max(_b[2], _x), max(_b[3], _y)]
HALO = [pe.withStroke(linewidth=2.6, foreground="white")]


def tag(ax, ref, side="n", off=0.5, size=9, grow=0.35):
    """Outline the part (its pads + `grow` mm) and put its designator against the outline, `off` mm out on `side`."""
    x0, y0, x1, y1 = BB[ref]
    x0, y0, x1, y1 = x0 - grow, y0 - grow, x1 + grow, y1 + grow
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=C.ink, lw=1.0, zorder=7))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    xy, ha, va, edge = {"n": ((cx, y0 - off), "center", "bottom", (cx, y0)), "s": ((cx, y1 + off), "center", "top", (cx, y1)),
                        "e": ((x1 + off, cy), "left", "center", (x1, cy)), "w": ((x0 - off, cy), "right", "center", (x0, cy))}[side]
    if off > 0.9:
        ax.plot(*zip(edge, xy), color=C.ink, lw=0.7, zorder=7)
    ax.text(*xy, ref, fontsize=size, color=C.ink, ha=ha, va=va, zorder=8, weight="semibold", path_effects=HALO)


def mid(net, longest=True, within=None):
    """Midpoint of the longest top-layer segment of `net` (inside `within` = (x0, x1, y0, y1) if given)."""
    seg = [t for t in G["tracks"] if t["net"] == net and t["layer"] == "F.Cu"]
    if within:
        x0, x1, y0, y1 = within
        seg = [t for t in seg if all(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in (t["a"], t["b"]))]
    t = max(seg, key=lambda t: (t["a"][0] - t["b"][0]) ** 2 + (t["a"][1] - t["b"][1]) ** 2)
    return ((t["a"][0] + t["b"][0]) / 2, (t["a"][1] + t["b"][1]) / 2)


MARK = dict(boxstyle="circle,pad=0.22", fc=C.ink, ec="white", lw=1.0)


def mark(ax, xy, n, at=None):
    """Numbered marker on a feature; `at` moves the marker off the feature with a short leader to a dot on it."""
    if at:
        ax.plot(*zip(xy, at), color=C.ink, lw=0.8, zorder=9)
        ax.plot([xy[0]], [xy[1]], "o", ms=3.4, color=C.ink, mec="white", mew=0.8, zorder=10)
    ax.text(*(at or xy), str(n), fontsize=8.5, color="white", weight="bold", ha="center", va="center", bbox=MARK, zorder=11)


KEYS = {}


def key(name, items):
    """The numbered key is set as text in the report (docs/figures/layout_keys.json), at body size."""
    KEYS[name] = items


def board_axes(fig, rect, title=None):
    """Board view; close-ups carry no title (the report caption names them)."""
    ax = fig.add_axes(rect)
    ax.set_anchor("N")
    if title:
        fig.text(0.02, 0.985, title, fontsize=11, weight="semibold", color=C.ink, va="top")
    return ax


# ---------------------------------------------------------------- whole board
fig = plt.figure(figsize=(6.8, 5.6))
ax = board_axes(fig, [0.01, 0.12, 0.98, 0.81], "TW-1 rev B copper by electrical role (top layer solid, bottom layer faint)")
draw(ax, -1, 97, -1.5, 71)
for ref, side in [("U1", "s"), ("U2", "n"), ("U3", "n"), ("L1", "e"), ("Q1", "n"), ("D1", "w"), ("Q2", "w"), ("U4", "n"),
                  ("U5", "w"), ("U6", "e"), ("U7", "n"), ("C5", "n"), ("J1", "n"), ("J2", "n"), ("J3", "n"), ("J4", "n"),
                  ("J5", "e"), ("J6", "e")]:
    tag(ax, ref, side)
ax.text(48, 20.5, "BT1: 18650 cell holder (through-hole) across the top band", ha="center", fontsize=9, color=C.mute, zorder=8)
legend(ax, loc="lower center", bbox_to_anchor=(0.5, 0.0))
save(fig, os.path.join(FIG, "layout_map"), tight=False)

# ---------------------------------------------------------------- power close-up
fig = plt.figure(figsize=(6.8, 3.95))
ax = board_axes(fig, [0.01, 0.165, 0.98, 0.83])
draw(ax, 4, 42, 41.6, 60.2)
for ref, side in [("U2", "n"), ("U3", "w"), ("L1", "e"), ("C6", "n"), ("C7", "e"), ("C8", "e"), ("C4", "w"), ("Q1", "s"),
                  ("D1", "w"), ("C1", "s"), ("C2", "s"), ("R4", "w"), ("R5", "w"), ("U7", "n")]:
    tag(ax, ref, side, 0.4)
pad = {(p["ref"], p["num"]): p["c"] for p in G["pads"]}
padn = {}
for p in G["pads"]:
    padn.setdefault((p["ref"], p["net"]), p["c"])
loops = [[padn[("C6", "VSYS")], pad[("U3", "10")], pad[("U3", "8")], padn[("C6", "GND")]],
         [pad[("U3", "6")], padn[("C7", "+3V3")], padn[("C7", "GND")], pad[("U3", "8")]]]
for pts in loops:
    ax.add_patch(Polygon(pts, closed=True, fc=C.series[4], alpha=0.30, ec=C.series[4], lw=1.4, ls="--", zorder=7))
cen = [tuple(sum(c) / len(pts) for c in zip(*pts)) for pts in loops]
lx = [p["c"] for p in G["pads"] if p["net"] in ("LX1", "LX2") and p["ref"] == "L1"]
u2c = ((BB["U2"][0] + BB["U2"][2]) / 2, (BB["U2"][1] + BB["U2"][3]) / 2)
lm = A["loops_mm2"]
pp = {p["net"]: p for p in A["paths"] if p["current_A"]}
mark(ax, cen[0], 1, at=(33.6, 43.0))
mark(ax, cen[1], 2)
mark(ax, tuple(sum(c) / len(lx) for c in zip(*lx)), 3, at=(34.6, 46.0))
mark(ax, mid("VIN_SOLAR", within=(10, 20, 52, 54)), 4)
mark(ax, u2c, 5, at=(12.4, 44.0))
key("layout_power", ["Buck-boost input loop C6 → U3 VIN → PGND: %.1f mm² (keep this one smallest)" % lm["Buck-boost input (C6 → VIN → PGND)"],
          "Buck-boost output loop U3 VOUT → C7 → PGND: %.1f mm²" % lm["Buck-boost output (VOUT → C7 → PGND)"],
          "Switch node LX1/LX2: %.1f mm² of copper, all on L1 over the solid L2 ground" % A["switch_node_copper_mm2"],
          "VIN_SOLAR, 0.3 mm, %.0f mA max: %.0f mΩ, %.0f mV drop, +%.0f °C" % (
              pp["VIN_SOLAR"]["current_A"] * 1e3, pp["VIN_SOLAR"]["r_mohm"], pp["VIN_SOLAR"]["drop_mV"], pp["VIN_SOLAR"]["dT_C"]),
          "U2 thermal pad: %d vias into the L2 ground plane" % A["board"]["u2_thermal_vias"]])
legend(ax, loc="lower center", bbox_to_anchor=(0.5, 0.0))
save(fig, os.path.join(FIG, "layout_power"), tight=False)

# ---------------------------------------------------------------- RF close-up
fig = plt.figure(figsize=(6.8, 4.15))
ax = board_axes(fig, [0.01, 0.01, 0.98, 0.98])
draw(ax, 53, 83, 48.6, 67.3)
for ref, label in [("C14", "C14  1.8 pF shunt to GND"), ("L2", "L2  7.5 nH series"),
                   ("C15", "C15  not fitted (tuning spare)"), ("J5", "J5  U.FL → 150 mm pigtail → SMA")]:
    tag(ax, ref, "e", 0.4, size=9.5, grow=0.25)
    ax.texts[-1].set_text(label)
rf = A["rf"]
fv = sorted((v["p"] for v in G["vias"] if v["net"] == "GND" and 65 < v["p"][0] < 66.5 and 51 < v["p"][1] < 62), key=lambda p: p[1])
mark(ax, pad[("U1", "12")], 1, at=(71.2, 49.6))
mark(ax, mid("RF_ANT"), 2, at=(63.4, 61.6))
mark(ax, fv[len(fv) // 2], 3, at=(62.0, 57.0))
key("layout_rf", ["RAK3172 RF pad: %.1f mm of line to the U.FL, %.0f° at 915 MHz, one bend" % (rf["length_mm"], rf["electrical_length_deg"]),
          "CPWG: %.2f mm trace, 0.20 mm gap to the L1 pour, 0.21 mm over solid L2 (Z₀ ≈ 50 Ω)" % rf["width_mm"][0],
          "GND via fence both sides, %.1f mm pitch (%s at 915 MHz)" % (rf["fence_pitch_mm"], rf["fence_pitch_vs_lambda_g"])])
save(fig, os.path.join(FIG, "layout_rf"), tight=False)
json.dump(KEYS, open(os.path.join(FIG, "layout_keys.json"), "w"), indent=1, ensure_ascii=False)
print("layout figures written")
