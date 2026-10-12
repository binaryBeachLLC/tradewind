"""Sun roof + 2 W panel. The roof is a 3 mm ASA tray (8 mm down-turned lip) tilted 20 deg toward the south
(+z), held 25 mm above the box by two aluminium gussets bolted to the pole bracket. The panel sits on top,
so the panel itself is the box's sunshade; the air gap vents the heat off the roof underside."""
from common import *

T = math.radians(TILT)
TZ = ROOF_FRONT_Z - (ROOF_L / 2) * math.cos(T)
TY = roof_underside_y(TZ)


def place(shape):
    """Roof-local (x across, y up from the underside, z along the slope toward the front) -> L frame."""
    return shape.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), TILT).translate(cq.Vector(0, TY, TZ))


def local_to_L(x, y, z):
    v = cq.Vector(x, y, z)
    c, s = math.cos(T), math.sin(T)
    return (v.x, v.y * c - v.z * s + TY, v.y * s + v.z * c + TZ)


def roof_plate():
    w, l = ROOF_W, ROOF_L
    plate = box(-w / 2, w / 2, 0, ROOF_T, -l / 2, l / 2)
    lip = box(-w / 2, w / 2, -ROOF_LIP, ROOF_T, -l / 2, l / 2).cut(
        box(-w / 2 + 2.5, w / 2 - 2.5, -ROOF_LIP - 1, 0.01, -l / 2 + 2.5, l / 2 - 2.5))
    s = plate.fuse(lip)
    # underside ribs (stiffness), cable hole near the back-left under the panel junction box
    for x in (-40.0, 0.0, 40.0):
        s = s.fuse(box(x - 1.0, x + 1.0, -5.0, 0.01, -l / 2 + 2.5, l / 2 - 2.5))
    s = s.cut(cyl(4.0, 10, (-52.0, -6, -40.0), (0, 1, 0)))
    return s


def panel_parts():
    """136 x 110 x 3 mm epoxy panel: dark backsheet, 2 x 5 mono cells with busbars, junction box below."""
    y0 = ROOF_T
    back = box(-PANEL_W / 2, PANEL_W / 2, y0, y0 + PANEL_T, -PANEL_L / 2, PANEL_L / 2)
    cells, bus = None, None
    cw, cl, gap = 24.0, 50.0, 1.6
    for i in range(5):
        for j in range(2):
            cx = (i - 2) * (cw + gap)
            cz = (j - 0.5) * (cl + gap)
            c = box(cx - cw / 2, cx + cw / 2, y0 + PANEL_T, y0 + PANEL_T + 0.25, cz - cl / 2, cz + cl / 2)
            cells = c if cells is None else cells.fuse(c)
            for k in (-1, 0, 1):
                b = box(cx + k * 7.5 - 0.35, cx + k * 7.5 + 0.35, y0 + PANEL_T + 0.25, y0 + PANEL_T + 0.32,
                        cz - cl / 2 + 0.5, cz + cl / 2 - 0.5)
                bus = b if bus is None else bus.fuse(b)
    jbox = box(-60.0, -44.0, -12.0, -8.0, -46.0, -34.0).fuse(cyl(2.5, 8, (-52.0, -8.0, -40.0), (0, 1, 0)))
    return back, cells, bus, jbox


def gusset(sign):
    x0 = sign * 28.0
    zf = PLATE_Z0
    pts = [(zf, 66.0), (zf, roof_underside_y(zf) - 0.2), (40.0, roof_underside_y(40.0) - 0.2), (zf + 12.0, 66.0)]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(x0 - 1.5, y, z) for z, y in pts], close=True))
    g = cq.Solid.extrudeLinear(face, cq.Vector(3.0, 0, 0))
    lo, hi = (26.5, 32.0) if sign > 0 else (-32.0, -26.5)
    flange = box(lo, hi, 66.0, roof_underside_y(zf + 3.0) - 0.2, zf, zf + 3.0)
    return g.fuse(flange)


def build():
    parts = []
    parts.append(Part("roof", place(roof_plate()), "asa_grey", explode=(0, 60, 0), printed=True, group="roof"))
    back, cells, bus, jbox = panel_parts()
    parts.append(Part("panel", place(back), "panel_back", explode=(0, 95, 0), group="panel"))
    parts.append(Part("panel_cells", place(cells), "panel_cell", explode=(0, 95, 0), group="panel"))
    parts.append(Part("panel_busbars", place(bus), "panel_bus", explode=(0, 95, 0), group="panel"))
    parts.append(Part("panel_jbox", place(jbox), "black", explode=(0, 60, 0), group="panel"))
    for s in (-1, 1):
        parts.append(Part("roof_gusset_%s" % ("L" if s < 0 else "R"), gusset(s), "alu", explode=(0, 30, 0),
                          group="roof_gussets"))
    return parts


if __name__ == "__main__":
    for p in build():
        bb = p.solid().BoundingBox()
        print(p.name, p.solid().isValid(), [round(v, 1) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)])
    print("roof underside at box front:", round(roof_underside_y(LID_Z1), 1), "TY", round(TY, 1), "TZ", round(TZ, 1))
