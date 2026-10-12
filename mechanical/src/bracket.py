"""Pole bracket: 3 mm 5052 aluminium plate (64 x 195 mm), two M6 stainless U-bolts for 25–50 mm poles,
the box bolts to it with four M4 screws into blind inserts; the roof gussets and the shield arm bolt to it too.
Includes a 42 mm pole segment for context."""
from common import *

UBOLT_Y = (58.0, -62.0)
UB_R = POLE_D / 2 + 3.0     # centreline radius of the U


def plate():
    p = box(-PLATE_W / 2, PLATE_W / 2, PLATE_Y0, PLATE_Y1, PLATE_Z0 - PLATE_T, PLATE_Z0)
    p = cq.Workplane("XY").add(p).edges("|Z").fillet(4.0).val()
    for x, y in MOUNT_PTS:
        p = p.cut(cyl(2.25, 10, (x, y, -20)))
    for y in UBOLT_Y:
        for sx in (-1, 1):
            p = p.cut(cyl(3.3, 10, (sx * UB_R, y, -20)))
    # bolt holes for the gusset flanges and the shield arm
    for sx in (-1, 1):
        for y in (72.0, 86.0):
            p = p.cut(cyl(2.25, 10, (sx * 29.2, y, -20)))
    for x in (17.0, 27.0):
        p = p.cut(cyl(2.25, 10, (x, ARM_Y, -20)))
    # lightening slot in the middle (behind the box, hidden)
    p = p.cut(cq.Workplane("XY").workplane(offset=-20).center(0, 0).slot2D(40, 10, 90).extrude(20).val())
    return p


def ubolt(y):
    z_front = PLATE_Z0 + 7.0
    e1 = cq.Edge.makeLine(cq.Vector(-UB_R, y, z_front), cq.Vector(-UB_R, y, POLE_Z))
    e2 = cq.Edge.makeThreePointArc(cq.Vector(-UB_R, y, POLE_Z), cq.Vector(0, y, POLE_Z - UB_R), cq.Vector(UB_R, y, POLE_Z))
    e3 = cq.Edge.makeLine(cq.Vector(UB_R, y, POLE_Z), cq.Vector(UB_R, y, z_front))
    path = cq.Wire.assembleEdges([e1, e2, e3])
    prof = cq.Wire.makeCircle(3.0, cq.Vector(-UB_R, y, z_front), cq.Vector(0, 0, -1))
    rod = cq.Solid.sweep(prof, [], path, transitionMode="round")
    for sx in (-1, 1):
        rod = rod.fuse(cyl(6.0, 1.2, (sx * UB_R, y, PLATE_Z0), (0, 0, 1)))           # washer
        rod = rod.fuse(hexprism(10.0, 5.0, (sx * UB_R, y, PLATE_Z0 + 1.2), (0, 0, 1)))  # M6 nut
    # V-saddle behind the plate grips round poles 25–50 mm
    saddle = box(-18, 18, y - 10, y + 10, PLATE_Z0 - PLATE_T - 6.0, PLATE_Z0 - PLATE_T)
    cut = cq.Solid.makeCylinder(POLE_D / 2 + 0.2, 40, cq.Vector(0, y - 20, POLE_Z), cq.Vector(0, 1, 0))
    saddle = saddle.cut(cut)
    return rod, saddle


def build():
    parts = [Part("bracket_plate", plate(), "alu", explode=(0, 0, -45), group="bracket")]
    rods, saddles = None, None
    for y in UBOLT_Y:
        r, s = ubolt(y)
        rods = r if rods is None else rods.fuse(r)
        saddles = s if saddles is None else saddles.fuse(s)
    parts.append(Part("ubolts", rods, "steel", explode=(0, 0, -95), group="bracket_hw"))
    parts.append(Part("pole_saddles", saddles, "alu", explode=(0, 0, -70), group="bracket"))
    pole = cyl(POLE_D / 2, 340.0, (0, -260.0, POLE_Z), (0, 1, 0)).cut(cyl(POLE_D / 2 - 2.5, 342, (0, -261, POLE_Z), (0, 1, 0)))
    cap = cyl(POLE_D / 2 + 1.0, 4.0, (0, 80.0, POLE_Z), (0, 1, 0))
    cap = cq.Workplane("XY").add(cap).faces(">Y").edges().fillet(1.5).val()
    parts.append(Part("pole_cap", cap, "black", explode=(0, 20, -130), group="pole"))
    parts.append(Part("pole", pole, "pole", explode=(0, 0, -130), group="pole"))
    return parts


if __name__ == "__main__":
    for p in build():
        bb = p.solid().BoundingBox()
        print(p.name, p.solid().isValid(), [round(v, 1) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
