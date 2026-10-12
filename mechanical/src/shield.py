"""Radiation shield (Stevenson-style gill stack) for the SHT45 air probe: a solid cap plus five louvred
rings (white ASA, sloped skirts shed rain and block direct/reflected sun), three M5 stainless rods with
spacer tubes, a printed probe holder, hung from an aluminium arm on the pole bracket."""
from common import *

AX = (SHIELD_X, SHIELD_Z)


def _ring_profile(r_in, solid_top=False):
    # (r, y) outline of a 2 mm bent strip: flat ring then a 45 deg skirt (prints top-down without support)
    pts = [(r_in, 2.0), (48.0, 2.0), (SHIELD_OD / 2, -10.0), (SHIELD_OD / 2, -12.8), (47.2, 0.0), (r_in, 0.0)]
    if solid_top:
        pts = [(0.0, 6.0), (20.0, 4.5), (48.0, 2.0), (SHIELD_OD / 2, -10.0), (SHIELD_OD / 2, -12.8), (47.2, 0.0),
               (0.0, 0.0)]
    return pts


def _revolve(pts, y0):
    wp = cq.Workplane("XY").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    return wp.val().translate(cq.Vector(AX[0], y0, AX[1]))


ROD_R = 42.0
ROD_ANG = (90.0, 210.0, 330.0)


def rod_xy(a):
    return AX[0] + ROD_R * math.cos(math.radians(a)), AX[1] + ROD_R * math.sin(math.radians(a))


def build():
    parts = []
    y_cap = SHIELD_TOP_Y - 6.0
    cap = _revolve(_ring_profile(0, True), y_cap)
    plates = [cap]
    ys = [y_cap - SHIELD_PITCH * (i + 1) for i in range(SHIELD_N - 1)]
    for y in ys:
        plates.append(_revolve(_ring_profile(SHIELD_ID / 2), y))
    # rod holes
    holes = None
    for a in ROD_ANG:
        x, z = rod_xy(a)
        h = cyl(2.8, 200, (x, -260, z), (0, 1, 0))
        holes = h if holes is None else holes.fuse(h)
    holes = holes.fuse(cyl(2.5, 20, (AX[0], y_cap - 2, AX[1]), (0, 1, 0)))  # probe cable hole through the cap
    for i, pl in enumerate(plates):
        parts.append(Part("shield_plate_%d" % i if i else "shield_cap", pl.cut(holes), "asa_white",
                          explode=(40, 18 - 14 * i, 0), printed=True, group="shield"))
    y_bot = ys[-1] - 3.0
    rods, tubes = None, None
    for a in ROD_ANG:
        x, z = rod_xy(a)
        r = cyl(2.5, y_cap + 8 - y_bot, (x, y_bot, z), (0, 1, 0))
        rods = r if rods is None else rods.fuse(r)
        for i in range(SHIELD_N - 1):
            ytop = (y_cap if i == 0 else ys[i - 1])
            t = cyl(4.5, SHIELD_PITCH - 2.0, (x, ys[i] + 2.0, z), (0, 1, 0)).cut(cyl(2.6, 20, (x, ys[i], z), (0, 1, 0)))
            tubes = t if tubes is None else tubes.fuse(t)
        nut = hexprism(8.0, 4.0, (x, y_bot - 4.0, z), (0, 1, 0))
        rods = rods.fuse(nut).fuse(hexprism(8.0, 4.0, (x, y_cap + 6.0, z), (0, 1, 0)))
    parts.append(Part("shield_rods", rods, "steel", explode=(40, 0, 0), group="shield_hw"))
    parts.append(Part("shield_spacers", tubes, "asa_white", explode=(40, 0, 0), printed=True, group="shield"))
    # probe holder: hub + three spokes to the rods, between plates 2 and 3
    yh = ys[1] + 6.0
    hub = cyl(10.0, 6.0, (AX[0], yh, AX[1]), (0, 1, 0)).cut(cyl(6.1, 8, (AX[0], yh - 1, AX[1]), (0, 1, 0)))
    for a in ROD_ANG:
        x, z = rod_xy(a)
        dx, dz = x - AX[0], z - AX[1]
        L = math.hypot(dx, dz)
        spoke = (cq.Workplane(cq.Plane(origin=(AX[0], yh + 3, AX[1]), xDir=(dx / L, 0, dz / L), normal=(0, 1, 0)))
                 .center(L / 2, 0).rect(L, 3.0).extrude(3.0, both=True).val())
        ring = cyl(4.5, 6.0, (x, yh, z), (0, 1, 0))
        hub = hub.fuse(spoke).fuse(ring).cut(cyl(2.6, 10, (x, yh - 2, z), (0, 1, 0)))
    parts.append(Part("probe_holder", hub, "asa_white", explode=(40, -10, 0), printed=True, group="shield"))
    # SHT45 probe: Ø12 x 40, sintered stainless tip, cable up through the cap
    tip = cyl(6.0, 15.0, (AX[0], yh - 30.0, AX[1]), (0, 1, 0))
    body = cyl(6.0, 25.0, (AX[0], yh - 15.0, AX[1]), (0, 1, 0))
    cable = cyl(2.2, (y_cap + 6.0) - (yh + 10.0), (AX[0], yh + 10.0, AX[1]), (0, 1, 0))
    parts.append(Part("probe_tip", tip, "probe", explode=(40, -40, 0), group="probe"))
    parts.append(Part("probe_body", body.fuse(cable), "steel", explode=(40, -40, 0), group="probe"))
    # arm: 25 x 4 aluminium flat bar from the bracket plate, plus a clamp block onto the cap
    arm = box(12.0, AX[0] + 14.0, ARM_Y - 10.0, ARM_Y + 10.0, PLATE_Z0, PLATE_Z0 + 4.0)
    block = cyl(9.0, (ARM_Y - 10.0) - (y_cap + 6.0) + 0.01, (AX[0], y_cap + 5.99, AX[1]), (0, 1, 0))
    parts.append(Part("shield_arm", arm.fuse(block).cut(cyl(2.5, 30, (AX[0], y_cap, AX[1]), (0, 1, 0))), "alu",
                      explode=(20, 0, 15), group="bracket"))
    return parts


if __name__ == "__main__":
    for p in build():
        bb = p.solid().BoundingBox()
        print(p.name, p.solid().isValid(), [round(v, 1) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
