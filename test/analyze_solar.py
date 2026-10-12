"""Solar charging in the field (one clear day, one cloudy day) and the VIN-DPM bench sweep; TS charge window.

Reads: solar_day_clear.csv, solar_day_cloudy.csv, vin_dpm_sweep.csv, ts_window.csv
Writes: docs/figures/test_solar_days, test_vin_dpm
"""
import numpy as np
import pandas as pd

from testlib import C, fig_path, limit_line, log, plt, save, store, sim_results

days = {"Clear day": log("solar_day_clear.csv"), "Cloudy day": log("solar_day_cloudy.csv")}
fig, axes = plt.subplots(3, 2, figsize=(6.8, 5.6), sharex="col", sharey="row")
summary = {}
for c, (name, d) in enumerate(days.items()):
    d["t"] = pd.to_datetime(d.time)
    h = d.t.dt.hour + d.t.dt.minute / 60
    charging = d.charge_mA > 1
    mah = d.charge_mA.sum() / 60
    ax = axes[0, c]
    ax.plot(h, d.panel_V, lw=1.0, color=C.series[0])
    ax.axhspan(4.35, 4.63, color=C.band, zorder=0)
    ax.text(12.5, 3.75, "VIN-DPM band", fontsize=7, color=C.mute, ha="center", va="center")
    ax.set_ylim(0, 6.5)
    ax.set_title(name + " (%s)" % d.t.iloc[0].strftime("%d %b"))
    ax = axes[1, c]
    ax.plot(h, d.charge_mA, lw=1.0, color=C.series[1])
    ax.set_ylim(0, 500)
    limit_line(ax, y=475, text="input limit 475 mA", va="bottom")
    ax.text(6.3, 420, "%.0f mAh in" % mah, fontsize=8, color=C.ink)
    ax = axes[2, c]
    ax.plot(h, d.vbat_V, lw=1.2, color=C.series[2])
    ax.set_ylim(3.5, 4.3)
    ax.set_xlabel("Hour of day (HST)")
    ax.set_xlim(6, 19)
    # ~CHG low = charging, shown as a strip at the bottom
    ax.fill_between(h, 3.5, 3.53, where=charging, color=C.series[3], step="mid", lw=0)
    ax.text(6.2, 3.56, "~CHG low (charging)", fontsize=6.8, color=C.mute)
    summary[name] = {"date": d.t.iloc[0].strftime("%Y-%m-%d"), "mAh_in": mah,
                     "peak_charge_mA": d.charge_mA.max(),
                     "panel_V_median_while_charging": float(d.panel_V[charging & (d.charge_mA < 465)].median()),
                     "vbat_start_V": d.vbat_V.iloc[0], "vbat_end_V": d.vbat_V.iloc[-1],
                     "hours_charging": float(charging.sum() / 60),
                     "peak_panel_temp_C": d.panel_temp_C.max()}
axes[0, 0].set_ylabel("Panel (V)")
axes[1, 0].set_ylabel("Charge (mA)")
axes[2, 0].set_ylabel("Battery (V)")
fig.suptitle("Solar charging in the field, unit TW1B-004", x=0.02, ha="left", fontsize=10, fontweight="semibold")
save(fig, fig_path("solar_days"))

# ---------------------------------------------------------------- VIN-DPM bench sweep
s = log("vin_dpm_sweep.csv")
fig, ax = plt.subplots(figsize=(6.8, 2.8))
for k, (sn, g) in enumerate(s.groupby("serial")):
    ax.plot(g.source_limit_mA, g.vin_V, "o-", ms=3.5, color=C.series[k], label=sn)
ax.axhspan(4.35, 4.63, color=C.band, zorder=0)
ax.text(60, 4.66, "datasheet VIN-DPM window 4.35–4.63 V", fontsize=7.5, color=C.mute)
limit_line(ax, x=475)
ax.text(485, 5.3, "USB500 input\nlimit 475 mA", fontsize=7.5, color=C.mute)
ax.set_ylim(4.2, 6.2)
ax.set_xlim(40, 590)
ax.set_xlabel("Source current limit, panel stand-in (mA)")
ax.set_ylabel("VIN at C2 (V)")
ax.set_title("VIN-DPM holds the input at 4.5 V whenever the source is current-limited")
ax.legend(loc="center left")
save(fig, fig_path("vin_dpm"))
reg = s[s.source_limit_mA < 460]
vdpm = reg.groupby("serial").vin_V.mean()

ts = log("ts_window.csv")
sr = sim_results()["solar_iv"]
store("solar", {
    "field_days": summary,
    "vin_dpm_V": {"per_board": vdpm.to_dict(), "mean": vdpm.mean(), "min": vdpm.min(), "max": vdpm.max()},
    "input_limit_mA_measured": float(s[s.source_limit_mA > 500].iin_mA.mean()),
    "sim_charge_current_hot_mA": sr["charge_current_hot_mA"],
    "ts_window_C": {"hot_stop": float(ts[(ts.edge == "rising") & (ts.cell_temp_C > 20)].cell_temp_C.iloc[0]),
                    "hot_resume": float(ts[(ts.edge == "falling") & (ts.cell_temp_C > 20)].cell_temp_C.iloc[0]),
                    "cold_stop": float(ts[(ts.edge == "falling") & (ts.cell_temp_C < 20)].cell_temp_C.iloc[0]),
                    "cold_resume": float(ts[(ts.edge == "rising") & (ts.cell_temp_C < 20)].cell_temp_C.iloc[0])},
})
print({k: (round(v["mAh_in"]), round(v["peak_charge_mA"]), v["panel_V_median_while_charging"]) for k, v in summary.items()},
      "VIN-DPM %.3f V" % vdpm.mean())
