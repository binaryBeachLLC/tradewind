#!/usr/bin/env bash
# Regenerate every Tradewind simulation, figure (docs/figures/sim_*) and sim/results.json.
# Needs: conda env "hwdesign" (python 3.11, numpy, scipy, matplotlib, ngspice 41).
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-$HOME/miniforge3/envs/hwdesign/bin/python}
export NGSPICE=${NGSPICE:-$HOME/miniforge3/envs/hwdesign/bin/ngspice}
rm -f results.json
for s in solar_iv thermal_enclosure link_budget power_budget energy_year vbat_sense tx_droop rain_debounce rf_match board_si; do
  echo "== $s"
  "$PY" "$s.py" > "out/$s.log"
done
echo "done: $(ls ../docs/figures/sim_*.png | wc -l) figures, results in sim/results.json"
