"""Lid — ASA: 6 mm skirt + 3 mm top, tongue that compresses the cord 28 %, captive M4 counterbores outside
the seal line, inside ribs kept clear of the 18650 cell, recessed label with the magnet-tap target over the
hall switch, and a light-pipe boss over the status LED."""
from common import *

HALL = b2l(46.0, 35.2)
LED = b2l(52.0, 34.4)
LABEL_C, LABEL_W, LABEL_H = (0.0, -22.0), 84.0, 22.0


def build():
    t = math.tan(math.radians(DRAFT))
    h = LID_SKIRT + LID_TOP
    body = tapered(ext_face(LID_Z0), h, DRAFT).val()
    body = cq.Workplane("XY").add(body).faces(">Z").edges().fillet(2.5).val()
    pocket = cq.Solid.extrudeLinear(cavity_face(LID_Z0 - 0.01, -RIM_BAND_W), cq.Vector(0, 0, LID_SKIRT + 0.01))
    body = body.cut(pocket)
    # tongue (enters the groove 0.6 mm)
    tongue = band_face(LID_Z0 - TONGUE_H, GROOVE_OFF, TONGUE_W / 2)
    for f in tongue.Faces():
        body = body.fuse(cq.Solid.extrudeLinear(f, cq.Vector(0, 0, TONGUE_H + 0.01)))
    # captive M4 screws: clearance hole + counterbore from the front, 0.3 mm retaining lip printed under the
    # head pocket is drilled out; a nylon retaining washer keeps the screw captive (BOM)
    for x, y in LID_SCREWS:
        body = body.cut(cyl(M4_CLEAR / 2, h + 1, (x, y, LID_Z0 - 0.5)))
        body = body.cut(cyl(M4_CBORE / 2, M4_CBORE_D + 0.01, (x, y, LID_Z1 - M4_CBORE_D)))
    # inside ribs (1.6 mm, 2 mm tall) — only where nothing tall sits below (cell band is y 9..32)
    rib_z0 = LID_CEIL - 2.0
    ribs = [(-50, 50, -3.0, -1.4), (-50, 50, -24.0, -22.4), (-50, 50, 37.0, 38.6)]
    for x0, x1, y0, y1 in ribs:
        body = body.fuse(box(x0, x1, y0, y1, rib_z0, LID_CEIL + 0.01))
    for x in (-36.0, -12.0, 12.0, 36.0):
        body = body.fuse(box(x - 0.8, x + 0.8, -40.0, 6.0, rib_z0, LID_CEIL + 0.01))
    # light pipe: Ø3 hole through the top, Ø6 guide boss 5 mm down
    body = body.fuse(cyl(3.0, 5.0, (LED[0], LED[1], LID_CEIL - 5.0)))
    body = body.cut(cyl(1.55, h + 8, (LED[0], LED[1], LID_CEIL - 6.0)))
    # front: recessed label area (0.6 mm) and the magnet-tap target (two engraved rings + dot)
    body = body.cut(box(LABEL_C[0] - LABEL_W / 2, LABEL_C[0] + LABEL_W / 2, LABEL_C[1] - LABEL_H / 2,
                        LABEL_C[1] + LABEL_H / 2, LID_Z1 - 0.6, LID_Z1 + 1))
    hx, hy = HALL
    for r_out, r_in in ((7.0, 6.2), (4.2, 3.4)):
        body = body.cut(cyl(r_out, 1.0, (hx, hy, LID_Z1 - 0.4)).cut(cyl(r_in, 1.0, (hx, hy, LID_Z1 - 0.4))))
    body = body.cut(cyl(1.2, 1.0, (hx, hy, LID_Z1 - 0.4)))
    # engraved wordmark in the label recess
    try:
        txt = (cq.Workplane("XY").workplane(offset=LID_Z1 - 0.6 - 0.4)
               .center(LABEL_C[0], LABEL_C[1] + 2.5).text("TRADEWIND", 8.0, 0.5, kind="bold", combine=False))
        sub = (cq.Workplane("XY").workplane(offset=LID_Z1 - 0.6 - 0.4)
               .center(LABEL_C[0], LABEL_C[1] - 6.0).text("TW-1  ·  SOLAR LoRaWAN SENSOR", 3.2, 0.5, combine=False))
        body = body.cut(txt.val()).cut(sub.val())
    except Exception as e:  # font missing: keep the plain recess
        print("text skipped:", e)
    return Part("lid", body.clean(), "asa_white", explode=(0, 0, 70), printed=True)


def light_pipe():
    s = cyl(1.45, LID_Z1 - 0.2 - (BOARD_Z0 + BOARD_T + 1.2), (LED[0], LED[1], BOARD_Z0 + BOARD_T + 1.2))
    return Part("light_pipe", s, "clear", explode=(0, 0, 95))


if __name__ == "__main__":
    p = build()
    s = p.solid()
    bb = s.BoundingBox()
    print("valid", s.isValid(), "vol cm3", round(s.Volume() / 1000, 1), "bbox", round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zmin, 2), round(bb.zmax, 2))
