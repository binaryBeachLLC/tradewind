"""Build the Tradewind rev B board (placement, outline, stackup, planes, RF pre-route) from tools/design.py.

Run inside KiCad's Python:  snap run --shell kicad.kicad-cli -c "python3 tools/gen_pcb.py place"
Stages:
  place  -> hardware/tradewind/tradewind.kicad_pcb with footprints, nets, outline, planes, RF trace, silk
  dsn    -> hardware/tradewind/tradewind.dsn for Freerouting (inner layers marked as planes)
  ses    -> import Freerouting's .ses, add GND pours on outer layers + stitching vias, refill zones
Footprints carry the schematic symbol path, so DRC's schematic-parity check ties board and schematic together.
"""
import math
import os
import re
import sys

sys.path.insert(0, "/snap/kicad/current/usr/lib/python3/dist-packages")
import pcbnew  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
import design  # noqa: E402
import gen_schematic as gs  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(HERE, "..", "hardware", "tradewind")
PCB = os.path.join(HW, "tradewind.kicad_pcb")
FPD = "/snap/kicad/current/usr/share/kicad/footprints/"
OX, OY = 100.0, 100.0          # board origin on the KiCad page
W, H, RC = 96.0, 70.0, 3.0     # outline and corner radius (mm)
MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


# ------------------------------------------------------------------ placement (board mm, y down, rot deg CCW)
PLACE = {
    # mechanical
    "H1": (4, 4, 0), "H2": (92, 4, 0), "H3": (4, 66, 0), "H4": (92, 66, 0),
    "FID1": (10, 33.2, 0), "FID2": (86, 33.2, 0), "FID3": (62.0, 67.6, 0),
    # battery band
    "BT1": (48, 19.5, 0), "RT1": (38.0, 32.4, 90), "C5": (79.5, 32.6, 0), "TP3": (83.0, 32.6, 0),
    # field connectors, openings face the bottom edge
    "J1": (13, 64.6, 0), "J2": (24.6, 64.6, 0), "J3": (37.2, 64.6, 0), "J4": (52.4, 64.6, 0),
    # solar input + protection
    "D1": (9.2, 55.6, 90), "Q1": (14.6, 55.4, 0), "R1": (17.6, 55.4, 90), "C1": (19.6, 56.2, 90),
    "C2": (22.2, 56.2, 90), "TP5": (18.8, 58.9, 0),
    "R2": (6.0, 47.8, 90), "R3": (7.4, 47.8, 90), "C3": (8.8, 47.8, 90),
    # charger
    "U2": (16.0, 47.6, 0), "R4": (11.6, 49.6, 0), "R5": (11.6, 50.7, 0), "C4": (21.0, 44.6, 90),
    "R15": (19.6, 51.0, 0), "R16": (19.6, 52.2, 0),
    # buck-boost
    "U3": (27.6, 47.4, 0), "L1": (30.95, 47.4, 270), "C6": (27.6, 44.7, 0), "C7": (29.95, 50.9, 0),
    "C8": (29.95, 52.95, 0), "C9": (32.9, 50.6, 0), "R6": (24.2, 47.4, 180), "R7": (25.0, 50.3, 270),
    "R8": (24.2, 48.8, 180), "TP1": (35.4, 50.6, 0), "TP2": (22.0, 49.2, 0), "TP4": (35.4, 53.4, 0),
    # battery sense (left column)
    "Q2": (7.2, 38.6, 0), "R9": (10.6, 37.2, 90), "Q3": (7.2, 42.8, 0), "R10": (10.6, 42.8, 90),
    "R11": (13.4, 37.6, 90), "R12": (13.4, 40.6, 90), "C10": (14.8, 40.6, 90),
    # sensors / field I/O (middle)
    "U7": (38.4, 47.4, 0), "C19": (35.2, 45.2, 90), "C18": (38.4, 44.4, 0), "C20": (41.8, 45.2, 90),
    "R25": (41.8, 48.6, 90),
    "R21": (35.0, 57.6, 90), "R22": (37.2, 55.6, 0), "C21": (39.8, 55.6, 90),
    "R23": (24.4, 56.6, 90), "R24": (27.0, 57.0, 0), "C22": (29.6, 57.0, 90),
    "U6": (45.0, 56.6, 0), "F1": (49.0, 53.8, 0), "R19": (52.2, 56.4, 90), "R20": (53.6, 56.4, 90),
    "R17": (56.2, 48.0, 90), "R18": (57.6, 48.0, 90), "C17": (91.4, 38.4, 0), "U5": (91.4, 35.2, 0),
    # MCU / RF
    "U1": (77.0, 46.6, 0), "C12": (86.6, 41.8, 90), "C13": (86.6, 38.6, 90), "R13": (88.2, 44.8, 0),
    "C11": (88.2, 46.2, 0), "SW1": (90.2, 50.8, 90), "TP6": (61.4, 55.0, 0),
    "C14": (67.38, 54.0, 0), "L2": (66.9, 57.0, 270), "C15": (67.38, 60.0, 0), "J5": (67.95, 64.2, 0),
    "J6": (62.4, 44.0, 90), "J7": (61.6, 36.8, 90),
    # UI
    "D3": (52.0, 34.4, 0), "R14": (52.0, 36.6, 0), "U4": (46.0, 35.2, 0), "C16": (46.0, 38.2, 0),
}
# SHT40 island: three milled slots around U5, bridge toward the module side
ISLAND_SLOT = [(87.6, 31.8), (95.0, 31.8), (95.0, 32.8), (88.6, 32.8), (88.6, 39.6), (87.6, 39.6)]
SIDE = {}  # all parts on top


def outline(board):
    lay = pcbnew.Edge_Cuts
    w = MM(0.1)

    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(lay); s.SetWidth(w); board.Add(s)

    def arc(c, start, mid, end):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(P(*start), P(*mid), P(*end)); s.SetLayer(lay); s.SetWidth(w); board.Add(s)

    r = RC
    k = r * (1 - math.sqrt(0.5))
    seg((r, 0), (W - r, 0)); seg((W, r), (W, H - r)); seg((W - r, H), (r, H)); seg((0, H - r), (0, r))
    arc(None, (W - r, 0), (W - k, k), (W, r))
    arc(None, (W, H - r), (W - k, H - k), (W - r, H))
    arc(None, (r, H), (k, H - k), (0, H - r))
    arc(None, (0, r), (k, k), (r, 0))
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_POLY)
    s.SetPolyPoints([P(x, y) for x, y in ISLAND_SLOT])
    s.SetLayer(lay); s.SetWidth(w); s.SetFilled(False); board.Add(s)


def zone(board, netname, layer, poly, clearance=0.25, priority=0, min_w=0.2, thermal=0.4, name=""):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(full(netname)))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in poly:
        ol.Append(MM(OX + x), MM(OY + y))
    z.SetLocalClearance(MM(clearance))
    z.SetMinThickness(MM(min_w))
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(thermal))
    z.SetAssignedPriority(priority)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def board_poly(inset=0.4):
    i = inset
    return [(i, i), (W - i, i), (W - i, H - i), (i, H - i)]


def track(board, net, pts, width, layer=pcbnew.F_Cu, locked=True):
    n = board.FindNet(full(net))
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*a)); t.SetEnd(P(*b)); t.SetWidth(MM(width)); t.SetLayer(layer); t.SetNet(n)
        t.SetLocked(locked)
        board.Add(t)


def via(board, net, x, y, d=0.6, drill=0.3, locked=True):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(board.FindNet(full(net)))
    v.SetLocked(locked)
    board.Add(v)


def text(board, s, x, y, size=1.0, layer=pcbnew.F_SilkS, bold=False, rot=0, just="center"):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s); t.SetPosition(P(x, y)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(size * (0.2 if bold else 0.14)))
    t.SetTextAngleDegrees(rot)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    if just == "left":
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)


def silk_box(board, x0, y0, x1, y1, layer=pcbnew.F_SilkS, w=0.12):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    s.SetStart(P(x0, y0)); s.SetEnd(P(x1, y1)); s.SetLayer(layer); s.SetWidth(MM(w)); board.Add(s)


def kicad_netnames():
    """(ref, pin) -> full KiCad net name, from the exported netlist (local nets carry their sheet path)."""
    from sexpr import parse, find, find1
    tree = parse(open(os.path.join(HW, "tradewind.net")).read())
    m = {}
    for n in find(find1(tree, "nets"), "net"):
        for node in find(n, "node"):
            m[(find1(node, "ref")[1], find1(node, "pin")[1])] = find1(n, "name")[1]
    return m


NETMAP = {}


def full(net):
    return NETMAP.get(net, net)




STACKUP = """(stackup
			(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "prepreg") (color "FR4 natural") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 2" (type "core") (color "FR4 natural") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 3" (type "prepreg") (color "FR4 natural") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
			(copper_finish "ENIG")
			(dielectric_constraints no)
		)"""


def add_stackup():
    """JLC04161H-7628 4-layer stackup, matte black mask, white silk, ENIG (written into the board file)."""
    txt = open(PCB).read()
    if "(stackup" not in txt:
        txt = txt.replace("(setup", "(setup\n\t\t" + STACKUP, 1)
        open(PCB, "w").write(txt)


def apply_settings(board):
    """Fab rules (JLC 4-layer standard) and net classes, set on the board so every save carries them."""
    ds = board.GetDesignSettings()
    ds.m_MinClearance = MM(0.15); ds.m_TrackMinWidth = MM(0.15); ds.m_ViasMinSize = MM(0.45)
    ds.m_ViasMinAnnularWidth = MM(0.1); ds.m_MinThroughDrill = MM(0.2); ds.m_HoleClearance = MM(0.2)
    ds.m_HoleToHoleMin = MM(0.25); ds.m_CopperEdgeClearance = MM(0.3); ds.m_MinSilkTextHeight = MM(0.5)
    ds.m_MinSilkTextThickness = MM(0.08)
    ns = ds.m_NetSettings
    d = ns.GetDefaultNetclass()
    d.SetClearance(MM(0.15)); d.SetTrackWidth(MM(0.2)); d.SetViaDiameter(MM(0.6)); d.SetViaDrill(MM(0.3))
    for name, cl, tw, vd, vdr, pr in (("Power", 0.15, 0.3, 0.6, 0.3, 0), ("RF", 0.2, 0.35, 0.6, 0.3, 1)):
        nc = pcbnew.NETCLASS(name)
        nc.SetClearance(MM(cl)); nc.SetTrackWidth(MM(tw)); nc.SetViaDiameter(MM(vd)); nc.SetViaDrill(MM(vdr))
        nc.SetPriority(pr)
        ns.SetNetclass(name, nc)
    ns.ClearNetclassPatternAssignments()
    for pat in ["*VSYS", "*/VBAT", "*VIN_SOLAR", "*SOLAR_RAW", "*/LX1", "*/LX2"]:
        ns.SetNetclassPatternAssignment(pat, "Power")
    for pat in ["*RF_MOD", "*RF_ANT"]:
        ns.SetNetclassPatternAssignment(pat, "RF")
    ns.ClearAllCaches()
    board.SynchronizeNetsAndNetClasses(True)


def fanout(board, nets=("GND", "+3V3"), skip=("BT1",)):
    """Give every SMD pad on a plane net its own via to the inner plane (collision-checked)."""
    obstacles = []  # (x, y, r, net) in mm, board coords
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            bb = pd.GetBoundingBox()
            cx, cy = pcbnew.ToMM(bb.GetCenter().x) - OX, pcbnew.ToMM(bb.GetCenter().y) - OY
            obstacles.append(("pad", cx, cy, pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2, pd.GetNetname()))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            obstacles.append(("via", pcbnew.ToMM(t.GetPosition().x) - OX, pcbnew.ToMM(t.GetPosition().y) - OY, 0.3, 0.3, t.GetNetname()))
    # board-edge and slot keep-outs handled by staying inside 1 mm of the outline
    def free(x, y, net, rv=0.3, cl=0.22):
        if not (1.0 < x < W - 1.0 and 1.0 < y < H - 1.0):
            return False
        if 87.0 < x < 89.2 and 31.2 < y < 40.2:   # SHT island slot
            return False
        for kind, ox, oy, hw, hh, n in obstacles:
            dx = max(abs(x - ox) - hw, 0); dy = max(abs(y - oy) - hh, 0)
            d = math.hypot(dx, dy)
            need = rv + (cl if n != net else 0.05)
            if d < need:
                return False
        return True
    count = 0
    for fp in board.GetFootprints():
        if fp.GetReference() in skip:
            continue
        fc = fp.GetPosition()
        fx, fy = pcbnew.ToMM(fc.x) - OX, pcbnew.ToMM(fc.y) - OY
        for pd in fp.Pads():
            net = pd.GetNetname()
            if net not in nets or pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                continue
            if (fp.GetReference(), pd.GetNumber()) in (("U2", "17"), ("U3", "11"), ("U3", "8"), ("U3", "2")):
                continue  # exposed pads already stitched
            pc = pd.GetPosition()
            px, py = pcbnew.ToMM(pc.x) - OX, pcbnew.ToMM(pc.y) - OY
            bb = pd.GetBoundingBox()
            hw, hh = pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2
            vx, vy = px - fx, py - fy
            if math.hypot(vx, vy) < 0.05:
                vx, vy = 0, 1
            n0 = math.atan2(vy, vx)
            placed = False
            for extra in (0.0, 0.25, 0.5, 0.9, 1.4):
                for da in (0, 30, -30, 60, -60, 90, -90, 135, -135, 180):
                    a = n0 + math.radians(da)
                    ux, uy = math.cos(a), math.sin(a)
                    reach = abs(ux) * hw + abs(uy) * hh
                    dist = reach + 0.55 + extra
                    x, y = px + ux * dist, py + uy * dist
                    if free(x, y, net):
                        via(board, net, x, y, locked=False)
                        track(board, net, [(px, py), (x, y)], 0.3, locked=False)
                        obstacles.append(("via", x, y, 0.3, 0.3, net))
                        placed = True
                        count += 1
                        break
                if placed:
                    break
            if not placed:
                print("  no fanout room:", fp.GetReference(), pd.GetNumber(), net)
    print("fanout vias:", count)


def place():
    pinnet = kicad_netnames()
    for p in design.parts:
        for pin, n in p["pins"].items():
            if n and (p["ref"], pin) in pinnet:
                NETMAP[n] = pinnet[(p["ref"], pin)]
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(1.6))
    board.SetLayerName(pcbnew.In1_Cu, "In1.Cu")
    board.SetLayerName(pcbnew.In2_Cu, "In2.Cu")

    nets = sorted(set(pinnet.values()))
    for n in nets:
        board.Add(pcbnew.NETINFO_ITEM(board, n))

    for p in design.parts:
        if not p["fp"] or p["ref"].startswith("#"):
            continue
        lib, name = p["fp"].split(":")
        fp = pcbnew.FootprintLoad(FPD + lib + ".pretty", name)
        fp.SetReference(p["ref"])
        fp.SetValue(p["value"])
        fp.SetFPIDAsString(p["fp"])
        sheet_uuid = gs.SHEET_UUID[p["sheet"]]
        sym_uuid = gs.uid(p["sheet"], "sym", p["ref"])
        fp.SetPath(pcbnew.KIID_PATH("/%s/%s" % (sheet_uuid, sym_uuid)))
        fp.SetSheetname(gs.SHEET_NAME[p["sheet"]])
        fp.SetSheetfile(p["sheet"] + ".kicad_sch")
        for k, v in (("MPN", p["mpn"]), ("Manufacturer", p["mfr"]), ("Description", p["desc"])):
            if v:
                fld = pcbnew.PCB_FIELD(fp, fp.GetNextFieldId(), k)
                fld.SetText(v)
                fld.SetVisible(False)
                fld.SetLayer(pcbnew.F_Fab)
                fp.AddField(fld)
        if p["dnp"]:
            fp.SetDNP(True)
        if not p["bom"]:
            fp.SetExcludedFromBOM(True)
            if p["ref"].startswith(("TP", "H", "FID", "J6", "J7")):
                fp.SetExcludedFromPosFiles(True)
        for pad in fp.Pads():
            key = (p["ref"], pad.GetNumber())
            if key in pinnet:
                pad.SetNet(board.FindNet(pinnet[key]))
            if p["ref"] == "J7":
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        own = {"J1": "JST_PH_S2B-PH-SM4-TB", "J2": "JST_PH_S2B-PH-SM4-TB", "J3": "JST_PH_S3B-PH-SM4-TB",
               "J4": "JST_PH_S4B-PH-SM4-TB", "U2": "VQFN-16_3x3mm_P0.5mm", "U5": "Sensirion_DFN-4_1.5x1.5mm_SHT4x"}
        if p["ref"] in own:
            fp.Models().clear()
            m = pcbnew.FP_3DMODEL(); m.m_Filename = "${KIPRJMOD}/3d/%s.step" % own[p["ref"]]
            fp.Models().push_back(m)
        if p["ref"] == "U1":
            fp.Models().clear()
            m = pcbnew.FP_3DMODEL(); m.m_Filename = "${KIPRJMOD}/3d/RAK3172.step"
            fp.Models().push_back(m)
        if p["ref"] == "BT1":
            m = pcbnew.FP_3DMODEL(); m.m_Filename = "${KIPRJMOD}/3d/Cell_18650_protected.step"
            m.m_Offset = pcbnew.VECTOR3D(0, 0, 10.4)
            fp.Models().push_back(m)
        if p["ref"] == "U5":
            for z in list(fp.Zones()):
                fp.Remove(z)
        x, y, r = PLACE[p["ref"]]
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(r)
        # small references; passives' references live on the fab layer (assembly drawing)
        ref = fp.Reference()
        ref.SetTextSize(pcbnew.VECTOR2I(MM(0.7), MM(0.7)))
        ref.SetTextThickness(MM(0.12))
        if (p["ref"][0] in "RCL" and not p["ref"].startswith("RT") or p["ref"].startswith(("TP", "FID", "H"))
                or p["ref"] in ("J1", "J2", "J3", "J4", "J5", "U3", "U7", "Q2", "Q3")):
            ref.SetLayer(pcbnew.F_Fab)
        fp.Value().SetLayer(pcbnew.F_Fab)
        fp.Value().SetVisible(False)
        board.Add(fp)

    outline(board)
    # no copper pour under the humidity sensor (thermal isolation, per Sensirion layout guidance)
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True); ko.SetDoNotAllowCopperPour(True); ko.SetDoNotAllowTracks(False)
    ko.SetDoNotAllowVias(False); ko.SetDoNotAllowPads(False); ko.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET(); [ls.AddLayer(l) for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)]
    ko.SetLayerSet(ls)
    ol = ko.Outline(); ol.NewOutline()
    for x, y in [(90.0, 34.0), (92.8, 34.0), (92.8, 36.4), (90.0, 36.4)]:
        ol.Append(MM(OX + x), MM(OY + y))
    board.Add(ko)

    # planes: In1 = solid GND, In2 = +3V3 (with a VSYS/VBAT island under the power section)
    zone(board, "GND", pcbnew.In1_Cu, board_poly(0.3), clearance=0.2, name="GND_In1")
    zone(board, "+3V3", pcbnew.In2_Cu, board_poly(0.5), clearance=0.25, name="3V3_In2")

    # RF: 50 ohm CPWG, module RF pad 12 -> C14 -> L2 -> C15 -> U.FL. Locked; Freerouting keeps it.
    rf_w = 0.35
    u1 = board.FindFootprintByReference("U1")
    rfpad = [pd for pd in u1.Pads() if pd.GetNumber() == "12"][0]
    rx, ry = pcbnew.ToMM(rfpad.GetPosition().x) - OX, pcbnew.ToMM(rfpad.GetPosition().y) - OY
    def padxy(ref, num, net=None):
        f = board.FindFootprintByReference(ref)
        for pd in f.Pads():
            if pd.GetNumber() == num or (net and pd.GetNetname() == full(net)):
                return (pcbnew.ToMM(pd.GetPosition().x) - OX, pcbnew.ToMM(pd.GetPosition().y) - OY)
    l2a = padxy("L2", None, "RF_MOD"); l2b = padxy("L2", None, "RF_ANT"); j5 = padxy("J5", "1")
    print("RF pads", (rx, ry), l2a, l2b, j5)
    track(board, "RF_MOD", [(rx, ry), (l2a[0], ry), l2a], rf_w)
    track(board, "RF_ANT", [l2b, j5], rf_w)
    # ground-via fence beside the RF line
    for yy in [52.2, 54.0, 55.8, 57.6, 59.4, 61.2]:
        via(board, "GND", 65.6, yy)
        if yy not in (52.2, 54.0, 59.4, 61.2):
            via(board, "GND", 68.4, yy)

    # TPS63900 power stage, hand-routed (short switch nodes, tight input/output loops)
    track(board, "VSYS", [(26.2, 46.4), (26.2, 45.7), (28.95, 45.7), (28.95, 46.4)], 0.3)
    track(board, "VSYS", [(26.825, 44.7), (26.825, 45.7)], 0.3)
    track(board, "LX1", [(28.812, 46.9), (30.4, 46.9)], 0.25)
    track(board, "LX2", [(28.812, 47.9), (29.3, 48.0), (30.4, 48.0)], 0.25)
    track(board, "GND", [(28.6, 47.4), (28.05, 47.4)], 0.25)
    track(board, "GND", [(26.388, 46.9), (27.1, 46.9)], 0.25)
    track(board, "+3V3", [(28.812, 48.4), (29.0, 48.9), (29.0, 52.95)], 0.3)
    track(board, "CFG1", [(26.388, 47.4), (24.71, 47.4)], 0.2)
    track(board, "CFG3", [(26.388, 48.4), (25.2, 48.4), (24.71, 48.8)], 0.2)
    track(board, "CFG2", [(26.388, 47.9), (25.45, 47.9)], 0.2)
    via(board, "CFG2", 25.45, 47.9, d=0.45, drill=0.2)
    track(board, "CFG2", [(25.45, 47.9), (25.45, 49.79)], 0.2, layer=pcbnew.B_Cu)
    via(board, "CFG2", 25.45, 49.79, d=0.45, drill=0.2)
    track(board, "CFG2", [(25.45, 49.79), (25.0, 49.79)], 0.2)

    # thermal vias under the charger pad
    for dx in (-0.45, 0.45):
        for dy in (-0.45, 0.45):
            via(board, "GND", 16.0 + dx, 47.6 + dy, d=0.45, drill=0.2)

    # ---------------------------------------------------------------- silkscreen
    text(board, "TRADEWIND", 29.0, 34.8, size=1.6, bold=True)
    text(board, "TW-1 · REV B", 29.0, 37.0, size=0.9)
    text(board, "binarybeach.tech", 29.0, 38.8, size=0.7)
    text(board, "J1 SOLAR", 14.6, 58.9, size=0.8, bold=True)
    text(board, "J2 RAIN", 23.4, 58.9, size=0.8, bold=True)
    text(board, "J3 SOIL", 38.6, 58.9, size=0.8, bold=True)
    text(board, "J4 AIR PROBE", 52.4, 58.9, size=0.8, bold=True)
    text(board, "J5 ANT", 72.6, 64.2, size=0.8, bold=True)
    text(board, "+", 5.6, 19.5, size=1.6, bold=True)
    text(board, "−", 90.4, 19.5, size=1.6, bold=True)
    text(board, "PROTECTED 18650 Li-ion ONLY", 58.0, 31.8, size=0.7)
    text(board, "MAGNET", 46.0, 40.1, size=0.6)
    text(board, "SWD", 62.4, 48.2, size=0.6)
    text(board, "UART", 61.6, 39.6, size=0.6)
    text(board, "RH ISLAND", 92.0, 40.7, size=0.6)
    text(board, "Binary Beach LLC · Honolulu, Hawaiʻi · CERN-OHL-P-2.0", 48.0, 1.2, size=0.6, layer=pcbnew.B_SilkS)
    text(board, "TRADEWIND TW-1 rev B · 4L 1.6 mm ENIG", 48.0, 68.6, size=0.7, layer=pcbnew.B_SilkS)

    fanout(board)
    apply_settings(board)
    board.Save(PCB)
    add_stackup()
    board = pcbnew.LoadBoard(PCB)
    apply_settings(board)
    board.BuildConnectivity()
    print("zone fill:", pcbnew.ZONE_FILLER(board).Fill(board.Zones()))
    board.Save(PCB)
    print("placed", len(board.GetFootprints()), "footprints")


def export_dsn():
    board = pcbnew.LoadBoard(PCB)
    apply_settings(board)
    for z in list(board.Zones()):
        if z.GetIsRuleArea():
            board.Remove(z)
    dsn = PCB.replace(".kicad_pcb", ".dsn")
    pcbnew.ExportSpecctraDSN(board, dsn)
    s = open(dsn).read()
    # inner layers are planes: no routing on them, vias may connect to them
    s = re.sub(r"\(layer In1\.Cu\s*\(type signal\)", "(layer In1.Cu (type power)", s)
    s = re.sub(r"\(layer In2\.Cu\s*\(type signal\)", "(layer In2.Cu (type power)", s)
    open(dsn, "w").write(s)
    print("dsn written", dsn)


def import_ses():
    board = pcbnew.LoadBoard(PCB)
    apply_settings(board)
    ses = PCB.replace(".kicad_pcb", ".ses")
    ok = pcbnew.ImportSpecctraSES(board, ses)
    print("ses import:", ok)
    for t in list(board.GetTracks()):
        if t.GetClass() == "PCB_VIA" and "RF_" in t.GetNetname() and not t.IsLocked():
            board.Remove(t)
    # drop dangling stubs the router leaves behind (repeat until stable)
    for _ in range(6):
        board.BuildConnectivity()
        conn = board.GetConnectivity()
        dead = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and conn.TestTrackEndpointDangling(t, False)]
        for t in dead:
            board.Remove(t)
        if not dead:
            break
        print("removed dangling:", len(dead))
    # outer-layer ground pours (RF CPWG gap comes from the 0.2 mm zone clearance)
    zone(board, "GND", pcbnew.F_Cu, board_poly(0.4), clearance=0.2, priority=1, name="GND_F")
    zone(board, "GND", pcbnew.B_Cu, board_poly(0.4), clearance=0.2, priority=1, name="GND_B")
    # stitching grid (skipped where it would hit copper is handled by DRC-free placement test)
    board.BuildConnectivity()
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(PCB)
    print("routed board saved")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "place"
    {"place": place, "dsn": export_dsn, "ses": import_ses}[stage]()
