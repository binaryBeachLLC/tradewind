"""3D model for the RAK3172 module (not in KiCad's library): 15.5 x 15.5 mm board, shield can, castellations.
Origin = footprint origin (module centre), Z = 0 at the host board's top surface."""
import cadquery as cq
import os
OUT = os.path.join(os.path.dirname(__file__), "..", "hardware", "tradewind", "3d", "RAK3172.step")
S, T = 15.5, 0.8
base = cq.Workplane("XY").rect(S, S).extrude(T)
# castellations: half-holes on the pad pitch along the four sides (1.0 mm pitch)
cuts = []
for i in range(12):
    y = -5.75 + i * 1.0
    cuts += [(-S / 2, y), (S / 2, y)]
for i in range(8):
    x = -3.5 + i * 1.0
    cuts += [(x, -S / 2), (x, S / 2)]
base = base.cut(cq.Workplane("XY").pushPoints(cuts).circle(0.3).extrude(T))
pads = cq.Workplane("XY").pushPoints(cuts).rect(0.6, 0.6).extrude(0.05).translate((0, 0, -0.02))
can = (cq.Workplane("XY").workplane(offset=T).rect(13.6, 13.6).extrude(1.7)
       .edges("|Z").fillet(0.6).faces(">Z").edges().fillet(0.25))
label = (cq.Workplane("XY").workplane(offset=T + 1.7).rect(9.0, 6.0).extrude(0.02))
asm = cq.Assembly(name="RAK3172")
asm.add(base, name="pcb", color=cq.Color(0.08, 0.22, 0.12))
asm.add(pads, name="pads", color=cq.Color(0.85, 0.7, 0.3))
asm.add(can, name="shield", color=cq.Color(0.78, 0.79, 0.80))
asm.add(label, name="label", color=cq.Color(0.95, 0.95, 0.95))
asm.save(OUT)
print("wrote", OUT)
