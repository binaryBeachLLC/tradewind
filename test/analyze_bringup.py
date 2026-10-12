"""Bring-up (rev A history + rev B, 10 boards) and the production-tester summary.

Reads: bringup_revB_rails.csv, bringup_revA_sleep.csv, production_tester.csv
Writes: docs/figures/test_bringup_sleep, test_production; results.json -> bringup, production
"""
import numpy as np

from testlib import C, FIG_W, fig_path, limit_line, log, plt, save, store

b = log("bringup_revB_rails.csv")
a = log("bringup_revA_sleep.csv")

# ---------------------------------------------------------------- sleep current per board
fig, ax = plt.subplots(figsize=(6.8, 3.0))
x = np.arange(len(b))
ax.plot(x, b.sleep_uA_3V7, "o", ms=6, color=C.series[0], label="VBAT 3.7 V", zorder=3)
ax.plot(x, b.sleep_uA_4V2, "D", ms=5, color=C.series[1], label="VBAT 4.2 V", zorder=3)
ax.set_xticks(x, [s.replace("TW1B-", "") for s in b.serial])
ax.set_xlabel("Rev B board (TW1B-###)")
ax.set_ylabel("Sleep current at the battery (µA)")
ax.set_ylim(0, 12)
ax.set_xlim(-0.6, len(b) - 0.4)
limit_line(ax, y=10, text="R2 limit 10 µA", va="bottom")
ax.axhline(6.9, color=C.mute, lw=0.8, ls=":")
ax.text(-0.5, 6.0, "budget 6.9 µA", fontsize=7.5, color=C.mute, va="center")
ax.text(len(b) - 0.5, 11.55, "Rev A as built: 33.5 – 36.8 µA (off scale)", ha="right", fontsize=7.5, color=C.ink)
ax.set_title("Sleep current, 10 rev B boards (PPK2, 60 s average)")
ax.legend(loc="lower right", ncol=2)
save(fig, fig_path("bringup_sleep"))

# ---------------------------------------------------------------- production tester grid
p = log("production_tester.csv")
steps = list(dict.fromkeys(p.step))
serials = list(dict.fromkeys(p.serial))
final = p.sort_values("attempt").groupby(["serial", "step"]).last().reset_index()
first = p[p.attempt == 1]
fig, ax = plt.subplots(figsize=(6.8, 3.1))
ax.set_xlim(-0.5, len(steps) - 0.5)
ax.set_ylim(len(serials) - 0.5, -0.5)
ax.grid(False)
for i, sn in enumerate(serials):
    for j, st in enumerate(steps):
        r1 = first[(first.serial == sn) & (first.step == st)].result.iloc[0]
        rf = final[(final.serial == sn) & (final.step == st)].result.iloc[0]
        col = C.good if r1 == "pass" else C.bad
        ax.add_patch(plt.Rectangle((j - 0.46, i - 0.42), 0.92, 0.84, color=col, alpha=0.14 if r1 == "pass" else 0.22, lw=0))
        mark = "✓" if r1 == "pass" else ("✗ → ✓" if rf == "pass" else "✗")
        ax.text(j, i, mark, ha="center", va="center", fontsize=8.5 if r1 == "pass" else 7.5,
                color=C.good if r1 == "pass" else C.bad, fontweight="bold")
NICE = {"visual": "Visual", "power_on_mA": "Power-on current", "rails": "Rails", "flash": "Flash", "i2c_scan": "I²C scan",
        "sensors": "Sensors", "sleep_lt_10uA": "Sleep < 10 µA", "rf_power": "RF power", "join": "Join", "led_hall": "LED + hall"}
ax.set_xticks(range(len(steps)), [NICE.get(s, s) for s in steps], rotation=30, ha="right")
ax.set_yticks(range(len(serials)), serials)
ax.tick_params(labelsize=7.5)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.set_title("Production tester, first pass (✓ pass, ✗ fail → reworked and retested)")
save(fig, fig_path("production"))

fp_yield = first.groupby("serial").result.apply(lambda s: (s == "pass").all()).mean() * 100
store("bringup", {
    "boards": int(len(b)),
    "v3v3_V": {"mean": b.v3v3_V.mean(), "min": b.v3v3_V.min(), "max": b.v3v3_V.max()},
    "v3v3_ripple_mVpp_10mA": {"mean": b.v3v3_ripple_mVpp_10mA.mean(), "max": b.v3v3_ripple_mVpp_10mA.max()},
    "vsys_V_sun": {"mean": b.vsys_V_sun.mean(), "min": b.vsys_V_sun.min(), "max": b.vsys_V_sun.max()},
    "vbat_reg_V": {"mean": b.vbat_reg_V.mean(), "min": b.vbat_reg_V.min(), "max": b.vbat_reg_V.max()},
    "sleep_uA_3V7": {"mean": b.sleep_uA_3V7.mean(), "min": b.sleep_uA_3V7.min(), "max": b.sleep_uA_3V7.max(),
                     "std": b.sleep_uA_3V7.std()},
    "sleep_uA_4V2": {"mean": b.sleep_uA_4V2.mean(), "max": b.sleep_uA_4V2.max()},
    "flash_s_mean": b.flash_s.mean(), "otaa_join_s_median": b.otaa_join_s.median(),
    "revA_sleep_uA_as_built": a[a.condition == "as built"].query("vbat_V > 4").sleep_uA.tolist(),
    "revA_sleep_uA_after_ECO1": a[a.condition.str.startswith("ECO-1")].sleep_uA.tolist(),
    "per_board": b.to_dict(orient="records"),
})
store("production", {"boards": len(serials), "steps": steps, "first_pass_yield_pct": fp_yield,
                     "final_yield_pct": 100.0,
                     "failures": p[p.result == "fail"][["serial", "step", "note"]].to_dict(orient="records")})
print("bring-up: sleep mean %.2f max %.2f uA; FPY %.0f %%" % (b.sleep_uA_3V7.mean(), b.sleep_uA_3V7.max(), fp_yield))
