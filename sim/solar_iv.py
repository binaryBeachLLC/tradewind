"""solar_iv — How much of the panel's power does the BQ24074's fixed 4.5 V VIN-DPM capture?

Model: single-diode PV model, 10 series mono cells (a "5 V" panel: 0.60 V/cell open circuit).
    I = Iph - I0*(exp((V + I*Rs)/(n*Ns*Vt)) - 1) - (V + I*Rs)/Rsh
Fitted at STC (1000 W/m², 25 °C cell) to the spec's datasheet points: Voc 6.0 V, Isc 0.44 A,
Vmp 5.0 V, Imp 0.40 A (dP/dV = 0 at Vmp). Rsh fixed at 800 Ω (typical small epoxy panel).
Irradiance: Iph ∝ G. Temperature: Isc +0.05 %/°C; I0(T) re-fitted so Voc follows −0.33 %/°C.

The charger (EN2=LO, EN1=HI, USB500) draws up to 475 mA. The panel's Isc (0.44 A) is below that,
so whenever the battery wants current the input collapses until VIN-DPM holds it at 4.5 V
(4.35–4.63 V across parts). The operating point is therefore V = 4.5 V and, because a linear
charger passes input current straight to the battery, the charge current equals I_panel(4.5 V).
"""
import numpy as np
from scipy.optimize import brentq, least_squares

from common import apply, C, save, fig_path, record, FIG_W
import matplotlib.pyplot as plt

NS = 10
K, Q = 1.380649e-23, 1.602176634e-19
VOC, ISC, VMP, IMP = 6.0, 0.44, 5.0, 0.40
RSH = 800.0
DPM, DPM_LO, DPM_HI = 4.5, 4.35, 4.63


def vt(tc):
    return K * (tc + 273.15) / Q


def current(v, iph, i0, n, rs, rsh, tc):
    a = n * NS * vt(tc)
    f = lambda i: iph - i0 * (np.exp((v + i * rs) / a) - 1) - (v + i * rs) / rsh - i
    lo, hi = -2.0, iph + 0.5
    if f(lo) * f(hi) > 0:
        return 0.0
    return brentq(f, lo, hi)


def fit_stc():
    def eqs(p):
        log_i0, n, rs = p
        i0 = np.exp(log_i0)
        a = n * NS * vt(25)
        iph = ISC * (1 + rs / RSH) + i0 * (np.exp(ISC * rs / a) - 1)
        e1 = iph - i0 * (np.exp(VOC / a) - 1) - VOC / RSH                       # I(Voc) = 0
        e2 = iph - i0 * (np.exp((VMP + IMP * rs) / a) - 1) - (VMP + IMP * rs) / RSH - IMP
        # dP/dV = 0 at MPP  ->  dI/dV = -Imp/Vmp ; implicit derivative of the diode equation
        g = i0 / a * np.exp((VMP + IMP * rs) / a) + 1 / RSH
        didv = -g / (1 + g * rs)
        e3 = didv + IMP / VMP
        return [e1, e2, e3]
    sol = least_squares(lambda p: np.array(eqs(p)) * [100, 100, 10], [np.log(7e-9), 1.3, 0.1],
                        bounds=([np.log(1e-14), 0.9, 0.0], [np.log(1e-5), 2.0, 2.0]), xtol=1e-14, ftol=1e-14)
    log_i0, n, rs = sol.x
    i0 = np.exp(log_i0)
    a = n * NS * vt(25)
    iph = ISC * (1 + rs / RSH) + i0 * (np.exp(ISC * rs / a) - 1)
    return dict(iph=iph, i0=i0, n=n, rs=rs, rsh=RSH)


P0 = fit_stc()


def params(g, tc):
    """Model parameters at irradiance g (W/m²) and cell temperature tc (°C)."""
    dt = tc - 25
    iph = P0["iph"] * g / 1000 * (1 + 0.0005 * dt)
    voc_t = VOC * (1 - 0.0033 * dt)
    a = P0["n"] * NS * vt(tc)
    # choose I0 so that Voc at 1000 W/m² follows the datasheet coefficient
    iph_stc_t = P0["iph"] * (1 + 0.0005 * dt)
    i0 = (iph_stc_t - voc_t / RSH) / (np.exp(voc_t / a) - 1)
    return dict(iph=iph, i0=i0, n=P0["n"], rs=P0["rs"], rsh=RSH, tc=tc)


def iv(g, tc, v):
    p = params(g, tc)
    return np.array([max(current(x, **p), 0.0) for x in v])


def mpp(g, tc):
    v = np.linspace(0, 7, 1401)
    i = iv(g, tc, v)
    k = np.argmax(v * i)
    return v[k], i[k], v[k] * i[k]


def at(g, tc, vop):
    p = params(g, tc)
    i = max(current(vop, **p), 0.0)
    return i, i * vop


def main():
    apply()
    v = np.linspace(0, 6.6, 661)
    conds = [(1000, 25), (600, 25), (300, 25), (100, 25), (1000, 55), (600, 45), (300, 35), (100, 28)]
    rows = []
    for g, tc in conds:
        vm, im, pm = mpp(g, tc)
        i45, p45 = at(g, tc, DPM)
        _, plo = at(g, tc, DPM_LO)
        _, phi = at(g, tc, DPM_HI)
        rows.append(dict(G=g, Tcell=tc, Vmp=vm, Pmp=pm, I_dpm=i45, P_dpm=p45,
                         capture=100 * p45 / pm, capture_lo=100 * plo / pm, capture_hi=100 * phi / pm))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=FIG_W)
    for k, g in enumerate([1000, 600, 300, 100]):
        i = iv(g, 25, v)
        a1.plot(v, i * 1000, color=C.series[k], label=f"{g} W/m²")
    a1.axvspan(DPM_LO, DPM_HI, color=C.band, zorder=0, lw=0)
    a1.axvline(DPM, color=C.mute, lw=0.9, ls=(0, (4, 3)))
    a1.text(DPM - 0.08, 470, "VIN-DPM 4.5 V", ha="right", va="center", fontsize=7.5, color=C.mute)
    a1.set(xlim=(0, 6.6), ylim=(0, 500), xlabel="Panel voltage (V)", ylabel="Panel current (mA)",
           title="I–V, cell at 25 °C")
    a1.legend(loc="upper left", bbox_to_anchor=(0.0, 0.85), handlelength=1.4)

    for col, tc, lab in [(C.series[0], 25, "Cell 25 °C"), (C.series[4], 55, "Cell 55 °C (in sun)")]:
        p = v * iv(1000, tc, v)
        a2.plot(v, p, color=col, label=lab)
        vm, im, pm = mpp(1000, tc)
        _, p45 = at(1000, tc, DPM)
        a2.plot([vm], [pm], "o", color=col, ms=5, mec="white", mew=1.2, zorder=5)
        a2.plot([DPM], [p45], "s", color=col, ms=5, mec="white", mew=1.2, zorder=5)
        a2.annotate(f"{100 * p45 / pm:.0f} % of MPP", (DPM, p45), xytext=(-6, -50 if tc == 55 else 12),
                    textcoords="offset points", ha="right", fontsize=7.5, color=C.ink,
                    arrowprops=dict(arrowstyle="-", color=C.mute, lw=0.6, shrinkA=1, shrinkB=4))
    a2.axvspan(DPM_LO, DPM_HI, color=C.band, zorder=0, lw=0)
    a2.axvline(DPM, color=C.mute, lw=0.9, ls=(0, (4, 3)))
    a2.set(xlim=(0, 6.6), ylim=(0, 2.7), xlabel="Panel voltage (V)", ylabel="Panel power (W)",
           title="P–V at 1000 W/m²")
    a2.legend(loc="upper left")
    save(fig, fig_path("solar_iv"))

    hot = next(r for r in rows if r["G"] == 1000 and r["Tcell"] == 55)
    stc = next(r for r in rows if r["G"] == 1000 and r["Tcell"] == 25)
    import csv, os
    from common import OUT
    with open(os.path.join(OUT, "solar_iv_capture.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: round(x, 4) for k, x in r.items()})
    record("solar_iv", {
        "fit": {k: float(f"{v:.4g}") for k, v in P0.items()},
        "cells_series": NS,
        "mpp_capture_stc_pct": round(stc["capture"], 1),
        "mpp_capture_hot_pct": round(hot["capture"], 1),
        "mpp_capture_hot_range_pct": [round(hot["capture_lo"], 1), round(hot["capture_hi"], 1)],
        "vmp_hot_V": round(hot["Vmp"], 2),
        "charge_current_hot_mA": round(hot["I_dpm"] * 1000, 0),
        "charge_current_stc_mA": round(stc["I_dpm"] * 1000, 0),
        "table": [{k: round(x, 3) for k, x in r.items()} for r in rows],
    })
    for r in rows:
        print({k: round(x, 3) for k, x in r.items()})
    print("fit", P0)


if __name__ == "__main__":
    main()
