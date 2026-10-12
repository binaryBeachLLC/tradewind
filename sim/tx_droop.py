"""tx_droop — Does +3V3 stay inside ±3 % when the radio keys up, and how much output capacitance is needed?

Deck: sim/spice/tx_droop.cir — an averaged (no switching ripple) model of cell → BQ24074 power path →
TPS63900 → +3V3, with a PI controller (Kp 2.5 A/V, integrator zero ≈ 3 kHz) behind an 8 µs lag that
stands in for the converter's on-time and inductor slew (TI does not publish the loop; this is a
behavioural stand-in tuned to the datasheet's transient plots, so treat absolute mV as ±30 %).
Load: RAK3172 5 mA → 87 mA (+20 dBm TX) for 206 ms (SF9, 24-byte frame), 10 µs edges.
COUT options, effective capacitance after DC-bias derating (X5R 0805 10 V at 3.3 V ≈ 60 %):
   1 × 22 µF → 13.2 µF ;  2 × 22 µF → 26.4 µF ;  2 × 22 µF + 10 µF at the module → 26.4 + 6.0 µF.
Cell at 3.6 V (≈ 30 % SoC — the worst realistic case for supply droop).
Spec: +3V3 within 3.3 V ± 3 % (3.201–3.399 V).
"""
import os

import numpy as np
import matplotlib.pyplot as plt

from common import apply, C, save, fig_path, record, run_spice, read_vec, OUT, FIG_W, limit_line

OPTS = [("1 × 22 µF", 13.2e-6, 1e-12), ("2 × 22 µF", 26.4e-6, 1e-12), ("2 × 22 µF + 10 µF at module (rev B)", 26.4e-6, 6.0e-6)]
KP, CINT = 2.5, 21e-6


def main():
    apply()
    data = []
    for i, (name, co, cm) in enumerate(OPTS):
        tag = f"tx_droop_{i}"
        run_spice("tx_droop.cir", dict(vocv=3.6, cout=co, cmod=cm, kp=KP, cint=CINT, tag=tag), tag=tag)
        d = read_vec(os.path.join(OUT, tag + ".dat"))
        data.append((name, d))

    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(6.8, 3.2), gridspec_kw=dict(width_ratios=[1, 1, 1.1]))
    res = {}
    for k, (name, d) in enumerate(data):
        t = d["time"] * 1e3
        v = d["v(vout)"]
        on = (t > 0.95) & (t < 1.6)
        off = (t > 206.95) & (t < 207.6)
        a1.plot(t[on] - 1.0, v[on] * 1000, color=C.series[k], lw=1.6, label=name)
        a2.plot(t[off] - 207.0, v[off] * 1000, color=C.series[k], lw=1.6, label=name)
        burst = (t > 1.0) & (t < 206.9)
        res[name] = dict(droop_mV=round(float((3.3 - v[(t > 1) & (t < 3)].min()) * 1000), 1),
                         overshoot_mV=round(float((v[(t > 207) & (t < 209)].max() - 3.3) * 1000), 1),
                         within_3pct=bool(v[t > 0.5].min() > 3.201 and v[t > 0.5].max() < 3.399))
    for ax, ttl in [(a1, "TX on (5 → 87 mA)"), (a2, "TX off (87 → 5 mA)")]:
        ax.set(xlim=(-0.05, 0.6), ylim=(3180, 3420), xlabel="Time from edge (ms)", title=ttl)
        ax.axhline(3201, color=C.mute, lw=0.9, ls=(0, (4, 3)))
        ax.axhline(3399, color=C.mute, lw=0.9, ls=(0, (4, 3)))
    a1.set_ylabel("+3V3 (mV)")
    a1.text(0.58, 3205, "−3 %", ha="right", va="bottom", fontsize=7, color=C.mute)
    a2.text(0.58, 3395, "+3 %", ha="right", va="top", fontsize=7, color=C.mute)
    a2.set_yticklabels([])

    name, d = data[2]
    t = d["time"] * 1e3
    a3.plot(t, d["v(vbat)"], color=C.series[3], lw=1.6, label="VBAT (cell, 3.6 V OCV)")
    a3.plot(t, d["v(vsys)"], color=C.series[4], lw=1.6, label="VSYS (charger OUT)")
    a3.set(xlim=(-10, 230), ylim=(3.57, 3.61), xlabel="Time (ms)", ylabel="Volts", title="Cell side (rev B)")
    a3.legend(loc="lower center", fontsize=7)
    h, l = a1.get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.36, -0.01), fontsize=7.5, handlelength=1.3,
               columnspacing=1.0)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, fig_path("tx_droop"), tight=False)

    vb = data[2][1]["v(vbat)"]
    tb = data[2][1]["time"] * 1e3
    res["cell_dip_mV"] = round(float((vb[tb < 0.9].mean() - vb[(tb > 100) & (tb < 200)].mean()) * 1000), 1)
    res["cell_current_mA_during_tx"] = round(float(-data[2][1]["i(VOCV)"][(tb > 100) & (tb < 200)].mean() * 1000), 1)
    record("tx_droop", res)
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()
