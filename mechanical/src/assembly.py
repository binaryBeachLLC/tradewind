"""Build the full Tradewind TW-1 installed assembly, check fit, and export everything.

  python mechanical/src/assembly.py            # all outputs
Outputs: mechanical/out/tradewind_assembly.step (Z-up, installed), mechanical/out/stl/*.stl (print
orientation), mechanical/out/web/{assembly,exploded,enclosure_only}.glb (glTF frame: Y up, metres),
mechanical/results.json.
"""
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(__file__))
from common import *  # noqa
import base, lid, roof, shield, bracket, hardware  # noqa

from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp


def all_parts():
    P = [base.build(), lid.build(), lid.light_pipe()]
    P += roof.build() + shield.build() + bracket.build() + hardware.build()
    return P


def board_shape():
    s = cq.importers.importStep(BOARD_STEP).val()
    return s.translate(cq.Vector(-148.0, 140.0, BOARD_Z0))


# ------------------------------------------------------------------ checks
def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


def common_vol(a, b):
    op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    op.Build()
    g = GProp_GProps()
    BRepGProp.VolumeProperties_s(op.Shape(), g)
    return g.Mass()


def checks(parts, board):
    by = {p.name: p.solid() for p in parts}
    res = {}
    solids = board.Solids()
    tall = [s for s in solids if s.BoundingBox().zmax > BOARD_Z0 + 12]       # 18650 cell + holder
    cell = max(tall, key=lambda s: s.BoundingBox().zmax)
    others = [s for s in solids if s.BoundingBox().zmax <= BOARD_Z0 + 12 and s.BoundingBox().zmin > BOARD_Z0 - 0.5]
    res["cell_top_mm_above_floor"] = round(cell.BoundingBox().zmax, 2)
    res["clear_cell_to_lid_mm"] = round(dist(cell, by["lid"]), 2)
    res["clear_cell_holder_to_lid_mm"] = round(min(dist(s, by["lid"]) for s in tall), 2)
    comp_others = cq.Compound.makeCompound(others)
    res["clear_other_parts_to_lid_mm"] = round(dist(comp_others, by["lid"]), 2)
    pcb_body = [s for s in solids if abs(s.BoundingBox().xlen - 96) < 0.5 and abs(s.BoundingBox().ylen - 70) < 0.5]
    # the board rests on the four bosses (contact by design); measure everything else
    base_nb = by["base"]
    for bx, bY in BOARD_HOLES:
        x, y = b2l(bx, bY)
        base_nb = base_nb.cut(cyl(5.6, BOARD_Z0 + 1.5, (x, y, -1.0)))
    res["clear_board_edge_to_walls_and_columns_mm"] = round(min(dist(s, base_nb) for s in pcb_body), 2) if pcb_body else None
    comp_all = cq.Compound.makeCompound(solids)
    res["clear_populated_board_to_base_excl_bosses_mm"] = round(dist(comp_all, base_nb), 2)
    res["board_seated_on_bosses"] = dist(cq.Compound.makeCompound(pcb_body), by["base"]) < 0.01
    res["clear_board_to_gland_nuts_mm"] = round(dist(comp_all, by["glands_pg7"]), 2)
    res["clear_board_to_vent_mm"] = round(dist(comp_all, by["vent_m12"]), 2)
    res["clear_board_to_lid_screws_mm"] = round(dist(comp_all, by["lid_screws"]), 2)
    res["clear_box_top_to_roof_underside_mm"] = round(dist(by["lid"].fuse(by["base"]), by["roof"]), 2)
    res["clear_antenna_to_shield_mm"] = round(dist(by["antenna_915"], by["shield_cap"]), 2)
    # unintended interference (mm^3) for pairs that must not touch
    pairs = [("base", "lid_screws"), ("lid", "light_pipe"), ("base", "glands_pg7"), ("base", "vent_m12"),
             ("base", "sma_bulkhead"), ("roof", "roof_gusset_L"), ("bracket_plate", "pole"), ("ubolts", "pole"),
             ("shield_arm", "bracket_plate"), ("cable_solar", "base"), ("cable_probe", "shield_arm"),
             ("antenna_915", "cable_probe")]
    inter = {}
    for a, b in pairs:
        v = common_vol(by[a], by[b])
        inter["%s|%s" % (a, b)] = round(v, 2)
    res["interference_mm3"] = inter
    # intended: the gasket is compressed by the tongue
    res["gasket_tongue_overlap_mm3"] = round(common_vol(by["gasket"], by["lid"]), 1)
    return res


# ------------------------------------------------------------------ masses / volumes
EXTRA_MASS_G = {"board_assembly_est": 37.0, "cell_18650_protected": 48.0}


def masses(parts):
    m = {}
    for p in parts:
        m[p.name] = round(p.solid().Volume() / 1000.0 * MAT[p.mat]["density"], 1)
    return m


# ------------------------------------------------------------------ exports
def assemble_step(parts, board_assy, path):
    a = cq.Assembly(name="tradewind_tw1")
    for p in parts:
        a.add(p.solid(), name=p.name, color=color(p.mat))
    if board_assy is not None:
        a.add(board_assy, name="pcba", loc=cq.Location(cq.Vector(-148.0, 140.0, BOARD_Z0)))
    world = cq.Assembly(name="tradewind_tw1_installed", loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90))
    world.add(a, name="tw1")
    world.save(path)


def export_stls(parts):
    d = os.path.join(OUT, "stl")
    os.makedirs(d, exist_ok=True)
    by = {p.name: p.solid() for p in parts}
    flip = lambda s: s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180)
    jobs = {
        "base": by["base"],                                    # floor down (bosses on supports)
        "lid": flip(by["lid"]),                                # front face on the bed
        "roof": flip(roof.roof_plate()),                       # flat, top on the bed
        "shield_cap": flip(by["shield_cap"]),
        "shield_plate_x5": flip(by["shield_plate_1"]),
        "shield_spacers_x15": by["shield_spacers"],
        "probe_holder": by["probe_holder"],
    }
    for n, s in jobs.items():
        cq.exporters.export(s, os.path.join(d, n + ".stl"), tolerance=0.02, angularTolerance=0.15)
    return sorted(jobs)


def tess(shape, tol=0.08, ang=0.3):
    v, f = shape.tessellate(tol, ang)
    return np.array([[p.x, p.y, p.z] for p in v]), np.array(f, dtype=np.int64)


def pbr(mat):
    r, g, b = MAT[mat]["rgb"]
    a = MAT[mat].get("alpha", 1.0)
    return trimesh.visual.material.PBRMaterial(
        name=mat, baseColorFactor=[r, g, b, a], metallicFactor=MAT[mat]["metal"],
        roughnessFactor=MAT[mat]["rough"], alphaMode="BLEND" if a < 1 else "OPAQUE", doubleSided=False)


BOARD_GLB = os.path.join(ROOT, ".scratch", "mech", "board.glb")


def board_meshes():
    """KiCad's own GLB of the populated board (colours, silkscreen), merged per material, in the L frame."""
    if shutil.which("snap") and os.path.exists(PCB_FILE):
        os.makedirs(os.path.dirname(BOARD_GLB), exist_ok=True)
        subprocess.run(["snap", "run", "kicad.kicad-cli", "pcb", "export", "glb", "--subst-models", "--include-tracks",
                        "--include-zones", "--include-silkscreen", "--include-soldermask", "--force", "-o", BOARD_GLB,
                        PCB_FILE], capture_output=True)
    sc = trimesh.load(BOARD_GLB)
    # KiCad glTF (m): x = page x, y = up from board bottom, z = page y  ->  L (m)
    M = np.array([[1, 0, 0, -0.148], [0, 0, -1, 0.140], [0, 1, 0, BOARD_Z0 / 1000.0], [0, 0, 0, 1]], dtype=float)
    groups = {}
    for node in sc.graph.nodes_geometry:
        T, gname = sc.graph[node]
        g = sc.geometry[gname]
        mat = getattr(g.visual, "material", None)
        key = None
        if mat is not None and hasattr(mat, "baseColorFactor") and mat.baseColorFactor is not None:
            key = tuple(np.round(np.array(mat.baseColorFactor, dtype=float), 3))
        mesh = g.copy()
        mesh.apply_transform(M @ T)
        groups.setdefault(key, []).append(mesh)
    out = []
    for i, (key, ms) in enumerate(groups.items()):
        merged = trimesh.util.concatenate([trimesh.Trimesh(m.vertices, m.faces, process=False) for m in ms])
        c = list(key) if key else [0.1, 0.4, 0.2, 1.0]
        c = [x / 255.0 if max(c) > 1.0 else x for x in c]
        merged.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            name="pcb_%d" % i, baseColorFactor=c, metallicFactor=0.3 if c[0] > 0.6 and c[1] > 0.6 else 0.0,
            roughnessFactor=0.5))
        out.append(("pcba_%02d" % i, merged))
    return out


def glb(parts, path, explode=False, include=None, with_board=True, board_explode=(0, 0, 40)):
    scene = trimesh.Scene()
    for p in parts:
        if include and p.group not in include and p.name not in include:
            continue
        v, f = tess(p.solid())
        if explode:
            v = v + np.array(p.explode, dtype=float)
        m = trimesh.Trimesh(v / 1000.0, f, process=False)
        m.visual = trimesh.visual.TextureVisuals(material=pbr(p.mat))
        scene.add_geometry(m, node_name=p.name, geom_name=p.name)
    if with_board:
        for n, m in board_meshes():
            m = m.copy()
            if explode:
                m.apply_translation(np.array(board_explode) / 1000.0)
            scene.add_geometry(m, node_name=n, geom_name=n)
    scene.export(path)
    return os.path.getsize(path) / 1e6


ENCLOSURE_GROUPS = {"base", "lid", "light_pipe", "gasket", "inserts", "screws", "glands", "antenna", "vent"}


def main(skip_checks=False):
    os.makedirs(WEB, exist_ok=True)
    parts = all_parts()
    for p in parts:
        assert p.solid().isValid(), p.name
    board = board_shape()
    results = {}
    if not skip_checks:
        results["fit"] = checks(parts, board)
    by = {p.name: p.solid() for p in parts}
    bbox = lambda names: cq.Compound.makeCompound([by[n] for n in names]).BoundingBox()
    b = bbox(["base", "lid"])
    box_dims = [round(b.xlen, 1), round(b.ylen, 1), round(b.zlen, 1)]
    inst = bbox([p.name for p in parts if p.group not in ("pole",)])
    withroof = bbox(["base", "lid", "roof", "panel", "panel_cells", "roof_gusset_L", "roof_gusset_R", "bracket_plate"])
    results["dimensions_mm"] = {
        "box_w_h_d": box_dims,
        "box_with_bosses_depth": round(bbox(["base", "lid"]).zlen, 1),
        "box_roof_panel_w_h_d": [round(withroof.xlen, 1), round(withroof.ylen, 1), round(withroof.zlen, 1)],
        "installed_envelope_w_h_d_excl_pole": [round(inst.xlen, 1), round(inst.ylen, 1), round(inst.zlen, 1)],
        "roof_gap_over_box_front": ROOF_GAP, "roof_tilt_deg": TILT,
        "gland_spacing": round(GLAND_X[1] - GLAND_X[0], 1),
    }
    m = masses(parts)
    groups = {}
    for p in parts:
        groups[p.group] = round(groups.get(p.group, 0) + m[p.name], 1)
    groups.update(EXTRA_MASS_G)
    groups.pop("pole", None)
    results["mass_g"] = {"by_group": groups, "total_installed_excl_pole": round(sum(groups.values()), 0),
                         "box_unit_only": round(sum(groups[g] for g in ("base", "lid", "gasket", "inserts", "screws",
                                                                        "glands", "antenna", "vent", "light_pipe")
                                                    if g in groups) + 37 + 48, 0)}
    # internal free volume: cavity + lid pocket - rim band - board assembly
    t = math.tan(math.radians(DRAFT))
    cav = tapered(cavity_face(0.0, -BASE_DEPTH * t), BASE_DEPTH, -DRAFT).val().Volume()
    pocket = cq.Solid.extrudeLinear(cavity_face(LID_Z0, -RIM_BAND_W), cq.Vector(0, 0, LID_SKIRT)).Volume()
    bandv = (cavity_face(0).Area() - cavity_face(0, -RIM_BAND_W).Area()) * RIM_BAND_H
    vb = sum(s.Volume() for s in board.Solids())
    results["internal_volume_cm3"] = {"gross": round((cav + pocket - bandv) / 1000, 1),
                                      "free_after_pcba": round((cav + pocket - bandv - vb) / 1000, 1)}
    # gasket compression (geometric)
    comp_h = GROOVE_D - TONGUE_H
    results["gasket"] = {"cord_d_mm": CORD_D, "groove_w_x_d_mm": [GROOVE_W, GROOVE_D], "tongue_h_mm": TONGUE_H,
                         "compressed_height_mm": comp_h,
                         "compression_pct": round((CORD_D - comp_h) / CORD_D * 100, 1),
                         "groove_fill_pct": round(math.pi * (CORD_D / 2) ** 2 / (GROOVE_W * comp_h) * 100, 1)}
    # print time estimate: 0.2 mm layers, 0.4 mm nozzle, 4 perimeters / 25 % gyroid -> ~55 % solid,
    # effective 7 mm^3/s on a CoreXY at ASA speeds
    pt = {}
    for n in ("base", "lid", "roof", "shield_cap", "shield_plate_1", "probe_holder", "shield_spacers"):
        v = by[n].Volume() if n != "roof" else roof.roof_plate().Volume()
        k = 5 if n == "shield_plate_1" else 1
        pt[n + (" (x5)" if k > 1 else "")] = round(v * 0.55 * k / 7.0 / 3600 + 0.15, 1)
    results["print_time_h_est"] = pt
    results["print_time_h_total"] = round(sum(pt.values()), 1)

    import csv
    rows = list(csv.DictReader(open(os.path.join(MECH, "BOM_mechanical.csv"))))
    results["bom_usd"] = {"per_unit_at_100": round(sum(float(r["qty"]) * float(r["unit cost @100 (USD)"]) for r in rows), 2),
                          "per_unit_at_1k": round(sum(float(r["qty"]) * float(r["unit cost @1k (USD)"]) for r in rows), 2),
                          "note": "mechanical + panel + probe; 1k assumes molded box/lid (tooling not included)"}
    stls = export_stls(parts)
    results["stl"] = stls
    try:
        board_assy = cq.Assembly.importStep(BOARD_STEP)
    except Exception as e:
        print("board assembly import (colours) failed, using plain solids:", e)
        board_assy = cq.Assembly().add(cq.importers.importStep(BOARD_STEP).val(), name="pcba",
                                       color=cq.Color(0.1, 0.4, 0.2))
    assemble_step(parts, board_assy, os.path.join(OUT, "tradewind_assembly.step"))
    sizes = {}
    sizes["assembly.glb"] = glb(parts, os.path.join(WEB, "assembly.glb"))
    sizes["exploded.glb"] = glb(parts, os.path.join(WEB, "exploded.glb"), explode=True)
    sizes["enclosure_only.glb"] = glb(parts, os.path.join(WEB, "enclosure_only.glb"), include=ENCLOSURE_GROUPS,
                                      with_board=False)
    results["glb_MB"] = {k: round(v, 2) for k, v in sizes.items()}
    json.dump(results, open(os.path.join(MECH, "results.json"), "w"), indent=2)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main(skip_checks="--fast" in sys.argv)
