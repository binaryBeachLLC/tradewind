"""Protected 18650 cell (68 mm, Ø18.4) for the board render and enclosure fit. Axis along X, centred."""
import cadquery as cq
import os
OUT = os.path.join(os.path.dirname(__file__), "..", "hardware", "tradewind", "3d", "Cell_18650_protected.step")
L, D = 68.0, 18.4
wrap = cq.Workplane("YZ").circle(D / 2).extrude(L - 1.6).translate((-(L - 1.6) / 2, 0, 0)).edges().fillet(0.8)
band = cq.Workplane("YZ").circle(D / 2 + 0.02).circle(D / 2 - 0.2).extrude(6).translate((L / 2 - 14, 0, 0))
cap_pos = cq.Workplane("YZ").circle(D / 2 - 0.6).extrude(0.8).translate((L / 2 - 0.8, 0, 0))
nub = cq.Workplane("YZ").circle(3.5).extrude(0.8).translate((L / 2, 0, 0)).edges(">X").fillet(0.3)
cap_neg = cq.Workplane("YZ").circle(D / 2 - 0.6).extrude(0.8).translate((-L / 2, 0, 0))
asm = cq.Assembly(name="Cell18650")
asm.add(wrap, name="wrap", color=cq.Color(0.10, 0.36, 0.42))
asm.add(band, name="band", color=cq.Color(0.94, 0.54, 0.24))
asm.add(cap_pos.union(nub), name="pos", color=cq.Color(0.80, 0.80, 0.82))
asm.add(cap_neg, name="neg", color=cq.Color(0.80, 0.80, 0.82))
asm.save(OUT)
print("wrote", OUT)
