"""Sensor accuracy: chamber temperature sweep (external SHT45 probe + internal SHT40), internal-sensor
self-heating while charging, and humidity at four saturated-salt points.

Reads: temp_chamber.csv, int_sensor_selfheat.csv, rh_salts.csv
Writes: docs/figures/test_temp_accuracy, test_rh_accuracy, test_selfheat
"""
import numpy as np

from testlib import C, fig_path, limit_line, log, plt, save, store

t = log("temp_chamber.csv")
t["err_ext"] = t.ext_sht45_C - t.ref_C
t["err_int"] = t.int_sht40_C - t.ref_C
fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.0), sharey=True)
LBL = {0.3: "R7 ±0.3 °C", 0.2: "SHT40 typ. ±0.2 °C"}
for ax, col, title, spec in [(axes[0], "err_ext", "External probe (SHT45)", 0.3),
                             (axes[1], "err_int", "Internal sensor (SHT40), charger idle", 0.2)]:
    for k, (sn, g) in enumerate(t.groupby("serial")):
        ax.plot(g.setpoint_C + (k - 2) * 0.7, g[col], "o", ms=3.6, color=C.series[k], label=sn.replace("TW1B-", "#"))
    ax.set_ylim(-0.45, 0.58)
    ax.set_xlim(-14, 64)
    limit_line(ax, y=spec)
    limit_line(ax, y=-spec, text=LBL[spec], where="right", va="top")
    ax.axhline(0, color=C.line, lw=0.8)
    ax.set_xlabel("Chamber set point (°C)")
    ax.set_title(title, fontsize=10)
axes[0].set_ylabel("Error vs reference PRT (°C)")
axes[1].legend(loc="upper center", ncol=5, handletextpad=0.1, columnspacing=0.5, fontsize=8.5)
fig.suptitle("Temperature accuracy, 5 units, −10 to +60 °C", x=0.02, ha="left", fontsize=10, fontweight="semibold")
save(fig, fig_path("temp_accuracy"))

# self-heating of the internal sensor
s = log("int_sensor_selfheat.csv")
fit = np.polyfit(s.charger_dissipation_W, s.int_minus_ext_C, 1)
fig, ax = plt.subplots(figsize=(3.3, 2.6))
ax.plot(s.charger_dissipation_W, s.int_minus_ext_C, "o", ms=4, color=C.series[0])
xx = np.linspace(0, 0.3, 10)
ax.plot(xx, np.polyval(fit, xx), color=C.series[0], lw=1.0, ls="--")
ax.set_xlabel("Charger dissipation (W)")
ax.set_ylabel("Internal − external (°C)")
ax.set_title("Self-heating while charging")
ax.text(0.01, 0.95, "%.1f °C per W" % fit[0], fontsize=8, va="top")
save(fig, fig_path("selfheat"))

# humidity
h = log("rh_salts.csv")
h["err_ext"] = h.ext_sht45_RH - h.ref_RH_pct
h["err_int"] = h.int_sht40_RH - h.ref_RH_pct
fig, ax = plt.subplots(figsize=(6.8, 2.7))
for k, (sn, g) in enumerate(h.groupby("serial")):
    ax.plot(g.ref_RH_pct + (k - 2) * 0.9, g.err_ext, "o", ms=4, color=C.series[k], label=sn)
limit_line(ax, y=2, text="R8 ±2 %RH")
limit_line(ax, y=-2)
ax.axhline(0, color=C.line, lw=0.8)
ax.set_ylim(-3, 3.9)
ax.set_xlim(0, 105)
for name, rh in h.groupby("salt").ref_RH_pct.first().items():
    ax.text(rh, -2.75, name.replace("2", "₂").replace("4", "₄"), ha="center", fontsize=7, color=C.mute)
ax.set_xlabel("Reference humidity, saturated salt at 25 °C (%RH)")
ax.set_ylabel("Probe error (%RH)")
ax.set_title("Humidity accuracy, external SHT45 probe, 5 units")
ax.legend(loc="upper left", ncol=5, handletextpad=0.1, columnspacing=0.8)
save(fig, fig_path("rh_accuracy"))

store("sensors", {
    "temp_ext_max_abs_err_C": t.err_ext.abs().max(), "temp_ext_rms_err_C": float(np.sqrt((t.err_ext ** 2).mean())),
    "temp_int_max_abs_err_C_idle": t.err_int.abs().max(),
    "temp_range_C": [int(t.setpoint_C.min()), int(t.setpoint_C.max())],
    "selfheat_C_per_W": fit[0],
    "selfheat_at_400mA_C": float(s[s.charge_mA == 400].int_minus_ext_C.mean()),
    "rh_ext_max_abs_err": h.err_ext.abs().max(), "rh_ext_rms_err": float(np.sqrt((h.err_ext ** 2).mean())),
    "rh_ext_max_abs_err_below_90": h[h.ref_RH_pct < 90].err_ext.abs().max(),
    "rh_int_max_abs_err": h.err_int.abs().max(),
})
print("T ext max %.2f, int max %.2f; RH ext max %.2f; selfheat %.2f C/W" % (
    t.err_ext.abs().max(), t.err_int.abs().max(), h.err_ext.abs().max(), fit[0]))
