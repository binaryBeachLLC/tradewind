"""Load KiCad 9 library symbols (flattening `extends`) and report pin geometry."""
import copy
import os
from sexpr import parse, find, find1, Sym

KICAD_SHARE = "/snap/kicad/current/usr/share/kicad"
SYM_DIR = os.path.join(KICAD_SHARE, "symbols")
PROJECT_SYM = os.path.join(os.path.dirname(__file__), "..", "hardware", "tradewind", "tradewind.kicad_sym")

_cache = {}


def _lib(libname):
    if libname not in _cache:
        path = PROJECT_SYM if libname == "tradewind" else os.path.join(SYM_DIR, libname + ".kicad_sym")
        tree = parse(open(path).read())
        _cache[libname] = {s[1]: s for s in find(tree, "symbol")}
    return _cache[libname]


def load_symbol(lib_id):
    """Return a flattened symbol S-expr named 'Lib:Name' suitable for a schematic's lib_symbols."""
    libname, name = lib_id.split(":")
    syms = _lib(libname)
    sym = copy.deepcopy(syms[name])
    ext = find1(sym, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        child_props = {p[1]: p for p in find(sym, "property")}
        out = [Sym("symbol"), lib_id]
        for item in parent[2:]:
            if isinstance(item, list) and item and item[0] == "property" and item[1] in child_props:
                out.append(child_props.pop(item[1]))
            elif isinstance(item, list) and item and item[0] == "symbol":
                sub = copy.deepcopy(item)
                sub[1] = sub[1].replace(ext[1], name, 1)
                out.append(sub)
            else:
                out.append(item)
        # child-only properties go after the parent's
        idx = max(i for i, x in enumerate(out) if isinstance(x, list) and x and x[0] == "property") + 1
        for p in child_props.values():
            out.insert(idx, p)
            idx += 1
        sym = out
    else:
        sym[1] = lib_id
    return sym


def pins(sym):
    """List of dicts: number, name, type, x, y (lib coords, Y up), angle, length, hidden, unit."""
    res = []
    for sub in find(sym, "symbol"):
        unit = int(sub[1].split("_")[-2])
        for p in find(sub, "pin"):
            at = find1(p, "at")
            hidden = any(x == "hide" for x in p) or bool(find1(p, "hide"))
            res.append(dict(
                type=str(p[1]), number=find1(p, "number")[1], name=find1(p, "name")[1],
                x=float(at[1]), y=float(at[2]), angle=int(float(at[3])),
                length=float(find1(p, "length")[1]), hidden=hidden, unit=unit))
    return res


def bbox(sym):
    """Rough body bbox in lib coords from rectangles/polylines/pins."""
    xs, ys = [], []
    for sub in find(sym, "symbol"):
        for r in find(sub, "rectangle"):
            s, e = find1(r, "start"), find1(r, "end")
            xs += [float(s[1]), float(e[1])]
            ys += [float(s[2]), float(e[2])]
        for p in find(sub, "pin"):
            at = find1(p, "at")
            xs.append(float(at[1]))
            ys.append(float(at[2]))
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))


if __name__ == "__main__":
    import sys
    for lid in sys.argv[1:]:
        s = load_symbol(lid)
        print("==", lid, "bbox", bbox(s))
        for p in sorted(pins(s), key=lambda p: (p["unit"], p["number"])):
            print("  %4s %-16s %-14s (%7.2f,%7.2f) a%-3d u%d%s" % (
                p["number"], p["name"], p["type"], p["x"], p["y"], p["angle"], p["unit"], " hidden" if p["hidden"] else ""))
