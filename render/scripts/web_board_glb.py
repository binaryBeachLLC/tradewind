"""Re-export the KiCad board GLB with real finishes for the website's 3D viewer.
blender -b --python render/scripts/web_board_glb.py  ->  hardware/fab/3d/tradewind_revB_web.glb"""
import os
import sys
import bpy
sys.path.insert(0, os.path.dirname(__file__))
import render as R  # noqa: E402

R.reset()
objs = R.import_glb(os.path.join(R.ROOT, "hardware/fab/3d/tradewind_revB.glb"))
R.tune_board_materials(objs)
for o in objs:
    if o.hide_render:
        bpy.data.objects.remove(o, do_unlink=True)
out = os.path.join(R.ROOT, "hardware/fab/3d/tradewind_revB_web.glb")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_apply=True, export_draco_mesh_compression_enable=False)
print("wrote", out, os.path.getsize(out) // 1024, "KB")
