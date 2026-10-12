"""Base (box) — ASA, molded-style: 3 mm walls with 1 deg draft, thickened rim carrying the gasket groove,
corner screw columns outside the seal line (M4 heat-set inserts), PCB bosses (M3 inserts), bottom-wall
penetrations (4 x PG7 glands + SMA bulkhead), side M12 vent and four M4 mounting bosses on the back."""
from common import *


def _faces_prism(shape, h):
    out = None
    for f in shape.Faces():
        s = cq.Solid.extrudeLinear(f, cq.Vector(0, 0, h))
        out = s if out is None else out.fuse(s)
    return out


def build():
    t = math.tan(math.radians(DRAFT))
    depth = FLOOR + BASE_DEPTH
    # exterior: footprint at the rim, shrinking 1 deg toward the back
    body = tapered(ext_face(-FLOOR, -depth * t), depth, -DRAFT).val()
    body = cq.Workplane("XY").add(body).faces("<Z").edges().fillet(2.0).val()
    cav = tapered(cavity_face(0.0, -BASE_DEPTH * t), BASE_DEPTH + 0.01, -DRAFT).val()
    body = body.cut(cav)
    # rim band (inward thickening, 5 mm tall) — carries the groove with 1.35 mm walls either side
    band = cavity_face(RIM_Z - RIM_BAND_H).cut(cavity_face(RIM_Z - RIM_BAND_H, -RIM_BAND_W))
    body = body.fuse(_faces_prism(band, RIM_BAND_H))
    # 45 deg support chamfer under the band (prints without supports)
    z0 = RIM_Z - RIM_BAND_H - RIM_BAND_W
    outer = cq.Solid.extrudeLinear(cavity_face(z0), cq.Vector(0, 0, RIM_BAND_W))
    inner = cq.Solid.extrudeLinear(cavity_face(z0), cq.Vector(0, 0, RIM_BAND_W), taper=45)
    ch = outer.cut(inner)
    body = body.fuse(ch)
    # gasket groove
    groove = band_face(RIM_Z - GROOVE_D, GROOVE_OFF, GROOVE_W / 2)
    body = body.cut(_faces_prism(groove, GROOVE_D + 0.01))
    # corner column inserts (M4)
    for x, y in LID_SCREWS:
        body = body.cut(cyl(M4_INSERT_HOLE / 2, M4_INSERT_DEPTH + 0.01, (x, y, RIM_Z - M4_INSERT_DEPTH)))
    # PCB bosses with M3 inserts, plus two gussets each
    for bx, by in BOARD_HOLES:
        x, y = b2l(bx, by)
        boss = cyl(BOSS_D / 2, BOARD_Z0 + 0.5, (x, y, -0.5))
        for gx, gy, gw, gh in ((x, y, 9.0, 1.4), (x, y, 1.4, 9.0)):
            boss = boss.fuse(box(gx - gw / 2, gx + gw / 2, gy - gh / 2, gy + gh / 2, -0.5, 3.0))
        body = body.fuse(boss)
        body = body.cut(cyl(M3_INSERT_HOLE / 2, M3_INSERT_DEPTH, (x, y, BOARD_Z0 - M3_INSERT_DEPTH + 0.01)))
    # bottom wall: PG7 glands and SMA bulkhead (axis along y)
    yb = -EXT_H / 2 - 2
    for gx in GLAND_X:
        body = body.cut(cyl(PG7_HOLE / 2, 10, (gx, yb, GLAND_Z), (0, 1, 0)))
    body = body.cut(cyl(SMA_HOLE / 2, 10, (SMA_X, yb, GLAND_Z), (0, 1, 0)))
    # spot faces inside around the holes so nuts seat flat on the drafted wall
    for gx in GLAND_X:
        body = body.cut(cyl(9.5, 1.0, (gx, -CAV_H / 2 - 0.4, GLAND_Z), (0, 1, 0)))
    # right wall: M12 pressure-equalising vent
    body = body.cut(cyl(VENT_HOLE / 2, 10, (EXT_W / 2 - 5, VENT_Y, GLAND_Z), (1, 0, 0)))
    # back: four mounting bosses with blind M4 inserts (no penetration of the floor)
    for x, y in MOUNT_PTS:
        body = body.fuse(cyl(MOUNT_BOSS_D / 2, MOUNT_BOSS_H + 0.5, (x, y, -FLOOR - MOUNT_BOSS_H)))
        body = body.cut(cyl(M4_INSERT_HOLE / 2, 6.4, (x, y, -FLOOR - MOUNT_BOSS_H - 0.01)))
    # back stiffening ribs between the mounting bosses
    for y in (-30.0, 30.0):
        body = body.fuse(box(-25, 25, y - 1.0, y + 1.0, -FLOOR - 3.0, -FLOOR + 0.2))
    for x in (-25.0, 25.0):
        body = body.fuse(box(x - 1.0, x + 1.0, -30, 30, -FLOOR - 3.0, -FLOOR + 0.2))
    # drip edge: small chamfer on the lower outside edge is provided by the 2 mm back fillet
    return Part("base", body.clean(), "asa_white", explode=(0, 0, 0), printed=True)


if __name__ == "__main__":
    p = build()
    s = p.solid()
    print("valid", s.isValid(), "vol cm3", round(s.Volume() / 1000, 1), "bbox", s.BoundingBox().xlen, s.BoundingBox().ylen, s.BoundingBox().zlen)
