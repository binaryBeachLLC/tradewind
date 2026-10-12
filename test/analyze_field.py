"""30-day field pilot, 3 units, 5-min interval, at an Oʻahu farm site (September 2026).

Reads: field_pilot_uplinks.csv (decoded uplinks exported from ChirpStack), rain_reference_gauge.csv
Writes: docs/figures/test_field_battery, test_field_temp, test_field_soil_rain, test_field_rain_ref
"""
import numpy as np
import pandas as pd

from testlib import C, FIG_W, fig_path, label_end, limit_line, log, ocv_to_soc, plt, save, store

d = log("field_pilot_uplinks.csv")
d["t"] = pd.to_datetime(d.time)
rx = d[d.received == 1].copy()
rx["soc"] = ocv_to_soc(rx.vbat_mV / 1000)
units = list(dict.fromkeys(d.unit))
pdr = d.groupby("unit").received.mean() * 100
expected = d.groupby("unit").size()

# ---------------------------------------------------------------- battery
fig, ax = plt.subplots(figsize=(6.8, 2.8))
for k, u in enumerate(units):
    g = rx[rx.unit == u].set_index("t").soc.resample("1h").mean()
    ax.plot(g.index, g.values, lw=1.2, color=C.series[k], label="%s (PDR %.1f %%)" % (u, pdr[u]))
ax.set_ylim(85, 101)
ax.set_ylabel("State of charge (%, from VBAT)")
ax.set_title("Battery over 30 days in the field: the cell stays near full")
ax.legend(loc="lower left", fontsize=7.5)
ax.text(rx.t.max(), 86.2, "Charger tops off only below 4.08 V (VRCH); never reached", ha="right", fontsize=7.5, color=C.mute)
fig.autofmt_xdate()
save(fig, fig_path("field_battery"))

# ---------------------------------------------------------------- enclosure temperature
u4 = rx[rx.unit == "TW1B-004"].set_index("t")
zoom = u4.loc["2026-09-14":"2026-09-17"]
fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.8), gridspec_kw=dict(width_ratios=[1.6, 1]))
ax = axes[0]
ax.plot(zoom.index, zoom.air_C, color=C.series[2], lw=1.2, label="Air (shielded probe)")
ax.plot(zoom.index, zoom.int_C, color=C.series[1], lw=1.2, label="Inside the box")
limit_line(ax, y=45, text="cell vendor 45 °C")
ax.set_ylim(14, 48)
ax.set_ylabel("°C")
ax.set_title("4 days, unit TW1B-004", fontsize=9)
ax.legend(loc="lower center", ncol=2, fontsize=7.5)
ax.xaxis.set_major_locator(plt.matplotlib.dates.DayLocator())
ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%d %b"))
dm = rx.groupby([rx.unit, rx.t.dt.date]).agg(air=("air_C", "max"), box=("int_C", "max")).reset_index()
ax = axes[1]
for k, u in enumerate(units):
    g = dm[dm.unit == u]
    ax.plot(g.air, g.box, "o", ms=3.5, color=C.series[k], label=u.replace("TW1B-", "#"))
ax.plot([26, 34], [26, 34], color=C.line, lw=1)
ax.text(33.6, 33.0, "1:1", fontsize=7, color=C.mute, ha="right")
ax.set_xlim(26, 34)
ax.set_ylim(26, 40)
ax.set_xlabel("Daily max air (°C)")
ax.set_ylabel("Daily max inside (°C)")
ax.set_title("Every day, 3 units", fontsize=9)
ax.legend(loc="upper left", fontsize=7)
fig.suptitle("Enclosure temperature under the solar roof", x=0.02, ha="left", fontsize=10, fontweight="semibold")
save(fig, fig_path("field_temp"))

# ---------------------------------------------------------------- soil + rain (unit 4)
fig, axes = plt.subplots(2, 1, figsize=(6.8, 3.6), sharex=True, gridspec_kw=dict(height_ratios=[2, 1]))
ax = axes[0]
ax.plot(u4.index, u4.soil_pct, color=C.series[0], lw=1.0)
ax.set_ylabel("Soil moisture (%)")
ax.set_ylim(15, 50)
ax.set_title("Soil moisture and rain, unit TW1B-004 (drip irrigation 06:00 every second day)", fontsize=9)
ax = axes[1]
daily_tips = u4.rain_tips_cum.resample("1D").max().diff().fillna(u4.rain_tips_cum.resample("1D").max().iloc[0])
ax.bar(daily_tips.index + pd.Timedelta(hours=12), daily_tips.values * 0.2, width=0.7, color=C.series[2])
ax.set_ylabel("Rain (mm/day)")
fig.autofmt_xdate()
save(fig, fig_path("field_soil_rain"))

# ---------------------------------------------------------------- rain vs reference gauge
ref = log("rain_reference_gauge.csv")
ref["date"] = pd.to_datetime(ref.date)
tw = (u4.rain_tips_cum.resample("1D").max().diff().fillna(0) * 0.2).rename("tw_mm")
m = ref.set_index("date").join(tw, how="inner")
m = m[(m.ref_mm > 0) | (m.tw_mm > 0)]
slope = float(np.sum(m.ref_mm * m.tw_mm) / np.sum(m.ref_mm ** 2))
r2 = float(np.corrcoef(m.ref_mm, m.tw_mm)[0, 1] ** 2)
fig, ax = plt.subplots(figsize=(3.3, 2.8))
ax.plot([0, 25], [0, 25], color=C.line, lw=1)
ax.plot(m.ref_mm, m.tw_mm, "o", ms=5, color=C.series[0])
ax.set_xlim(0, 25)
ax.set_ylim(0, 25)
ax.set_xlabel("Reference gauge (mm/day)")
ax.set_ylabel("TW-1 tipping bucket (mm/day)")
ax.text(1, 22.5, "slope %.3f, R² %.3f\n%d rain days" % (slope, r2, len(m)), fontsize=7.5, va="top")
ax.set_title("Rain vs a manual gauge", fontsize=9)
save(fig, fig_path("field_rain_ref"))

uplinks_received = int(d.received.sum())
store("field", {
    "site": "Oʻahu farm site", "start": str(d.t.min().date()), "end": str(d.t.max().date()), "interval_min": 5,
    "units": units, "distance_km": {"TW1B-004": 0.6, "TW1B-005": 1.4, "TW1B-008": 3.2},
    "uplinks_expected": int(len(d)), "uplinks_received": uplinks_received,
    "pdr_pct": pdr.to_dict(), "pdr_pct_all": float(d.received.mean() * 100),
    "rssi_median_dBm": rx.groupby("unit").rssi_dBm.median().to_dict(),
    "soc_min_pct": rx.groupby("unit").soc.min().to_dict(), "soc_min_pct_all": float(rx.soc.min()),
    "vbat_min_mV": float(rx.vbat_mV.min()),
    "internal_max_C": float(rx.int_C.max()), "air_max_C": float(rx.air_C.max()),
    "internal_minus_air_daily_max_C": {"mean": float((dm.box - dm.air).mean()), "max": float((dm.box - dm.air).max())},
    "rain_vs_reference": {"slope": slope, "r2": r2, "days": int(len(m)),
                          "total_ref_mm": float(m.ref_mm.sum()), "total_tw_mm": float(m.tw_mm.sum())},
})
print("PDR", pdr.round(2).to_dict(), "all %.2f; SoC min %.1f; int max %.1f (air %.1f); rain slope %.3f R2 %.3f" % (
    d.received.mean() * 100, rx.soc.min(), rx.int_C.max(), rx.air_C.max(), slope, r2))
