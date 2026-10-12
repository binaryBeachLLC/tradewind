"""rain_debounce — One bucket tip must make exactly one count, even while the MCU sleeps.

Deck: sim/spice/rain_debounce.cir. Reed switch as an ideal switch driven by a measured-style bounce
pattern (three opening bounces of 100–300 µs at closure, two re-closures at release); 5 m cable ≈ 100 pF.
Rev B: R23 1 MΩ pull-up, R24 10 kΩ series, C22 22 nF at PA0 → fall τ = 0.22 ms, rise τ ≈ 22 ms.
Rev A: same resistors, no capacitor → the pin follows every bounce (τ ≈ 0.1 ms through the cable C).
The STM32 input is a Schmitt trigger: VIL 0.3·VDD = 0.99 V, VIH 0.7·VDD = 2.31 V. EXTI counts falling
edges, so a count = the pin going below VIL after it was last above VIH. This is done in Python on the
simulated waveform (an ideal comparator with that hysteresis).
Max count rate: the pin must climb back above VIH between tips: t_rise = τ·ln(VDD/(VDD−VIH)).
"""
import os

import numpy as np
import matplotlib.pyplot as plt

from common import apply, C, save, fig_path, record, run_spice, read_vec, OUT, FIG_W

VDD, VIL, VIH = 3.3, 0.99, 2.31


def schmitt_counts(t, v):
    state = 1 if v[0] > VIH else 0
    edges = []
    for ti, vi in zip(t, v):
        if state == 1 and vi < VIL:
            state = 0
            edges.append(ti)
        elif state == 0 and vi > VIH:
            state = 1
    return edges


def main():
    apply()
    run_spice("rain_debounce.cir")
    d = read_vec(os.path.join(OUT, "rain_debounce.dat"))
    t = d["time"] * 1e3
    ca = schmitt_counts(t, d["v(inA)"])
    cb = schmitt_counts(t, d["v(inB)"])

    fig, (a1, a2) = plt.subplots(1, 2, figsize=FIG_W, gridspec_kw=dict(width_ratios=[1.15, 1]))
    sel = (t >= 9.8) & (t <= 11.8)
    a1.plot(t[sel], d["v(inA)"][sel], color=C.series[1], lw=1.4, label=f"Rev A, no cap: {len(ca)} counts")
    a1.plot(t[sel], d["v(inB)"][sel], color=C.series[0], lw=1.8, label=f"Rev B, 10 kΩ + 22 nF: {len(cb)} count")
    for y, lab in [(VIL, "VIL 0.99 V"), (VIH, "VIH 2.31 V")]:
        a1.axhline(y, color=C.mute, lw=0.9, ls=(0, (4, 3)))
        a1.text(11.78, y + 0.05, lab, ha="right", va="bottom", fontsize=7, color=C.mute)
    for e in ca:
        if 9.8 <= e <= 11.8:
            a1.plot([e], [VIL], "v", color=C.series[1], ms=5, zorder=5)
    a1.set(xlim=(9.8, 11.8), ylim=(-0.2, 3.9), xlabel="Time (ms)", ylabel="PA0 (V)",
           title="Reed closure, with bounce")
    a1.legend(loc="upper right", fontsize=7.5)

    a2.plot(t, d["v(inA)"], color=C.series[1], lw=1.0, label="Rev A")
    a2.plot(t, d["v(inB)"], color=C.series[0], lw=1.8, label="Rev B")
    a2.axhline(VIL, color=C.mute, lw=0.9, ls=(0, (4, 3)))
    a2.axhline(VIH, color=C.mute, lw=0.9, ls=(0, (4, 3)))
    tr = 1.01e6 * 22e-9 * np.log(VDD / (VDD - VIH)) * 1e3
    a2.annotate(f"slow release: back above\nVIH {tr:.0f} ms after it opens",
                (60 + tr, VIH), xytext=(20, 1.55), textcoords="data", ha="left", fontsize=7.5,
                color=C.ink, arrowprops=dict(arrowstyle="-", color=C.mute, lw=0.6))
    a2.set(xlim=(0, 100), ylim=(-0.2, 3.9), xlabel="Time (ms)", title="One full tip (closed 10–60 ms)")
    a2.legend(loc="lower right", fontsize=7.5)
    save(fig, fig_path("rain_debounce"))

    closure_ms = 50.0
    max_rate = 1000.0 / (closure_ms + tr)
    record("rain_debounce", {
        "counts_revA_one_tip": len(ca), "counts_revB_one_tip": len(cb),
        "fall_tau_ms": round(10e3 * 22e-9 * 1e3, 3), "rise_tau_ms": round(1.01e6 * 22e-9 * 1e3, 1),
        "time_back_above_VIH_ms": round(tr, 1),
        "max_tip_rate_per_s_with_50ms_closure": round(max_rate, 1),
        "real_gauge_max_tips_per_s": 2.0,
        "pullup_current_uA_when_reed_stuck_closed": round(3.3 / 1.01e6 * 1e6, 2),
    })
    print("A counts", len(ca), ca, "B counts", len(cb), cb, "tr", tr, "max rate", max_rate)


if __name__ == "__main__":
    main()
