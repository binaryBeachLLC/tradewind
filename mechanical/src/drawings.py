"""Dimensioned 2D drawings from the CadQuery model (hidden-line-removed projections + true sections).

  python mechanical/src/drawings.py
Writes docs/figures/mech_ga_enclosure, mech_ga_installed, mech_section, mech_mass_table (.svg + .png).
Third-angle projection, units mm.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from common import *  # noqa
import assembly  # noqa
from plotstyle import apply, C, save  # noqa

from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

INK, MUTE = C.ink, C.mute
VIEWS = {  # name: (view direction, screen-x direction)
    "front": ((0, 0, 1), (1, 0, 0)),
    "right": ((1, 0, 0), (0, 0, -1)),
    "bottom": ((0, -1, 0), (1, 0, 0)),
}


def _edges_xy(comp, n=24):
    out = []
    if comp.IsNull():
        return out
    for e in cq.Shape.cast(comp).Edges():
        k = 2 if e.geomType() == "LINE" else max(6, min(n * 3, int(e.Length() / 0.6)))
        pts = [e.positionAt(t) for t in np.linspace(0, 1, k)]
        out.append(np.array([[p.x, p.y] for p in pts]))
    return out


def hlr(shapes, view):
    d, x = VIEWS[view]
    algo = HLRBRep_Algo()
    for s in shapes:
        algo.Add(s.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*d), gp_Dir(*x))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _edges_xy(h.VCompound()) + _edges_xy(h.OutLineVCompound()) + _edges_xy(h.Rg1LineVCompound())
    hid = _edges_xy(h.HCompound()) + _edges_xy(h.OutLineHCompound())
    return vis, hid


def draw(ax, vis, hid, dx=0, dy=0, lw=0.7, hidden=True, color=INK):
    for e in vis:
        ax.plot(e[:, 0] + dx, e[:, 1] + dy, color=color, lw=lw, solid_capstyle="round")
    if hidden:
        for e in hid:
            ax.plot(e[:, 0] + dx, e[:, 1] + dy, color="#9aa3ab", lw=0.35, ls=(0, (2.5, 1.5)))


def dim(ax, p1, p2, off, text, orient="h", fs=7.5, ext=True):
    (x1, y1), (x2, y2) = p1, p2
    kw = dict(color=MUTE, lw=0.5)
    if orient == "h":
        y = max(y1, y2) + off if off > 0 else min(y1, y2) + off
        if ext:
            ax.plot([x1, x1], [y1, y + np.sign(off) * 1.5], **kw)
            ax.plot([x2, x2], [y2, y + np.sign(off) * 1.5], **kw)
        ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<|-|>", color=MUTE, lw=0.5, shrinkA=0, shrinkB=0,
                                                           mutation_scale=6))
        ax.text((x1 + x2) / 2, y + (1.2 if off > 0 else -1.2), text, ha="center", va="bottom" if off > 0 else "top",
                fontsize=fs, color=INK)
    else:
        x = max(x1, x2) + off if off > 0 else min(x1, x2) + off
        if ext:
            ax.plot([x1, x + np.sign(off) * 1.5], [y1, y1], **kw)
            ax.plot([x2, x + np.sign(off) * 1.5], [y2, y2], **kw)
        ax.annotate("", (x, y1), (x, y2), arrowprops=dict(arrowstyle="<|-|>", color=MUTE, lw=0.5, shrinkA=0, shrinkB=0,
                                                           mutation_scale=6))
        ax.text(x + (1.2 if off > 0 else -1.2), (y1 + y2) / 2, text, ha="left" if off > 0 else "right", va="center",
                fontsize=fs, color=INK, rotation=90 if False else 0)


def label(ax, x, y, s, fs=8, bold=True):
    ax.text(x, y, s, fontsize=fs, color=C.teal, fontweight="bold" if bold else "normal", ha="center", va="top")


def titleblock(fig, title, sub):
    fig.text(0.012, 0.985, title, fontsize=11, fontweight="bold", color=C.teal, va="top")
    fig.text(0.012, 0.952, sub, fontsize=7.5, color=MUTE, va="top")
    fig.text(0.988, 0.015, "Tradewind TW-1 · rev B · units mm · third-angle projection · Binary Beach LLC",
             fontsize=6.5, color=MUTE, ha="right")


def by_name(parts):
    return {p.name: p for p in parts}


# ------------------------------------------------------------------ sheet 1: enclosure GA
def sheet_enclosure(parts):
    P = by_name(parts)
    names = ["base", "lid", "lid_screws", "glands_pg7", "sma_bulkhead", "vent_m12"]
    shapes = [P[n].solid() for n in names]
    fig, ax = plt.subplots(figsize=(10.5, 7.6))
    ax.set_aspect("equal"); ax.axis("off")
    # front at (0,0); right view to the right; bottom view below
    fv, fh = hlr(shapes, "front")
    draw(ax, fv, fh, hidden=False)
    RX = 125.0
    rv, rh = hlr(shapes, "right")
    draw(ax, rv, rh, dx=RX, hidden=False)
    BY = -128.0
    bv, bh = hlr(shapes, "bottom")
    draw(ax, bv, bh, dy=BY, hidden=False)
    # front dims
    dim(ax, (-61, 49), (61, 49), 9, "122")
    dim(ax, (-61, -49), (-61, 49), -9, "98", orient="v")
    dim(ax, (-55.5, 43.5), (55.5, 43.5), 4.5, "111 (lid screws)", fs=6.5)
    dim(ax, (55.5, -43.5), (55.5, 43.5), 10, "87", orient="v", fs=6.5)
    hx, hy = b2l(46.0, 35.2)
    ax.annotate("magnet-tap target\n(hall switch U4 below)", (hx, hy), (hx - 40, hy + 22), fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    lx, ly = b2l(52.0, 34.4)
    ax.annotate("Ø3 light pipe (LED D3)", (lx, ly), (lx - 2, ly - 12), fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    # right-view dims: screen x = -z
    zmin, zmax = -FLOOR - MOUNT_BOSS_H, LID_Z1
    dim(ax, (RX - zmax, 49), (RX - zmin, 49), 9, "%.0f" % (zmax - zmin))
    dim(ax, (RX - LID_Z1, -49), (RX - RIM_Z, -49), -20, "%.0f lid" % (LID_Z1 - RIM_Z), fs=6.5)
    dim(ax, (RX - RIM_Z, -49), (RX + FLOOR, -49), -20, "%.0f base" % (RIM_Z + FLOOR), fs=6.5, ext=True)
    dim(ax, (RX + FLOOR, -49), (RX - zmin, -49), -20, "%.0f" % (-zmin - FLOOR), fs=6.5)
    ax.annotate("M12 ePTFE vent", (RX - GLAND_Z, VENT_Y), (RX + 22, VENT_Y - 18), fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    ax.annotate("4 × M4 mounting bosses\n(blind inserts, to pole bracket)", (RX + 6, 30), (RX + 22, 52), fontsize=6.5,
                color=INK, arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    # bottom view dims (screen y = z + BY)
    yb = BY + GLAND_Z
    xs = GLAND_X + [SMA_X]
    for a, b in zip(xs, xs[1:]):
        dim(ax, (a, yb), (b, yb), -24, "%.0f" % (b - a) if b != SMA_X else "%.1f" % (b - a), fs=6.5)
    dim(ax, (-61, yb), (GLAND_X[0], yb), -24, "%.1f" % (GLAND_X[0] + 61), fs=6.5)
    for x, s in zip(xs, ["J1\nSOLAR", "J2\nRAIN", "J3\nSOIL", "J4\nAIR", "ANT"]):
        ax.text(x, BY + LID_Z1 + 4, s, fontsize=6, ha="center", color=INK)
    dim(ax, (66, BY + 0), (66, yb), 4, "%.1f" % GLAND_Z, orient="v", fs=6.5)
    ax.text(70, BY - 2, "4 × PG7 (M12×1.5) glands, Ø12.5\nSMA bulkhead Ø6.4", fontsize=6.5, color=INK, va="top")
    label(ax, -40, -49 - 16, "FRONT (lid)")
    label(ax, RX - 13, -49 - 30, "RIGHT")
    label(ax, 0, BY - 26, "BOTTOM (gland side, viewed from below)")
    ax.set_xlim(-85, 215); ax.set_ylim(-165, 72)
    titleblock(fig, "Enclosure — general arrangement",
               "ASA box + lid, 3 mm walls, 1° draft · IP66 target: 2.5 mm silicone cord, 26 % squeeze · captive M4 lid screws outside the seal")
    save(fig, os.path.join(FIG, "mech_ga_enclosure"), tight=False)


# ------------------------------------------------------------------ sheet 2: installed GA
def sheet_installed(parts):
    skip = {"cable_solar", "cable_probe", "cable_rain", "cable_soil", "ufl_pigtail", "light_pipe", "inserts",
            "panel_busbars", "panel_cells"}
    shapes = [p.solid() for p in parts if p.name not in skip]
    fig, ax = plt.subplots(figsize=(10.5, 7.6))
    ax.set_aspect("equal"); ax.axis("off")
    fv, fh = hlr(shapes, "front")
    draw(ax, fv, fh, hidden=False, lw=0.5)
    RX = 300.0
    rv, rh = hlr(shapes, "right")
    draw(ax, rv, rh, dx=RX, hidden=False, lw=0.5)
    comp = cq.Compound.makeCompound([s for s in shapes])
    bb = comp.BoundingBox()
    bbx = cq.Compound.makeCompound([p.solid() for p in parts if p.group not in ("pole",) and p.name not in skip]).BoundingBox()
    dim(ax, (bbx.xmin, bbx.ymax), (bbx.xmax, bbx.ymax), 12, "%.0f" % bbx.xlen)
    dim(ax, (bbx.xmin, bbx.ymin), (bbx.xmin, bbx.ymax), -12, "%.0f\n(roof to\nantenna tip)" % bbx.ylen, orient="v")
    dim(ax, (0, -200), (SHIELD_X, -200), -10, "%.0f" % SHIELD_X, fs=6.5)
    ax.annotate("Ø%.0f pole (25–50 mm fits)" % POLE_D, (0, -230), (40, -245), fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    ax.annotate("915 MHz whip, points down", (SMA_X, -200), (SMA_X + 12, -192), fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    ax.annotate("radiation shield\n(SHT45 probe inside)", (SHIELD_X + 40, -170), (SHIELD_X + 20, -215), fontsize=6.5,
                color=INK, arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    # right view: tilt + gap
    import roof as R
    yfront = roof_underside_y(LID_Z1)
    dim(ax, (RX - LID_Z1, EXT_H / 2), (RX - LID_Z1, yfront), -4, "", orient="v", fs=6.5)
    ax.annotate("%.0f mm ventilated air gap" % (yfront - EXT_H / 2), (RX - LID_Z1 - 4, (EXT_H / 2 + yfront) / 2),
                (RX - LID_Z1 - 118, EXT_H / 2 - 4), fontsize=6.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    p0 = R.local_to_L(0, ROOF_T + PANEL_T, ROOF_L / 2)
    p1 = R.local_to_L(0, ROOF_T + PANEL_T, -ROOF_L / 2)
    ax.plot([RX - p0[2] - 10, RX - p0[2] + 90], [p0[1], p0[1]], color=MUTE, lw=0.5, ls=(0, (3, 2)))
    ax.text(RX - p0[2] - 12, p0[1] + 2, "%.0f° tilt, panel faces south" % TILT, fontsize=6.5, color=INK, ha="right")
    zr = cq.Compound.makeCompound([s for s in shapes])
    dim(ax, (RX - bb.zmax, bb.ymax), (RX - bb.zmin, bb.ymax), 12, "%.0f" % bb.zlen)
    label(ax, 60, bb.ymin - 8, "FRONT")
    label(ax, RX - 20, bb.ymin - 8, "RIGHT")
    ax.set_xlim(-110, RX + 110); ax.set_ylim(bb.ymin - 30, bb.ymax + 30)
    titleblock(fig, "Installed system — pole mount, sun roof and radiation shield",
               "2 W panel on a ventilated roof (the panel is the box's sunshade) · aluminium bracket, M6 U-bolts · louvred ASA shield on an arm")
    save(fig, os.path.join(FIG, "mech_ga_installed"), tight=False)


# ------------------------------------------------------------------ sheet 3: sections
SECT_COL = {"asa_white": "#e8e6df", "silicone": "#3a3b3d", "steel": "#9aa1a8", "brass": "#c9a14a", "black": "#555",
            "cable": "#333", "clear": "#cfe8f0"}


def section_faces(shape, x):
    plane = cq.Face.makePlane(800, 800, cq.Vector(x, 0, 0), cq.Vector(1, 0, 0))
    bb = shape.BoundingBox()
    if not (bb.xmin - 1e-6 <= x <= bb.xmax + 1e-6):
        return []
    op = BRepAlgoAPI_Common(shape.wrapped, plane.wrapped)
    op.Build()
    if not op.IsDone():
        return []
    r = cq.Shape.cast(op.Shape())
    return r.Faces()


def fill_faces(ax, faces, col, edge=INK, hatch=None, dx=0, scale=1.0, oy=0.0):
    for f in faces:
        try:
            vs, tris = f.tessellate(0.05, 0.2)
        except Exception:
            continue
        pts = np.array([[(-(v.z)) * scale + dx, v.y * scale + oy] for v in vs])
        for t in tris:
            ax.add_patch(Polygon(pts[list(t)], closed=True, facecolor=col, edgecolor=col, lw=0.15, hatch=hatch))
        for e in f.Edges():
            k = 2 if e.geomType() == "LINE" else 24
            q = np.array([[-(e.positionAt(t).z) * scale + dx, e.positionAt(t).y * scale + oy] for t in np.linspace(0, 1, k)])
            ax.plot(q[:, 0], q[:, 1], color=edge, lw=0.45)


def sheet_section(parts):
    P = by_name(parts)
    board = assembly.board_shape()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 6.4), gridspec_kw=dict(width_ratios=[1.0, 0.75]))
    for ax in (a1, a2):
        ax.set_aspect("equal"); ax.axis("off")
    # A-A: through J4's gland and the 18650 cell (x = 23.5)
    xA = GLAND_X[3]
    for n in ("base", "lid", "gasket", "glands_pg7", "pcb_screws", "inserts", "light_pipe"):
        fill_faces(a1, section_faces(P[n].solid(), xA), SECT_COL[P[n].mat], hatch="////" if P[n].mat == "asa_white" else None)
    bcol = {"pcb": "#1d6b3a", "cell": "#1a5c6b", "other": "#7d8790"}
    for s in board.Solids():
        bb = s.BoundingBox()
        if not (bb.xmin <= xA <= bb.xmax):
            continue
        kind = "pcb" if abs(bb.xlen - 96) < 0.5 else ("cell" if bb.zmax > BOARD_Z0 + 18 and bb.ylen < 20 else "other")
        fill_faces(a1, section_faces(s, xA), bcol[kind], edge="#222")
    a1.text(-LID_Z1 - 2, 52, "A–A  (x = %.1f, through J4 gland and the cell)" % xA, fontsize=8, color=C.teal, fontweight="bold")
    callouts = [((-(BOARD_Z0 + 0.8), 0), "PCB 1.6 mm on M3 bosses", (25, 6)),
                ((-(BOARD_Z0 + 11.0), 20.5), "18650 cell (Ø18.4)", (25, 26)),
                ((-(LID_Z1 - 1.5), 0), "lid 3 mm, ribs clear the cell", (-95, 8)),
                ((-(RIM_Z - 1.3), 47.0), "2.5 mm cord in 3.4 × 2.6 groove", (-95, 58)),
                ((-GLAND_Z, -49 - 6), "PG7 gland + locknut", (25, -62)),
                ((-(BOARD_Z0 + 13.6), 0), "", None)]
    for p, s, t in callouts:
        if t:
            a1.annotate(s, p, t, fontsize=6.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTE, lw=0.5))
    dim(a1, (-(BOARD_Z0 + 11 + 9.2), 20.5 + 9.3), (-LID_CEIL, 20.5 + 9.3), 0, "", ext=False)
    a1.text(-(LID_CEIL + 2), 33.5, "%.1f" % (LID_CEIL - 27.21), fontsize=6.5, color=INK)
    a1.set_xlim(-60, 45); a1.set_ylim(-75, 60)
    # B-B detail: through the lid screw (x = 55.5), 2.5x
    xB, S = LID_SCREWS[3][0], 2.5
    oy = -43.5 * S
    for n in ("base", "lid", "gasket", "lid_screws", "inserts", "vent_m12"):
        fill_faces(a2, section_faces(P[n].solid(), xB), SECT_COL[P[n].mat], scale=S, oy=-oy * 0 - 43.5 * S * 0,
                   hatch="////" if P[n].mat == "asa_white" else None)
    a2.set_xlim(-(LID_Z1 + 2) * S, -(RIM_Z - 12) * S)
    a2.set_ylim(35 * S, 50.5 * S)
    a2.text(-(LID_Z1 + 2) * S, 51.2 * S, "B–B  detail ×2.5 (x = %.1f, lid screw)" % xB, fontsize=8, color=C.teal,
            fontweight="bold")
    notes = ["M4×12 stainless socket head, captive (nylon washer)",
             "M4 brass heat-set insert, 6.4 mm, in the corner column",
             "screw sits outside the seal: no leak path",
             "tongue 1.6 × 0.75 → cord squeezed 26 %, groove fill 78 %"]
    for i, s in enumerate(notes):
        a2.text(0.0, -0.10 - i * 0.07, "• " + s, fontsize=6.5, color=INK, transform=a2.transAxes)
    titleblock(fig, "Sections", "Cut faces hatched; PCB green, cell teal, steel grey, brass gold, silicone dark")
    save(fig, os.path.join(FIG, "mech_section"), tight=False)


# ------------------------------------------------------------------ sheet 4: mass / volume table
def sheet_table():
    r = json.load(open(os.path.join(MECH, "results.json")))
    g = r["mass_g"]["by_group"]
    rows = [("Box (base + lid)", g.get("base", 0) + g.get("lid", 0), "ASA, printed (molded later)"),
            ("Gasket, inserts, screws, vent, light pipe", g.get("gasket", 0) + g.get("inserts", 0) + g.get("screws", 0) + g.get("vent", 0) + g.get("light_pipe", 0), "silicone / brass / A2 steel"),
            ("Glands, SMA + whip antenna, U.FL pigtail", g.get("glands", 0) + g.get("antenna", 0), "PA66 / brass"),
            ("Board assembly + protected 18650", g.get("board_assembly_est", 0) + g.get("cell_18650_protected", 0), "estimate"),
            ("Sun roof + gussets", g.get("roof", 0) + g.get("roof_gussets", 0), "ASA + 5052 Al"),
            ("Solar panel 2 W", g.get("panel", 0), "epoxy-encapsulated mono"),
            ("Radiation shield + rods + probe", g.get("shield", 0) + g.get("shield_hw", 0) + g.get("probe", 0), "ASA / A2 / sintered SS"),
            ("Bracket, saddles, U-bolts", g.get("bracket", 0) + g.get("bracket_hw", 0), "5052 Al / A2"),
            ("Cables (stubs as drawn)", g.get("cables", 0), "PUR")]
    tot = sum(x[1] for x in rows)
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    ax.axis("off")
    cell = [[a, "%.0f" % b, c] for a, b, c in rows] + [["Total installed (excl. pole)", "%.0f" % tot, ""]]
    t = ax.table(cellText=cell, colLabels=["Group", "Mass (g)", "Material"], loc="upper left",
                 colWidths=[0.5, 0.14, 0.36], cellLoc="left")
    t.auto_set_font_size(False); t.set_fontsize(7.5); t.scale(1, 1.25)
    for (i, j), c in t.get_celld().items():
        c.set_edgecolor(C.line)
        if i == 0:
            c.set_facecolor(C.cream); c.get_text().set_color(C.teal); c.get_text().set_fontweight("bold")
        if i == len(cell):
            c.get_text().set_fontweight("bold")
    v = r["internal_volume_cm3"]; d = r["dimensions_mm"]
    ax.text(0, -0.06, "Box %s mm · internal volume %.0f cm³ gross, %.0f cm³ free after the PCBA · print time ≈ %.1f h (all printed parts)"
            % (" × ".join("%.0f" % x for x in d["box_w_h_d"]), v["gross"], v["free_after_pcba"], r["print_time_h_total"]),
            fontsize=7, color=MUTE, transform=ax.transAxes)
    save(fig, os.path.join(FIG, "mech_mass_table"))


if __name__ == "__main__":
    apply()
    parts = assembly.all_parts()
    sheet_enclosure(parts)
    sheet_installed(parts)
    sheet_section(parts)
    sheet_table()
    print("drawings written")
