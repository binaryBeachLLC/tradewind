#!/usr/bin/env bash
# Manufacturing + documentation outputs for Tradewind rev B (KiCad 9 CLI via snap).
# Usage: tools/export_fab.sh        (run from the repo root)
set -euo pipefail
cd "$(dirname "$0")/.."
K="snap run kicad.kicad-cli"
PCB=hardware/tradewind/tradewind.kicad_pcb
SCH=hardware/tradewind/tradewind.kicad_sch
F=hardware/fab
rm -rf "$F/gerbers" "$F/assembly" "$F/3d" "$F/svg"
mkdir -p "$F/gerbers" "$F/assembly" "$F/3d" "$F/svg" docs/schematic

echo "== checks"
$K sch erc --severity-all --exit-code-violations -o "$F/erc_report.txt" "$SCH"
$K pcb drc --schematic-parity --severity-error --exit-code-violations -o "$F/drc_report.txt" "$PCB"

echo "== gerbers + drill"
$K pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
   --subtract-soldermask --use-drill-file-origin -o "$F/gerbers/" "$PCB" >/dev/null
$K pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 -o "$F/gerbers/" "$PCB" >/dev/null
(cd "$F/gerbers" && rm -f ../tradewind_revB_gerbers.zip && zip -q ../tradewind_revB_gerbers.zip ./*)

echo "== placement + BOM"
$K pcb export pos --format csv --units mm --side front --exclude-dnp -o "$F/assembly/tradewind_revB_cpl.csv" "$PCB" >/dev/null
python3 tools/bom.py >/dev/null

echo "== drawings"
$K sch export pdf -o docs/schematic/tradewind_schematic.pdf "$SCH" >/dev/null
$K sch export svg -o docs/schematic/ "$SCH" >/dev/null
$K pcb export pdf --layers F.Fab,Edge.Cuts --include-border-title -o "$F/assembly/assembly_drawing_top.pdf" "$PCB" >/dev/null
$K pcb export pdf --layers F.Cu,F.Silkscreen,Edge.Cuts -o "$F/assembly/top_copper_silk.pdf" "$PCB" >/dev/null
for L in F.Cu In1.Cu In2.Cu B.Cu F.Silkscreen B.Silkscreen F.Mask; do
  $K pcb export svg --layers "$L,Edge.Cuts" --mode-single --page-size-mode 2 --exclude-drawing-sheet \
     -o "$F/svg/${L/./_}.svg" "$PCB" >/dev/null
done
$K pcb export svg --layers F.Cu,B.Cu,F.Silkscreen,Edge.Cuts --mode-single --page-size-mode 2 --exclude-drawing-sheet \
   -o "$F/svg/composite_top.svg" "$PCB" >/dev/null

echo "== 3D"
$K pcb export step --subst-models --force -o "$F/3d/tradewind_revB.step" "$PCB" >/dev/null
$K pcb export glb --subst-models --include-tracks --include-pads --include-silkscreen --include-soldermask --force \
   -o "$F/3d/tradewind_revB.glb" "$PCB" >/dev/null
$K pcb export vrml --force -o "$F/3d/tradewind_revB.wrl" "$PCB" >/dev/null 2>&1 || true

echo "== KiCad renders"
mkdir -p render/out/kicad
$K pcb render --quality high -w 2400 -h 1750 --side top -o render/out/kicad/pcb_top.png "$PCB" >/dev/null
$K pcb render --quality high -w 2400 -h 1750 --side bottom -o render/out/kicad/pcb_bottom.png "$PCB" >/dev/null
$K pcb render --quality high --perspective --floor --rotate "320,0,335" -w 2400 -h 1600 -o render/out/kicad/pcb_iso.png "$PCB" >/dev/null
echo "== layout audit"
snap run --shell kicad.kicad-cli -c "python3 tools/layout_audit.py" >/dev/null 2>&1
${PY:-$HOME/miniforge3/envs/hwdesign/bin/python} tools/layout_figs.py >/dev/null

echo "done: $(ls $F | tr '\n' ' ')"
