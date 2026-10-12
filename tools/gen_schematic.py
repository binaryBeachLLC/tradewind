"""Generate the Tradewind KiCad 9 schematic (root + 3 sheets) from tools/design.py.

Style: every pin gets a short stub; nets are joined by labels (local inside a sheet, global across sheets)
and by GND / +3V3 power symbols. Functional blocks are framed and titled, with design notes in each.
Run: python3 tools/gen_schematic.py   (then kicad-cli sch erc hardware/tradewind/tradewind.kicad_sch)
"""
import math
import os
import uuid

import design
from kicadlib import load_symbol, pins as sym_pins, bbox
from sexpr import dump, fmt_num as F

OUT = os.path.join(os.path.dirname(__file__), "..", "hardware", "tradewind")
PROJECT = "tradewind"
NS = uuid.UUID("6f1d2b1e-7a43-4c55-9a0e-1d0c5e7a7b11")
STUB = 2.54
DATE = "2026-10-11"
REV = "B"
TEAL = "(color 29 63 71 1)"
ORANGE = "(color 196 98 27 1)"


def uid(*seed):
    return str(uuid.uuid5(NS, "/".join(str(s) for s in seed)))


ROOT_UUID = uid("root")
SHEET_UUID = {s: uid("sheet", s) for s in design.SHEETS}
PAGE = {"power": "2", "mcu_rf": "3", "sensors_io": "4"}
SHEET_NAME = {"power": "Power", "mcu_rf": "Radio_MCU", "sensors_io": "Sensors_IO"}


def rot(vx, vy, deg):
    """Rotate a screen vector CCW (as seen on screen, Y down) by deg."""
    t = math.radians(deg)
    c, s = round(math.cos(t)), round(math.sin(t))
    return vx * c + vy * s, -vx * s + vy * c


def r2(v):
    return round(v * 10000) / 10000


# ---------------------------------------------------------------------------- net scope
net_sheets = {}
for p in design.parts:
    for n in p["pins"].values():
        if n:
            net_sheets.setdefault(n, set()).add(p["sheet"])
POWER_SYMS = {"GND": "power:GND", "+3V3": "power:+3V3"}


def is_global(net):
    return len(net_sheets.get(net, ())) > 1


class Sheet:
    def __init__(self, name, title):
        self.name, self.title = name, title
        self.items = []
        self.libs = set()
        self.pwr = 0

    def add(self, s):
        self.items.append(s)

    def wire(self, x1, y1, x2, y2):
        self.add('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))'
                 % (F(r2(x1)), F(r2(y1)), F(r2(x2)), F(r2(y2)), uid(self.name, "w", x1, y1, x2, y2)))

    def label(self, net, x, y, d):
        ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[d]
        if is_global(net):
            just = "left" if ang in (0, 90) else "right"
            self.add('(global_label "%s" (shape passive) (at %s %s %d) (fields_autoplaced yes) '
                     '(effects (font (size 1.27 1.27)) (justify %s)) (uuid "%s") '
                     '(property "Intersheetrefs" "${INTERSHEET_REFS}" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes))))'
                     % (net, F(r2(x)), F(r2(y)), ang, just, uid(self.name, "gl", net, x, y), F(r2(x)), F(r2(y))))
        else:
            just = "left bottom" if ang in (0, 90) else "right bottom"
            self.add('(label "%s" (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s)) (uuid "%s"))'
                     % (net, F(r2(x)), F(r2(y)), ang, just, uid(self.name, "l", net, x, y)))

    def power(self, net, x, y, d):
        lib = POWER_SYMS[net]
        self.libs.add(lib)
        if net == "GND":
            ang = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
        else:
            ang = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
        self.pwr += 1
        ref = "#PWR%s%02d" % ({"power": "1", "mcu_rf": "2", "sensors_io": "3"}[self.name], self.pwr)
        vx, vy = x + d[0] * 4.2, y + d[1] * 4.2
        vis = "(hide yes)" if net == "GND" else ""
        just = "(justify %s)" % ("right" if d == (-1, 0) else "left") if d[0] else ""
        u = uid(self.name, "pwr", net, x, y)
        self.add(
            '(symbol (lib_id "%s") (at %s %s %d) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
            '(uuid "%s") '
            '(property "Reference" "%s" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes))) '
            '(property "Value" "%s" (at %s %s 0) (effects (font (size 1.27 1.27)) %s %s)) '
            '(property "Footprint" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes))) '
            '(property "Datasheet" "" (at %s %s 0) (effects (font (size 1.27 1.27)) (hide yes))) '
            '(pin "1" (uuid "%s")) '
            '(instances (project "%s" (path "/%s/%s" (reference "%s") (unit 1)))))'
            % (lib, F(r2(x)), F(r2(y)), ang, u, ref, F(r2(x)), F(r2(y)), net, F(r2(vx)), F(r2(vy)), vis, just,
               F(r2(x)), F(r2(y)), F(r2(x)), F(r2(y)), uid(u, "p"), PROJECT, ROOT_UUID, SHEET_UUID[self.name], ref))

    def noconnect(self, x, y):
        self.add('(no_connect (at %s %s) (uuid "%s"))' % (F(r2(x)), F(r2(y)), uid(self.name, "nc", x, y)))

    def text(self, s, x, y, size=1.27, bold=False, color="", ang=0):
        self.add('(text "%s" (exclude_from_sim no) (at %s %s %d) (effects (font (size %s %s) %s %s) (justify left bottom)) (uuid "%s"))'
                 % (s.replace('"', "'"), F(r2(x)), F(r2(y)), ang, F(size), F(size), "(bold yes)" if bold else "",
                    color, uid(self.name, "t", s, x, y)))

    def frame(self, title, x0, y0, x1, y1):
        self.add('(rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type dash) %s) (fill (type none)) (uuid "%s"))'
                 % (F(x0), F(y0), F(x1), F(y1), TEAL, uid(self.name, "fr", title)))
        self.text(title, x0 + 1.27, y0 + 3.3, size=1.8, bold=True, color=TEAL)

    # ------------------------------------------------------------------ parts
    def part(self, p):
        if p["lib"] == "tradewind:DRV5032FB" or True:
            self.libs.add(p["lib"])
        sym = load_symbol(p["lib"])
        x, y, r = p["x"], p["y"], p["rot"]
        u = uid(self.name, "sym", p["ref"])
        placed = {}
        for pin in sym_pins(sym):
            if pin["number"] not in p["pins"]:
                continue
            ox, oy = rot(pin["x"], -pin["y"], r)
            px, py = x + ox, y + oy
            a = math.radians(pin["angle"])
            dx, dy = rot(-round(math.cos(a)), round(math.sin(a)), r)
            d = (int(dx), int(dy))
            net = p["pins"][pin["number"]]
            key = (round(px, 3), round(py, 3))
            if key in placed:
                assert placed[key] == net, (p["ref"], pin["number"], net, placed[key])
                continue
            placed[key] = net
            if net is None:
                self.noconnect(px, py)
                continue
            ex, ey = px + d[0] * STUB, py + d[1] * STUB
            self.wire(px, py, ex, ey)
            if net in POWER_SYMS:
                self.power(net, ex, ey, d)
            else:
                self.label(net, ex, ey, d)

        # field placement
        bx0, by0, bx1, by1 = bbox(sym)
        two_pin = p["lib"] in ("Device:R", "Device:C", "Device:L", "Device:Thermistor_NTC", "Device:Polyfuse",
                               "Device:Battery_Cell")
        fet = p["lib"].startswith("Transistor_FET")
        if two_pin and r == 0:
            rf, vf, j = (x + 2.54, y - 1.0), (x + 2.54, y + 1.6), "left"
        elif two_pin:
            rf, vf, j = (x, y - 2.6), (x, y + 3.6), ""
        elif fet:
            rf, vf, j = (x + 5.08, y - 1.0), (x + 5.08, y + 1.6), "left"
        elif p["lib"] in ("Device:LED", "Device:D_TVS", "Switch:SW_Push"):
            rf, vf, j = (x, y - 3.4), (x, y + 4.2), ""
        elif p["lib"] in ("Connector:TestPoint", "power:PWR_FLAG"):
            rf, vf, j = (x + 1.6, y - 3.2), (x + 1.6, y - 5.2), "left"
        elif p["lib"].startswith("Mechanical"):
            rf, vf, j = (x + 3.2, y - 0.6), (x + 3.2, y + 1.6), "left"
        else:
            rf, vf, j = (x + bx0, y - by1 - 1.6), (x + bx0, y - by0 + 2.4 + (3.2 if by0 < -1 else 0)), "left"
            if p["lib"].startswith("Connector_Generic"):
                rf, vf = (x - 1.27, y - by1 - 1.6), (x - 1.27, y - by0 + 1.9)
        hide_ref = p["ref"].startswith("#")
        just = "(justify %s)" % j if j else ""

        def fld(name, val, at=None, hide=True, size=1.27):
            at = at or (x, y)
            return '(property "%s" "%s" (at %s %s 0) (effects (font (size %s %s)) %s %s))' % (
                name, str(val).replace('"', "'"), F(r2(at[0])), F(r2(at[1])), F(size), F(size),
                "(hide yes)" if hide else "", "" if hide else just)

        props = [fld("Reference", p["ref"], rf, hide=hide_ref), fld("Value", p["value"], vf, hide=False),
                 fld("Footprint", p["fp"]), fld("Datasheet", p["extra"].get("ds", "")),
                 fld("Description", p["desc"])]
        if p["mpn"]:
            props += [fld("MPN", p["mpn"]), fld("Manufacturer", p["mfr"])]
        pins_txt = " ".join('(pin "%s" (uuid "%s"))' % (pn["number"], uid(u, "pin", pn["number"]))
                            for pn in sym_pins(sym))
        self.add('(symbol (lib_id "%s") (at %s %s %d) (unit 1) (exclude_from_sim no) (in_bom %s) (on_board %s) (dnp %s) '
                 '(uuid "%s") %s %s (instances (project "%s" (path "/%s/%s" (reference "%s") (unit 1)))))'
                 % (p["lib"], F(r2(x)), F(r2(y)), r, "yes" if p["bom"] else "no",
                    "no" if p["lib"] == "power:PWR_FLAG" else "yes", "yes" if p["dnp"] else "no",
                    u, " ".join(props), pins_txt, PROJECT, ROOT_UUID, SHEET_UUID[self.name], p["ref"]))

    def write(self, path, page_title, comments=()):
        libs = "\n".join(dump(load_symbol(l), 1) for l in sorted(self.libs))
        cm = " ".join('(comment %d "%s")' % (i + 1, c) for i, c in enumerate(comments))
        body = "\n\t".join(self.items)
        uu = ROOT_UUID if self.name == "root" else SHEET_UUID[self.name]
        tail = '\n\t(sheet_instances (path "/" (page "1")))' if self.name == "root" else ""
        txt = ('(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "9.0")\n'
               '\t(uuid "%s")\n\t(paper "A3")\n'
               '\t(title_block (title "%s") (date "%s") (rev "%s") (company "Binary Beach LLC · Honolulu, Hawaii") %s)\n'
               '\t(lib_symbols\n%s\n\t)\n\t%s%s\n\t(embedded_fonts no)\n)\n'
               % (uu, page_title, DATE, REV, cm, libs, body, tail))
        open(path, "w").write(txt)


def build():
    sheets = {}
    for name, title in design.SHEETS.items():
        sh = Sheet(name, title)
        for fr in design.FRAMES[name]:
            t, x0, y0, x1, y1 = fr
            sh.frame(t, x0 * 2.54, y0 * 2.54, x1 * 2.54, y1 * 2.54)
        for (gx, gy, s) in design.NOTES[name]:
            sh.text(s, gx * 2.54, gy * 2.54, size=1.27)
        for p in design.parts:
            if p["sheet"] == name:
                sh.part(p)
        sheets[name] = sh
        sh.write(os.path.join(OUT, name + ".kicad_sch"), "Tradewind TW-1 · " + title,
                 ("Solar LoRaWAN field sensor", "Generated from tools/design.py", "CERN-OHL-P-2.0"))

    # ---------------------------------------------------------------- root
    root = Sheet("root", "root")
    root.text("TRADEWIND TW-1", 25.4, 35.56, size=5, bold=True, color=TEAL)
    root.text("Solar LoRaWAN field sensor · rev B · 4-layer, 96 × 70 mm", 25.4, 43.18, size=2.2, color=ORANGE)
    blocks = [("power", 25.4, 60.96), ("mcu_rf", 152.4, 60.96), ("sensors_io", 279.4, 60.96)]
    for name, x, y in blocks:
        su = SHEET_UUID[name]
        root.add('(sheet (at %s %s) (size 101.6 50.8) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
                 '(fields_autoplaced yes) (stroke (width 0.3) (type solid) %s) (fill (color 253 246 227 1)) (uuid "%s") '
                 '(property "Sheetname" "%s" (at %s %s 0) (effects (font (size 1.8 1.8) (bold yes)) (justify left bottom))) '
                 '(property "Sheetfile" "%s.kicad_sch" (at %s %s 0) (effects (font (size 1.27 1.27)) (justify left top))) '
                 '(instances (project "%s" (path "/%s" (page "%s")))))'
                 % (F(x), F(y), TEAL, su, SHEET_NAME[name], F(x), F(y - 0.8), name, F(x), F(y + 51.6),
                    PROJECT, ROOT_UUID, PAGE[name]))
    # contents of each block, as text inside the sheet symbol
    contents = {
        "power": ["Solar in: TVS + reverse-FET", "BQ24074 charger, VIN-DPM 4.5 V", "Protected 18650 + NTC",
                  "TPS63900 buck-boost → 3.3 V", "Switched battery sense"],
        "mcu_rf": ["RAK3172 (STM32WLE5) LoRaWAN", "π-match → U.FL → SMA", "SWD (Tag-Connect), UART pads",
                   "LED, reset, hall-switch wake", "Holes, fiducials"],
        "sensors_io": ["SHT40 internal T/RH", "J4 air probe (SHT45)", "J3 soil probe, switched 3.3 V",
                       "J2 rain gauge, debounced", "TPD4E02B04 ESD"],
    }
    for name, x, y in blocks:
        for i, line in enumerate(contents[name]):
            root.text("• " + line, x + 3.81, y + 8.89 + i * 4.3, size=1.5)
    notes = [
        "Power tree: panel 5 V/2 W → VIN_SOLAR → BQ24074 → VSYS (4.4 V in sun, = VBAT in dark) → TPS63900 → +3V3 (module, sensors).",
        "Sleep budget at the battery: BQ24074 4.3 µA + RAK3172 1.7 µA + hall 0.54 µA + rest → about 7 µA.",
        "Default uplink every 5 min (≈ 78 µA average); rapid mode 1 min (≈ 365 µA). Charging allowed 0 to 50 °C (NTC).",
        "All parts on the top side. 50 Ω CPWG RF trace. Fab: 4-layer 1.6 mm (JLC 7628 stackup), ENIG, matte black mask, white silk.",
        "Rev B changes from rev A: high-side battery-sense switch (sleep 34 → 7 µA), debounce C22 22 nF added,",
        "π-match fitted (C14 1.8 pF, L2 7.5 nH) after tuning in the closed case.",
    ]
    for i, n in enumerate(notes):
        root.text(n, 25.4, 137.16 + i * 5.08, size=1.6)
    root.text("Generated from tools/design.py by tools/gen_schematic.py. Checked with KiCad 9 ERC.", 25.4, 175.26,
              size=1.27, color=ORANGE)
    root.write(os.path.join(OUT, PROJECT + ".kicad_sch"), "Tradewind TW-1 · Solar LoRaWAN field sensor",
               ("Root sheet", "Binary Beach reference design", "CERN-OHL-P-2.0"))

    open(os.path.join(OUT, "sym-lib-table"), "w").write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "tradewind")(type "KiCad")(uri "${KIPRJMOD}/tradewind.kicad_sym")(options "")(descr "Tradewind project symbols"))\n)\n')
    print("schematic written:", ", ".join(design.SHEETS), "+ root")


if __name__ == "__main__":
    build()
