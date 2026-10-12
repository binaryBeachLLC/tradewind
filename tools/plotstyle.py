"""Shared figure style for every Tradewind plot (simulation, test, report).

Usage:
    import sys; sys.path.insert(0, "<repo>/tools")
    from plotstyle import apply, C, save, limit_line, label_end
    apply()
    fig, ax = plt.subplots(figsize=FIG_W)
    ...
    save(fig, "<repo>/docs/figures/name")   # writes name.svg and name.png (200 dpi)

Rules (from the data-viz method we follow):
  * Series colors in the fixed order C.series[0..4]; never cycle, never reuse for status.
  * One y-axis per chart. Two measures of different scale -> two panels.
  * 2 px lines, recessive grid, no top/right spines.
  * Spec limits: muted dashed gray with a text label, not a colored band.
  * >= 2 series: legend present; up to 4 series also get direct end labels (label_end).
  * Text stays in ink colors, never the series color.
"""
from types import SimpleNamespace
import matplotlib as mpl
import matplotlib.pyplot as plt

C = SimpleNamespace(
    series=["#00909a", "#d9622a", "#3d6ad0", "#a87800", "#9558c2"],  # validated, fixed order
    teal="#1d3f47", teal2="#26545a", orange="#f08a3c", gold="#fbbf4a", cream="#fdf6e3",
    ink="#1f2328", mute="#5d6670", grid="#e4e7ea", line="#d9dee2",
    good="#1d7349", bad="#b0322a", band="#eef3f3",
)

FIG_W = (6.8, 3.4)       # full report width
FIG_HALF = (3.3, 2.6)    # half width
FIG_TALL = (6.8, 4.6)
MIN_PT = 8.5             # smallest text in any figure (the report prints them at about 1:1)


def apply():
    mpl.rcParams.update({
        "font.family": ["Inter", "DejaVu Sans", "Arial", "sans-serif"],
        "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
        "axes.titleweight": "semibold", "axes.titlelocation": "left", "axes.titlepad": 8,
        "axes.edgecolor": C.line, "axes.labelcolor": C.ink, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": C.grid, "grid.linewidth": 0.6,
        "axes.prop_cycle": mpl.cycler(color=C.series),
        "xtick.color": C.mute, "ytick.color": C.mute, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "lines.linewidth": 1.6, "lines.markersize": 4,
        "legend.frameon": False, "legend.fontsize": 9, "legend.labelcolor": C.ink,
        "text.color": C.ink, "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "figure.dpi": 110,
        "svg.fonttype": "none",
    })


def limit_line(ax, y=None, x=None, text="", where="right", va="bottom"):
    """Spec / threshold line: muted dashed gray, labelled in ink."""
    kw = dict(color=C.mute, lw=0.9, ls=(0, (4, 3)), zorder=1)
    if y is not None:
        ax.axhline(y, **kw)
        if text:
            xr = ax.get_xlim()
            xt = xr[1] if where == "right" else xr[0]
            ax.annotate(" " + text + " ", (xt, y), xytext=(0, 2 if va == "bottom" else -2), textcoords="offset points",
                        ha="right" if where == "right" else "left", va=va, fontsize=MIN_PT, color=C.mute)
    if x is not None:
        ax.axvline(x, **kw)
        if text:
            yr = ax.get_ylim()
            ax.text(x, yr[1], " " + text, ha="left", va="top", fontsize=MIN_PT, color=C.mute, rotation=0)


def label_end(ax, x, y, text, dy=0, color=None):
    """Direct label at the end of a line (text in ink; a small dot in the series color)."""
    if color:
        ax.plot([x], [y], "o", ms=3.5, color=color, zorder=5, clip_on=False)
    ax.annotate(text, (x, y), xytext=(5, dy), textcoords="offset points",
                va="center", fontsize=MIN_PT, color=C.ink, annotation_clip=False)


def save(fig, path_no_ext, tight=True):
    for t in fig.findobj(mpl.text.Text):        # floor for annotations that set their own size
        if t.get_text() and t.get_fontsize() < MIN_PT:
            t.set_fontsize(MIN_PT)
    if tight:
        fig.tight_layout()
    fig.savefig(path_no_ext + ".svg")
    fig.savefig(path_no_ext + ".png", dpi=200)
    plt.close(fig)
