import sys
sys.path.insert(0, "/snap/kicad/current/usr/lib/python3/dist-packages")
import pcbnew
sys.path.insert(0, "tools")
import design
FPD = "/snap/kicad/current/usr/share/kicad/footprints/"
seen = set()
for p in design.parts:
    if not p["fp"] or p["fp"] in seen: continue
    seen.add(p["fp"])
    lib, name = p["fp"].split(":")
    fp = pcbnew.FootprintLoad(FPD + lib + ".pretty", name)
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False, False)
    pads = [(pd.GetNumber(), round(pcbnew.ToMM(pd.GetPosition().x),2), round(pcbnew.ToMM(pd.GetPosition().y),2)) for pd in fp.Pads()]
    print("%-70s %6.2f x %6.2f  c=(%.2f,%.2f) pads=%d" % (p["fp"], pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()), pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y), len(pads)))
    if name in ("RAK3172","BatteryHolder_Keystone_1042_1x18650","U.FL_Hirose_U.FL-R-SMT-1_Vertical","JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal"):
        print("    ", pads)
