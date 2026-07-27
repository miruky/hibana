"""Build Hibana's original, game-ready enemy soldier pack in Blender.

The user-supplied GLBs are observation-only.  This script neither imports nor
embeds them; all geometry, rigging, materials, textures, and motion are authored
deterministically here.  Run with Blender 5.2 LTS using an absolute script path.

Connection map (rest pose, metres; every clothing seam overlaps by >= 0.012m):
  pelvis_top Z=1.020 <-> spine_01_head Z=1.020          connected bone
  spine_01_tail Z=1.210 <-> spine_02_head Z=1.210       connected bone
  spine_02_tail Z=1.440 <-> neck_head Z=1.440           connected bone
  neck_tail Z=1.570 <-> head_head Z=1.570               connected bone
  clavicle_L_tail <-> upper_arm_L_head                  connected bone
  upper_arm_L_tail <-> forearm_L_head                   connected bone
  forearm_L_tail <-> hand_L_head                        connected bone
  clavicle_R_tail <-> upper_arm_R_head                  connected bone
  upper_arm_R_tail <-> forearm_R_head                   connected bone
  forearm_R_tail <-> hand_R_head                        connected bone
  thigh_L_tail <-> shin_L_head; shin_L_tail <-> foot_L  connected bones
  thigh_R_tail <-> shin_R_head; shin_R_tail <-> foot_R  connected bones
  right glove <-> pistol grip                            0.018m visual overlap
  left glove <-> handguard                               0.016m visual overlap
  magazine bone <-> receiver magazine well              0.020m visual overlap
  breacher groin flap top <-> carrier/cummerbund         0.020m visual overlap
  boot soles <-> ground Z=0.000                          0.006m sole sink

Attached geometry is built from verified bone endpoints, never guessed Euler
rotations.  Directional tubes derive an orthonormal basis from start/end points.
"""

from __future__ import annotations

import argparse
import bmesh
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

import bpy
from mathutils import Matrix, Vector


PROJECT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT / "public/assets/aaa/enemies"
WORK_DIR = PROJECT / "tools/blender/work/enemies"
SCREENSHOT_DIR = PROJECT / "tools/blender/screenshots/enemies"
PREFIX = "HBE_"
FPS = 30

MAT_FABRIC = 0
MAT_SKIN = 1
MAT_ARMOR = 2
MAT_GEAR = 3
MAT_RUBBER = 4
MAT_METAL = 5
MAT_LENS = 6
MAT_ACCENT = 7


VARIANTS = (
    {
        "id": "rifleman",
        "label": "Urban Rifleman",
        "palette": ("#46514E", "#66706B", "#2D3634", "#7B857D"),
        "headgear": "helmet",
        "weapon": "rifle",
        "gear": "standard",
    },
    {
        "id": "breacher",
        "label": "Armored Breacher",
        "palette": ("#293744", "#435563", "#18242C", "#64727C"),
        "headgear": "visor",
        "weapon": "breacher",
        "gear": "heavy",
    },
    {
        "id": "scout",
        "label": "Woodland Scout",
        "palette": ("#48583E", "#6F7B50", "#2C3828", "#82765A"),
        "headgear": "hood",
        "weapon": "carbine",
        "gear": "light",
    },
    {
        "id": "marksman",
        "label": "Desert Marksman",
        "palette": ("#796C53", "#9A8867", "#4D4638", "#B09A73"),
        "headgear": "boonie",
        "weapon": "marksman",
        "gear": "marksman",
    },
    {
        "id": "support",
        "label": "Heavy Support",
        "palette": ("#48563D", "#68774F", "#2D3929", "#808A68"),
        "headgear": "helmet",
        "weapon": "support",
        "gear": "support",
    },
    {
        "id": "medic",
        "label": "Combat Medic",
        "palette": ("#56635C", "#748179", "#39463F", "#8B9589"),
        "headgear": "medic",
        "weapon": "carbine",
        "gear": "medic",
    },
)


REQUIRED_ANIMATIONS = (
    "AN_Soldier_Idle",
    "AN_Soldier_RifleReady",
    "AN_Soldier_Aim",
    "AN_Soldier_Fire",
    "AN_Soldier_Reload",
    "AN_Soldier_WalkForward",
    "AN_Soldier_WalkBackward",
    "AN_Soldier_StrafeLeft",
    "AN_Soldier_StrafeRight",
    "AN_Soldier_RunForward",
    "AN_Soldier_HitFront",
    "AN_Soldier_HitBack",
    "AN_Soldier_DeathFront",
    "AN_Soldier_DeathBack",
)


BONES = (
    ("root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.12), None, False),
    ("pelvis", (0.0, 0.0, 0.88), (0.0, 0.0, 1.02), "root", False),
    ("spine_01", (0.0, 0.0, 1.02), (0.0, 0.0, 1.21), "pelvis", True),
    ("spine_02", (0.0, 0.0, 1.21), (0.0, 0.0, 1.44), "spine_01", True),
    ("neck", (0.0, 0.0, 1.44), (0.0, 0.0, 1.57), "spine_02", True),
    ("head", (0.0, 0.0, 1.57), (0.0, 0.0, 1.80), "neck", True),
    ("clavicle_l", (-0.02, 0.0, 1.40), (-0.27, 0.015, 1.40), "spine_02", False),
    ("upper_arm_l", (-0.27, 0.015, 1.40), (-0.43, 0.18, 1.26), "clavicle_l", True),
    ("forearm_l", (-0.43, 0.18, 1.26), (-0.20, 0.40, 1.22), "upper_arm_l", True),
    ("hand_l", (-0.20, 0.40, 1.22), (-0.105, 0.525, 1.225), "forearm_l", True),
    ("clavicle_r", (0.02, 0.0, 1.40), (0.27, 0.015, 1.40), "spine_02", False),
    ("upper_arm_r", (0.27, 0.015, 1.40), (0.405, 0.14, 1.29), "clavicle_r", True),
    ("forearm_r", (0.405, 0.14, 1.29), (0.18, 0.34, 1.285), "upper_arm_r", True),
    ("hand_r", (0.18, 0.34, 1.285), (0.095, 0.445, 1.27), "forearm_r", True),
    # Shoulder-width fighting stance with a subtle forward knee break.  This is
    # the common low-ready base; Aim/Fire layer the upper-body firing solution.
    ("thigh_l", (-0.155, 0.0, 0.94), (-0.155, 0.095, 0.56), "pelvis", False),
    ("shin_l", (-0.155, 0.095, 0.56), (-0.155, 0.018, 0.13), "thigh_l", True),
    ("foot_l", (-0.155, 0.018, 0.13), (-0.155, 0.225, 0.07), "shin_l", True),
    ("thigh_r", (0.155, 0.0, 0.94), (0.155, 0.095, 0.56), "pelvis", False),
    ("shin_r", (0.155, 0.095, 0.56), (0.155, 0.018, 0.13), "thigh_r", True),
    ("foot_r", (0.155, 0.018, 0.13), (0.155, 0.225, 0.07), "shin_r", True),
    # Root-space weapon control lets the authored firing solution preserve a
    # level sight axis independently of hand roll; both hands are then solved
    # onto its grip/handguard contacts.
    ("weapon", (0.095, 0.405, 1.27), (0.02, 1.02, 1.235), "root", False),
    ("magazine", (0.02, 0.52, 1.20), (0.02, 0.46, 1.06), "weapon", False),
)


BONE_POINTS = {
    name: (Vector(head), Vector(tail)) for name, head, tail, _parent, _connected in BONES
}


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-renders", action="store_true")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="GLB/manifest destination; use a private directory for visual iterations",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=WORK_DIR,
        help="Blend file and generation-report destination",
    )
    parser.add_argument(
        "--screenshot-dir",
        type=Path,
        default=SCREENSHOT_DIR,
        help="QA render destination",
    )
    return parser.parse_args(argv)


def stable_unit(seed: int, x: int, y: int, salt: int = 0) -> float:
    value = (seed ^ (x * 0x9E3779B1) ^ (y * 0x85EBCA77) ^ salt) & 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    value ^= value >> 16
    return value / 0xFFFFFFFF


def hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    channels = tuple(int(value[index : index + 2], 16) / 255.0 for index in (0, 2, 4))

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    return tuple(linear(channel) for channel in channels)


def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def remove_collection_tree(collection: bpy.types.Collection) -> None:
    for child in list(collection.children):
        remove_collection_tree(child)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)


def clear_generated() -> None:
    roots = [collection for collection in bpy.data.collections if collection.name.startswith(PREFIX)]
    for collection in list(roots):
        if bpy.data.collections.get(collection.name) is not None:
            remove_collection_tree(collection)
    for datablocks in (bpy.data.meshes, bpy.data.armatures, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.name.startswith((PREFIX, "SM_Enemy_", "ARM_Enemy_")) and datablock.users == 0:
                datablocks.remove(datablock)
    for material in list(bpy.data.materials):
        if material.name.startswith("MAT_Enemy_") and material.users == 0:
            bpy.data.materials.remove(material)
    for image in list(bpy.data.images):
        if image.name.startswith("T_Enemy_") and image.users == 0:
            bpy.data.images.remove(image)
    for action in list(bpy.data.actions):
        if action.name.startswith("AN_Soldier_"):
            bpy.data.actions.remove(action)


def new_collection(name: str, parent: bpy.types.Collection | None = None) -> bpy.types.Collection:
    collection = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(collection)
    return collection


def create_fabric_atlases() -> tuple[bpy.types.Image, bpy.types.Image, bpy.types.Image]:
    # Six role cells share one 1024x512 POT atlas.  The former 128px cells made
    # camouflage islands visibly pixelated in close killcams; 256px cells keep
    # the same material/draw count while resolving cloth and dirt at gameplay
    # distance.
    cell = 256
    # 4x2 power-of-two atlas; the two final cells are deterministic padding.
    width = cell * 4
    height = cell * 2
    base = bpy.data.images.new("T_Enemy_FabricAtlas_BC", width=width, height=height, alpha=False)
    rough = bpy.data.images.new("T_Enemy_FabricAtlas_R", width=width, height=height, alpha=False)
    normal = bpy.data.images.new("T_Enemy_FabricAtlas_N", width=width, height=height, alpha=False)
    rough.colorspace_settings.name = "Non-Color"
    normal.colorspace_settings.name = "Non-Color"
    base_pixels: list[float] = []
    rough_pixels: list[float] = []
    normal_pixels: list[float] = []
    for y in range(height):
        for x in range(width):
            atlas_cell_x = x // cell
            cell_x = min(2, atlas_cell_x)
            cell_y = min(1, y // cell)
            variant_index = cell_y * 3 + cell_x
            palette = [hex_rgb(color) for color in VARIANTS[variant_index]["palette"]]
            lx = x % cell
            ly = y % cell
            # The fourth atlas column was padding.  Use it for one original,
            # tiny balaclava-eye texture so human gaze survives close killcams
            # without another texture, material, or geometry-eye draw group.
            if atlas_cell_x == 3 and cell_y == 0:
                u = lx / (cell - 1)
                v = ly / (cell - 1)
                seed = stable_unit(211, lx // 3, ly // 3, 0xB17) - 0.5
                # Keep the exposed orbital skin inside the same value range as
                # the supplied modern-operator reference.  The previous brown
                # was so dark that only a thin orange line survived under the
                # helmet, destroying the last human cue at gameplay distance.
                skin = hex_rgb("#74584B")
                shade = 0.91 + 0.07 * (1.0 - abs(u - 0.5) * 1.35) + seed * 0.014
                color = tuple(channel * shade for channel in skin)
                # Paint restrained eyes into the shared atlas and project them
                # onto a curved, partially embedded orbital patch.  The same
                # marks on a flat panel looked pixel-art; curvature, a dark
                # upper lid and low-contrast sclera preserve a human gaze
                # without extra eye geometry or draw calls.
                for eye_center in (0.330, 0.670):
                    dx = (u - eye_center) / 0.17
                    dy = (v - 0.52) / 0.16
                    eye_d = dx * dx + dy * dy
                    if eye_d <= 1.0:
                        # The orbit is mostly shadow beneath the helmet brow.
                        # A dark socket around a narrow palpebral opening reads
                        # as a masked adult face; a bright oval reads as a toy.
                        socket = 0.72 + 0.13 * eye_d
                        color = tuple(channel * socket for channel in color)
                    eye_dx = (u - eye_center) / 0.100
                    eye_dy = (v - 0.515) / 0.025
                    painted_eye = eye_dx * eye_dx + eye_dy * eye_dy
                    if painted_eye <= 1.0:
                        # Sclera is deliberately low-value and warm.  Human
                        # eyes in a balaclava never present as two white discs
                        # under the reference's diffuse tactical lighting.
                        sclera = hex_rgb("#5F554D")
                        edge_mix = min(0.88, max(0.0, (1.0 - painted_eye) * 1.45))
                        color = tuple(
                            channel * (1.0 - edge_mix) + sclera[index] * edge_mix
                            for index, channel in enumerate(color)
                        )
                    iris_dx = (u - eye_center) / 0.023
                    iris_dy = (v - 0.515) / 0.025
                    if iris_dx * iris_dx + iris_dy * iris_dy <= 1.0:
                        color = hex_rgb("#3D392C")
                    pupil_dx = (u - eye_center) / 0.010
                    pupil_dy = (v - 0.515) / 0.017
                    if pupil_dx * pupil_dx + pupil_dy * pupil_dy <= 1.0:
                        color = hex_rgb("#141312")
                    # Lid lines slightly occlude the iris and are asymmetric
                    # toward the nose, matching the narrow alert gaze in the
                    # supplied modern-operator reference.
                    lid_curve = 0.552 - ((u - eye_center) / 0.125) ** 2 * 0.020
                    if abs(u - eye_center) < 0.112 and abs(v - lid_curve) < 0.009:
                        color = hex_rgb("#2A211D")
                    lower_curve = 0.477 + ((u - eye_center) / 0.120) ** 2 * 0.012
                    if abs(u - eye_center) < 0.108 and abs(v - lower_curve) < 0.005:
                        color = hex_rgb("#4A352D")
                    brow_v = 0.625 + (0.5 - eye_center) * (u - eye_center) * 0.18
                    if abs(u - eye_center) < 0.145 and abs(v - brow_v) < 0.014:
                        color = hex_rgb("#261D19")
                if 0.30 < v < 0.62:
                    # Soft tapered nose-bridge occlusion; the former constant
                    # width rectangle looked like a pasted plastic nose piece.
                    bridge_half_width = 0.014 + (0.62 - v) * 0.070
                    bridge_distance = abs(u - 0.5)
                    if bridge_distance < bridge_half_width:
                        bridge_mix = 1.0 - bridge_distance / bridge_half_width
                        color = tuple(channel * (0.87 - bridge_mix * 0.08) for channel in color)
                edge = min(u, 1.0 - u)
                if edge < 0.055:
                    color = tuple(channel * (0.62 + edge * 5.0) for channel in color)
                base_pixels.extend((*color, 1.0))
                face_roughness = 0.56 + seed * 0.025
                rough_pixels.extend((face_roughness, face_roughness, face_roughness, 1.0))
                normal_pixels.extend((0.5, 0.5, 1.0, 1.0))
                continue
            if atlas_cell_x == 3 and cell_y == 1:
                # Split the last cell into ballistic shell (left) and webbing /
                # pouch fabric (right).  Both share the existing three images,
                # adding centimetre-scale wear without extra residency.
                local_half_x = lx if lx < cell // 2 else lx - cell // 2
                material_seed = 307 if lx < cell // 2 else 401
                base_hex = "#303B38" if lx < cell // 2 else "#3D4439"
                base_color = hex_rgb(base_hex)
                coarse = stable_unit(material_seed, local_half_x // 13, ly // 17, 0xC31) - 0.5
                fine = stable_unit(material_seed, local_half_x // 3, ly // 3, 0xE17) - 0.5
                weave = math.sin(math.tau * local_half_x / 7.0) * math.sin(math.tau * ly / 9.0)
                scuff = 1.0 if stable_unit(material_seed, local_half_x // 19, ly // 5, 0x713) > 0.93 else 0.0
                value = 0.92 + coarse * 0.10 + fine * 0.035 + weave * (0.012 if lx < cell // 2 else 0.028)
                value += scuff * (0.045 if lx < cell // 2 else 0.022)
                color = tuple(channel * value for channel in base_color)
                base_pixels.extend((*color, 1.0))
                roughness = (0.59 if lx < cell // 2 else 0.76) + coarse * 0.07 - scuff * 0.05
                roughness = min(0.90, max(0.46, roughness))
                rough_pixels.extend((roughness, roughness, roughness, 1.0))
                normal_strength = 0.012 if lx < cell // 2 else 0.025
                nx = 0.5 + math.sin(math.tau * local_half_x / 7.0) * normal_strength
                ny = 0.5 + math.sin(math.tau * ly / 9.0) * normal_strength
                normal_pixels.extend((nx, ny, 0.998, 1.0))
                continue
            # Broad organic 8–20cm camouflage islands plus fine woven response.
            # Earlier nearest-cell hashing exposed axis-aligned 22px squares on
            # the thighs and sleeves, making the soldier read as voxel art.
            # Warped analytic fields retain deterministic hard-edged cloth
            # printing while producing interlocking, non-rectangular islands.
            phase = variant_index * 0.83
            warp_x = math.sin(ly * 0.031 + phase) * 17.0 + math.sin(ly * 0.083 - phase) * 5.0
            warp_y = math.cos(lx * 0.028 - phase) * 15.0 + math.sin(lx * 0.071 + phase) * 4.0
            field = (
                math.sin((lx + warp_x) * (0.046 + variant_index * 0.0015) + phase)
                + math.cos((ly + warp_y) * (0.052 - variant_index * 0.0012) - phase * 0.7)
                + math.sin((lx + ly + warp_x * 0.4) * 0.029 + phase * 1.8) * 0.72
                + math.cos((lx - ly + warp_y * 0.5) * 0.081 - phase) * 0.28
            )
            # Unequal thresholds keep the darkest anchor colour sparse and the
            # mid-tones dominant, matching printed combat fabric rather than a
            # four-colour checkerboard.
            if field < -1.05:
                palette_index = 2
            elif field < -0.18:
                palette_index = 0
            elif field < 0.82:
                palette_index = 1
            else:
                palette_index = 3
            color = palette[palette_index]
            weave = math.sin(math.tau * lx / 6.0) * math.sin(math.tau * ly / 6.0)
            dirt = stable_unit(variant_index + 71, lx // 5, ly // 5, 0xA53) - 0.5
            abrasion = abs(math.sin((lx * 0.37 + ly * 0.19 + phase) * 0.11))
            value = 0.93 + weave * 0.016 + dirt * 0.040 + abrasion * 0.014
            base_pixels.extend((color[0] * value, color[1] * value, color[2] * value, 1.0))
            roughness = min(0.92, max(0.62, 0.78 + dirt * 0.10 + abs(weave) * 0.04))
            rough_pixels.extend((roughness, roughness, roughness, 1.0))
            nx = 0.5 + math.sin(math.tau * lx / 6.0) * 0.025
            ny = 0.5 + math.sin(math.tau * ly / 6.0) * 0.025
            normal_pixels.extend((nx, ny, 0.995, 1.0))
    base.pixels.foreach_set(base_pixels)
    rough.pixels.foreach_set(rough_pixels)
    normal.pixels.foreach_set(normal_pixels)
    for image in (base, rough, normal):
        image.pack()
    return base, rough, normal


def principled_node(material: bpy.types.Material) -> bpy.types.Node | None:
    return next(
        (node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"),
        None,
    )


def make_material(
    name: str,
    color: tuple[float, float, float],
    roughness: float,
    metallic: float = 0.0,
    alpha: float = 1.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (*color, alpha)
    bsdf = principled_node(material)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, alpha)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        try:
            material.surface_render_method = "DITHERED"
        except AttributeError:
            material.blend_method = "BLEND"
        if hasattr(material, "use_transparency_overlap"):
            material.use_transparency_overlap = False
    return material


def create_materials() -> list[bpy.types.Material]:
    base, rough, normal = create_fabric_atlases()
    fabric = make_material("MAT_Enemy_FabricAtlas", (1.0, 1.0, 1.0), 0.76)
    bsdf = principled_node(fabric)
    if bsdf is not None:
        tex_base = fabric.node_tree.nodes.new("ShaderNodeTexImage")
        tex_base.image = base
        tex_base.name = "T_Enemy_FabricAtlas_BC"
        fabric.node_tree.links.new(tex_base.outputs["Color"], bsdf.inputs["Base Color"])
        tex_rough = fabric.node_tree.nodes.new("ShaderNodeTexImage")
        tex_rough.image = rough
        tex_rough.image.colorspace_settings.name = "Non-Color"
        fabric.node_tree.links.new(tex_rough.outputs["Color"], bsdf.inputs["Roughness"])
        tex_normal = fabric.node_tree.nodes.new("ShaderNodeTexImage")
        tex_normal.image = normal
        tex_normal.image.colorspace_settings.name = "Non-Color"
        normal_map = fabric.node_tree.nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = 0.34
        fabric.node_tree.links.new(tex_normal.outputs["Color"], normal_map.inputs["Color"])
        fabric.node_tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    skin = make_material("MAT_Enemy_Skin", (1.0, 1.0, 1.0), 0.58)
    skin_bsdf = principled_node(skin)
    if skin_bsdf is not None:
        skin_tex = skin.node_tree.nodes.new("ShaderNodeTexImage")
        skin_tex.image = base
        skin_tex.name = "T_Enemy_FaceAtlas_BC_Shared"
        skin.node_tree.links.new(skin_tex.outputs["Color"], skin_bsdf.inputs["Base Color"])

    def atlas_surface(name: str, metallic: float, normal_strength: float) -> bpy.types.Material:
        material = make_material(name, (1.0, 1.0, 1.0), 0.68, metallic)
        node = principled_node(material)
        if node is not None:
            base_tex = material.node_tree.nodes.new("ShaderNodeTexImage")
            base_tex.image = base
            base_tex.name = f"{name}_BC_Shared"
            material.node_tree.links.new(base_tex.outputs["Color"], node.inputs["Base Color"])
            rough_tex = material.node_tree.nodes.new("ShaderNodeTexImage")
            rough_tex.image = rough
            rough_tex.image.colorspace_settings.name = "Non-Color"
            rough_tex.name = f"{name}_R_Shared"
            material.node_tree.links.new(rough_tex.outputs["Color"], node.inputs["Roughness"])
            normal_tex = material.node_tree.nodes.new("ShaderNodeTexImage")
            normal_tex.image = normal
            normal_tex.image.colorspace_settings.name = "Non-Color"
            normal_tex.name = f"{name}_N_Shared"
            normal_map = material.node_tree.nodes.new("ShaderNodeNormalMap")
            normal_map.inputs["Strength"].default_value = normal_strength
            material.node_tree.links.new(normal_tex.outputs["Color"], normal_map.inputs["Color"])
            material.node_tree.links.new(normal_map.outputs["Normal"], node.inputs["Normal"])
        return material

    armor = atlas_surface("MAT_Enemy_Armor", 0.05, 0.32)
    gear = atlas_surface("MAT_Enemy_Gear", 0.01, 0.44)
    return [
        fabric,
        # A restrained brown skin value is visible only inside the balaclava
        # aperture.  Earlier near-black skin removed the last human cue and
        # turned every role into a visor-faced robot under game lighting.
        skin,
        armor,
        gear,
        make_material("MAT_Enemy_Rubber", hex_rgb("#171B19"), 0.80),
        make_material("MAT_Enemy_Metal", hex_rgb("#1B2427"), 0.31, 0.68),
        # Smoked ballistic polycarbonate: dark enough to conceal the simplified
        # orbital texture, but not a featureless black void under overcast map
        # lighting.  A restrained specular response gives the lens one broad
        # highlight instead of two glowing robot eyes.
        make_material("MAT_Enemy_Lens", hex_rgb("#0B1517"), 0.38, 0.02),
        make_material("MAT_Enemy_Accent", hex_rgb("#A52D2D"), 0.62),
    ]


def basis_between(start: Vector, end: Vector) -> tuple[Vector, Vector, Vector]:
    forward = (end - start).normalized()
    helper = Vector((0.0, 0.0, 1.0)) if abs(forward.z) < 0.94 else Vector((1.0, 0.0, 0.0))
    right = forward.cross(helper).normalized()
    up = right.cross(forward).normalized()
    return right, up, forward


class MeshBuilder:
    def __init__(self, variant_index: int, lod: int) -> None:
        self.variant_index = variant_index
        self.lod = lod
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[list[int], int, bool]] = []
        self.vertex_weights: list[dict[str, float]] = []

    def add_raw(
        self,
        vertices: Iterable[Vector],
        faces: Iterable[Iterable[int]],
        material: int,
        bone: str,
        smooth: bool = False,
        vertex_weights: Iterable[dict[str, float]] | None = None,
    ) -> None:
        offset = len(self.vertices)
        vertices = list(vertices)
        self.vertices.extend(tuple(vertex) for vertex in vertices)
        if vertex_weights is None:
            self.vertex_weights.extend([{bone: 1.0} for _vertex in vertices])
        else:
            weights = [dict(weight) for weight in vertex_weights]
            if len(weights) != len(vertices):
                raise ValueError("vertex weight count must match vertex count")
            for weight in weights:
                if not weight or len(weight) > 4 or sum(weight.values()) <= 0.0:
                    raise ValueError("each vertex requires one to four positive bone weights")
            self.vertex_weights.extend(weights)
        self.faces.extend(([offset + index for index in face], material, smooth) for face in faces)

    def add_tube(
        self,
        start: Vector,
        end: Vector,
        radius_start: float,
        radius_end: float,
        material: int,
        bone: str,
        segments: int | None = None,
        ellipse: tuple[float, float] = (1.0, 1.0),
    ) -> None:
        segments = segments or {0: 18, 1: 8, 2: 6}[self.lod]
        right, up, _forward = basis_between(start, end)
        vertices: list[Vector] = []
        for center, radius in ((start, radius_start), (end, radius_end)):
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append(
                    center
                    + right * math.cos(angle) * radius * ellipse[0]
                    + up * math.sin(angle) * radius * ellipse[1]
                )
        vertices.extend((start, end))
        faces: list[list[int]] = []
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append([index, nxt, segments + nxt, segments + index])
            faces.append([2 * segments, nxt, index])
            faces.append([2 * segments + 1, segments + index, segments + nxt])
        self.add_raw(vertices, faces, material, bone, smooth=True)

    def add_loft(
        self,
        rings: Iterable[tuple[Vector, float, float]],
        material: int,
        bone: str,
        segments: int | None = None,
        smooth: bool = True,
    ) -> None:
        """Create one watertight, tapered organic form from elliptical rings.

        A single continuous loft avoids the stacked-cylinder silhouette that made
        the first soldier pass read as a toy.  The ring radii are expressed in
        the stable right/up basis of the complete form, so slightly curved feet,
        gloves, limbs, packs, and torso panels remain deterministic.
        """
        rings = list(rings)
        if len(rings) < 2:
            raise ValueError("add_loft requires at least two rings")
        segments = segments or {0: 18, 1: 8, 2: 6}[self.lod]
        right, up, _forward = basis_between(rings[0][0], rings[-1][0])
        vertices: list[Vector] = []
        for center, radius_right, radius_up in rings:
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append(
                    center
                    + right * math.cos(angle) * radius_right
                    + up * math.sin(angle) * radius_up
                )
        start_cap = len(vertices)
        vertices.append(rings[0][0])
        end_cap = len(vertices)
        vertices.append(rings[-1][0])
        faces: list[list[int]] = []
        for ring_index in range(len(rings) - 1):
            a = ring_index * segments
            b = (ring_index + 1) * segments
            for index in range(segments):
                nxt = (index + 1) % segments
                faces.append([a + index, a + nxt, b + nxt, b + index])
        last = (len(rings) - 1) * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append([start_cap, nxt, index])
            faces.append([end_cap, last + index, last + nxt])
        self.add_raw(vertices, faces, material, bone, smooth=smooth)

    def add_blended_loft(
        self,
        rings: Iterable[tuple[Vector, float, float]],
        material: int,
        ring_weights: Iterable[dict[str, float]],
        segments: int | None = None,
        smooth: bool = True,
    ) -> None:
        """Create a watertight loft whose rings blend across a joint.

        Rigid, capped limb pieces can reveal saw-tooth seams when adjacent bones
        rotate.  A short overlapping sleeve with two-bone gradients preserves a
        continuous first-person silhouette while keeping four-influence glTF
        compatibility and the shared 22-joint skeleton.
        """
        rings = list(rings)
        weights = list(ring_weights)
        if len(rings) < 2 or len(weights) != len(rings):
            raise ValueError("blended loft requires one weight map per ring")
        segments = segments or {0: 18, 1: 8, 2: 6}[self.lod]
        right, up, _forward = basis_between(rings[0][0], rings[-1][0])
        vertices: list[Vector] = []
        vertex_weights: list[dict[str, float]] = []
        for (center, radius_right, radius_up), weight in zip(rings, weights):
            total = sum(weight.values())
            normalized = {bone: value / total for bone, value in weight.items() if value > 0.0}
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append(
                    center
                    + right * math.cos(angle) * radius_right
                    + up * math.sin(angle) * radius_up
                )
                vertex_weights.append(normalized)
        start_cap = len(vertices)
        vertices.append(rings[0][0])
        vertex_weights.append(weights[0])
        end_cap = len(vertices)
        vertices.append(rings[-1][0])
        vertex_weights.append(weights[-1])
        faces: list[list[int]] = []
        for ring_index in range(len(rings) - 1):
            a = ring_index * segments
            b = (ring_index + 1) * segments
            for index in range(segments):
                nxt = (index + 1) % segments
                faces.append([a + index, a + nxt, b + nxt, b + index])
        last = (len(rings) - 1) * segments
        for index in range(segments):
            nxt = (index + 1) % segments
            faces.append([start_cap, nxt, index])
            faces.append([end_cap, last + index, last + nxt])
        self.add_raw(
            vertices,
            faces,
            material,
            next(iter(weights[0])),
            smooth=smooth,
            vertex_weights=vertex_weights,
        )

    def add_sphere(
        self,
        center: Vector,
        radii: tuple[float, float, float],
        material: int,
        bone: str,
        segments: int | None = None,
        rings: int | None = None,
    ) -> None:
        # Silhouette spheres stay smooth at close range while avoiding UV-pole
        # density that is invisible after normal mapping and WebGL projection.
        segments = segments or {0: 20, 1: 8, 2: 6}[self.lod]
        rings = rings or {0: 12, 1: 5, 2: 4}[self.lod]
        vertices = [center + Vector((0.0, 0.0, radii[2]))]
        for ring in range(1, rings):
            phi = math.pi * ring / rings
            for segment in range(segments):
                theta = math.tau * segment / segments
                vertices.append(
                    center
                    + Vector(
                        (
                            math.sin(phi) * math.cos(theta) * radii[0],
                            math.sin(phi) * math.sin(theta) * radii[1],
                            math.cos(phi) * radii[2],
                        )
                    )
                )
        bottom = len(vertices)
        vertices.append(center - Vector((0.0, 0.0, radii[2])))
        faces: list[list[int]] = []
        first = 1
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append([0, first + segment, first + nxt])
        for ring in range(rings - 2):
            a = 1 + ring * segments
            b = a + segments
            for segment in range(segments):
                nxt = (segment + 1) % segments
                faces.append([a + segment, b + segment, b + nxt, a + nxt])
        last = 1 + (rings - 2) * segments
        for segment in range(segments):
            nxt = (segment + 1) % segments
            faces.append([bottom, last + nxt, last + segment])
        self.add_raw(vertices, faces, material, bone, smooth=True)

    def add_box(
        self,
        center: Vector,
        size: tuple[float, float, float],
        material: int,
        bone: str,
        bevel: float = 0.012,
        axes: tuple[Vector, Vector, Vector] | None = None,
    ) -> None:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        half = Vector(size) * 0.5
        for vertex in bm.verts:
            local = Vector((vertex.co.x * half.x, vertex.co.y * half.y, vertex.co.z * half.z))
            if axes is None:
                vertex.co = center + local
            else:
                vertex.co = center + axes[0] * local.x + axes[1] * local.y + axes[2] * local.z
        if bevel > 0.0 and self.lod < 2:
            try:
                bmesh.ops.bevel(
                    bm,
                    geom=list(bm.edges),
                    offset=min(bevel, min(size) * 0.20),
                    segments=2 if self.lod == 0 else 1,
                    affect="EDGES",
                    clamp_overlap=True,
                )
            except (TypeError, ValueError):
                pass
        bm.normal_update()
        verts = list(bm.verts)
        index_by_vert = {vertex: index for index, vertex in enumerate(verts)}
        vertices = [vertex.co.copy() for vertex in verts]
        faces = [[index_by_vert[vertex] for vertex in face.verts] for face in bm.faces]
        self.add_raw(vertices, faces, material, bone, smooth=False)
        bm.free()

    def add_panel_y(
        self,
        outline_xz: Iterable[tuple[float, float]],
        y_min: float,
        y_max: float,
        material: int,
        bone: str,
        smooth: bool = False,
    ) -> None:
        """Extrude one convex X/Z outline through Y as a closed plate.

        Tactical plates, patches and armor flaps need clipped corners and a
        thin edge profile.  Rounded lofts made them read like padded capsules,
        while cuboids erased the real plate silhouette.  This explicit prism
        keeps both faces parallel, triangulates the caps for glTF tangents, and
        gives every edge a physical contact surface without Euler rotations.
        """
        outline = list(outline_xz)
        if len(outline) < 3 or y_max <= y_min:
            raise ValueError("add_panel_y requires a convex outline and positive thickness")
        vertices = [Vector((x, y, z)) for y in (y_min, y_max) for x, z in outline]
        count = len(outline)
        faces: list[list[int]] = []
        for index in range(1, count - 1):
            faces.append([0, index + 1, index])
            faces.append([count, count + index, count + index + 1])
        for index in range(count):
            nxt = (index + 1) % count
            faces.append([index, nxt, count + nxt, count + index])
        self.add_raw(vertices, faces, material, bone, smooth=smooth)

    def add_clipped_loft(
        self,
        rings: Iterable[tuple[Vector, float, float]],
        material: int,
        bone: str,
    ) -> None:
        """Build a watertight hard-surface loft with clipped corners.

        A curved magazine needs a changing centreline but must not become the
        inflated capsule produced by an elliptical loft.  All rings share one
        measured basis and one rigid bone, preventing exploded transforms.
        """
        rings = list(rings)
        if len(rings) < 2:
            raise ValueError("add_clipped_loft requires at least two rings")
        right, up, _forward = basis_between(rings[0][0], rings[-1][0])
        profile = (
            (-0.72, -1.00),
            (0.72, -1.00),
            (1.00, -0.70),
            (1.00, 0.70),
            (0.72, 1.00),
            (-0.72, 1.00),
            (-1.00, 0.70),
            (-1.00, -0.70),
        )
        vertices: list[Vector] = []
        for center, half_right, half_up in rings:
            vertices.extend(
                center + right * px * half_right + up * py * half_up
                for px, py in profile
            )
        count = len(profile)
        faces: list[list[int]] = []
        for ring_index in range(len(rings) - 1):
            a = ring_index * count
            b = (ring_index + 1) * count
            for index in range(count):
                nxt = (index + 1) % count
                faces.append([a + index, a + nxt, b + nxt, b + index])
        last = (len(rings) - 1) * count
        for index in range(1, count - 1):
            faces.append([0, index + 1, index])
            faces.append([last, last + index, last + index + 1])
        self.add_raw(vertices, faces, material, bone, smooth=False)

    def finish(
        self,
        name: str,
        collection: bpy.types.Collection,
        armature: bpy.types.Object,
        materials: list[bpy.types.Material],
        variant: dict[str, Any],
    ) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], [face[0] for face in self.faces])
        mesh.validate(verbose=False)
        mesh.update(calc_edges=True)
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        for material in materials:
            mesh.materials.append(material)
        for polygon, (_face, material, smooth) in zip(mesh.polygons, self.faces):
            polygon.material_index = material
            polygon.use_smooth = smooth
        uv_layer = mesh.uv_layers.new(name="UVMap")
        cell_x = self.variant_index % 3
        cell_y = self.variant_index // 3
        for polygon in mesh.polygons:
            for loop_index in polygon.loop_indices:
                loop = mesh.loops[loop_index]
                vertex = Vector(mesh.vertices[loop.vertex_index].co)
                if polygon.material_index == MAT_FABRIC:
                    local_u = (vertex.x * 1.83 + vertex.y * 0.47 + 0.37) % 1.0
                    local_v = (vertex.z * 1.57 + vertex.y * 0.31 + 0.19) % 1.0
                    uv_layer.data[loop_index].uv = (
                        (cell_x + 0.03 + local_u * 0.94) / 4.0,
                        (cell_y + 0.03 + local_v * 0.94) / 2.0,
                    )
                elif polygon.material_index == MAT_SKIN:
                    # Project the small front aperture into the unused fourth
                    # column of the same shared atlas.  Clamp avoids sampling
                    # adjacent camouflage cells at the ellipse rim.
                    local_u = min(1.0, max(0.0, (vertex.x + 0.080) / 0.160))
                    local_v = min(1.0, max(0.0, (vertex.z - 1.640) / 0.100))
                    uv_layer.data[loop_index].uv = (
                        (3.0 + 0.035 + local_u * 0.930) / 4.0,
                        (0.035 + local_v * 0.930) / 2.0,
                    )
                elif polygon.material_index in {MAT_ARMOR, MAT_GEAR}:
                    local_u = (vertex.x * 2.73 + vertex.y * 1.17 + 0.41) % 1.0
                    local_v = (vertex.z * 2.11 + vertex.y * 0.73 + 0.23) % 1.0
                    half_offset = 0.035 if polygon.material_index == MAT_ARMOR else 0.525
                    uv_layer.data[loop_index].uv = (
                        (3.0 + half_offset + local_u * 0.440) / 4.0,
                        (1.035 + local_v * 0.930) / 2.0,
                    )
                else:
                    uv_layer.data[loop_index].uv = (0.5, 0.5)
        mesh.calc_tangents(uvmap="UVMap")
        by_bone: dict[str, list[tuple[int, float]]] = {}
        for index, weights in enumerate(self.vertex_weights):
            total = sum(weights.values())
            for bone, weight in weights.items():
                if weight > 0.0:
                    by_bone.setdefault(bone, []).append((index, weight / total))
        for bone, weighted_indices in by_bone.items():
            group = obj.vertex_groups.new(name=bone)
            # Blender's group API accepts one weight per call, so group equal
            # values to keep deterministic generation reasonably fast.
            buckets: dict[float, list[int]] = {}
            for index, weight in weighted_indices:
                buckets.setdefault(round(weight, 6), []).append(index)
            for weight, indices in buckets.items():
                group.add(indices, weight, "REPLACE")
        modifier = obj.modifiers.new(name="ARM_Enemy_Deform", type="ARMATURE")
        modifier.object = armature
        # Keep every skinned mesh at the scene root and let the explicit,
        # uniquely named Armature modifier identify its skeleton. glTF 2.0
        # ignores parent transforms on skinned mesh nodes, so parenting these
        # objects to the armature produced one Khronos
        # NODE_SKINNED_MESH_NON_ROOT warning per role even though all matrices
        # were identity. Root placement is the portable hierarchy.
        obj.parent = None
        obj["variantId"] = variant["id"]
        obj["variantLabel"] = variant["label"]
        obj["lod"] = self.lod
        obj["sharedSkeleton"] = "ARM_Enemy_Shared"
        obj["sourcePolicy"] = "original-procedural-no-reference-geometry"
        return obj


def create_armature(collection: bpy.types.Collection) -> bpy.types.Object:
    data = bpy.data.armatures.new("ARM_Enemy_Shared")
    armature = bpy.data.objects.new("ARM_Enemy_Shared", data)
    collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    created: dict[str, bpy.types.EditBone] = {}
    for name, head, tail, parent, connected in BONES:
        bone = data.edit_bones.new(name)
        bone.head = head
        bone.tail = tail
        bone.roll = 0.0
        bone.use_deform = True
        if parent:
            bone.parent = created[parent]
            bone.use_connect = connected
        created[name] = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    armature["hibanaEnemyPackVersion"] = 1
    armature["sharedSkeleton"] = True
    armature["forwardAxisGltf"] = "-Z"
    armature["heightMeters"] = 1.80
    return armature


def add_body(builder: MeshBuilder, variant: dict[str, Any], detail: int) -> None:
    segment = {0: 18, 1: 8, 2: 6}[builder.lod]
    bulk = {
        "light": 0.93,
        "standard": 1.00,
        "marksman": 0.98,
        "heavy": 1.07,
        "support": 1.10,
        "medic": 1.01,
    }[variant["gear"]]

    # Anatomical torso lofts: pelvis flare -> narrow waist -> ribcage -> sloped
    # shoulder line.  Overlapping end rings hide skinning seams while preserving
    # the shared three-bone spine used by all fourteen animation clips.
    head_segments = {0: 32, 1: 16, 2: 8}[builder.lod]
    builder.add_loft(
        (
            (Vector((0, 0.000, 0.875)), 0.128 * bulk, 0.190 * bulk),
            (Vector((0, 0.000, 0.925)), 0.145 * bulk, 0.218 * bulk),
            (Vector((0, 0.000, 1.035)), 0.126 * bulk, 0.184 * bulk),
        ),
        MAT_FABRIC,
        "pelvis",
        segment,
    )
    builder.add_loft(
        (
            (Vector((0, 0.000, 1.005)), 0.126 * bulk, 0.181 * bulk),
            (Vector((0, 0.004, 1.095)), 0.132 * bulk, 0.177 * bulk),
            (Vector((0, 0.008, 1.175)), 0.147 * bulk, 0.211 * bulk),
            (Vector((0, 0.010, 1.235)), 0.153 * bulk, 0.242 * bulk),
        ),
        MAT_FABRIC,
        "spine_01",
        segment,
    )
    builder.add_loft(
        (
            (Vector((0, 0.010, 1.195)), 0.151 * bulk, 0.235 * bulk),
            (Vector((0, 0.008, 1.300)), 0.170 * bulk, 0.278 * bulk),
            (Vector((0, 0.002, 1.395)), 0.164 * bulk, 0.294 * bulk),
            (Vector((0, 0.000, 1.445)), 0.139 * bulk, 0.246 * bulk),
        ),
        MAT_FABRIC,
        "spine_02",
        segment,
    )
    builder.add_loft(
        (
            (Vector((0, 0, 1.425)), 0.061, 0.067),
            (Vector((0, 0, 1.505)), 0.057, 0.061),
            (Vector((0, 0, 1.590)), 0.064, 0.069),
        ),
        # A black technical gaiter continues the balaclava below the jaw. A
        # camouflage/atlas neck read as a long exposed fabric tube in profile.
        MAT_RUBBER,
        "neck",
        head_segments,
    )
    # Sloped trapezius/yoke volumes close the visual valley between the collar
    # and deltoids.  This keeps the gaiter from reading as a long isolated tube.
    for side, sign in (("l", -1.0), ("r", 1.0)):
        builder.add_blended_loft(
            (
                (Vector((sign * 0.052, -0.002, 1.462)), 0.052, 0.058),
                (Vector((sign * 0.135, 0.000, 1.445)), 0.064, 0.069),
                (Vector((sign * 0.205, 0.008, 1.423)), 0.078, 0.082),
                (Vector((sign * 0.258, 0.014, 1.402)), 0.087, 0.092),
            ),
            MAT_FABRIC,
            (
                {"spine_02": 1.0},
                {"spine_02": 0.78, f"clavicle_{side}": 0.22},
                {"spine_02": 0.36, f"clavicle_{side}": 0.64},
                {f"clavicle_{side}": 1.0},
            ),
            max(8, segment),
        )

    # A shallow front collar bib bridges the carrier and jaw.  It breaks the
    # long cylindrical neck silhouette without restricting head animation and
    # remains fabric-weighted across the upper-spine/neck/head chain.
    builder.add_blended_loft(
        (
            (Vector((0, 0.112, 1.405)), 0.034, 0.172),
            (Vector((0, 0.108, 1.462)), 0.038, 0.154),
            (Vector((0, 0.097, 1.520)), 0.043, 0.126),
            (Vector((0, 0.072, 1.580)), 0.047, 0.105),
        ),
        MAT_FABRIC,
        (
            {"spine_02": 1.0},
            {"spine_02": 0.60, "neck": 0.40},
            {"neck": 1.0},
            {"neck": 0.55, "head": 0.45},
        ),
        max(8, segment),
    )

    # One continuous human head under a fitted balaclava.  Earlier candidates
    # stacked this loft with a full ellipsoid; the doubled volume created a
    # spherical toy head and an overlong cylindrical neck.  The five rings
    # below establish jaw, cheek, temple and crown in a single watertight form.
    builder.add_loft(
        (
            (Vector((0, 0.000, 1.555)), 0.058, 0.064),
            (Vector((0, 0.010, 1.600)), 0.073, 0.078),
            (Vector((0, 0.019, 1.650)), 0.086, 0.091),
            (Vector((0, 0.010, 1.704)), 0.084, 0.089),
            (Vector((0, -0.002, 1.752)), 0.064, 0.071),
            (Vector((0, -0.006, 1.772)), 0.036, 0.042),
        ),
        MAT_RUBBER,
        "head",
        head_segments,
    )

    # A restrained balaclava muzzle gives the lower face only the depth a
    # covered nose/chin needs.  The former 99 mm projection read as a beak in
    # the front and hero cameras.
    builder.add_panel_y(
        (
            (-0.044, 1.580),
            (0.044, 1.580),
            (0.062, 1.602),
            (0.060, 1.630),
            (0.045, 1.651),
            (-0.045, 1.651),
            (-0.060, 1.630),
            (-0.062, 1.602),
        ),
        0.046,
        0.074,
        MAT_RUBBER,
        "head",
    )

    # Tapered deltoid/biceps/forearm profiles with overlapping elbow volume.
    # Hands use a compact palm plus visibly curled fingers around the weapon.
    for side in ("l", "r"):
        upper_start, upper_end = BONE_POINTS[f"upper_arm_{side}"]
        fore_start, fore_end = BONE_POINTS[f"forearm_{side}"]
        hand_start, hand_end = BONE_POINTS[f"hand_{side}"]
        upper_axis = (upper_end - upper_start).normalized()
        fore_axis = (fore_end - fore_start).normalized()
        hand_axis = (hand_end - hand_start).normalized()
        # Two-bone deltoid sleeve bridges the torso/clavicle to the moving arm.
        # It sits just outside the underlying shirt loft, so the shoulder reads
        # as one anatomical volume instead of a ball joint or open socket.
        builder.add_blended_loft(
            (
                (upper_start - upper_axis * 0.045, 0.077 * bulk, 0.083 * bulk),
                (upper_start - upper_axis * 0.010, 0.091 * bulk, 0.097 * bulk),
                (upper_start + upper_axis * 0.055, 0.094 * bulk, 0.099 * bulk),
                (upper_start + upper_axis * 0.110, 0.083 * bulk, 0.088 * bulk),
            ),
            MAT_FABRIC,
            (
                {f"clavicle_{side}": 1.0},
                {f"clavicle_{side}": 0.72, f"upper_arm_{side}": 0.28},
                {f"clavicle_{side}": 0.25, f"upper_arm_{side}": 0.75},
                {f"upper_arm_{side}": 1.0},
            ),
            max(8, segment),
        )
        builder.add_loft(
            (
                (upper_start - upper_axis * 0.018, 0.086 * bulk, 0.092 * bulk),
                (upper_start.lerp(upper_end, 0.18), 0.092 * bulk, 0.098 * bulk),
                (upper_start.lerp(upper_end, 0.58), 0.074 * bulk, 0.079 * bulk),
                (upper_end + upper_axis * 0.018, 0.062 * bulk, 0.066 * bulk),
            ),
            MAT_FABRIC,
            f"upper_arm_{side}",
            segment,
        )
        # Continuous elbow sleeve replaces the formerly spherical joint cap.
        builder.add_blended_loft(
            (
                (upper_end - upper_axis * 0.060, 0.064 * bulk, 0.067 * bulk),
                (upper_end - upper_axis * 0.018, 0.070 * bulk, 0.071 * bulk),
                (upper_end + fore_axis * 0.020, 0.071 * bulk, 0.070 * bulk),
                (upper_end + fore_axis * 0.070, 0.064 * bulk, 0.064 * bulk),
            ),
            MAT_FABRIC,
            (
                {f"upper_arm_{side}": 1.0},
                {f"upper_arm_{side}": 0.74, f"forearm_{side}": 0.26},
                {f"upper_arm_{side}": 0.35, f"forearm_{side}": 0.65},
                {f"forearm_{side}": 1.0},
            ),
            max(8, segment),
        )
        builder.add_loft(
            (
                (fore_start - fore_axis * 0.020, 0.064 * bulk, 0.066 * bulk),
                (fore_start.lerp(fore_end, 0.30), 0.073 * bulk, 0.076 * bulk),
                (fore_start.lerp(fore_end, 0.67), 0.058 * bulk, 0.061 * bulk),
                (fore_end + fore_axis * 0.015, 0.045 * bulk, 0.048 * bulk),
            ),
            MAT_FABRIC,
            f"forearm_{side}",
            segment,
        )
        builder.add_loft(
            (
                (hand_start - hand_axis * 0.012, 0.036, 0.030),
                (hand_start.lerp(hand_end, 0.28), 0.044, 0.035),
                (hand_start.lerp(hand_end, 0.56), 0.048, 0.034),
                (hand_start.lerp(hand_end, 0.76), 0.045, 0.031),
            ),
            MAT_RUBBER,
            f"hand_{side}",
            max(8, segment - 2),
        )
        if detail >= 2:
            right, up, forward = basis_between(hand_start, hand_end)
            # A low glove-back panel establishes one readable palm mass.  The
            # fingers then emerge from it as compressed wedges instead of four
            # bead-ended tubes floating in front of the rifle.
            builder.add_box(
                hand_start.lerp(hand_end, 0.52) + up * 0.026,
                (0.070, 0.010, 0.054),
                MAT_GEAR,
                f"hand_{side}",
                0.005,
                (right, up, forward),
            )
            for finger in range(4):
                spread = (finger - 1.5) * 0.0145
                length_scale = 1.0 - finger * 0.055
                base = hand_start.lerp(hand_end, 0.66) + right * spread - up * 0.002
                knuckle = base + forward * (0.031 * length_scale) - up * 0.007
                distal = knuckle + forward * (0.022 * length_scale) - up * 0.015
                tip = distal + forward * (0.012 * length_scale) - up * 0.013
                builder.add_loft(
                    (
                        (base, 0.0084, 0.0074),
                        (knuckle, 0.0078, 0.0068),
                        (distal, 0.0067, 0.0059),
                        (tip, 0.0048, 0.0044),
                    ),
                    MAT_RUBBER,
                    f"hand_{side}",
                    7,
                )
            thumb_sign = -1.0 if side == "l" else 1.0
            thumb_base = hand_start.lerp(hand_end, 0.48) + right * (thumb_sign * 0.035) + up * 0.004
            thumb_knuckle = thumb_base + forward * 0.024 - right * (thumb_sign * 0.012) - up * 0.006
            thumb_tip = thumb_knuckle + forward * 0.018 - right * (thumb_sign * 0.008) - up * 0.012
            builder.add_loft(
                ((thumb_base, 0.009, 0.008), (thumb_knuckle, 0.0075, 0.0068), (thumb_tip, 0.0055, 0.0048)),
                MAT_RUBBER,
                f"hand_{side}",
                7,
            )

    # Thigh -> knee -> calf -> ankle continuity.  The calf bulges high and then
    # tapers into a laced boot instead of terminating in a rectangular shoe.
    for side, x in (("l", -0.155), ("r", 0.155)):
        thigh_start, knee = BONE_POINTS[f"thigh_{side}"]
        _knee_start, ankle = BONE_POINTS[f"shin_{side}"]
        _ankle_start, foot_tail = BONE_POINTS[f"foot_{side}"]
        thigh_axis = (knee - thigh_start).normalized()
        shin_axis = (ankle - knee).normalized()
        foot_axis = (foot_tail - ankle).normalized()
        builder.add_loft(
            (
                (Vector((x, 0.000, 0.965)), 0.101 * bulk, 0.109 * bulk),
                (Vector((x, 0.025, 0.835)), 0.107 * bulk, 0.113 * bulk),
                (Vector((x, 0.065, 0.670)), 0.095 * bulk, 0.098 * bulk),
                (Vector((x, 0.095, 0.545)), 0.078 * bulk, 0.079 * bulk),
            ),
            MAT_FABRIC,
            f"thigh_{side}",
            segment,
        )
        builder.add_blended_loft(
            (
                (knee - thigh_axis * 0.080, 0.084 * bulk, 0.087 * bulk),
                (knee - thigh_axis * 0.025, 0.088 * bulk, 0.091 * bulk),
                (knee + shin_axis * 0.025, 0.087 * bulk, 0.089 * bulk),
                (knee + shin_axis * 0.085, 0.080 * bulk, 0.082 * bulk),
            ),
            MAT_FABRIC,
            (
                {f"thigh_{side}": 1.0},
                {f"thigh_{side}": 0.72, f"shin_{side}": 0.28},
                {f"thigh_{side}": 0.30, f"shin_{side}": 0.70},
                {f"shin_{side}": 1.0},
            ),
            max(8, segment),
        )
        builder.add_loft(
            (
                (Vector((x, 0.095, 0.580)), 0.079 * bulk, 0.081 * bulk),
                (Vector((x, 0.078, 0.465)), 0.092 * bulk, 0.094 * bulk),
                (Vector((x, 0.045, 0.315)), 0.080 * bulk, 0.079 * bulk),
                (Vector((x, 0.018, 0.130)), 0.058 * bulk, 0.061 * bulk),
            ),
            MAT_FABRIC,
            f"shin_{side}",
            segment,
        )
        # A shallow anatomical shell follows the knee instead of a cuboid or
        # a capped ring whose radial fan caught light like a dark hole.
        builder.add_sphere(
            Vector((x, 0.150, 0.560)),
            (0.061, 0.022, 0.070),
            MAT_ARMOR,
            f"shin_{side}",
            max(10, segment),
            7 if builder.lod == 0 else 5,
        )
        builder.add_loft(
            (
                (Vector((x, 0.018, 0.105)), 0.064, 0.073),
                (Vector((x, 0.019, 0.185)), 0.068, 0.074),
                (Vector((x, 0.016, 0.270)), 0.061, 0.067),
            ),
            MAT_RUBBER,
            f"shin_{side}",
            max(8, segment),
        )
        builder.add_blended_loft(
            (
                (ankle - shin_axis * 0.075, 0.068, 0.072),
                (ankle - shin_axis * 0.020, 0.071, 0.074),
                (ankle + foot_axis * 0.030, 0.072, 0.071),
                (ankle + foot_axis * 0.080, 0.069, 0.064),
            ),
            MAT_FABRIC,
            (
                {f"shin_{side}": 1.0},
                {f"shin_{side}": 0.68, f"foot_{side}": 0.32},
                {f"shin_{side}": 0.28, f"foot_{side}": 0.72},
                {f"foot_{side}": 1.0},
            ),
            max(8, segment),
        )
        builder.add_loft(
            (
                (Vector((x, -0.005, 0.100)), 0.066, 0.086),
                (Vector((x, 0.055, 0.096)), 0.073, 0.079),
                (Vector((x, 0.150, 0.075)), 0.074, 0.062),
                (Vector((x, 0.195, 0.052)), 0.061, 0.038),
                (Vector((x, 0.224, 0.045)), 0.049, 0.029),
                (Vector((x, 0.240, 0.044)), 0.028, 0.017),
            ),
            MAT_RUBBER,
            f"foot_{side}",
            max(8, segment),
        )
        builder.add_loft(
            (
                (Vector((x, -0.010, 0.017)), 0.067, 0.014),
                (Vector((x, 0.090, 0.016)), 0.075, 0.014),
                (Vector((x, 0.180, 0.014)), 0.069, 0.012),
                (Vector((x, 0.238, 0.013)), 0.050, 0.010),
            ),
            MAT_RUBBER,
            f"foot_{side}",
            max(8, segment),
        )
        if detail >= 2:
            # Low-profile cross laces and side rails give the boot a readable
            # manufactured surface in close killcams. They overlap the vamp
            # and share the foot bone, so they cannot float during locomotion.
            for lace_index in range(5):
                lace_y = 0.052 + lace_index * 0.026
                lace_half_width = 0.051 - lace_index * 0.0035
                lace_z = 0.145 - lace_index * 0.010
                builder.add_tube(
                    Vector((x - lace_half_width, lace_y, lace_z)),
                    Vector((x + lace_half_width, lace_y, lace_z)),
                    0.0032,
                    0.0032,
                    MAT_GEAR,
                    f"foot_{side}",
                    6,
                )
            for rail_x in (-0.052, 0.052):
                builder.add_tube(
                    Vector((x + rail_x, 0.046, 0.151)),
                    Vector((x + rail_x * 0.78, 0.164, 0.108)),
                    0.0034,
                    0.0030,
                    MAT_GEAR,
                    f"foot_{side}",
                    6,
                )


def add_armor_and_gear(builder: MeshBuilder, variant: dict[str, Any], detail: int) -> None:
    gear = variant["gear"]
    heavy = gear in {"heavy", "support"}
    light = gear == "light"
    plate_half_width = 0.235 if heavy else 0.205 if not light else 0.180
    plate_depth = 0.044 if heavy else 0.035
    # Real SAPI-style clipped plate outlines replace the padded capsule shells
    # used by V3-M.  Thin physical edge depth, shoulder cuts and a narrowed
    # lower edge make the carrier read as layered equipment over a human torso.
    top = plate_half_width * 0.72
    shoulder = plate_half_width * 0.96
    lower = plate_half_width * 0.78
    front_outline = (
        (-top, 1.475),
        (top, 1.475),
        (shoulder, 1.405),
        (plate_half_width, 1.225),
        (lower, 1.105),
        (-lower, 1.105),
        (-plate_half_width, 1.225),
        (-shoulder, 1.405),
    )
    builder.add_panel_y(
        front_outline,
        0.153,
        0.153 + plate_depth * 1.15,
        MAT_ARMOR,
        "spine_02",
    )
    back_outline = tuple((x * 0.96, z - 0.008) for x, z in front_outline)
    builder.add_panel_y(
        back_outline,
        -0.160 - plate_depth,
        -0.150,
        MAT_ARMOR,
        "spine_02",
    )
    # Side cummerbunds bridge front and rear shells instead of leaving the two
    # plates floating as unrelated slabs.
    for x in (-plate_half_width * 0.98, plate_half_width * 0.98):
        builder.add_box(
            Vector((x, 0.002, 1.235)),
            (0.042, 0.285, 0.105),
            MAT_GEAR,
            "spine_01",
            0.008,
        )
    builder.add_loft(
        (
            (Vector((0, 0.010, 1.035)), 0.137, 0.190),
            (Vector((0, 0.012, 1.090)), 0.148, 0.215),
            (Vector((0, 0.012, 1.135)), 0.143, 0.210),
        ),
        MAT_GEAR,
        "spine_01",
    )
    for side in ("l", "r"):
        upper_start, upper_end = BONE_POINTS[f"upper_arm_{side}"]
        upper_axes = basis_between(upper_start, upper_end)
        upper_axis = upper_axes[2]
        armor_center = upper_start + upper_axis * 0.040 + upper_axes[1] * 0.067
        if heavy:
            builder.add_box(
                armor_center,
                (0.162, 0.040, 0.145),
                MAT_ARMOR,
                f"upper_arm_{side}",
                0.016,
                upper_axes,
            )
        # Shoulder retention webbing follows the anatomical slope rather than
        # forming a horizontal floating bar.
        x = upper_start.x * 1.11
        strap_end = Vector((x * 0.58, 0.145, 1.463))
        builder.add_tube(Vector((x, 0.018, 1.425)), strap_end, 0.018, 0.024, MAT_GEAR, f"clavicle_{side}", 8)
    pouch_count = 2 if light else 5 if gear in {"support", "medic"} else 4
    for index in range(pouch_count):
        x = (index - (pouch_count - 1) * 0.5) * (0.082 if pouch_count >= 5 else 0.095)
        height = 0.092 + (index % 2) * 0.016
        builder.add_box(Vector((x, 0.207, 1.150 + (index % 2) * 0.006)), (0.057, 0.036, height * 0.92), MAT_GEAR, "spine_01", 0.009)
        if detail >= 2:
            builder.add_box(Vector((x, 0.227, 1.174 + (index % 2) * 0.006)), (0.043, 0.006, 0.010), MAT_RUBBER, "spine_01", 0.002)
    if detail >= 1:
        # Upper admin/identity panel and one offset push-to-talk unit create the
        # layered, asymmetric carrier read visible in the modern-operator ref.
        builder.add_panel_y(
            ((-0.092, 1.425), (0.092, 1.425), (0.106, 1.365), (0.086, 1.322), (-0.086, 1.322), (-0.106, 1.365)),
            0.198,
            0.214,
            MAT_GEAR,
            "spine_02",
        )
        builder.add_box(Vector((0.142, 0.222, 1.354)), (0.050, 0.028, 0.074), MAT_RUBBER, "spine_02", 0.006)
        builder.add_tube(Vector((0.160, 0.214, 1.390)), Vector((0.218, 0.095, 1.486)), 0.005, 0.004, MAT_RUBBER, "spine_02", 6)
    if detail >= 1:
        builder.add_box(Vector((0.195, -0.183, 1.30)), (0.090, 0.076, 0.215), MAT_GEAR, "spine_02", 0.015)
        builder.add_tube(Vector((0.22, -0.21, 1.37)), Vector((0.25, -0.20, 1.66)), 0.011, 0.006, MAT_METAL, "spine_02", 6)
        builder.add_box(Vector((-0.205, 0.092, 0.995)), (0.094, 0.064, 0.135), MAT_GEAR, "pelvis", 0.012)
        builder.add_box(Vector((0.205, 0.088, 0.995)), (0.080, 0.060, 0.125), MAT_GEAR, "pelvis", 0.012)
    # A narrow utility belt overlaps shirt and trousers, removing the dark
    # disconnected-crotch read while preserving pelvis deformation.
    builder.add_loft(
        (
            (Vector((0, 0.008, 0.992)), 0.132, 0.188),
            (Vector((0, 0.010, 1.035)), 0.138, 0.202),
        ),
        MAT_GEAR,
        "pelvis",
        max(8, {0: 12, 1: 8, 2: 6}[builder.lod]),
        smooth=False,
    )
    backpack_size = {
        "light": (0.30, 0.13, 0.34),
        "standard": (0.38, 0.17, 0.40),
        "marksman": (0.36, 0.16, 0.38),
        # Keep the rear contact plane common across the shared death clips.
        # Heavy roles remain wider/taller, while excess depth would bury their
        # packs below terrain when the common skeleton falls onto its back.
        "heavy": (0.43, 0.17, 0.45),
        "support": (0.45, 0.15, 0.50),
        "medic": (0.43, 0.17, 0.44),
    }[gear]
    pack_width, pack_depth, pack_height = backpack_size
    pack_center_y = -0.160 - pack_depth * 0.43
    builder.add_loft(
        (
            (Vector((0, pack_center_y + 0.010, 1.27 - pack_height * 0.50)), pack_depth * 0.37, pack_width * 0.34),
            (Vector((0, pack_center_y, 1.27 - pack_height * 0.34)), pack_depth * 0.52, pack_width * 0.49),
            (Vector((0, pack_center_y - 0.005, 1.27 + pack_height * 0.28)), pack_depth * 0.54, pack_width * 0.50),
            (Vector((0, pack_center_y + 0.008, 1.27 + pack_height * 0.50)), pack_depth * 0.35, pack_width * 0.39),
        ),
        MAT_GEAR,
        "spine_02",
    )
    if detail >= 1:
        rear_y = pack_center_y - pack_depth * 0.53
        panel_half_w = pack_width * 0.39
        panel_bottom = 1.27 - pack_height * 0.34
        panel_top = 1.27 + pack_height * 0.34
        builder.add_panel_y(
            (
                (-panel_half_w * 0.82, panel_top),
                (panel_half_w * 0.82, panel_top),
                (panel_half_w, panel_top - 0.060),
                (panel_half_w, panel_bottom + 0.045),
                (panel_half_w * 0.82, panel_bottom),
                (-panel_half_w * 0.82, panel_bottom),
                (-panel_half_w, panel_bottom + 0.045),
                (-panel_half_w, panel_top - 0.060),
            ),
            # Keep the plate visually proud by only 2 mm.  The former 14 mm
            # rear overhang became the lowest point of three LOD1 variants in
            # the shared prone/death pose and buried the panel 30--37 mm below
            # the terrain plane.
            rear_y - 0.002,
            rear_y + 0.014,
            MAT_ARMOR,
            "spine_02",
        )
        for z in (1.27 - pack_height * 0.19, 1.27 + pack_height * 0.13):
            # Compression webbing sits on the plate face rather than floating
            # behind it; this also keeps all shared death poses terrain-safe.
            builder.add_box(Vector((0, rear_y + 0.004, z)), (pack_width * 0.82, 0.014, 0.027), MAT_GEAR, "spine_02", 0.004)
        # One offset side pocket and top grab loop remove mirror symmetry while
        # keeping the rear death-contact plane shallow.
        side_sign = -1.0 if variant["id"] in {"rifleman", "scout", "medic"} else 1.0
        builder.add_box(
            Vector((side_sign * (pack_width * 0.50 + 0.030), pack_center_y, 1.20)),
            (0.072, pack_depth * 0.64, 0.150),
            MAT_GEAR,
            "spine_02",
            0.010,
        )
        builder.add_tube(
            Vector((-0.055, pack_center_y - pack_depth * 0.38, 1.27 + pack_height * 0.50)),
            Vector((0.055, pack_center_y - pack_depth * 0.38, 1.27 + pack_height * 0.50)),
            0.008,
            0.008,
            MAT_GEAR,
            "spine_02",
            8,
        )
    if gear == "support":
        builder.add_tube(Vector((0.17, -0.230, 1.08)), Vector((0.17, -0.230, 1.48)), 0.050, 0.050, MAT_METAL, "spine_02", 12, (1.0, 0.82))
        if detail >= 1:
            for index in range(5):
                builder.add_box(Vector((-0.15 + index * 0.055, 0.235, 1.08)), (0.035, 0.030, 0.10), MAT_METAL, "spine_01", 0.005)
    if gear == "marksman" and detail >= 1:
        for index, x in enumerate((-0.31, -0.18, 0.18, 0.31)):
            builder.add_loft(
                (
                    (Vector((x, -0.025, 1.42 - (index % 2) * 0.035)), 0.022, 0.055),
                    (Vector((x * 1.08, -0.035, 1.18 - (index % 2) * 0.055)), 0.016, 0.043),
                ),
                MAT_FABRIC,
                "spine_02",
                8,
            )
    if gear == "medic":
        builder.add_box(Vector((0, 0.225, 1.315)), (0.12, 0.020, 0.041), MAT_ACCENT, "spine_02", 0.004)
        builder.add_box(Vector((0, 0.227, 1.315)), (0.041, 0.022, 0.12), MAT_ACCENT, "spine_02", 0.004)
        builder.add_box(Vector((0, pack_center_y - pack_depth * 0.53, 1.29)), (0.15, 0.020, 0.046), MAT_ACCENT, "spine_02", 0.004)
        builder.add_box(Vector((0, pack_center_y - pack_depth * 0.54, 1.29)), (0.046, 0.022, 0.15), MAT_ACCENT, "spine_02", 0.004)

    # Six silhouettes remain recognisable even when camouflage collapses at
    # distance.  These are functional role cues, not interchangeable greebles.
    if gear == "heavy":
        # A thin, tapered ballistic groin flap overlaps the lower carrier.  A
        # rounded loft still read as a ball from the hero camera, so author the
        # real panel outline explicitly: broad webbing edge, clipped corners,
        # and a pointed lower edge.  Front/back surfaces are only 52mm apart.
        outline = (
            (-0.096, 1.125),
            (0.096, 1.125),
            (0.118, 1.060),
            (0.087, 0.975),
            (0.000, 0.918),
            (-0.087, 0.975),
            (-0.118, 1.060),
        )
        panel_vertices = [
            Vector((x, y, z))
            for y in (0.184, 0.236)
            for x, z in outline
        ]
        panel_size = len(outline)
        panel_faces: list[list[int]] = []
        # Triangulate both convex caps explicitly. Blender's tangent generator
        # rejects n-gons even when the export path would triangulate them later.
        for index in range(1, panel_size - 1):
            panel_faces.append([0, index + 1, index])
            panel_faces.append([panel_size, panel_size + index, panel_size + index + 1])
        for index in range(panel_size):
            next_index = (index + 1) % panel_size
            panel_faces.append([index, next_index, panel_size + next_index, panel_size + index])
        builder.add_raw(panel_vertices, panel_faces, MAT_ARMOR, "pelvis", smooth=False)
        for side in ("l", "r"):
            fore_start, fore_end = BONE_POINTS[f"forearm_{side}"]
            axes = basis_between(fore_start, fore_end)
            builder.add_box(fore_start.lerp(fore_end, 0.48) + axes[1] * 0.065, (0.125, 0.040, 0.145), MAT_ARMOR, f"forearm_{side}", 0.016, axes)
    elif gear == "light":
        # Scout shoulder cape and compact hydration roll break the standard
        # helmet/plate/backpack outline without hiding the arm joints.
        builder.add_loft(
            (
                (Vector((-0.27, -0.045, 1.43)), 0.028, 0.090),
                (Vector((-0.34, -0.055, 1.18)), 0.018, 0.065),
            ),
            MAT_FABRIC,
            "spine_02",
            8,
        )
        builder.add_tube(Vector((-0.16, -0.24, 1.10)), Vector((0.16, -0.24, 1.10)), 0.038, 0.038, MAT_GEAR, "spine_01", 10)
    elif gear == "support":
        upper_start, upper_end = BONE_POINTS["upper_arm_l"]
        axes = basis_between(upper_start, upper_end)
        builder.add_box(
            upper_start + axes[2] * 0.060 + axes[1] * 0.080,
            (0.190, 0.052, 0.170),
            MAT_ARMOR,
            "upper_arm_l",
            0.020,
            axes,
        )
        builder.add_box(Vector((-0.20, 0.245, 1.02)), (0.16, 0.09, 0.15), MAT_METAL, "pelvis", 0.018)
    elif gear == "medic":
        for x in (-0.23, 0.23):
            builder.add_tube(Vector((x, -0.18, 1.12)), Vector((x, -0.18, 1.34)), 0.050, 0.050, MAT_GEAR, "spine_02", 10, (1.0, 0.72))
    else:
        builder.add_tube(Vector((-0.20, -0.19, 1.38)), Vector((-0.25, -0.18, 1.67)), 0.008, 0.005, MAT_METAL, "spine_02", 6)


def add_headgear(builder: MeshBuilder, variant: dict[str, Any], detail: int) -> None:
    kind = variant["headgear"]
    if kind in {"helmet", "visor", "medic"}:
        # Multi-ring high-cut shell follows a real brow/crown profile.  It
        # replaces the glossy half-sphere that made V2-D read as a toy helmet.
        builder.add_loft(
            (
                (Vector((0, -0.004, 1.680)), 0.092, 0.107),
                (Vector((0, -0.016, 1.708)), 0.104, 0.116),
                (Vector((0, -0.024, 1.748)), 0.094, 0.109),
                (Vector((0, -0.026, 1.780)), 0.058, 0.074),
                (Vector((0, -0.025, 1.793)), 0.018, 0.026),
            ),
            MAT_ARMOR,
            "head",
            max(10, {0: 18, 1: 10, 2: 8}[builder.lod]),
        )
        builder.add_box(Vector((0, 0.083, 1.711)), (0.194, 0.028, 0.021), MAT_ARMOR, "head", 0.007)
        if detail >= 1:
            builder.add_sphere(Vector((-0.102, -0.004, 1.668)), (0.019, 0.031, 0.036), MAT_GEAR, "head", 12, 7)
            builder.add_sphere(Vector((0.102, -0.004, 1.668)), (0.019, 0.031, 0.036), MAT_GEAR, "head", 12, 7)
            builder.add_box(Vector((0, -0.098, 1.750)), (0.060, 0.022, 0.024), MAT_GEAR, "head", 0.006)
    if kind == "visor":
        builder.add_loft(
            (
                (Vector((0, 0.088, 1.686)), 0.090, 0.033),
                (Vector((0, 0.112, 1.687)), 0.080, 0.027),
            ),
            MAT_LENS,
            "head",
            12,
        )
        builder.add_box(Vector((0, 0.085, 1.721)), (0.184, 0.018, 0.012), MAT_RUBBER, "head", 0.004)
        builder.add_box(Vector((0, 0.087, 1.650)), (0.174, 0.016, 0.012), MAT_RUBBER, "head", 0.004)
    else:
        # Keep the same human cue as the supplied modern-operator reference:
        # one narrow exposed orbital strip inside the balaclava.  This patch is
        # a shallow, face-conforming grid rather than a flattened sphere.  The
        # latter still produced a flesh-coloured capsule with bulbous ends even
        # after its height was reduced.  Five columns follow the head's convex
        # front and four tapered rows tuck beneath the helmet brow and mask.
        # Gaze comes from the shared atlas; there are no protruding eye meshes.
        if detail >= 1:
            aperture_scale = 1.03 if kind in {"hood", "boonie"} else 1.0
            # Rounded seven-column opening follows the brow and cheek planes.
            # The previous four-row rectangle exposed a visible flesh-coloured
            # sticker at every corner in close killcams.  Narrow end rings and
            # a stronger convex Y profile tuck this surface beneath the fabric
            # rim while retaining enough pixels for a readable gaze.
            rows = (
                (1.681, 0.034 * aperture_scale, 0.0990),
                (1.686, 0.050 * aperture_scale, 0.1015),
                (1.693, 0.061 * aperture_scale, 0.1020),
                (1.701, 0.061 * aperture_scale, 0.1000),
                (1.708, 0.050 * aperture_scale, 0.0960),
                (1.713, 0.034 * aperture_scale, 0.0920),
            )
            column_factors = (-1.0, -0.70, -0.35, 0.0, 0.35, 0.70, 1.0)
            aperture_vertices: list[Vector] = []
            for z, half_width, surface_y in rows:
                for factor in column_factors:
                    aperture_vertices.append(
                        Vector(
                            (
                                factor * half_width,
                                surface_y + (1.0 - factor * factor) * 0.0052,
                                z,
                            )
                        )
                    )
            aperture_faces: list[list[int]] = []
            columns = len(column_factors)
            for row in range(len(rows) - 1):
                for column in range(columns - 1):
                    a = row * columns + column
                    aperture_faces.append([a, a + columns, a + columns + 1, a + 1])
            builder.add_raw(
                aperture_vertices,
                aperture_faces,
                MAT_SKIN,
                "head",
                smooth=True,
            )
            # Physical balaclava seam around the aperture hides the skin patch
            # boundary and provides a real cloth contact line under grazing
            # light.  Four overlapping rails are cheaper and more stable than
            # a second alpha texture and remain attached to the head bone.
            rim_y = 0.105
            rim_segments = 8 if builder.lod == 0 else 6
            for x_sign in (-1.0, 1.0):
                builder.add_tube(
                    Vector((x_sign * 0.061 * aperture_scale, rim_y, 1.685)),
                    Vector((x_sign * 0.057 * aperture_scale, rim_y - 0.006, 1.709)),
                    0.0045,
                    0.0038,
                    MAT_RUBBER,
                    "head",
                    rim_segments,
                )
            builder.add_tube(
                Vector((-0.052 * aperture_scale, rim_y - 0.004, 1.713)),
                Vector((0.052 * aperture_scale, rim_y - 0.004, 1.713)),
                0.0040,
                0.0040,
                MAT_RUBBER,
                "head",
                rim_segments,
            )
            builder.add_tube(
                Vector((-0.056 * aperture_scale, rim_y + 0.001, 1.681)),
                Vector((0.056 * aperture_scale, rim_y + 0.001, 1.681)),
                0.0043,
                0.0043,
                MAT_RUBBER,
                "head",
                rim_segments,
            )

            # Helmeted and marksman roles use one continuous ballistic-eyewear
            # silhouette over the face opening.  A single clipped lens avoids
            # the paired robot-eye look while matching contemporary operator
            # references and concealing face-detail limitations at killcam
            # range. Role identity remains in the helmet, hood, boonie, armour,
            # weapon and pack silhouettes; leaving one role with a painted eye
            # strip made the scout conspicuously less realistic than the pack.
            if kind in {"helmet", "medic", "boonie", "hood"}:
                frame = (
                    (-0.073, 1.681),
                    (-0.063, 1.706),
                    (0.063, 1.706),
                    (0.073, 1.681),
                    (0.060, 1.674),
                    (-0.060, 1.674),
                )
                lens = (
                    (-0.066, 1.683),
                    (-0.057, 1.700),
                    (0.057, 1.700),
                    (0.066, 1.683),
                    (0.055, 1.678),
                    (-0.055, 1.678),
                )
                builder.add_panel_y(frame, 0.104, 0.112, MAT_RUBBER, "head")
                builder.add_panel_y(lens, 0.111, 0.117, MAT_LENS, "head", smooth=True)
                # Short, almost-horizontal temple arms terminate beneath the
                # helmet/boonie instead of crossing the cheeks like antennae.
                builder.add_tube(
                    Vector((-0.086, 0.075, 1.691)),
                    Vector((-0.069, 0.110, 1.691)),
                    0.0037,
                    0.0030,
                    MAT_RUBBER,
                    "head",
                    rim_segments,
                )
                builder.add_tube(
                    Vector((0.069, 0.110, 1.691)),
                    Vector((0.086, 0.075, 1.691)),
                    0.0030,
                    0.0037,
                    MAT_RUBBER,
                    "head",
                    rim_segments,
                )
    # High neck gaiter is common to every role, including the breacher visor.
    # Its lower flare overlaps the carrier collar and visually shortens the neck.
    builder.add_blended_loft(
        (
            (Vector((0, -0.008, 1.430)), 0.116, 0.145),
            (Vector((0, -0.002, 1.468)), 0.103, 0.123),
            (Vector((0, 0.002, 1.505)), 0.089, 0.102),
            (Vector((0, 0.004, 1.540)), 0.078, 0.089),
            (Vector((0, 0.004, 1.575)), 0.073, 0.084),
        ),
        MAT_RUBBER,
        (
            {"spine_02": 1.0},
            {"spine_02": 0.55, "neck": 0.45},
            {"neck": 1.0},
            {"neck": 0.74, "head": 0.26},
            {"neck": 0.30, "head": 0.70},
        ),
        {0: 24, 1: 12, 2: 8}[builder.lod],
    )
    if kind == "hood":
        builder.add_loft(
            (
                (Vector((0, -0.012, 1.590)), 0.087, 0.094),
                (Vector((0, -0.024, 1.660)), 0.108, 0.113),
                (Vector((0, -0.030, 1.730)), 0.098, 0.106),
                (Vector((0, -0.028, 1.782)), 0.045, 0.055),
            ),
            MAT_FABRIC,
            "head",
            max(10, {0: 18, 1: 10, 2: 8}[builder.lod]),
        )
        builder.add_loft(
            (
                (Vector((0, -0.018, 1.455)), 0.106, 0.150),
                (Vector((0, -0.020, 1.505)), 0.122, 0.164),
                (Vector((0, -0.016, 1.555)), 0.108, 0.144),
            ),
            MAT_FABRIC,
            "neck",
            10,
        )
        if detail >= 1:
            # Sagittal seam and compact brow reinforcement give the hood a sewn
            # garment construction instead of an uninterrupted egg silhouette.
            builder.add_tube(
                Vector((-0.072, 0.079, 1.716)),
                Vector((0.072, 0.079, 1.716)),
                0.0034,
                0.0034,
                MAT_GEAR,
                "head",
                8,
            )
    if kind == "boonie":
        builder.add_loft(
            (
                (Vector((0, -0.006, 1.754)), 0.087, 0.104),
                (Vector((0, -0.010, 1.792)), 0.073, 0.086),
                (Vector((0, -0.012, 1.812)), 0.030, 0.042),
            ),
            MAT_FABRIC,
            "head",
            14,
        )
        builder.add_loft(
            (
                # Raise and shorten the forward brim so the verified eye line
                # remains visible from a level gameplay camera. The prior
                # 145 mm projection combined with the -7 degree neck pitch
                # blanked both eyes and made the marksman look headless.
                (Vector((0, -0.005, 1.748)), 0.094, 0.139),
                (Vector((0, -0.002, 1.756)), 0.096, 0.142),
            ),
            MAT_FABRIC,
            "head",
            16,
        )
    if kind == "medic":
        # The identity mark lives on carrier and pack; a bright forehead cross
        # made the face read as an arcade target.  Keep only a restrained side
        # helmet tab that does not dominate the front silhouette.
        builder.add_box(Vector((0.108, -0.004, 1.735)), (0.010, 0.054, 0.044), MAT_ACCENT, "head", 0.003)


def add_weapon(builder: MeshBuilder, variant: dict[str, Any], detail: int) -> None:
    kind = variant["weapon"]
    receiver_length = {"breacher": 0.25, "carbine": 0.24, "rifle": 0.30, "marksman": 0.34, "support": 0.36}[kind]
    barrel_end = {"breacher": 0.93, "carbine": 0.98, "rifle": 1.09, "marksman": 1.24, "support": 1.16}[kind]
    receiver_center = Vector((0.02, 0.58, 1.245))
    receiver_width = 0.090 if kind != "support" else 0.114
    # Stepped upper/lower receiver, ejection-side housing and magazine well.
    # The old single bevelled cuboid was the largest remaining toy cue.
    builder.add_box(
        receiver_center + Vector((0.0, 0.010, 0.024)),
        (receiver_width, receiver_length, 0.074),
        MAT_METAL,
        "weapon",
        0.008,
    )
    builder.add_box(
        Vector((0.020, 0.552, 1.205)),
        (receiver_width * 0.86, receiver_length * 0.66, 0.058),
        MAT_METAL,
        "weapon",
        0.007,
    )
    builder.add_box(Vector((0.071, 0.588, 1.258)), (0.010, 0.112, 0.036), MAT_RUBBER, "weapon", 0.003)
    # Full-length adjustable stock reaches the firing-side shoulder pocket when
    # the weapon bone enters Aim/Fire; low-ready keeps it clear of the torso.
    builder.add_loft(
        (
            (Vector((0.02, 0.050, 1.245)), 0.052, 0.059),
            (Vector((0.02, 0.120, 1.298)), 0.057, 0.059),
            (Vector((0.02, 0.240, 1.294)), 0.050, 0.050),
            (Vector((0.02, 0.410, 1.255)), 0.042, 0.044),
        ),
        MAT_RUBBER,
        "weapon",
        8 if builder.lod == 0 else 6,
        smooth=False,
    )
    builder.add_box(Vector((0.02, 0.030, 1.245)), (0.102, 0.032, 0.112), MAT_RUBBER, "weapon", 0.008)
    builder.add_box(
        Vector((0.02, 0.785, 1.245)),
        (0.104 if kind == "support" else 0.076, 0.272, 0.070),
        MAT_METAL,
        "weapon",
        0.009,
    )
    # Top and lower handguard rails make the long axis readable in silhouette.
    builder.add_box(Vector((0.02, 0.785, 1.296)), (0.090, 0.265, 0.018), MAT_RUBBER, "weapon", 0.003)
    builder.add_box(Vector((0.02, 0.785, 1.195)), (0.074, 0.245, 0.014), MAT_RUBBER, "weapon", 0.003)
    barrel_start = 0.895
    builder.add_tube(
        Vector((0.02, barrel_start, 1.245)),
        Vector((0.02, barrel_end, 1.245)),
        0.018 if kind != "support" else 0.024,
        0.014 if kind != "support" else 0.019,
        MAT_METAL,
        "weapon",
        10 if builder.lod == 0 else 8,
    )
    # Angled pistol grip with the authored contact point inside its upper half.
    grip_top = Vector((0.045, 0.555, 1.215))
    grip_bottom = Vector((0.050, 0.485, 1.095))
    grip_axes = basis_between(grip_top, grip_bottom)
    builder.add_box(
        grip_top.lerp(grip_bottom, 0.50),
        (0.055, 0.046, (grip_bottom - grip_top).length + 0.018),
        MAT_RUBBER,
        "weapon",
        0.008,
        grip_axes,
    )
    # A rigid, angled magazine follows the magazine bone.  The floorplate is a
    # separate profile break but shares the same bone for reload continuity.
    magazine_top = Vector((0.020, 0.525, 1.205))
    magazine_mid = Vector((0.020, 0.493, 1.132))
    magazine_bottom = Vector((0.020, 0.472, 1.052))
    mag_axes = basis_between(magazine_top, magazine_bottom)
    magazine_width = 0.135 if kind == "support" else 0.072
    magazine_depth = 0.095 if kind == "support" else 0.050
    builder.add_clipped_loft(
        (
            (magazine_top, magazine_width * 0.45, magazine_depth * 0.46),
            (magazine_mid, magazine_width * 0.50, magazine_depth * 0.50),
            (magazine_bottom, magazine_width * 0.46, magazine_depth * 0.47),
        ),
        MAT_METAL,
        "magazine",
    )
    builder.add_box(
        magazine_bottom + mag_axes[2] * 0.004,
        (magazine_width * 1.10, magazine_depth * 1.10, 0.018),
        MAT_RUBBER,
        "magazine",
        0.004,
        mag_axes,
    )
    if kind in {"rifle", "carbine", "breacher"}:
        builder.add_box(Vector((0.02, 0.65, 1.332)), (0.032, 0.046, 0.028), MAT_METAL, "weapon", 0.005)
        builder.add_box(Vector((0.02, 0.65, 1.361)), (0.040, 0.070, 0.034), MAT_LENS, "weapon", 0.006)
    if kind == "marksman":
        builder.add_box(Vector((0.02, 0.64, 1.342)), (0.034, 0.138, 0.032), MAT_METAL, "weapon", 0.005)
        builder.add_tube(Vector((0.02, 0.50, 1.382)), Vector((0.02, 0.77, 1.382)), 0.030, 0.028, MAT_LENS, "weapon", 10)
        builder.add_tube(Vector((0.02, 1.12, 1.245)), Vector((0.02, 1.25, 1.245)), 0.022, 0.032, MAT_METAL, "weapon", 8)
    if kind == "support":
        builder.add_box(Vector((0.02, 0.66, 1.340)), (0.038, 0.108, 0.030), MAT_METAL, "weapon", 0.005)
        builder.add_box(Vector((0.02, 0.66, 1.378)), (0.058, 0.132, 0.050), MAT_LENS, "weapon", 0.008)
        builder.add_tube(Vector((-0.05, 0.79, 1.20)), Vector((-0.09, 0.97, 1.05)), 0.009, 0.007, MAT_METAL, "weapon", 6)
        builder.add_tube(Vector((0.05, 0.79, 1.20)), Vector((0.09, 0.97, 1.05)), 0.009, 0.007, MAT_METAL, "weapon", 6)
    if detail >= 2:
        builder.add_tube(Vector((-0.05, 0.73, 1.305)), Vector((0.05, 0.73, 1.305)), 0.007, 0.007, MAT_METAL, "weapon", 6)
        builder.add_box(Vector((0.02, 0.920, 1.302)), (0.038, 0.026, 0.050), MAT_METAL, "weapon", 0.005)
        # Recessed M-LOK-like side slots and magazine ribs replace broad blank
        # cuboid faces with functional, scale-readable construction detail.
        for side_x in (-0.0195, 0.0595):
            for slot in range(4):
                builder.add_box(
                    Vector((side_x, 0.724 + slot * 0.043, 1.244)),
                    (0.003, 0.026, 0.028),
                    MAT_RUBBER,
                    "weapon",
                    0.001,
                )
        for amount in (0.36, 0.70):
            rib_center = magazine_top.lerp(magazine_bottom, amount)
            builder.add_box(
                rib_center,
                (magazine_width * 1.02, magazine_depth * 1.04, 0.008),
                MAT_RUBBER,
                "magazine",
                0.002,
                mag_axes,
            )
        builder.add_tube(
            Vector((0.02, barrel_end + 0.004, 1.245)),
            Vector((0.02, barrel_end + 0.064, 1.245)),
            0.020 if kind == "support" else 0.015,
            0.023 if kind == "support" else 0.018,
            MAT_METAL,
            "weapon",
            8,
        )


def add_lod0_details(builder: MeshBuilder, variant: dict[str, Any]) -> None:
    """Spend close-range geometry on contacts, silhouette, and readable kit.

    The parts below are centimetre-scale construction features, not random
    greebles: vest webbing, closures, joint protection, clothing pockets,
    footwear layers, helmet rails, and weapon controls visible at combat range.
    """
    # Plate carrier edge rails and shoulder retention straps.
    builder.add_box(Vector((-0.205, 0.204, 1.30)), (0.030, 0.025, 0.34), MAT_GEAR, "spine_02", 0.006)
    builder.add_box(Vector((0.205, 0.204, 1.30)), (0.030, 0.025, 0.34), MAT_GEAR, "spine_02", 0.006)
    builder.add_box(Vector((-0.16, 0.135, 1.47)), (0.058, 0.046, 0.18), MAT_GEAR, "spine_02", 0.010)
    builder.add_box(Vector((0.16, 0.135, 1.47)), (0.058, 0.046, 0.18), MAT_GEAR, "spine_02", 0.010)
    # Three MOLLE courses; the narrow relief catches grazing light without a
    # unique high-resolution texture for every soldier.
    for row in range(3):
        z = 1.24 + row * 0.068
        for column in range(6):
            x = (column - 2.5) * 0.064
            builder.add_box(Vector((x, 0.194, z)), (0.043, 0.012, 0.011), MAT_GEAR, "spine_02", 0.003)
    # Quick-release buckles and radio/PTT routing.
    for x in (-0.18, 0.18):
        builder.add_box(Vector((x, 0.220, 1.18)), (0.035, 0.026, 0.050), MAT_RUBBER, "spine_01", 0.006)
    builder.add_tube(Vector((0.18, 0.205, 1.34)), Vector((0.24, 0.13, 1.51)), 0.006, 0.005, MAT_RUBBER, "spine_02", 6)
    # Sleeve cargo pockets, cuff straps, and elbow shells follow actual limb
    # axes so they cannot detach when the arm bends.
    for side in ("l", "r"):
        upper_start, upper_end = BONE_POINTS[f"upper_arm_{side}"]
        fore_start, fore_end = BONE_POINTS[f"forearm_{side}"]
        upper_axes = basis_between(upper_start, upper_end)
        fore_axes = basis_between(fore_start, fore_end)
        upper_mid = upper_start.lerp(upper_end, 0.42)
        elbow = upper_end.lerp(fore_end, 0.08)
        cuff = fore_start.lerp(fore_end, 0.76)
        builder.add_box(upper_mid + upper_axes[1] * 0.064, (0.086, 0.024, 0.105), MAT_FABRIC, f"upper_arm_{side}", 0.008, upper_axes)
        builder.add_box(elbow + fore_axes[1] * 0.057, (0.086, 0.030, 0.090), MAT_ARMOR, f"forearm_{side}", 0.010, fore_axes)
        builder.add_box(cuff, (0.094, 0.018, 0.042), MAT_GEAR, f"forearm_{side}", 0.004, fore_axes)
    # Cargo pockets and knee retention bands.
    for side, x in (("l", -0.155), ("r", 0.155)):
        builder.add_box(Vector((x + (-0.084 if side == "l" else 0.084), 0.030, 0.76)), (0.078, 0.052, 0.140), MAT_FABRIC, f"thigh_{side}", 0.010)
        builder.add_box(Vector((x, 0.148, 0.60)), (0.122, 0.020, 0.025), MAT_GEAR, f"thigh_{side}", 0.004)
        builder.add_box(Vector((x, 0.145, 0.51)), (0.120, 0.020, 0.025), MAT_GEAR, f"shin_{side}", 0.004)
        # Tongue, heel counter and toe rand introduce recognizable boot
        # construction while the underlying loft continues to deform cleanly.
        builder.add_box(Vector((x, 0.090, 0.105)), (0.092, 0.118, 0.022), MAT_GEAR, f"foot_{side}", 0.005)
        builder.add_box(Vector((x, -0.006, 0.082)), (0.112, 0.040, 0.094), MAT_RUBBER, f"foot_{side}", 0.008)
        builder.add_box(Vector((x, 0.190, 0.047)), (0.112, 0.086, 0.028), MAT_RUBBER, f"foot_{side}", 0.006)
        # Five lace bars follow the already-rounded boot volume; no slab sole.
        for lace in range(5):
            builder.add_box(Vector((x, 0.188 - lace * 0.024, 0.119 + lace * 0.002)), (0.082, 0.008, 0.006), MAT_GEAR, f"foot_{side}", 0.002)
    # Helmet rails, counterweight, front mount, chin strap, and ventilation.
    if variant["headgear"] in {"helmet", "visor", "medic"}:
        for side, x in (("l", -0.108), ("r", 0.108)):
            builder.add_box(Vector((x, 0.006, 1.704)), (0.018, 0.138, 0.042), MAT_GEAR, "head", 0.005)
            for slot in range(3):
                builder.add_box(Vector((x, 0.052 - slot * 0.036, 1.720)), (0.010, 0.017, 0.009), MAT_RUBBER, "head", 0.002)
        builder.add_box(Vector((0, 0.108, 1.758)), (0.052, 0.024, 0.040), MAT_GEAR, "head", 0.006)
        builder.add_box(Vector((0, -0.108, 1.738)), (0.080, 0.024, 0.044), MAT_GEAR, "head", 0.006)
        builder.add_tube(Vector((-0.103, 0.018, 1.668)), Vector((-0.052, 0.096, 1.590)), 0.005, 0.004, MAT_GEAR, "head", 6)
        builder.add_tube(Vector((0.103, 0.018, 1.668)), Vector((0.052, 0.096, 1.590)), 0.005, 0.004, MAT_GEAR, "head", 6)
    # Face depth stays fully covered; the small bridge and brow pads shape the
    # smoked goggles without reintroducing a bright exposed nose.
    if variant["headgear"] == "visor":
        for x in (-0.040, 0.040):
            builder.add_box(Vector((x, 0.119, 1.700)), (0.052, 0.010, 0.008), MAT_RUBBER, "head", 0.003)
    # Weapon handguard ribs, selector housing, charging handle, sling anchors,
    # and stock pad.  All are rigidly bound to the weapon bone.
    for rib in range(5):
        builder.add_box(Vector((0.02, 0.705 + rib * 0.033, 1.245)), (0.079, 0.006, 0.070), MAT_RUBBER, "weapon", 0.002)
    builder.add_box(Vector((0.074, 0.565, 1.26)), (0.022, 0.055, 0.025), MAT_METAL, "weapon", 0.004)
    builder.add_box(Vector((-0.052, 0.595, 1.31)), (0.045, 0.018, 0.018), MAT_METAL, "weapon", 0.003)
    builder.add_tube(Vector((-0.055, 0.10, 1.28)), Vector((-0.25, 0.08, 1.03)), 0.006, 0.006, MAT_GEAR, "weapon", 6)


def build_variant(
    variant_index: int,
    variant: dict[str, Any],
    lod: int,
    collection: bpy.types.Collection,
    armature: bpy.types.Object,
    materials: list[bpy.types.Material],
) -> bpy.types.Object:
    detail = {0: 2, 1: 1, 2: 0}[lod]
    builder = MeshBuilder(variant_index, lod)
    add_body(builder, variant, detail)
    add_armor_and_gear(builder, variant, detail)
    add_headgear(builder, variant, detail)
    add_weapon(builder, variant, detail)
    if detail >= 2:
        add_lod0_details(builder, variant)
    name = f"SM_Enemy_{variant['id'].title()}_LOD{lod}"
    return builder.finish(name, collection, armature, materials, variant)


def rot(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> tuple[float, float, float]:
    return (math.radians(x), math.radians(y), math.radians(z))


def combat_pose_rot(neck_x: float = -7.0, head_x: float = 2.0) -> dict[str, tuple[float, float, float]]:
    """Restrained upper-body counter-rotation shared by Aim and Fire.

    Lower-body Euler offsets were deliberately removed after the V2-E side
    render exposed crossed ankles and lost ground contact.  Until a solved foot
    IK target is added, the verified rest stance remains authoritative while
    the ribcage and head provide the small asymmetry needed for shouldering.
    Upper-limb segment targets remain absolute and retain measured contacts.
    """
    return {
        "spine_01": rot(-1.5, 0.0, 1.2),
        "spine_02": rot(-2.0, 0.0, -1.0),
        "neck": rot(neck_x, 0.0, 0.0),
        "head": rot(head_x, 0.0, 0.0),
    }


def combat_leg_segments() -> dict[str, tuple[Vector, Vector]]:
    """Solve a planted, asymmetric firing stance without crossed ankles.

    Both ankles stay at their authored ground height and every target segment
    preserves the exact rest-bone length.  This removes the mannequin-straight
    parallel legs while avoiding the floating feet produced by arbitrary Euler
    offsets in the earlier candidate.
    """
    targets: dict[str, tuple[Vector, Vector]] = {}
    specifications = {
        "l": {
            "ankle": Vector((-0.170, 0.050, 0.130)),
            "knee_hint": Vector((-0.170, 0.155, 0.555)),
            "foot_direction": Vector((-0.012, 0.207, -0.060)),
        },
        "r": {
            "ankle": Vector((0.170, -0.045, 0.130)),
            "knee_hint": Vector((0.170, 0.060, 0.550)),
            "foot_direction": Vector((0.012, 0.207, -0.060)),
        },
    }
    for side in ("l", "r"):
        hip = BONE_POINTS[f"thigh_{side}"][0]
        ankle = specifications[side]["ankle"]
        thigh_length = (BONE_POINTS[f"thigh_{side}"][1] - hip).length
        shin_length = (
            BONE_POINTS[f"shin_{side}"][1] - BONE_POINTS[f"shin_{side}"][0]
        ).length
        knee = solve_elbow(
            hip,
            ankle,
            thigh_length,
            shin_length,
            specifications[side]["knee_hint"],
        )
        foot_length = (
            BONE_POINTS[f"foot_{side}"][1] - BONE_POINTS[f"foot_{side}"][0]
        ).length
        foot_tail = ankle + specifications[side]["foot_direction"].normalized() * foot_length
        targets[f"thigh_{side}"] = (hip, knee)
        targets[f"shin_{side}"] = (knee, ankle)
        targets[f"foot_{side}"] = (ankle, foot_tail)
    return targets


def firing_pose_with_stance(
    recoil: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, tuple[Vector, Vector]]:
    segments = combat_leg_segments()
    segments.update(firing_pose_segments(recoil))
    return segments


def clear_pose(armature: bpy.types.Object) -> None:
    for bone in armature.pose.bones:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = (0.0, 0.0, 0.0)
        bone.location = (0.0, 0.0, 0.0)
        bone.scale = (1.0, 1.0, 1.0)


def segment_matrix(head: Vector, tail: Vector) -> Matrix:
    """Armature-space matrix whose local +Y axis spans head→tail."""
    y_axis = (tail - head).normalized()
    helper = Vector((0.0, 0.0, 1.0)) if abs(y_axis.z) < 0.94 else Vector((1.0, 0.0, 0.0))
    x_axis = y_axis.cross(helper).normalized()
    z_axis = x_axis.cross(y_axis).normalized()
    matrix = Matrix((x_axis, y_axis, z_axis)).transposed().to_4x4()
    matrix.translation = head
    return matrix


def segment_basis(
    pose_bone: bpy.types.PoseBone,
    target: Matrix,
    solved_matrices: dict[str, Matrix],
) -> Matrix:
    """Convert an armature-space target into a stable pose-local basis.

    Assigning ``PoseBone.matrix`` directly and then updating the dependency
    graph is not deterministic for connected chains: Blender can re-compose
    children from their rest matrices and move the glove off its authored
    contact.  This is the explicit standard-inheritance conversion used by the
    armature evaluator, with already-solved parent targets carried forward.
    """
    rest = pose_bone.bone.matrix_local
    if pose_bone.parent is None:
        return rest.inverted_safe() @ target
    parent_pose = solved_matrices.get(pose_bone.parent.name, pose_bone.parent.matrix.copy())
    parent_rest = pose_bone.parent.bone.matrix_local
    parent_to_bone = parent_pose @ parent_rest.inverted_safe() @ rest
    return parent_to_bone.inverted_safe() @ target


def solve_elbow(shoulder: Vector, wrist: Vector, upper_length: float, fore_length: float, hint: Vector) -> Vector:
    span = wrist - shoulder
    distance = min(upper_length + fore_length - 0.002, max(abs(upper_length - fore_length) + 0.002, span.length))
    axis = span.normalized()
    along = (upper_length * upper_length - fore_length * fore_length + distance * distance) / (2.0 * distance)
    height = math.sqrt(max(0.0, upper_length * upper_length - along * along))
    # `hint` is an armature-space elbow position, not a direction from the
    # global origin.  Projecting the absolute coordinate lifted both elbows
    # unnaturally above the rifle and pulled the gloves away from their grips.
    # Work in shoulder-relative space before removing the along-axis component.
    hint_vector = hint - shoulder
    bend = hint_vector - axis * hint_vector.dot(axis)
    if bend.length < 1e-5:
        bend = axis.cross(Vector((0.0, 0.0, 1.0)))
    return shoulder + axis * along + bend.normalized() * height


def arm_targets(
    side: str,
    wrist: tuple[float, float, float],
    hint: tuple[float, float, float],
    hand_direction: tuple[float, float, float],
) -> dict[str, tuple[Vector, Vector]]:
    """Solve a shoulder/elbow/wrist chain in armature space.

    Explicit targets keep the hands on the weapon or magazine through a clip;
    arbitrary Euler offsets were the main source of detached-looking elbows in
    earlier procedural enemy attempts.
    """
    shoulder = BONE_POINTS[f"upper_arm_{side}"][0]
    wrist_point = Vector(wrist)
    upper_length = (BONE_POINTS[f"upper_arm_{side}"][1] - shoulder).length
    fore_length = (BONE_POINTS[f"forearm_{side}"][1] - BONE_POINTS[f"forearm_{side}"][0]).length
    elbow = solve_elbow(shoulder, wrist_point, upper_length, fore_length, Vector(hint))
    hand_vector = Vector(hand_direction).normalized()
    hand_length = (BONE_POINTS[f"hand_{side}"][1] - BONE_POINTS[f"hand_{side}"][0]).length
    return {
        f"upper_arm_{side}": (shoulder, elbow),
        f"forearm_{side}": (elbow, wrist_point),
        f"hand_{side}": (wrist_point, wrist_point + hand_vector * hand_length),
    }


def left_arm_targets(wrist: tuple[float, float, float], hint: tuple[float, float, float]) -> dict[str, tuple[Vector, Vector]]:
    return arm_targets("l", wrist, hint, (0.075, 0.105, -0.020))


def weapon_target_point(head: Vector, tail: Vector, rest_point: tuple[float, float, float]) -> Vector:
    rest_head, rest_tail = BONE_POINTS["weapon"]
    rest_matrix = segment_matrix(rest_head, rest_tail)
    target_matrix = segment_matrix(head, tail)
    return target_matrix @ rest_matrix.inverted_safe() @ Vector(rest_point)


def firing_pose_segments(recoil: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> dict[str, tuple[Vector, Vector]]:
    """Absolute armature-space contacts for a shouldered sight picture.

    The weapon rises 0.265m from low-ready. Its extended stock terminates at the
    right shoulder pocket, the smoked optic sits below the dominant eye, the
    support elbow resolves below the handguard, and the firing elbow resolves
    naturally outboard.  All contacts derive from the authored hand lengths.
    """
    offset = Vector(recoil)
    # The rear control point moves to the firing-side shoulder while the muzzle
    # remains near centreline.  This diagonal is what makes the butt pad occupy
    # the right shoulder pocket instead of floating in front of the sternum.
    weapon_head = Vector((0.195, 0.370, 1.510)) + offset
    weapon_tail = Vector((0.000, 0.990, 1.525)) + offset
    # Contact the actual pistol grip and handguard geometry, not the weapon
    # control bone's endpoints.  The firing wrist sits high/rear of the grip so
    # the palm descends naturally around it while the support palm tracks the
    # underside/side of the handguard.
    right_contact = weapon_target_point(weapon_head, weapon_tail, (0.045, 0.535, 1.160))
    right_direction = Vector((-0.040, 0.060, -0.112)).normalized()
    right_length = (BONE_POINTS["hand_r"][1] - BONE_POINTS["hand_r"][0]).length
    right_wrist = right_contact - right_direction * right_length
    segments = arm_targets(
        "r",
        tuple(right_wrist),
        (0.52, 0.14, 1.23),
        tuple(right_direction),
    )

    left_contact = weapon_target_point(weapon_head, weapon_tail, (-0.035, 0.700, 1.245))
    left_direction = Vector((0.055, 0.110, -0.028)).normalized()
    left_length = (BONE_POINTS["hand_l"][1] - BONE_POINTS["hand_l"][0]).length
    left_wrist = left_contact - left_direction * left_length
    segments.update(
        arm_targets(
            "l",
            tuple(left_wrist),
            (-0.40, 0.30, 1.08),
            tuple(left_direction),
        )
    )
    # Override the child weapon matrix after the grip solve so hand roll cannot
    # tip the optic away from the dominant eye.
    segments["weapon"] = (weapon_head, weapon_tail)
    return segments


def low_ready_pose_segments(
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
    muzzle_lift: float = 0.0,
) -> dict[str, tuple[Vector, Vector]]:
    """Solve both hands onto the low-ready weapon for idle and locomotion.

    Earlier clips animated only the legs and spine, leaving a perfectly frozen
    rifle floating between moving sleeves.  This absolute contact solution
    keeps stock, pistol hand and support hand coherent while permitting a few
    millimetres of breathing/gait sway.
    """
    delta = Vector(offset)
    weapon_head = BONE_POINTS["weapon"][0] + delta
    weapon_tail = BONE_POINTS["weapon"][1] + delta + Vector((0.0, 0.0, muzzle_lift))

    right_contact = weapon_target_point(weapon_head, weapon_tail, (0.045, 0.535, 1.160))
    right_direction = Vector((-0.040, 0.060, -0.112)).normalized()
    right_length = (BONE_POINTS["hand_r"][1] - BONE_POINTS["hand_r"][0]).length
    right_wrist = right_contact - right_direction * right_length
    segments = arm_targets(
        "r",
        tuple(right_wrist),
        (0.47 + delta.x, 0.10 + delta.y, 1.20 + delta.z),
        tuple(right_direction),
    )

    left_contact = weapon_target_point(weapon_head, weapon_tail, (-0.035, 0.700, 1.245))
    left_direction = Vector((0.055, 0.105, -0.026)).normalized()
    left_length = (BONE_POINTS["hand_l"][1] - BONE_POINTS["hand_l"][0]).length
    left_wrist = left_contact - left_direction * left_length
    segments.update(
        arm_targets(
            "l",
            tuple(left_wrist),
            (-0.43 + delta.x, 0.25 + delta.y, 1.08 + delta.z),
            tuple(left_direction),
        )
    )
    segments["weapon"] = (weapon_head, weapon_tail)
    return segments


def reload_pose_segments(
    magazine_head: tuple[float, float, float],
    magazine_tail: tuple[float, float, float],
    hand_contact: tuple[float, float, float],
    elbow_hint: tuple[float, float, float],
) -> dict[str, tuple[Vector, Vector]]:
    """Keep the support glove physically wrapped around the moving magazine."""
    contact = Vector(hand_contact)
    # The wrist approaches from below/outboard and the palm rises along the
    # magazine.  V2-H pointed the hand bone downward, leaving a dangling glove
    # under the magazine even though the numeric contact itself passed.
    hand_direction = Vector((0.060, 0.045, 0.105)).normalized()
    hand_length = (BONE_POINTS["hand_l"][1] - BONE_POINTS["hand_l"][0]).length
    wrist = contact - hand_direction * hand_length
    segments = arm_targets("l", tuple(wrist), elbow_hint, tuple(hand_direction))
    segments["magazine"] = (Vector(magazine_head), Vector(magazine_tail))
    return segments


def reload_sequence_segments(
    magazine_head: tuple[float, float, float],
    magazine_tail: tuple[float, float, float],
    hand_contact: tuple[float, float, float],
    elbow_hint: tuple[float, float, float],
    weapon_cant: float = 1.0,
) -> dict[str, tuple[Vector, Vector]]:
    """Cant the rifle for inspection while both glove contacts stay solved.

    The earlier clip kept the rifle aimed squarely at the viewer for all 48
    frames.  Although its numeric hand contacts passed, the pose read as a
    mannequin holding a floating magazine.  This creates a restrained inward
    roll/downward muzzle arc around the shoulder, then solves the firing wrist
    back onto the transformed pistol grip before the support-hand magazine
    contact is applied.
    """
    amount = min(1.0, max(0.0, weapon_cant))
    rest_head, rest_tail = BONE_POINTS["weapon"]
    # Keep the butt/receiver tight to the torso and rotate the muzzle inward;
    # the previous target sat 10–15cm too far forward and straightened both
    # arms into a synthetic reach pose.
    canted_head = Vector((0.182, 0.302, 1.372))
    canted_tail = Vector((-0.082, 0.884, 1.278))
    weapon_head = rest_head.lerp(canted_head, amount)
    weapon_tail = rest_tail.lerp(canted_tail, amount)

    # Transform the authored glove direction with the rifle basis so palm roll
    # follows the grip instead of remaining world-aligned during the cant.
    rest_basis = segment_matrix(rest_head, rest_tail).to_3x3()
    target_basis = segment_matrix(weapon_head, weapon_tail).to_3x3()
    grip_direction = (
        target_basis
        @ rest_basis.inverted_safe()
        @ Vector((-0.040, 0.060, -0.112)).normalized()
    ).normalized()
    grip_contact = weapon_target_point(weapon_head, weapon_tail, (0.045, 0.535, 1.160))
    hand_length = (BONE_POINTS["hand_r"][1] - BONE_POINTS["hand_r"][0]).length
    grip_wrist = grip_contact - grip_direction * hand_length
    segments = arm_targets(
        "r",
        tuple(grip_wrist),
        (0.48, 0.035, 1.24),
        tuple(grip_direction),
    )
    segments["weapon"] = (weapon_head, weapon_tail)
    segments.update(reload_pose_segments(magazine_head, magazine_tail, hand_contact, elbow_hint))
    return segments


def create_action(
    armature: bpy.types.Object,
    name: str,
    frames: list[dict[str, Any]],
) -> bpy.types.Action:
    action = bpy.data.actions.new(name=name)
    action.use_fake_user = True
    if armature.animation_data is None:
        armature.animation_data_create()
    animated_bones = sorted(
        {
            bone
            for frame in frames
            for channel in (frame.get("rot", {}), frame.get("loc", {}), frame.get("segments", {}))
            for bone in channel
        }
    )
    baked_frames: list[tuple[int, dict[str, tuple[Vector, Vector, Vector]]]] = []
    for frame in frames:
        frame_number = int(frame["frame"])
        # Solve with animation evaluation detached.  Updating a view layer while
        # the partially-authored action is active lets Blender re-apply earlier
        # F-curves and corrupt an otherwise exact arm/magazine contact pose.
        armature.animation_data.action = None
        bpy.context.scene.frame_set(frame_number)
        clear_pose(armature)
        for bone_name in animated_bones:
            pose_bone = armature.pose.bones[bone_name]
            pose_bone.rotation_euler = frame.get("rot", {}).get(bone_name, (0.0, 0.0, 0.0))
            pose_bone.location = frame.get("loc", {}).get(bone_name, (0.0, 0.0, 0.0))
            pose_bone.scale = (1.0, 1.0, 1.0)
        # Resolve ordinary parent rotations before imposing armature-space
        # segment matrices on the connected limb chains.
        bpy.context.view_layer.update()
        solved_matrices: dict[str, Matrix] = {}
        for bone_name, (head, tail) in frame.get("segments", {}).items():
            target = segment_matrix(Vector(head), Vector(tail))
            pose_bone = armature.pose.bones[bone_name]
            pose_bone.matrix_basis = segment_basis(pose_bone, target, solved_matrices)
            solved_matrices[bone_name] = target
        bpy.context.view_layer.update()
        baked_frames.append(
            (
                frame_number,
                {
                    bone_name: (
                        armature.pose.bones[bone_name].rotation_euler.copy(),
                        armature.pose.bones[bone_name].location.copy(),
                        armature.pose.bones[bone_name].scale.copy(),
                    )
                    for bone_name in animated_bones
                },
            )
        )

    armature.animation_data.action = action
    for frame_number, pose_values in baked_frames:
        bpy.context.scene.frame_set(frame_number)
        for bone_name in animated_bones:
            pose_bone = armature.pose.bones[bone_name]
            rotation, location, scale = pose_values[bone_name]
            pose_bone.rotation_euler = rotation
            pose_bone.location = location
            pose_bone.scale = scale
            pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame_number, group=bone_name)
            pose_bone.keyframe_insert(data_path="location", frame=frame_number, group=bone_name)
            pose_bone.keyframe_insert(data_path="scale", frame=frame_number, group=bone_name)
    try:
        for curve in action.fcurves:
            for keyframe in curve.keyframe_points:
                keyframe.interpolation = "BEZIER"
    except AttributeError:
        pass
    bpy.context.scene.frame_set(1)
    return action


def locomotion_frames(direction: str, run: bool = False) -> list[dict[str, Any]]:
    amplitude = 34.0 if run else 23.0
    if direction == "backward":
        amplitude *= -0.72
    side = -1.0 if direction == "left" else 1.0
    frames = []
    for frame, phase in ((1, 0.0), (8 if run else 10, math.pi / 2), (15 if run else 19, math.pi), (22 if run else 28, math.pi * 1.5), (29 if run else 37, math.tau)):
        swing = math.sin(phase) * amplitude
        lift_l = max(0.0, math.sin(phase))
        lift_r = max(0.0, -math.sin(phase))
        rotations = {
            "thigh_l": rot(swing),
            "thigh_r": rot(-swing),
            "shin_l": rot(-lift_l * (52.0 if run else 35.0)),
            "shin_r": rot(-lift_r * (52.0 if run else 35.0)),
            "spine_01": rot(-6.0 if run else -2.0, 0.0, math.sin(phase) * 2.0),
            "head": rot(2.0 if run else 0.0, 0.0, -math.sin(phase) * 1.5),
        }
        locations = {"root": (0.0, 0.0, abs(math.sin(phase)) * (0.045 if run else 0.025))}
        if direction in {"left", "right"}:
            rotations["thigh_l"] = rot(swing * 0.40, 0.0, side * 10.0 * math.sin(phase))
            rotations["thigh_r"] = rot(-swing * 0.40, 0.0, side * 10.0 * math.sin(phase + math.pi))
            rotations["spine_01"] = rot(-2.0, 0.0, -side * 3.5)
        weapon_sway = math.sin(phase) * (0.010 if run else 0.006)
        weapon_bob = abs(math.sin(phase)) * (0.012 if run else 0.007)
        segments = low_ready_pose_segments(
            (weapon_sway, 0.0, weapon_bob),
            muzzle_lift=math.cos(phase) * (0.008 if run else 0.004),
        )
        frames.append({"frame": frame, "rot": rotations, "loc": locations, "segments": segments})
    return frames


def create_actions(armature: bpy.types.Object) -> dict[str, bpy.types.Action]:
    actions: dict[str, bpy.types.Action] = {}
    specs = {
        "AN_Soldier_Idle": [
            {"frame": 1, "rot": {"spine_01": rot(-1.0), "spine_02": rot(0.6), "head": rot(0, 0, -1.0)}, "segments": low_ready_pose_segments()},
            {"frame": 45, "rot": {"spine_01": rot(0.7), "spine_02": rot(-0.5), "head": rot(0, 0, 1.2)}, "loc": {"root": (0, 0, 0.008)}, "segments": low_ready_pose_segments((0.003, 0.0, 0.008), 0.003)},
            {"frame": 90, "rot": {"spine_01": rot(-1.0), "spine_02": rot(0.6), "head": rot(0, 0, -1.0)}, "segments": low_ready_pose_segments()},
        ],
        "AN_Soldier_RifleReady": [
            {"frame": 1, "rot": {"spine_02": rot(-1.0), "head": rot(1.0)}, "segments": low_ready_pose_segments()},
            {"frame": 30, "rot": {"spine_02": rot(-2.0), "head": rot(2.0)}, "segments": low_ready_pose_segments((0.0, 0.008, 0.026), 0.035)},
        ],
        "AN_Soldier_Aim": [
            {
                "frame": 1,
                "rot": combat_pose_rot(-7.0, 2.0),
                "segments": firing_pose_with_stance(),
            },
            {
                "frame": 16,
                # Sub-perceptual breathing keeps the sight picture alive
                # without the irritating lateral dodge motion removed from AI.
                "rot": combat_pose_rot(-6.7, 1.7),
                "segments": firing_pose_with_stance((0.0012, 0.0018, 0.0015)),
            },
            {
                "frame": 28,
                "rot": combat_pose_rot(-7.0, 2.0),
                "segments": firing_pose_with_stance(),
            },
        ],
        "AN_Soldier_Fire": [
            {
                "frame": 1,
                "rot": combat_pose_rot(-7.0, 2.0),
                "segments": firing_pose_with_stance(),
            },
            {
                "frame": 3,
                "rot": combat_pose_rot(-6.0, 1.0),
                "segments": firing_pose_with_stance((0.0, -0.022, 0.010)),
            },
            {
                "frame": 6,
                "rot": combat_pose_rot(-7.5, 2.5),
                "segments": firing_pose_with_stance((0.0, 0.006, -0.003)),
            },
            {
                "frame": 10,
                "rot": combat_pose_rot(-7.0, 2.0),
                "segments": firing_pose_with_stance(),
            },
        ],
        "AN_Soldier_Reload": [
            {"frame": 1, "segments": low_ready_pose_segments()},
            {
                "frame": 10,
                "rot": {"spine_02": rot(0), "head": rot(3.0)},
                "segments": reload_sequence_segments(
                    (0.020, 0.520, 1.200),
                    (0.020, 0.460, 1.060),
                    (-0.045, 0.490, 1.125),
                    (-0.55, 0.12, 1.12),
                    0.42,
                ),
            },
            {
                "frame": 18,
                "rot": {"head": rot(5.0, 0.0, -2.5)},
                "segments": reload_sequence_segments(
                    (-0.020, 0.440, 1.130),
                    (-0.055, 0.350, 0.990),
                    (-0.070, 0.395, 1.055),
                    (-0.58, 0.15, 1.05),
                    0.82,
                ),
            },
            {
                "frame": 28,
                "rot": {"spine_02": rot(0), "head": rot(7.0, 0.0, -4.0)},
                "segments": reload_sequence_segments(
                    (-0.075, 0.300, 1.020),
                    (-0.140, 0.180, 0.910),
                    (-0.115, 0.235, 0.965),
                    (-0.57, 0.09, 0.98),
                    1.0,
                ),
            },
            {
                "frame": 38,
                "rot": {"head": rot(4.0, 0.0, -1.0)},
                "segments": reload_sequence_segments(
                    (-0.020, 0.460, 1.150),
                    (-0.025, 0.390, 1.000),
                    (-0.070, 0.420, 1.065),
                    (-0.55, 0.13, 1.08),
                    0.62,
                ),
            },
            {"frame": 48, "segments": low_ready_pose_segments()},
        ],
        "AN_Soldier_HitFront": [
            {"frame": 1, "rot": {"root": rot(0), "neck": rot(0), "head": rot(0)}},
            {
                "frame": 4,
                "rot": {"root": rot(6, 0, -1.5), "neck": rot(-5), "head": rot(-7)},
                "loc": {"root": (0, -0.018, 0.006)},
            },
            {"frame": 12, "rot": {"root": rot(0), "neck": rot(0), "head": rot(0)}},
        ],
        "AN_Soldier_HitBack": [
            {"frame": 1, "rot": {"root": rot(0), "neck": rot(0), "head": rot(0)}},
            {
                "frame": 4,
                "rot": {"root": rot(-6, 0, 1.5), "neck": rot(5), "head": rot(7)},
                "loc": {"root": (0, 0.018, 0.006)},
            },
            {"frame": 12, "rot": {"root": rot(0), "neck": rot(0), "head": rot(0)}},
        ],
        "AN_Soldier_DeathFront": [
            {"frame": 1, "rot": {"root": rot(0), "spine_01": rot(0)}},
            {"frame": 10, "rot": {"thigh_l": rot(28), "thigh_r": rot(20), "shin_l": rot(-38), "shin_r": rot(-32), "spine_01": rot(12)}, "loc": {"root": (0, 0.02, -0.18)}},
            {"frame": 22, "rot": {"root": rot(72, 0, -8), "spine_01": rot(18), "head": rot(-20)}, "loc": {"root": (0, 0.18, -0.55)}},
            {"frame": 32, "rot": {"root": rot(88, 0, -10), "spine_01": rot(18), "head": rot(-20)}, "loc": {"root": (0, 0.38, -0.58)}},
        ],
        "AN_Soldier_DeathBack": [
            {"frame": 1, "rot": {"root": rot(0), "spine_01": rot(0)}},
            {"frame": 10, "rot": {"thigh_l": rot(-18), "thigh_r": rot(-22), "spine_01": rot(-15)}, "loc": {"root": (0, 0.03, -0.04)}},
            {
                "frame": 22,
                "rot": {"root": rot(-70, 0, 12), "spine_01": rot(-18), "head": rot(18), "weapon": rot(55)},
                "loc": {"root": (0, 0.26, 0.27)},
            },
            {
                "frame": 32,
                "rot": {"root": rot(-88, 0, 12), "spine_01": rot(-18), "head": rot(18), "weapon": rot(88)},
                "loc": {"root": (0, 0.58, 0.59)},
            },
        ],
    }
    specs["AN_Soldier_WalkForward"] = locomotion_frames("forward")
    specs["AN_Soldier_WalkBackward"] = locomotion_frames("backward")
    specs["AN_Soldier_StrafeLeft"] = locomotion_frames("left")
    specs["AN_Soldier_StrafeRight"] = locomotion_frames("right")
    specs["AN_Soldier_RunForward"] = locomotion_frames("forward", run=True)
    for name in REQUIRED_ANIMATIONS:
        actions[name] = create_action(armature, name, specs[name])
    armature.animation_data.action = actions["AN_Soldier_RifleReady"]
    return actions


def audit_actions(armature: bpy.types.Object, actions: dict[str, bpy.types.Action]) -> dict[str, Any]:
    cases = {
        "AN_Soldier_Idle": (1, 45, 90),
        "AN_Soldier_RifleReady": (1, 15, 30),
        "AN_Soldier_Aim": (1, 16, 28),
        "AN_Soldier_Fire": (1, 3, 10),
        "AN_Soldier_Reload": (1, 10, 18, 28, 38, 48),
        "AN_Soldier_WalkForward": (1, 10, 19, 28),
        "AN_Soldier_WalkBackward": (1, 10, 19, 28),
        "AN_Soldier_StrafeLeft": (1, 10, 19, 28),
        "AN_Soldier_StrafeRight": (1, 10, 19, 28),
        "AN_Soldier_RunForward": (1, 8, 15, 22, 29),
        "AN_Soldier_HitFront": (1, 4, 12),
        "AN_Soldier_HitBack": (1, 4, 12),
        "AN_Soldier_DeathFront": (1, 10, 22, 32),
        "AN_Soldier_DeathBack": (1, 10, 22, 32),
    }
    errors: list[str] = []
    samples = 0
    for action_name, frames in cases.items():
        for frame in frames:
            armature.animation_data.action = None
            clear_pose(armature)
            armature.animation_data.action = actions[action_name]
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            samples += 1
            for bone_name in BONE_POINTS:
                bone = armature.pose.bones[bone_name]
                values = (*bone.head, *bone.tail)
                if not all(math.isfinite(value) for value in values):
                    errors.append(f"{action_name}:{frame}:{bone_name}:non-finite")
                rest_length = (BONE_POINTS[bone_name][1] - BONE_POINTS[bone_name][0]).length
                if abs((bone.tail - bone.head).length - rest_length) > 0.002:
                    errors.append(f"{action_name}:{frame}:{bone_name}:length")
            if action_name not in {"AN_Soldier_DeathFront", "AN_Soldier_DeathBack"}:
                weapon = armature.pose.bones["weapon"]
                weapon_axis = (weapon.tail - weapon.head).normalized()
                # Hibana's authored forward direction is Blender +Y. A rifle
                # pointing vertically or backwards is always a bad parent/local
                # transform, even if every bone retains its nominal length.
                if weapon_axis.y < 0.78 or abs(weapon_axis.z) > 0.42:
                    errors.append(
                        f"{action_name}:{frame}:weapon-axis:"
                        f"{weapon_axis.x:.3f},{weapon_axis.y:.3f},{weapon_axis.z:.3f}"
                    )
            if action_name in {"AN_Soldier_Aim", "AN_Soldier_Fire"}:
                weapon = armature.pose.bones["weapon"]
                weapon_delta = weapon.matrix @ weapon.bone.matrix_local.inverted_safe()
                right_grip = armature.pose.bones["hand_r"].tail
                right_contact = weapon_delta @ Vector((0.045, 0.535, 1.160))
                if (right_grip - right_contact).length > 0.13:
                    errors.append(f"{action_name}:{frame}:right-grip:{(right_grip - right_contact).length:.3f}")
                left_grip = armature.pose.bones["hand_l"].tail
                left_contact = weapon_delta @ Vector((-0.035, 0.700, 1.245))
                if (left_grip - left_contact).length > 0.15:
                    errors.append(f"{action_name}:{frame}:left-grip:{(left_grip - left_contact).length:.3f}")
                butt = weapon_delta @ Vector((0.020, 0.030, 1.245))
                shoulder_pocket = Vector((0.190, 0.015, 1.470))
                if (butt - shoulder_pocket).length > 0.10:
                    errors.append(f"{action_name}:{frame}:stock-shoulder:{(butt - shoulder_pocket).length:.3f}")
                head = armature.pose.bones["head"]
                head_delta = head.matrix @ head.bone.matrix_local.inverted_safe()
                dominant_eye = head_delta @ Vector((0.040, 0.105, 1.708))
                optic = weapon_delta @ Vector((0.020, 0.650, 1.385))
                sight_error = Vector((dominant_eye.x - optic.x, 0.0, dominant_eye.z - optic.z)).length
                if sight_error > 0.10:
                    errors.append(f"{action_name}:{frame}:optic-eye:{sight_error:.3f}")
                cheek = head_delta @ Vector((0.080, 0.070, 1.625))
                comb = weapon_delta @ Vector((0.020, 0.160, 1.330))
                if (cheek - comb).length > 0.16:
                    errors.append(f"{action_name}:{frame}:cheek-stock:{(cheek - comb).length:.3f}")
            if action_name in {
                "AN_Soldier_Idle",
                "AN_Soldier_RifleReady",
                "AN_Soldier_WalkForward",
                "AN_Soldier_WalkBackward",
                "AN_Soldier_StrafeLeft",
                "AN_Soldier_StrafeRight",
                "AN_Soldier_RunForward",
                "AN_Soldier_Reload",
            }:
                weapon = armature.pose.bones["weapon"]
                weapon_delta = weapon.matrix @ weapon.bone.matrix_local.inverted_safe()
                sides = ("r",) if action_name == "AN_Soldier_Reload" and frame not in {1, 48} else ("r", "l")
                contacts = {
                    "r": Vector((0.045, 0.535, 1.160)),
                    "l": Vector((-0.035, 0.700, 1.245)),
                }
                for side in sides:
                    hand_tail = armature.pose.bones[f"hand_{side}"].tail
                    contact = weapon_delta @ contacts[side]
                    tolerance = 0.060 if side == "r" else 0.070
                    if (hand_tail - contact).length > tolerance:
                        errors.append(
                            f"{action_name}:{frame}:{side}-low-ready-contact:"
                            f"{(hand_tail - contact).length:.3f}"
                        )
            if action_name in {"AN_Soldier_HitFront", "AN_Soldier_HitBack"}:
                # Hit reactions move the common root, so the low-ready hand-to-
                # weapon spacing must remain invariant even while the head
                # whips independently.  This rejects the previous torso-only
                # recoil that visibly left the rifle floating between hands.
                weapon = armature.pose.bones["weapon"]
                weapon_delta = weapon.matrix @ weapon.bone.matrix_local.inverted_safe()
                for side, rest_contact in (
                    ("r", (0.045, 0.535, 1.160)),
                    ("l", (-0.035, 0.700, 1.245)),
                ):
                    hand = armature.pose.bones[f"hand_{side}"].tail
                    contact = weapon_delta @ Vector(rest_contact)
                    rest_distance = (BONE_POINTS[f"hand_{side}"][1] - Vector(rest_contact)).length
                    drift = abs((hand - contact).length - rest_distance)
                    if drift > 0.004:
                        errors.append(f"{action_name}:{frame}:{side}-grip-drift:{drift:.3f}")
            if action_name in {
                "AN_Soldier_Idle",
                "AN_Soldier_Aim",
                "AN_Soldier_Fire",
                "AN_Soldier_Reload",
                "AN_Soldier_HitFront",
                "AN_Soldier_HitBack",
            }:
                foot_separation = abs(armature.pose.bones["foot_l"].head.x - armature.pose.bones["foot_r"].head.x)
                if foot_separation < 0.16:
                    errors.append(f"{action_name}:{frame}:feet-overlap:{foot_separation:.3f}")
            if action_name == "AN_Soldier_Reload" and frame in {10, 18, 28, 38}:
                hand = armature.pose.bones["hand_l"].tail
                magazine = armature.pose.bones["magazine"]
                axis = magazine.tail - magazine.head
                along = min(1.0, max(0.0, (hand - magazine.head).dot(axis) / axis.length_squared))
                contact = magazine.head + axis * along
                if (hand - contact).length > 0.14:
                    errors.append(f"{action_name}:{frame}:hand-magazine:{(hand - contact).length:.3f}")
    armature.animation_data.action = None
    clear_pose(armature)
    armature.animation_data.action = actions["AN_Soldier_RifleReady"]
    if errors:
        raise RuntimeError("animation-audit:" + ";".join(errors[:12]))
    return {"samples": samples, "errors": errors}


def audit_death_ground_contact(
    armature: bpy.types.Object,
    meshes: list[bpy.types.Object],
    actions: dict[str, bpy.types.Action],
) -> dict[str, Any]:
    """Reject final death poses that float or bury the soldier under terrain."""
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for action_name in ("AN_Soldier_DeathFront", "AN_Soldier_DeathBack"):
        armature.animation_data.action = None
        clear_pose(armature)
        armature.animation_data.action = actions[action_name]
        bpy.context.scene.frame_set(32)
        bpy.context.view_layer.update()
        for mesh in meshes:
            evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
            evaluated_mesh = evaluated.to_mesh()
            points = [evaluated.matrix_world @ vertex.co for vertex in evaluated_mesh.vertices]
            point_rows: list[tuple[int, Vector, tuple[str, ...]]] = []
            body_rows: list[tuple[int, Vector, tuple[str, ...]]] = []
            for index, point in enumerate(points):
                groups = tuple(sorted({
                    mesh.vertex_groups[group.group].name
                    for group in mesh.data.vertices[index].groups
                }))
                point_rows.append((index, point, groups))
                if set(groups) - {"weapon", "magazine"}:
                    body_rows.append((index, point, groups))
            evaluated.to_mesh_clear()
            overall_index, overall_point, overall_groups = min(point_rows, key=lambda row: row[1].z)
            body_index, body_point, body_groups = min(body_rows, key=lambda row: row[1].z)
            overall_local = mesh.data.vertices[overall_index].co
            body_local = mesh.data.vertices[body_index].co
            overall_min = overall_point.z
            body_min = body_point.z
            rows.append(
                {
                    "action": action_name,
                    "variant": mesh.get("variantId", mesh.name),
                    "overallMinZ": round(overall_min, 4),
                    "bodyMinZ": round(body_min, 4),
                    "overallMinVertex": overall_index,
                    "overallMinPoint": [round(value, 4) for value in overall_point],
                    "overallMinLocalPoint": [round(value, 4) for value in overall_local],
                    "overallMinGroups": list(overall_groups),
                    "bodyMinVertex": body_index,
                    "bodyMinPoint": [round(value, 4) for value in body_point],
                    "bodyMinLocalPoint": [round(value, 4) for value in body_local],
                    "bodyMinGroups": list(body_groups),
                }
            )
            if not -0.06 <= overall_min <= 0.08:
                errors.append(
                    f"{action_name}:{mesh.name}:overall-ground:{overall_min:.3f}:"
                    f"v{overall_index}:point={tuple(round(value, 3) for value in overall_point)}:"
                    f"local={tuple(round(value, 3) for value in overall_local)}:"
                    f"groups={','.join(overall_groups)}"
                )
            if not -0.03 <= body_min <= 0.08:
                errors.append(
                    f"{action_name}:{mesh.name}:body-ground:{body_min:.3f}:"
                    f"v{body_index}:point={tuple(round(value, 3) for value in body_point)}:"
                    f"local={tuple(round(value, 3) for value in body_local)}:"
                    f"groups={','.join(body_groups)}"
                )
    armature.animation_data.action = None
    clear_pose(armature)
    armature.animation_data.action = actions["AN_Soldier_RifleReady"]
    if errors:
        raise RuntimeError("death-ground-audit:" + ";".join(errors[:12]))
    return {"samples": len(rows), "errors": errors, "poses": rows}


def triangle_count(obj: bpy.types.Object) -> int:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    count = len(mesh.loop_triangles)
    evaluated.to_mesh_clear()
    return count


def build_pack(lod: int) -> tuple[bpy.types.Object, list[bpy.types.Object], dict[str, bpy.types.Action], dict[str, Any]]:
    clear_generated()
    root_collection = new_collection(f"{PREFIX}SOLDIER_PACK_ROOT")
    rig_collection = new_collection(f"{PREFIX}10_RIG", root_collection)
    geo_collection = new_collection(f"{PREFIX}20_GEO_LOD{lod}", root_collection)
    export_collection = new_collection(f"{PREFIX}90_EXPORT", root_collection)
    materials = create_materials()
    armature = create_armature(rig_collection)
    root = bpy.data.objects.new(f"{PREFIX}EnemyPack_ROOT", None)
    export_collection.objects.link(root)
    root["hibanaAssetType"] = "enemy-soldier-pack"
    root["packVersion"] = 1
    root["lod"] = lod
    root["variantCount"] = len(VARIANTS)
    root["referenceSourceIncluded"] = False
    armature.parent = root
    # Link the armature into export without unlinking its authoring collection.
    export_collection.objects.link(armature)
    meshes = []
    for index, variant in enumerate(VARIANTS):
        mesh = build_variant(index, variant, lod, geo_collection, armature, materials)
        export_collection.objects.link(mesh)
        meshes.append(mesh)
    actions = create_actions(armature)
    animation_audit = audit_actions(armature, actions)
    ground_contact_audit = audit_death_ground_contact(armature, meshes, actions)
    metrics = {
        "lod": lod,
        "triangles": sum(triangle_count(mesh) for mesh in meshes),
        "vertices": sum(len(mesh.data.vertices) for mesh in meshes),
        "materials": len(materials),
        "variants": len(meshes),
        "bones": len(armature.data.bones),
        "animations": len(actions),
        "animationAudit": animation_audit,
        "groundContactAudit": ground_contact_audit,
    }
    return armature, meshes, actions, metrics


def export_pack(lod: int, armature: bpy.types.Object, meshes: list[bpy.types.Object]) -> Path:
    output = OUTPUT_DIR / f"soldier-pack-lod{lod}.glb"
    bpy.ops.object.select_all(action="DESELECT")
    selected = [armature, armature.parent, *meshes]
    for obj in selected:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = armature
    kwargs: dict[str, Any] = {
        "filepath": str(output),
        "export_format": "GLB",
        "use_selection": True,
        # Applying transforms in the exporter can change armature rest matrices.
        # Authoring transforms are already identity, so keep this disabled.
        "export_apply": False,
        "export_yup": True,
        "export_cameras": False,
        "export_lights": False,
        "export_extras": True,
        "export_skins": True,
        "export_animations": True,
        "export_animation_mode": "ACTIONS",
        "export_force_sampling": True,
        "export_def_bones": True,
        "export_optimize_animation_size": True,
        "export_tangents": True,
        "export_morph": False,
    }
    supported = {prop.identifier for prop in bpy.ops.export_scene.gltf.get_rna_type().properties}
    kwargs = {key: value for key, value in kwargs.items() if key in supported}
    bpy.ops.export_scene.gltf(**kwargs)
    return output


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_qa_scene() -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    # Factory-startup includes a cube at the character origin.  Keep unrelated
    # objects intact, but exclude them from this isolated QA render.
    for obj in bpy.context.scene.objects:
        if not obj.name.startswith((PREFIX, "SM_Enemy_", "ARM_Enemy_")):
            obj.hide_render = True
    qa_collection = new_collection(f"{PREFIX}80_QA")
    floor_mesh = bpy.data.meshes.new(f"{PREFIX}QA_Floor")
    floor_mesh.from_pydata(
        [(-3.0, -2.0, 0.0), (3.0, -2.0, 0.0), (3.0, 3.0, 0.0), (-3.0, 3.0, 0.0)],
        [],
        [(0, 1, 2, 3)],
    )
    floor = bpy.data.objects.new(f"{PREFIX}QA_Floor", floor_mesh)
    qa_collection.objects.link(floor)
    floor.data.materials.append(make_material("MAT_Enemy_QAFloor", hex_rgb("#222722"), 0.82))
    camera_data = bpy.data.cameras.new(f"{PREFIX}QA_CAMERA")
    camera = bpy.data.objects.new(f"{PREFIX}QA_CAMERA", camera_data)
    qa_collection.objects.link(camera)
    # Soldier faces Blender +Y (glTF -Z), so camera is on the +Y/front side.
    camera.location = (2.65, 4.8, 2.25)
    camera.data.lens = 58
    look_at(camera, Vector((0.0, 0.08, 0.98)))
    lights = []
    for name, location, energy, color, size in (
        ("KEY", (-2.4, 3.0, 4.2), 950.0, (1.0, 0.88, 0.75), 2.2),
        ("FILL", (2.8, 1.8, 2.6), 520.0, (0.62, 0.76, 1.0), 2.8),
        ("RIM", (0.5, -2.6, 3.4), 780.0, (0.75, 0.86, 1.0), 1.7),
    ):
        data = bpy.data.lights.new(f"{PREFIX}LGT_{name}", type="AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(f"{PREFIX}LGT_{name}", data)
        qa_collection.objects.link(light)
        light.location = location
        look_at(light, Vector((0.0, 0.0, 1.0)))
        lights.append(light)
    scene = bpy.context.scene
    scene.camera = camera
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 100
    scene.render.use_file_extension = True
    scene.render.image_settings.color_depth = "8"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.world.use_nodes = True
    background = next(
        (node for node in scene.world.node_tree.nodes if node.bl_idname == "ShaderNodeBackground"),
        None,
    )
    if background:
        background.inputs["Color"].default_value = (0.018, 0.025, 0.022, 1.0)
        background.inputs["Strength"].default_value = 0.22
    return camera, [floor, *lights]


def render_qa(
    armature: bpy.types.Object,
    meshes: list[bpy.types.Object],
    actions: dict[str, bpy.types.Action],
) -> list[str]:
    camera, _qa_objects = setup_qa_scene()
    scene = bpy.context.scene
    rendered: list[str] = []

    camera_views = {
        "hero": ((2.65, 4.8, 2.25), (0.0, 0.08, 0.98), 58),
        "rear": ((-2.35, -4.55, 2.18), (0.0, -0.04, 1.02), 58),
        "front": ((0.0, 4.4, 1.68), (0.0, 0.08, 0.96), 64),
        "side": ((4.4, 0.24, 1.68), (0.0, 0.08, 0.96), 64),
        "grip": ((1.55, 2.35, 1.62), (0.0, 0.47, 1.25), 76),
        "support_grip": ((-1.55, 2.35, 1.62), (0.0, 0.60, 1.25), 76),
        "joints": ((0.0, 3.0, 0.62), (0.0, 0.06, 0.46), 78),
        "shoulder": ((2.35, 0.28, 1.62), (0.10, 0.12, 1.47), 82),
        "stock": ((2.10, -1.62, 1.72), (0.15, 0.13, 1.49), 86),
        "head": ((0.62, 1.35, 1.82), (0.0, 0.045, 1.675), 92),
        # Level, centred inspection prevents a high three-quarter camera from
        # falsely hiding a boonie/hood eye opening or flattering mask depth.
        "head_front": ((0.0, 1.30, 1.695), (0.0, 0.060, 1.695), 96),
        "fall": ((4.9, 5.9, 3.5), (0.0, -0.28, 0.42), 46),
        "fall_back": ((-4.9, -5.9, 3.5), (0.0, 0.58, 0.42), 46),
    }

    def render_one(
        filename: str,
        variant_index: int,
        action_name: str,
        frame: int,
        camera_view: str = "hero",
    ) -> None:
        for index, mesh in enumerate(meshes):
            mesh.hide_render = index != variant_index
            mesh.hide_viewport = index != variant_index
        # Actions intentionally contain only the channels they need. Reset
        # unkeyed bones so a prior gait/death preview cannot leak into reload.
        armature.animation_data.action = None
        clear_pose(armature)
        armature.animation_data.action = actions[action_name]
        scene.frame_set(frame)
        location, target, lens = camera_views[camera_view]
        camera.location = location
        camera.data.lens = lens
        look_at(camera, Vector(target))
        target = SCREENSHOT_DIR / filename
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        try:
            rendered.append(str(target.relative_to(PROJECT)))
        except ValueError:
            rendered.append(str(target))

    for index, variant in enumerate(VARIANTS):
        render_one(f"enemy-{variant['id']}-aim.png", index, "AN_Soldier_Aim", 24)
        render_one(f"enemy-{variant['id']}-aim-rear.png", index, "AN_Soldier_Aim", 24, "rear")
    for frame in (1, 10, 18, 28, 38, 48):
        render_one(f"enemy-rifleman-reload-{frame:02d}.png", 0, "AN_Soldier_Reload", frame)
    for frame in (1, 10, 19, 28):
        render_one(f"enemy-rifleman-walk-{frame:02d}.png", 0, "AN_Soldier_WalkForward", frame)
    render_one("enemy-rifleman-fire.png", 0, "AN_Soldier_Fire", 3)
    render_one("enemy-rifleman-death.png", 0, "AN_Soldier_DeathFront", 32, "fall")
    # Stable orthographic-like comparisons for article and ship/no-ship review.
    # Front/side views expose silhouette defects hidden by the hero angle;
    # close grip views make finger-to-weapon contact auditable.
    for action_label, action_name, frame in (
        ("aim", "AN_Soldier_Aim", 24),
        ("fire", "AN_Soldier_Fire", 3),
        ("reload", "AN_Soldier_Reload", 28),
    ):
        render_one(f"enemy-rifleman-{action_label}-front.png", 0, action_name, frame, "front")
        render_one(f"enemy-rifleman-{action_label}-side.png", 0, action_name, frame, "side")
    render_one("enemy-rifleman-aim-grip-close.png", 0, "AN_Soldier_Aim", 24, "grip")
    render_one("enemy-rifleman-aim-support-grip-close.png", 0, "AN_Soldier_Aim", 24, "support_grip")
    render_one("enemy-rifleman-reload-grip-close.png", 0, "AN_Soldier_Reload", 28, "grip")
    render_one("enemy-rifleman-aim-joints-close.png", 0, "AN_Soldier_Aim", 24, "joints")
    render_one("enemy-rifleman-walk-joints-close.png", 0, "AN_Soldier_WalkForward", 10, "joints")
    render_one("enemy-rifleman-aim-shoulder-close.png", 0, "AN_Soldier_Aim", 24, "shoulder")
    render_one("enemy-rifleman-aim-stock-contact-close.png", 0, "AN_Soldier_Aim", 24, "stock")
    render_one("enemy-rifleman-aim-head-close.png", 0, "AN_Soldier_Aim", 24, "head")
    render_one("enemy-scout-aim-head-close.png", 2, "AN_Soldier_Aim", 24, "head")
    render_one("enemy-marksman-aim-head-close.png", 3, "AN_Soldier_Aim", 24, "head")
    render_one("enemy-rifleman-aim-head-front-close.png", 0, "AN_Soldier_Aim", 24, "head_front")
    render_one("enemy-scout-aim-head-front-close.png", 2, "AN_Soldier_Aim", 24, "head_front")
    render_one("enemy-marksman-aim-head-front-close.png", 3, "AN_Soldier_Aim", 24, "head_front")
    render_one("enemy-rifleman-reload-shoulder-close.png", 0, "AN_Soldier_Reload", 28, "shoulder")
    # One representative visual sample per clip complements the 50-sample
    # transform/contact audit.  These captures stay in the ignored article/QA
    # directory and never become runtime textures.
    for clip_label, action_name, frame in (
        ("idle", "AN_Soldier_Idle", 45),
        ("rifle-ready", "AN_Soldier_RifleReady", 15),
        ("walk-backward", "AN_Soldier_WalkBackward", 10),
        ("strafe-left", "AN_Soldier_StrafeLeft", 10),
        ("strafe-right", "AN_Soldier_StrafeRight", 10),
        ("run-forward", "AN_Soldier_RunForward", 8),
        ("hit-front", "AN_Soldier_HitFront", 4),
        ("hit-back", "AN_Soldier_HitBack", 4),
    ):
        render_one(f"enemy-rifleman-clip-{clip_label}.png", 0, action_name, frame)
    render_one("enemy-rifleman-clip-death-back.png", 0, "AN_Soldier_DeathBack", 32, "fall_back")
    for mesh in meshes:
        mesh.hide_render = False
        mesh.hide_viewport = False
    return rendered


def write_manifest(metrics: list[dict[str, Any]]) -> None:
    manifest = {
        "schemaVersion": 1,
        "packVersion": 1,
        "id": "hibana-enemy-soldiers",
        "authorship": "Original procedural Hibana asset",
        "referenceSourceIncluded": False,
        "sharedSkeleton": "ARM_Enemy_Shared",
        "heightMeters": 1.80,
        "forwardAxis": "-Z",
        "variants": [variant["id"] for variant in VARIANTS],
        "animations": list(REQUIRED_ANIMATIONS),
        "lods": [
            {"level": 0, "url": "soldier-pack-lod0.glb", "screenHeightMin": 0.24},
            {"level": 1, "url": "soldier-pack-lod1.glb", "screenHeightMin": 0.09},
            {"level": 2, "url": "soldier-pack-lod2.glb", "screenHeightMin": 0.0},
        ],
        "budgets": {
            "maxMaterials": 8,
            "maxBones": 32,
            "maxTriangles": {"lod0": 90000, "lod1": 42000, "lod2": 18000},
            "maxBytes": {"lod0": 5500000, "lod1": 3500000, "lod2": 2500000},
        },
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (WORK_DIR / "generation-report.json").write_text(
        json.dumps({"metrics": sorted(metrics, key=lambda item: item["lod"])}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    global OUTPUT_DIR, WORK_DIR, SCREENSHOT_DIR
    args = parse_args()
    OUTPUT_DIR = args.output_dir.expanduser().resolve()
    WORK_DIR = args.work_dir.expanduser().resolve()
    SCREENSHOT_DIR = args.screenshot_dir.expanduser().resolve()
    ensure_directories()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = FPS
    metrics: list[dict[str, Any]] = []
    final_pack: tuple[bpy.types.Object, list[bpy.types.Object], dict[str, bpy.types.Action]] | None = None
    for lod in (2, 1, 0):
        armature, meshes, actions, report = build_pack(lod)
        output = export_pack(lod, armature, meshes)
        try:
            report["output"] = str(output.relative_to(PROJECT))
        except ValueError:
            report["output"] = str(output)
        report["bytesRaw"] = output.stat().st_size
        metrics.append(report)
        if lod == 0:
            final_pack = (armature, meshes, actions)
    if final_pack is None:
        raise RuntimeError("LOD0 pack was not built")
    armature, meshes, actions = final_pack
    rendered = [] if args.skip_renders else render_qa(armature, meshes, actions)
    metrics[-1]["qaRenders"] = rendered
    write_manifest(metrics)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK_DIR / "hibana-enemy-soldiers.blend"))
    print(json.dumps({"ok": True, "metrics": sorted(metrics, key=lambda item: item["lod"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
