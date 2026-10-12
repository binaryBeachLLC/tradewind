"""Bought-in hardware, modelled to catalogue dimensions: gasket cord, heat-set inserts, screws, PG7 glands,
SMA bulkhead + U.FL pigtail + 915 MHz whip, M12 vent, light pipe, and the field cables with drip loops."""
from common import *
import roof as roofmod
import shield as shieldmod

T1 = math.tan(math.radians(DRAFT))
Y_EXT = -(EXT_H / 2 - (RIM_Z - GLAND_Z - 8.7) * T1) - 0.05  # seat plane: outermost wall point under the flange
Y_INT = -(CAV_H / 2 - (RIM_Z - GLAND_Z) * T1)     # bottom wall inner face
X_EXT = EXT_W / 2 - (RIM_Z - GLAND_Z - 8.7) * T1 + 0.05


def tube(points, r):
    """Sweep a round cable along a smooth spline through points (L frame)."""
    vs = [cq.Vector(*p) for p in points]
    path = cq.Wire.assembleEdges([cq.Edge.makeSpline(vs)])
    t0 = path.tangentAt(0)
    prof = cq.Wire.makeCircle(r, vs[0], t0)
    return cq.Solid.sweep(prof, [], path, isFrenet=True)


def gasket():
    """2.5 mm cord as installed in the groove: a 2.5 x 2.5 ring along the groove centreline, edges rounded
    R1.2 (a swept circle along this arc/line path is not a valid solid in OCCT; this is within 2 % in volume)."""
    b = band_face(RIM_Z - GROOVE_D, GROOVE_OFF, CORD_D / 2)
    s = cq.Solid.extrudeLinear(b.Faces()[0], cq.Vector(0, 0, CORD_D))
    return cq.Workplane().add(s).edges().fillet(1.2).val()


def socket_head(x, y, z_top, d_head, h_head, d_shank, L, axis=-1):
    """Socket head cap screw, head top at z_top, shank along axis (-1 = into -z)."""
    head = cyl(d_head / 2, h_head, (x, y, z_top - h_head if axis < 0 else z_top))
    head = head.cut(hexprism(d_head * 0.43, h_head * 0.55, (x, y, z_top - h_head * 0.55) if axis < 0 else (x, y, z_top),
                             (0, 0, 1)))
    shank = cyl(d_shank / 2, L, (x, y, z_top - h_head - L) if axis < 0 else (x, y, z_top + h_head))
    return head.fuse(shank)


def build():
    P = []
    P.append(Part("gasket", gasket(), "silicone", explode=(0, 0, 45), group="gasket"))
    # heat-set inserts
    ins = None
    for x, y in LID_SCREWS:
        s = cyl(2.9, 6.4, (x, y, RIM_Z - 6.4)).cut(cyl(1.75, 7, (x, y, RIM_Z - 6.5)))
        ins = s if ins is None else ins.fuse(s)
    for bx, by in BOARD_HOLES:
        x, y = b2l(bx, by)
        ins = ins.fuse(cyl(2.0, 4.0, (x, y, BOARD_Z0 - 4.0)).cut(cyl(1.25, 5, (x, y, BOARD_Z0 - 4.5))))
    for x, y in MOUNT_PTS:
        ins = ins.fuse(cyl(2.9, 6.4, (x, y, -FLOOR - MOUNT_BOSS_H)).cut(cyl(1.75, 7, (x, y, -FLOOR - MOUNT_BOSS_H - 0.5))))
    P.append(Part("inserts", ins, "brass", explode=(0, 0, 0), group="inserts"))
    # screws: lid M4x12 (captive), PCB M3x6, bracket M4x8 from behind the plate
    sc = None
    for x, y in LID_SCREWS:
        s = socket_head(x, y, LID_Z1, 7.0, 4.0, 4.0, 12.0)
        sc = s if sc is None else sc.fuse(s)
    P.append(Part("lid_screws", sc, "steel", explode=(0, 0, 110), group="screws"))
    pc = None
    for bx, by in BOARD_HOLES:
        x, y = b2l(bx, by)
        top = BOARD_Z0 + BOARD_T + 2.0
        s = cyl(2.75, 2.0, (x, y, top - 2.0)).fuse(cyl(1.5, 6.0, (x, y, top - 2.0 - 6.0)))
        pc = s if pc is None else pc.fuse(s)
    P.append(Part("pcb_screws", pc, "steel", explode=(0, 0, 55), group="screws"))
    bc = None
    for x, y in MOUNT_PTS:
        s = cyl(3.5, 4.0, (x, y, PLATE_Z0 - PLATE_T - 4.0)).fuse(cyl(2.0, 8.0, (x, y, PLATE_Z0 - PLATE_T)))
        bc = s if bc is None else bc.fuse(s)
    P.append(Part("bracket_screws", bc, "steel", explode=(0, 0, -75), group="screws"))

    # PG7 glands (M12x1.5): outside hex flange + dome cap, inside lock nut
    gl = None
    for gx in GLAND_X:
        o = (gx, Y_EXT, GLAND_Z)
        g = hexprism(15.0, 5.0, o, (0, -1, 0))
        cap = cyl(7.5, 8.0, (gx, Y_EXT - 5.0, GLAND_Z), (0, -1, 0))
        cap = cq.Workplane("XY").add(cap).faces("<Y").edges().fillet(2.5).val()
        g = g.fuse(cap).cut(cyl(2.7, 30, (gx, Y_EXT - 20, GLAND_Z), (0, 1, 0)))
        g = g.fuse(cyl(5.9, Y_INT + 5.5 - Y_EXT, (gx, Y_EXT, GLAND_Z), (0, 1, 0)))
        g = g.fuse(hexprism(15.0, 4.0, (gx, Y_INT + 0.6, GLAND_Z), (0, 1, 0)))
        gl = g if gl is None else gl.fuse(g)
    P.append(Part("glands_pg7", gl, "black", explode=(0, -30, 0), group="glands"))

    # SMA bulkhead + whip antenna (points down), U.FL pigtail to J5
    sma = hexprism(8.0, 2.5, (SMA_X, Y_EXT, GLAND_Z), (0, -1, 0))
    sma = sma.fuse(cyl(3.15, 9.0, (SMA_X, Y_EXT - 2.5, GLAND_Z), (0, -1, 0)))
    sma = sma.fuse(hexprism(8.0, 2.5, (SMA_X, Y_INT + 0.2, GLAND_Z), (0, 1, 0)))
    sma = sma.fuse(cyl(2.6, 6.0, (SMA_X, Y_INT + 2.7, GLAND_Z), (0, 1, 0)))
    P.append(Part("sma_bulkhead", sma, "brass", explode=(0, -30, 0), group="antenna"))
    y_a = Y_EXT - 11.5
    ant = cyl(5.0, 22.0, (SMA_X, y_a, GLAND_Z), (0, -1, 0))
    ant = ant.fuse(cq.Solid.makeSphere(5.4, cq.Vector(SMA_X, y_a - 23.0, GLAND_Z)))
    whip = cq.Solid.makeCone(4.6, 2.8, 172.0, cq.Vector(SMA_X, y_a - 23.0, GLAND_Z), cq.Vector(0, -1, 0))
    whip = whip.fuse(cq.Solid.makeSphere(2.8, cq.Vector(SMA_X, y_a - 195.0, GLAND_Z)))
    P.append(Part("antenna_915", ant.fuse(whip), "black", explode=(0, -70, 0), group="antenna"))
    j5 = b2l(67.95, 64.2)
    pig = tube([(SMA_X, Y_INT + 8.7, GLAND_Z), (SMA_X - 2, -33.0, 12.5), (j5[0] + 6, j5[1] - 4.0, 12.0),
                (j5[0], j5[1], BOARD_Z0 + BOARD_T + 3.0)], 0.7)
    pig = pig.fuse(cyl(1.0, 2.6, (j5[0], j5[1], BOARD_Z0 + BOARD_T)))
    P.append(Part("ufl_pigtail", pig, "cable", explode=(0, 0, 20), group="antenna"))

    # M12 vent on the right wall
    v = cyl(8.0, 7.0, (X_EXT, VENT_Y, GLAND_Z), (1, 0, 0))
    v = cq.Workplane("XY").add(v).faces(">X").edges().fillet(3.0).val()
    v = v.fuse(cyl(5.9, 6.0, (X_EXT - 5.5, VENT_Y, GLAND_Z), (1, 0, 0)))
    v = v.fuse(hexprism(16.0, 3.5, (CAV_W / 2 - (RIM_Z - 1.0) * T1 - 0.1 - 3.5, VENT_Y, GLAND_Z), (1, 0, 0)))
    P.append(Part("vent_m12", v, "black", explode=(30, 0, 0), group="vent"))

    # cables with drip loops below the glands (all leave downward, then turn up toward their sensor)
    yc = Y_EXT - 13.0
    jb = roofmod.local_to_L(-52.0, -12.0, -40.0)
    solar = tube([(GLAND_X[0], yc, GLAND_Z), (GLAND_X[0], yc - 25, GLAND_Z), (GLAND_X[0] - 12, yc - 42, 2),
                  (-62.0, yc - 20, -6.0), (-66.0, 10.0, -6.0), (-62.0, 70.0, -6.0), (jb[0] - 4, jb[1] - 8, jb[2]),
                  (jb[0], jb[1], jb[2])], 2.6)
    shield_top = (SHIELD_X, SHIELD_TOP_Y + 4.0, SHIELD_Z)
    probe = tube([(GLAND_X[3], yc, GLAND_Z), (GLAND_X[3], yc - 22, GLAND_Z), (GLAND_X[3] + 12, yc - 34, -3.0),
                  (70.0, ARM_Y - 18.0, -1.0), (125.0, ARM_Y - 18.0, 2.0), (shield_top[0] - 10, ARM_Y - 16.0, -3.0),
                  (shield_top[0] + 12, ARM_Y - 14.0, SHIELD_Z + 10.0)], 2.2)
    rain = tube([(GLAND_X[1], yc, GLAND_Z), (GLAND_X[1], yc - 30, GLAND_Z), (GLAND_X[1] + 3, yc - 70, 18.0)], 2.2)
    soil = tube([(GLAND_X[2], yc, GLAND_Z), (GLAND_X[2], yc - 30, GLAND_Z), (GLAND_X[2] - 3, yc - 70, 18.0)], 2.2)
    for n, s in (("cable_solar", solar), ("cable_probe", probe), ("cable_rain", rain), ("cable_soil", soil)):
        P.append(Part(n, s, "cable", explode=(0, -30, 0), group="cables"))
    return P


if __name__ == "__main__":
    for p in build():
        bb = p.solid().BoundingBox()
        print(p.name, p.solid().isValid(), [round(v, 1) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
