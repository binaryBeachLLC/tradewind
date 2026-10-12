"""Measure the routed rev B board: copper per net, current paths, hot loops, RF line, separations.

Run inside KiCad's Python:  snap run --shell kicad.kicad-cli -c "python3 tools/layout_audit.py"
Writes hardware/fab/layout_audit.json (numbers for the report) and hardware/fab/layout_geometry.json
(tracks, vias, pads and the top GND pour, for tools/layout_figs.py). Nothing on the board is changed.
"""
import collections
import heapq
import json
import math
import os
import sys

sys.path.insert(0, "/snap/kicad/current/usr/lib/python3/dist-packages")
import pcbnew  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.path.join(HERE, "..", "hardware", "fab")
PCB = os.path.join(HERE, "..", "hardware", "tradewind", "tradewind.kicad_pcb")
OX, OY = 100.0, 100.0
RHO = 1.72e-8                                   # copper at 20 °C, Ω·m
T_CU = {"F.Cu": 35e-6, "B.Cu": 35e-6, "In1.Cu": 15.2e-6, "In2.Cu": 15.2e-6}
VIA_R = 0.0012                                  # 0.3 mm drill, ~18 µm plating, 1.6 mm barrel (Ω)

b = pcbnew.LoadBoard(PCB)
b.BuildConnectivity()
mm = pcbnew.ToMM


def xy(p):
    return (round(mm(p.x) - OX, 4), round(mm(p.y) - OY, 4))


def short(net):
    return net.split("/")[-1]


# ------------------------------------------------------------------ geometry dump
tracks, vias, pads, fps = [], [], [], []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias.append(dict(p=xy(t.GetPosition()), d=mm(t.GetWidth(pcbnew.F_Cu)), drill=mm(t.GetDrillValue()), net=short(t.GetNetname())))
    else:
        tracks.append(dict(a=xy(t.GetStart()), b=xy(t.GetEnd()), w=mm(t.GetWidth()), layer=b.GetLayerName(t.GetLayer()),
                           net=short(t.GetNetname())))
for fp in b.GetFootprints():
    fps.append(dict(ref=fp.GetReference(), p=xy(fp.GetPosition()), rot=fp.GetOrientationDegrees(), dnp=fp.IsDNP()))
    for pd in fp.Pads():
        poly = pcbnew.SHAPE_POLY_SET()
        pd.TransformShapeToPolygon(poly, pcbnew.F_Cu if pd.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu, 0, 5000,
                                   pcbnew.ERROR_INSIDE)
        pts = []
        if poly.OutlineCount():
            o = poly.Outline(0)
            pts = [xy(o.CPoint(i)) for i in range(o.PointCount())]
        pads.append(dict(ref=fp.GetReference(), num=pd.GetNumber(), net=short(pd.GetNetname()), c=xy(pd.GetPosition()),
                         poly=pts, pth=pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH))
pour = []
for z in b.Zones():
    if z.GetZoneName() == "GND_F":
        fl = z.GetFilledPolysList(pcbnew.F_Cu)
        for i in range(fl.OutlineCount()):
            o = fl.Outline(i)
            pour.append([xy(o.CPoint(k)) for k in range(o.PointCount())])
            for h in range(fl.HoleCount(i)):
                hh = fl.Hole(i, h)
                pour.append([xy(hh.CPoint(k)) for k in range(hh.PointCount())])
outline = []
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        if d.GetShape() == pcbnew.SHAPE_T_POLY:
            ps = d.GetPolyShape().Outline(0)
            outline.append([xy(ps.CPoint(i)) for i in range(ps.PointCount())] + [xy(ps.CPoint(0))])
        elif d.GetShape() == pcbnew.SHAPE_T_ARC:
            c, r = d.GetCenter(), d.GetRadius()
            a0, a1 = d.GetArcAngleStart().AsDegrees(), d.GetArcAngle().AsDegrees()
            outline.append([xy(pcbnew.VECTOR2I(int(c.x + r * math.cos(math.radians(a0 + a1 * k / 8))),
                                               int(c.y + r * math.sin(math.radians(a0 + a1 * k / 8))))) for k in range(9)])
        else:
            outline.append([xy(d.GetStart()), xy(d.GetEnd())])
json.dump(dict(tracks=tracks, vias=vias, pads=pads, footprints=fps, pour_f=pour, outline=outline),
          open(os.path.join(FAB, "layout_geometry.json"), "w"))

# ------------------------------------------------------------------ copper per net
nc = b.GetDesignSettings().m_NetSettings
per_net = collections.defaultdict(lambda: dict(length_mm=collections.Counter(), widths=set(), vias=0))
for t in tracks:
    s = per_net[t["net"]]; s["length_mm"][t["layer"]] += math.dist(t["a"], t["b"]); s["widths"].add(t["w"])
for v in vias:
    per_net[v["net"]]["vias"] += 1
nets = {}
for n, s in per_net.items():
    nets[n] = dict(length_mm={k: round(v, 1) for k, v in s["length_mm"].items()}, widths_mm=sorted(s["widths"]),
                   vias=s["vias"])
b_cu_nets = sorted(n for n, s in nets.items() if s["length_mm"].get("B.Cu", 0) > 0.5 and n != "GND")


# ------------------------------------------------------------------ current paths (graph of copper, Dijkstra on resistance)
def pad_of(ref, num):
    for p in pads:
        if p["ref"] == ref and p["num"] == num:
            return p
    raise KeyError((ref, num))


def inside(pt, poly):
    x, y = pt; c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            c = not c
    return c


def path(net, a, bpad):
    """Lowest-resistance copper path between two pads on one net (tracks + vias; pours ignored)."""
    G = collections.defaultdict(list)
    key = lambda p, l: (round(p[0], 3), round(p[1], 3), l)
    segs = []
    raw = [t for t in tracks if t["net"] == net]
    ends = [(t["a"], t["layer"]) for t in raw] + [(t["b"], t["layer"]) for t in raw]
    for t in raw:   # split segments where another track tees into their middle
        L = math.dist(t["a"], t["b"])
        cut = [0.0, 1.0]
        for p, l in ends:
            if l != t["layer"] or L == 0:
                continue
            u = ((p[0] - t["a"][0]) * (t["b"][0] - t["a"][0]) + (p[1] - t["a"][1]) * (t["b"][1] - t["a"][1])) / L ** 2
            q = (t["a"][0] + u * (t["b"][0] - t["a"][0]), t["a"][1] + u * (t["b"][1] - t["a"][1]))
            if 1e-4 < u < 1 - 1e-4 and math.dist(p, q) < t["w"] / 2:
                cut.append(u)
        cut.sort()
        pts = [(t["a"][0] + u * (t["b"][0] - t["a"][0]), t["a"][1] + u * (t["b"][1] - t["a"][1])) for u in cut]
        for a2, b2 in zip(pts, pts[1:]):
            segs.append(dict(t, a=a2, b=b2))
    for t in segs:
        r = RHO * math.dist(t["a"], t["b"]) * 1e-3 / (t["w"] * 1e-3 * T_CU[t["layer"]])
        u, v = key(t["a"], t["layer"]), key(t["b"], t["layer"])
        G[u].append((v, r, math.dist(t["a"], t["b"]), t["w"])); G[v].append((u, r, math.dist(t["a"], t["b"]), t["w"]))
    for v in vias:
        if v["net"] != net:
            continue
        ends = [n for n in list(G) if n[0] != "pad" and math.dist(n[:2], v["p"]) < v["d"] / 2 + 1e-3]
        for i in ends:
            for j in ends:
                if i != j and i[2] != j[2]:
                    G[i].append((j, VIA_R, 0, None))
    for name, p in (("A", a), ("B", bpad)):
        node = ("pad", name)
        for n in [k for k in G if k[0] != "pad"]:
            if inside(n[:2], p["poly"]) or math.dist(n[:2], p["c"]) < 0.05:
                G[node].append((n, 0, 0, None)); G[n].append((node, 0, 0, None))
    dist, prev = {("pad", "A"): (0, 0, None)}, {}
    q = [(0, 0, ("pad", "A"))]
    seen = set()
    while q:
        r, L, u = heapq.heappop(q)
        if u in seen:
            continue
        seen.add(u)
        if u == ("pad", "B"):
            break
        for v, dr, dl, w in G[u]:
            nr = r + dr
            if v not in dist or nr < dist[v][0]:
                dist[v] = (nr, L + dl, w); prev[v] = u
                heapq.heappush(q, (nr, L + dl, v))
    if ("pad", "B") not in dist:
        return None
    r, L, _ = dist[("pad", "B")]
    nvias, minw, u = 0, 9, ("pad", "B")
    while u in prev:
        p = prev[u]
        if u[0] != "pad" and p[0] != "pad" and u[2] != p[2]:
            nvias += 1
        for v, dr, dl, w in G[p]:
            if v == u and w:
                minw = min(minw, w)
        u = p
    return dict(length_mm=round(L, 1), r_mohm=round(r * 1e3, 1), vias=nvias, min_width_mm=minw)


def pad_net(ref, net):
    for p in pads:
        if p["ref"] == ref and p["net"] == net:
            return p
    raise KeyError((ref, net))


# (label, net, from pad, to pad, worst-case DC current A, why)
PATHS = [
    ("Panel in → reverse FET", "SOLAR_RAW", pad_of("J1", "1"), pad_net("Q1", "SOLAR_RAW"), 0.44, "panel Isc at STC"),
    ("Reverse FET → charger IN", "VIN_SOLAR", pad_net("Q1", "VIN_SOLAR"), pad_of("U2", "13"), 0.475, "USB500 input limit"),
    ("Charger BAT → cell +", "VBAT", pad_of("U2", "2"), pad_of("BT1", "1"), 0.50, "ISET charge current"),
    ("Charger IN → input cap C2", "VIN_SOLAR", pad_of("U2", "13"), pad_net("C2", "VIN_SOLAR"), 0.0, "local decoupling"),
    ("Charger BAT → BAT cap C5", "VBAT", pad_of("U2", "2"), pad_net("C5", "VBAT"), 0.0, "local decoupling"),
    ("Charger OUT → buck-boost VIN", "VSYS", pad_of("U2", "10"), pad_of("U3", "10"), 0.12, "TX burst at 3.0 V in"),
    ("Charger OUT → OUT cap C4", "VSYS", pad_of("U2", "10"), pad_net("C4", "VSYS"), 0.0, "local decoupling"),
    ("Buck-boost VIN → input cap C6", "VSYS", pad_of("U3", "10"), pad_net("C6", "VSYS"), 0.0, "hot-loop decoupling"),
    ("Cell + → sense switch Q2", "VBAT", pad_of("BT1", "1"), pad_net("Q2", "VBAT"), 0.0, "sense only (3 nA)"),
]
paths = []
for label, net, a, bb, amps, why in PATHS:
    r = path(net, a, bb)
    if r is None:
        print("no path", label); continue
    r.update(label=label, net=net, from_=a["ref"] + "." + a["num"], to=bb["ref"] + "." + bb["num"], current_A=amps, basis=why,
             drop_mV=round(r["r_mohm"] * amps, 1))
    # IPC-2221 external-layer curve for the narrowest section: ΔT = (I / (k·A^0.725))^(1/0.44), A in mil²
    A = (r["min_width_mm"] / 0.0254) * (35 / 25.4)
    r["dT_C"] = round((amps / (0.048 * A ** 0.725)) ** (1 / 0.44), 2) if amps else 0.0
    r["ampacity_10C_A"] = round(0.048 * 10 ** 0.44 * A ** 0.725, 2)
    paths.append(r)


# ------------------------------------------------------------------ hot loops and separations
def poly_area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def c(ref, net):
    return pad_net(ref, net)["c"]


loops = {
    "Buck-boost input (C6 → VIN → PGND)": [c("C6", "VSYS"), pad_of("U3", "10")["c"], pad_of("U3", "8")["c"], c("C6", "GND")],
    "Buck-boost output (VOUT → C7 → PGND)": [pad_of("U3", "6")["c"], c("C7", "+3V3"), c("C7", "GND"), pad_of("U3", "8")["c"]],
    "Charger output (OUT → C4 → GND)": [pad_of("U2", "10")["c"], c("C4", "VSYS"), c("C4", "GND"), pad_of("U2", "8")["c"]],
    "Module supply (C12 → VDD → GND)": [c("C12", "+3V3"), pad_of("U1", "24")["c"], pad_of("U1", "23")["c"], c("C12", "GND")],
}
loops = {k: round(poly_area(v), 2) for k, v in loops.items()}


def copper_of(net):
    pts = [p["c"] for p in pads if p["net"] == net]
    for t in tracks:
        if t["net"] == net:
            n = max(2, int(math.dist(t["a"], t["b"]) / 0.2))
            pts += [(t["a"][0] + (t["b"][0] - t["a"][0]) * k / n, t["a"][1] + (t["b"][1] - t["a"][1]) * k / n) for k in range(n + 1)]
    return pts


def sep(n1, n2):
    A, B = copper_of(n1), copper_of(n2)
    return round(min(math.dist(a, q) for a in A for q in B), 1)


swn = copper_of("LX1") + copper_of("LX2")
def sep_sw(net):
    return round(min(math.dist(a, q) for a in swn for q in copper_of(net)), 1)


fp_at = {f["ref"]: f["p"] for f in fps}
separations = {
    "Switch node → RF line": sep_sw("RF_MOD"),
    "Switch node → U.FL (J5)": round(min(math.dist(a, fp_at["J5"]) for a in swn), 1),
    "Switch node → SHT40 (U5)": round(min(math.dist(a, fp_at["U5"]) for a in swn), 1),
    "Switch node → soil ADC net": sep_sw("SOIL_ADC"),
    "Switch node → battery ADC net": sep_sw("VBAT_ADC"),
    "Switch node → solar sense net": sep_sw("SOLAR_SENSE"),
    "Switch node → external I²C": min(sep_sw("SDA_EXT"), sep_sw("SCL_EXT")),
    "Charger U2 → SHT40 U5": round(math.dist(fp_at["U2"], fp_at["U5"]), 1),
    "Module U1 → SHT40 U5": round(math.dist(fp_at["U1"], fp_at["U5"]), 1),
}
sw_area = 0.0
for t in tracks:
    if t["net"] in ("LX1", "LX2"):
        sw_area += math.dist(t["a"], t["b"]) * t["w"]
for p in pads:
    if p["net"] in ("LX1", "LX2") and p["poly"]:
        sw_area += poly_area(p["poly"])

# RF line
rf = [t for t in tracks if t["net"] in ("RF_MOD", "RF_ANT")]
fence = sorted(v["p"] for v in vias if v["net"] == "GND" and 65 < v["p"][0] < 69 and 51 < v["p"][1] < 62)
left = sorted(p[1] for p in fence if p[0] < 66.5)
right = sorted(p[1] for p in fence if p[0] > 66.5)
rf_info = dict(fence_left=len(left), fence_right=len(right), length_mm=round(sum(math.dist(t["a"], t["b"]) for t in rf), 1), width_mm=sorted({t["w"] for t in rf}),
               layer=sorted({t["layer"] for t in rf}), fence_vias=len(fence),
               fence_pitch_mm=round(min(b2 - a2 for a2, b2 in zip(left, left[1:])), 2) if len(left) > 1 else None,
               bends=sum(1 for t1, t2 in zip(rf, rf[1:]) if t1["net"] == t2["net"]
                         and abs(math.atan2(t1["b"][1] - t1["a"][1], t1["b"][0] - t1["a"][0])
                                 - math.atan2(t2["b"][1] - t2["a"][1], t2["b"][0] - t2["a"][0])) > 0.1))
lam_g = 299.792458 / 915 / math.sqrt(3.14) * 1000   # guided wavelength (mm), εeff from sim/rf_match.py
rf_info["electrical_length_deg"] = round(rf_info["length_mm"] / lam_g * 360, 1)
rf_info["fence_pitch_vs_lambda_g"] = "λg/%d" % round(lam_g / rf_info["fence_pitch_mm"]) if rf_info["fence_pitch_mm"] else None

via_sizes = collections.Counter((v["d"], v["drill"]) for v in vias)
u2_ep = sum(1 for v in vias if v["net"] == "GND" and abs(v["p"][0] - 16.0) < 0.9 and abs(v["p"][1] - 47.6) < 0.9)
u3_ep = sum(1 for p in pads if p["ref"] == "U3" and p["pth"])

out = dict(
    board=dict(size_mm=[96, 70], layers=4, footprints=len(fps), pads=len(pads), tracks=len(tracks), vias=len(vias),
               via_sizes={"%.2f/%.2f" % k: n for k, n in sorted(via_sizes.items())},
               track_length_mm={l: round(sum(math.dist(t["a"], t["b"]) for t in tracks if t["layer"] == l), 0)
                                for l in ("F.Cu", "B.Cu")},
               gnd_vias=sum(1 for v in vias if v["net"] == "GND"), p3v3_vias=sum(1 for v in vias if v["net"] == "+3V3"),
               u2_thermal_vias=u2_ep, u3_thermal_vias=u3_ep),
    netclasses={n: nc.GetEffectiveNetClass(n).GetName() for n in [x.GetNetname() for x in b.GetNetInfo().NetsByName().values()] if n},
    nets=nets, b_cu_nets=b_cu_nets, paths=paths, loops_mm2=loops, separations_mm=separations,
    switch_node_copper_mm2=round(sw_area, 2), rf=rf_info,
)
json.dump(out, open(os.path.join(FAB, "layout_audit.json"), "w"), indent=1, default=list)
print(json.dumps({k: out[k] for k in ("board", "paths", "loops_mm2", "separations_mm", "switch_node_copper_mm2", "rf", "b_cu_nets")},
                 indent=1, default=list))
