"""link_budget — How far does the TW-1 reach, and how long is each uplink on air?

Airtime: Semtech LoRa time-on-air formula (AN1200.13), BW 125 kHz, CR 4/5, explicit header, CRC on,
8-symbol preamble, low-data-rate optimisation off for SF7–SF10. Frame = 24 bytes
(13 B LoRaWAN overhead + 11 B application payload).

Link: TX +20 dBm conducted, 0.5 dB node pigtail/cable, 2 dBi node whip, 5 dBi gateway antenna,
1 dB gateway feeder. Sensitivities (SX126x, BW125): SF7 −123, SF8 −126, SF9 −129, SF10 −132 dBm.
Path loss: Okumura–Hata "open area" at 915 MHz, gateway mast 10 m, node 1.5 m, plus 5 dB of
agricultural clutter (orchards, windbreaks) — i.e. between Hata open and suburban. Ranges are quoted
with a 10 dB fade margin (shadowing σ ≈ 6–8 dB).
"""
import csv
import math
import os

import numpy as np
import matplotlib.pyplot as plt

from common import apply, C, save, fig_path, record, limit_line, FIG_W, OUT

SFS = [7, 8, 9, 10]
SENS = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0}
TX, NODE_LOSS, NODE_GAIN, GW_GAIN, GW_LOSS = 20.0, 0.5, 2.0, 5.0, 1.0
F_MHZ, HB, HM = 915.0, 10.0, 1.5
CLUTTER = 5.0
MARGIN = 10.0
PAYLOAD = 24


def airtime_ms(sf, pl=PAYLOAD, bw=125e3, cr=1, preamble=8, crc=1, ih=0):
    de = 1 if (sf >= 11 and bw == 125e3) else 0
    tsym = (2 ** sf) / bw
    t_pre = (preamble + 4.25) * tsym
    n = 8 + max(math.ceil((8 * pl - 4 * sf + 28 + 16 * crc - 20 * ih) / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return 1000 * (t_pre + n * tsym)


def path_loss(d_km):
    lf, lhb = math.log10(F_MHZ), math.log10(HB)
    a_hm = (1.1 * lf - 0.7) * HM - (1.56 * lf - 0.8)
    lu = 69.55 + 26.16 * lf - 13.82 * lhb - a_hm + (44.9 - 6.55 * lhb) * np.log10(d_km)
    lo = lu - 4.78 * lf ** 2 + 18.33 * lf - 40.94
    return lo + CLUTTER


def rx_power(d_km):
    return TX - NODE_LOSS + NODE_GAIN + GW_GAIN - GW_LOSS - path_loss(d_km)


def max_range_km(sf, margin=MARGIN):
    d = np.logspace(-1, 2, 20001)
    ok = rx_power(d) >= SENS[sf] + margin
    return float(d[ok].max())


def main():
    apply()
    air = {sf: airtime_ms(sf) for sf in SFS}
    rng = {sf: max_range_km(sf) for sf in SFS}
    rng0 = {sf: max_range_km(sf, 0) for sf in SFS}

    fig, (a1, a2) = plt.subplots(1, 2, figsize=FIG_W, gridspec_kw=dict(width_ratios=[1.7, 1]))
    d = np.logspace(-1, math.log10(40), 400)
    a1.plot(d, rx_power(d), color=C.series[0], lw=2, label="Median received power")
    a1.set_xscale("log")
    a1.set(xlim=(0.1, 40), ylim=(-145, -55), xlabel="Distance to gateway (km)", ylabel="Received power (dBm)",
           title="Link budget, +20 dBm, 10 m gateway mast")
    a1.set_xticks([0.1, 0.3, 1, 3, 10, 30])
    a1.set_xticklabels(["0.1", "0.3", "1", "3", "10", "30"])
    for sf in SFS:
        y = SENS[sf] + MARGIN
        a1.axhline(SENS[sf], color=C.mute, lw=0.8, ls=(0, (4, 3)))
        a1.plot([rng[sf]], [y], "o", ms=4.5, color=C.series[0], mec="white", mew=1, zorder=5)
    a1.annotate(f"SF10: {rng[10]:.1f} km\nwith 10 dB margin", (rng[10], SENS[10] + MARGIN), xytext=(0.9, -95),
                textcoords="data", ha="right", fontsize=7.5, color=C.ink,
                arrowprops=dict(arrowstyle="-", color=C.mute, lw=0.6))
    a1.text(0.107, -133.5, "Gateway sensitivity, dashed:\n" + ", ".join(f"SF{sf} {SENS[sf]:.0f}" for sf in SFS) + " dBm",
            color=C.mute, va="top", fontsize=8.5)
    a1.text(0.6, -60, "Dots: range with a 10 dB fade margin\n(SF7 → SF10, left to right)",
            color=C.ink, va="top")

    x = np.arange(len(SFS))
    a2.bar(x, [air[s] for s in SFS], width=0.6, color=C.series[0])
    for i, s in enumerate(SFS):
        a2.text(i, air[s] + 6, f"{air[s]:.0f}", ha="center", fontsize=7.5, color=C.ink)
    a2.set_xticks(x)
    a2.set_xticklabels([f"SF{s}" for s in SFS])
    a2.set(ylim=(0, 420), ylabel="Time on air (ms)", title="Airtime, 24 B frame")
    a2.grid(axis="x", visible=False)
    a2.set_axisbelow(True)
    save(fig, fig_path("link_budget"))

    with open(os.path.join(OUT, "link_budget.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["SF", "sensitivity_dBm", "airtime_ms", "range_km_10dB_margin", "range_km_no_margin"])
        for s in SFS:
            w.writerow([s, SENS[s], round(air[s], 1), round(rng[s], 2), round(rng0[s], 2)])
    record("link_budget", {
        "airtime_ms": {f"SF{s}": round(air[s], 1) for s in SFS},
        "range_km_10dB_margin": {f"SF{s}": round(rng[s], 1) for s in SFS},
        "range_km_no_margin": {f"SF{s}": round(rng0[s], 1) for s in SFS},
        "max_path_loss_dB_SF10_with_margin": round(TX - NODE_LOSS + NODE_GAIN + GW_GAIN - GW_LOSS - SENS[10] - MARGIN, 1),
        "path_loss_1km_dB": round(float(path_loss(1.0)), 1),
    })
    print(air, rng, rng0)


if __name__ == "__main__":
    main()
