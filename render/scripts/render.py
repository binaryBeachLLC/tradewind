"""Photoreal renders of Tradewind TW-1 with Blender Cycles (GPU).

blender -b --python render/scripts/render.py -- [shot ...] [--fast]
Shots: hero, outdoor, exploded, open, pcb_hero, pcb_top, pcb_detail, turntable
Inputs: mechanical/out/web/{assembly,exploded}.glb, hardware/fab/3d/tradewind_revB.glb
Outputs: render/out/*.png (and render/out/turntable/*.png)
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "render", "out")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FAST = "--fast" in ARGS
SHOTS = [a for a in ARGS if not a.startswith("--")] or ["hero", "outdoor", "exploded", "open", "pcb_hero", "pcb_top", "pcb_detail"]


# ------------------------------------------------------------------ scene setup
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                break
        except TypeError:
            continue
    for d in prefs.devices:
        d.use = d.type != "CPU"
    sc.cycles.device = "GPU"
    sc.cycles.samples = 64 if FAST else 384
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    sc.render.resolution_percentage = 50 if FAST else 100
    sc.render.image_settings.file_format = "PNG"
    return sc


def world_color(rgb, strength=1.0):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*rgb, 1)
    bg.inputs[1].default_value = strength


def world_sky(sun_elev=38, sun_rot=210, strength=0.9):
    w = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "NISHITA"
        sky.sun_elevation = math.radians(sun_elev)
        sky.sun_rotation = math.radians(sun_rot)
        sky.altitude = 50
        sky.air_density = 1.0
        sky.dust_density = 0.6
    except (AttributeError, TypeError):
        pass
    nt.links.new(sky.outputs[0], nt.nodes["Background"].inputs[0])
    nt.nodes["Background"].inputs[1].default_value = strength


def mat(name, color, rough=0.5, metal=0.0, coat=0.0, sss=0.0, transmission=0.0, ior=1.45):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key, val in (("Coat Weight", coat), ("Subsurface Weight", sss), ("Transmission Weight", transmission), ("IOR", ior)):
        if key in b.inputs:
            b.inputs[key].default_value = val
    if sss and "Subsurface Radius" in b.inputs:
        b.inputs["Subsurface Radius"].default_value = (0.6, 0.6, 0.55)
        if "Subsurface Scale" in b.inputs:
            b.inputs["Subsurface Scale"].default_value = 0.002
    return m


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


def studio(back="#eceae4", floor_y=None, dark=False):
    """Curved cyclorama + three soft area lights."""
    bpy.ops.mesh.primitive_plane_add(size=1)
    cyc = bpy.context.object
    cyc.name = "cyclorama"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.delete(type="VERT")
    bpy.ops.object.mode_set(mode="OBJECT")
    me = cyc.data
    verts, faces = [], []
    R, W, D, Hh, n = 1.2, 8.0, 6.0, 5.0, 24
    prof = [(0, -D)] + [(0, -R + 0.0)]
    pts = [(-D, 0.0)]
    for i in range(n + 1):
        a = -math.pi / 2 + (math.pi / 2) * i / n
        pts.append((R * math.cos(a) - R + 0.0, R * math.sin(a) + R))
    pts = [(-D, 0.0), (0.0, 0.0)] + [(R * math.sin(math.pi / 2 * i / n), R - R * math.cos(math.pi / 2 * i / n)) for i in range(1, n + 1)] + [(R, Hh)]
    for (y, z) in pts:
        verts += [(-W / 2, y, z), (W / 2, y, z)]
    for i in range(len(pts) - 1):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    me.from_pydata(verts, [], faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
    cyc.data.materials.append(mat("backdrop", srgb(back), rough=0.9))
    world_color(srgb("#20262a") if dark else srgb("#d8d6d0"), 0.35 if dark else 0.5)
    return cyc


def area(name, loc, target, size, energy, color=(1, 1, 1)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    L = bpy.context.object
    L.name = name
    L.data.size = size
    L.data.energy = energy
    L.data.color = color
    d = Vector(target) - Vector(loc)
    L.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return L


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def bbox(objs):
    bpy.context.view_layer.update()
    mn, mx = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, w))
            mx = Vector(map(max, mx, w))
    return mn, mx


def camera(target, direction, dist, lens=70, ortho=None, dof=None):
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    d = Vector(direction).normalized()
    cam.location = Vector(target) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    cam_data.clip_start = 0.001
    cam_data.clip_end = 100
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    if dof:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = dist
        cam_data.dof.aperture_fstop = dof
    bpy.context.scene.camera = cam
    return cam


def tune_enclosure_materials(objs):
    """Product materials: UV-stable white ASA with a hint of subsurface, glass-topped panel, steel, etc."""
    table = {
        "asa_white": mat("ASA white", srgb("#f1f0ea"), rough=0.42, sss=0.08, coat=0.08),
        "asa_grey": mat("ASA grey", srgb("#c9ccce"), rough=0.5),
        "panel_cell": mat("Mono cells", srgb("#0d1a30"), rough=0.22, coat=0.5),
        "panel_back": mat("Panel back", srgb("#e8e8e8"), rough=0.5),
        "panel_bus": mat("Bus bars", srgb("#c8c8c8"), rough=0.25, metal=1.0),
        "steel": mat("Stainless", srgb("#b8bcc0"), rough=0.28, metal=1.0),
        "alu": mat("Aluminium", srgb("#c9ced3"), rough=0.35, metal=1.0),
        "brass": mat("Brass", srgb("#c9a24a"), rough=0.3, metal=1.0),
        "black": mat("Black PA", srgb("#1b1d20"), rough=0.55),
        "cable": mat("Cable PUR", srgb("#2a2d31"), rough=0.6),
        "silicone": mat("Silicone", srgb("#3a3d40"), rough=0.7),
        "pole": mat("Galv pole", srgb("#a9adb0"), rough=0.45, metal=0.9),
        "probe": mat("Sintered probe", srgb("#9a9ea2"), rough=0.75, metal=0.6),
        "clear": mat("Light pipe", srgb("#e8f4ff"), rough=0.05, transmission=1.0, ior=1.49),
    }
    for o in objs:
        if o.type != "MESH":
            continue
        for i, slot in enumerate(o.material_slots):
            if slot.material and slot.material.name.split(".")[0] in table:
                o.material_slots[i].material = table[slot.material.name.split(".")[0]]
        o.data.shade_smooth() if hasattr(o.data, "shade_smooth") else None


def ground(color="#5b6b3d", size=40):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    g = bpy.context.object
    m = mat("ground", srgb(color), rough=0.95)
    nt = m.node_tree
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*srgb("#2f4a1f"), 1)
    ramp.color_ramp.elements[1].color = (*srgb("#5f7a38"), 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    g.data.materials.append(m)
    return g


def front_dir(objs):
    """Direction the lid faces (lid centre minus base centre), flattened to horizontal."""
    by = {o.name.split(".")[0]: o for o in objs}
    if "lid" in by and "base" in by:
        a = sum((by["lid"].matrix_world @ Vector(c) for c in by["lid"].bound_box), Vector()) / 8
        b = sum((by["base"].matrix_world @ Vector(c) for c in by["base"].bound_box), Vector()) / 8
        d = a - b
        d.z = 0
        if d.length > 1e-6:
            return d.normalized()
    return Vector((0, -1, 0))


def place_on_floor(objs, z=0.0):
    mn, mx = bbox(objs)
    for o in objs:
        if o.parent is None:
            o.location.z += z - mn.z


def save(name, w, h):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    os.makedirs(OUT, exist_ok=True)
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath)


def three_quarter(front, side=0.75, up=0.32):
    right = Vector((front.y, -front.x, 0))
    return (front + right * side + Vector((0, 0, up))).normalized()


# ------------------------------------------------------------------ shots
def shot_hero(outdoor=False, name="product_hero"):
    reset()
    objs = import_glb(os.path.join(ROOT, "mechanical/out/web/assembly.glb"))
    tune_enclosure_materials(objs)
    place_on_floor(objs, 0.0)
    mn, mx = bbox(objs)
    c = (mn + mx) / 2
    f = front_dir(objs)
    if outdoor:
        world_sky(sun_elev=34, sun_rot=math.degrees(math.atan2(f.y, f.x)) + 140, strength=0.35)
        bpy.context.scene.view_settings.exposure = -0.6
        ground("#3f5a2a")
        bpy.ops.object.light_add(type="SUN")
        sun = bpy.context.object
        sun.data.energy = 2.2
        sun.data.angle = math.radians(1.5)
        d = three_quarter(f, side=-1.4, up=0.9)
        sun.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        camera(c + Vector((0, 0, 0.02)), three_quarter(f, 0.85, 0.18), 1.35, lens=60, dof=5.6)
        save(name + "_outdoor", 2400, 1600)
        return
    studio("#d9dedf")
    span = (mx - mn).length
    area("key", c + three_quarter(f, -1.1, 0.9) * 1.6, c, 1.2, 95)
    area("fill", c + three_quarter(f, 1.4, 0.2) * 1.8, c, 1.6, 30)
    area("rim", c + (-f + Vector((0, 0, 0.9))) * 1.4, c, 0.8, 70)
    area("top", c + Vector((0, 0, 1.6)), c, 2.0, 25)
    camera(c, three_quarter(f, 0.8, 0.22), span * 1.6, lens=55)
    save(name, 2000, 2400)


def shot_exploded():
    reset()
    objs = import_glb(os.path.join(ROOT, "mechanical/out/web/exploded.glb"))
    tune_enclosure_materials(objs)
    tune_pcba_in_assembly(objs)
    place_on_floor(objs, 0.0)
    mn, mx = bbox(objs)
    c = (mn + mx) / 2
    f = front_dir(objs)
    studio("#d9dedf")
    area("key", c + three_quarter(f, -1.1, 0.9) * 1.8, c, 1.4, 110)
    area("fill", c + three_quarter(f, 1.4, 0.2) * 2.0, c, 1.6, 35)
    area("rim", c + (-f + Vector((0, 0, 0.9))) * 1.6, c, 0.9, 75)
    camera(c, three_quarter(f, 1.7, 0.25), (mx - mn).length * 1.5, lens=55)
    save("product_exploded", 2000, 2400)


def tune_pcba_in_assembly(objs):
    """The assembly carries the board as pcba_NN meshes grouped by KiCad colour; give them real finishes."""
    M = {"00": mat("FR4b", srgb("#6d7448"), rough=0.8),
         "01": mat("Black mask b", (0.010, 0.011, 0.012), rough=0.48, coat=0.12),
         "02": mat("Silk b", srgb("#f2f2ee"), rough=0.75),
         "03": mat("ENIG b", srgb("#d9b25a"), rough=0.22, metal=1.0),
         "04": mat("Parts b", srgb("#1b1c1e"), rough=0.5),
         "05": mat("Shield b", srgb("#c4c7ca"), rough=0.25, metal=1.0),
         "09": mat("Tin b", srgb("#cfd1d3"), rough=0.25, metal=1.0),
         "15": mat("Can b", srgb("#c4c7ca"), rough=0.25, metal=1.0)}
    for o in objs:
        n = o.name.split(".")[0]
        if n.startswith("pcba_") and n[5:] in M:
            o.data.materials.clear()
            o.data.materials.append(M[n[5:]])


def shot_open():
    reset()
    objs = import_glb(os.path.join(ROOT, "mechanical/out/web/assembly.glb"))
    tune_enclosure_materials(objs)
    tune_pcba_in_assembly(objs)
    hide = ("lid", "lid_screws", "light_pipe", "roof", "panel", "panel_cells", "panel_busbars", "panel_jbox",
            "roof_gusset_L", "roof_gusset_R", "shield", "probe", "cable_probe")
    keep = [o for o in objs if not o.name.split(".")[0].startswith(hide)]
    f = front_dir(objs)
    for o in objs:
        if o not in keep:
            o.hide_render = True
    place_on_floor(keep, 0.0)
    by = {o.name.split(".")[0]: o for o in objs}
    mn, mx = bbox([by["base"]])
    c = (mn + mx) / 2
    studio("#efede7")
    area("key", c + three_quarter(f, -0.9, 1.1) * 0.9, c, 0.6, 30)
    area("fill", c + three_quarter(f, 1.2, 0.4) * 1.0, c, 0.8, 10)
    area("top", c + f * 0.6 + Vector((0, 0, 0.8)), c, 0.6, 14)
    camera(c, three_quarter(f, 0.45, 0.5), 0.42, lens=60, dof=8)
    save("product_open", 2400, 1800)


def tune_board_materials(objs):
    """KiCad's GLB drops library-model colours; give every part a believable finish by reference."""
    M = dict(
        mask=mat("Black mask", (0.010, 0.011, 0.012), rough=0.48, coat=0.12),
        fr4=mat("FR4", srgb("#6d7448"), rough=0.8),
        enig=mat("ENIG", srgb("#d9b25a"), rough=0.22, metal=1.0),
        cu=mat("Plated holes", srgb("#c9a36a"), rough=0.3, metal=1.0),
        silk=mat("Silk", srgb("#f2f2ee"), rough=0.75),
        epoxy=mat("Epoxy", srgb("#17181a"), rough=0.45),
        mlcc=mat("MLCC", srgb("#a8865c"), rough=0.5),
        res=mat("Thick film", srgb("#1d1e20"), rough=0.5),
        tin=mat("Tin", srgb("#cfd1d3"), rough=0.25, metal=1.0),
        holder=mat("Holder PA66", srgb("#141516"), rough=0.55),
        led=mat("LED", srgb("#7fd18a"), rough=0.1, transmission=0.6),
        gold=mat("Gold", srgb("#e0b85a"), rough=0.2, metal=1.0),
    )
    layer = {"mat_13": "enig", "mat_14": "cu", "mat_15": "silk", "mat_16": "silk", "mat_17": "mask",
             "mat_18": "mask", "mat_19": "fr4"}
    for o in objs:
        if o.type != "MESH":
            continue
        n = o.name.split(".")[0]
        slot = o.material_slots[0].material.name.split(".")[0] if o.material_slots and o.material_slots[0].material else ""
        key = layer.get(slot)
        if not key and not o.material_slots:
            if n.startswith(("C",)):
                key = "mlcc"
            elif n.startswith(("R", "F")):
                key = "res"
            elif n.startswith(("Q", "U", "D1", "L1")):
                key = "epoxy"
            elif n.startswith("L"):
                key = "mlcc"
            elif n == "BT1":
                key = "holder"
            elif n == "D3":
                key = "led"
            elif n in ("SW1", "J5"):
                key = "tin"
            elif n == "J7":
                o.hide_render = True
                continue
        if key:
            o.data.materials.clear()
            o.data.materials.append(M[key])
    for o in objs:
        if o.name.split(".")[0] == "C15":   # not fitted
            o.hide_render = True


def board_scene(dark=True):
    reset()
    objs = import_glb(os.path.join(ROOT, "hardware/fab/3d/tradewind_revB.glb"))
    tune_board_materials(objs)
    mn, mx = bbox(objs)
    c = (mn + mx) / 2
    for o in objs:
        if o.parent is None:
            o.location -= Vector((c.x, c.y, mn.z))
    mn, mx = bbox(objs)
    return objs, (mn + mx) / 2, mn, mx


def shot_pcb_hero():
    objs, c, mn, mx = board_scene()
    studio("#3a4246", dark=True)
    area("key", c + Vector((-0.25, -0.2, 0.35)), c, 0.35, 7)
    area("fill", c + Vector((0.3, -0.25, 0.15)), c, 0.4, 1.6, color=(0.85, 0.92, 1.0))
    area("rim", c + Vector((0.05, 0.35, 0.2)), c, 0.3, 6, color=(1.0, 0.85, 0.7))
    camera(c + Vector((0.004, 0.0, 0.0)), (0.35, -0.75, 0.55), 0.26, lens=70, dof=4.0)
    save("pcb_hero", 2400, 1600)


def shot_pcb_detail():
    objs, c, mn, mx = board_scene()
    studio("#2b3236", dark=True)
    by = {o.name.split(".")[0]: o for o in objs}
    t = c
    if "shield" in by:
        sm, sx = bbox([by["shield"]])
        t = (sm + sx) / 2 + Vector((-0.004, -0.006, -0.002))
    area("key", t + Vector((-0.12, -0.1, 0.18)), t, 0.2, 2.2)
    area("rim", t + Vector((0.08, 0.18, 0.1)), t, 0.15, 2.0, color=(1.0, 0.85, 0.7))
    area("fill", t + Vector((0.15, -0.1, 0.05)), t, 0.2, 0.6)
    camera(t, (-0.45, -0.7, 0.55), 0.085, lens=90, dof=2.8)
    save("pcb_detail_rf", 2400, 1600)


def shot_pcb_top():
    objs, c, mn, mx = board_scene()
    studio("#f4f3ef")
    area("top", c + Vector((0, 0, 0.5)), c, 0.8, 9)
    area("side", c + Vector((-0.3, -0.3, 0.3)), c, 0.4, 2.5)
    camera(c, (0, 0, 1), 0.4, ortho=(mx.x - mn.x) * 1.12)
    save("pcb_top_ortho", 2400, 1800)


def shot_turntable(frames=72):
    reset()
    objs = import_glb(os.path.join(ROOT, "mechanical/out/web/assembly.glb"))
    tune_enclosure_materials(objs)
    place_on_floor(objs, 0.0)
    mn, mx = bbox(objs)
    c = (mn + mx) / 2
    pivot = bpy.data.objects.new("pivot", None)
    bpy.context.scene.collection.objects.link(pivot)
    pivot.location = (c.x, c.y, 0)
    for o in objs:
        if o.parent is None:
            o.parent = pivot
            o.matrix_parent_inverse = pivot.matrix_world.inverted()
    f = front_dir(objs)
    studio("#efede7")
    area("key", c + three_quarter(f, -1.1, 0.9) * 1.6, c, 1.2, 160)
    area("fill", c + three_quarter(f, 1.4, 0.2) * 1.8, c, 1.6, 55)
    area("top", c + Vector((0, 0, 1.6)), c, 2.0, 60)
    camera(c, three_quarter(f, 0.5, 0.18), (mx - mn).length * 2.3, lens=55)
    sc = bpy.context.scene
    sc.cycles.samples = 48 if FAST else 96
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1200
    d = os.path.join(OUT, "turntable")
    os.makedirs(d, exist_ok=True)
    for i in range(frames):
        pivot.rotation_euler = (0, 0, 2 * math.pi * i / frames)
        sc.render.filepath = os.path.join(d, "f%03d.png" % i)
        bpy.ops.render.render(write_still=True)
    print("turntable done")


RUN = {"hero": shot_hero, "outdoor": lambda: shot_hero(outdoor=True), "exploded": shot_exploded, "open": shot_open,
       "pcb_hero": shot_pcb_hero, "pcb_top": shot_pcb_top, "pcb_detail": shot_pcb_detail, "turntable": shot_turntable}
if __name__ == "__main__":
    for s in SHOTS:
        RUN[s]()
