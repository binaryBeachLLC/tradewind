"""Quick sanity-check renders of the mechanical GLBs (Blender, Cycles, small sample count).
blender -b -P mechanical/src/preview_blender.py -- <glb> <out.png> <view> [res]
views: front34, rear34, front, side, top, close
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
glb, out, view = argv[0], argv[1], argv[2]
res = int(argv[3]) if len(argv) > 3 else 1200

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
ctr = (lo + hi) / 2
rad = (hi - lo).length / 2

# Blender is Z-up; glTF import converts Y-up -> Z-up, so the box front (+z glTF) faces -Y here.
dirs = {
    "front34": Vector((0.55, -1.0, 0.35)), "rear34": Vector((-0.6, 1.0, 0.35)), "front": Vector((0, -1, 0.02)),
    "side": Vector((1, 0, 0.02)), "top": Vector((0.0, -0.25, 1.0)), "close": Vector((0.45, -1.0, 0.25)),
}
d = dirs[view].normalized()
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 70 if view != "close" else 85
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
fov = 2 * math.atan(36 / 2 / cam_data.lens)
dist = rad / math.sin(fov / 2) * (1.02 if view != "close" else 0.8)
cam.location = ctr + d * dist
cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
cam_data.clip_end = 1000
bpy.context.scene.camera = cam

world = bpy.data.worlds.new("w"); bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.93, 0.94, 0.95, 1); bg.inputs[1].default_value = 0.8
for name, loc, energy, size in (("key", (2, -3, 4), 900, 3), ("fill", (-3, -1, 2), 300, 4), ("rim", (0, 4, 3), 500, 3)):
    L = bpy.data.lights.new(name, "AREA"); L.energy = energy * rad ** 2 * 4; L.size = size * rad
    o = bpy.data.objects.new(name, L); o.location = ctr + Vector(loc) * rad * 2
    o.rotation_euler = (ctr - o.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(o)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 48
sc.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"; prefs.get_devices()
    for dv in prefs.devices: dv.use = True
    sc.cycles.device = "GPU"
except Exception:
    pass
sc.render.resolution_x = res; sc.render.resolution_y = int(res * 0.75)
sc.render.film_transparent = False
sc.view_settings.view_transform = "AgX"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
