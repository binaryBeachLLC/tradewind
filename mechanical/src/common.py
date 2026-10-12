"""Shared parameters and helpers for the Tradewind TW-1 enclosure system.

Model frame "L" (also the glTF frame): x right, y up (installed vertical), z toward the viewer
(the lid / front faces +z, the pole is behind at -z). Units: mm.
Installed CAD frame "W" (STEP export): Z up — W = L rotated +90 deg about X  (W.Y = -L.z, W.Z = L.y).

Board mapping: board point (bx, by) [KiCad mm, origin top-left, y down] -> L (bx - 48, 40 - by),
board bottom face at z = BOARD_Z0, top face at BOARD_Z0 + 1.6.
"""
import math
import os

import cadquery as cq

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MECH = os.path.join(ROOT, "mechanical")
OUT = os.path.join(MECH, "out")
WEB = os.path.join(OUT, "web")
FIG = os.path.join(ROOT, "docs", "figures")
BOARD_STEP = os.path.join(ROOT, ".scratch", "tradewind_board_placed.step")
PCB_FILE = os.path.join(ROOT, "hardware", "tradewind", "tradewind.kicad_pcb")

# ---------------------------------------------------------------- box
EXT_W, EXT_H, EXT_R = 122.0, 98.0, 6.0      # exterior footprint (x, y) and corner radius
WALL = 3.0
CAV_W, CAV_H, CAV_R = EXT_W - 2 * WALL, EXT_H - 2 * WALL, 2.0
COL_R = 10.0                                # corner screw columns (cut out of the cavity)
FLOOR = 3.0                                 # back wall (floor) thickness
BASE_DEPTH = 27.0                           # floor inner face (z=0) to rim (z=27)
RIM_Z = BASE_DEPTH
RIM_BAND_W, RIM_BAND_H = 3.0, 5.0           # inward rim thickening that carries the groove
DRAFT = 1.0                                 # deg, molded-style walls

# gasket: 2.5 mm silicone cord in a 3.4 x 2.6 groove, lid tongue 1.6 wide enters 0.75 mm (26 % squeeze, 78 % fill)
CORD_D = 2.5
GROOVE_W, GROOVE_D = 3.4, 2.6
GROOVE_OFF = 0.0                            # groove centreline offset outward from cavity outline
TONGUE_W, TONGUE_H = 1.6, 0.75

# lid: skirt + top plate
LID_SKIRT = 6.0
LID_TOP = 3.0
LID_Z0 = RIM_Z
LID_Z1 = RIM_Z + LID_SKIRT + LID_TOP        # 33, front face
LID_CEIL = RIM_Z + LID_SKIRT                # 30, inner ceiling

# screws
LID_SCREWS = [(sx * 55.5, sy * 43.5) for sx in (-1, 1) for sy in (-1, 1)]
M4_INSERT_HOLE, M4_INSERT_DEPTH = 5.6, 8.0
M4_CLEAR, M4_CBORE, M4_CBORE_D = 4.5, 8.5, 4.0

# PCB
BOARD_Z0 = 6.0                              # board back face above the floor
BOARD_T = 1.6
BOARD_HOLES = [(4, 4), (92, 4), (4, 66), (92, 66)]
M3_INSERT_HOLE, M3_INSERT_DEPTH = 4.0, 5.5
BOSS_D = 7.0


def b2l(bx, by):
    return (bx - 48.0, 40.0 - by)


# bottom wall penetrations (x positions, z height)
GLAND_X = [-39.5, -18.5, 2.5, 23.5]         # J1 solar, J2 rain, J3 soil, J4 air probe
GLAND_Z = 9.5
PG7_HOLE = 12.5
SMA_X, SMA_HOLE = 40.0, 6.4
VENT_Y, VENT_HOLE = -20.0, 12.5             # right side wall

# back mounting bosses (M4 inserts) -> bracket plate
MOUNT_PTS = [(sx * 25.0, sy * 30.0) for sx in (-1, 1) for sy in (-1, 1)]
MOUNT_BOSS_D, MOUNT_BOSS_H = 11.0, 6.0
PLATE_Z0, PLATE_T = -FLOOR - MOUNT_BOSS_H, 3.0   # plate front face z=-9, back z=-12
POLE_D = 42.0
POLE_Z = PLATE_Z0 - PLATE_T - POLE_D / 2          # -33
PLATE_W, PLATE_Y0, PLATE_Y1 = 64.0, -100.0, 95.0

# roof (sun shade + panel carrier), tilted 20 deg, front (south, +z) edge low
TILT = 20.0
ROOF_GAP = 25.0                             # min air gap over the box top (at the box front face)
ROOF_W, ROOF_L, ROOF_T, ROOF_LIP = 150.0, 125.0, 3.0, 8.0
ROOF_FRONT_Z = LID_Z1 + 45.0                # front edge projection
PANEL_W, PANEL_L, PANEL_T = 136.0, 110.0, 3.0


def roof_underside_y(z):
    """Height of the roof underside above the box centre at depth z."""
    return EXT_H / 2 + ROOF_GAP + (LID_Z1 - z) * math.tan(math.radians(TILT))


# radiation shield on an arm to the right
SHIELD_X, SHIELD_Z = 150.0, -7.0
ARM_Y = -80.0
SHIELD_TOP_Y = -92.0
SHIELD_N, SHIELD_PITCH, SHIELD_OD, SHIELD_ID = 6, 14.0, 120.0, 50.0

# ---------------------------------------------------------------- colors / materials (glTF PBR)
MAT = {
    "asa_white": dict(rgb=(0.949, 0.945, 0.925), metal=0.0, rough=0.55, density=1.07),
    "asa_grey": dict(rgb=(0.79, 0.80, 0.82), metal=0.0, rough=0.6, density=1.07),
    "silicone": dict(rgb=(0.20, 0.20, 0.21), metal=0.0, rough=0.8, density=1.15),
    "steel": dict(rgb=(0.72, 0.74, 0.76), metal=1.0, rough=0.35, density=7.9),
    "alu": dict(rgb=(0.80, 0.81, 0.83), metal=1.0, rough=0.45, density=2.7),
    "brass": dict(rgb=(0.78, 0.62, 0.30), metal=1.0, rough=0.35, density=8.5),
    "black": dict(rgb=(0.10, 0.10, 0.10), metal=0.0, rough=0.6, density=1.15),
    "panel_back": dict(rgb=(0.063, 0.086, 0.110), metal=0.0, rough=0.4, density=1.9),
    "panel_cell": dict(rgb=(0.09, 0.15, 0.30), metal=0.3, rough=0.25, density=2.3),
    "panel_bus": dict(rgb=(0.80, 0.81, 0.83), metal=1.0, rough=0.3, density=8.9),
    "clear": dict(rgb=(0.90, 0.95, 0.97), metal=0.0, rough=0.1, density=1.19, alpha=0.55),
    "cable": dict(rgb=(0.12, 0.12, 0.13), metal=0.0, rough=0.7, density=1.4),
    "probe": dict(rgb=(0.70, 0.71, 0.70), metal=0.6, rough=0.6, density=7.9),
    "pole": dict(rgb=(0.55, 0.57, 0.58), metal=0.9, rough=0.5, density=7.9),
}


def color(mat):
    r, g, b = MAT[mat]["rgb"]
    return cq.Color(r, g, b, MAT[mat].get("alpha", 1.0))


class Part:
    """A solid with a material, an explode offset (L frame, mm) and a flag for printed parts."""

    def __init__(self, name, shape, mat, explode=(0, 0, 0), printed=False, group=""):
        self.name, self.shape, self.mat = name, shape, mat
        self.explode, self.printed, self.group = explode, printed, group or name

    def solid(self):
        s = self.shape
        return s.val() if isinstance(s, cq.Workplane) else s


# ---------------------------------------------------------------- 2D outlines
def rrect(w, h, r, z=0.0):
    face = cq.Sketch().rect(w, h).vertices().fillet(r)._faces.Faces()[0]
    return face.moved(cq.Location(cq.Vector(0, 0, z))).outerWire()


def ext_face(z=0.0, grow=0.0):
    f = cq.Sketch().rect(EXT_W + 2 * grow, EXT_H + 2 * grow).vertices().fillet(EXT_R + grow)._faces.Faces()[0]
    return f.moved(cq.Location(cq.Vector(0, 0, z)))


def cavity_face(z=0.0, grow=0.0):
    """Cavity outline: rounded rectangle minus the four corner screw columns. grow>0 enlarges."""
    sk = (cq.Sketch().rect(CAV_W + 2 * grow, CAV_H + 2 * grow).vertices().fillet(max(CAV_R + grow, 0.3))
          .push([(sx * CAV_W / 2, sy * CAV_H / 2) for sx in (-1, 1) for sy in (-1, 1)])
          .circle(max(COL_R - grow, 0.5), mode="s"))
    return sk._faces.Faces()[0].moved(cq.Location(cq.Vector(0, 0, z)))


def band_face(z, c_off, half_w):
    """Closed band of width 2*half_w centred on the cavity outline offset by c_off (outward)."""
    outer = cavity_face(z, c_off + half_w)
    inner = cavity_face(z, c_off - half_w)
    return outer.cut(inner)


def prism(face, h):
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, h)))


def tapered(face, h, taper_deg):
    """Extrude a face by h with a draft (taper>0 shrinks along +h)."""
    return cq.Workplane("XY").add(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, h), taper=taper_deg))


def cyl(r, h, base=(0, 0, 0), axis=(0, 0, 1)):
    return cq.Solid.makeCylinder(r, h, cq.Vector(*base), cq.Vector(*axis))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def hexprism(af, h, base=(0, 0, 0), axis=(0, 0, 1)):
    """Hex nut blank: across-flats af, height h, standing on base along axis."""
    wp = cq.Workplane(cq.Plane(origin=base, xDir=_perp(axis), normal=axis))
    return wp.polygon(6, af / math.cos(math.radians(30))).extrude(h).val()


def _perp(axis):
    ax = cq.Vector(*axis).normalized()
    ref = cq.Vector(1, 0, 0) if abs(ax.x) < 0.9 else cq.Vector(0, 1, 0)
    return ref.cross(ax).normalized()
