"""Minimal S-expression reader/writer for KiCad files (symbols, schematics, footprints)."""
import re

_TOKEN = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))', re.S)


class Sym(str):
    """Unquoted atom (keyword / number). Plain str = quoted string."""


def parse(text):
    stack, cur = [], []
    pos = 0
    n = len(text)
    while pos < n:
        m = _TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("parse error at %d: %r" % (pos, text[pos:pos + 40]))
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            s = m.group(3)[1:-1]
            cur.append(s.replace('\\"', '"').replace("\\\\", "\\"))
        else:
            cur.append(Sym(m.group(4)))
    return cur[0] if len(cur) == 1 else cur


def dump(node, indent=0):
    """Serialize back to KiCad-style text (tabs, one list per line when nested)."""
    if isinstance(node, list):
        if not node:
            return "()"
        simple = all(not isinstance(x, list) for x in node)
        if simple:
            return "(" + " ".join(_atom(x) for x in node) + ")"
        pad = "\t" * (indent + 1)
        parts = ["(" + _atom(node[0])]
        rest = node[1:]
        # keep leading atoms on the first line
        i = 0
        while i < len(rest) and not isinstance(rest[i], list):
            parts[0] += " " + _atom(rest[i])
            i += 1
        for x in rest[i:]:
            parts.append(pad + (dump(x, indent + 1) if isinstance(x, list) else _atom(x)))
        return "\n".join(parts) + "\n" + "\t" * indent + ")"
    return _atom(node)


def _atom(x):
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int, float)):
        return fmt_num(x)
    s = str(x).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"' + s + '"'


def fmt_num(v):
    if isinstance(v, int):
        return str(v)
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def find(node, key):
    """All direct children lists whose head == key."""
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def find1(node, key):
    r = find(node, key)
    return r[0] if r else None


def prop(node, name):
    for p in find(node, "property"):
        if p[1] == name:
            return p[2]
    return None
