#!/usr/bin/env python3
"""Render eight deterministic QA views of a private Kairou V10.1 GLB.

Run with Blender in background mode.  The imported GLB is never modified or
re-exported; the floor, camera, lights and physical sky are presentation-only
objects used to judge first-person readability and material response.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resolution-x", type=int, default=960)
    parser.add_argument("--resolution-y", type=int, default=540)
    return parser.parse_args(argv)


def runtime_point(x: float, y: float, z: float) -> Vector:
    """Map Hibana X/Y-up/Z coordinates into Blender X/Y/Z-up."""
    return Vector((x, -z, y))


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def linear_hex(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    result = []
    for offset in (0, 2, 4):
        channel = int(value[offset:offset + 2], 16) / 255.0
        result.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return tuple(result)


def reset_and_import(path: Path) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        if collection.name != "Collection":
            bpy.data.collections.remove(collection)
    bpy.ops.import_scene.gltf(filepath=str(path))
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.hide_render = False


def add_ground() -> None:
    bpy.ops.mesh.primitive_plane_add(size=420.0, location=(0.0, 0.0, -0.035))
    ground = bpy.context.object
    ground.name = "QA_ONLY_KairouGround"
    material = bpy.data.materials.new("QA_ONLY_KairouGroundMaterial")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")
    noise.inputs["Scale"].default_value = 0.42
    noise.inputs["Detail"].default_value = 5.0
    noise.inputs["Roughness"].default_value = 0.68
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = (*linear_hex("#62594c"), 1.0)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (*linear_hex("#a79b84"), 1.0)
    shader.inputs["Roughness"].default_value = 0.91
    bump.inputs["Strength"].default_value = 0.28
    bump.inputs["Distance"].default_value = 0.22
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    ground.data.materials.append(material)


def add_area_light(name: str, location: Vector, target: Vector, energy: float, size: float, color: str) -> None:
    data = bpy.data.lights.new(f"{name}_DATA", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = linear_hex(color)
    light = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(light)
    light.location = location
    point_at(light, target)


def configure_presentation(resolution_x: int, resolution_y: int) -> bpy.types.Object:
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.look = "AgX - Medium High Contrast"
    # Keep the deep arch reveal readable in the technical render set.  The
    # previous presentation value left neutral stone shadows just below the
    # near-black-card detector despite zero black facade geometry in the GLB.
    # +0.09 stop is a measured 6.4% lift, not a washed-out art-lighting change.
    scene.view_settings.exposure = 1.14

    world = bpy.data.worlds.new("QA_ONLY_KairouWorld")
    world.use_nodes = True
    scene.world = world
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    background = next(node for node in nodes if node.bl_idname == "ShaderNodeBackground")
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "HOSEK_WILKIE"
    sky.sun_disc = True
    sky.sun_size = math.radians(1.2)
    sky.sun_intensity = 0.58
    sky.sun_elevation = math.radians(38.0)
    sky.sun_rotation = math.radians(132.0)
    sky.altitude = 0.30
    sky.air_density = 1.0
    sky.turbidity = 2.8
    sky.ground_albedo = 0.32
    background.inputs["Strength"].default_value = 1.12
    links.new(sky.outputs["Color"], background.inputs["Color"])

    sun_data = bpy.data.lights.new("QA_ONLY_KairouSun_DATA", "SUN")
    sun_data.energy = 2.30
    sun_data.angle = math.radians(4.5)
    sun_data.color = linear_hex("#fffaf0")
    sun = bpy.data.objects.new("QA_ONLY_KairouSun", sun_data)
    scene.collection.objects.link(sun)
    sun.location = runtime_point(125.0, 150.0, -105.0)
    point_at(sun, runtime_point(0.0, 0.0, 25.0))
    sky_sun_data = bpy.data.lights.new("QA_ONLY_KairouSkySun_DATA", "SUN")
    sky_sun_data.energy = 0.92
    sky_sun_data.angle = math.radians(7.5)
    sky_sun_data.color = linear_hex("#b9d1dc")
    sky_sun = bpy.data.objects.new("QA_ONLY_KairouSkySun", sky_sun_data)
    scene.collection.objects.link(sky_sun)
    sky_sun.location = runtime_point(-125.0, 110.0, 115.0)
    point_at(sky_sun, runtime_point(0.0, 2.0, 30.0))
    add_area_light(
        "QA_ONLY_KairouSkyFill",
        runtime_point(-90.0, 74.0, -35.0),
        runtime_point(-20.0, 8.0, 34.0),
        2320.0,
        96.0,
        "#b7d1dc",
    )
    add_area_light(
        "QA_ONLY_KairouBounce",
        runtime_point(90.0, 24.0, 90.0),
        runtime_point(16.0, 7.0, 28.0),
        920.0,
        62.0,
        "#d6cbb9",
    )
    add_area_light(
        "QA_ONLY_KairouNorthFill",
        runtime_point(0.0, 38.0, 128.0),
        runtime_point(0.0, 7.0, 28.0),
        1580.0,
        70.0,
        "#c7d7dc",
    )
    add_area_light(
        "QA_ONLY_KairouSanctuaryCourtyardFill",
        runtime_point(-66.0, 34.0, 46.0),
        runtime_point(-66.0, 0.0, 46.0),
        2100.0,
        42.0,
        "#d7d2c8",
    )
    add_area_light(
        "QA_ONLY_KairouObservatoryCourtyardFill",
        runtime_point(56.0, 38.0, 46.0),
        runtime_point(56.0, 0.0, 46.0),
        2200.0,
        38.0,
        "#c1cbd0",
    )

    camera_data = bpy.data.cameras.new("QA_ONLY_KairouCamera_DATA")
    camera = bpy.data.objects.new("QA_ONLY_KairouCamera", camera_data)
    scene.collection.objects.link(camera)
    camera_data.sensor_width = 36.0
    camera_data.lens = 34.0
    camera_data.clip_start = 0.08
    camera_data.clip_end = 1300.0
    camera_data.dof.use_dof = False
    scene.camera = camera
    return camera


VIEWS = (
    ("01-south-avenue-eye165.png", (-65.0, 1.65, -145.0), (-66.0, 25.0, 9.0), 40.0),
    ("02-sanctuary-approach-eye165.png", (-65.0, 1.65, -95.0), (-66.0, 27.0, 9.2), 42.0),
    ("03-sanctuary-threshold-eye165.png", (-115.0, 1.65, -75.0), (-66.0, 28.0, 9.2), 42.0),
    ("04-observatory-approach-eye165.png", (56.0, 1.65, -45.0), (26.08, 61.4, 20.40), 31.0),
    ("05-west-plaza-eye165.png", (-4.0, 1.65, -54.0), (38.0, 13.0, 5.0), 36.0),
    ("06-observatory-courtyard-eye165.png", (-25.0, 1.65, 105.0), (26.08, 45.0, 20.40), 43.0),
    ("07-sanctuary-courtyard-eye165.png", (-85.0, 1.65, 105.0), (-66.0, 27.0, 9.2), 43.0),
    ("08-aerial-composition.png", (146.0, 104.0, -128.0), (0.0, 15.0, 32.0), 48.0),
)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reset_and_import(args.glb.resolve())
    add_ground()
    camera = configure_presentation(args.resolution_x, args.resolution_y)
    scene = bpy.context.scene
    contract = []
    for filename, origin, target, lens in VIEWS:
        camera.location = runtime_point(*origin)
        camera.data.lens = lens
        point_at(camera, runtime_point(*target))
        scene.render.filepath = str(args.output_dir / filename)
        bpy.ops.render.render(write_still=True)
        contract.append({
            "file": filename,
            "cameraRuntimeXYZ": origin,
            "targetRuntimeXYZ": target,
            "lensMm": lens,
            "gameplayEyeHeight": origin[1] == 1.65,
        })
    (args.output_dir / "camera-contract.json").write_text(
        json.dumps({"schemaVersion": 1, "views": contract}, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
