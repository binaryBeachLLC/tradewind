"""3D models missing from the KiCad library: JST PH side-entry SMD headers (S2B/S3B/S4B-PH-SM4-TB),
VQFN-16 3x3 (BQ24074) and Sensirion DFN-4 1.5x1.5 (SHT40). Origins match the KiCad footprints."""
import os
import cadquery as cq

OUT = os.path.join(os.path.dirname(__file__), "..", "hardware", "tradewind", "3d")
IVORY = cq.Color(0.93, 0.90, 0.82)
TIN = cq.Color(0.80, 0.80, 0.80)
BLACK = cq.Color(0.08, 0.08, 0.09)


def jst_ph(n):
    w = 2.0 * (n - 1) + 3.9          # housing width (x)
    y0, y1, h = -1.9, 4.1, 4.75      # housing depth (y) and height; mating face at +y (board edge)
    body = cq.Workplane("XY").box(w, y1 - y0, h, centered=(True, False, False)).translate((0, y0, 0))
    # cavity for the mating plug, open toward +y
    cav = cq.Workplane("XY").box(w - 1.2, 4.6, h - 1.4, centered=(True, False, False)).translate((0, y1 - 4.6 + 0.01, 0.7))
    body = body.cut(cav)
    # latch ridge on top
    body = body.union(cq.Workplane("XY").box(w * 0.5, 1.2, 0.4, centered=(True, False, False)).translate((0, y1 - 2.2, h)))
    pins = None
    for i in range(n):
        x = -(n - 1) + 2.0 * i
        p = (cq.Workplane("XY").box(0.5, 1.6, 0.15, centered=(True, False, False)).translate((x, -3.55, 0))
             .union(cq.Workplane("XY").box(0.5, 0.15, 1.2, centered=(True, False, False)).translate((x, -2.05, 0))))
        pins = p if pins is None else pins.union(p)
    tabs = None
    for sx in (-1, 1):
        t = cq.Workplane("XY").box(1.6, 3.0, 0.2, centered=(True, True, False)).translate((sx * (w / 2 + 0.3), 2.9, 0))
        t = t.union(cq.Workplane("XY").box(0.2, 3.0, 2.6, centered=(True, True, False)).translate((sx * (w / 2 + 0.05), 2.9, 0)))
        tabs = t if tabs is None else tabs.union(t)
    a = cq.Assembly(name="JST_PH_%d" % n)
    a.add(body, name="housing", color=IVORY)
    a.add(pins.union(tabs), name="metal", color=TIN)
    a.save(os.path.join(OUT, "JST_PH_S%dB-PH-SM4-TB.step" % n))


def qfn(name, size, n_side, pitch, h, ep):
    body = cq.Workplane("XY").box(size, size, h, centered=(True, True, False)).edges("|Z").fillet(0.05)
    pads = None
    for side in range(4):
        for i in range(n_side):
            o = (i - (n_side - 1) / 2) * pitch
            pd = cq.Workplane("XY").box(0.25, 0.4, 0.2, centered=(True, True, False)).translate((o, -size / 2 + 0.2, -0.0))
            pd = pd.rotate((0, 0, 0), (0, 0, 1), 90 * side)
            pads = pd if pads is None else pads.union(pd)
    dot = cq.Workplane("XY").circle(0.15).extrude(0.01).translate((-size / 2 + 0.45, size / 2 - 0.45, h))
    a = cq.Assembly(name=name)
    a.add(body, name="body", color=BLACK)
    a.add(pads, name="pads", color=TIN)
    a.add(dot, name="pin1", color=cq.Color(0.5, 0.5, 0.5))
    a.save(os.path.join(OUT, name + ".step"))


def sht4x():
    body = cq.Workplane("XY").box(1.5, 1.5, 0.5, centered=(True, True, False))
    win = cq.Workplane("XY").circle(0.3).extrude(0.02).translate((0, 0, 0.5))
    pads = cq.Workplane("XY").pushPoints([(-0.4, -0.4), (-0.4, 0.4), (0.4, -0.4), (0.4, 0.4)]).box(0.3, 0.45, 0.15, centered=(True, True, False))
    pads = cq.Workplane("XY").pushPoints([(-0.6, -0.4), (-0.6, 0.4), (0.6, -0.4), (0.6, 0.4)]).box(0.35, 0.25, 0.12, centered=(True, True, False))
    a = cq.Assembly(name="SHT4x")
    a.add(body, name="body", color=cq.Color(0.18, 0.18, 0.2))
    a.add(win, name="window", color=cq.Color(0.85, 0.65, 0.2))
    a.add(pads, name="pads", color=TIN)
    a.save(os.path.join(OUT, "Sensirion_DFN-4_1.5x1.5mm_SHT4x.step"))


if __name__ == "__main__":
    for n in (2, 3, 4):
        jst_ph(n)
    qfn("VQFN-16_3x3mm_P0.5mm", 3.0, 4, 0.5, 0.9, 1.6)
    sht4x()
    print("models written to", OUT)
