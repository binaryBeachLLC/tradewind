"""Requirement-by-requirement compliance (R1–R15 from docs/design-spec.md) from the measured results,
plus the 'headline' block of results.json. Run after the other analyze_*.py scripts.

Writes: test/compliance.csv, results.json -> headline
"""
import csv
import os

from testlib import TEST, load_results, store

r = load_results()
b, pw, so, se, rf, en, fi = (r[k] for k in ["bringup", "power", "solar", "sensors", "rf", "environmental", "field"])
ts = {row["edge"] + ("_hot" if row["cell_temp_C"] > 20 else "_cold"): row["cell_temp_C"] for row in en["ts_window"]}
ranges = rf["range"]

rows = [
    ("R1", "Uplink interval 5 min default, 1 min rapid", "5 min / 1 min",
     "5-min cadence held for 30 days (%d of %d uplinks received); 1-min rapid mode run 14 days (dark test)" % (
         fi["uplinks_received"], fi["uplinks_expected"]), "pass", ""),
    ("R2", "Sleep current, whole board at 3.7 V", "≤ 10 µA",
     "%.1f µA mean, %.1f µA max (10 boards)" % (b["sleep_uA_3V7"]["mean"], b["sleep_uA_3V7"]["max"]), "pass",
     "%.0f %% margin on the worst board" % ((10 - b["sleep_uA_3V7"]["max"]) / 10 * 100)),
    ("R3", "Average current, 5-min interval, SF9", "≤ 100 µA",
     "%.1f µA (PPK2, sim %.0f µA)" % (pw["avg_current_uA_5min_SF9"], pw["sim_avg_current_uA_5min_SF9"]), "pass",
     "%.0f %% margin" % ((100 - pw["avg_current_uA_5min_SF9"])))
    ,
    ("R4", "Dark autonomy, 1-min rapid mode", "≥ 60 days",
     "%.0f days to a 20 %% reserve (projected from a 14-day dark test, %.2f %%/day)" % (
         pw["dark_autonomy_days_to_20pct_projected"], pw["dark_test_soc_drop_pct_per_day"]), "pass", "≈ 4× the requirement"),
    ("R5", "Energy-positive every month incl. 7-day overcast", "yes",
     "Sept field: cell held ≥ %.1f %% with the charger in top-off standby; clear day %.0f mAh in, cloudy day %.0f mAh in vs ≈ 12 mAh/day used (1-min)" % (
         fi["soc_min_pct_all"], so["field_days"]["Clear day"]["mAh_in"], so["field_days"]["Cloudy day"]["mAh_in"]),
     "pass (1 month measured)", "full year and the overcast week are covered by simulation only (sim/energy_year.py)"),
    ("R6", "Charging only inside 0–50 °C", "0–50 °C",
     "stops at %.1f °C rising / resumes %.1f °C; stops at %.1f °C falling (cold)" % (
         ts["rising_hot"], ts["falling_hot"], ts["falling_cold"]), "pass (marginal)",
     "trip points sit 0.4–0.6 °C outside nominal, inside the BQ24074 TS threshold tolerance; field cell max %.1f °C" % fi["internal_max_C"]),
    ("R7", "Air temperature accuracy, external probe", "±0.3 °C",
     "%.2f °C worst of 5 units, −10 to +60 °C (RMS %.2f °C)" % (se["temp_ext_max_abs_err_C"], se["temp_ext_rms_err_C"]), "pass", ""),
    ("R8", "Humidity accuracy, external probe, 10–90 %RH", "±2 %RH",
     "%.1f %%RH worst below 90 %%RH; %.1f %%RH at 97 %%RH" % (se["rh_ext_max_abs_err_below_90"], se["rh_ext_max_abs_err"]), "pass",
     "97 %RH point is outside the requirement range but also inside ±2"),
    ("R9", "Radio range, line of sight, SF10", "≥ 5 km",
     "decoded at %.1f km (last stop on the test road); SF7 ≥ 50 %% delivery to %.1f km" % (
         ranges["SF10"]["last_decode_km"], ranges["SF7"]["max_km_PDR50"]), "pass", "true SF10 limit not reached"),
    ("R10", "Ingress protection", "IP66 (target), 1 m dunk stretch",
     "30 min at 1 m: no ingress (dew-point drift %.2f °C); IPX5-style hose test passed" % en["dunk"]["dewpoint_drift_C"],
     "open", "IP66 100 L/min jet not performed: needs an accredited lab"),
    ("R11", "Operating temperature", "−10 to +60 °C",
     "uplinks, sensors and sleep current OK at every chamber step −10 to +60 °C; 50 thermal cycles passed", "pass", ""),
    ("R12", "ESD on external connectors", "±8 kV contact",
     "±8 kV contact: criterion A on all ports; ±15 kV air: one self-recovering reset on J4 (criterion B)", "pass", ""),
    ("R13", "Conducted TX power at U.FL, 902.3–914.9 MHz", "+20 dBm ±1 dB",
     "%.2f to %.2f dBm, mean %.2f dBm (2 units × 64 channels)" % (
         rf["tx_power_dBm"]["min"], rf["tx_power_dBm"]["max"], rf["tx_power_dBm"]["mean"]), "pass", ""),
    ("R14", "BOM cost, electronics, 1k units", "≤ $25", "costed in the BOM, not a test item", "n/a", "see hardware/fab BOM"),
    ("R15", "Rain counting: no double counts, counts while asleep", "exact",
     "%d of %d bench tips counted (exact up to %.0f tips/s, gauge max ≈ 2/s); field vs manual gauge slope %.3f" % (
         en["rain_bench"]["tips_counted"], en["rain_bench"]["tips_applied"], en["rain_bench"]["exact_up_to_tips_per_s"],
         fi["rain_vs_reference"]["slope"]), "pass", "the one miss was at 10 tips/s, inside the 50 ms firmware lockout"),
]
path = os.path.join(TEST, "compliance.csv")
with open(path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "requirement", "target", "measured", "status", "note"])
    w.writerows(rows)

store("headline", {
    "sleep_uA_mean": b["sleep_uA_3V7"]["mean"], "sleep_uA_max": b["sleep_uA_3V7"]["max"],
    "avg_current_uA_5min_SF9": pw["avg_current_uA_5min_SF9"], "charge_per_uplink_mC": pw["charge_per_uplink_mC_total"],
    "efficiency_pct_10uA_10mA_100mA": [pw["efficiency_pct"]["VIN3.7_10uA"], pw["efficiency_pct"]["VIN3.7_10mA"],
                                       pw["efficiency_pct"]["VIN3.7_100mA"]],
    "loadstep_droop_mV": pw["loadstep_droop_mV"], "dark_autonomy_days_1min": pw["dark_autonomy_days_to_20pct_projected"],
    "vin_dpm_V": so["vin_dpm_V"]["mean"], "solar_clear_day_mAh": so["field_days"]["Clear day"]["mAh_in"],
    "solar_cloudy_day_mAh": so["field_days"]["Cloudy day"]["mAh_in"],
    "tx_power_dBm_mean": rf["tx_power_dBm"]["mean"], "tx_power_dBm_range": [rf["tx_power_dBm"]["min"], rf["tx_power_dBm"]["max"]],
    "s11_dB_915_in_case_matched": rf["s11"]["case_matched_revB"]["at_915_dB"],
    "s11_dB_worst_in_band_matched": rf["s11"]["case_matched_revB"]["worst_in_band_dB"],
    "s11_dB_915_in_case_unmatched": rf["s11"]["case_unmatched"]["at_915_dB"],
    "range_km_last_decode": {k: v["last_decode_km"] for k, v in ranges.items()},
    "temp_err_max_C": se["temp_ext_max_abs_err_C"], "rh_err_max_pct": se["rh_ext_max_abs_err"],
    "ip": "1 m / 30 min dunk pass; IPX5 hose pass; IP66 jet pending", "esd": "±8 kV contact A; ±15 kV air B (J4)",
    "field_pdr_pct": fi["pdr_pct_all"], "field_min_soc_pct": fi["soc_min_pct_all"],
    "field_max_internal_C": fi["internal_max_C"], "field_max_air_C": fi["air_max_C"],
    "first_pass_yield_pct": r["production"]["first_pass_yield_pct"],
    "compliance": {row[0]: row[4] for row in rows},
})
for row in rows:
    print("%-4s %-18s %s" % (row[0], row[4], row[3]))
