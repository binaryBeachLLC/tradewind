"""energy_year — Is the TW-1 energy-positive all year in Honolulu, including a stormy week?

Hourly simulation, 8 760 h, Honolulu (21.31 N, 157.86 W), panel tilted 20° facing south.
Sun:     solar position + clear-sky GHI/DNI/DHI from thermal_enclosure.py.
Weather: monthly mean GHI (kWh/m²/day) for Honolulu: 4.3 5.0 5.6 6.0 6.4 6.6 6.6 6.5 6.0 5.3 4.6 4.2.
         Each day gets a random clearness factor (seed 7, beta-distributed, re-normalised so every month
         hits its mean); then a forced 7-day overcast run (clearness 0.15) in December, the worst month.
         Cloud reduces the beam faster than the diffuse (beam ∝ ((k−0.25)/0.75)^1.2).
Panel:   plane-of-array irradiance → single-diode model from solar_iv.py at cell temp Ta + 25·G/1000,
         operated at the BQ24074's VIN-DPM 4.5 V. Linear charger: battery current = panel current at
         4.5 V (≤ 475 mA input limit, ≤ 500 mA ICHG), CC to 80 % SoC then CV taper to full.
Power path: while the panel can carry the load, the load runs from the panel (not the cell).
Thermal: battery temperature = ambient + k·G (k = 3.5 K per kW/m² under the ventilated roof, from
         thermal_enclosure.py); charging is blocked outside 0–50 °C. The "panel glued to the lid" design
         (k ≈ 23 K) is also run to show what the roof buys.
Cell:    3 350 mAh protected 18650, installed 1 Jan at 30 % (air-shipping limit), self-discharge 3 mAh/day.
Loads:   78 µA (5-min, SF9) and 362 µA (1-min rapid, SF9) average at the battery (power_budget.py).
"""
import csv
import os

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator

from common import apply, C, save, fig_path, record, limit_line, FIG_TALL, OUT
from thermal_enclosure import sun, clear_sky
import solar_iv

GHI_MONTH = [4.3, 5.0, 5.6, 6.0, 6.4, 6.6, 6.6, 6.5, 6.0, 5.3, 4.6, 4.2]
TMIN = [19.5, 19.5, 20.5, 21.5, 22.5, 23.5, 24.0, 24.5, 24.0, 23.0, 22.0, 20.5]
TMAX = [26.5, 26.5, 27.0, 27.8, 28.9, 30.0, 30.6, 31.2, 31.0, 30.0, 28.5, 27.2]
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
TILT = np.radians(20)
CAP = 3350.0
SELF_MA = 3.0 / 24
LOADS = {"5-min": 0.078, "1-min rapid": 0.362}          # mA at the battery
OVERCAST_START_DOY = 340                                # 6 Dec
OVERCAST_DAYS = 7


def panel_table():
    gs = np.array([0, 25, 50, 100, 200, 300, 450, 600, 800, 1000, 1150])
    ts = np.array([10, 20, 30, 40, 50, 60, 70])
    tab = np.zeros((len(gs), len(ts)))
    for i, g in enumerate(gs):
        for j, t in enumerate(ts):
            tab[i, j] = solar_iv.at(g, t, solar_iv.DPM)[0] * 1000 if g > 0 else 0.0
    return RegularGridInterpolator((gs, ts), tab, bounds_error=False, fill_value=None)


def weather(seed=7):
    rng = np.random.default_rng(seed)
    hours = np.arange(8760) + 0.5
    doy = (hours // 24).astype(int) + 1
    hod = hours % 24
    clear = np.array([clear_sky(sun(d, h)[0]) for d, h in zip(doy, hod)])   # ghi, dni, dhi
    el_az = np.array([sun(d, h) for d, h in zip(doy, hod)])
    month = np.repeat(np.arange(12), [d * 24 for d in DAYS])
    kday = np.zeros(365)
    start = 0
    for m in range(12):
        n = DAYS[m]
        clear_mean = clear[start * 24:(start + n) * 24, 0].sum() / n / 1000
        k_mean = GHI_MONTH[m] / clear_mean
        r = rng.beta(5, 1.6, n)                         # skewed: mostly fair days, some cloudy
        kday[start:start + n] = np.clip(r / r.mean() * k_mean, 0.12, 0.98)
        start += n
    kday[OVERCAST_START_DOY - 1:OVERCAST_START_DOY - 1 + OVERCAST_DAYS] = 0.15
    k = kday[doy - 1]
    ghi = clear[:, 0] * k
    dni = clear[:, 1] * np.clip((k - 0.25) / 0.75, 0, 1) ** 1.2
    el, az = el_az[:, 0], el_az[:, 1]
    cz = np.sin(el)
    dhi = np.clip(ghi - dni * np.clip(cz, 0, None), 0, None)
    # angle of incidence on a south-facing plane tilted 20°
    s = np.stack([np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)], 1)
    n = np.array([0, -np.sin(TILT), np.cos(TILT)])
    cos_i = np.clip(s @ n, 0, None) * (el > 0)
    poa = dni * cos_i + dhi * (1 + np.cos(TILT)) / 2 + ghi * 0.2 * (1 - np.cos(TILT)) / 2
    tmin = np.array(TMIN)[month]
    tmax = np.array(TMAX)[month]
    ta = np.interp(hod, [0, 6, 14.5, 24], [0.0, 0.0, 1.0, 0.0])
    ta = tmin + 1.0 + (tmax - tmin - 1.0) * ta
    ta = np.where(hod < 6, tmin + 1.0 * (1 - hod / 6), ta)
    return dict(hours=hours, doy=doy, hod=hod, month=month, ghi=ghi, poa=poa, ta=ta, kday=kday)


def run(wx, table, load_ma, k_thermal=3.5):
    soc_mah = 0.3 * CAP                                    # IATA air-shipping charge
    soc = np.zeros(8760)
    harvest = np.zeros(8760)       # mAh the panel could deliver this hour (at 4.5 V)
    charged = np.zeros(8760)
    inhibit = np.zeros(8760, bool)
    tbat = wx["ta"] + k_thermal * np.r_[0, wx["ghi"][:-1]] / 1000     # 1 h lag
    i_panel = table(np.stack([wx["poa"], np.clip(wx["ta"] + 25 * wx["poa"] / 1000, 10, 70)], 1))
    i_panel = np.clip(i_panel, 0, 475.0)
    for h in range(8760):
        ip = i_panel[h]
        harvest[h] = ip / 1000 * 1.0 * 1000 / 1000 * 1   # mA·h -> mAh over one hour (= ip/1000 A·h·1000)
        harvest[h] = ip                                    # mAh in one hour == mA
        allowed = 0.0 <= tbat[h] <= 50.0
        inhibit[h] = (ip > 1) and not allowed
        net = -SELF_MA
        if ip > load_ma:                                   # power path: panel carries the load
            if allowed:
                frac = soc_mah / CAP
                i_acc = 500.0 if frac < 0.8 else 500.0 * max(1 - frac, 0) / 0.2
                ich = min(ip - load_ma, i_acc)
                if frac >= 0.999:
                    ich = 0.0
                net += 0.99 * ich
                charged[h] = ich
        else:
            net -= load_ma - ip
        soc_mah = float(np.clip(soc_mah + net, 0, CAP))
        soc[h] = soc_mah / CAP * 100
    return dict(soc=soc, harvest=harvest, charged=charged, inhibit=inhibit, tbat=tbat)


def dark_autonomy(load_ma, days=400):
    d = np.arange(days + 1)
    soc = 100 - (load_ma * 24 + 3.0) * d / CAP * 100
    return d, np.clip(soc, 0, 100)


def main():
    apply()
    wx = weather()
    table = panel_table()
    res = {m: run(wx, table, l) for m, l in LOADS.items()}
    lid = run(wx, table, LOADS["1-min rapid"], k_thermal=23.0)

    days = wx["hours"] / 24
    fig = plt.figure(figsize=FIG_TALL)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], hspace=0.6, wspace=0.28)
    a0 = fig.add_subplot(gs[0, :])
    dh = res["5-min"]["harvest"].reshape(365, 24).sum(1)
    dd = np.arange(365) + 0.5
    a0.plot(dd, dh, color=C.series[0], lw=1.2, label="Harvest available")
    for k, (m, l) in enumerate(LOADS.items()):
        a0.plot(dd, np.full(365, (l + SELF_MA) * 24), color=C.series[k + 1], lw=1.6,
                label=f"Use, {m}")
    a0.set_yscale("log")
    a0.set(xlim=(0, 365), ylim=(3, 6000), ylabel="Charge per day (mAh)",
           title="Daily harvest vs. daily use, Honolulu (7-day overcast run, 6–12 Dec)")
    mstart = np.cumsum([0] + DAYS[:-1])
    a0.set_xticks(mstart + 15)
    a0.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    a0.set_yticks([10, 100, 1000])
    a0.set_yticklabels(["10", "100", "1 000"])
    a0.axvspan(OVERCAST_START_DOY - 1, OVERCAST_START_DOY - 1 + OVERCAST_DAYS, color=C.band, lw=0, zorder=0)
    worst = (l + SELF_MA) * 24
    i = int(np.argmin(dh))
    a0.annotate(f"worst day {dh[i]:.0f} mAh\n= {dh[i] / worst:.0f}× the 1-min use", (dd[i], dh[i]),
                xytext=(-150, -4), textcoords="offset points", fontsize=7.5, color=C.ink, va="center",
                arrowprops=dict(arrowstyle="-", color=C.mute, lw=0.6))
    a0.legend(loc="lower left", bbox_to_anchor=(0.0, 0.21), ncol=3, fontsize=7.5, columnspacing=1.6, handlelength=1.4)
    a0.text(5, 7.8, "use includes 3 mAh/day of cell self-discharge", ha="left", va="center", fontsize=7, color=C.mute)
    mins = {m: float(r["soc"][24 * 14:].min()) for m, r in res.items()}

    a1 = fig.add_subplot(gs[1, 0])
    sel = days <= 6
    for k, (m, r) in enumerate(res.items()):
        a1.plot(days[sel], r["soc"][sel], color=C.series[k + 1], lw=1.5, label=m)
    a1.set(xlim=(0, 6), ylim=(0, 105), xlabel="Days after install (1 Jan)", ylabel="State of charge (%)",
           title="Charge-up from 30 % (shipping)")
    limit_line(a1, y=30, text="shipped at 30 %", where="right", va="bottom")
    a1.legend(loc="center right")

    a2 = fig.add_subplot(gs[1, 1])
    for k, (m, l) in enumerate(LOADS.items()):
        d, s = dark_autonomy(l, 800)
        a2.plot(d, s, color=C.series[k + 1], lw=1.6, label=m)
        cut = d[np.argmax(s <= 20)]
        a2.plot([cut], [20], "o", ms=4, color=C.series[k + 1], mec="white", mew=1, zorder=5)
        a2.annotate(f"{cut} days", (cut, 20), xytext=(-6, 7) if k == 1 else (-6, -13), textcoords="offset points",
                    fontsize=7.5, color=C.ink, ha="right")
    a2.set(xlim=(0, 800), ylim=(0, 105), xlabel="Days with no sun at all", ylabel="State of charge (%)",
           title="Dark autonomy from full")
    limit_line(a2, y=20, text="20 % reserve", where="right", va="bottom")
    a2.legend(loc="upper right")
    save(fig, fig_path("energy_year"), tight=False)

    # monthly table: harvest available vs consumed (mAh)
    rows = []
    month = wx["month"]
    for m in range(12):
        sel = month == m
        row = dict(month=m + 1, ghi_kwh_m2_day=round(float(wx["ghi"][sel].sum() / DAYS[m] / 1000), 2),
                   poa_kwh_m2_day=round(float(wx["poa"][sel].sum() / DAYS[m] / 1000), 2),
                   harvest_available_mAh=round(float(res["5-min"]["harvest"][sel].sum()), 0))
        for name, l in LOADS.items():
            used = (l + SELF_MA) * sel.sum()
            row[f"consumed_{name}_mAh"] = round(used, 0)
            row[f"ratio_in_out_{name}"] = round(row["harvest_available_mAh"] / used, 1)
        row["charge_inhibit_hours_roof"] = int(res["1-min rapid"]["inhibit"][sel].sum())
        row["charge_inhibit_hours_lid_glued"] = int(lid["inhibit"][sel].sum())
        rows.append(row)
    with open(os.path.join(OUT, "energy_monthly.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    daily_h = res["5-min"]["harvest"].reshape(365, 24).sum(1)
    autonomy = {m: int(dark_autonomy(l, 800)[0][np.argmax(dark_autonomy(l, 800)[1] <= 20)]) for m, l in LOADS.items()}
    autonomy0 = {m: int(dark_autonomy(l, 800)[0][np.argmax(dark_autonomy(l, 800)[1] <= 0.001)]) for m, l in LOADS.items()}
    record("energy_year", {
        "min_soc_pct_after_first_2_weeks": {m: round(v, 1) for m, v in mins.items()},
        "days_to_full_from_30pct": {m: round(float(np.argmax(r["soc"] >= 99.5) / 24), 1) for m, r in res.items()},
        "panel_oversize_vs_1min_worst_day": round(float(daily_h.min() / ((LOADS["1-min rapid"] + SELF_MA) * 24)), 1),
        "min_soc_pct_lid_glued_1min_after_2wk": round(float(lid["soc"][24 * 14:].min()), 1),
        "charge_inhibit_hours_year": {"roof": int(res["1-min rapid"]["inhibit"].sum()),
                                      "lid_glued": int(lid["inhibit"].sum())},
        "worst_month_ratio_in_out_1min": min(r["ratio_in_out_1-min rapid"] for r in rows),
        "worst_month_ratio_in_out_5min": min(r["ratio_in_out_5-min"] for r in rows),
        "min_daily_harvest_mAh": round(float(daily_h.min()), 0),
        "median_daily_harvest_mAh": round(float(np.median(daily_h)), 0),
        "dark_autonomy_days_to_20pct": autonomy,
        "dark_autonomy_days_to_empty": autonomy0,
        "energy_positive_every_month": all(r["ratio_in_out_1-min rapid"] > 1 for r in rows),
    })
    for r in rows:
        print(r)
    print(mins, autonomy, autonomy0, daily_h.min(), np.median(daily_h), lid["soc"].min(),
          res["1-min rapid"]["inhibit"].sum(), lid["inhibit"].sum())


if __name__ == "__main__":
    main()
