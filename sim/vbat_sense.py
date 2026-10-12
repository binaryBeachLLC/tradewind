"""vbat_sense — Why the battery divider is switched on the HIGH side (rev B), and how long to wait before sampling.

Deck: sim/spice/vbat_sense.cir (ngspice, level-1 MOSFETs from spice/models.lib).
  Rev A: VBAT → 10 kΩ → ADC → 10 kΩ → low-side BSS138 → GND. With the FET off the ADC pin is pulled
         up to VBAT through 10 kΩ; above ~3.8 V the STM32's clamp diode to VDD (3.3 V) conducts, so
         current flows from the battery into the 3.3 V rail all the time.
  Rev B: AO3401A P-FET on the high side (gate held at VBAT by R9 1 MΩ, pulled low by BSS138 Q3),
         then R11/R12 100 kΩ/100 kΩ and C10 10 nF. Off: only FET leakage (nA).
STM32 ADC pin: clamp diode to VDD + 5 pF; 12-bit, VREF 3.3 V → 0.5 LSB = 0.40 mV.
"""
import os

import numpy as np
import matplotlib.pyplot as plt

from common import apply, C, save, fig_path, record, run_spice, read_vec, OUT, FIG_W, limit_line


def main():
    apply()
    run_spice("vbat_sense.cir")
    dc = read_vec(os.path.join(OUT, "vbat_sense_dc.dat"))
    tr = read_vec(os.path.join(OUT, "vbat_sense_tran.dat"))
    vb = dc["v-sweep"]
    ia = np.abs(dc["i(VMA)"]) * 1e6
    ib = np.abs(dc["i(VMB)"]) * 1e6

    t = tr["time"] * 1e3
    va = tr["v(adcB)"]
    vfinal = va[t > 11.5].mean()
    lsb_half = 0.5 * 3.3 / 4096
    after = t >= 1.0
    bad = np.where(after & (np.abs(va - vfinal) > lsb_half))[0]
    settle_ms = float(t[bad[-1]] - 1.0) if len(bad) else 0.0

    fig, (a1, a2) = plt.subplots(1, 2, figsize=FIG_W)
    a1.semilogy(vb, np.maximum(ia, 1e-4), color=C.series[1], lw=1.8, label="Rev A, low-side switch")
    a1.semilogy(vb, np.maximum(ib, 1e-4), color=C.series[0], lw=1.8, label="Rev B, high-side P-FET")
    a1.set(xlim=(3.0, 4.2), ylim=(1e-3, 100), xlabel="Battery voltage (V)",
           ylabel="Battery current, sensor off (µA)", title="Off-state drain from the cell")
    a1.set_yticks([1e-3, 1e-2, 1e-1, 1, 10, 100])
    a1.set_yticklabels(["0.001", "0.01", "0.1", "1", "10", "100"])
    k = np.argmin(np.abs(vb - 4.1))
    a1.annotate(f"{ia[k]:.0f} µA at 4.1 V", (4.1, ia[k]), xytext=(-40, 4), textcoords="offset points",
                ha="right", va="center", fontsize=7.5, color=C.ink,
                arrowprops=dict(arrowstyle="-", color=C.mute, lw=0.6, shrinkB=3))
    a1.annotate(f"{ib[k] * 1000:.0f} nA", (4.1, ib[k]), xytext=(-10, 10), textcoords="offset points",
                ha="right", fontsize=7.5, color=C.ink)
    a1.legend(loc="center left", bbox_to_anchor=(0, 0.42))

    sel = (t >= 0.5) & (t <= 8)
    a2.plot(t[sel] - 1.0, va[sel] * 1000, color=C.series[0], lw=1.8, label="VBAT_ADC (rev B)")
    a2.set(xlim=(-0.5, 7.5), ylim=(0, 2400), xlabel="Time after VBAT_SENSE_EN (ms)", ylabel="ADC pin (mV)",
           title="Settling after enable, VBAT 4.2 V")
    a2.axvline(settle_ms, color=C.mute, lw=0.9, ls=(0, (4, 3)))
    a2.text(settle_ms + 0.2, 700, f"within ½ LSB\n(12-bit) after\n{settle_ms:.1f} ms;\nfirmware\nsamples at 5 ms",
            fontsize=7.5, color=C.ink, va="bottom", ha="left")
    save(fig, fig_path("vbat_sense"))

    i41 = float(np.interp(4.1, vb, ia))
    record("vbat_sense", {
        "leakage_revA_uA_at_4V2": round(float(ia[-1]), 1),
        "leakage_revA_uA_at_4V1": round(i41, 1),
        "leakage_revA_uA_at_4V05": round(float(np.interp(4.05, vb, ia)), 1),
        "leakage_revA_uA_at_3V7": round(float(np.interp(3.7, vb, ia)), 2),
        "leakage_revB_nA_at_4V2": round(float(ib[-1] * 1000), 1),
        "settle_time_ms_half_lsb": round(settle_ms, 2),
        "adc_sample_delay_ms_chosen": 5.0,
        "adc_reading_V_at_4V2": round(float(vfinal), 4),
    })
    print("leak A 4.2/4.1/3.7", ia[-1], i41, np.interp(3.7, vb, ia), "leak B nA", ib[-1] * 1000, "settle", settle_ms, vfinal)


if __name__ == "__main__":
    main()
