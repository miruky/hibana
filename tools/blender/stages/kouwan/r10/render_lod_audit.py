from __future__ import annotations

"""Render deterministic player/aerial views from all three optimized GLBs."""

import json
import os
from pathlib import Path

import bpy
from mathutils import Vector


ARTIFACT_ROOT = Path(
    os.environ.get(
        "HIBANA_KOUWAN_R10_ROOT",
        Path(__file__).resolve().parents[3] / "work/kouwan-r10",
    )
).expanduser().resolve()
REPO = Path(__file__).resolve().parents[5]
PUBLIC = (REPO / "public").resolve()
WORK = (REPO / "tools/blender/work").resolve()
if ARTIFACT_ROOT == PUBLIC or PUBLIC in ARTIFACT_ROOT.parents:
    raise RuntimeError(f"private candidate must never write below public/: {ARTIFACT_ROOT}")
if REPO in ARTIFACT_ROOT.parents and ARTIFACT_ROOT != WORK and WORK not in ARTIFACT_ROOT.parents:
    raise RuntimeError(f"repository-local output must stay below ignored {WORK}: {ARTIFACT_ROOT}")
ROOT = ARTIFACT_ROOT / "optimized-r10"
OUT = ROOT / "lod-visual-audit"
OUT.mkdir(parents=True, exist_ok=True)


def rp(x: float, y: float, z: float) -> Vector:
    return Vector((x, -z, y))


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (rp(*target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def add_presentation() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.75
    scene.world.color = (0.035, 0.055, 0.075)
    world = scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.08, 0.13, 0.18, 1.0)
        background.inputs["Strength"].default_value = 0.65

    sun_data = bpy.data.lights.new("LOD_AUDIT_SUN", type="SUN")
    sun_data.energy = 3.2
    sun_data.angle = 0.18
    sun = bpy.data.objects.new("LOD_AUDIT_SUN", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (0.72, -0.48, -0.62)

    camera_data = bpy.data.cameras.new("LOD_AUDIT_CAMERA")
    camera = bpy.data.objects.new("LOD_AUDIT_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


views = (
    ("player-eye", (146.0, 1.65, 151.0), (-8.0, 18.0, -12.0), 20.0),
    ("aerial", (270.0, 120.0, 280.0), (-5.0, 22.0, -20.0), 39.0),
)
records = []
for level in range(3):
    clear_scene()
    source = ROOT / "stages" / f"kouwan-r10-lod{level}.glb"
    bpy.ops.import_scene.gltf(filepath=str(source))
    camera = add_presentation()
    for label, position, target, lens in views:
        camera.location = rp(*position)
        camera.data.lens = lens
        point_at(camera, target)
        output = OUT / f"lod{level}-{label}.png"
        bpy.context.scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        records.append({"level": level, "view": label, "path": str(output)})

(OUT / "renders.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
print(json.dumps(records, indent=2))
