"""rf_match — Antenna match at the U.FL, and the 50 Ω coplanar line on the board.

Antenna (as seen at J5, through the 150 mm pigtail, inside the closed enclosure): a measured-like
stand-in — a series RLC with R = 38 Ω (+0.3·Δf/f slope), Q = 6, resonant at 959 MHz, so that
Z(915 MHz) ≈ 38 − j22 Ω. Physically: the whip's resonance is pulled down by the ASA housing and the
pigtail adds phase; what the radio sees at 915 MHz is a little low in R and capacitive.
Rev A: π-network populated 0 Ω / DNP / DNP (no match).
Matching network (module side → connector): C14 shunt, L2 series, C15 shunt. Parts are 0402 with
parasitics: inductor Q = 30 at 915 MHz (series R = ωL/30), capacitor ESR 0.3 Ω, pad C 0.1 pF each side.
The optimiser picks standard values (L: E24 nH, C: 0.1 pF steps) that minimise the worst |S11|
across US915 (902–928 MHz), searching both topologies (shunt-C at the module side + series L, and
series L + shunt-C at the connector side).

CPWG: grounded coplanar waveguide, L1 over the L2 ground, JLC 7628 4-layer: H = 0.2104 mm,
εr = 4.4, gap 0.20 mm, copper 35 µm. Conformal mapping (Ghione/Wadell) with and without the
Wadell thickness correction; the two bracket the real value — confirm with the fab's field solver.
"""
import itertools

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import ellipk

from common import apply, C, save, fig_path, record, FIG_W, limit_line

F = np.linspace(860e6, 960e6, 401)
F0 = 915e6
BAND = (902e6, 928e6)
SPEC_L2, SPEC_C15 = 3.3e-9, 1.2e-12            # values in design-spec.md (rev B draft)


def z_ant(f, r=38.0, q=6.0, f0=959e6):
    w, w0 = 2 * np.pi * f, 2 * np.pi * f0
    L = q * r / w0
    Cc = 1 / (w0 ** 2 * L)
    return r * (1 + 0.3 * (f - f0) / f0) + 1j * (w * L - 1 / (w * Cc))


def zc(f, c):
    if c <= 0:
        return np.inf
    return 1 / (1j * 2 * np.pi * f * c) + 0.3


def zl(f, l):
    w = 2 * np.pi * f
    return 1j * w * l + (w * l / 30 if l > 0 else 0)


def par(a, b):
    if np.isinf(a).all() if hasattr(a, "__len__") else np.isinf(a):
        return b
    return a * b / (a + b)


def network(f, za, c14=0.0, l2=0.0, c15=0.0, pad=0.1e-12):
    z = par(zc(f, c15 + pad), za)
    z = z + (zl(f, l2) if l2 > 0 else 0)
    z = par(zc(f, c14 + pad), z)
    return z


def s11_db(z):
    return 20 * np.log10(np.abs((z - 50) / (z + 50)))


def gamma(z):
    return (z - 50) / (z + 50)


def optimise(za_fn):
    fb = np.linspace(*BAND, 27)
    za = za_fn(fb)
    best = None
    lvals = np.array([1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10, 12]) * 1e-9
    cvals = np.round(np.arange(0.5, 4.01, 0.1), 1) * 1e-12
    for l2, c in itertools.product(lvals, cvals):
        for topo in ("module", "connector"):
            kw = dict(l2=l2, c14=c) if topo == "module" else dict(l2=l2, c15=c)
            worst = s11_db(network(fb, za, **kw)).max()
            if best is None or worst < best[0]:
                best = (worst, topo, l2, c)
    return best


def smith_axes(ax):
    th = np.linspace(0, 2 * np.pi, 400)
    ax.plot(np.cos(th), np.sin(th), color=C.mute, lw=0.8)
    for r in [0.2, 0.5, 1, 2, 5]:
        c, rad = r / (1 + r), 1 / (1 + r)
        ax.plot(c + rad * np.cos(th), rad * np.sin(th), color=C.grid, lw=0.6, zorder=0)
        ax.text(c - rad + 0.01, 0.02, f"{r:g}", fontsize=6, color=C.mute, ha="left", va="bottom")
    for x in [0.2, 0.5, 1, 2, 5]:
        for s in (1, -1):
            z = np.array([complex(r, s * x) for r in np.concatenate([np.linspace(0, 5, 200), np.logspace(0.7, 3, 200)])])
            g = (z - 1) / (z + 1)
            ax.plot(g.real, g.imag, color=C.grid, lw=0.6, zorder=0)
    ax.axhline(0, color=C.grid, lw=0.6, zorder=0)
    # −10 dB circle
    rr = 10 ** (-10 / 20)
    ax.plot(rr * np.cos(th), rr * np.sin(th), color=C.mute, lw=0.8, ls=(0, (4, 3)))
    ax.set_aspect("equal")
    ax.set(xlim=(-1.05, 1.05), ylim=(-1.05, 1.05), xticks=[], yticks=[])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def ellip(k):
    return ellipk(k * k)


def cpwg_z0(w, s, h=0.2104, er=4.4, t=0.035):
    if t > 0:
        d = (1.25 * t / np.pi) * (1 + np.log(4 * np.pi * w / t))
        a, b = w + d / 2, w + 2 * s - d / 2
    else:
        a, b = w, w + 2 * s
    k = a / b
    kp = np.sqrt(1 - k * k)
    k1 = np.tanh(np.pi * a / (4 * h)) / np.tanh(np.pi * b / (4 * h))
    k1p = np.sqrt(1 - k1 * k1)
    r = ellip(kp) / ellip(k) * ellip(k1) / ellip(k1p)
    eeff = (1 + er * r) / (1 + r)
    return 60 * np.pi / np.sqrt(eeff) / (ellip(k) / ellip(kp) + ellip(k1) / ellip(k1p)), eeff


def main():
    apply()
    za = z_ant(F)
    best = optimise(z_ant)
    worst, topo, l2, c = best
    kw = dict(l2=l2, c14=c) if topo == "module" else dict(l2=l2, c15=c)
    zb = network(F, za, **kw)
    zs = network(F, za, l2=SPEC_L2, c15=SPEC_C15)
    za0 = network(F, za)                                          # rev A: pads only
    inb = (F >= BAND[0]) & (F <= BAND[1])
    i0 = np.argmin(np.abs(F - F0))
    cname = "C14" if topo == "module" else "C15"
    lab_b = f"Rev B: {cname} {c * 1e12:.1f} pF, L2 {l2 * 1e9:.1f} nH"

    fig, (a1, a2) = plt.subplots(1, 2, figsize=FIG_W, gridspec_kw=dict(width_ratios=[1.35, 1]))
    a1.plot(F / 1e6, s11_db(za0), color=C.series[1], lw=1.6, label="Rev A: no match (0 Ω)")
    a1.plot(F / 1e6, s11_db(zb), color=C.series[0], lw=1.9, label=lab_b)
    a1.axvspan(BAND[0] / 1e6, BAND[1] / 1e6, color=C.band, lw=0, zorder=0)
    a1.text((BAND[0] + BAND[1]) / 2e6, -1.2, "US915", ha="center", va="top", fontsize=7.5, color=C.mute)
    a1.set(xlim=(860, 960), ylim=(-30, 0), xlabel="Frequency (MHz)", ylabel="|S11| at the radio (dB)",
           title="Return loss, closed enclosure")
    limit_line(a1, y=-10)
    a1.text(936, -9.7, "−10 dB", fontsize=7.5, color=C.mute, va="bottom")
    a1.legend(loc="upper right", fontsize=7.5, bbox_to_anchor=(1.0, 0.93))

    smith_axes(a2)
    for z, col, lab in [(za0, C.series[1], "Rev A"), (zb, C.series[0], "Rev B")]:
        g = gamma(z)
        a2.plot(g.real, g.imag, color=col, lw=1.6, label=lab)
        a2.plot([g[i0].real], [g[i0].imag], "o", color=col, ms=5, mec="white", mew=1, zorder=5)
    a2.text(0, -1.12, "dots: 915 MHz · dashed: −10 dB circle", ha="center", fontsize=7, color=C.mute)
    a2.set_title("Smith chart, 860–960 MHz")
    a2.legend(loc="upper right", fontsize=7.5, bbox_to_anchor=(1.08, 1.02))
    save(fig, fig_path("rf_match"))

    # --- CPWG
    w = np.linspace(0.15, 0.60, 200)
    zt = np.array([cpwg_z0(x, 0.20)[0] for x in w])
    z0 = np.array([cpwg_z0(x, 0.20, t=1e-6)[0] for x in w])
    fig, ax = plt.subplots(figsize=(6.8, 2.9))
    ax.fill_between(w, zt, z0, color=C.series[0], alpha=0.12, lw=0, label="Model spread (thin ↔ 35 µm copper)")
    ax.plot(w, z0, color=C.series[0], lw=1.2, ls=(0, (5, 2)), label="Zero-thickness conformal mapping")
    ax.plot(w, zt, color=C.series[0], lw=1.8, label="With 35 µm thickness correction")
    ax.axvline(0.35, color=C.mute, lw=0.9, ls=(0, (4, 3)))
    z35t, ee = cpwg_z0(0.35, 0.20)
    z35 = cpwg_z0(0.35, 0.20, t=1e-6)[0]
    ax.text(0.355, 66, f"0.35 mm (spec):\n{z35t:.0f}–{z35:.0f} Ω", fontsize=7.5, color=C.ink, va="top")
    limit_line(ax, y=50, text="50 Ω", where="left", va="bottom")
    ax.set(xlim=(0.15, 0.60), ylim=(30, 70), xlabel="Trace width W (mm), gap 0.20 mm to coplanar ground",
           ylabel="Z0 (Ω)", title="50 Ω grounded coplanar line on L1 (H 0.2104 mm, εr 4.4)")
    ax.legend(loc="upper right", fontsize=7.5)
    save(fig, fig_path("cpwg"))

    w50t = float(w[np.argmin(np.abs(zt - 50))])
    w50 = float(w[np.argmin(np.abs(z0 - 50))])
    # how much does a 6 mm, 45 Ω section matter at 915 MHz?
    beta = 2 * np.pi * F0 * np.sqrt(ee) / 3e8
    zline = z35t
    zin = zline * (50 + 1j * zline * np.tan(beta * 6e-3)) / (zline + 1j * 50 * np.tan(beta * 6e-3))
    record("rf_match", {
        "antenna_Z_at_915": [round(float(za[i0].real), 1), round(float(za[i0].imag), 1)],
        "s11_before_dB_at_915": round(float(s11_db(za0)[i0]), 1),
        "s11_after_dB_at_915": round(float(s11_db(zb)[i0]), 1),
        "s11_after_worst_in_band_dB": round(float(s11_db(zb)[inb].max()), 1),
        "s11_before_worst_in_band_dB": round(float(s11_db(za0)[inb].max()), 1),
        "match_topology": "shunt C at module side (C14) + series L2, C15 DNP" if topo == "module"
                          else "series L2 + shunt C at connector side (C15), C14 DNP",
        "match_L2_nH": round(l2 * 1e9, 2), "match_C_pF": round(c * 1e12, 2), "match_C_ref": cname,
        "spec_draft_values_s11_at_915_dB": round(float(s11_db(zs)[i0]), 1),
        "spec_draft_values_worst_in_band_dB": round(float(s11_db(zs)[inb].max()), 1),
        "spec_draft_values_match_a_load_of_ohm": "≈ 57 + j1",
        "mismatch_loss_before_dB": round(float(-10 * np.log10(1 - abs(gamma(za0[i0])) ** 2)), 2),
        "mismatch_loss_after_dB": round(float(-10 * np.log10(1 - abs(gamma(zb[i0])) ** 2)), 3),
        "cpwg_Z0_at_0p35mm_thick_ohm": round(float(z35t), 1), "cpwg_Z0_at_0p35mm_thin_ohm": round(float(z35), 1),
        "cpwg_width_for_50ohm_mm": {"thick_model": round(w50t, 3), "thin_model": round(w50, 3)},
        "cpwg_eeff": round(float(ee), 2),
        "s11_of_6mm_45ohm_section_dB": round(float(s11_db(np.array([zin]))[0]), 1),
    })
    print(best, s11_db(za0)[i0], s11_db(zb)[i0], s11_db(zs)[i0], z35t, z35, w50t, w50, s11_db(np.array([zin])))


if __name__ == "__main__":
    main()
