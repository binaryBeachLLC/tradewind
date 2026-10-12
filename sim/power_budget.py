"""power_budget — Where does the charge go, and what is the average current per mode?

Per uplink (at the 3.3 V rail, spec §5): wake + sense 9 mA × 150 ms; TX +20 dBm 87 mA × time-on-air
(from link_budget, 24-byte frame); RX1 + RX2 windows 5.2 mA × 2 × 25 ms; waits between TX and the RX
windows 1.0 mA × 2.0 s. Converted to the battery at 3.7 V through the buck-boost at 90 %
(factor 3.3 / (3.7 · 0.90) = 0.991). Sleep at the battery: 6.9 µA (charger IBAT(PDWN) 4.3 µA +
RAK3172 STOP2 1.69 µA + hall switch 0.54 µA + sensors/leakage ≈ 0.4 µA, the 3.3 V loads scaled by the
same factor). Self-discharge of the Li-ion cell (≈ 3 mAh/day at 25–35 °C) is reported separately.
"""
import csv
import os

import numpy as np
import matplotlib.pyplot as plt

from common import apply, C, save, fig_path, record, FIG_W, OUT
from link_budget import airtime_ms

K_BAT = 3.3 / (3.7 * 0.90)
SLEEP_UA = 6.9
SELF_DISCHARGE_MAH_DAY = 3.0
CAP_USABLE_MAH = 3350 * 0.8


def per_uplink_mC(sf):
    return {
        "Wake + sense": 9.0 * 0.150,
        "TX (+20 dBm)": 87.0 * airtime_ms(sf) / 1000,
        "RX windows": 5.2 * 0.050,
        "Waits between windows": 1.0 * 2.0,
    }


def average_ua(sf, interval_s):
    parts = {"Sleep": SLEEP_UA}
    for k, q in per_uplink_mC(sf).items():
        parts[k] = q * K_BAT / interval_s * 1000      # mC/s = mA -> µA
    return parts


def main():
    apply()
    rows = []
    for interval, mode in [(300, "5-min"), (60, "1-min rapid")]:
        for sf in [7, 9, 10]:
            p = average_ua(sf, interval)
            tot = sum(p.values())
            mah_day = tot * 24 / 1000
            autonomy = CAP_USABLE_MAH / (mah_day + SELF_DISCHARGE_MAH_DAY)
            rows.append(dict(mode=mode, sf=sf, parts=p, total=tot, mah_day=mah_day, autonomy=autonomy,
                             per_uplink=sum(per_uplink_mC(sf).values())))

    cats = ["Sleep", "Wake + sense", "TX (+20 dBm)", "RX windows", "Waits between windows"]
    fig, axes = plt.subplots(1, 2, figsize=FIG_W, sharey=False)
    for ax, mode, xmax in [(axes[0], "5-min", 140), (axes[1], "1-min rapid", 700)]:
        sub = [r for r in rows if r["mode"] == mode]
        y = np.arange(len(sub))[::-1]
        left = np.zeros(len(sub))
        for ci, cat in enumerate(cats):
            vals = np.array([r["parts"][cat] for r in sub])
            ax.barh(y, vals, left=left, height=0.55, color=C.series[ci], edgecolor="white", linewidth=1.0,
                    label=cat)
            left += vals
        for yy, r in zip(y, sub):
            ax.text(r["total"] + xmax * 0.015, yy, f"{r['total']:.0f} µA", va="center", fontsize=7.5, color=C.ink)
        ax.set_yticks(y)
        ax.set_yticklabels([f"SF{r['sf']}" for r in sub])
        ax.set(xlim=(0, xmax), xlabel="Average current at the battery (µA)", title=f"{mode} uplinks")
        ax.grid(axis="y", visible=False)
        ax.set_axisbelow(True)
    if True:
        r9 = next(r for r in rows if r["mode"] == "5-min" and r["sf"] == 9)
        axes[0].axvline(100, color=C.mute, lw=0.9, ls=(0, (4, 3)))
        axes[0].text(100, 2.45, " R3 target 100 µA", fontsize=7, color=C.mute, va="bottom")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.01), handlelength=1.2,
               columnspacing=1.0, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, fig_path("power_budget"), tight=False)

    with open(os.path.join(OUT, "power_budget.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mode", "SF", "per_uplink_mC_3v3"] + [c + "_uA" for c in cats] +
                   ["total_uA", "mAh_per_day", "dark_autonomy_days_incl_self_discharge"])
        for r in rows:
            w.writerow([r["mode"], r["sf"], round(r["per_uplink"], 2)] + [round(r["parts"][c], 2) for c in cats] +
                       [round(r["total"], 1), round(r["mah_day"], 2), round(r["autonomy"], 0)])
    record("power_budget", {
        "sleep_uA": SLEEP_UA,
        "per_uplink_mC_3v3": {f"SF{sf}": round(sum(per_uplink_mC(sf).values()), 2) for sf in [7, 9, 10]},
        "avg_current_uA": {f"{r['mode']} SF{r['sf']}": round(r["total"], 1) for r in rows},
        "mAh_per_day": {f"{r['mode']} SF{r['sf']}": round(r["mah_day"], 2) for r in rows},
        "dark_autonomy_days_incl_self_discharge": {f"{r['mode']} SF{r['sf']}": round(r["autonomy"]) for r in rows},
    })
    for r in rows:
        print(r["mode"], r["sf"], round(r["total"], 1), round(r["mah_day"], 2), round(r["autonomy"]))


if __name__ == "__main__":
    main()
