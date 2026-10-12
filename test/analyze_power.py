"""Power: PPK2 capture of one 5-min wake cycle, charge per phase vs the simulated budget,
buck-boost efficiency, +3V3 load-step response vs the ngspice prediction, 14-day dark test.

Reads: ppk2_wake_cycle_5min_SF9.csv, buckboost_efficiency.csv, loadstep_3v3_scope.csv, dark_test_1min.csv
       sim/out/power_budget.csv, sim/out/tx_droop_2.dat (simulation overlays)
Writes: docs/figures/test_ppk2_cycle, test_charge_budget, test_efficiency, test_loadstep, test_dark_test
"""
import os

import numpy as np
import pandas as pd

from testlib import C, FIG_W, ROOT, fig_path, label_end, limit_line, log, plt, save, store

INTERVAL_S = 300.0

# ---------------------------------------------------------------- PPK2 capture
d = log("ppk2_wake_cycle_5min_SF9.csv")
t, i = d.t_s.values, d.i_A.values
dt = np.median(np.diff(t))
tx = i > 40e-3
tx_start, tx_end = t[tx].min(), t[tx].max()
awake = i > 20e-6
lab = np.full(i.size, "Sleep", dtype=object)
lab[awake & (t < tx_start)] = "Wake + sense"
lab[tx] = "TX (+20 dBm)"
post = awake & (t > tx_end)
lab[post & (i > 3.5e-3)] = "RX windows"
lab[post & (i <= 3.5e-3)] = "Waits between windows"
phases = ["Wake + sense", "TX (+20 dBm)", "RX windows", "Waits between windows"]
q = {p: float(np.sum(i[lab == p]) * dt * 1e3) for p in phases}  # mC at the battery
sleep_uA = float(np.median(i[~awake]) * 1e6)
q_wake = sum(q.values())
avg_uA = q_wake / INTERVAL_S * 1e3 + sleep_uA * (1 - (awake.sum() * dt) / INTERVAL_S)

fig, ax = plt.subplots(figsize=FIG_W)
ax.plot(t, i * 1e3, lw=0.7, color=C.series[0])
ax.set_yscale("log")
ax.set_ylim(3e-3, 300)
ax.set_xlim(t[0], t[-1])
ax.set_xlabel("Time (s)")
ax.set_ylabel("Battery current (mA)")
ax.set_title("One 5-min wake cycle at SF9, at the battery (PPK2, 3.70 V)")
ann = [("sense", t[lab == "Wake + sense"].mean(), 25), ("TX SF9, 206 ms", (tx_start + tx_end) / 2 + 0.33, 140),
       ("RX1", tx_start + 1.013, 14), ("RX2", tx_start + 2.012, 14), ("wait", tx_start + 0.6, 2.4),
       ("wait", tx_start + 1.5, 2.4), ("sleep %.1f µA" % sleep_uA, 2.95, 0.016)]
for txt, x, y in ann:
    ax.text(x, y, txt, ha="center", va="center", fontsize=7.5, color=C.ink)
save(fig, fig_path("ppk2_cycle"))

# charge per phase vs simulation (sim budget is at the 3.3 V rail -> convert to battery side via its own uA table)
sim = pd.read_csv(os.path.join(ROOT, "sim", "out", "power_budget.csv"))
row = sim[(sim["mode"] == "5-min") & (sim.SF == 9)].iloc[0]
sim_mC = {p: row[p + "_uA"] * INTERVAL_S / 1e3 for p in phases}
fig, ax = plt.subplots(figsize=(6.8, 2.6))
y = np.arange(len(phases))
ax.barh(y - 0.19, [sim_mC[p] for p in phases], height=0.36, color=C.series[2], label="Simulated budget")
ax.barh(y + 0.19, [q[p] for p in phases], height=0.36, color=C.series[0], label="Measured (PPK2)")
for k, p in enumerate(phases):
    ax.text(max(q[p], sim_mC[p]) + 0.25, k, "meas. %.2f · sim %.2f mC" % (q[p], sim_mC[p]), va="center")
ax.set_yticks(y, phases)
ax.invert_yaxis()
ax.set_xlabel("Charge per uplink at the battery (mC)")
ax.set_xlim(0, 29)
ax.grid(axis="y", visible=False)
ax.set_title("Where the charge goes per uplink (5-min, SF9)")
ax.legend(loc="lower right")
save(fig, fig_path("charge_budget"))

# ---------------------------------------------------------------- efficiency
e = log("buckboost_efficiency.csv")
fig, ax = plt.subplots(figsize=FIG_W)
for k, vin in enumerate([3.0, 3.7, 4.2]):
    s = e[e.vin_V == vin].sort_values("iout_A")
    ax.plot(s.iout_A * 1e3, s.efficiency_pct, "-o", ms=3, color=C.series[k], label="VIN %.1f V" % vin)
    label_end(ax, s.iout_A.iloc[-1] * 1e3, s.efficiency_pct.iloc[-1], "%.1f V" % vin, dy=(-4, 7, -6)[k])
ax.set_xscale("log")
ax.set_xlim(0.008, 400)
ax.set_ylim(80, 100)
ax.set_xlabel("Load current at +3V3 (mA)")
ax.set_ylabel("Efficiency (%)")
ax.set_title("TPS63900 buck-boost efficiency on the board (VOUT 3.3 V)")
for x_, txt in [(0.01, "µA-level\nsleep loads"), (4, "sensing"), (87, "TX")]:
    ax.axvline(x_, color=C.mute, lw=0.6, ls=":")
    ax.text(x_ * 1.12, 81, txt, fontsize=7, color=C.mute)
ax.legend(loc="upper center", ncol=3)
save(fig, fig_path("efficiency"))


def eff_at(vin, il):
    s = e[e.vin_V == vin].sort_values("iout_A")
    return float(np.interp(np.log10(il), np.log10(s.iout_A), s.efficiency_pct))


# ---------------------------------------------------------------- load step vs ngspice
ls = log("loadstep_3v3_scope.csv")
simd = np.loadtxt(os.path.join(ROOT, "sim", "out", "tx_droop_2.dat"), skiprows=1)
st, sv = simd[:, 0], simd[:, 1]
step_t = st[np.argmax(np.abs(sv - sv[0]) > 0.5e-3)]   # first visible deviation = load step in the deck
m = (st >= step_t - 100e-6) & (st <= step_t + 200e-6)
fig, ax = plt.subplots(figsize=FIG_W)
ax.plot(ls.t_s * 1e6, (ls.v3v3_V - 3.3) * 1e3, lw=1.0, color=C.series[0], label="Measured (scope at C8)")
ax.plot((st[m] - step_t) * 1e6, (sv[m] - 3.3) * 1e3, lw=1.6, color=C.series[2], ls="--", label="ngspice (rev B COUT)")
ax.set_xlim(-100, 300)
ax.set_ylim(-110, 110)
limit_line(ax, y=-99, text="−3 %", va="top")
limit_line(ax, y=99, text="+3 %")
ax.axvspan(0, 200, color=C.band, zorder=0)
ax.text(100, 80, "87 mA load (TX)", ha="center", fontsize=7.5, color=C.mute)
ax.set_xlabel("Time from load step (µs)")
ax.set_ylabel("+3V3 deviation (mV)")
ax.set_title("+3V3 response to a 5 → 87 mA step (radio keying up)")
ax.legend(loc="lower right", bbox_to_anchor=(1.0, 0.1))
save(fig, fig_path("loadstep"))
droop = float(-(ls.v3v3_V[(ls.t_s >= 0) & (ls.t_s < 200e-6)].min() - 3.3015) * 1e3)
over = float((ls.v3v3_V[ls.t_s >= 200e-6].max() - 3.3015) * 1e3)

# ---------------------------------------------------------------- dark test
dk = log("dark_test_1min.csv")
slope = np.polyfit(dk.day, dk.soc_pct_coulomb, 1)[0]
proj_20 = (100 - 20) / -slope
fig, ax = plt.subplots(figsize=(6.8, 2.8))
ax.plot(dk.day, dk.soc_pct_coulomb, "o-", color=C.series[0], ms=4, label="Measured (coulomb count)")
dd = np.linspace(0, 60, 50)
ax.plot(dd, 100 + slope * dd, ls="--", color=C.series[2], lw=1.2, label="Linear projection")
ax.set_xlim(0, 60)
ax.set_ylim(70, 101)
ax.set_xlabel("Days without sun (panel unplugged), 1-min rapid mode")
ax.set_ylabel("State of charge (%)")
limit_line(ax, x=60, text="")
ax.text(59, 72, "R4: ≥ 60 days", ha="right", fontsize=7.5, color=C.mute)
ax.text(20, 83.5, "projected to a 20 %% reserve: %.0f days" % proj_20, fontsize=8, color=C.ink)
ax.set_title("Dark test: 14 days in 1-min rapid mode with no sun")
ax.legend(loc="lower left")
save(fig, fig_path("dark_test"))

store("power", {
    "ppk2_board": "TW1B-003", "sleep_uA_in_capture": sleep_uA,
    "charge_per_uplink_mC_battery": q, "charge_per_uplink_mC_total": q_wake,
    "sim_charge_per_uplink_mC_battery": sim_mC, "sim_total_mC": sum(sim_mC.values()),
    "awake_time_s": float(awake.sum() * dt), "tx_time_ms": float((tx_end - tx_start) * 1e3),
    "avg_current_uA_5min_SF9": avg_uA, "sim_avg_current_uA_5min_SF9": float(row["total_uA"]),
    "avg_current_uA_1min_SF9_projected": q_wake / 60 * 1e3 + sleep_uA,
    "efficiency_pct": {"VIN3.7_10uA": eff_at(3.7, 10e-6), "VIN3.7_1mA": eff_at(3.7, 1e-3),
                       "VIN3.7_10mA": eff_at(3.7, 10e-3), "VIN3.7_100mA": eff_at(3.7, 0.1),
                       "VIN3.0_100mA": eff_at(3.0, 0.1), "VIN4.2_100mA": eff_at(4.2, 0.1),
                       "VIN3.7_300mA": eff_at(3.7, 0.3)},
    "loadstep_droop_mV": droop, "loadstep_overshoot_mV": over,
    "sim_droop_mV": 32.6,
    "dark_test_soc_drop_pct_per_day": -slope, "dark_test_days": int(dk.day.max()),
    "dark_autonomy_days_to_20pct_projected": proj_20,
})
print("avg 5-min %.1f uA (sim %.1f); per uplink %.2f mC; droop %.1f mV; dark %.0f d" % (
    avg_uA, row["total_uA"], q_wake, droop, proj_20))
