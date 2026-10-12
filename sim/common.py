"""Shared helpers for the Tradewind simulations: paths, plot style, ngspice runner, results.json."""
import json
import logging
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIM = os.path.join(ROOT, "sim")
SPICE = os.path.join(SIM, "spice")
OUT = os.path.join(SIM, "out")
FIG = os.path.join(ROOT, "docs", "figures")
sys.path.insert(0, os.path.join(ROOT, "tools"))
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
from plotstyle import apply, C, save, limit_line, label_end, FIG_W, FIG_HALF, FIG_TALL  # noqa: E402,F401

os.makedirs(OUT, exist_ok=True)
os.makedirs(FIG, exist_ok=True)

NGSPICE = os.environ.get("NGSPICE", os.path.expanduser("~/miniforge3/envs/hwdesign/bin/ngspice"))


def fig_path(name):
    return os.path.join(FIG, "sim_" + name)


def run_spice(deck, params=None, tag=None):
    """Run an ngspice deck in batch mode. The deck writes ASCII data with `wrdata`.

    `params` replaces {key} placeholders in the deck text; the expanded deck is written to sim/out.
    Returns the path of the expanded deck.
    """
    src = os.path.join(SPICE, deck)
    text = open(src).read().replace("{SPICE_DIR}", SPICE)
    for k, v in (params or {}).items():
        text = text.replace("{" + k + "}", str(v))
    tag = tag or os.path.splitext(deck)[0]
    run = os.path.join(OUT, tag + ".cir")
    open(run, "w").write(text)
    r = subprocess.run([NGSPICE, "-b", run], cwd=OUT, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise RuntimeError(f"ngspice failed on {deck}")
    return run


def read_vec(path):
    """Read a wrdata file written with `set wr_singlescale` + `set wr_vecnames` -> dict of arrays."""
    with open(path) as f:
        names = f.readline().split()
    d = np.loadtxt(path, skiprows=1)
    return {n: d[:, i] for i, n in enumerate(names)}


def read_wrdata(path):
    """wrdata writes x1 y1 x2 y2 ... columns; return (x, [y...])."""
    d = np.loadtxt(path)
    x = d[:, 0]
    ys = [d[:, i] for i in range(1, d.shape[1], 2)]
    return x, ys


def record(section, values):
    """Merge headline numbers into sim/results.json under `section`."""
    p = os.path.join(SIM, "results.json")
    data = json.load(open(p)) if os.path.exists(p) else {}
    data[section] = values
    json.dump(data, open(p, "w"), indent=2, sort_keys=True)


def load_results():
    p = os.path.join(SIM, "results.json")
    return json.load(open(p)) if os.path.exists(p) else {}
