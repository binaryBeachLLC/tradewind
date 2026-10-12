"""Costed BOM for Tradewind TW-1 rev B, grouped by part, from tools/design.py.

Writes hardware/fab/BOM_tradewind_revB.csv (engineering BOM with unit prices at 10 / 100 / 1k),
hardware/fab/BOM_JLCPCB.csv (assembler format) and hardware/fab/bom_summary.json.
Prices are typical distributor quantity-break prices (Oct 2026) — refresh before ordering.
"""
import csv
import json
import os
from collections import OrderedDict

import design

HERE = os.path.dirname(os.path.abspath(__file__))
FAB = os.path.join(HERE, "..", "hardware", "fab")

# MPN -> (price@10, @100, @1k) USD
PRICE = {
    "RAK3172-8-SM-I": (7.90, 6.90, 5.95), "BQ24074RGTR": (2.10, 1.55, 1.10), "TPS63900DSKR": (1.95, 1.45, 1.05),
    "SHT40-BD1B-R2": (1.80, 1.35, 0.98), "TPS22917DBVR": (0.42, 0.29, 0.19), "TPD4E02B04DQAR": (0.45, 0.31, 0.21),
    "DRV5032FBDBZR": (0.62, 0.45, 0.32), "DMP3099L-7": (0.30, 0.18, 0.11), "AO3401A": (0.12, 0.06, 0.035),
    "BSS138LT1G": (0.10, 0.05, 0.03), "SMAJ12CA": (0.25, 0.14, 0.09), "DFE252012F-2R2M=P2": (0.28, 0.19, 0.13),
    "LQG15HS7N5J02D": (0.10, 0.05, 0.025), "U.FL-R-SMT-1(10)": (0.48, 0.33, 0.22),
    "S2B-PH-SM4-TB(LF)(SN)": (0.30, 0.21, 0.15), "S3B-PH-SM4-TB(LF)(SN)": (0.33, 0.23, 0.17),
    "S4B-PH-SM4-TB(LF)(SN)": (0.36, 0.25, 0.18), "1042": (3.20, 2.45, 1.90), "B3U-1000P": (0.65, 0.50, 0.38),
    "LTST-C191KGKT": (0.12, 0.06, 0.03), "MF-PSMF010X-2": (0.20, 0.12, 0.08), "NCP15XH103F03RC": (0.10, 0.05, 0.03),
    "GRM155R71C104KA88D": (0.02, 0.008, 0.004), "GRM155R71C103KA01D": (0.02, 0.008, 0.004),
    "GRM155R71H102KA01D": (0.02, 0.008, 0.004), "GRM155R71C223KA01D": (0.02, 0.008, 0.004),
    "GRM188R61A106KE69D": (0.08, 0.04, 0.02), "GRM188R61A475KE15D": (0.06, 0.03, 0.015),
    "GRM21BR61A226ME51L": (0.15, 0.08, 0.045), "GRM21BR61E106KA73L": (0.12, 0.06, 0.035),
    "GRM188R61E105KA12D": (0.04, 0.02, 0.01), "GRM155R61A105KE15D": (0.03, 0.012, 0.007),
    "GJM1555C1H1R8BB01D": (0.03, 0.012, 0.006),
}
RES = (0.01, 0.004, 0.002)
EXTRA = [  # non-schematic items in the electronics cost
    ("PCB", "Bare board, 4-layer 1.6 mm, ENIG, black mask, 96 × 70 mm", (6.50, 2.20, 1.15)),
    ("PCBA", "SMT assembly, one side (setup amortised)", (14.00, 3.10, 1.45)),
]
CELL = ("BAT", "Protected 18650 Li-ion 3350 mAh (shipped at 30 % SoC)", (7.50, 6.20, 4.80))
LCSC = {"RAK3172-8-SM-I": "C2924540", "BQ24074RGTR": "C54313", "TPS63900DSKR": "C2683460", "SHT40-BD1B-R2": "C2758077",
        "TPS22917DBVR": "C2155396", "TPD4E02B04DQAR": "C1974361", "DRV5032FBDBZR": "C1850416", "AO3401A": "C15127",
        "BSS138LT1G": "C78284", "DMP3099L-7": "C155407", "SMAJ12CA": "C113951", "U.FL-R-SMT-1(10)": "C88374"}


def build():
    groups = OrderedDict()
    for p in design.parts:
        if not p["bom"] or p["dnp"] or p["ref"].startswith("#"):
            continue
        key = (p["mpn"], p["value"], p["fp"].split(":")[-1])
        g = groups.setdefault(key, dict(refs=[], p=p))
        g["refs"].append(p["ref"])
    rows = []
    for (mpn, value, fp), g in groups.items():
        p = g["p"]
        price = PRICE.get(mpn, RES if p["lib"] == "Device:R" else (0.02, 0.01, 0.005))
        n = len(g["refs"])
        refs = sorted(g["refs"], key=lambda r: (r.rstrip("0123456789"), int("".join(c for c in r if c.isdigit()) or 0)))
        rows.append(dict(Item=len(rows) + 1, Qty=n, References=" ".join(refs), Value=value, Description=p["desc"],
                         Manufacturer=p["mfr"], MPN=mpn, Footprint=fp, LCSC=LCSC.get(mpn, ""),
                         Unit_10=price[0], Unit_100=price[1], Unit_1k=price[2],
                         Ext_1k=round(price[2] * n, 4)))
    os.makedirs(FAB, exist_ok=True)
    cols = list(rows[0].keys())
    with open(os.path.join(FAB, "BOM_tradewind_revB.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
        for code, desc, pr in EXTRA + [CELL]:
            w.writerow(dict(Item="", Qty=1, References=code, Value="", Description=desc, Unit_10=pr[0],
                            Unit_100=pr[1], Unit_1k=pr[2], Ext_1k=pr[2]))
    with open(os.path.join(FAB, "BOM_JLCPCB.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for r in rows:
            w.writerow([r["Value"] + " " + r["MPN"], ",".join(r["References"].split()), r["Footprint"], r["LCSC"]])

    def total(i):
        parts = sum(r["Qty"] * [r["Unit_10"], r["Unit_100"], r["Unit_1k"]][i] for r in rows)
        return parts, parts + sum(e[2][i] for e in EXTRA)
    summ = {}
    for i, q in enumerate(("10", "100", "1000")):
        parts, board = total(i)
        summ[q] = dict(components=round(parts, 2), electronics_incl_pcb_pcba=round(board, 2),
                       with_cell=round(board + CELL[2][i], 2))
    summ["line_items"] = len(rows)
    summ["placements"] = sum(r["Qty"] for r in rows)
    summ["unique_mpns"] = len({r["MPN"] for r in rows})
    json.dump(summ, open(os.path.join(FAB, "bom_summary.json"), "w"), indent=2)
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    build()
