from __future__ import annotations

"""Kouwan R10 private visual candidate.

Connection map (authoring coordinates: X horizontal, Y up, Z depth):

  HB_R10_TUG_BOW_LOWER rear Z=-206.0 <-> HB_R82_TUG_LOWER_HULL front Z=-205.5
      overlap: 0.5 m on Z; shared X/Y envelope
  HB_R10_TUG_BOW_UPPER rear Z=-206.2 <-> HB_R82_TUG_UPPER_HULL front Z=-205.9
      overlap: 0.3 m on Z; shared X/Y envelope
  HB_R10_TUG_FOREDECK rear Z=-209.7 <-> HB_R82_TUG_DECK front Z=-209.55
      overlap: 0.15 m on Z
  HB_R10_TUG_WINDSHIELD_* Z=-220.70 <-> HB_R82_TUG_FRONT_GLASS Z=[-220.95,-220.81]
      overlap/contact tolerance: 0.12 m through brow/mullion depth
  HB_R10_BULK_LOADING_CANOPY rear Z=-243.4 <-> existing warehouse frontage
      canopy fascia and roof ties physically overlap the warehouse envelope
  HB_R10_TOWER_VTS_PEDESTAL base Y=70.0 <-> existing exchange-tower roof
      VTS crown, mast, and upper control glazing remain within the tower envelope
  HB_R10_DOCK_CRANE_CAB_STAY start=(91,52,-224) <-> existing crane trolley/cable
      stay, hook block, and hook form one supported handling chain
  HB_R10_SHIP_PLATE_SEAM_* / CRADLE_* <-> existing suspended-ship hull/cradle
      relief remains flush to the hull and knees overlap their pads/supports
  HB_R10_FAR_* base Y=0.0 <-> ground Y=0.0
      sits on ground outside the authoritative playable boundary

No existing collection is deleted.  New geometry is art-only and nonblocking.
The authoritative layout/collision hash remains unchanged.
"""

import hashlib
import json
import math
import os
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


ROOT = Path(
    os.environ.get(
        "HIBANA_KOUWAN_R10_ROOT",
        Path(__file__).resolve().parents[3] / "work/kouwan-r10",
    )
).expanduser().resolve()
REPO = Path(__file__).resolve().parents[5]
PUBLIC = (REPO / "public").resolve()
WORK = (REPO / "tools/blender/work").resolve()
if ROOT == PUBLIC or PUBLIC in ROOT.parents:
    raise RuntimeError(f"private candidate must never write below public/: {ROOT}")
if REPO in ROOT.parents and ROOT != WORK and WORK not in ROOT.parents:
    raise RuntimeError(f"repository-local output must stay below ignored {WORK}: {ROOT}")
OUT = ROOT / "renders/final-v5-r10"
OUT.mkdir(parents=True, exist_ok=True)
EYE_OUT = ROOT / "render-pre-gate-eye"
EYE_OUT.mkdir(parents=True, exist_ok=True)
BLEND_OUT = ROOT / "kouwan-current-v5-r10.blend"
REPORT_OUT = ROOT / "kouwan-current-v5-r10-report.json"
LAYOUT_SHA = "b0e1b9c0b7377dc4978ba2d74a01703677d38fda24d83aef38d59a73b1b9d482"


def rebase_external_images() -> None:
    """Relocate the R9.5 scene's project-authored images with the artifact root."""

    missing: list[str] = []
    for image in bpy.data.images:
        if image.source != "FILE" or image.packed_file is not None:
            continue
        candidate = ROOT / "textures-r5" / Path(image.filepath).name
        if candidate.is_file():
            image.filepath = str(candidate)
        else:
            missing.append(str(candidate))
    if missing:
        raise RuntimeError(f"missing external R9.5 texture inputs: {missing}")


rebase_external_images()


def rp(x: float, y: float, z: float) -> Vector:
    return Vector((x, -z, y))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collection(name: str) -> bpy.types.Collection:
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


C = collection("HB_V5_R10_HARBOR_SHIP_GATE")


def own(obj: bpy.types.Object) -> bpy.types.Object:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    C.objects.link(obj)
    obj["hibanaArtOnly"] = True
    obj["hbWalkBlocker"] = False
    obj["hibanaSourcePass"] = "kouwan-r10"
    return obj


def set_mat(obj: bpy.types.Object, material: bpy.types.Material) -> bpy.types.Object:
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


def box(
    name: str,
    x: float,
    y: float,
    z: float,
    width: float,
    height: float,
    depth: float,
    material: bpy.types.Material,
    bevel: float = 0.0,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=2, location=rp(x, y, z))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (width, depth, height)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        modifier = obj.modifiers.new("HB_R10_BEVEL", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    set_mat(obj, material)
    return own(obj)


def cylinder(
    name: str,
    x: float,
    y: float,
    z: float,
    radius: float,
    height: float,
    material: bpy.types.Material,
    vertices: int = 16,
) -> bpy.types.Object:
    # Blender Z is Hibana authoring Y, so this is world-axis aligned and needs no Euler rotation.
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=height, location=rp(x, y, z))
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_mat(obj, material)
    return own(obj)


def ico_sphere(
    name: str,
    x: float,
    y: float,
    z: float,
    radius: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=rp(x, y, z))
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_mat(obj, material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return own(obj)


def ellipsoid_disc(
    name: str,
    x: float,
    y: float,
    z: float,
    radius_x: float,
    radius_z: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_circle_add(vertices=20, radius=1.0, fill_type="NGON", location=rp(x, y, z))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (radius_x, radius_z, 1.0)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    set_mat(obj, material)
    return own(obj)


def beam(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    half_width: float,
    half_height: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    a = rp(*start)
    b = rp(*end)
    delta = b - a
    length = delta.length
    if length < 1.0e-6:
        raise ValueError(f"zero-length beam: {name}")
    forward = delta / length
    reference_up = Vector((0, 0, 1)) if abs(forward.z) < 0.99 else Vector((1, 0, 0))
    right = forward.cross(reference_up).normalized()
    up = right.cross(forward).normalized()
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = bpy.data.objects.new(name, mesh)
    C.objects.link(obj)
    bm = bmesh.new()
    vertices = []
    for base in (a, b):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            vertices.append(bm.verts.new(base + right * half_width * sx + up * half_height * sy))
    for indices in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (0, 3, 2, 1), (4, 5, 6, 7)):
        bm.faces.new([vertices[index] for index in indices])
    bm.to_mesh(mesh)
    bm.free()
    set_mat(obj, material)
    obj["hibanaArtOnly"] = True
    obj["hbWalkBlocker"] = False
    obj["hibanaSourcePass"] = "kouwan-r10"
    return obj


def polyhedron(
    name: str,
    author_vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    material: bpy.types.Material,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata([tuple(rp(*vertex)) for vertex in author_vertices], [], faces)
    mesh.validate(clean_customdata=False)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    C.objects.link(obj)
    set_mat(obj, material)
    obj["hibanaArtOnly"] = True
    obj["hbWalkBlocker"] = False
    obj["hibanaSourcePass"] = "kouwan-r10"
    return obj


def frustum(
    name: str,
    rear: tuple[tuple[float, float], tuple[float, float]],
    rear_z: float,
    nose: tuple[tuple[float, float], tuple[float, float]],
    nose_z: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    # Each plane is ((left_x, bottom_y), (right_x, top_y)).
    (rl, rb), (rr, rt) = rear
    (nl, nb), (nr, nt) = nose
    vertices = [
        (rl, rb, rear_z), (rr, rb, rear_z), (rr, rt, rear_z), (rl, rt, rear_z),
        (nl, nb, nose_z), (nr, nb, nose_z), (nr, nt, nose_z), (nl, nt, nose_z),
    ]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return polyhedron(name, vertices, faces, material)


def triangular_prism_x(
    name: str,
    x: float,
    thickness: float,
    points_yz: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    material: bpy.types.Material,
) -> bpy.types.Object:
    left = x - thickness * 0.5
    right = x + thickness * 0.5
    vertices = [(left, y, z) for y, z in points_yz] + [(right, y, z) for y, z in points_yz]
    faces = [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]
    return polyhedron(name, vertices, faces, material)


def triangular_prism_z(
    name: str,
    z: float,
    thickness: float,
    points_xy: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    material: bpy.types.Material,
) -> bpy.types.Object:
    front = z + thickness * 0.5
    back = z - thickness * 0.5
    vertices = [(x, y, front) for x, y in points_xy] + [(x, y, back) for x, y in points_xy]
    faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    return polyhedron(name, vertices, faces, material)


def ring_on_z_plane(
    name: str,
    center_x: float,
    center_y: float,
    z: float,
    outer_radius: float,
    inner_radius: float,
    thickness: float,
    material: bpy.types.Material,
    segments: int = 16,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    for plane_z in (z - thickness * 0.5, z + thickness * 0.5):
        for radius in (outer_radius, inner_radius):
            for index in range(segments):
                angle = math.tau * index / segments
                vertices.append((center_x + math.cos(angle) * radius, center_y + math.sin(angle) * radius, plane_z))
    faces: list[tuple[int, ...]] = []
    front_outer = 0
    front_inner = segments
    back_outer = segments * 2
    back_inner = segments * 3
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.extend(
            (
                (front_outer + index, front_outer + nxt, front_inner + nxt, front_inner + index),
                (back_outer + index, back_inner + index, back_inner + nxt, back_outer + nxt),
                (front_outer + index, back_outer + index, back_outer + nxt, front_outer + nxt),
                (front_inner + index, front_inner + nxt, back_inner + nxt, back_inner + index),
            )
        )
    return polyhedron(name, vertices, faces, material)


def principled(material: bpy.types.Material):
    if not material.use_nodes or material.node_tree is None:
        return None
    return next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)


def set_input(node, name: str, value) -> None:
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value


concrete = bpy.data.materials["MAT_KOUWAN_ATLAS_WEATHERED_CONCRETE"]
salt = bpy.data.materials["MAT_KOUWAN_ATLAS_SALT_CONCRETE"]
steel = bpy.data.materials["MAT_KOUWAN_ATLAS_GUNMETAL_PLATE"]
rust = bpy.data.materials["MAT_KOUWAN_ATLAS_RUSTED_STEEL"]
orange = bpy.data.materials["MAT_KOUWAN_ATLAS_SAFETY_ORANGE"]
offwhite = bpy.data.materials["MAT_KOUWAN_ATLAS_PAINTED_OFFWHITE"]
corrugated = bpy.data.materials["MAT_KOUWAN_ATLAS_CORRUGATED_METAL"]
roof = bpy.data.materials["MAT_KOUWAN_ATLAS_ROOF_MEMBRANE"]
brick = bpy.data.materials["MAT_KOUWAN_ATLAS_OLD_BRICK"]
grating = bpy.data.materials["MAT_KOUWAN_ATLAS_GALVANIZED_GRATING"]
oxide = bpy.data.materials["MAT_KOUWAN_R8_OXIDE_GREEN"]
smoked_glass = bpy.data.materials["MAT_KOUWAN_R9_SMOKED_GLASS"]
warm_glass = bpy.data.materials["MAT_KOUWAN_R9_WARM_OCCUPIED_GLASS"]
interior = bpy.data.materials["MAT_KOUWAN_R9_INTERIOR_RECESS"]
legacy_interior = bpy.data.materials.get("MAT_KOUWAN_R5_INTERIOR")
legacy_warm_glass = bpy.data.materials.get("MAT_KOUWAN_ATLAS_WARM_GLASS")
hull = bpy.data.materials["MAT_KOUWAN_R83_HULL_NAVY"]
antifoul = bpy.data.materials["MAT_KOUWAN_R83_HULL_RED"]
water = bpy.data.materials["MAT_KOUWAN_HARBOR_WATER"]
wet_film = bpy.data.materials.get("MAT_KOUWAN_R84_DARK_PUDDLE", water)
lamp = bpy.data.materials["MAT_KOUWAN_PRACTICAL_LAMP"]


# Replace black-window read with physically plausible sea-green reflections.
glass_node = principled(smoked_glass)
if glass_node is not None:
    set_input(glass_node, "Base Color", (0.025, 0.16, 0.18, 1.0))
    set_input(glass_node, "Metallic", 0.12)
    set_input(glass_node, "Roughness", 0.24)
    set_input(glass_node, "IOR", 1.45)
    set_input(glass_node, "Coat Weight", 0.28)
    set_input(glass_node, "Coat Roughness", 0.14)
    set_input(glass_node, "Emission Color", (0.015, 0.06, 0.07, 1.0))
    set_input(glass_node, "Emission Strength", 0.10)
interior_node = principled(interior)
if interior_node is not None:
    set_input(interior_node, "Base Color", (0.022, 0.032, 0.038, 1.0))
    set_input(interior_node, "Metallic", 0.0)
    set_input(interior_node, "Roughness", 0.68)
warm_node = principled(warm_glass)
if warm_node is not None:
    set_input(warm_node, "Base Color", (0.04, 0.16, 0.18, 1.0))
    set_input(warm_node, "Roughness", 0.22)
    set_input(warm_node, "Coat Weight", 0.30)
    set_input(warm_node, "Emission Color", (0.12, 0.065, 0.025, 1.0))
    set_input(warm_node, "Emission Strength", 0.18)
legacy_interior_node = principled(legacy_interior) if legacy_interior is not None else None
if legacy_interior_node is not None:
    set_input(legacy_interior_node, "Base Color", (0.04, 0.065, 0.07, 1.0))
    set_input(legacy_interior_node, "Roughness", 0.62)
    set_input(legacy_interior_node, "Emission Color", (0.05, 0.025, 0.01, 1.0))
    set_input(legacy_interior_node, "Emission Strength", 0.08)
legacy_warm_node = principled(legacy_warm_glass) if legacy_warm_glass is not None else None
if legacy_warm_node is not None:
    set_input(legacy_warm_node, "Base Color", (0.06, 0.14, 0.15, 1.0))
    set_input(legacy_warm_node, "Roughness", 0.28)
    set_input(legacy_warm_node, "Emission Color", (0.11, 0.06, 0.025, 1.0))
    set_input(legacy_warm_node, "Emission Strength", 0.16)


# --- Tugboat: replace the rectangular termination with a connected flare bow. ---
frustum(
    "HB_R10_TUG_BOW_LOWER",
    ((52.85, 0.0), (63.15, 2.55)),
    -206.0,
    ((56.15, 0.35), (59.85, 2.15)),
    -196.4,
    hull,
)
frustum(
    "HB_R10_TUG_BOW_UPPER",
    ((52.65, 2.20), (63.35, 3.95)),
    -206.2,
    ((55.90, 1.95), (60.10, 3.18)),
    -196.2,
    oxide,
)
frustum(
    "HB_R10_TUG_FOREDECK",
    ((52.95, 3.78), (63.05, 4.08)),
    -209.7,
    ((56.25, 3.00), (59.75, 3.28)),
    -196.1,
    offwhite,
)
box("HB_R10_TUG_BOW_RUB_RAIL", 58.0, 2.80, -201.15, 6.7, 0.28, 0.34, offwhite, 0.07)
for side, x in (("L", 53.05), ("R", 62.95)):
    beam(f"HB_R10_TUG_BULWARK_{side}", (x, 3.92, -206.1), (58.0 + (-1.65 if side == "L" else 1.65), 3.30, -196.8), 0.075, 0.075, steel)
for index, z in enumerate((-204.7, -201.7, -198.9)):
    width = 4.3 - index * 1.05
    for side in (-1, 1):
        x = 58.0 + side * width
        beam(f"HB_R10_TUG_BOW_RAIL_POST_{index}_{side:+d}", (x, 3.55, z), (x, 4.55, z), 0.045, 0.045, steel)
    beam(f"HB_R10_TUG_BOW_RAIL_{index}", (58.0 - width, 4.50, z), (58.0 + width, 4.50, z), 0.045, 0.045, steel)
for side, x in (("L", 56.25), ("R", 59.75)):
    cylinder(f"HB_R10_TUG_HAWSE_{side}", x, 2.55, -197.1, 0.34, 0.18, rust, 18)

# Wheelhouse glazing gains real mullions, a drip brow, and navigation lights.
for index, x in enumerate((55.15, 56.58, 58.0, 59.42, 60.85)):
    box(f"HB_R10_TUG_WINDSHIELD_MULLION_{index}", x, 7.12, -220.68, 0.12, 2.95, 0.16, steel, 0.02)
box("HB_R10_TUG_WINDSHIELD_BROW", 58.0, 8.76, -220.70, 6.15, 0.20, 0.62, oxide, 0.04)
box("HB_R10_TUG_WINDSHIELD_SILL", 58.0, 5.56, -220.70, 6.15, 0.18, 0.48, steel, 0.03)
for side, x, material in (("PORT", 54.45, orange), ("STARBOARD", 61.55, lamp)):
    box(f"HB_R10_TUG_NAV_{side}", x, 9.66, -221.5, 0.32, 0.32, 0.32, material, 0.06)
for side, x in (("PORT", 54.75), ("STARBOARD", 61.25)):
    ring_on_z_plane(f"HB_R10_TUG_LIFE_RING_{side}", x, 5.25, -220.48, 0.62, 0.36, 0.12, orange, 18)
    beam(f"HB_R10_TUG_LIFE_RING_STRAP_{side}", (x - 0.52, 5.25, -220.36), (x + 0.52, 5.25, -220.36), 0.035, 0.035, offwhite)


# --- Waterfront warehouse: attached loading canopy and credible rooftop plant. ---
box("HB_R10_BULK_LOADING_CANOPY", 81.5, 20.1, -241.9, 59.5, 0.55, 3.0, roof, 0.10)
box("HB_R10_BULK_LOADING_CANOPY_FASCIA", 81.5, 19.9, -240.35, 59.8, 0.75, 0.22, rust, 0.05)
for index, x in enumerate((54.0, 65.0, 76.0, 87.0, 98.0, 109.0)):
    beam(f"HB_R10_BULK_CANOPY_TIE_{index}", (x, 19.45, -242.5), (x, 23.0, -250.0), 0.10, 0.10, steel)
    box(f"HB_R10_BULK_CANOPY_LAMP_{index}", x, 19.6, -240.12, 0.75, 0.18, 0.18, lamp, 0.03)
for index, (x, height, width) in enumerate(((60.0, 4.8, 6.2), (78.0, 6.2, 7.0), (99.0, 5.4, 6.5))):
    box(f"HB_R10_BULK_ROOF_PLANT_{index}", x, 20.0 + height * 0.5, -252.0, width, height, 7.0, corrugated if index != 1 else oxide, 0.15)
    box(f"HB_R10_BULK_ROOF_PLANT_LOUVER_{index}", x, 20.2 + height * 0.5, -248.42, width * 0.72, height * 0.62, 0.16, grating, 0.03)
    cylinder(f"HB_R10_BULK_ROOF_STACK_{index}", x + width * 0.22, 24.2 + height, -253.5, 0.42, 5.2 + index, rust, 14)


# --- Exchange tower: a compact VTS radar lantern, preserving the existing facade. ---
cylinder("HB_R10_TOWER_VTS_PEDESTAL", 68.0, 71.2, -74.0, 2.55, 2.4, steel, 18)
ico_sphere("HB_R10_TOWER_VTS_RADOME", 68.0, 75.0, -74.0, 3.2, offwhite)
cylinder("HB_R10_TOWER_VTS_RADOME_COLLAR", 68.0, 72.9, -74.0, 3.35, 0.55, rust, 20)
beam("HB_R10_TOWER_VTS_MAST", (68.0, 77.4, -74.0), (68.0, 87.0, -74.0), 0.11, 0.11, steel)
for index, y in enumerate((80.6, 84.0)):
    beam(f"HB_R10_TOWER_VTS_YARD_{index}", (62.8 + index, y, -74.0), (73.2 - index, y, -74.0), 0.09, 0.09, orange if index else steel)

# Panoramic control-room panes sit within the existing upper volume and preserve the roof overhang.
for bay, x in enumerate((70.5, 75.0, 79.5, 84.0)):
    box(f"HB_R10_TOWER_CONTROL_GLASS_{bay}", x, 51.0, -56.78, 3.65, 10.2, 0.12, smoked_glass, 0.035)
    for side in (-1, 1):
        box(f"HB_R10_TOWER_CONTROL_JAMB_{bay}_{side:+d}", x + side * 1.90, 51.0, -56.67, 0.15, 10.7, 0.24, steel, 0.025)
box("HB_R10_TOWER_CONTROL_BROW", 77.25, 56.35, -56.62, 18.7, 0.20, 0.62, rust, 0.04)
box("HB_R10_TOWER_CONTROL_SILL", 77.25, 45.65, -56.62, 18.7, 0.20, 0.46, steel, 0.04)


# Dock-crane operator cabin, trolley connection, and hook block.
box("HB_R10_DOCK_CRANE_CAB", 96.0, 47.4, -225.0, 4.8, 5.2, 4.2, offwhite, 0.18)
box("HB_R10_DOCK_CRANE_CAB_GLASS", 96.0, 48.0, -222.84, 3.75, 2.5, 0.14, smoked_glass, 0.04)
for side in (-1, 1):
    box(f"HB_R10_DOCK_CRANE_CAB_POST_{side:+d}", 96.0 + side * 2.08, 47.7, -222.68, 0.18, 4.65, 0.20, steel, 0.03)
box("HB_R10_DOCK_CRANE_CAB_BROW", 96.0, 50.75, -222.64, 4.8, 0.22, 0.52, rust, 0.04)
beam("HB_R10_DOCK_CRANE_CAB_STAY", (91.0, 52.0, -224.0), (96.0, 50.1, -225.0), 0.14, 0.14, steel)
box("HB_R10_DOCK_CRANE_HOOK_BLOCK", 91.0, 13.8, -224.0, 1.6, 2.0, 1.2, orange, 0.12)
beam("HB_R10_DOCK_CRANE_HOOK_A", (90.6, 12.9, -224.0), (91.0, 11.2, -224.0), 0.09, 0.09, steel)
beam("HB_R10_DOCK_CRANE_HOOK_B", (91.0, 11.2, -224.0), (91.7, 11.8, -224.0), 0.09, 0.09, steel)


# --- Suspended ship: real plate seams, draft marks, and cradle hardware. ---
for row, y in enumerate((5.0, 9.2, 13.4, 17.6, 21.8)):
    box(f"HB_R10_SHIP_PLATE_SEAM_H_{row}", -38.94, y, 67.0, 0.14, 0.11, 42.0, rust if row in {0, 4} else steel, 0.015)
for column, z in enumerate((50.0, 58.5, 67.0, 75.5, 84.0)):
    box(f"HB_R10_SHIP_PLATE_SEAM_V_{column}", -38.92, 13.3, z, 0.16, 17.0, 0.10, steel, 0.015)
for tick, y in enumerate((4.4, 5.3, 6.2, 7.1, 8.0, 8.9)):
    box(f"HB_R10_SHIP_DRAFT_MARK_{tick}", -38.80, y, 47.4, 0.12, 0.14, 1.8 if tick % 2 == 0 else 1.1, offwhite, 0.01)
for index, z in enumerate((51.0, 61.5, 72.0, 82.5)):
    box(f"HB_R10_SHIP_CRADLE_PAD_{index}", -38.35, 2.1, z, 1.25, 0.65, 2.1, concrete, 0.08)
    beam(f"HB_R10_SHIP_CRADLE_KNEE_{index}", (-38.5, 2.5, z), (-40.2, 8.0, z), 0.12, 0.12, rust)


# --- Layered real-3D horizon outside the playable boundary. ---
far_halls = (
    ("A", -6.0, -279.0, 42.0, 31.0, 24.0, brick),
    ("B", 128.0, -286.0, 48.0, 36.0, 30.0, concrete),
)
for label, x, z, width, height, depth, material in far_halls:
    box(f"HB_R10_FAR_HALL_{label}_BODY", x, height * 0.5, z, width, height, depth, material, 0.18)
    box(f"HB_R10_FAR_HALL_{label}_PLINTH", x, 0.75, z, width + 2.0, 1.5, depth + 2.0, salt, 0.12)
    box(f"HB_R10_FAR_HALL_{label}_ROOF", x, height + 1.1, z, width + 1.5, 2.2, depth + 1.5, roof, 0.16)
    for bay in range(4):
        window_x = x - width * 0.34 + bay * width * 0.225
        pane_width = width * 0.15
        pane_y = height * 0.62
        face_z = z + depth * 0.505
        box(f"HB_R10_FAR_HALL_{label}_GLASS_{bay}", window_x, pane_y, face_z, pane_width, 4.2, 0.12, smoked_glass, 0.03)
        box(f"HB_R10_FAR_HALL_{label}_FRAME_TOP_{bay}", window_x, pane_y + 2.22, face_z + 0.05, pane_width + 0.35, 0.18, 0.18, steel, 0.03)
        box(f"HB_R10_FAR_HALL_{label}_FRAME_BOTTOM_{bay}", window_x, pane_y - 2.22, face_z + 0.05, pane_width + 0.35, 0.18, 0.18, steel, 0.03)
        for side in (-1, 1):
            box(f"HB_R10_FAR_HALL_{label}_FRAME_SIDE_{bay}_{side:+d}", window_x + side * (pane_width * 0.5 + 0.08), pane_y, face_z + 0.05, 0.18, 4.55, 0.18, steel, 0.03)

for index, x in enumerate((77.0, 86.0, 95.0)):
    cylinder(f"HB_R10_FAR_SILO_{index}", x, 17.0 + index * 1.5, -286.0, 3.5 + index * 0.2, 34.0 + index * 3.0, offwhite if index != 1 else oxide, 20)
    cylinder(f"HB_R10_FAR_SILO_CAP_{index}", x, 34.4 + index * 3.0, -286.0, 3.75 + index * 0.2, 0.8, steel, 20)
    beam(f"HB_R10_FAR_SILO_PIPE_{index}", (x, 34.5 + index * 3.0, -286.0), (x, 43.0 + index * 3.0, -286.0), 0.10, 0.10, rust)
beam("HB_R10_FAR_SILO_GALLERY", (73.0, 39.0, -286.0), (100.0, 39.0, -286.0), 0.24, 0.18, grating)


# Deterministic inspection views, identical to R9.5 for direct comparison.
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1536
scene.render.resolution_y = 864
scene.render.resolution_percentage = 100
scene.view_settings.exposure = 0.90
scene.view_settings.look = "AgX - Medium High Contrast"
camera = bpy.data.objects["HB_V5_REVIEW_CAMERA"]
scene.camera = camera


def point_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (rp(*target) - obj.location).to_track_quat("-Z", "Y").to_euler()


views = (
    ("kouwan-r10-player-eye.png", "01-player-eye165.png", (146.0, 1.65, 151.0), (-8.0, 18.0, -12.0), 20.0),
    ("kouwan-r10-waterfront.png", "02-waterfront-eye165.png", (18.0, 1.65, -182.2), (58.0, 8.0, -245.0), 30.0),
    ("kouwan-r10-ship-player-eye.png", "03-ship-eye165.png", (14.0, 1.65, 142.0), (-49.0, 26.0, 67.0), 34.0),
    ("kouwan-r10-tower-player-eye.png", "04-tower-eye165.png", (158.0, 1.65, -18.0), (76.0, 42.0, -79.0), 24.0),
    ("kouwan-r10-aerial.png", None, (270.0, 120.0, 280.0), (-5.0, 22.0, -20.0), 39.0),
)
renders: list[Path] = []
for filename, eye_filename, position, target, lens in views:
    camera.location = rp(*position)
    camera.data.lens = lens
    point_at(camera, target)
    output = OUT / filename
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    if eye_filename is not None:
        bpy.data.images["Render Result"].save_render(filepath=str(EYE_OUT / eye_filename))
    renders.append(output)


scene["hibanaLayoutSha256"] = LAYOUT_SHA
scene["hibanaLayoutChanged"] = False
scene["hibanaCollisionChanged"] = False
scene["hibanaR10PrivateNoShip"] = True
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))

visible_meshes = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render]
for obj in visible_meshes:
    obj.data.calc_loop_triangles()
r10_meshes = [obj for obj in C.objects if obj.type == "MESH" and not obj.hide_render]
for obj in r10_meshes:
    obj.data.calc_loop_triangles()
report = {
    "candidate": "kouwan-r10-private-harbor-ship-gate",
    "status": "NO-SHIP pending independent five-view score, contact, LOD, size, and Khronos gates",
    "blend": str(BLEND_OUT),
    "blendSha256": sha256(BLEND_OUT),
    "layoutSha256": LAYOUT_SHA,
    "layoutChanged": False,
    "collisionChanged": False,
    "baseline": {
        "blend": str(ROOT / "kouwan-current-v5-r9-5.blend"),
        "visibleMeshes": 3867,
        "visibleBaseTriangles": 94132,
    },
    "r10AddedMeshes": len(r10_meshes),
    "r10AddedBaseTriangles": sum(len(obj.data.loop_triangles) for obj in r10_meshes),
    "visibleMeshes": len(visible_meshes),
    "visibleBaseTriangles": sum(len(obj.data.loop_triangles) for obj in visible_meshes),
    "materialsTouched": [
        smoked_glass.name,
        warm_glass.name,
        interior.name,
        *([legacy_interior.name] if legacy_interior is not None else []),
        *([legacy_warm_glass.name] if legacy_warm_glass is not None else []),
    ],
    "renders": [{"path": str(path), "sha256": sha256(path)} for path in renders],
}
REPORT_OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
