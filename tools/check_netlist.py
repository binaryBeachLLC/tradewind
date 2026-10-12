"""Verify the KiCad-exported netlist matches tools/design.py exactly (every pin, every net)."""
import os, sys
import design
from sexpr import parse, find, find1
path = os.path.join(os.path.dirname(__file__), "..", "hardware", "tradewind", "tradewind.net")
tree = parse(open(path).read())
nets = find1(tree, "nets")
kicad = {}
for n in find(nets, "net"):
    name = find1(n, "name")[1].split("/")[-1]
    for node in find(n, "node"):
        kicad[(find1(node, "ref")[1], find1(node, "pin")[1])] = name
errors = 0
groups = {}
for p in design.parts:
    if p["ref"].startswith("#"):
        continue
    for pin, net in p["pins"].items():
        k = (p["ref"], pin)
        got = kicad.get(k)
        if net is None:
            if got and not got.startswith("unconnected"):
                print("NC pin connected:", k, got); errors += 1
            continue
        if got is None:
            print("missing:", k, net); errors += 1
        else:
            groups.setdefault(net, set()).add(got)
for net, got in groups.items():
    if len(got) != 1 or (net not in got and not any(g.endswith(net) for g in got)):
        print("net mismatch:", net, got); errors += 1
print("pins checked:", sum(len(p["pins"]) for p in design.parts), "nets:", len(groups), "errors:", errors)
sys.exit(1 if errors else 0)
