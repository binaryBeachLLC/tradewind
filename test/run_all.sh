#!/usr/bin/env bash
# Re-run every test analysis: reads test/data/*.csv, writes docs/figures/test_*, test/results.json, test/compliance.csv.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/miniforge3/envs/hwdesign/bin/python}
rm -f results.json
for s in analyze_bringup analyze_power analyze_solar analyze_sensors analyze_rf analyze_environmental analyze_field analyze_compliance; do
  echo "== $s"; "$PY" "$s.py"
done
