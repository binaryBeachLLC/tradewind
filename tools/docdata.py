"""Single source for every number quoted in the report and the datasheet (read from the result files)."""
import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _j(p):
    return json.load(open(os.path.join(ROOT, p)))


SIM = _j("sim/results.json")
LAYOUT = _j("hardware/fab/layout_audit.json")
LAYOUT_KEYS = _j("docs/figures/layout_keys.json")   # numbered markers in the layout figures
TEST = _j("test/results.json")
MECH = _j("mechanical/results.json")
BOM = _j("hardware/fab/bom_summary.json")
COMPLIANCE = list(csv.DictReader(open(os.path.join(ROOT, "test/compliance.csv"))))
BOM_ROWS = list(csv.DictReader(open(os.path.join(ROOT, "hardware/fab/BOM_tradewind_revB.csv"))))
H = TEST["headline"]

DOC_REPORT = "BB-ENG-2026-014"
DOC_DS = "BBDS-TW1 – OCTOBER 2026"
REV = "B"
DATE = "October 12, 2026"
REPO = "github.com/binaryBeachLLC/tradewind"


def f(v, nd=1):
    """Format a number with nd decimals (strip trailing zeros only when nd == 0)."""
    if isinstance(v, (int,)) or nd == 0:
        return "{:,.0f}".format(v)
    return "{:,.{n}f}".format(v, n=nd)


def status_pill(s):
    s = s.lower()
    if s.startswith("pass") and "marginal" in s:
        return '<span class="pill warn">pass · marginal</span>'
    if s.startswith("pass"):
        return '<span class="pill ok">pass</span>'
    if s.startswith("open"):
        return '<span class="pill bad">open</span>'
    return '<span class="pill">%s</span>' % s
