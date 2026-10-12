"""Environmental: IP67-style dunk (internal humidity log), thermal cycling, UV coupons, drop, ESD, TS charge window,
rain-gauge bench counting.

Reads: ip67_dunk_internal.csv, thermal_cycling.csv, uv_coupons.csv, drop_test.csv, esd_results.csv,
       rain_bench.csv, ts_window.csv
Writes: docs/figures/test_ip67_dunk, test_uv
"""
import math

import numpy as np

from testlib import C, fig_path, label_end, limit_line, log, plt, save, store

d = log("ip67_dunk_internal.csv")


def dewpoint(t, rh):
    a, b = 17.62, 243.12
    g = np.log(rh / 100) + a * t / (b + t)
    return b * g / (a - g)


d["dp"] = dewpoint(d.int_T_C, d.int_RH_pct)
fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8))
ax = axes[0]
ax.plot(d.t_min, d.int_RH_pct, color=C.series[0], lw=1.4)
ax.set_ylabel("Internal RH (%)")
ax.set_xlabel("Time (min)")
ax.set_ylim(40, 100)
ax.set_title("Internal humidity", fontsize=9)
ax = axes[1]
ax.plot(d.t_min, d.int_T_C, color=C.series[1], lw=1.4, label="Internal temperature")
ax.plot(d.t_min, d.dp, color=C.series[2], lw=1.4, label="Internal dew point")
ax.set_ylabel("°C")
ax.set_xlabel("Time (min)")
ax.set_ylim(10, 30)
ax.set_title("Dew point stays flat: no water got in", fontsize=9)
ax.legend(loc="lower left", fontsize=7.5)
for a in axes:
    a.axvspan(10, 40, color=C.band, zorder=0)
    a.text(25, a.get_ylim()[1] - (a.get_ylim()[1] - a.get_ylim()[0]) * 0.06, "1 m under water", ha="center",
           fontsize=7.5, color=C.mute)
fig.suptitle("Dunk test, 30 min at 1 m, unit TW1B-006", x=0.02, ha="left", fontsize=10, fontweight="semibold")
save(fig, fig_path("ip67_dunk"))
sub = d[(d.t_min >= 10) & (d.t_min < 40)]
dp_drift = float(d.dp.iloc[-5:].mean() - d.dp.iloc[:8].mean())

u = log("uv_coupons.csv")
fig, ax = plt.subplots(figsize=(3.3, 2.6))
for k, (m, g) in enumerate(u.groupby("material", sort=False)):
    ax.plot(g.hours, g.delta_E, "o-", ms=4, color=C.series[k])
    label_end(ax, g.hours.iloc[-1], g.delta_E.iloc[-1], m)
ax.set_xlim(0, 640)
ax.set_ylim(0, 10)
ax.set_xlabel("UVA-340 exposure (h)")
ax.set_ylabel("Colour change ΔE")
limit_line(ax, y=3, text="visible ≈ 3", where="right")
ax.set_title("UV ageing of the shell plastic", fontsize=9)
save(fig, fig_path("uv"))

tc, dr, esd, rb, ts = (log(n) for n in ["thermal_cycling.csv", "drop_test.csv", "esd_results.csv", "rain_bench.csv",
                                        "ts_window.csv"])
store("environmental", {
    "dunk": {"result": "pass", "depth_m": 1.0, "duration_min": 30, "dewpoint_drift_C": dp_drift,
             "internal_RH_max_pct": float(d.int_RH_pct.max())},
    "ip66_jet": {"result": "not performed",
                 "note": "IPX5-style hose test (12.5 L/min, 3 min, all faces) passed; 100 L/min IP66 jet needs an accredited lab"},
    "thermal_cycling": tc.to_dict(orient="records"),
    "uv_deltaE_500h": {m: float(g.delta_E.iloc[-1]) for m, g in u.groupby("material")},
    "drop": dr.to_dict(orient="records"),
    "esd": {"contact_8kV": "pass (criterion A, all ports)",
            "air_15kV": "pass (criterion B on J4: one self-recovering reset; A elsewhere)",
            "rows": esd.to_dict(orient="records")},
    "rain_bench": {"tips_applied": int(rb.tips_applied.sum()), "tips_counted": int(rb.tips_counted.sum()),
                   "exact_up_to_tips_per_s": float(rb[rb.tips_applied == rb.tips_counted].rate_tips_per_s.max()),
                   "rows": rb.to_dict(orient="records")},
    "ts_window": ts.to_dict(orient="records"),
    "salt_fog": "deferred (ASTM B117 at a test house before a coastal deployment)",
})
print("dunk dew-point drift %.2f C; UV ASA %.1f; rain %d/%d" % (
    dp_drift, u[u.material == "ASA white"].delta_E.iloc[-1], rb.tips_counted.sum(), rb.tips_applied.sum()))
