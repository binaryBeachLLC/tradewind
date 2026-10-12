"""EMC pre-compliance: radiated emissions scan (FCC 15.109 class B), conducted TX harmonics at J5 with the
rev A and rev B match, and receiver desensitisation from the board's own noise.

Reads: emi_radiated_prescan.csv, emi_radiated_qp.csv, tx_harmonics_conducted.csv, rx_desense.csv
Writes: docs/figures/test_emi_radiated, test_tx_harmonics; results.json["emc"]
Not an accredited test: these runs find the margins and the sources before the lab visit.
"""
import numpy as np

from testlib import C, FIG_W, fig_path, log, plt, save, sim_results, store

res = {}

# ---------------------------------------------------------------- radiated pre-scan
s = log("emi_radiated_prescan.csv")
q = log("emi_radiated_qp.csv")


def limit(fx):
    return np.where(fx < 88, 40.0, np.where(fx < 216, 43.5, np.where(fx < 960, 46.0, 54.0)))


fig, ax = plt.subplots(figsize=FIG_W)
ax.plot(s.freq_MHz, s.peak_dBuV_m_H, lw=0.8, color=C.series[0], label="Peak, horizontal")
ax.plot(s.freq_MHz, s.peak_dBuV_m_V, lw=0.8, color=C.series[1], label="Peak, vertical")
ff = np.geomspace(30, 1000, 400)
ax.plot(ff, limit(ff), color=C.mute, lw=1.0, ls=(0, (4, 3)), drawstyle="steps-post")
ax.text(32, 38.6, "FCC 15.109 class B (QP), 3 m", color=C.mute, va="top")
ax.plot(q.freq_MHz, q.qp_dBuV_m, "D", ms=4.5, color=C.ink, label="Quasi-peak re-measure", zorder=5)
w = q.loc[q.margin_dB.idxmin()]
ax.annotate("%.0f MHz: %.1f dB margin" % (w.freq_MHz, w.margin_dB), (w.freq_MHz, w.qp_dBuV_m), xytext=(14, 10),
            textcoords="offset points", fontsize=7.5, color=C.ink, arrowprops=dict(arrowstyle="-", color=C.mute, lw=0.7))
ax.set_xscale("log")
ax.set_xlim(30, 1000)
ax.set_ylim(10, 55)
ax.set_xticks([30, 50, 100, 200, 300, 500, 1000], ["30", "50", "100", "200", "300", "500", "1000"])
ax.xaxis.set_minor_formatter(plt.NullFormatter())
ax.set_xlabel("Frequency (MHz)")
ax.set_ylabel("Field strength at 3 m (dBµV/m)")
ax.set_title("Radiated emissions pre-scan, radio idle, charger running")
ax.legend(loc="upper left", ncol=3, bbox_to_anchor=(0.0, 1.0))
save(fig, fig_path("emi_radiated"))
res["radiated"] = dict(min_margin_dB=float(q.margin_dB.min()), at_MHz=float(w.freq_MHz), source=w.attributed_to,
                       qp=q.to_dict("records"))

# ---------------------------------------------------------------- conducted harmonics
h = log("tx_harmonics_conducted.csv")
G_HARM_DBI = 0.0                      # whip gain off-resonance at 1.8–4.6 GHz (assumed)
RESTRICTED = [(2690, 2900), (3600, 4400), (4500, 5150)]


def restricted(fx):
    return any(a <= fx <= b for a, b in RESTRICTED)


rows = []
for (rev, n), g in h.groupby(["rev", "harmonic"]):
    fund = h[(h.rev == rev) & (h.harmonic == 1)].p_dBm.min()
    worst = g.p_dBm.max()
    f_lo, f_hi = g.freq_MHz.min(), g.freq_MHz.max()
    rows.append(dict(rev=rev, n=int(n), f_lo=f_lo, f_hi=f_hi, worst_dBm=worst, dBc=worst - fund,
                     restricted=bool(restricted(f_lo) or restricted(f_hi)),
                     field_dBuV_m=worst + G_HARM_DBI + 95.2))
fig, ax = plt.subplots(figsize=FIG_W)
for k, rev in enumerate(("A", "B")):
    d = [r for r in rows if r["rev"] == rev and r["n"] > 1]
    x = np.array([r["n"] for r in d]) + (k - 0.5) * 0.22
    ax.bar(x, [r["worst_dBm"] + 80 for r in d], bottom=-80, width=0.2, color=C.series[k * 2],
           label="Rev A (no match)" if rev == "A" else "Rev B (π-match)")
    for xx, r in zip(x, d):
        ax.text(xx, r["worst_dBm"] + 1.0, ("%.0f" % r["worst_dBm"]).replace("-", "−"), ha="center", color=C.ink,
                bbox=dict(boxstyle="square,pad=0.05", fc="white", ec="none"), zorder=4)
# limits at the antenna port: restricted bands (3f0–5f0 here) → 54 dBµV/m average at 3 m, i.e. EIRP −41.2 dBm
# with 0 dBi; 2f0 is outside them → −20 dBc (15.247(d))
lim_r = 54 - 95.2 - G_HARM_DBI
ax.plot([2.55, 5.45], [lim_r] * 2, color=C.mute, lw=1.0, ls=(0, (4, 3)))
ax.text(5.45, lim_r - 1.5, "restricted bands: 54 dBµV/m at 3 m", color=C.mute, ha="right", va="top")
ax.plot([1.6, 2.4], [0, 0], color=C.mute, lw=1.0, ls=(0, (4, 3)))
ax.text(2.4, 1.5, "−20 dBc", fontsize=7, color=C.mute, ha="right")
ax.set_xticks([2, 3, 4, 5], ["2f₀\n1805–1830", "3f₀\n2707–2745", "4f₀\n3609–3660", "5f₀\n4512–4575"])
ax.set_xlim(1.5, 5.5)
ax.set_ylim(-80, 5)
ax.set_ylabel("Worst channel, conducted at J5 (dBm)")
ax.set_title("TX harmonics at the antenna port, CW at +20 dBm")
ax.legend(loc="upper right")
save(fig, fig_path("tx_harmonics"))
res["harmonics"] = rows
b3 = next(r for r in rows if r["rev"] == "B" and r["n"] == 3)
a3 = next(r for r in rows if r["rev"] == "A" and r["n"] == 3)
res["third_margin_dB"] = {"A": round(float(54 - a3["field_dBuV_m"]), 1), "B": round(float(54 - b3["field_dBuV_m"]), 1)}
res["third_improvement_dB"] = round(float(a3["worst_dBm"] - b3["worst_dBm"]), 1)
res["third_improvement_sim_dB"] = -sim_results()["board_si"]["harmonics"]["rel_attenuation_dB"]["3f0"]

# ---------------------------------------------------------------- desense
d = log("rx_desense.csv")
ref = d[d.condition == "bench_ldo"].set_index("channel").sens_dBm_10pct_per
des = {}
for c, g in d.groupby("condition"):
    if c == "bench_ldo":
        continue
    des[c] = float((g.set_index("channel").sens_dBm_10pct_per - ref).max())
res["desense"] = dict(reference_dBm=round(float(ref.mean()), 1), worst_dB={k: round(v, 1) for k, v in des.items()},
                     worst_overall_dB=round(max(des.values()), 1))
store("emc", res)
print(res["radiated"]["min_margin_dB"], res["third_margin_dB"], res["third_improvement_dB"], res["desense"])
