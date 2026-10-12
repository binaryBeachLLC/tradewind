"""Shared helpers for the TW-1 test analysis scripts: paths, log reader, plot style, results.json."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST = os.path.join(ROOT, "test")
DATA = os.path.join(TEST, "data")
FIG = os.path.join(ROOT, "docs", "figures")
RESULTS = os.path.join(TEST, "results.json")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "sim"))
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402,F401
from plotstyle import apply, C, save, limit_line, label_end, FIG_W, FIG_HALF, FIG_TALL  # noqa: E402,F401

os.makedirs(FIG, exist_ok=True)
apply()


def log(name):
    """Read a CSV log from test/data (lines starting with '#' are the instrument/setup header)."""
    return pd.read_csv(os.path.join(DATA, name), comment="#")


def header(name):
    with open(os.path.join(DATA, name)) as f:
        return [ln[2:].strip() for ln in f if ln.startswith("#")]


def fig_path(name):
    return os.path.join(FIG, "test_" + name)


def sim_results():
    with open(os.path.join(ROOT, "sim", "results.json")) as f:
        return json.load(f)


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating,)):
        return round(float(o), 4)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, float):
        return round(o, 4)
    return o


def store(section, values):
    """Merge one section into test/results.json."""
    data = {}
    if os.path.exists(RESULTS):
        with open(RESULTS) as f:
            data = json.load(f)
    data[section] = _clean(values)
    with open(RESULTS, "w") as f:
        json.dump(dict(sorted(data.items())), f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_results():
    with open(RESULTS) as f:
        return json.load(f)


def ocv_to_soc(v):
    """18650 (NCR18650B-class) open-circuit voltage -> state of charge, %."""
    pts = [(3.0, 0), (3.3, 5), (3.45, 10), (3.55, 20), (3.62, 30), (3.68, 40), (3.74, 50), (3.82, 60),
           (3.9, 70), (3.98, 80), (4.07, 90), (4.18, 100)]
    xs, ys = zip(*pts)
    return np.interp(v, xs, ys)
