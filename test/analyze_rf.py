"""RF: conducted TX power across the 64 US915 uplink channels, antenna S11 (NanoVNA) before and after the
rev B π-match in the closed case vs the simulation, and the drive range test vs the link budget.

Reads: tx_power_channels.csv, s11_nanovna.csv, range_drive_test.csv; imports sim/rf_match.py, sim/link_budget.py
Writes: docs/figures/test_tx_power, test_s11, test_range
"""
import numpy as np

from testlib import C, FIG_W, fig_path, limit_line, log, plt, save, store
import link_budget as lb  # noqa: E402  (sim/ is on the path via common)
import rf_match as rm  # noqa: E402

# ---------------------------------------------------------------- TX power
p = log("tx_power_channels.csv")
fig, ax = plt.subplots(figsize=(6.8, 2.6))
for k, (sn, g) in enumerate(p.groupby("serial")):
    ax.plot(g.freq_MHz, g.p_dBm, "o-", ms=2.6, lw=0.9, color=C.series[k], label=sn)
ax.set_ylim(18.5, 21.5)
limit_line(ax, y=21, text="R13 +21 dBm")
limit_line(ax, y=19, text="+19 dBm", va="top")
ax.set_xlabel("Uplink channel frequency (MHz), US915 125 kHz channels 0–63")
ax.set_ylabel("Conducted power at J5 (dBm)")
ax.set_title("Conducted TX power, +20 dBm setting")
ax.legend(loc="lower center", ncol=2)
save(fig, fig_path("tx_power"))

# ---------------------------------------------------------------- S11
s = log("s11_nanovna.csv")
NAMES = {"free_air": "Antenna in free air", "case_unmatched": "In the case, no match (rev A)",
         "case_matched_revB": "In the case, rev B π-match"}
fig, ax = plt.subplots(figsize=FIG_W)
s11_at = {}
for k, (cond, g) in enumerate([(c, s[s.condition == c]) for c in NAMES]):
    gam = g.s11_re.values + 1j * g.s11_im.values
    db = 20 * np.log10(np.abs(gam))
    ax.plot(g.freq_MHz, db, lw=1.4, color=C.series[k], label=NAMES[cond])
    band = (g.freq_MHz >= 902) & (g.freq_MHz <= 928)
    s11_at[cond] = {"at_915_dB": float(np.interp(915, g.freq_MHz, db)), "worst_in_band_dB": float(db[band].max()),
                    "vswr_at_915": float((1 + 10 ** (np.interp(915, g.freq_MHz, db) / 20)) / (1 - 10 ** (np.interp(915, g.freq_MHz, db) / 20)))}
f = np.linspace(860e6, 960e6, 201)
zsim = rm.network(f, rm.z_ant(f), c14=1.8e-12, l2=7.5e-9)
ax.plot(f / 1e6, rm.s11_db(zsim), ls="--", lw=1.1, color=C.series[2], label="Simulated, rev B (sim/rf_match.py)")
ax.axvspan(902, 928, color=C.band, zorder=0)
ax.text(915, -2.5, "US915 uplink band", ha="center", fontsize=7.5, color=C.mute)
limit_line(ax, y=-10, text="−10 dB")
ax.set_xlim(800, 1000)
ax.set_ylim(-50, 0)
ax.set_xlabel("Frequency (MHz)")
ax.set_ylabel("|S11| (dB)")
ax.set_title("Antenna match measured with a NanoVNA at the U.FL pigtail")
ax.legend(loc="lower left", fontsize=7.5)
save(fig, fig_path("s11"))

# ---------------------------------------------------------------- range test
r = log("range_drive_test.csv")
fig, ax = plt.subplots(figsize=FIG_W)
dd = np.logspace(np.log10(0.25), np.log10(15), 100)
ax.plot(dd, lb.rx_power(dd), color=C.mute, lw=1.0, ls="--", label="Link budget (sim)")
maxr = {}
for k, sf in enumerate([7, 10]):
    g = r[(r.sf == sf) & (r.received == 1)]
    med = g.groupby("dist_km").rssi_dBm.median()
    ax.plot(g.dist_km * (1 + 0.012 * (k * 2 - 1)), g.rssi_dBm, "o", ms=2.4, alpha=0.45, color=C.series[k])
    ax.plot(med.index, med.values, "-", lw=1.4, color=C.series[k], label="SF%d received (median)" % sf)
    ax.axhline(lb.SENS[sf], color=C.series[k], lw=0.8, ls=":")
    ax.text(0.27, lb.SENS[sf] + 1, "SF%d sensitivity %d dBm" % (sf, lb.SENS[sf]), fontsize=7, color=C.ink)
    per = r[r.sf == sf].groupby("dist_km").received.mean()
    ok = per[per >= 0.5]
    maxr[sf] = {"last_decode_km": float(r[(r.sf == sf) & (r.received == 1)].dist_km.max()),
                "max_km_PDR50": float(ok.index.max()),
                "pdr_by_km": {str(kk): float(v) for kk, v in per.items()}}
ax.set_xscale("log")
ax.set_xlim(0.25, 15)
ax.set_ylim(-140, -50)
ax.set_xticks([0.3, 0.5, 1, 2, 3, 5, 10], ["0.3", "0.5", "1", "2", "3", "5", "10"])
ax.set_xlabel("Distance from gateway (km)")
ax.set_ylabel("RSSI at the gateway (dBm)")
ax.set_title("Range drive test: gateway on a 10 m mast, node in its enclosure")
ax.legend(loc="upper right", fontsize=7.5)
save(fig, fig_path("range"))

store("rf", {
    "tx_power_dBm": {"mean": p.p_dBm.mean(), "min": p.p_dBm.min(), "max": p.p_dBm.max(),
                     "per_unit_mean": p.groupby("serial").p_dBm.mean().to_dict()},
    "s11": s11_at,
    "sim_s11_revB_at_915_dB": float(np.interp(915e6, f, rm.s11_db(zsim))),
    "range": {"SF%d" % k: v for k, v in maxr.items()},
    "rssi_median_dBm_at_1km_SF7": float(r[(r.sf == 7) & (r.dist_km == 1.0)].rssi_dBm.median()),
    "sim_rssi_dBm_at_1km": float(lb.rx_power(1.0)),
})
print("TX %.2f dBm [%.2f, %.2f]; S11 915 matched %.1f dB; range SF7 %.1f / SF10 %.1f km (PDR>=50%%: %.1f / %.1f)" % (
    p.p_dBm.mean(), p.p_dBm.min(), p.p_dBm.max(), s11_at["case_matched_revB"]["at_915_dB"],
    maxr[7]["last_decode_km"], maxr[10]["last_decode_km"], maxr[7]["max_km_PDR50"], maxr[10]["max_km_PDR50"]))
for k_, v in s11_at.items():
    print(" ", k_, {a: round(b, 1) for a, b in v.items()})
