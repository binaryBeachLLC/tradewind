"""thermal_enclosure — Does the cell stay inside its charge window on a hot Honolulu day?

Model (two lumped nodes, explicit Euler at 10 s):
  shell  — the ASA box walls (≈ 0.20 kg × 1300 J/kgK = 260 J/K)
  core   — 18650 cell + holder + PCB + inside air (≈ 95 J/K); this is the "battery temperature".
  Shell gains: absorbed beam + diffuse + ground-reflected sun on each face (α = 0.60 grey, 0.25 white),
    and, under the roof, long-wave from the roof underside (panel runs ≈ Ta + 25 K at 1000 W/m²).
  Shell losses: convection h_c(wind) and linearised long-wave (ε 0.9, h_r ≈ 5.5 W/m²K) to sky / ground.
  Core: coupled to the shell by inside air + mounts (G = 0.35 W/K) and heated by the linear charger's
    loss (VIN−VBAT)·ICHG while charging.
Sun: NOAA-style solar position for Honolulu (21.31 N, 157.86 W, HST), 15 August (clear, hot).
  Clear-sky GHI (Haurwitz), DNI (Meinel), DHI = GHI − DNI·cos z. Ground albedo 0.25.
Weather (design case): Kona-wind day — trades stop, ambient 25 → 32 °C (min 06:00, max 14:30), wind
  0.4–1.2 m/s, h_c = 4 + 1.6·v W/m²K. A normal trade-wind day (24 → 31 °C, 1.5–4 m/s) is also run.
Box: 120 (E–W) × 100 (high) × 60 (N–S) mm, lid faces south, back face against the pole bracket.
Roof: 150 × 120 mm panel on a sun roof, 25 mm ventilated gap, 30 mm overhang; it removes the beam on
  the top face and shades vertical faces when the sun is high (shaded height = overhang·tan(profile)).
Charger cutoff: BQ24074 TS window ≈ 0–50 °C (103AT, ITS 75 µA). Cell vendor preference: ≤ 45 °C.
"""
import csv
import os

import numpy as np
import matplotlib.pyplot as plt

from common import apply, C, save, fig_path, record, limit_line, label_end, FIG_W, OUT

LAT, LON, TZ = 21.31, -157.86, -10
W, H, D = 0.120, 0.100, 0.060
OVERHANG = 0.030
DT = 10.0


def sun(doy, hour_local):
    """Return (elevation rad, azimuth rad from north, cw) for local standard time."""
    g = 2 * np.pi / 365 * (doy - 1 + (hour_local - 12) / 24)
    eot = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                    - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    tst = hour_local * 60 + eot + 4 * LON - 60 * TZ
    ha = np.radians(tst / 4 - 180)
    lat = np.radians(LAT)
    cz = np.sin(lat) * np.sin(decl) + np.cos(lat) * np.cos(decl) * np.cos(ha)
    cz = np.clip(cz, -1, 1)
    z = np.arccos(cz)
    el = np.pi / 2 - z
    az = np.arctan2(np.sin(ha), np.cos(ha) * np.sin(lat) - np.tan(decl) * np.cos(lat)) + np.pi
    return el, az


def clear_sky(el):
    cz = np.sin(el)
    if cz <= 0.01:
        return 0.0, 0.0, 0.0
    ghi = 1098 * cz * np.exp(-0.057 / cz)
    am = 1 / (cz + 0.50572 * (np.degrees(el) + 6.07995) ** -1.6364)
    dni = 1361 * 0.7 ** (am ** 0.678)
    dhi = max(ghi - dni * cz, 0.08 * ghi)
    return ghi, dni, dhi


def faces():
    # (name, normal (E, N, Up), area)
    return [("top", (0, 0, 1), W * D), ("south", (0, -1, 0), W * H), ("east", (1, 0, 0), D * H),
            ("west", (-1, 0, 0), D * H), ("bottom", (0, 0, -1), W * D)]  # back (north) face on the pole


def absorbed(el, az, ghi, dni, dhi, alpha, roof):
    s = np.array([np.cos(el) * np.sin(az), np.cos(el) * np.cos(az), np.sin(el)])
    q = 0.0
    for name, n, a in faces():
        n = np.array(n, float)
        cos_i = max(float(s @ n), 0.0) if el > 0 else 0.0
        beam = dni * cos_i
        if name == "top":
            diff = dhi
        elif name == "bottom":
            diff = 0.25 * ghi
            beam = 0.0
        else:
            diff = 0.5 * dhi + 0.5 * 0.25 * ghi
        if roof:
            if name == "top":
                beam, diff = 0.0, 0.15 * dhi          # only a sliver of sky through the vent gap
            elif name != "bottom":
                # profile angle of the sun on this vertical face
                if cos_i > 0:
                    prof = np.arctan2(np.tan(el), cos_i / max(np.cos(el), 1e-3))
                    shaded = np.clip(OVERHANG * np.tan(prof) / H, 0, 1)
                    beam *= (1 - shaded)
                diff *= 0.7                            # roof hides the upper half-sky
        q += alpha * a * (beam + diff)
    return q


WEATHER = {
    # design case: Kona-wind day — trades stop, air is still and hot (common Aug–Oct)
    "kona": dict(t_lo=25.0, t_hi=32.0, wind=[0.4, 0.5, 1.2, 0.8, 0.4]),
    # typical trade-wind day
    "trades": dict(t_lo=24.0, t_hi=31.0, wind=[1.5, 1.8, 4.0, 2.5, 1.5]),
}


def simulate(alpha, roof, doy=227, weather="kona", lid_panel=False):
    wx = WEATHER[weather]
    t_amb_lo, t_amb_hi = wx["t_lo"], wx["t_hi"]
    n = int(24 * 3600 / DT)
    t = np.arange(n) * DT / 3600
    area = sum(a for *_, a in faces())
    c_shell, c_core, g_sc = 260.0, 95.0, 0.35
    ts = tc = t_amb_lo
    out = np.zeros((n, 5))
    for day in range(3):                               # 2 warm-up days, keep the 3rd
        for k in range(n):
            h = t[k]
            ta = np.interp(h, [0, 6, 14.5, 24], [t_amb_lo + 1, t_amb_lo, t_amb_hi, t_amb_lo + 1])
            wind = np.interp(h, [0, 8, 15, 20, 24], wx["wind"])
            hc = 4.0 + 1.6 * wind
            el, az = sun(doy, h)
            ghi, dni, dhi = clear_sky(el)
            q_sun = absorbed(el, az, ghi, dni, dhi, alpha, roof)
            if lid_panel:
                # panel glued flat to the lid (tilt 0 here for simplicity): 0.0150 m² absorbing 0.90 of the
                # sun on it, 15 % leaves as electricity; it replaces the lid's own top-face gain
                q_sun += 0.0150 * 0.90 * 0.85 * ghi - alpha * W * D * (dhi + max(dni * np.sin(el), 0))
            t_sky = ta - 12 * (1 - 0.5 * roof)          # roof underside replaces part of the cold sky
            q_roof = 0.0
            if roof:
                t_roof = ta + 25 * ghi / 1000           # panel/roof temperature
                q_roof = 5.0 * W * D * 0.8 * (t_roof - ts)
            area_x = area + (0.0150 - W * D if lid_panel else 0.0)
            q_conv = hc * area_x * (ts - ta)
            q_rad = 5.5 * area_x * (ts - (0.4 * t_sky + 0.6 * ta))
            # linear charger loss: panel current ≈ 0.39 A·G/1000 at 4.5 V into a ~3.95 V cell,
            # only while the charger is allowed to run and the cell is not yet full (afternoon taper)
            charging = (0 <= tc <= 50) and ghi > 50
            taper = float(np.clip((15.0 - h) / 4.0, 0, 1))   # CV taper: cell nearly full by mid-afternoon
            q_chg = (4.5 - 3.95) * 0.39 * ghi / 1000 * taper if charging else 0.0
            ts += DT * (q_sun + q_roof - q_conv - q_rad - g_sc * (ts - tc)) / c_shell
            tc += DT * (g_sc * (ts - tc) + q_chg) / c_core
            if day == 2:
                out[k] = (h, ta, ts, tc, ghi)
    return out


CASES = [("Grey box, panel elsewhere", 0.60, False, False),
         ("White box, panel elsewhere", 0.25, False, False),
         ("White box, panel glued to lid", 0.25, False, True),
         ("White box under ventilated solar roof", 0.25, True, False)]


def main():
    apply()
    res = {}
    fig, ax = plt.subplots(figsize=FIG_W)
    traces = []
    trades = {}
    for name, alpha, roof, lp in CASES:
        o = simulate(alpha, roof, weather="trades", lid_panel=lp)
        trades[name] = dict(max_battery_C=round(float(o[:, 3].max()), 1),
                            charge_inhibit_hours=round(float((o[:, 3] > 50).sum() * DT / 3600), 2))
    for k, (name, alpha, roof, lp) in enumerate(CASES):
        o = simulate(alpha, roof, lid_panel=lp)
        h, ta, ts, tc = o[:, 0], o[:, 1], o[:, 2], o[:, 3]
        hrs = DT / 3600
        res[name] = dict(max_battery_C=round(float(tc.max()), 1),
                         hours_above_45C=round(float((tc > 45).sum() * hrs), 2),
                         charge_inhibit_hours=round(float((tc > 50).sum() * hrs), 2),
                         max_shell_C=round(float(ts.max()), 1))
        ax.plot(h, tc, color=C.series[k], label=f"{name.replace('White box under ventilated solar roof', 'White box, ventilated roof')} (peak {tc.max():.0f} °C)", lw=1.8)
        traces.append((h, tc, name, k))
        np.savetxt(os.path.join(OUT, f"thermal_case{k}.csv"), o, delimiter=",",
                   header="hour,ambient_C,shell_C,battery_C,ghi_Wm2", comments="", fmt="%.3f")
    ax.plot(h, ta, color=C.mute, lw=1.0, ls=":", label="Ambient air")
    ax.set(xlim=(0, 24), ylim=(20, 74), xticks=range(0, 25, 3), xlabel="Time of day (HST) — 15 Aug, clear, calm Kona-wind day",
           ylabel="Battery temperature (°C)", title="Battery temperature in the enclosure on a hot, clear day")
    limit_line(ax, y=50, text="Charger stops (TS 50 °C)", where="left")
    limit_line(ax, y=45, text="Cell vendor limit 45 °C", where="left", va="top")
    ax.legend(loc="upper left", ncol=2, columnspacing=1.2, fontsize=8.5)
    save(fig, fig_path("thermal_enclosure"))
    record("thermal_enclosure", {"design_day_kona_calm": res, "trade_wind_day": trades})
    print("trades", trades)
    for k, v in res.items():
        print(k, v)


if __name__ == "__main__":
    main()
