"""Generate all 31 Hibana stage shells in the visible Blender session.

The TypeScript layout JSON remains authoritative. This script adds optimized visual
geometry around that layout, exports three GLB levels, renders deterministic QA
thumbnails, and keeps the UI responsive by processing one stage per Blender timer tick.
"""

import bpy
import hashlib
import importlib.util
import json
import math
from mathutils import Vector
from pathlib import Path


EXEC_ARGS = globals().get("args", {})
if not isinstance(EXEC_ARGS, dict):
    EXEC_ARGS = {}

# `__file__` is available for normal Blender/headless script execution. The
# localhost MCP bridge intentionally compiles reviewed scripts as
# `<mcp-script>`, so it supplies the already-known repository root explicitly.
# Both paths are validated before any output directory is created.
if "__file__" in globals():
    PROJECT_PATH = Path(__file__).resolve().parents[2]
else:
    project_root = EXEC_ARGS.get("project_root")
    if not project_root:
        raise RuntimeError("project_root is required when Blender execution does not expose __file__")
    PROJECT_PATH = Path(project_root).expanduser().resolve()
if not (PROJECT_PATH / "tools/blender/build_all_stages.py").is_file():
    raise RuntimeError(f"invalid Hibana project root: {PROJECT_PATH}")
PROJECT = str(PROJECT_PATH)
PROFILE_PATH = PROJECT + "/tools/blender/stage-profiles.json"


def load_reviewed_stage_kit(relative_path, module_name):
    """Load a reviewed, repository-owned stage kit without mutating sys.path."""
    source = PROJECT_PATH / relative_path
    if not source.is_file():
        raise RuntimeError(f"missing reviewed stage kit: {source}")
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load reviewed stage kit: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(source.read_bytes()).hexdigest()


# Phase 4a reconciliation: nakaniwa's production kit was NAKANIWA_REFERENCE_A18
# through Phase 3, but every A23-round improvement to nakaniwa (district
# infill, material family split, articulated facades, window rhythm, and the
# Tier 1 palace-occlusion recovery) was built on
# nakaniwa_reference_a21_r6.py, not a18 -- so the production generator would
# have shipped a nakaniwa GLB containing none of it. build_nakaniwa_reference_lod
# below now loads a21_r6 instead (see NAKANIWA_A23_RECONCILIATION's own module
# docstring for the ported fix chain that reproduces the round's proven best
# build -- verified byte-for-byte spec-identical and pixel-identical to
# /private/tmp/hibana-blender/claude-a23-tier1/views/*.png).
NAKANIWA_REFERENCE_A21_R6, NAKANIWA_REFERENCE_SOURCE_SHA = load_reviewed_stage_kit(
    "tools/blender/stage_kits/nakaniwa_reference_a21_r6.py",
    "hibana_nakaniwa_reference_a21_r6",
)

# The promoted tools/blender/a23 toolchain (Phase 2), its Phase 3 bridge
# (tools/blender/a23_bridge.py), and the Phase 4a nakaniwa reconciliation
# module (tools/blender/stage_kits/nakaniwa_a23_reconciliation.py) are
# ordinary repository packages that use absolute `tools.blender...` imports --
# the same convention the a23 package's own unit tests already rely on. That
# is different from load_reviewed_stage_kit's deliberately sys.path-free
# dynamic loading of a single reviewed stage-kit file; these are shared
# library code (or, for the reconciliation module, glue code composed from
# shared library code), so the standard import system is the right tool here.
import sys  # noqa: E402

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
from tools.blender import a23_bridge  # noqa: E402
from tools.blender.a23 import orphan as a23_orphan  # noqa: E402
from tools.blender.stage_kits import nakaniwa_a23_reconciliation as NAKANIWA_A23_RECONCILIATION  # noqa: E402


def approved_output_path(argument, default):
    """Resolve a production or ignored QA output without allowing arbitrary writes."""
    path = Path(EXEC_ARGS.get(argument, default)).expanduser().resolve()
    approved_roots = (
        Path(PROJECT).resolve(),
        Path("/private/tmp/hibana-blender").resolve(),
    )
    if not any(path == root or root in path.parents for root in approved_roots):
        raise RuntimeError(f"{argument} must stay inside the Hibana project or /private/tmp/hibana-blender: {path}")
    return path


LAYOUT_PATH = str(approved_output_path(
    "layout_path",
    PROJECT + "/tools/blender/generated/stage-layouts.json",
))
OUTPUT_DIR_PATH = approved_output_path("output_dir", PROJECT + "/public/assets/aaa/stages")
WORK_DIR_PATH = approved_output_path("work_dir", PROJECT + "/tools/blender/work")
RENDER_DIR_PATH = approved_output_path("render_dir", PROJECT + "/tools/blender/renders")
PROGRESS_PATH_OBJ = approved_output_path("progress_path", PROJECT + "/tools/blender/progress.json")
MANIFEST_PATH_OBJ = approved_output_path("manifest_path", PROJECT + "/public/assets/aaa/manifest.json")
for directory in (OUTPUT_DIR_PATH, WORK_DIR_PATH, RENDER_DIR_PATH, PROGRESS_PATH_OBJ.parent, MANIFEST_PATH_OBJ.parent):
    directory.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = str(OUTPUT_DIR_PATH)
WORK_DIR = str(WORK_DIR_PATH)
RENDER_DIR = str(RENDER_DIR_PATH)
PROGRESS_PATH = str(PROGRESS_PATH_OBJ)
MANIFEST_PATH = str(MANIFEST_PATH_OBJ)
PREFIX = "HB_"
GENERATOR_VERSION = "dense-world-v4"
GENERATOR_PATH = Path(PROJECT) / "tools/blender/build_all_stages.py"
GENERATOR_SHA = hashlib.sha256(GENERATOR_PATH.read_bytes()).hexdigest()

# Natural perimeter rocks are a gameplay-facing silhouette, not disposable
# scatter.  Keep their sample lattice and physical envelope identical across
# every LOD; only the primitive's angular tessellation may reduce.  The
# seven-metre inward cap leaves at least four metres between the conservative
# rock envelope and canonical spawns, which are authored twelve metres inside
# the square boundary (including the Kunren east spawn that exposed A17's
# count/radius coupling).
BOUNDARY_SAMPLE_COUNT = 42
BOUNDARY_CHIKURIN_SAMPLE_COUNT = 34
# LOD2 dropped 10->6->4 to 10->6->3 (release round: setsugen's ice-ridge
# boundary alone puts up to 168 rocks in frame, and its LOD2 was 8,828
# triangles = 12.21% of LOD0 against the 12% cap -- about 150 triangles over).
# add_rock() triangulates 4 taper rings into 3 side quad-bands plus two
# n-gon caps, i.e. 8*segments-4 triangles/rock, so 4->3 saves 8 triangles per
# rock at the farthest, coarsest tier only (viewed no closer than the LOD2
# swap distance). LOD0/LOD1 segment counts (10, 6) are untouched, so near-view
# rock silhouettes do not change; this can only ever reduce LOD2 triangle
# totals, so it cannot introduce a new budget breach on any of the other 30
# stages that share this constant.
BOUNDARY_ROCK_SEGMENTS_BY_LOD = (10, 6, 3)
BOUNDARY_ROCK_MAX_RADIAL_STRETCH = 1.16
BOUNDARY_MAX_INWARD_REACH_M = 7.0

# A18 Souko is a reference-match rebuild, not another facade-detail pass.  The
# constants below mirror the frozen connection map in the private QA package.
# Ground-level route/collision remains TypeScript-authored; new hero mass begins
# on a tagged support or above the declared traversal-clearance plane.
SOUKO_REFERENCE_MATCH_VERSION = "a18-reference-match-v2"
SOUKO_STACKHOUSE_RACK_BASE_M = 12.82
SOUKO_STACKHOUSE_SKYBRIDGE_BOTTOM_M = 35.80
SOUKO_CUSTOMS_ROOF_BASE_M = 11.20
SOUKO_CUSTOMS_CANOPY_BOTTOM_M = 10.82
SOUKO_ROUTE_VISUAL_MARGIN_M = 2.0
SOUKO_SPAWN_CLEARANCE_M = 30.0


def canonical_json_sha256(value):
    """Hash JSON by value, independent of indentation and object key order."""
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


IDENTITIES = {
    "kunren": ("military", "range-radar"),
    "souko": ("industrial", "container-crane"),
    "nakaniwa": ("heritage", "palace-dome"),
    "kairou": ("heritage", "desert-gate"),
    "kouwan": ("industrial", "harbor-crane"),
    "takadai": ("heritage", "grand-abbey"),
    "sakyuu": ("wilderness", "desert-rig"),
    "setsugen": ("arctic", "polar-array"),
    "koushou": ("industrial", "refinery-stack"),
    "yoichi": ("urban", "neon-spire"),
    "okujou": ("urban", "rooftop-helipad"),
    "saisekiba": ("industrial", "quarry-conveyor"),
    "chikurin": ("heritage", "bamboo-pagoda"),
    "tanada": ("wilderness", "terrace-village"),
    "misaki": ("military", "coastal-lighthouse"),
    "haieki": ("industrial", "rail-terminal"),
    "kyokoku": ("wilderness", "canyon-bridge"),
    "kohan": ("wilderness", "lakeside-observatory"),
    "kuko": ("airport", "airport-control"),
    "onsengai": ("heritage", "onsen-pagoda"),
    "z01": ("undead", "ruined-city"),
    "z02": ("undead", "burning-block"),
    "z03": ("undead", "wrecked-port"),
    "z04": ("undead", "ruined-abbey"),
    "z05": ("geothermal", "lava-mine"),
    "z06": ("undead", "slaughter-stack"),
    "z07": ("undead", "quarantine-gate"),
    "z08": ("undead", "subway-vault"),
    "z09": ("undead", "broken-ferris-wheel"),
    "z10": ("geothermal", "volcano-fortress"),
    "renshujo": ("military", "training-tower"),
}


# Two profile-backed mega-landmarks are authored for every stage.  The labels
# are deliberately specific rather than broad asset-library archetypes: they
# become deterministic geometry seeds and QA identifiers, while the builder
# below groups them only at the lowest-level construction primitive.  This
# keeps all 62 silhouettes unique without creating 62 unrelated export paths.
MEGA_LANDMARK_STYLES = {
    "kunren": ("command-bastion", "aerostat-vault-hangar"),
    "souko": ("rack-bridge-storehouse", "customs-sawtooth-terminal"),
    "nakaniwa": ("crowned-water-palace", "fan-glass-conservatory"),
    # The profile identity explicitly promises an observatory.  Keeping that
    # token in the construction style is functional: reference-first branches
    # use it to build the supported armillary crown instead of a generic cone.
    "kairou": ("hypostyle-sanctuary", "windtower-windcrown-caravan-observatory"),
    "kouwan": ("twin-ship-lift", "harbor-exchange-tower"),
    "takadai": ("existing-tidal-abbey", "octagonal-dawn-citadel"),
    "sakyuu": ("crawler-fortress-hangar", "spiral-drill-crown"),
    "setsugen": ("tripod-polar-arcology", "aurora-data-cathedral"),
    "koushou": ("twin-furnace-keep", "continuous-casting-hall"),
    "yoichi": ("vertical-market-spire", "rain-opera-exchange"),
    "okujou": ("cloud-broadcast-spire", "skyrail-atrium-hotel"),
    "saisekiba": ("strata-crusher-step-tower", "echo-stone-saw-hall"),
    "chikurin": ("nine-canopy-pagoda", "bamboo-academy-citadel"),
    "tanada": ("terraced-granary-castle", "waterwheel-irrigation-monastery"),
    "misaki": ("storm-glass-lighthouse-castle", "whaleback-submarine-pen"),
    "haieki": ("iron-fog-grand-terminal", "clock-water-tower-keep"),
    "kyokoku": ("suspended-cliff-palace", "chain-aqueduct-fortress"),
    "kohan": ("triple-mirror-observatory", "hydro-cliff-grand-lodge"),
    "kuko": ("wing-crown-air-terminal", "orbital-control-citadel"),
    "onsengai": ("thousand-bath-grand-ryokan", "steam-clock-onsen-tower"),
    "z01": ("blackout-civic-megablock", "broken-crown-transit-keep"),
    "z02": ("cremation-arena-basilica", "firewatch-collective-tower"),
    "z03": ("capsized-drydock-hall", "fog-bell-cargo-keep"),
    # Z04 owns the same *playable* abbey collider grammar as Takadai, but its
    # exported shell must be the broken, asymmetrical version seated on those
    # colliders.  Prefixing the unique style with ``existing-`` routes it
    # through add_abbey_visual(damaged=True) instead of accidentally placing a
    # second cathedral hundreds of metres beyond an undecorated central shell.
    "z04": ("existing-severed-rose-ruined-cathedral", "ossuary-bell-keep"),
    "z05": ("magma-shaft-hoist-castle", "obsidian-smelter-ark"),
    "z06": ("frozen-chain-storage-tower", "cable-processing-hall"),
    "z07": ("quarantine-great-gate", "white-shield-hospital-tower"),
    "z08": ("underground-ring-bazaar", "last-light-flood-terminal"),
    "z09": ("ash-crown-ferris-keep", "eclipse-mirror-maze-palace"),
    "z10": ("fire-ring-command-fort", "geothermal-needle-castle"),
    "renshujo": ("ridge-command-lodge", "twin-ridge-target-tower"),
}


MEGA_LANDMARK_ORDER = {
    (stage_id, landmark_index): sequence
    for sequence, (stage_id, landmark_index) in enumerate(
        (pair for stage_id in IDENTITIES for pair in ((stage_id, 0), (stage_id, 1)))
    )
}


def stable_unit(seed, index, salt=0):
    value = (seed ^ (index * 0x9E3779B1) ^ salt) & 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x7FEB352D) & 0xFFFFFFFF
    value ^= value >> 15
    value = (value * 0x846CA68B) & 0xFFFFFFFF
    value ^= value >> 16
    return value / 0xFFFFFFFF


def stable_text_signature(*values):
    """Return a deterministic 32-bit signature for profile-authored art language."""
    payload = "\u241f".join(str(value) for value in values).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def signed_angle_degrees(from_x, from_z, to_x, to_z):
    """Return the signed plan-view angle from one direction to another."""
    from_length = math.hypot(from_x, from_z)
    to_length = math.hypot(to_x, to_z)
    if from_length < 1e-6 or to_length < 1e-6:
        return 0.0
    from_x, from_z = from_x / from_length, from_z / from_length
    to_x, to_z = to_x / to_length, to_z / to_length
    cross = from_x * to_z - from_z * to_x
    dot = max(-1.0, min(1.0, from_x * to_x + from_z * to_z))
    return math.degrees(math.atan2(cross, dot))


def landmark_spawn_vista(stage, landmark_index, profile_landmark):
    """Numerically place a mega-landmark inside the initial FPS vista.

    Normal maps spawn at the north-east corner and look at the centre.  The
    first landmark therefore sits beyond the north boundary and the second
    beyond the west boundary.  Their bearings straddle the centre line rather
    than the old north/east arrangement whose second landmark was 83-90
    degrees off-screen.  Both footprints remain wholly outside the gameplay
    square, so TypeScript collision and routes stay authoritative.
    """
    dimensions = profile_landmark["dimensionsM"]
    width = float(dimensions["width"]) * 0.78
    depth = float(dimensions["depth"]) * 0.70
    half = stage["size"] / 2
    spawn = stage.get("playerSpawns", [[half * 0.78, 0, half * 0.78]])[0]
    spawn_x, spawn_z = float(spawn[0]), float(spawn[2])
    view_x, view_z = -spawn_x, -spawn_z
    if math.hypot(view_x, view_z) < 1e-5:
        view_x, view_z = -1.0, -1.0
    view_angle = math.atan2(view_z, view_x)
    signature = stable_text_signature(stage["id"], profile_landmark["id"], "spawn-vista-v5")
    # Stage-specific but tightly art-directed separation.  At the normal
    # 75-degree horizontal FOV this leaves safe edge margin for the weapon.
    spread = 13.5 + (signature % 37) / 37.0 * 3.5
    bearing = spread if landmark_index == 0 else -spread
    direction_angle = view_angle + math.radians(bearing)
    direction_x, direction_z = math.cos(direction_angle), math.sin(direction_angle)
    clearance = 5.5 + (signature % 5) * 0.55

    if landmark_index == 0 and stage["id"] not in {"takadai", "z04"}:
        # North: local +Z is the player-facing elevation at yaw=0.
        z = -half - depth / 2 - clearance
        travel = (z - spawn_z) / direction_z
        x = spawn_x + direction_x * travel
        yaw = 0.0
    else:
        # West: yaw=-90 degrees maps local +Z to world +X (toward the player).
        x = -half - depth / 2 - clearance
        travel = (x - spawn_x) / direction_x
        z = spawn_z + direction_z * travel
        yaw = -math.pi / 2

    distance = math.hypot(x - spawn_x, z - spawn_z)
    minimum_angular_height = 9.5 + (signature % 4) * 0.35
    authored_height = float(dimensions["height"]) * 1.04
    height = max(authored_height, math.tan(math.radians(minimum_angular_height)) * distance)
    # A hundred-metre silhouette is already enormous at this map scale.  The
    # cap protects natural perspective and near/far precision on small maps.
    height = min(100.0, height)
    return {
        "x": x,
        "z": z,
        "yaw": yaw,
        "width": width,
        "depth": depth,
        "height": height,
        "bearingDeg": bearing,
        "distanceM": distance,
        "minimumAngularHeightDeg": minimum_angular_height,
    }


def landmark_bounds_spawn_metrics(stage, bounds):
    """Measure what the first-person spawn actually sees from exported bounds."""
    center_x = (bounds[0] + bounds[3]) * 0.5
    center_z = (bounds[2] + bounds[5]) * 0.5
    height = bounds[4] - bounds[1]
    spawn = stage["playerSpawns"][0]
    spawn_x, spawn_z = float(spawn[0]), float(spawn[2])
    to_x, to_z = center_x - spawn_x, center_z - spawn_z
    distance = math.hypot(to_x, to_z)
    bearing = signed_angle_degrees(-spawn_x, -spawn_z, to_x, to_z)
    angular_height = math.degrees(math.atan2(height, max(0.001, distance)))
    return {
        "bearingDeg": round(bearing, 3),
        "distanceM": round(distance, 3),
        "angularHeightDeg": round(angular_height, 3),
        "readable": abs(bearing) <= 32.0 and angular_height >= 8.0,
    }


def hex_rgb(value):
    value = value.lstrip("#")
    channels = tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    def to_linear(channel):
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    return tuple(to_linear(channel) for channel in channels)


def blend_rgb(a, b, amount):
    return tuple(a[i] * (1.0 - amount) + b[i] * amount for i in range(3))


def runtime_point(x, y, z):
    """Map Three runtime X/Y-up/Z into Blender X/Y/Z-up."""
    return Vector((x, -z, y))


def new_collection(name, parent=None):
    collection = bpy.data.collections.new(name)
    (parent.children if parent else bpy.context.scene.collection.children).link(collection)
    return collection


def remove_collection_tree(collection):
    for child in list(collection.children):
        remove_collection_tree(child)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)


def clear_generated():
    # Re-resolve by name on every removal.  Removing a root also removes its
    # children, so keeping StructRNA references from the original list makes a
    # second build attempt touch already-removed collections.
    collection_names = [collection.name for collection in bpy.data.collections if collection.name.startswith(PREFIX)]
    root_names = [name for name in collection_names if name.endswith("_ROOT")]
    for name in root_names + collection_names:
        collection = bpy.data.collections.get(name)
        if collection is not None:
            remove_collection_tree(collection)
    for name in [obj.name for obj in bpy.data.objects if obj.name.startswith(PREFIX)]:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            if datablock.name.startswith(PREFIX) and datablock.users == 0:
                datablocks.remove(datablock)
    for material in list(bpy.data.materials):
        if material.name.startswith("HBMAT_") and material.users == 0:
            bpy.data.materials.remove(material)
    for image in list(bpy.data.images):
        if image.name.startswith("HBIMG_") and image.users == 0:
            bpy.data.images.remove(image)


def make_surface_image(name, color, kind, size=128):
    image = bpy.data.images.new("HBIMG_" + name, width=size, height=size, alpha=False)
    image.colorspace_settings.name = "sRGB"
    seed = sum((index + 1) * ord(char) for index, char in enumerate(name)) & 0xFFFFFFFF
    stage_id = name.split("_", 1)[0]
    family = IDENTITIES.get(stage_id, ("industrial", ""))[0]
    souko_rust = hex_rgb("#73351f")
    souko_grime = hex_rgb("#202a2d")

    def to_srgb(channel):
        channel = min(1.0, max(0.0, channel))
        return channel * 12.92 if channel <= 0.0031308 else 1.055 * (channel ** (1.0 / 2.4)) - 0.055

    pixels = []
    for y in range(size):
        for x in range(size):
            index = y * size + x
            fine = stable_unit(seed, index, 0x913) - 0.5
            broad = math.sin((x + seed % 17) * 0.31) * math.sin((y + seed % 11) * 0.27)
            factor = 0.90 + fine * 0.16 + broad * 0.055
            if kind in {"wall", "wall_alt", "obstacle"}:
                if family in {"heritage", "wilderness"}:
                    # Staggered masonry with 50-100cm real-scale courses.
                    course = y // 14
                    shifted_x = x + (12 if course & 1 else 0)
                    mortar = shifted_x % 24 in {0, 1} or y % 14 in {0, 1}
                    cell_tone = stable_unit(seed, (shifted_x // 24) + course * 19, 0xB21)
                    factor *= 0.82 if mortar else 0.92 + cell_tone * 0.16
                elif family in {"military", "industrial", "airport"}:
                    # Cast-concrete/steel panel seams, bolt shadows and mild
                    # rain streaking. The grid is construction scale, not a
                    # pixel-noise substitute for geometry.
                    seam = x % 32 in {0, 1} or y % 32 in {0, 1}
                    bolt = (x % 32 in {4, 27}) and (y % 32 in {4, 27})
                    streak = max(0.0, 1.0 - (y % 32) / 32) * stable_unit(seed, x // 5, 0x319)
                    factor *= 0.76 if seam else 1.04 if bolt else 0.92 - streak * 0.075
                else:
                    course = y // 16
                    shifted_x = x + (14 if course & 1 else 0)
                    mortar = shifted_x % 28 in {0, 1} or y % 16 in {0, 1}
                    grime = stable_unit(seed, x // 8 + (y // 8) * 23, 0x911)
                    factor *= 0.72 if mortar else 0.88 + grime * 0.18
            elif kind in {"floor", "road"}:
                aggregate = stable_unit(seed, (x // 3) + (y // 3) * 47, 0xF10)
                crack = ((x * 7 + y * 11 + seed) % 97) in {0, 1}
                factor *= 0.74 if crack else 0.88 + aggregate * 0.18
            elif kind in {"natural", "terrain"}:
                coarse = stable_unit(seed, (x // 6) + (y // 6) * 31, 0xA17)
                factor *= 0.80 + coarse * 0.28
            elif kind in {"trim", "accent"}:
                scratch = ((x * 13 + y * 5 + seed) % 113) in {0, 1}
                factor *= 0.74 if scratch else 0.94 + stable_unit(seed, index // 8, 0x817) * 0.10
            pixel_color = [color[channel] * factor for channel in range(3)]
            if stage_id == "souko" and kind in {"wall", "wall_alt", "obstacle", "trim", "accent"}:
                # Deterministic tileable oxide and rain runs add real colour
                # breakup to the logistics surfaces instead of a grey scalar-
                # noise blockout. Zinc stays cooler than warm brick/steel.
                column_noise = stable_unit(seed, x // 3, 0x5017)
                drip_phase = math.sin(math.tau * (y / size + (x % 19) / 19.0))
                seam_bleed = 1.0 if x % 32 in {0, 1, 2, 29, 30, 31} else 0.0
                rust_mask = max(0.0, column_noise - 0.60) * max(0.0, 0.72 + drip_phase * 0.28)
                rust_mask += seam_bleed * stable_unit(seed, y // 5 + x * 3, 0x5018) * 0.20
                rust_weight = rust_mask * (
                    0.48 if "wall_warm" in name else 0.26 if kind in {"accent", "trim"} else 0.18
                )
                grime_weight = max(0.0, stable_unit(seed, x // 5, 0x5019) - 0.72) * (
                    0.20 + 0.18 * (y / size)
                )
                for channel in range(3):
                    pixel_color[channel] = (
                        pixel_color[channel] * (1.0 - rust_weight - grime_weight)
                        + souko_rust[channel] * rust_weight
                        + souko_grime[channel] * grime_weight
                    )
            pixels.extend((
                to_srgb(pixel_color[0]),
                to_srgb(pixel_color[1]),
                to_srgb(pixel_color[2]),
                1.0,
            ))
    image.pixels.foreach_set(pixels)
    image.pack()
    return image


def make_surface_detail_images(name, kind, roughness, size=64):
    """Create tiny deterministic PBR maps that survive GLB export.

    The maps are intentionally small and tileable.  In game they provide the
    grazing-angle breakup which makes concrete, rock and water read as a real
    surface without adding geometry or a second reflection render pass.
    """
    roughness_image = bpy.data.images.new("HBIMG_" + name + "_roughness", width=size, height=size, alpha=False)
    roughness_image.colorspace_settings.name = "Non-Color"
    normal_image = bpy.data.images.new("HBIMG_" + name + "_normal", width=size, height=size, alpha=False)
    normal_image.colorspace_settings.name = "Non-Color"
    seed = sum((index + 7) * ord(char) for index, char in enumerate(name)) & 0xFFFFFFFF
    stage_id = name.split("_", 1)[0]
    family = IDENTITIES.get(stage_id, ("industrial", ""))[0]
    roughness_pixels = []
    normal_pixels = []
    for y in range(size):
        for x in range(size):
            index = y * size + x
            u = x / size
            v = y / size
            fine = stable_unit(seed, index, 0xA53) - 0.5
            if kind == "water":
                # Two crossing capillary-wave families.  Periods divide the
                # image size, keeping the packed texture perfectly tileable.
                wave_x = math.sin(math.tau * (u * 6.0 + v * 2.0)) * 0.46 + math.sin(math.tau * v * 13.0) * 0.18
                wave_y = math.cos(math.tau * (v * 5.0 - u * 1.0)) * 0.42 + math.cos(math.tau * u * 11.0) * 0.16
                nx = 0.5 + wave_x * 0.19
                ny = 0.5 + wave_y * 0.19
                nz = 0.94
                rough = min(0.19, max(0.035, roughness + fine * 0.035 + abs(wave_x) * 0.018))
            else:
                broad_x = math.sin(math.tau * u * 4.0) * math.cos(math.tau * v * 3.0)
                broad_y = math.cos(math.tau * v * 5.0) * math.sin(math.tau * u * 2.0)
                if kind in {"wall", "wall_alt", "obstacle"}:
                    cell_x = 12 if family in {"heritage", "wilderness"} else 16
                    cell_y = 7 if family in {"heritage", "wilderness"} else 16
                    seam_x = min(x % cell_x, cell_x - (x % cell_x))
                    seam_y = min(y % cell_y, cell_y - (y % cell_y))
                    edge_x = 1.0 if seam_x <= 1 else -0.35 if seam_x == 2 else 0.0
                    edge_y = 1.0 if seam_y <= 1 else -0.35 if seam_y == 2 else 0.0
                    broad_x += edge_x * 0.85
                    broad_y += edge_y * 0.85
                strength = 0.095 if kind in {"wall", "wall_alt", "obstacle"} else 0.16 if kind in {"natural", "terrain"} else 0.07
                nx = 0.5 + (broad_x * 0.55 + fine * 0.45) * strength
                ny = 0.5 + (broad_y * 0.55 - fine * 0.45) * strength
                nz = 0.96
                rough = min(1.0, max(0.18, roughness + fine * 0.13 + broad_x * 0.035))
            roughness_pixels.extend((rough, rough, rough, 1.0))
            normal_pixels.extend((nx, ny, nz, 1.0))
    roughness_image.pixels.foreach_set(roughness_pixels)
    normal_image.pixels.foreach_set(normal_pixels)
    roughness_image.pack()
    normal_image.pack()
    return roughness_image, normal_image


def make_material(
    name,
    color,
    roughness=0.75,
    metallic=0.0,
    emission=None,
    emission_strength=0.0,
    texture_kind=None,
    uv_scale=0.12,
):
    material = bpy.data.materials.new("HBMAT_" + name)
    material.use_nodes = True
    material.diffuse_color = (*color, 1.0)
    material["hibanaUvScale"] = float(uv_scale)
    # Blender localizes node display names (for example, the Japanese UI calls
    # this node "プリンシプルBSDF").  bl_idname is stable across locales.
    bsdf = next(
        (node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"),
        None,
    )
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        if emission and emission_strength > 0:
            emission_input = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
            if emission_input:
                emission_input.default_value = (*emission, 1.0)
            strength_input = bsdf.inputs.get("Emission Strength")
            if strength_input:
                strength_input.default_value = emission_strength
        kind = name.rsplit("_", 1)[-1]
        texture_kind = texture_kind or ("wall_alt" if kind == "alt" else kind)
        if texture_kind in {"floor", "road", "wall", "wall_alt", "obstacle", "natural", "terrain", "trim", "accent"}:
            image = make_surface_image(name, color, texture_kind)
            texture = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture.name = "HB Surface Color"
            texture.image = image
            texture.extension = "REPEAT"
            texture.interpolation = "Linear"
            material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
        if texture_kind in {"floor", "road", "wall", "wall_alt", "obstacle", "natural", "terrain", "water", "trim", "accent"}:
            roughness_image, normal_image = make_surface_detail_images(name, texture_kind, roughness)
            roughness_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
            roughness_texture.name = "HB Surface Roughness"
            roughness_texture.image = roughness_image
            roughness_texture.extension = "REPEAT"
            roughness_texture.interpolation = "Linear"
            material.node_tree.links.new(roughness_texture.outputs["Color"], bsdf.inputs["Roughness"])
            normal_texture = material.node_tree.nodes.new("ShaderNodeTexImage")
            normal_texture.name = "HB Surface Normal"
            normal_texture.image = normal_image
            normal_texture.extension = "REPEAT"
            normal_texture.interpolation = "Linear"
            normal_map = material.node_tree.nodes.new("ShaderNodeNormalMap")
            normal_map.name = "HB Surface Normal Map"
            normal_map.inputs["Strength"].default_value = 0.58 if texture_kind == "water" else 0.34
            material.node_tree.links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
            material.node_tree.links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
        if kind == "water":
            # Alpha survives GLB export; the runtime completes the lightweight
            # IBL/refraction-like presentation without a planar reflection pass.
            material.diffuse_color = (*color, 0.72)
            if bsdf.inputs.get("Alpha"):
                bsdf.inputs["Alpha"].default_value = 0.72
            try:
                material.surface_render_method = "DITHERED"
            except (AttributeError, TypeError):
                try:
                    material.blend_method = "BLEND"
                except AttributeError:
                    pass
        elif kind == "glass":
            # Facade glazing is intentionally opaque smoked glass. Most panes
            # are seated over authoritative solid collision walls, so alpha
            # would promise an interior which does not exist and a map-wide
            # transparent batch would self-sort incorrectly in WebGL. Real
            # openings retain their geometry/route; the reflective PBR response
            # provides depth without a second render pass.
            material.diffuse_color = (*color, 1.0)
            if bsdf.inputs.get("Alpha"):
                bsdf.inputs["Alpha"].default_value = 1.0
            if bsdf.inputs.get("Coat Weight"):
                bsdf.inputs["Coat Weight"].default_value = 0.36
    return material


def configure_translucent_hero_glass(material, alpha, transmission):
    """Give opening-backed hero glass controlled depth without a planar pass."""
    bsdf = next(
        (
            node for node in material.node_tree.nodes
            if node.bl_idname == "ShaderNodeBsdfPrincipled"
        ),
        None,
    )
    material.diffuse_color = (*material.diffuse_color[:3], alpha)
    material["hibanaTransmissionFactor"] = float(transmission)
    if bsdf:
        if bsdf.inputs.get("Alpha"):
            bsdf.inputs["Alpha"].default_value = alpha
        transmission_input = (
            bsdf.inputs.get("Transmission Weight")
            or bsdf.inputs.get("Transmission")
        )
        if transmission_input:
            transmission_input.default_value = transmission
        if bsdf.inputs.get("IOR"):
            bsdf.inputs["IOR"].default_value = 1.47
        if bsdf.inputs.get("Coat Weight"):
            bsdf.inputs["Coat Weight"].default_value = 0.48
        if bsdf.inputs.get("Coat Roughness"):
            bsdf.inputs["Coat Roughness"].default_value = 0.16
    try:
        material.surface_render_method = "DITHERED"
    except (AttributeError, TypeError):
        try:
            material.blend_method = "BLEND"
        except AttributeError:
            pass
    return material


def build_materials(stage):
    palette = stage["palette"]
    floor = hex_rgb(palette["floor"])
    wall = hex_rgb(palette["wall"])
    obstacle = hex_rgb(palette["obstacle"])
    accent = hex_rgb(palette["accent"])
    if stage["id"] == "kairou":
        # Reference-match swatches.  Keep this visual override in the Blender
        # asset pipeline until the single-stage browser gate is approved; the
        # authoritative StageDef remains unchanged during the proof.
        floor = hex_rgb("#8f745b")
        wall = hex_rgb("#b99773")
        obstacle = hex_rgb("#806b55")
        accent = hex_rgb("#355a67")
    elif stage["id"] == "nakaniwa":
        # Reference-owned garden-palace palette.  White limestone and honey
        # sandstone carry the occupied facade depth; verdigris and brass are
        # reserved for roofs, ribs, screens and ceremonial inlay.
        floor = hex_rgb("#4d5149")
        wall = hex_rgb("#d8cdb7")
        obstacle = hex_rgb("#ad7f4d")
        accent = hex_rgb("#9a6724")
    elif stage["id"] == "souko":
        # Wet bonded-logistics swatches from the 1672x941 reference.  These
        # separate zinc, brick, concrete and sparse safety paint before the
        # shared procedural roughness/normal treatment is applied.
        floor = hex_rgb("#42494d")
        wall = hex_rgb("#687277")
        obstacle = hex_rgb("#826f55")
        accent = hex_rgb("#d77924")
    if palette.get("mood") == "night":
        floor = blend_rgb(floor, (0.17, 0.18, 0.21), 0.70)
        wall = blend_rgb(wall, (0.19, 0.20, 0.23), 0.66)
        obstacle = blend_rgb(obstacle, (0.16, 0.17, 0.20), 0.62)
    family = IDENTITIES[stage["id"]][0]
    profile = PROFILES[stage["id"]]
    natural_target = (0.055, 0.12, 0.035)
    if stage["id"] == "kairou":
        natural_target = hex_rgb("#4b593b")
    elif stage["id"] == "nakaniwa":
        natural_target = hex_rgb("#174628")
    elif profile["surface"] in {"desert-stone", "dune-sand", "canyon-stone", "quarry-gravel"}:
        natural_target = (0.27, 0.13, 0.055)
    elif family == "arctic":
        natural_target = (0.42, 0.52, 0.62)
    elif family == "geothermal" or stage["id"] in {"z05", "z09", "z10"}:
        natural_target = (0.045, 0.028, 0.024)
    elif family in {"industrial", "airport", "urban", "undead"}:
        natural_target = (0.10, 0.085, 0.065)
    # A single wall swatch across an entire district was technically PBR but
    # still read as a grey blockout in first person.  These stage-owned
    # variations share the same tiny tiling texture workflow and draw-call
    # batching, while introducing believable changes of construction period,
    # repair history and facade material.  The complete export remains well
    # below the 24-material stage budget.
    if family in {"heritage", "wilderness"}:
        warm_target = (0.34, 0.22, 0.12)
        cool_target = (0.20, 0.24, 0.25)
        roof_target = (0.08, 0.12, 0.16)
        timber_target = (0.18, 0.075, 0.028)
    elif family == "arctic":
        warm_target = (0.34, 0.36, 0.34)
        cool_target = (0.14, 0.25, 0.34)
        roof_target = (0.06, 0.12, 0.18)
        timber_target = (0.20, 0.13, 0.08)
    elif family in {"industrial", "military", "airport"}:
        warm_target = (0.27, 0.19, 0.12)
        cool_target = (0.12, 0.18, 0.22)
        roof_target = (0.045, 0.065, 0.078)
        timber_target = (0.19, 0.095, 0.045)
    elif family in {"undead", "geothermal"}:
        warm_target = (0.18, 0.085, 0.045)
        cool_target = (0.085, 0.10, 0.11)
        roof_target = (0.045, 0.035, 0.032)
        timber_target = (0.12, 0.045, 0.025)
    else:
        warm_target = (0.30, 0.16, 0.11)
        cool_target = (0.10, 0.18, 0.25)
        roof_target = (0.045, 0.06, 0.085)
        timber_target = (0.16, 0.065, 0.035)

    if stage["id"] == "kairou":
        # Sun-bleached limestone, ochre repairs and dark walnut.  The previous
        # heritage defaults pulled the cool/weathered batches toward charcoal
        # and made the otherwise valid hero structure read as blue scaffolding
        # in an eye-level exposure.
        warm_target = hex_rgb("#d3a36e")
        cool_target = hex_rgb("#a98d70")
        roof_target = hex_rgb("#795a43")
        timber_target = hex_rgb("#4c2f1e")
    elif stage["id"] == "kunren":
        # Charcoal blast roofs and zinc command decks.  Letting the red stage
        # accent dominate every roof made the training complex look like the
        # same fantasy castle used by the heritage maps.
        roof_target = hex_rgb("#263945")
    elif stage["id"] == "nakaniwa":
        # Verdigris is the palace/conservatory crown identity; orange remains
        # a sparse mosaic/wayfinding accent at pedestrian height.
        warm_target = hex_rgb("#b17d49")
        cool_target = hex_rgb("#7f978e")
        roof_target = hex_rgb("#236b68")
        timber_target = hex_rgb("#2d1b12")
    elif stage["id"] == "souko":
        warm_target = hex_rgb("#743d2d")
        cool_target = hex_rgb("#718087")
        roof_target = hex_rgb("#56666c")
        timber_target = hex_rgb("#59422e")

    wall_base = (
        hex_rgb("#b8b099")
        if stage["id"] == "nakaniwa"
        else blend_rgb(wall, (0.65, 0.67, 0.68), 0.08)
    )
    wall_alt_base = (
        blend_rgb(wall, hex_rgb("#80664e"), 0.36)
        if stage["id"] == "kairou"
        else hex_rgb("#a87946")
        if stage["id"] == "nakaniwa"
        else blend_rgb(wall, (0.04, 0.045, 0.05), 0.24)
    )
    # Reflect the local sky in a mid-value low-iron base.  Near-black smoked
    # panes repeated across hundreds of bays produced the global "black window
    # grid" failure even when the geometry itself was correct.
    glass_base = blend_rgb(hex_rgb(palette["sky"]), (0.16, 0.21, 0.24), 0.66)
    if stage["id"] == "nakaniwa":
        # The conservatory owns real opening-backed glazing.  Keep it light
        # enough that five overlapping fan lobes still read as translucent
        # botanical glass instead of accumulating into a near-black shed.
        glass_base = hex_rgb("#416f70")
    elif stage["id"] == "souko":
        # Pale, rain-dulled FRP/anti-glare glazing stays above the dark-card
        # threshold when the sawtooth north lights repeat across the terminal.
        glass_base = hex_rgb("#8d9da0")
    facade_uv_scale = 0.105 if family in {"heritage", "wilderness"} else 0.052
    materials = {
        "floor": make_material(
            stage["id"] + "_floor",
            hex_rgb("#55645b")
            if stage["id"] == "nakaniwa"
            else hex_rgb("#363e42")
            if stage["id"] == "souko"
            else blend_rgb(floor, (0.12, 0.13, 0.14), 0.15),
            0.60 if stage["id"] == "souko" else 0.88,
        ),
        "road": make_material(
            stage["id"] + "_road",
            hex_rgb("#8f8068")
            if stage["id"] == "nakaniwa"
            else blend_rgb(floor, hex_rgb("#705943"), 0.24)
            if stage["id"] == "kairou"
            else blend_rgb(floor, (0.055, 0.06, 0.065), 0.48),
            0.54 if stage["id"] == "souko" else 0.72,
        ),
        "wall": make_material(stage["id"] + "_wall", wall_base, 0.74, uv_scale=facade_uv_scale),
        "wall_alt": make_material(stage["id"] + "_wall_alt", wall_alt_base, 0.82, uv_scale=facade_uv_scale),
        "wall_warm": make_material(
            stage["id"] + "_wall_warm",
            hex_rgb("#a87946")
            if stage["id"] == "nakaniwa"
            else hex_rgb("#704034")
            if stage["id"] == "souko"
            else blend_rgb(wall_base, warm_target, 0.34),
            0.70 if stage["id"] == "souko" else 0.79,
            0.02 if stage["id"] == "souko" else 0.0,
            texture_kind="wall",
            uv_scale=facade_uv_scale,
        ),
        "wall_cool": make_material(
            stage["id"] + "_wall_cool",
            hex_rgb("#718086") if stage["id"] == "souko" else blend_rgb(wall_base, cool_target, 0.32),
            0.42 if stage["id"] == "souko" else 0.70,
            0.36 if stage["id"] == "souko" else 0.06 if family in {"industrial", "airport"} else 0.015,
            texture_kind="wall",
            uv_scale=facade_uv_scale,
        ),
        "wall_weathered": make_material(
            stage["id"] + "_wall_weathered",
            blend_rgb(wall_alt_base, hex_rgb("#876d50"), 0.30)
            if stage["id"] == "kairou"
            else hex_rgb("#555850")
            if stage["id"] == "nakaniwa"
            else hex_rgb("#4c5558")
            if stage["id"] == "souko"
            else blend_rgb(wall_alt_base, natural_target, 0.25),
            0.68 if stage["id"] == "souko" else 0.91,
            0.18 if stage["id"] == "souko" else 0.0,
            texture_kind="wall_alt",
            uv_scale=facade_uv_scale,
        ),
        "roof": make_material(
            stage["id"] + "_roof",
            hex_rgb("#586b71") if stage["id"] == "souko" else blend_rgb(hex_rgb(palette["accent"]), roof_target, 0.72),
            0.34 if stage["id"] == "souko" else 0.30 if stage["id"] == "nakaniwa" else 0.48 if family in {"industrial", "airport", "military"} else 0.76,
            0.48 if stage["id"] == "souko" else 0.58 if stage["id"] == "nakaniwa" else 0.32 if family in {"industrial", "airport", "military"} else 0.04,
            texture_kind="accent",
            uv_scale=0.075,
        ),
        "wood": make_material(
            stage["id"] + "_wood",
            timber_target,
            0.86,
            texture_kind="natural",
            uv_scale=0.18,
        ),
        "obstacle": make_material(stage["id"] + "_obstacle", obstacle, 0.68, 0.08 if family in {"industrial", "airport"} else 0.01),
        "accent": make_material(
            stage["id"] + "_accent",
            accent,
            0.38 if stage["id"] == "souko" else 0.26 if stage["id"] == "nakaniwa" else 0.46,
            0.28 if stage["id"] == "souko" else 0.76 if stage["id"] == "nakaniwa" else 0.16,
        ),
        "trim": make_material(
            stage["id"] + "_trim",
            blend_rgb(wall, hex_rgb("#594330"), 0.60)
            if stage["id"] == "kairou"
            else blend_rgb(wall, (0.025, 0.03, 0.035), 0.66),
            0.36 if stage["id"] == "souko" else 0.52,
            0.48 if stage["id"] == "souko" else 0.18 if stage["id"] == "kairou" else 0.32,
        ),
        # Keep daylight glazing close to neutral low-iron glass.  Mixing too
        # much stage accent into every pane made whole districts read as rows
        # of pink/cyan cards instead of recessed windows.
        # A neutral smoked value is more believable across all 31 palettes
        # than tinting every facade with the stage accent.  Even a small pink
        # or cyan contribution turned hundreds of opaque, collision-backed
        # panes into bright cards in first-person views.  Night identity stays
        # in the sparse emissive material; ordinary glazing remains dark,
        # reflective and visually recessed.
        "glass": make_material(stage["id"] + "_glass", glass_base, 0.28, 0.32),
        "natural": make_material(
            stage["id"] + "_natural",
            hex_rgb("#326b38")
            if stage["id"] == "nakaniwa"
            else blend_rgb(obstacle, natural_target, 0.58),
            0.82 if stage["id"] == "nakaniwa" else 0.94,
        ),
        "terrain": make_material(stage["id"] + "_terrain", blend_rgb(obstacle, natural_target, 0.24), 0.97),
        "water": make_material(
            stage["id"] + "_water",
            hex_rgb("#0a3344")
            if stage["id"] == "souko"
            else blend_rgb(hex_rgb(palette["sky"]), (0.012, 0.045, 0.065), 0.62),
            0.18 if stage["id"] == "souko" else 0.07,
            0.08 if stage["id"] == "souko" else 0.34,
        ),
        "emissive": make_material(stage["id"] + "_emissive", accent, 0.36, 0.08, accent, 1.9 if palette.get("mood") == "night" else 0.9),
    }
    if stage["id"] == "nakaniwa":
        # Reuse the stage's existing glass batch for the dark low-iron field.
        # Sparse brighter panes use the already-budgeted water response below;
        # no 17th/18th material or draw group is introduced on medium.
        materials["glass"] = configure_translucent_hero_glass(
            materials["glass"],
            0.58,
            0.28,
        )
    elif stage["id"] == "souko":
        materials["glass"] = configure_translucent_hero_glass(
            materials["glass"],
            0.84,
            0.12,
        )
        # The coast is a real closed water volume outside the east play edge.
        # At the generic 0.72 alpha it inherited too much of the grey quay
        # below and read as wet paving in player-height evidence. Souko's
        # offshore volume therefore keeps only three percent transparency;
        # wave normals and coat response retain water motion while satisfying
        # the runtime's explicit lightweight alpha-water contract.
        water = materials["water"]
        water.diffuse_color = (*water.diffuse_color[:3], 0.97)
        water_bsdf = next(
            (
                node for node in water.node_tree.nodes
                if node.bl_idname == "ShaderNodeBsdfPrincipled"
            ),
            None,
        )
        if water_bsdf:
            if water_bsdf.inputs.get("Alpha"):
                water_bsdf.inputs["Alpha"].default_value = 0.97
            if water_bsdf.inputs.get("Coat Weight"):
                water_bsdf.inputs["Coat Weight"].default_value = 0.44
            if water_bsdf.inputs.get("Coat Roughness"):
                water_bsdf.inputs["Coat Roughness"].default_value = 0.10
        materials["wall_cool"]["hibanaSurfaceRole"] = "wet-zinc-steel"
        materials["wall_warm"]["hibanaSurfaceRole"] = "wet-red-brick"
        materials["roof"]["hibanaSurfaceRole"] = "weathered-folded-zinc"
        materials["glass"]["hibanaSurfaceRole"] = "translucent-frp-antiglare"
        materials["accent"]["hibanaSurfaceRole"] = "orange-safety-paint"
        materials["water"]["hibanaSurfaceRole"] = "coastal-water-lightweight-ibl"
    return materials


def facade_material_key(stage, index, salt=0):
    """Return a deterministic construction-family variation for one mass."""
    value = stable_unit(stage["seed"] ^ (salt * 0x9E3779B1), index, 0xFACADE)
    family = IDENTITIES[stage["id"]][0]
    if family in {"undead", "geothermal"}:
        choices = ("wall_weathered", "wall_alt", "wall_warm", "wall_cool")
    elif family in {"heritage", "wilderness"}:
        choices = ("wall_warm", "wall", "wall_weathered", "wall_cool")
    elif family == "arctic":
        choices = ("wall_cool", "wall", "wall_alt", "wall_warm")
    else:
        choices = ("wall", "wall_cool", "wall_alt", "wall_warm", "wall_weathered")
    return choices[min(len(choices) - 1, int(value * len(choices)))]


def _landmark_face_frame(placement, item):
    """Return one collider box projected into its landmark entrance frame."""
    centre_x = float(placement["cx"])
    centre_z = float(placement["cz"])
    entrance_x, entrance_z = (float(value) for value in placement["entrance"])
    forward_x = entrance_x - centre_x
    forward_z = entrance_z - centre_z
    forward_length = max(1e-6, math.hypot(forward_x, forward_z))
    forward_x /= forward_length
    forward_z /= forward_length
    right_x, right_z = forward_z, -forward_x
    delta_x = float(item["x"]) - centre_x
    delta_z = float(item["z"]) - centre_z
    lateral = delta_x * right_x + delta_z * right_z
    forward = delta_x * forward_x + delta_z * forward_z
    lateral_extent = (
        abs(right_x) * float(item["w"]) + abs(right_z) * float(item["d"])
    ) / 2
    forward_extent = (
        abs(forward_x) * float(item["w"]) + abs(forward_z) * float(item["d"])
    ) / 2
    return {
        "centreX": centre_x,
        "centreZ": centre_z,
        "forwardX": forward_x,
        "forwardZ": forward_z,
        "rightX": right_x,
        "rightZ": right_z,
        "yaw": math.atan2(-forward_x, forward_z),
        "lateral": lateral,
        "forward": forward,
        "lateralExtent": lateral_extent,
        "forwardExtent": forward_extent,
    }


def souko_tower_face_specs(placement, tower, lod):
    """Return shallow logistics-tower relief seated on one real collider face.

    Connection map (runtime metres, entrance-facing tower face):
      tower face -> two vertical rails: 0.08 m embedded / 0.04 m proud;
      tower face -> four LOD0 (two LOD1) collars: same 0.12 m section;
      tower face -> central service spine: same 0.12 m section;
      service spine -> small ID lamp: 0.02 m embedded / 0.04 m proud.
      tower top edge -> hoist/customs header: its upper edge is flush with the
        authoritative tower top and keeps the same 0.12 m face section;
      tower face -> large seven-segment bay numeral: every segment uses the
        same bounded face relief, with no independent deck or cover surface;
      stackhouse face -> broad hoist door/pulley datum and block chevron;
      customs face -> broad scanner and vent backplates.  All remain wholly
        inside the tower silhouette and are facade relief, never cover.

    Every element remains inside the tower's lateral and vertical bounds.  It
    therefore reads as logistics machinery, never a balcony, ladder, cover
    lip or free-standing gantry.
    """
    if lod >= 2:
        return []
    frame = _landmark_face_frame(placement, tower)
    lateral = frame["lateral"]
    face_forward = frame["forward"] + frame["forwardExtent"]
    lateral_extent = frame["lateralExtent"]
    base = float(tower["y"]) - float(tower["h"]) / 2
    height = float(tower["h"])
    usable_bottom = base + height * 0.08
    usable_top = base + height * 0.92
    usable_height = usable_top - usable_bottom
    relief_forward = face_forward - 0.02
    specs = []

    rail_offset = lateral_extent * 0.54
    rail_width = max(0.14, lateral_extent * (0.050 if lod == 0 else 0.065))
    for side in (-1, 1):
        specs.append({
            "role": "rail",
            "lateral": lateral + side * rail_offset,
            "y": (usable_bottom + usable_top) / 2,
            "forward": relief_forward,
            "w": rail_width,
            "h": usable_height,
            "d": 0.12,
            "key": "trim",
        })

    collar_count = 4 if lod == 0 else 2
    collar_width = lateral_extent * 1.56
    collar_height = max(0.16, height * (0.010 if lod == 0 else 0.014))
    for collar in range(collar_count):
        fraction = (collar + 1) / (collar_count + 1)
        specs.append({
            "role": "collar",
            "lateral": lateral,
            "y": usable_bottom + usable_height * fraction,
            "forward": relief_forward,
            "w": collar_width,
            "h": collar_height,
            "d": 0.12,
            "key": "accent" if lod == 0 and collar in {0, collar_count - 1} else "trim",
        })

    specs.append({
        "role": "service-spine",
        "lateral": lateral,
        "y": (usable_bottom + usable_top) / 2,
        "forward": relief_forward,
        "w": max(0.24, lateral_extent * 0.090),
        "h": usable_height * 0.91,
        "d": 0.12,
        "key": "wall_warm" if lod == 0 else "wall_alt",
    })
    specs.append({
        "role": "id-light",
        "lateral": lateral + rail_offset * 0.43,
        "y": usable_bottom + usable_height * 0.73,
        "forward": face_forward + 0.01,
        "w": max(0.34, lateral_extent * 0.17),
        "h": max(0.20, height * 0.013),
        "d": 0.06,
        "key": "emissive",
    })

    landmark_id = str(placement.get("id", ""))
    is_stackhouse = landmark_id == "souko-shiosai-stackhouse"
    is_customs = landmark_id == "souko-amakado-customs-terminal"
    tower_top = base + height

    # A broad datum meets the real tower top exactly.  Its 8 cm inward / 4 cm
    # outward section is identical to the proven rail contact and cannot be
    # interpreted as a walkable transfer deck.
    specs.append({
        "role": "hoist-header" if is_stackhouse else "customs-header",
        "lateral": lateral,
        "y": tower_top - max(0.18, height * 0.008),
        "forward": relief_forward,
        "w": lateral_extent * (1.62 if lod == 0 else 1.48),
        "h": max(0.36, height * 0.016),
        "d": 0.12,
        "key": "accent" if is_stackhouse else "wall_cool",
    })

    # Large bay numerals make the four T-tower faces useful cargo addresses.
    # The tower's signed local lateral coordinate deterministically chooses
    # 1/2 for the stackhouse and 3/4 for customs without adding authored world
    # coordinates.  Seven-segment boxes overlap at their joints and all remain
    # seated on the authoritative face.
    bay_number = (1 if lateral < 0 else 2) if is_stackhouse else (3 if lateral < 0 else 4)
    digit_segments = {
        1: ("b", "c"),
        2: ("a", "b", "g", "e", "d"),
        3: ("a", "b", "g", "c", "d"),
        4: ("f", "g", "b", "c"),
    }[bay_number]
    digit_height = min(6.6, max(4.8, height * 0.18))
    digit_width = min(lateral_extent * 0.72, 2.80)
    digit_stroke = max(0.32, digit_width * (0.15 if lod == 0 else 0.19))
    # Bias each address toward the landmark centre.  The two outer towers
    # previously hid bays 1/4 behind their own T crowns in three-quarter
    # approach views, while the inner 2/3 remained legible.
    digit_bias = 0.53 if is_customs else 0.26
    digit_lateral = lateral + rail_offset * (
        digit_bias if lateral <= 0 else -digit_bias
    )
    # Customs keeps its address high so the scanner and intake can occupy the
    # primary first-person band without competing with the numeral.
    digit_y = base + height * (0.80 if is_customs else 0.72)
    specs.append({
        "role": "bay-number-backing",
        "bayNumber": bay_number,
        "lateral": digit_lateral,
        "y": digit_y,
        "forward": relief_forward,
        "w": min(lateral_extent * 0.96, digit_width + 0.66),
        "h": min(height * 0.23, digit_height + 0.86),
        # 6 cm inside / 2 cm proud: the brighter 8/4 cm digit relief sits
        # unambiguously in front instead of sharing a coplanar outer face.
        "d": 0.08,
        "key": "wall_weathered" if is_stackhouse else "wall_alt",
    })
    segment_layout = {
        "a": (0.0, digit_height / 2, digit_width, digit_stroke),
        "g": (0.0, 0.0, digit_width, digit_stroke),
        "d": (0.0, -digit_height / 2, digit_width, digit_stroke),
        "f": (-digit_width / 2, digit_height / 4, digit_stroke, digit_height / 2),
        "b": (digit_width / 2, digit_height / 4, digit_stroke, digit_height / 2),
        "e": (-digit_width / 2, -digit_height / 4, digit_stroke, digit_height / 2),
        "c": (digit_width / 2, -digit_height / 4, digit_stroke, digit_height / 2),
    }
    for segment in digit_segments:
        offset_lateral, offset_y, segment_w, segment_h = segment_layout[segment]
        specs.append({
            "role": "bay-number-segment",
            "bayNumber": bay_number,
            "segment": segment,
            "lateral": digit_lateral + offset_lateral,
            "y": digit_y + offset_y,
            "forward": relief_forward,
            "w": segment_w,
            "h": segment_h,
            "d": 0.12,
            "key": "emissive",
        })

    if is_stackhouse:
        # Large *areas*, not thin rails, carry the cargo-hoist identity at
        # player distance.  The door, pulley housing and pixel-chevron are
        # all shallow wall relief; none creates a top face usable as cover.
        door_width = lateral_extent * 1.56
        door_height = min(height * 0.27, 11.0)
        door_y = base + height * 0.29
        specs.extend((
            {
                "role": "hoist-door",
                "lateral": lateral,
                "y": door_y,
                "forward": relief_forward,
                "w": door_width,
                "h": door_height,
                "d": 0.08,
                "key": "wall_warm",
            },
            {
                "role": "pulley-datum",
                "lateral": lateral,
                "y": min(tower_top - 1.0, door_y + door_height * 0.69),
                "forward": relief_forward,
                "w": max(1.30, lateral_extent * 0.48),
                "h": max(1.20, min(2.40, height * 0.055)),
                "d": 0.12,
                "key": "accent",
            },
        ))

        chevron_y = base + height * 0.88
        chevron_step_x = max(0.48, lateral_extent * 0.18)
        chevron_step_y = max(0.48, height * 0.018)
        chevron_block_w = max(0.54, lateral_extent * 0.20)
        chevron_block_h = max(0.62, height * 0.022)
        for step_x, step_y in (
            (-2, 2), (-1, 1), (0, 0), (1, 1), (2, 2),
        ):
            specs.append({
                "role": "cable-chevron-block",
                "lateral": lateral + step_x * chevron_step_x,
                "y": chevron_y + step_y * chevron_step_y,
                "forward": relief_forward,
                "w": chevron_block_w,
                "h": chevron_block_h,
                "d": 0.12,
                "key": "wall_warm",
            })

        # The paired vertical datum and short top carriage remain secondary
        # evidence for the mechanism.  Both are face-mounted.
        guide_lateral = lateral - rail_offset * 0.34
        guide_bottom = base + height * 0.24
        guide_top = tower_top
        specs.extend((
            {
                "role": "cable-guide",
                "lateral": guide_lateral,
                "y": (guide_bottom + guide_top) / 2,
                "forward": relief_forward,
                "w": max(0.22, lateral_extent * 0.075),
                "h": guide_top - guide_bottom,
                "d": 0.12,
                "key": "wall_warm",
            },
            {
                "role": "hoist-carriage",
                "lateral": guide_lateral,
                "y": tower_top - max(0.42, height * 0.020),
                "forward": relief_forward,
                "w": max(0.90, lateral_extent * 0.46),
                "h": max(0.44, height * 0.022),
                "d": 0.12,
                "key": "accent",
            },
        ))
    elif is_customs:
        # The old vent at 28% tower height disappeared behind the terminal
        # base in every main route view. Raise both functional fields above the
        # occluder and give the scanner a deep four-sided portal frame.
        vent_centre_y = base + height * 0.43
        scan_centre_y = base + height * 0.60
        vent_span = lateral_extent * 1.66
        deep_relief_forward = face_forward - 0.04
        specs.extend((
            {
                "role": "customs-vent-block",
                "lateral": lateral,
                "y": vent_centre_y,
                "forward": deep_relief_forward,
                "w": vent_span,
                "h": min(7.2, height * 0.20),
                "d": 0.16,
                "key": "wall_alt",
            },
            {
                "role": "customs-scan-panel",
                "lateral": lateral,
                "y": scan_centre_y,
                "forward": deep_relief_forward,
                "w": lateral_extent * 1.66,
                "h": min(5.4, height * 0.18),
                "d": 0.16,
                "key": "wall_cool",
            },
        ))
        # LOD1 keeps three broad louvers over the dark vent field.
        louver_count = 6 if lod == 0 else 3
        louver_centre_y = vent_centre_y
        louver_span = min(lateral_extent * 1.48, 5.0)
        for louver in range(louver_count):
            offset = (louver - (louver_count - 1) / 2) * max(0.38, height * 0.019)
            specs.append({
                "role": "vent-louver",
                "lateral": lateral,
                "y": louver_centre_y + offset,
                "forward": relief_forward,
                "w": louver_span,
                "h": max(0.24, height * 0.010),
                "d": 0.12,
                "key": "wall_weathered",
            })
        scan_width = lateral_extent * 1.66
        scan_height = min(5.4, height * 0.18)
        frame_bar = 0.44 if lod == 0 else 0.54
        for offset_lateral, offset_y, frame_w, frame_h in (
            (-scan_width / 2 + frame_bar / 2, 0.0, frame_bar, scan_height),
            (scan_width / 2 - frame_bar / 2, 0.0, frame_bar, scan_height),
            (0.0, -scan_height / 2 + frame_bar / 2, scan_width, frame_bar),
            (0.0, scan_height / 2 - frame_bar / 2, scan_width, frame_bar),
        ):
            specs.append({
                "role": "customs-scan-frame",
                "lateral": lateral + offset_lateral,
                "y": scan_centre_y + offset_y,
                "forward": face_forward - 0.05,
                "w": frame_w,
                "h": frame_h,
                "d": 0.18,
                "key": "accent",
            })
        specs.append({
            "role": "customs-scan-datum",
            "lateral": lateral,
            "y": scan_centre_y,
            "forward": relief_forward,
            "w": scan_width * 0.68,
            "h": max(0.36, height * 0.014),
            "d": 0.12,
            "key": "emissive",
        })
        # The lower machines remain physically correct but the terminal podium
        # can occlude them from the canonical spawn. Repeat the function as one
        # compact upper badge beside (not behind) the bay numeral: a deep dark
        # field, bright frame and horizontal intake blades. Its position is
        # derived from the tower's local lateral extent and always uses the
        # outer half, leaving the address on the landmark-centre half.
        badge_side = -1.0 if lateral < 0 else 1.0
        badge_width = lateral_extent * 0.62
        badge_height = min(8.4, height * 0.28)
        badge_lateral = lateral + badge_side * lateral_extent * 0.52
        badge_y = base + height * 0.75
        specs.append({
            "role": "customs-inspection-field",
            "lateral": badge_lateral,
            "y": badge_y,
            "forward": deep_relief_forward,
            "w": badge_width,
            "h": badge_height,
            "d": 0.16,
            "key": "wall_alt",
        })
        badge_bar = 0.32 if lod == 0 else 0.42
        for offset_lateral, offset_y, frame_w, frame_h in (
            (-badge_width / 2 + badge_bar / 2, 0.0, badge_bar, badge_height),
            (badge_width / 2 - badge_bar / 2, 0.0, badge_bar, badge_height),
            (0.0, -badge_height / 2 + badge_bar / 2, badge_width, badge_bar),
            (0.0, badge_height / 2 - badge_bar / 2, badge_width, badge_bar),
        ):
            specs.append({
                "role": "customs-inspection-frame",
                "lateral": badge_lateral + offset_lateral,
                "y": badge_y + offset_y,
                "forward": face_forward - 0.05,
                "w": frame_w,
                "h": frame_h,
                "d": 0.18,
                "key": "accent",
            })
        badge_blade_count = 4 if lod == 0 else 3
        for blade in range(badge_blade_count):
            specs.append({
                "role": "customs-intake-blade",
                "lateral": badge_lateral,
                "y": (
                    badge_y - badge_height * 0.24
                    + blade * badge_height * 0.48 / max(1, badge_blade_count - 1)
                ),
                "forward": face_forward - 0.05,
                "w": badge_width * 0.66,
                "h": 0.30 if lod == 0 else 0.38,
                "d": 0.18,
                "key": "emissive",
            })
    return specs


def nakaniwa_conservatory_face_specs(
    placement, shell, lod, roof_base, fan_rear, fan_front, fan_width, fan_height,
):
    """Return stepped glass/mullion infill joined only to supported faces.

    Connection map:
      authoritative entrance wall face -> wall glass/mullions: 0.06 m inside,
        0.04 m outside the collision face;
      front/rear portal beams -> first high glass courses: >=0.08 m Y overlap;
      high glass course -> next stepped course: 0.06 m Y overlap;
      stepped glass edges -> wood mullions: coplanar 0.10 m contact section.
      front/rear authoritative upper walks -> long-side glass sill: 0.10 m
        vertical overlap, above a minimum 6.5 m ground opening;
      rear authoritative towers + front upper walks -> side wall plane: the
        chosen lateral plane lies inside both support envelopes;
      side wall eave -> sloped glass roof: 0.06 m vertical overlap along the
        computed roof plane.
      paired front interiors -> high vestibule screen: 0.10 m lateral overlap;
      front upper walk -> vestibule sill: 0.10 m vertical overlap;
      vestibule head -> existing high portal beam: one deep top tie overlaps
        both planes by 0.12 m.

    The gable infill begins at the existing roof base and the long-side infill
    begins above the upper-walk sill, so the 28 m entrance, ground route and
    player-height LOS remain untouched.
    """
    if lod >= 2:
        return []
    shell_projected = [
        (item, _landmark_face_frame(placement, item)) for item in shell
    ]
    walls = [item for item in shell if item.get("landmarkPart") == "wall"]
    projected = [
        (item, frame) for item, frame in shell_projected
        if item.get("landmarkPart") == "wall"
    ]
    if not projected:
        return []
    front = max(frame["forward"] for _, frame in projected)
    front_walls = [
        (item, frame) for item, frame in projected
        if front - frame["forward"] <= 0.25
        and frame["lateralExtent"] >= frame["forwardExtent"] * 2
    ]
    specs = []
    pane_count = 3 if lod == 0 else 2
    for item, frame in front_walls:
        face_forward = frame["forward"] + frame["forwardExtent"]
        base = float(item["y"]) - float(item["h"]) / 2
        height = float(item["h"])
        pane_bottom = base + height * 0.54
        pane_span = frame["lateralExtent"] * 1.70
        pane_width = pane_span / pane_count
        for pane in range(pane_count):
            pane_lateral = (
                frame["lateral"]
                + (pane - (pane_count - 1) / 2) * pane_width
            )
            centre_bias = 1.0 - abs(pane_lateral) / max(1.0, float(placement["width"]) / 2)
            pane_top = base + height * (0.83 + max(0.0, centre_bias) * 0.09)
            specs.append({
                "scope": "wall-glass",
                "role": "glass",
                "lateral": pane_lateral,
                "y": (pane_bottom + pane_top) / 2,
                "forward": face_forward - 0.01,
                "w": pane_width * 0.86,
                "h": pane_top - pane_bottom,
                "d": 0.10,
                "key": "water" if pane % 2 == 0 else "glass",
            })
        for mullion in range(pane_count + 1):
            mullion_lateral = frame["lateral"] - pane_span / 2 + mullion * pane_width
            specs.append({
                "scope": "wall-mullion",
                "role": "mullion",
                "lateral": mullion_lateral,
                "y": base + height * 0.72,
                "forward": face_forward - 0.01,
                "w": 0.16 if lod == 0 else 0.22,
                "h": height * 0.38,
                "d": 0.10,
                "key": "wood",
            })

    # Both vertical gable faces are already bounded by supported portal beams
    # and their sloped ribs.  Fill both ends with broad stepped courses instead
    # of adding a free-standing frame or a gameplay-height wall.  A14 closed
    # only fan_front, so the primary approach still looked through the open
    # opposite end and read the landmark as a blockout.
    band_count = 4 if lod == 0 else 2
    course_height = fan_height * 0.78 / band_count
    high_base = roof_base + 0.20
    for portal_side, portal_forward, face_sign in (
        ("rear", fan_rear, -1.0),
        ("front", fan_front, 1.0),
    ):
        # Centre is 1 cm inside the end plane: 6 cm inside / 4 cm outside.
        face_forward = portal_forward - face_sign * 0.01
        for band in range(band_count):
            band_bottom = high_base + band * course_height
            band_top = high_base + (band + 1) * course_height + (0.06 if band else 0.0)
            band_mid = (band_bottom + band_top) / 2
            rise_fraction = min(0.96, max(0.0, (band_mid - roof_base) / fan_height))
            half_width = max(fan_width * 0.075, fan_width * 0.50 * (1.0 - rise_fraction) - 0.18)
            specs.append({
                "scope": f"portal-glass-{portal_side}",
                "role": "glass",
                "portalSide": portal_side,
                "lateral": 0.0,
                "y": band_mid,
                "forward": face_forward,
                "w": half_width * 2,
                "h": band_top - band_bottom,
                "d": 0.10,
                "key": (
                    "water"
                    if (band + (0 if portal_side == "front" else 1)) % 3 == 0
                    else "glass"
                ),
            })
            for lateral in (-half_width, 0.0, half_width):
                specs.append({
                    "scope": f"portal-mullion-{portal_side}",
                    "role": "mullion",
                    "portalSide": portal_side,
                    "lateral": lateral,
                    "y": band_mid,
                    "forward": portal_forward - face_sign * 0.02,
                    "w": 0.18 if lod == 0 else 0.24,
                    "h": band_top - band_bottom + 0.10,
                    "d": 0.12,
                    "key": "wood",
                })

    # Close the two long, upper side walls that remained open in A14.  Their
    # lateral plane is not guessed from the roof silhouette: it is the shared
    # interval of the rear collision towers and the nearest front/rear
    # collision-authoritative upper walks.  The glass begins above those walk
    # beams, leaving the entire player-height entrance and route untouched.
    wide_walks = [
        (item, frame) for item, frame in shell_projected
        if item.get("landmarkPart") == "upper-walk"
        and abs(frame["lateral"]) <= 0.25
        and frame["lateralExtent"] >= fan_width * 0.25
    ]
    towers = [
        (item, frame) for item, frame in shell_projected
        if item.get("landmarkPart") == "tower"
        and abs(frame["lateral"]) >= fan_width * 0.20
    ]
    if len(wide_walks) >= 2 and len(towers) >= 2:
        rear_walk = min(wide_walks, key=lambda pair: abs(pair[1]["forward"] - fan_rear))
        front_walk = min(wide_walks, key=lambda pair: abs(pair[1]["forward"] - fan_front))
        sill_top = min(
            float(rear_walk[0]["y"]) + float(rear_walk[0]["h"]) / 2,
            float(front_walk[0]["y"]) + float(front_walk[0]["h"]) / 2,
        )
        side_bottom = max(6.5, sill_top - 0.10)
        bay_count = 4 if lod == 0 else 2
        course_count = 3 if lod == 0 else 2
        side_depth = fan_front - fan_rear
        bay_depth = side_depth / bay_count
        pane_gap = 0.34 if lod == 0 else 0.52

        for side_sign in (-1.0, 1.0):
            side_towers = [
                (item, frame) for item, frame in towers
                if frame["lateral"] * side_sign > 0
            ]
            if not side_towers:
                continue
            _, side_tower = min(
                side_towers,
                key=lambda pair: abs(pair[1]["forward"] - fan_rear),
            )
            tower_inner = abs(side_tower["lateral"]) - side_tower["lateralExtent"]
            tower_outer = abs(side_tower["lateral"]) + side_tower["lateralExtent"]
            walk_limit = min(
                rear_walk[1]["lateralExtent"],
                front_walk[1]["lateralExtent"],
            )
            side_lateral_abs = min(
                fan_width / 2 - 0.30,
                tower_outer - 0.08,
                walk_limit - 0.08,
            )
            side_lateral_abs = max(tower_inner + 0.08, side_lateral_abs)
            if side_lateral_abs > tower_outer - 0.04:
                continue
            side_lateral = side_sign * side_lateral_abs
            roof_contact_y = roof_base + fan_height * (
                1.0 - side_lateral_abs / max(0.001, fan_width / 2)
            )
            side_top = roof_contact_y + 0.06
            side_height = side_top - side_bottom
            if side_height <= 0.5:
                continue
            course_height = side_height / course_count

            for course in range(course_count):
                course_bottom = side_bottom + course * course_height
                course_top = side_bottom + (course + 1) * course_height
                for bay in range(bay_count):
                    bay_forward = fan_rear + (bay + 0.5) * bay_depth
                    specs.append({
                        "scope": "side-glass-left" if side_sign < 0 else "side-glass-right",
                        "role": "glass",
                        "sideSign": side_sign,
                        "course": course,
                        "bay": bay,
                        "lateral": side_lateral,
                        "y": (course_bottom + course_top) / 2,
                        "forward": bay_forward,
                        "w": 0.10,
                        "h": max(0.20, course_top - course_bottom - 0.18),
                        "d": max(0.80, bay_depth - pane_gap),
                        "key": (
                            "water"
                            if (course + bay + (1 if side_sign > 0 else 0)) % 4 == 0
                            else "glass"
                        ),
                    })

            for mullion in range(bay_count + 1):
                specs.append({
                    "scope": "side-mullion-left" if side_sign < 0 else "side-mullion-right",
                    "role": "mullion",
                    "sideSign": side_sign,
                    "lateral": side_lateral,
                    "y": (side_bottom + side_top) / 2,
                    "forward": fan_rear + mullion * bay_depth,
                    "w": 0.14,
                    "h": side_height,
                    "d": 0.26 if lod == 0 else 0.34,
                    "key": "wood",
                })
            for course in range(1, course_count):
                specs.append({
                    "scope": "side-transom-left" if side_sign < 0 else "side-transom-right",
                    "role": "transom",
                    "sideSign": side_sign,
                    "lateral": side_lateral,
                    "y": side_bottom + course * course_height,
                    "forward": (fan_rear + fan_front) / 2,
                    "w": 0.16,
                    "h": 0.26 if lod == 0 else 0.34,
                    "d": side_depth,
                    "key": "wood",
                })
            specs.append({
                "scope": "side-eave-left" if side_sign < 0 else "side-eave-right",
                "role": "eave",
                "sideSign": side_sign,
                "lateral": side_lateral,
                "y": roof_contact_y,
                "forward": (fan_rear + fan_front) / 2,
                "w": 0.18,
                "h": 0.28,
                "d": side_depth,
                "key": "wood",
            })

    # Close the previously sky-filled upper entrance with a supported inner
    # vestibule.  Its plane is derived from the paired front interiors, whose
    # inner edges define the authoritative 28 m opening.  The screen begins on
    # the front upper walk (well above 4 m) and a deep head tie reaches the
    # existing portal beam at fan_front.  Ground traversal and eye-height LOS
    # therefore remain completely unchanged.
    front_interiors = [
        (item, frame) for item, frame in shell_projected
        if item.get("landmarkPart") == "interior"
        and frame["forward"] <= fan_front + 0.25
        and frame["lateralExtent"] >= frame["forwardExtent"] * 2
    ]
    front_upper_walks = [
        (item, frame) for item, frame in shell_projected
        if item.get("landmarkPart") == "upper-walk"
        and abs(frame["lateral"]) <= 0.25
        and frame["forward"] <= fan_front + 0.25
        and frame["lateralExtent"] >= fan_width * 0.25
    ]
    left_interiors = [pair for pair in front_interiors if pair[1]["lateral"] < 0]
    right_interiors = [pair for pair in front_interiors if pair[1]["lateral"] > 0]
    if left_interiors and right_interiors and front_upper_walks:
        left_item, left_frame = max(left_interiors, key=lambda pair: pair[1]["forward"])
        right_item, right_frame = max(right_interiors, key=lambda pair: pair[1]["forward"])
        upper_item, upper_frame = max(front_upper_walks, key=lambda pair: pair[1]["forward"])
        left_inner = left_frame["lateral"] + left_frame["lateralExtent"]
        right_inner = right_frame["lateral"] - right_frame["lateralExtent"]
        opening_width = right_inner - left_inner
        if 27.5 <= opening_width <= 28.5:
            vestibule_centre = (left_inner + right_inner) / 2
            vestibule_width = opening_width + 0.20
            vestibule_forward = (
                left_frame["forward"] + right_frame["forward"]
            ) / 2
            walk_top = float(upper_item["y"]) + float(upper_item["h"]) / 2
            vestibule_bottom = max(4.0, walk_top - 0.10)
            portal_y = roof_base + 0.28
            vestibule_top = portal_y + 0.10
            vestibule_height = vestibule_top - vestibule_bottom
            if vestibule_height > 1.0:
                pane_columns = 4 if lod == 0 else 2
                pane_rows = 3 if lod == 0 else 2
                column_width = vestibule_width / pane_columns
                row_height = vestibule_height / pane_rows
                for row in range(pane_rows):
                    for column in range(pane_columns):
                        specs.append({
                            "scope": "vestibule-glass",
                            "role": "glass",
                            "row": row,
                            "column": column,
                            "lateral": (
                                vestibule_centre - vestibule_width / 2
                                + (column + 0.5) * column_width
                            ),
                            "y": vestibule_bottom + (row + 0.5) * row_height,
                            "forward": vestibule_forward,
                            "w": max(0.80, column_width - (0.30 if lod == 0 else 0.44)),
                            "h": max(0.80, row_height - (0.28 if lod == 0 else 0.40)),
                            "d": 0.10,
                            "key": (
                                "water"
                                if (row * 2 + column) % 5 == 0
                                else "glass"
                            ),
                        })
                for column in range(pane_columns + 1):
                    specs.append({
                        "scope": "vestibule-mullion",
                        "role": "mullion",
                        "lateral": (
                            vestibule_centre - vestibule_width / 2
                            + column * column_width
                        ),
                        "y": (vestibule_bottom + vestibule_top) / 2,
                        "forward": vestibule_forward,
                        "w": 0.20 if lod == 0 else 0.28,
                        "h": vestibule_height,
                        "d": 0.14,
                        "key": "wood",
                    })
                for row in range(1, pane_rows):
                    specs.append({
                        "scope": "vestibule-crossbar",
                        "role": "crossbar",
                        "lateral": vestibule_centre,
                        "y": vestibule_bottom + row * row_height,
                        "forward": vestibule_forward,
                        "w": vestibule_width,
                        "h": 0.26 if lod == 0 else 0.34,
                        "d": 0.14,
                        "key": "wood",
                    })
                tie_depth = fan_front - vestibule_forward + 0.24
                specs.append({
                    "scope": "vestibule-top-tie",
                    "role": "top-tie",
                    "lateral": vestibule_centre,
                    "y": portal_y,
                    "forward": (vestibule_forward + fan_front) / 2,
                    "w": vestibule_width,
                    "h": 0.44,
                    "d": tie_depth,
                    "key": "wood",
                })
                # A second, recessed timber cage creates visible parallax
                # through the translucent panes. Side returns overlap the
                # front mullions and rear cage by 10 cm, so none of this high
                # visual-only structure floats. All bottoms inherit the proven
                # >=4 m vestibule clearance.
                recess_depth = min(
                    3.6,
                    max(2.4, fan_front - vestibule_forward - 0.42),
                )
                recess_forward = vestibule_forward - recess_depth
                return_depth = recess_depth + 0.20
                for side_lateral in (
                    vestibule_centre - vestibule_width / 2,
                    vestibule_centre + vestibule_width / 2,
                ):
                    specs.append({
                        "scope": "vestibule-return",
                        "role": "return",
                        "lateral": side_lateral,
                        "y": (vestibule_bottom + vestibule_top) / 2,
                        "forward": (vestibule_forward + recess_forward) / 2,
                        "w": 0.32 if lod == 0 else 0.42,
                        "h": vestibule_height,
                        "d": return_depth,
                        "key": "wood",
                    })
                rear_columns = 5 if lod == 0 else 3
                rear_column_width = vestibule_width / (rear_columns - 1)
                for column in range(rear_columns):
                    specs.append({
                        "scope": "vestibule-recess-mullion",
                        "role": "recess-mullion",
                        "lateral": (
                            vestibule_centre - vestibule_width / 2
                            + column * rear_column_width
                        ),
                        "y": (vestibule_bottom + vestibule_top) / 2,
                        "forward": recess_forward,
                        "w": 0.34 if lod == 0 else 0.46,
                        "h": vestibule_height,
                        "d": 0.34,
                        "key": "wood",
                    })
                rear_rows = 2 if lod == 0 else 1
                for row in range(1, rear_rows + 1):
                    specs.append({
                        "scope": "vestibule-recess-crossbar",
                        "role": "recess-crossbar",
                        "lateral": vestibule_centre,
                        "y": vestibule_bottom + vestibule_height * row / (rear_rows + 1),
                        "forward": recess_forward,
                        "w": vestibule_width,
                        "h": 0.36 if lod == 0 else 0.48,
                        "d": 0.34,
                        "key": "wood",
                    })
                # Three narrow opaque service fins provide dark/light response
                # and interior scale without filling the 28 m screen with a
                # second flat plane.
                fin_count = 3 if lod == 0 else 2
                for fin in range(fin_count):
                    fin_fraction = (fin + 1) / (fin_count + 1)
                    specs.append({
                        "scope": "vestibule-recess-fin",
                        "role": "recess-fin",
                        "lateral": (
                            vestibule_centre - vestibule_width / 2
                            + vestibule_width * fin_fraction
                        ),
                        "y": vestibule_bottom + vestibule_height * (0.40 + 0.12 * (fin % 2)),
                        "forward": recess_forward + 0.22,
                        "w": 1.10 if lod == 0 else 1.34,
                        "h": vestibule_height * 0.54,
                        "d": 0.62,
                        "key": "wall_cool" if fin % 2 == 0 else "wall_weathered",
                    })
    return specs


def stage_central_camera_views(stage):
    """Mirror the two deterministic player-height central render cameras."""
    half = float(stage["size"]) / 2
    return (
        {
            "viewId": "central-street-north",
            "cameraX": 0.0,
            "cameraZ": half * 0.22,
            "targetX": 0.0,
            "targetZ": -half * 0.34,
        },
        {
            "viewId": "central-street-south",
            "cameraX": 0.0,
            "cameraZ": -half * 0.22,
            "targetX": 0.0,
            "targetZ": half * 0.34,
        },
    )


def stage_authoritative_wayfinding_specs(stage, lod):
    """Choose central-street collider walls and return shallow signage.

    Connection map:
      selected Kunren wall face -> filled sign: 0.06 m embedded / 0.04 m
        proud, with its four-block direction glyph 0.02 m embedded / 0.06 m
        proud;
      other selected solid wall face -> sign/emissive slit: 0.06 m embedded
        / 0.04 m proud.

    Selection uses district tags and actual audit-camera frusta.  Kunren picks
    the nearest X-span wall whose physical face intersects each opposing
    central view, then uses the face normal that points back to that camera.
    No wall index or authored sign coordinate is baked into the art pass.
    """
    stage_id = stage["id"]
    if lod >= 2 or stage_id not in {"kunren", "souko", "nakaniwa"}:
        return []
    preferred_district = {
        "kunren": "arena",
        "souko": "hangar",
        "nakaniwa": "villa",
    }[stage_id]
    candidates = []
    for index, box in enumerate(stage["boxes"]):
        if (
            box.get("district") != preferred_district
            or box.get("landmarkId")
            or box.get("visualReplacement")
            or float(box["h"]) < 4.0
            or min(float(box["w"]), float(box["d"])) > 1.25
            or max(float(box["w"]), float(box["d"])) < 8.0
        ):
            continue
        candidates.append((
            math.hypot(float(box["x"]), float(box["z"])),
            index,
            box,
        ))
    if not candidates:
        return []
    if stage_id == "kunren":
        selected = []
        # Blender's 31 mm audit camera on a 36 mm sensor has this exact
        # horizontal half-angle.  Requiring enough in-frustum wall for the
        # whole sign catches both prior failure modes: a nearby off-screen wall
        # and a correct wall with relief on its back face.
        half_fov_tangent = 36.0 / (2.0 * 31.0)
        sign_span = 9.0
        for view in stage_central_camera_views(stage):
            forward_x = view["targetX"] - view["cameraX"]
            forward_z = view["targetZ"] - view["cameraZ"]
            forward_length = max(1e-6, math.hypot(forward_x, forward_z))
            forward_x /= forward_length
            forward_z /= forward_length
            visible = []
            for _, candidate_index, candidate in candidates:
                # The canonical cameras look along Z.  A Z-thickness wall is
                # the only face with usable projected area; X-thickness walls
                # are edge-on and cannot carry a readable stage sign.
                if float(candidate["w"]) < float(candidate["d"]):
                    continue
                to_x = float(candidate["x"]) - view["cameraX"]
                to_z = float(candidate["z"]) - view["cameraZ"]
                forward_distance = to_x * forward_x + to_z * forward_z
                if forward_distance <= 1.0:
                    continue
                viewport_half = forward_distance * half_fov_tangent
                wall_min = float(candidate["x"]) - float(candidate["w"]) / 2
                wall_max = float(candidate["x"]) + float(candidate["w"]) / 2
                allowed_min = max(
                    wall_min + sign_span / 2,
                    view["cameraX"] - viewport_half + sign_span / 2,
                )
                allowed_max = min(
                    wall_max - sign_span / 2,
                    view["cameraX"] + viewport_half - sign_span / 2,
                )
                if allowed_min > allowed_max:
                    continue
                tangent = min(allowed_max, max(allowed_min, view["cameraX"]))
                visible.append((
                    forward_distance,
                    abs(tangent - view["cameraX"]),
                    candidate_index,
                    candidate,
                    view,
                    tangent,
                    viewport_half,
                ))
            if visible:
                selected.append(min(visible, key=lambda item: item[:3]))
    else:
        selected = [min(candidates, key=lambda item: (item[0], item[1]))]

    specs = []
    for selection in selected:
        if stage_id == "kunren":
            (
                camera_distance, _, selected_index, wall, view,
                sign_tangent, viewport_half,
            ) = selection
        else:
            _, selected_index, wall = selection
            view = None
            sign_tangent = None
            camera_distance = None
            viewport_half = None
        long_x = float(wall["w"]) >= float(wall["d"])
        span = float(wall["w"] if long_x else wall["d"])
        thickness = float(wall["d"] if long_x else wall["w"])
        normal_coordinate = float(wall["z"] if long_x else wall["x"])
        if view is not None:
            camera_normal_coordinate = (
                view["cameraZ"] if long_x else view["cameraX"]
            )
            side = 1.0 if camera_normal_coordinate >= normal_coordinate else -1.0
        else:
            side = -1.0 if normal_coordinate > 0 else 1.0
        face = normal_coordinate + side * thickness / 2
        base = float(wall["y"]) - float(wall["h"]) / 2
        sign_y = base + float(wall["h"]) * 0.58

        if stage_id == "kunren":
            sign_span = min(span - 1.0, 9.0)
            sign_height = min(float(wall["h"]) * 0.40, 4.0)
            slit_span, slit_height = sign_span * 0.86, sign_height * 0.68
            # The stage's ordinary accent is intentionally non-emissive and
            # merged into the grey military palette; on a 31 mm player view a
            # large plate still disappeared into the collider wall.  Reusing
            # the already-budgeted emissive batch makes the *filled area*
            # readable, while the dark four-block glyph remains non-text.
            sign_key = "emissive"
        elif stage_id == "souko":
            sign_span = min(span * 0.18, 2.5)
            sign_height = min(float(wall["h"]) * 0.34, 2.6)
            slit_span, slit_height = sign_span * 0.72, 0.18
            sign_key = "wall_warm"
        else:
            sign_span = min(span * 0.34, 3.8)
            sign_height = min(float(wall["h"]) * 0.20, 1.30)
            slit_span, slit_height = 0.18, sign_height * 0.62
            sign_key = "wood"

        if view is not None:
            target_distance = math.hypot(
                view["targetX"] - view["cameraX"],
                view["targetZ"] - view["cameraZ"],
            )
            sightline_y = 1.65 + (5.0 - 1.65) * min(
                1.0, camera_distance / max(0.001, target_distance),
            )
            sign_y = min(
                base + float(wall["h"]) - sign_height / 2,
                max(base + sign_height / 2, sightline_y + 0.65),
            )
            tangent_origin = sign_tangent - (
                float(wall["x"]) if long_x else float(wall["z"])
            )
        else:
            tangent_origin = 0.0

        def face_box(
            role, tangent, y, tangent_span, height, key,
            depth=0.10, outside=0.04,
        ):
            normal_centre = face + side * (outside - depth / 2)
            common = {
                "role": role,
                "y": y,
                "h": height,
                "key": key,
                "wallIndex": selected_index,
                "faceSign": side,
            }
            if view is not None:
                common.update({
                    "viewId": view["viewId"],
                    "cameraX": view["cameraX"],
                    "cameraZ": view["cameraZ"],
                    "targetX": view["targetX"],
                    "targetZ": view["targetZ"],
                    "cameraDistance": camera_distance,
                    "viewportHalfSpan": viewport_half,
                })
            if long_x:
                return {
                    **common,
                    "x": float(wall["x"]) + tangent,
                    "z": normal_centre,
                    "w": tangent_span,
                    "d": depth,
                }
            return {
                **common,
                "x": normal_centre,
                "z": float(wall["z"]) + tangent,
                "w": depth,
                "d": tangent_span,
            }

        if stage_id == "kunren":
            specs.append(face_box(
                "sign", tangent_origin, sign_y, sign_span, sign_height,
                sign_key, depth=0.10, outside=0.04,
            ))
            # A filled pixel arrow survives native 1280x720 player views. Its
            # direction is expressed in screen space for each opposing camera,
            # not by a hard-coded world-side wall index.
            screen_right_world = (
                1.0 if view["targetZ"] < view["cameraZ"] else -1.0
            )
            glyph_specs = (
                (-0.50 * screen_right_world, 0.0, 3.00, 0.70, "direction-glyph-shaft"),
                (2.00 * screen_right_world, 0.0, 1.10, 1.10, "direction-glyph-tip"),
                (1.00 * screen_right_world, 1.00, 1.10, 1.10, "direction-glyph-head"),
                (1.00 * screen_right_world, -1.00, 1.10, 1.10, "direction-glyph-head"),
            )
            for offset_tangent, offset_y, glyph_w, glyph_h, role in glyph_specs:
                specs.append(face_box(
                    role,
                    tangent_origin + offset_tangent,
                    sign_y + offset_y,
                    glyph_w,
                    glyph_h,
                    "trim",
                    depth=0.08,
                    outside=0.06,
                ))
        else:
            specs.append(face_box("sign", tangent_origin, sign_y, sign_span, sign_height, sign_key))
            slit_offset = sign_height * (0.22 if stage_id != "nakaniwa" else 0.0)
            tangent_offset = tangent_origin + sign_span * (0.18 if stage_id == "nakaniwa" else 0.0)
            specs.append(face_box(
                "emissive-slit", tangent_offset, sign_y + slit_offset,
                slit_span, slit_height, "emissive",
            ))
        if lod == 0:
            # One attached trim, oriented differently per stage, is enough to
            # create a local sign family without becoming a generic facade kit.
            if stage_id == "kunren":
                specs.append(face_box(
                    "stage-trim", tangent_origin, sign_y + sign_height * 0.40,
                    sign_span * 0.86, 0.20, "emissive",
                    depth=0.08, outside=0.04,
                ))
            elif stage_id == "souko":
                specs.append(face_box("stage-trim", 0.0, sign_y - sign_height * 0.34, sign_span * 1.08, 0.14, "trim"))
            else:
                specs.append(face_box("stage-trim", 0.0, sign_y + sign_height * 0.54, sign_span * 1.10, 0.14, "roof"))
    return specs


def add_stage_authoritative_wayfinding(builder, stage, lod):
    for spec in stage_authoritative_wayfinding_specs(stage, lod):
        builder.add_box(
            spec["x"], spec["y"], spec["z"],
            spec["w"], spec["h"], spec["d"], spec["key"],
        )


class MeshBuilder:
    def __init__(self, collection, prefix, materials, bevel=0.0):
        self.collection = collection
        self.prefix = prefix
        self.materials = materials
        self.bevel = bevel
        self.parts = {}
        self.facade_glass_metrics = []
        self.facade_dark_card_count = 0
        self.facade_dark_card_breakdown = {}
        self.orphan_remediation = {"seatedCount": 0, "bracedCount": 0, "bracePylonCount": 0}

    @staticmethod
    def _is_thin_vertical_card(width, height, depth):
        """Mirror the independent GLB gate's oriented card dimensions."""
        thickness = min(float(width), float(depth))
        face_width = max(float(width), float(depth))
        face_height = float(height)
        face_area = face_width * face_height
        return (
            thickness <= 0.22
            and 0.35 <= face_width <= 4.8
            and 0.45 <= face_height <= 3.2
            and 0.30 <= face_area <= 20.0
        )

    def _material_luminance_and_transparency(self, key):
        material = self.materials[key]
        bsdf = material.node_tree.nodes.get("Principled BSDF") if material.use_nodes else None
        rgba = tuple(bsdf.inputs["Base Color"].default_value) if bsdf else tuple(material.diffuse_color)
        luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
        alpha = rgba[3] if len(rgba) > 3 else 1.0
        transmission = float(material.get("hibanaTransmissionFactor", 0.0))
        transparent = material.surface_render_method == "DITHERED" or alpha < 0.9 or transmission >= 0.25
        return luminance, transparent

    def _is_dark_card_material(self, key):
        if key not in {"wall_alt", "wall_cool", "glass", "accent"}:
            return False
        luminance, transparent = self._material_luminance_and_transparency(key)
        return (
            not transparent and luminance < 0.055
            if key == "glass"
            else luminance < 0.11
        )

    def _record_facade_dark_card(self, width, height, depth, key):
        """Count rejected thin, vertical, dark facade-card geometry.

        The Kairou reference uses relief, punched stone and open timber work;
        a shallow wall_alt/cool/glass/accent rectangle instead reads as a
        black or cyan UI card from first person.  Counting at primitive author
        time catches both axis-aligned and rotated exterior-city batches before
        they are merged by material and become difficult to audit in the GLB.
        Horizontal paving/roof trim is excluded by the vertical-height gate.
        """
        if not self._is_dark_card_material(key):
            return
        if self._is_thin_vertical_card(width, height, depth):
            self.facade_dark_card_count += 1
            self.facade_dark_card_breakdown[key] = self.facade_dark_card_breakdown.get(key, 0) + 1

    def _sanitize_facade_key(self, width, height, depth, key):
        """Convert rejected dark-card primitives into solid facade relief.

        This is a construction rule, not a metric loophole: the replacement
        material remains opaque, close in value to the supporting masonry and
        intentionally cannot produce a black/cyan plate under exposure.  Real
        cloth must use a sagged mesh and open screens must use separate bars,
        so neither belongs in this thin-box fallback.
        """
        is_kairou = self.prefix.startswith("HB_kairou_")
        # Kairou's accent is permitted only on explicitly curved cloth or
        # slender armillary/ceramic details authored by non-box primitives.
        # Every accent/cool/alt box—including horizontal roof plates and large
        # cover cubes—was responsible for the repeated cyan slab language in
        # the rejected proof, so box construction is warm masonry by rule.
        if is_kairou and key == "accent":
            return "wall_warm"
        if is_kairou and key in {"wall_alt", "wall_cool"}:
            return "wall_weathered"
        if is_kairou and key == "glass" and self._is_thin_vertical_card(width, height, depth):
            return "wall_weathered"
        # Across the remaining catalog, a genuinely dark thin rectangle is a
        # closed shutter/service repair, never a screen-space black window.
        # Reassign it to the brightest solid wall family while preserving the
        # same physical relief and UV density.  Real mid-value glass remains
        # glass and is still audited by pane/repetition/clearance metadata.
        if self._is_thin_vertical_card(width, height, depth) and self._is_dark_card_material(key):
            solid_keys = ("wall", "wall_warm", "wall_weathered")
            return max(
                solid_keys,
                key=lambda material_key: self._material_luminance_and_transparency(material_key)[0],
            )
        return key

    def record_facade_glass(self, width, height, wall_clearance, frame_recess):
        """Record one intentionally recessed facade pane for release QA.

        Decorative glass such as observatory domes is excluded: this metric is
        specifically the repeated rectangular facade pattern that previously
        produced the global black-window-grid failure.
        """
        self.facade_glass_metrics.append((
            round(float(width), 3),
            round(float(height), 3),
            round(float(wall_clearance), 4),
            round(float(frame_recess), 4),
        ))

    def _part(self, key):
        return self.parts.setdefault(key, {"verts": [], "faces": []})

    def add_box_blender(self, center, size, key="wall"):
        part = self._part(key)
        base = len(part["verts"])
        cx, cy, cz = center
        hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
        part["verts"].extend([
            (cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
            (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
            (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
            (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz),
        ])
        part["faces"].extend([
            (base + 0, base + 3, base + 2, base + 1),
            (base + 4, base + 5, base + 6, base + 7),
            (base + 0, base + 1, base + 5, base + 4),
            (base + 1, base + 2, base + 6, base + 5),
            (base + 2, base + 3, base + 7, base + 6),
            (base + 3, base + 0, base + 4, base + 7),
        ])

    def add_box(self, x, y, z, w, h, d, key="wall"):
        key = self._sanitize_facade_key(w, h, d, key)
        self._record_facade_dark_card(w, h, d, key)
        center = runtime_point(x, y, z)
        self.add_box_blender(center, (w, d, h), key)

    def add_oriented_box(self, x, y, z, w, h, d, yaw=0.0, key="wall"):
        """Add a Y-up box with an arbitrary runtime-space yaw.

        Stage prop placements carry continuous yaw jitter.  Baking that
        transform into the merged mesh lets Blender replace the old axis-
        aligned JavaScript props without adding an object/draw call per item.
        """
        key = self._sanitize_facade_key(w, h, d, key)
        self._record_facade_dark_card(w, h, d, key)
        part = self._part(key)
        base = len(part["verts"])
        hw, hh, hd = w / 2, h / 2, d / 2
        cosine = math.cos(yaw)
        sine = math.sin(yaw)
        runtime_vertices = []
        for lx, ly, lz in (
            (-hw, -hh, -hd), (hw, -hh, -hd), (hw, -hh, hd), (-hw, -hh, hd),
            (-hw, hh, -hd), (hw, hh, -hd), (hw, hh, hd), (-hw, hh, hd),
        ):
            rx = x + lx * cosine - lz * sine
            rz = z + lx * sine + lz * cosine
            runtime_vertices.append((rx, y + ly, rz))
        part["verts"].extend(tuple(runtime_point(*vertex)) for vertex in runtime_vertices)
        part["faces"].extend([
            (base + 0, base + 3, base + 2, base + 1),
            (base + 4, base + 5, base + 6, base + 7),
            (base + 0, base + 1, base + 5, base + 4),
            (base + 1, base + 2, base + 6, base + 5),
            (base + 2, base + 3, base + 7, base + 6),
            (base + 3, base + 0, base + 4, base + 7),
        ])

    def add_cylinder_between(self, start_runtime, end_runtime, radius, key="trim", segments=10, end_radius=None):
        """Add a capped low-poly cylinder between arbitrary runtime points."""
        start = runtime_point(*start_runtime)
        end = runtime_point(*end_runtime)
        forward = end - start
        if forward.length < 1e-5:
            return
        forward.normalize()
        reference = Vector((0, 0, 1)) if abs(forward.z) < 0.94 else Vector((1, 0, 0))
        right = forward.cross(reference).normalized()
        up = right.cross(forward).normalized()
        end_radius = radius if end_radius is None else end_radius
        part = self._part(key)
        base = len(part["verts"])
        for center, ring_radius in ((start, radius), (end, end_radius)):
            for index in range(segments):
                angle = math.tau * index / segments
                point = center + right * math.cos(angle) * ring_radius + up * math.sin(angle) * ring_radius
                part["verts"].append(tuple(point))
        part["verts"].append(tuple(start))
        part["verts"].append(tuple(end))
        bottom_center = base + segments * 2
        top_center = bottom_center + 1
        for index in range(segments):
            nxt = (index + 1) % segments
            part["faces"].append((base + index, base + nxt, base + segments + nxt, base + segments + index))
            part["faces"].append((bottom_center, base + nxt, base + index))
            part["faces"].append((top_center, base + segments + index, base + segments + nxt))

    def add_tube(self, points_runtime, radius, segments, key="trim", end_radius=None):
        """One continuous, capped tube through an ordered list of >=2 runtime
        points, sharing cross-section rings at every internal joint so only
        the two true endpoints are capped. Chaining add_cylinder_between per
        segment instead would cap every internal joint too, roughly doubling
        triangle cost for a long polyline (verified: nakaniwa's own reference
        kit's sweep primitive, ported in
        tools/blender/stage_kits/nakaniwa_a23_reconciliation.py, costs
        ``2*segments*(n-1) + 2*segments`` triangles for this reason -- see
        that module's ``emit_specs_to_mesh_builder``, which is this method's
        only current caller). Ring orientation uses one fixed frame derived
        from the polyline's overall start->end direction (not a per-ring
        Frenet frame): every radius here is small relative to the curves'
        span, so the resulting slight cross-section ellipticity on a curving
        polyline is not visible, and a fixed frame can never twist between
        rings the way a per-ring-recomputed one can.
        """
        points = [runtime_point(*point) for point in points_runtime]
        count = len(points)
        if count < 2:
            return
        end_radius = radius if end_radius is None else end_radius
        overall = points[-1] - points[0]
        if overall.length < 1e-6:
            overall = points[1] - points[0]
        if overall.length < 1e-6:
            return
        forward = overall.normalized()
        reference = Vector((0, 0, 1)) if abs(forward.z) < 0.94 else Vector((1, 0, 0))
        right = forward.cross(reference).normalized()
        up = right.cross(forward).normalized()
        part = self._part(key)
        ring_starts = []
        for index, point in enumerate(points):
            ring_radius = end_radius if index == count - 1 else radius
            ring_starts.append(len(part["verts"]))
            for side in range(segments):
                angle = math.tau * side / segments
                vertex = point + right * math.cos(angle) * ring_radius + up * math.sin(angle) * ring_radius
                part["verts"].append(tuple(vertex))
        for index in range(count - 1):
            r0, r1 = ring_starts[index], ring_starts[index + 1]
            for side in range(segments):
                nxt = (side + 1) % segments
                part["faces"].append((r0 + side, r0 + nxt, r1 + nxt, r1 + side))
        bottom_center = len(part["verts"])
        part["verts"].append(tuple(points[0]))
        top_center = bottom_center + 1
        part["verts"].append(tuple(points[-1]))
        for side in range(segments):
            nxt = (side + 1) % segments
            part["faces"].append((bottom_center, ring_starts[0] + nxt, ring_starts[0] + side))
            part["faces"].append((top_center, ring_starts[-1] + side, ring_starts[-1] + nxt))

    def add_oriented_gable_roof(self, x, base_y, z, width, roof_height, depth, yaw=0.0, key="accent"):
        """Add a watertight gabled roof with arbitrary plan rotation."""
        half_w = width / 2
        half_d = depth / 2
        cosine = math.cos(yaw)
        sine = math.sin(yaw)

        def world(lx, ly, lz):
            return (
                x + lx * cosine - lz * sine,
                ly,
                z + lx * sine + lz * cosine,
            )

        runtime_vertices = [
            world(-half_w, base_y, -half_d), world(half_w, base_y, -half_d),
            world(-half_w, base_y, half_d), world(half_w, base_y, half_d),
            world(-half_w, base_y + roof_height, 0), world(half_w, base_y + roof_height, 0),
        ]
        part = self._part(key)
        base = len(part["verts"])
        part["verts"].extend(tuple(runtime_point(*vertex)) for vertex in runtime_vertices)
        part["faces"].extend([
            (base + 0, base + 2, base + 3, base + 1),
            (base + 0, base + 1, base + 5, base + 4),
            (base + 2, base + 4, base + 5, base + 3),
            (base + 0, base + 4, base + 2),
            (base + 1, base + 3, base + 5),
        ])

    def add_cylinder(self, x, y, z, radius, height, key="trim", segments=12, top_radius=None):
        top_radius = radius if top_radius is None else top_radius
        part = self._part(key)
        base = len(part["verts"])
        for ring, ring_radius, height_offset in ((0, radius, -height / 2), (1, top_radius, height / 2)):
            for i in range(segments):
                angle = i * math.tau / segments
                p = runtime_point(x + math.cos(angle) * ring_radius, y + height_offset, z + math.sin(angle) * ring_radius)
                part["verts"].append(tuple(p))
        part["verts"].append(tuple(runtime_point(x, y - height / 2, z)))
        part["verts"].append(tuple(runtime_point(x, y + height / 2, z)))
        bottom_center = base + segments * 2
        top_center = bottom_center + 1
        for i in range(segments):
            nxt = (i + 1) % segments
            part["faces"].append((base + i, base + nxt, base + segments + nxt, base + segments + i))
            part["faces"].append((bottom_center, base + nxt, base + i))
            part["faces"].append((top_center, base + segments + i, base + segments + nxt))

    def add_beam(self, start_runtime, end_runtime, width, depth, key="trim"):
        start = runtime_point(*start_runtime)
        end = runtime_point(*end_runtime)
        forward = end - start
        if forward.length < 1e-5:
            return
        forward.normalize()
        reference = Vector((0, 0, 1)) if abs(forward.z) < 0.96 else Vector((1, 0, 0))
        right = forward.cross(reference).normalized()
        up = right.cross(forward).normalized()
        part = self._part(key)
        base = len(part["verts"])
        for point in (start, end):
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                part["verts"].append(tuple(point + right * width * sx + up * depth * sy))
        part["faces"].extend([
            (base + 0, base + 1, base + 5, base + 4),
            (base + 1, base + 2, base + 6, base + 5),
            (base + 2, base + 3, base + 7, base + 6),
            (base + 3, base + 0, base + 4, base + 7),
            (base + 0, base + 3, base + 2, base + 1),
            (base + 4, base + 5, base + 6, base + 7),
        ])

    def add_sloped_panel(self, corners_runtime, thickness, key="glass"):
        """Add a thin closed quadrilateral panel with vertical thickness.

        `corners_runtime` must walk the upper surface perimeter. Duplicating
        that perimeter downward avoids the arbitrary cross-section basis of a
        generic beam and guarantees rectangular end faces for pitched glass.
        """
        if len(corners_runtime) != 4:
            raise ValueError("sloped panel requires exactly four corners")
        if thickness <= 0:
            raise ValueError("sloped panel thickness must be positive")
        corners_runtime = list(corners_runtime)
        edge_a = (
            corners_runtime[1][0] - corners_runtime[0][0],
            corners_runtime[1][1] - corners_runtime[0][1],
            corners_runtime[1][2] - corners_runtime[0][2],
        )
        edge_b = (
            corners_runtime[2][0] - corners_runtime[0][0],
            corners_runtime[2][1] - corners_runtime[0][1],
            corners_runtime[2][2] - corners_runtime[0][2],
        )
        normal_y = edge_a[2] * edge_b[0] - edge_a[0] * edge_b[2]
        if abs(normal_y) < 1e-8:
            raise ValueError("sloped panel upper surface is degenerate")
        if normal_y < 0:
            # Call sites may traverse mirrored roof slopes in opposite order.
            # Normalize the upper surface to an upward runtime-Y winding so
            # both panes survive back-face culling in Blender and WebGL.
            corners_runtime.reverse()
        key = self._sanitize_facade_key(1.0, thickness, 1.0, key)
        part = self._part(key)
        base = len(part["verts"])
        lower = [(x, y - thickness, z) for x, y, z in corners_runtime]
        part["verts"].extend(tuple(runtime_point(*vertex)) for vertex in lower)
        part["verts"].extend(tuple(runtime_point(*vertex)) for vertex in corners_runtime)
        part["faces"].extend([
            (base + 0, base + 3, base + 2, base + 1),
            (base + 4, base + 5, base + 6, base + 7),
            (base + 0, base + 1, base + 5, base + 4),
            (base + 1, base + 2, base + 6, base + 5),
            (base + 2, base + 3, base + 7, base + 6),
            (base + 3, base + 0, base + 4, base + 7),
        ])

    def add_surface_panel(self, corners_runtime, thickness, key="glass"):
        """Extrude any reviewed quadrilateral along its true surface normal."""
        if len(corners_runtime) != 4:
            raise ValueError("surface panel requires exactly four corners")
        if thickness <= 0:
            raise ValueError("surface panel thickness must be positive")
        points = [Vector(tuple(float(value) for value in point)) for point in corners_runtime]
        normal = (points[1] - points[0]).cross(points[2] - points[0])
        if normal.length < 1e-8:
            raise ValueError("surface panel is degenerate")
        normal.normalize()
        offset = normal * (thickness / 2)
        key = self._sanitize_facade_key(1.0, thickness, 1.0, key)
        part = self._part(key)
        base = len(part["verts"])
        lower = [point - offset for point in points]
        upper = [point + offset for point in points]
        part["verts"].extend(tuple(runtime_point(*point)) for point in lower)
        part["verts"].extend(tuple(runtime_point(*point)) for point in upper)
        part["faces"].extend([
            (base + 0, base + 3, base + 2, base + 1),
            (base + 4, base + 5, base + 6, base + 7),
            (base + 0, base + 1, base + 5, base + 4),
            (base + 1, base + 2, base + 6, base + 5),
            (base + 2, base + 3, base + 7, base + 6),
            (base + 3, base + 0, base + 4, base + 7),
        ])

    def add_ngon_panel(self, corners_runtime, thickness, key="glass"):
        """Extrude an arbitrary (>=3-corner) polygon along its Newell's-
        method surface normal -- the general form of add_surface_panel
        (whose own single-cross-product normal is this method's planar,
        exactly-4-corner special case; both cost the same 4*n-4 triangles
        for n=4). Newell's method sums a contribution from every edge, so
        it stays correct even when a few consecutive corners are collinear
        or nearly coincident -- nakaniwa's own reference kit deliberately
        builds several conservatory rib/vault cross-sections that way (see
        tools/blender/stage_kits/nakaniwa_a23_reconciliation.py's
        emit_specs_to_mesh_builder, this method's only current caller,
        which uses it for every panel regardless of corner count rather
        than fan-triangulating >4-corner panels into separate quads --
        that would cost (n-2)*12 triangles instead of this method's n*4-4,
        multiple times more for n>4).
        """
        if len(corners_runtime) < 3:
            raise ValueError("ngon panel requires at least three corners")
        if thickness <= 0:
            raise ValueError("ngon panel thickness must be positive")
        corners = [tuple(float(value) for value in point) for point in corners_runtime]
        count = len(corners)
        normal = [0.0, 0.0, 0.0]
        for index, point in enumerate(corners):
            nxt = corners[(index + 1) % count]
            normal[0] += (point[1] - nxt[1]) * (point[2] + nxt[2])
            normal[1] += (point[2] - nxt[2]) * (point[0] + nxt[0])
            normal[2] += (point[0] - nxt[0]) * (point[1] + nxt[1])
        length = math.sqrt(sum(value * value for value in normal))
        if length < 1e-9:
            raise ValueError("ngon panel corners must span a non-zero plane")
        normal = tuple(value / length for value in normal)
        half = thickness / 2.0
        key = self._sanitize_facade_key(1.0, thickness, 1.0, key)
        part = self._part(key)
        base = len(part["verts"])
        front = [tuple(point[axis] + normal[axis] * half for axis in range(3)) for point in corners]
        back = [tuple(point[axis] - normal[axis] * half for axis in range(3)) for point in corners]
        part["verts"].extend(tuple(runtime_point(*point)) for point in front)
        part["verts"].extend(tuple(runtime_point(*point)) for point in back)
        part["faces"].append(tuple(base + index for index in range(count)))
        part["faces"].append(tuple(base + count + index for index in reversed(range(count))))
        for index in range(count):
            nxt = (index + 1) % count
            part["faces"].append((base + index, base + nxt, base + count + nxt, base + count + index))

    def add_sagged_awning(
        self,
        x,
        y,
        z,
        width,
        projection,
        sag,
        tangent_axis="x",
        outward=1,
        key="accent",
        width_segments=6,
        depth_segments=4,
    ):
        """Add a lightweight, genuinely curved cloth canopy.

        The back edge is the wall fastener line and the front edge projects
        into the public realm above head height.  Subdivision occurs in both
        directions, so the result has a changing normal and silhouette rather
        than the rejected flat cyan card/box shortcut.
        """
        part = self._part(key)
        base = len(part["verts"])
        for depth_index in range(depth_segments + 1):
            depth_t = depth_index / depth_segments
            outward_distance = projection * depth_t * outward
            drop = depth_t * 0.20 + math.sin(depth_t * math.pi) * sag
            for width_index in range(width_segments + 1):
                width_t = width_index / width_segments
                tangent = (width_t - 0.5) * width
                edge_sag = math.sin(width_t * math.pi) * sag * 0.16
                if tangent_axis == "x":
                    runtime = (x + tangent, y - drop - edge_sag, z + outward_distance)
                else:
                    runtime = (x + outward_distance, y - drop - edge_sag, z + tangent)
                part["verts"].append(tuple(runtime_point(*runtime)))
        row = width_segments + 1
        for depth_index in range(depth_segments):
            for width_index in range(width_segments):
                a = base + depth_index * row + width_index
                b = a + 1
                c = a + row + 1
                d = a + row
                part["faces"].append((a, d, c, b))

    def add_gable_roof(self, x, base_y, z, width, roof_height, depth, key="accent", ridge_axis="x"):
        """Add a watertight six-vertex gabled roof prism."""
        half_w = width / 2
        half_d = depth / 2
        if ridge_axis == "x":
            runtime_vertices = [
                (x - half_w, base_y, z - half_d),
                (x + half_w, base_y, z - half_d),
                (x - half_w, base_y, z + half_d),
                (x + half_w, base_y, z + half_d),
                (x - half_w, base_y + roof_height, z),
                (x + half_w, base_y + roof_height, z),
            ]
        else:
            runtime_vertices = [
                (x - half_w, base_y, z - half_d),
                (x - half_w, base_y, z + half_d),
                (x + half_w, base_y, z - half_d),
                (x + half_w, base_y, z + half_d),
                (x, base_y + roof_height, z - half_d),
                (x, base_y + roof_height, z + half_d),
            ]
        part = self._part(key)
        base = len(part["verts"])
        part["verts"].extend(tuple(runtime_point(*vertex)) for vertex in runtime_vertices)
        part["faces"].extend([
            (base + 0, base + 2, base + 3, base + 1),
            (base + 0, base + 1, base + 5, base + 4),
            (base + 2, base + 4, base + 5, base + 3),
            (base + 0, base + 4, base + 2),
            (base + 1, base + 3, base + 5),
        ])

    def add_rock(self, x, y, z, radius, height, key="natural", segments=7, seed=1):
        part = self._part(key)
        base = len(part["verts"])
        rings = []
        # A four-ring tapered profile reads as an eroded rock or mountain.  The
        # old three-ring profile had a wide flat cap and looked like a pillar.
        for ring_index, (ring_y, ring_scale) in enumerate((
            (0.0, 0.94),
            (height * 0.30, 1.0),
            (height * 0.70, 0.66),
            (height, 0.14),
        )):
            ring = []
            for i in range(segments):
                jitter = 0.78 + stable_unit(seed, i + ring_index * segments, 0x45D9F3B) * 0.38
                angle = i * math.tau / segments + stable_unit(seed, i, 0xA1B2) * 0.12
                p = runtime_point(x + math.cos(angle) * radius * ring_scale * jitter, y + ring_y, z + math.sin(angle) * radius * ring_scale * jitter)
                ring.append(len(part["verts"]))
                part["verts"].append(tuple(p))
            rings.append(ring)
        for lower, upper in zip(rings, rings[1:]):
            for i in range(segments):
                nxt = (i + 1) % segments
                part["faces"].append((lower[i], lower[nxt], upper[nxt], upper[i]))
        part["faces"].append(tuple(reversed(rings[0])))
        part["faces"].append(tuple(rings[-1]))

    def flush(self):
        # Construction rule for the catalogue-wide orphan-emissive defect
        # (measurementDefect3 -- see docs/A23_TOOLCHAIN.md and
        # tools/blender/a23/orphan.py): every emissive primitive added by any
        # of this file's ~40 add_* authoring functions is seated flush
        # against its nearest real neighbour when the gap is small enough to
        # be a placement bug, or braced with new vertical support pylons
        # (never deleted or moved -- some emissive primitives reaching this
        # point are add_layout_shell's direct render of a TypeScript-
        # authored collision box, and deleting or translating that mesh
        # would desync the visual GLB from the still-active collision) when
        # nothing plausible is nearby. This is the mesh-front-end sibling of
        # _sanitize_facade_key's dark-card construction rule above -- it
        # changes what actually gets exported, not a downstream patch.
        # assert_no_orphan_emissive is then a self-consistency trap: it
        # should never fire given the remediation just ran, so if it does,
        # the remediation itself has a bug and the build must stop rather
        # than silently ship a floating card.
        self.parts, self.orphan_remediation = a23_orphan.remediate_parts(self.parts)
        a23_orphan.assert_no_orphan_emissive(self.parts, context=self.prefix)
        objects = []
        for key, data in self.parts.items():
            if not data["verts"]:
                continue
            mesh = bpy.data.meshes.new(self.prefix + "_" + key + "_MESH")
            mesh.from_pydata(data["verts"], [], data["faces"])
            mesh.validate(verbose=False)
            mesh.update(calc_edges=True)
            uv_layer = mesh.uv_layers.new(name="UVMap")
            uv_scale = float(self.materials[key].get("hibanaUvScale", 0.12))
            for polygon in mesh.polygons:
                normal = polygon.normal
                axis = max(range(3), key=lambda component: abs(normal[component]))
                for loop_index in polygon.loop_indices:
                    coordinate = mesh.vertices[mesh.loops[loop_index].vertex_index].co
                    if axis == 0:
                        u, v = coordinate.y, coordinate.z
                    elif axis == 1:
                        u, v = coordinate.x, coordinate.z
                    else:
                        u, v = coordinate.x, coordinate.y
                    uv_layer.data[loop_index].uv = (u * uv_scale, v * uv_scale)
            if key in {"natural", "terrain"}:
                for polygon in mesh.polygons:
                    polygon.use_smooth = True
            obj = bpy.data.objects.new(self.prefix + "_" + key, mesh)
            self.collection.objects.link(obj)
            obj.data.materials.append(self.materials[key])
            obj["hibanaMaterial"] = key
            obj["hibanaExport"] = True
            # Keep physical chamfers on the architecture masses where they
            # affect the silhouette. Natural/terrain meshes are already smooth
            # and narrow trim is read through its baked normal map; beveling
            # those merged batches more than doubles GLB vertices with no
            # first-person benefit.
            if self.bevel > 0 and key in {
                "wall", "wall_alt", "wall_warm", "wall_cool", "wall_weathered",
            }:
                modifier = obj.modifiers.new("HB_micro_chamfer", "BEVEL")
                modifier.width = self.bevel
                modifier.segments = 1
                modifier.limit_method = "ANGLE"
            objects.append(obj)
        if objects:
            # Store the metrics once per independent builder, avoiding the
            # multiplication that would occur if every material batch repeated
            # the same count. They survive GLB export as auditable extras.
            pane_count = len(self.facade_glass_metrics)
            repeated_sizes = {}
            for width, height, _, _ in self.facade_glass_metrics:
                key = f"{width:.3f}x{height:.3f}"
                repeated_sizes[key] = repeated_sizes.get(key, 0) + 1
            metric_owner = next(
                (obj for obj in objects if obj.get("hibanaMaterial") == "glass"),
                objects[0],
            )
            # Independent post-export QA consumes this explicit schema rather
            # than trusting the generator implementation.  Keep the version
            # on every builder's single metric-owner node so merged GLBs still
            # prove which distance/count contract produced their metadata.
            metric_owner["hibanaFacadeAuditVersion"] = "black-window-v1"
            metric_owner["hibanaFacadeGlassPaneCount"] = pane_count
            metric_owner["hibanaFacadeGlassMaxEqualSizeRepeat"] = max(repeated_sizes.values(), default=0)
            metric_owner["hibanaFacadeGlassMinWallClearanceM"] = min(
                (item[2] for item in self.facade_glass_metrics),
                default=1.0,
            )
            metric_owner["hibanaFacadeGlassMaxWallClearanceM"] = max(
                (item[2] for item in self.facade_glass_metrics),
                default=0.0,
            )
            metric_owner["hibanaFacadeGlassMinFrameRecessM"] = min(
                (item[3] for item in self.facade_glass_metrics),
                default=1.0,
            )
            metric_owner["hibanaFacadeGlassNearCoplanarCount"] = sum(
                1 for _, _, wall_clearance, frame_recess in self.facade_glass_metrics
                if wall_clearance < 0.008 or frame_recess < 0.080
            )
            metric_owner["hibanaFacadeGlassFloatingCount"] = sum(
                1 for _, _, wall_clearance, _ in self.facade_glass_metrics
                if wall_clearance > 0.060
            )
            metric_owner["hibanaFacadeGlassEmbeddedCount"] = sum(
                1 for _, _, wall_clearance, _ in self.facade_glass_metrics
                if wall_clearance < 0.0
            )
            metric_owner["hibanaFacadeDarkCardCount"] = self.facade_dark_card_count
            # Diagnostic only: the independent release gate continues to use
            # geometry and the scalar count above.  This compact breakdown
            # makes a rejected material family actionable without weakening
            # any threshold or semantic exception.
            metric_owner["hibanaFacadeDarkCardBreakdown"] = json.dumps(
                self.facade_dark_card_breakdown,
                sort_keys=True,
                separators=(",", ":"),
            )
            # Orphan-emissive construction-rule provenance (measurementDefect3;
            # see the remediate_parts()/assert_no_orphan_emissive() call above
            # this loop). Independent post-export QA can re-derive the
            # geometric truth directly from the GLB; these counts are the
            # generator's own account of what it changed, kept on the same
            # metric-owner node as the sibling black-window metadata.
            metric_owner["hibanaOrphanEmissiveAuditVersion"] = "orphan-emissive-v1"
            metric_owner["hibanaOrphanEmissiveSeatedCount"] = self.orphan_remediation["seatedCount"]
            metric_owner["hibanaOrphanEmissiveBracedCount"] = self.orphan_remediation["bracedCount"]
            metric_owner["hibanaOrphanEmissiveBracePylonCount"] = self.orphan_remediation["bracePylonCount"]
        return objects


def choose_box_material(box, stage, index):
    palette = stage["palette"]
    if box.get("urbanVolume"):
        # Kairou's second collision-backed storeys must read as sun-warmed
        # masonry.  The generic facade family occasionally selected wall_alt,
        # which made these large new volumes look like blue/black inserts.
        return "wall_warm"
    if box.get("glazing"):
        return "glass"
    if box.get("emissive"):
        return "emissive"
    if box.get("district"):
        return facade_material_key(stage, index, 0x81)
    color = box.get("color", palette["obstacle"]).lower()
    if color == palette["accent"].lower():
        volume = box["w"] * box["h"] * box["d"]
        return "accent" if box.get("district") or volume >= 24 else "obstacle"
    if color == palette["wall"].lower():
        return "wall"
    return "obstacle"


def add_cover_skin(builder, box, stage, index, lod):
    """Turn an authoritative random cover box into a readable real-world prop.

    The collider-sized core is emitted by add_layout_shell before this call.
    Every piece here is a flush panel, cap, inset or roof seated on that core;
    no new route obstruction or walk-through house is introduced.  This lets
    the 80-150 ordinary cover blocks in every map carry most of the first-
    person density instead of concentrating all detail in a distant landmark.
    """
    if lod != 0:
        return
    family = IDENTITIES[stage["id"]][0]
    seed = stage["seed"]
    x, y, z = box["x"], box["y"], box["z"]
    width, height, depth = box["w"], box["h"], box["d"]
    base_y = y - height / 2
    top = y + height / 2
    long_x = width >= depth
    span = width if long_x else depth
    thickness = depth if long_x else width
    variation = int(stable_unit(seed, index, 0xC05E) * 4)

    def face_panel(offset, panel_y, panel_w, panel_h, key="trim"):
        if long_x:
            builder.add_box(x + offset, panel_y, z - depth / 2 - 0.044, panel_w, panel_h, 0.088, key)
        else:
            builder.add_box(x + width / 2 + 0.044, panel_y, z + offset, 0.088, panel_h, panel_w, key)

    # Waist-high cover receives construction logic instead of remaining a
    # scaled cube: concrete shoulders, stone coping, cargo straps or snow cap.
    if height <= 1.65:
        if family in {"wilderness", "geothermal"}:
            # Continuous plinth already represents collision. Overlapping
            # stones break the silhouette while never implying passable gaps.
            stones = max(2, min(6, int(span // 1.55)))
            for stone in range(stones):
                along = (stone - (stones - 1) / 2) * span * 0.82 / max(1, stones - 1)
                radius = min(0.82, span / stones * 0.56)
                sx, sz = (x + along, z) if long_x else (x, z + along)
                builder.add_rock(
                    sx,
                    top - height * 0.22,
                    sz,
                    radius,
                    height * (0.44 + stable_unit(seed, index * 7 + stone, 0x771) * 0.24),
                    "natural" if family == "wilderness" else "wall_alt",
                    7,
                    seed + index * 31 + stone,
                )
        elif family == "heritage":
            builder.add_box(x, top + 0.09, z, width + 0.24, 0.18, depth + 0.28, "accent")
            bays = max(2, min(6, int(span // 1.8)))
            for bay in range(bays):
                along = (bay - (bays - 1) / 2) * span * 0.82 / max(1, bays - 1)
                face_panel(along, base_y + height * 0.52, min(0.72, span / bays * 0.54), height * 0.48, "wall_alt")
        else:
            # Jersey/cargo cover: narrower shoulder, reflector plates and
            # seated end posts make the footprint legible at sprint speed.
            cap_w = width * (0.82 if long_x else 0.92)
            cap_d = depth * (0.92 if long_x else 0.82)
            builder.add_box(x, top + 0.08, z, cap_w, 0.16, cap_d, "trim")
            bays = max(2, min(5, int(span // 2.1)))
            for bay in range(bays):
                along = (bay - (bays - 1) / 2) * span * 0.78 / max(1, bays - 1)
                face_panel(along, base_y + height * 0.58, min(0.76, span / bays * 0.58), 0.20, "accent" if bay % 2 == variation % 2 else "trim")
        return

    # Human-height boxes become equipment cabinets, market kiosks or stacked
    # field stores. Door seams and service vents sit directly on the collider.
    if height <= 3.45 or min(width, depth) < 3.6:
        bays = max(1, min(5, int(span // 2.15)))
        for bay in range(bays):
            along = (bay - (bays - 1) / 2) * span * 0.76 / max(1, bays - 1)
            panel_key = "accent" if family == "heritage" and bay % 3 == 0 else "glass" if family in {"urban", "airport"} and bay == variation % bays else "trim"
            face_panel(along, base_y + height * 0.54, min(1.18, span / (bays + 0.4) * 0.62), min(1.62, height * 0.56), panel_key)
        builder.add_box(x, top + 0.10, z, width + 0.20, 0.20, depth + 0.20, "wall_alt")
        if family in {"industrial", "military", "airport", "undead", "geothermal"}:
            # Flush corner guards and a roof vent sell a manufactured shell.
            for sx in (-1, 1):
                for sz in (-1, 1):
                    builder.add_box(x + sx * width / 2, y, z + sz * depth / 2, 0.12, height * 0.88, 0.12, "trim")
            if top > 2.4 and min(width, depth) >= 2.1:
                builder.add_cylinder(x, top + 0.36, z, min(0.32, thickness * 0.11), 0.52, "trim", 8, min(0.22, thickness * 0.08))
        return

    # Larger random covers are promoted to fully collidable outbuildings.
    # The rectangular collider remains the wall mass; roof, windows, canopy,
    # gutters and door are facade-only, so this is not a hollow visual shell.
    roof_h = max(0.72, min(1.75, min(width, depth) * 0.24))
    if family in {"heritage", "wilderness"}:
        builder.add_gable_roof(x, top - 0.04, z, width + 0.54, roof_h, depth + 0.64, "accent", "x" if long_x else "z")
    else:
        builder.add_box(x, top + 0.18, z, width + 0.22, 0.36, depth + 0.22, "wall_alt")
        builder.add_box(x, top + 0.54, z, min(2.8, width * 0.34), 0.72, min(2.2, depth * 0.34), "trim")
    bays = max(2, min(5, int(span // 2.4)))
    for bay in range(bays):
        along = (bay - (bays - 1) / 2) * span * 0.74 / max(1, bays - 1)
        key = "emissive" if stage["palette"].get("mood") == "night" and (bay + index) % 5 == 0 else "glass"
        face_panel(along, base_y + min(2.25, height * 0.56), min(1.22, span / bays * 0.58), min(1.20, height * 0.28), key)
    door_offset = -span * 0.28 if variation & 1 else span * 0.28
    face_panel(door_offset, base_y + 1.22, min(1.16, span * 0.18), 2.18, "trim")
    if long_x:
        builder.add_box(x + door_offset, base_y + 2.48, z - depth / 2 - 0.46, min(2.2, span * 0.28), 0.16, 0.92, "accent")
    else:
        builder.add_box(x + width / 2 + 0.46, base_y + 2.48, z + door_offset, 0.92, 0.16, min(2.2, span * 0.28), "accent")


def add_layout_shell(builder, stage, lod):
    seed = stage["seed"]
    for index, box in enumerate(stage["boxes"]):
        if (
            box.get("ghost")
            or box.get("decor")
            or box.get("legacyHorizon")
            or box.get("prop")
            or box.get("breakable")
            or box.get("visualReplacement") == "souko-roof-monitor-v1"
        ):
            continue
        if box.get("landmarkId"):
            # Landmark batches own their complete collision-authoritative shell
            # so identity metadata, bounds and LOD QA remain independently auditable.
            continue
        district = box.get("district")
        volume = box["w"] * box["h"] * box["d"]
        if lod == 1 and not district and volume < 22:
            continue
        if lod == 2 and (not district or box["h"] < 4 or volume < 90):
            continue
        expansion = 0.06 if lod == 0 else 0.03
        key = choose_box_material(box, stage, index)
        builder.add_box(box["x"], box["y"], box["z"], box["w"] + expansion, box["h"] + expansion, box["d"] + expansion, key)

        if not district:
            add_cover_skin(builder, box, stage, index, lod)


def add_architectural_skin(builder, stage, lod):
    """Seat detail directly onto authoritative collision shells.

    These panels do not create walk-through props in lanes: facade pieces sit
    3-5 cm outside existing walls, while roof equipment is limited to high,
    inaccessible district masses.  Everything is merged by material.
    """
    if lod == 2 or stage["id"] == "kairou":
        return
    family = IDENTITIES[stage["id"]][0]
    mood = stage["palette"].get("mood")
    candidates = [
        box for box in stage["boxes"]
        if box.get("district")
        and not box.get("landmarkId")
        and not box.get("ghost")
        and not box.get("legacyHorizon")
        and not box.get("decor")
        and box["h"] >= 4.0
        and box["w"] * box["d"] >= 24
    ]
    limit = 34 if lod == 0 else 18
    candidates = sorted(candidates, key=lambda box: box["w"] * box["h"] * box["d"], reverse=True)[:limit]
    for index, box in enumerate(candidates):
        wide_x = box["w"] >= box["d"]
        span = box["w"] if wide_x else box["d"]
        bays = max(2, min(7 if lod == 0 else 4, int(span // 4.8)))
        levels = max(1, min(4 if lod == 0 else 2, int(box["h"] // 4.2)))
        facade_y0 = box["y"] - box["h"] / 2
        for level in range(levels):
            pane_y = facade_y0 + (level + 0.58) * box["h"] / levels
            pane_h = max(0.6, min(1.65, box["h"] / levels * 0.38))
            for bay in range(bays):
                offset = (bay - (bays - 1) / 2) * span / bays
                pane_w = max(0.7, span / bays * 0.58)
                if family in {"urban", "undead"} and mood == "night" and (bay + level + index) % 5 == 0:
                    key = "emissive"
                elif family in {"heritage", "wilderness"}:
                    key = "wall_alt" if (bay + level) % 3 else "accent"
                else:
                    key = "glass" if (bay + level + index) % 3 else "trim"
                if wide_x:
                    builder.add_box(box["x"] + offset, pane_y, box["z"] - box["d"] / 2 - 0.045, pane_w, pane_h, 0.09, key)
                else:
                    builder.add_box(box["x"] + box["w"] / 2 + 0.045, pane_y, box["z"] + offset, 0.09, pane_h, pane_w, key)
        # Flush vertical service ribs break the toy-like unbounded rectangles.
        for rib in range(1, bays):
            offset = (rib - bays / 2) * span / bays
            if wide_x:
                builder.add_box(box["x"] + offset, box["y"], box["z"] - box["d"] / 2 - 0.052, 0.12, box["h"] * 0.84, 0.10, "trim")
            else:
                builder.add_box(box["x"] + box["w"] / 2 + 0.052, box["y"], box["z"] + offset, 0.10, box["h"] * 0.84, 0.12, "trim")
        top = box["y"] + box["h"] / 2
        if lod == 0 and top > 7.5 and index % 2 == 0:
            # Roof equipment is kept low and only placed on tall district
            # masses, so players never encounter collider-free cover.
            unit_w = min(4.5, box["w"] * 0.28)
            unit_d = min(3.5, box["d"] * 0.28)
            builder.add_box(box["x"], top + 0.48, box["z"], unit_w, 0.96, unit_d, "wall_alt")
            if family in {"industrial", "airport", "undead"}:
                builder.add_cylinder(box["x"] + unit_w * 0.22, top + 1.65, box["z"], 0.32, 2.35, "trim", 8, 0.22)
            elif family == "urban":
                builder.add_box(box["x"], top + 1.12, box["z"] - unit_d * 0.52, unit_w * 0.82, 0.26, 0.08, "emissive" if mood == "night" else "accent")


def add_routes(builder, stage, lod):
    size = stage["size"]
    family = IDENTITIES[stage["id"]][0]
    road_width = 12 if family == "airport" else 8 if family in {"industrial", "urban", "undead"} else 6.5
    landmarks = stage.get("landmarkPlacements", [])
    if len(landmarks) == 2 and landmarks[0].get("collisionTemplate") != "abbey":
        primary, alley = landmarks
        builder.add_box(primary["cx"], 0.012, 0, 16.0, 0.024, size * 0.91, "road")
        builder.add_box(0, 0.014, primary["cz"], size * 0.91, 0.024, 16.0, "road")
        builder.add_box(alley["cx"], 0.016, 0, 7.0, 0.022, size * 0.91, "road")
        builder.add_box(0, 0.018, alley["cz"], size * 0.91, 0.020, 7.0, "road")
        for landmark in landmarks:
            start = landmark["approach"]["start"]
            end = landmark["approach"]["end"]
            dx, dz = end[0] - start[0], end[1] - start[1]
            length = math.hypot(dx, dz)
            if length > 0.01:
                builder.add_oriented_box(
                    (start[0] + end[0]) / 2,
                    0.020,
                    (start[1] + end[1]) / 2,
                    length,
                    0.022,
                    landmark["approach"]["width"],
                    math.atan2(dz, dx),
                    "road",
                )
    else:
        builder.add_box(0, 0.012, 0, road_width, 0.024, size * 0.91, "road")
        builder.add_box(0, 0.014, 0, size * 0.91, 0.024, road_width, "road")
    if lod == 0:
        if not landmarks:
            offset = size * 0.21
            builder.add_box(offset, 0.016, -offset * 0.55, road_width * 0.7, 0.022, size * 0.44, "road")
        marking_x = landmarks[0]["cx"] if len(landmarks) == 2 else 0
        marking_key = "wall_alt" if stage["id"] == "kairou" else "accent"
        for i in range(-8, 9):
            builder.add_box(marking_x, 0.03, i * size * 0.048, 0.12 if stage["id"] == "kairou" else 0.18, 0.014, size * 0.026, marking_key)


def add_route_set_dressing(builder, stage, lod):
    """Add low-profile infrastructure without creating fake cover."""
    if lod == 2:
        return
    size = stage["size"]
    family = IDENTITIES[stage["id"]][0]
    road_width = 12 if family == "airport" else 8 if family in {"industrial", "urban", "undead"} else 6.5
    interval = 14 if lod == 0 else 28
    count = max(5, int(size * 0.76 // interval))
    start = -(count - 1) * interval / 2
    landmarks = stage.get("landmarkPlacements", [])
    if len(landmarks) == 2 and landmarks[0].get("collisionTemplate") != "abbey":
        route_specs = [
            (0, landmarks[0]["cx"], 16.0),
            (1, landmarks[0]["cz"], 16.0),
            (0, landmarks[1]["cx"], 7.0),
            (1, landmarks[1]["cz"], 7.0),
        ]
    else:
        route_specs = [(0, 0.0, road_width), (1, 0.0, road_width)]
    # Curbs and storm drains are only 8-14cm tall: they enrich the near field
    # but cannot be mistaken for collision-bearing cover.
    for axis, center, active_width in route_specs:
        for side in (-1, 1):
            offset = center + side * (active_width / 2 + 0.72)
            if axis == 0:
                builder.add_box(offset, 0.07, 0, 0.26, 0.14, size * 0.76, "wall_alt")
            else:
                builder.add_box(0, 0.075, offset, size * 0.76, 0.15, 0.26, "wall_alt")
        for index in range(count):
            along = start + index * interval
            if axis == 0:
                builder.add_box(center + active_width / 2 + 0.48, 0.026, along, 0.46, 0.052, 1.08, "trim")
                builder.add_box(center - active_width / 2 - 0.48, 0.026, along + interval * 0.45, 0.46, 0.052, 1.08, "trim")
            else:
                builder.add_box(along, 0.026, center + active_width / 2 + 0.48, 1.08, 0.052, 0.46, "trim")
                builder.add_box(along + interval * 0.45, 0.026, center - active_width / 2 - 0.48, 1.08, 0.052, 0.46, "trim")
    if lod == 0:
        # Utility pads under authored props visually connect them to the site.
        for index, placement in enumerate(blender_prop_placements(stage)):
            if placement["kind"] in {"conifer", "broadleaf", "deadtree", "sakura", "bamboo", "rock", "rubble"}:
                continue
            radius = 1.05 + (index % 3) * 0.28
            builder.add_oriented_box(
                placement["cx"], 0.018, placement["cz"],
                radius * 2.0, 0.036, radius * 1.55,
                placement["rotRad"], "road",
            )

    if stage["id"] == "souko" and len(landmarks) == 2:
        # Portal pipe/sign frames turn both canonical approaches into readable
        # bonded-logistics thresholds. The 24cm posts sit 1.4m outside each
        # approach width; all cross-pipes remain above 7.7m, so the authored
        # 12m lanes and complete first-person headroom stay untouched.
        for approach_index, landmark in enumerate(landmarks):
            start_x, start_z = (float(value) for value in landmark["approach"]["start"])
            end_x, end_z = (float(value) for value in landmark["approach"]["end"])
            delta_x, delta_z = end_x - start_x, end_z - start_z
            approach_length = max(0.001, math.hypot(delta_x, delta_z))
            forward_x, forward_z = delta_x / approach_length, delta_z / approach_length
            right_x, right_z = forward_z, -forward_x
            centre_x = start_x + delta_x * 0.54
            centre_z = start_z + delta_z * 0.54
            half_span = float(landmark["approach"]["width"]) / 2 + 1.4
            frame_top = 8.8 if lod == 0 else 8.2
            endpoints = []
            for side in (-1, 1):
                post_x = centre_x + right_x * half_span * side
                post_z = centre_z + right_z * half_span * side
                endpoints.append((post_x, post_z))
                builder.add_cylinder(
                    post_x,
                    frame_top / 2,
                    post_z,
                    0.12 if lod == 0 else 0.18,
                    frame_top,
                    "trim",
                    8 if lod == 0 else 6,
                    0.10,
                )
            for pipe_index in range(3 if lod == 0 else 2):
                pipe_y = frame_top - 0.25 - pipe_index * 0.52
                offset = (pipe_index - 1) * 0.26 if lod == 0 else (pipe_index - 0.5) * 0.26
                builder.add_beam(
                    (
                        endpoints[0][0] + forward_x * offset,
                        pipe_y,
                        endpoints[0][1] + forward_z * offset,
                    ),
                    (
                        endpoints[1][0] + forward_x * offset,
                        pipe_y,
                        endpoints[1][1] + forward_z * offset,
                    ),
                    0.13 if lod == 0 else 0.19,
                    0.11 if lod == 0 else 0.16,
                    "accent" if pipe_index == approach_index % 3 else "wall_cool",
                )
            if lod == 0:
                sign_x = centre_x - right_x * half_span * 0.44
                sign_z = centre_z - right_z * half_span * 0.44
                builder.add_oriented_box(
                    sign_x,
                    frame_top - 1.50,
                    sign_z,
                    3.1,
                    0.86,
                    0.16,
                    math.atan2(delta_z, delta_x),
                    "wall_warm" if approach_index == 0 else "wall_cool",
                )


def add_district_public_realm(builder, stage, lod):
    """Connect every playable district with roads, pavements and street life.

    DistrictPlacement is exported from the same StageLayout that owns physics,
    so aprons and entrances are never guessed from rendered pixels.  All added
    furniture is knee-height or thin-pole scenery placed outside the building
    footprint; it enriches first-person views without inventing fake cover.
    """
    if lod == 2:
        return
    placements = stage.get("districtPlacements", [])
    if not placements:
        return
    family = IDENTITIES[stage["id"]][0]
    mood = stage["palette"].get("mood")
    detailed = lod == 0
    for index, district in enumerate(placements):
        x, z = district["cx"], district["cz"]
        width, depth = district["width"], district["depth"]
        yaw = district["rot"] * math.pi / 2
        cosine, sine = math.cos(yaw), math.sin(yaw)

        def point(lx, lz):
            return x + lx * cosine - lz * sine, z + lx * sine + lz * cosine

        # A construction apron seats each building into the world.  The four
        # narrow pavement strips leave the gameplay floor visible in the yard.
        pavement = 1.55 if family in {"urban", "airport", "industrial", "military"} else 1.05
        builder.add_oriented_box(x, 0.026, z, width + pavement * 2.8, 0.052, depth + pavement * 2.8, yaw, "road")
        for lx, lz, w, d in (
            (0, -depth / 2 - pavement * 0.72, width + pavement * 2.0, pavement, ),
            (0, depth / 2 + pavement * 0.72, width + pavement * 2.0, pavement, ),
            (-width / 2 - pavement * 0.72, 0, pavement, depth + pavement * 2.0),
            (width / 2 + pavement * 0.72, 0, pavement, depth + pavement * 2.0),
        ):
            px, pz = point(lx, lz)
            builder.add_oriented_box(px, 0.075, pz, w, 0.15, d, yaw, "wall_alt")

        # Link the district apron to the central crossroads.  One merged road
        # material means ten districts still cost one draw call.
        if index > 0:
            road_end_x, road_end_z = point(0, -depth / 2 - pavement * 1.8)
            builder.add_beam((0, 0.035, 0), (road_end_x, 0.035, road_end_z), 3.2 if detailed else 2.6, 0.025, "road")

        if not detailed:
            continue
        front_z = -depth / 2 - pavement * 1.22
        # Thin lamps, entrance bollards, address sign and planted corners give
        # human scale. Their footprints are deliberately below cover size.
        for side in (-1, 1):
            lamp_x, lamp_z = point(side * min(width * 0.36, width / 2 - 1.1), front_z)
            builder.add_cylinder(lamp_x, 2.75, lamp_z, 0.075, 5.5, "trim", 8, 0.055)
            builder.add_box(lamp_x, 5.42, lamp_z, 0.48, 0.18, 0.48, "emissive" if mood == "night" else "accent")
            bollard_x, bollard_z = point(side * 1.45, -depth / 2 - pavement * 0.42)
            builder.add_cylinder(bollard_x, 0.42, bollard_z, 0.12, 0.84, "trim", 8, 0.095)
        sign_x, sign_z = point(-width / 2 - pavement * 0.34, front_z)
        builder.add_box(sign_x, 1.05, sign_z, 1.35, 1.48, 0.12, "accent")
        builder.add_box(sign_x, 0.30, sign_z, 0.16, 0.62, 0.16, "trim")
        for side in (-1, 1):
            planter_x, planter_z = point(side * (width / 2 + pavement * 0.42), depth / 2 + pavement * 0.34)
            builder.add_oriented_box(planter_x, 0.18, planter_z, 1.55, 0.36, 0.74, yaw, "wall_alt")
            # Compact multi-lobed shrub, 45cm high: decoration rather than
            # collisionless player-height cover.
            for lobe in (-0.42, 0, 0.42):
                shrub_x, shrub_z = point(side * (width / 2 + pavement * 0.42) + lobe, depth / 2 + pavement * 0.34)
                builder.add_rock(shrub_x, 0.28, shrub_z, 0.34, 0.48, "natural", 8, stage["seed"] + index * 41 + int((lobe + 1) * 10))


def add_port_horizon_terrain(builder, stage, lod, half):
    """Seat active and ruined harbors on real low-cost 3D shoreline geology.

    Connection map (runtime Y-up coordinates):

    - quay-lip bottom at Y=0.00 <-> quay-foundation top at Y=0.04;
      overlap/contact allowance: 0.04 m.
    - quay-foundation <-> water sheet spanning Y=-0.22..-0.10;
      overlap: 0.12 m, preventing a light-leaking shoreline gap.
    - breakwater arm landward end <-> quay-foundation outer face;
      overlap: at least 2.0 m in Z.
    - armor/mudrock clusters <-> foundation or arm side faces;
      centers are inset by at least 0.35 radius so no rocks float offshore.

    Every part remains outside the authoritative playable square.  These are
    visual terrain meshes only; TypeScript collision, routes and spawns remain
    unchanged.  Boxes are closed solids and rocks are capped radial meshes —
    never black cards, raster horizons or single-plane background stand-ins.
    """
    stage_id = stage["id"]
    if stage_id not in {"kouwan", "z03"}:
        return

    size = stage["size"]
    seed = stage["seed"]
    ruined = stage_id == "z03"

    # Continuous load-bearing shoreline directly below the already-authored
    # quay lip.  Its upper face intersects the water and lip, so the exported
    # silhouette has neither a razor edge nor a floating concrete strip.
    foundation_width = size * (0.79 if ruined else 0.86)
    builder.add_box(0, -0.78, -half - 2.25, foundation_width, 1.64, 4.9, "terrain")

    # Paired arms frame a navigable harbor mouth while staying beyond the
    # gameplay boundary.  A tiny deterministic yaw avoids a duplicated-box
    # read without increasing draw calls (all terrain merges into one batch).
    arm_length = 42.0 if ruined else 50.0
    arm_width = 6.8 if ruined else 8.4
    arm_center_z = -half - arm_length / 2 + 1.65
    arm_x = size * (0.31 if ruined else 0.34)
    arm_y = -0.41 if ruined else -0.31
    arm_height = 1.42 if ruined else 1.72
    for side in (-1, 1):
        yaw = math.radians(side * (5.5 if ruined else 3.0))
        builder.add_oriented_box(
            side * arm_x,
            arm_y,
            arm_center_z,
            arm_width,
            arm_height,
            arm_length,
            yaw,
            "terrain",
        )

    # Irregular contact geology distinguishes the working harbor from the
    # drowned one.  LOD2 keeps four broad capped masses; nearer LODs add only
    # enough samples to break the shore silhouette and hide box contacts.
    cluster_count = (14, 8, 4)[lod] if ruined else (10, 6, 4)[lod]
    segments = (9, 7, 6)[lod]
    for index in range(cluster_count):
        t = (index + 0.5) / cluster_count
        x = (t - 0.5) * foundation_width * 0.94
        x += (stable_unit(seed, index, 0x5031) - 0.5) * (5.2 if ruined else 3.4)
        z = -half - 1.7 - stable_unit(seed, index, 0x5032) * (5.8 if ruined else 3.1)
        radius = (2.3 if ruined else 1.9) + stable_unit(seed, index, 0x5033) * (2.8 if ruined else 2.0)
        height = (1.6 if ruined else 1.25) + stable_unit(seed, index, 0x5034) * (2.7 if ruined else 1.8)
        builder.add_rock(
            x,
            -0.92 if ruined else -0.70,
            z,
            radius,
            height,
            "terrain",
            segments,
            seed ^ (index * 0x45D9F3B),
        )

    if ruined:
        # Three tilted, partially submerged mudstone/concrete ledges describe
        # subsidence in z03.  They are closed volumes, not dark shoreline cards.
        ledge_count = (5, 3, 2)[lod]
        for index in range(ledge_count):
            side = -1 if index & 1 else 1
            x = side * (size * (0.12 + index * 0.043))
            z = -half - 8.5 - index * 5.2
            builder.add_oriented_box(
                x,
                -0.66 - index * 0.055,
                z,
                13.0 + index * 2.1,
                1.15 + index * 0.12,
                5.4 + index * 0.85,
                math.radians(side * (7.0 + index * 2.3)),
                "terrain",
            )


def add_souko_coastal_edge(builder, stage, lod, half):
    """Build Souko's real east quay, water and bonded-port silhouette.

    The canonical playable square ends at X=+168m.  Every new solid begins at
    or beyond that edge; the retaining wall/fence replaces the generic east
    warehouse boundary without consuming the east spawn at X=+156m.  The water
    is a closed 3D volume, never a raster matte or cylindrical picture wall.

    Connection map:
      quay foundation top Y=+0.05 <-> lip/apron bottom Y=-0.08: 0.13m overlap;
      water top Y=-0.10 <-> foundation side/bottom: >=1.10m overlap;
      crane feet bottom Y=-0.18 <-> quay/pier top Y=+0.02: 0.20m overlap;
      fence feet begin 0.18m inside the closed quay lip.
    """
    if stage["id"] != "souko":
        return

    size = float(stage["size"])
    detail = lod == 0
    medium = lod == 1

    # Reflective coastal depth to the right of the player frame.  A broad
    # closed box gives Eevee/WebGL a stable normal and visible horizon contact.
    water_width = 132.0 if lod <= 1 else 104.0
    builder.add_box(
        half + water_width / 2,
        -0.16,
        0,
        water_width,
        0.12,
        size * 1.22,
        "water",
    )

    quay_depth = size * 0.88
    builder.add_box(half + 2.15, -1.25, 0, 4.30, 2.60, quay_depth, "terrain")
    builder.add_box(half + 0.52, 0.24, 0, 1.36, 0.64, quay_depth * 0.98, "trim")
    builder.add_box(half + 7.10, -0.02, 0, 12.20, 0.12, quay_depth * 0.94, "road")

    # Retaining pilasters and a real safety fence make the water edge an
    # authored boundary.  LODs reduce count, not its continuous silhouette.
    pier_count = 18 if detail else 10 if medium else 6
    for index in range(pier_count):
        z = -quay_depth * 0.45 + index * quay_depth * 0.90 / max(1, pier_count - 1)
        builder.add_box(half + 0.30, -0.32, z, 1.18, 1.70, 3.2, "wall_weathered")
        if lod <= 1:
            builder.add_box(half + 0.54, 1.15, z, 0.22, 1.92, 0.22, "trim")
    if lod <= 1:
        for rail_y in (0.70, 1.42):
            builder.add_beam(
                (half + 0.54, rail_y, -quay_depth * 0.45),
                (half + 0.54, rail_y, quay_depth * 0.45),
                0.08 if detail else 0.12,
                0.08 if detail else 0.12,
                "accent" if rail_y > 1.0 else "trim",
            )

    # Bonded cargo remains outside gameplay but close enough to provide the
    # reference's foreground/midground scale ladder from east-facing views.
    cargo_clusters = 4 if detail else 2 if medium else 1
    cargo_z = (-118.0, -54.0, 54.0, 112.0)
    for index in range(cargo_clusters):
        add_container_stack(
            builder,
            half + 3.4 + (index % 2) * 1.2,
            cargo_z[index],
            2 if lod <= 1 else 1,
            3 if detail and index in {0, 2} else 2,
            4,
        )

    # Quayside gantry cranes use two portal frames across X, a travelling
    # bridge and a waterside boom.  Their four feet meet real apron/pier pads;
    # no leg terminates in open water or functions as a map-boundary shortcut.
    crane_zs = (-76.0, 66.0) if detail else (-8.0,)
    for crane_index, crane_z in enumerate(crane_zs):
        land_x = half + 6.0
        sea_x = half + 40.0
        frame_half_depth = 5.2
        crane_height = 31.0 if detail else 27.0 if medium else 23.0
        for foot_x in (land_x, sea_x):
            for depth_side in (-1, 1):
                foot_z = crane_z + depth_side * frame_half_depth
                if foot_x == sea_x:
                    builder.add_box(foot_x, -0.58, foot_z, 3.2, 1.20, 3.6, "terrain")
                builder.add_beam(
                    (foot_x, -0.18, foot_z),
                    (
                        foot_x + (1 if foot_x == land_x else -1) * 2.6,
                        crane_height,
                        crane_z + depth_side * frame_half_depth * 0.72,
                    ),
                    0.58 if detail else 0.72,
                    0.58 if detail else 0.72,
                    "wall_cool",
                )
        for depth_side in (-1, 1):
            bridge_z = crane_z + depth_side * frame_half_depth * 0.72
            builder.add_beam(
                (land_x + 2.4, crane_height, bridge_z),
                (sea_x - 2.4, crane_height, bridge_z),
                0.72 if detail else 0.90,
                0.62 if detail else 0.78,
                "accent" if depth_side < 0 else "trim",
            )
        builder.add_beam(
            ((land_x + sea_x) / 2, crane_height + 1.2, crane_z - frame_half_depth * 0.72),
            ((land_x + sea_x) / 2, crane_height + 1.2, crane_z + frame_half_depth * 0.72),
            0.62,
            0.54,
            "trim",
        )
        builder.add_beam(
            (sea_x - 2.0, crane_height + 0.35, crane_z),
            (half + 70.0, crane_height - 4.0, crane_z),
            0.48 if detail else 0.64,
            0.42 if detail else 0.56,
            "wall_cool",
        )
        builder.add_oriented_box(
            (land_x + sea_x) / 2 - 3.0,
            crane_height + 2.6,
            crane_z,
            8.4,
            4.2,
            5.2,
            0.0,
            "wall_warm" if crane_index == 0 else "wall_alt",
        )
        if detail:
            builder.add_cylinder(
                (land_x + sea_x) / 2 + 4.0,
                crane_height - 5.4,
                crane_z,
                0.10,
                10.8,
                "trim",
                6,
                0.06,
            )

    # One low vessel and a layered warehouse/tank line keep the visible water
    # from ending in empty sky.  All are genuine closed meshes beyond play.
    add_workboat(builder, half + 66.0, -30.0, 28.0 if detail else 21.0, lod, False)
    if lod <= 1:
        add_workboat(builder, half + 72.0, 91.0, 19.0 if detail else 15.0, lod, False)
        buoy_count = 5 if detail else 3
        for buoy_index in range(buoy_count):
            buoy_x = half + 57.0 + (buoy_index % 2) * 8.0
            buoy_z = -105.0 + buoy_index * 52.0
            builder.add_cylinder(
                buoy_x,
                0.05,
                buoy_z,
                0.42 if detail else 0.54,
                0.64,
                "accent" if buoy_index % 2 == 0 else "trim",
                10 if detail else 8,
                0.24,
            )
    horizon_count = 5 if detail else 3 if medium else 2
    for index in range(horizon_count):
        z = -132.0 + index * 264.0 / max(1, horizon_count - 1)
        x = half + 88.0 + (index % 2) * 12.0
        if index % 3 == 1:
            builder.add_cylinder(x, 8.0, z, 8.2, 16.0, "wall_weathered", 12 if detail else 8, 7.6)
            builder.add_cylinder(x, 16.3, z, 8.4, 0.6, "trim", 12 if detail else 8, 7.2)
        else:
            builder.add_box(x, 9.0, z, 28.0, 18.0, 16.0, "wall_alt")
            builder.add_gable_roof(x, 18.0, z, 29.0, 4.8, 17.0, "roof", "x")


def boundary_natural_sample_count(stage):
    """Return the LOD-independent perimeter lattice for natural terrain."""
    return BOUNDARY_CHIKURIN_SAMPLE_COUNT if stage["id"] == "chikurin" else BOUNDARY_SAMPLE_COUNT


def boundary_primary_specs(stage, lod, profile):
    """Describe the primary 360-degree boundary without touching Blender.

    Connection map (runtime Y-up coordinates):

    - natural sample ``i`` <-> sample ``i+1`` on the same side: nominal
      radius overlap; no positive tangent gap;
    - last sample on side ``n`` <-> first sample on side ``n+1``: corner
      overlap, except the authored water opening whose water sheet is the
      continuous physical boundary;
    - every primary solid stays outside the canonical spawn-clearance band;
      rock conservative inward reach is capped at seven metres.

    Returning specs makes the exact geometry inputs available to regression
    tests before a costly 31-stage Blender export.  Natural boundaries use the
    same center/radius/height at LOD0/1/2 and reduce only radial segments.
    """
    size = float(stage["size"])
    half = size / 2
    seed = int(stage["seed"])
    boundary = profile["boundary"]
    water_stage = boundary in {
        "harbor-seawall", "coastal-cliffs", "lake-shore", "flooded-port",
        "terraced-hills", "tidal-abbey-shore",
    }
    natural_boundary = boundary in {
        "range-earthworks", "hill-ramparts", "dune-ridges", "ice-ridge", "quarry-terraces",
        "bamboo-slopes", "terraced-hills", "coastal-cliffs", "canyon-cliffs", "lake-shore",
        "basalt-tunnels", "amusement-ruins", "crater-rim", "mountain-base", "tidal-abbey-shore",
    }
    arcade_boundary = boundary in {
        "palace-arcades", "temple-cliffs", "gothic-precinct", "underground-vaults", "mountain-town",
    }
    count = boundary_natural_sample_count(stage) if natural_boundary else (
        42 if lod == 0 else 24 if lod == 1 else 14
    )
    if not natural_boundary and stage["id"] == "chikurin":
        count = 34 if lod == 0 else 22 if lod == 1 else 14

    specs = []
    for side in range(4):
        for i in range(count):
            t = -half + (i + 0.5) * size / count
            jitter = stable_unit(seed, i + side * count, 0xBA11) - 0.5
            outward_offset = 2.2 + jitter * 4
            radius = None
            if natural_boundary:
                # Radius is derived from the approved LOD0 lattice, never from
                # a reduced LOD count.  Push only oversized rocks outward so
                # their conservative irregular envelope cannot consume the
                # spawn band while preserving at least seven metres of terrain
                # overlap across the authoritative square edge.
                radius = size / count * (0.92 + stable_unit(seed, i, side) * 0.72)
                outward_offset = max(
                    outward_offset,
                    radius * BOUNDARY_ROCK_MAX_RADIAL_STRETCH - BOUNDARY_MAX_INWARD_REACH_M,
                )
            if side == 0:
                x, z = t, -half - outward_offset
            elif side == 1:
                x, z = t, half + outward_offset
            elif side == 2:
                x, z = -half - outward_offset, t
            else:
                x, z = half + outward_offset, t
            if water_stage and side == 0 and count * 0.14 < i < count * 0.86:
                continue
            if natural_boundary:
                height_scale = 1.55 if boundary in {"canyon-cliffs", "quarry-terraces", "crater-rim"} else 1.0
                base_height = 3.0 if boundary in {"range-earthworks", "mountain-base"} else 4.5
                height_range = 7 if boundary in {"range-earthworks", "mountain-base"} else 12
                height = (base_height + stable_unit(seed, i, side + 91) * height_range) * height_scale
                specs.append({
                    "kind": "rock",
                    "side": side,
                    "index": i,
                    "x": x,
                    "y": -0.8,
                    "z": z,
                    "radius": radius,
                    "height": height,
                    "key": "terrain",
                    "segments": BOUNDARY_ROCK_SEGMENTS_BY_LOD[lod],
                    "seed": seed + i + side * 100,
                })
            elif arcade_boundary:
                width = size / count * 0.94
                height = 7 + stable_unit(seed, i, side + 71) * (6 if lod == 0 else 3)
                if i % 3:
                    w, d, key = (
                        (width, 3.2, "wall")
                        if side < 2
                        else (3.2, width, "wall")
                    )
                    specs.append({
                        "kind": "box", "side": side, "index": i,
                        "x": x, "y": height / 2, "z": z,
                        "w": w, "h": height, "d": d, "key": key,
                    })
                elif side < 2:
                    specs.append({
                        "kind": "arch", "side": side, "index": i,
                        "x": x, "y": 0.0, "z": z,
                        "width": width * 1.5, "height": height,
                        "depth": 2.8, "key": "wall_alt",
                    })
                else:
                    specs.append({
                        "kind": "box", "side": side, "index": i,
                        "x": x, "y": height / 2, "z": z,
                        "w": 3.2, "h": height, "d": width, "key": "wall_alt",
                    })
            else:
                width = size / count * 0.92
                depth = 4.5 + stable_unit(seed, i, side + 44) * 5
                height = 4 + stable_unit(seed, i, side + 71) * (10 if lod == 0 else 7)
                if i in {count // 3, count * 2 // 3}:
                    height *= 0.36
                specs.append({
                    "kind": "box", "side": side, "index": i,
                    "x": x, "y": height / 2 - 0.2, "z": z,
                    "w": width if side < 2 else depth,
                    "h": height,
                    "d": depth if side < 2 else width,
                    "key": "wall_alt" if i % 3 else "wall",
                })
    return specs


def add_boundary(builder, stage, lod):
    size = stage["size"]
    half = size / 2
    seed = stage["seed"]
    profile = PROFILES[stage["id"]]
    boundary = profile["boundary"]
    water_stage = boundary in {"harbor-seawall", "coastal-cliffs", "lake-shore", "flooded-port", "terraced-hills", "tidal-abbey-shore"}
    souko_coast = stage["id"] == "souko"

    # Continuous outer ground seats midground districts and the skyline.
    # Four overlapping strips avoid a giant central duplicate over the runtime
    # floor while removing the floating-building / diorama edge outside it.
    outer_depth = 210 if lod == 0 else 170 if lod == 1 else 130
    outer_span = size + outer_depth * 2
    if not water_stage:
        builder.add_box(0, -0.34, -half - outer_depth / 2, outer_span, 0.62, outer_depth, "terrain")
        builder.add_box(0, -0.34, half + outer_depth / 2, outer_span, 0.62, outer_depth, "terrain")
        builder.add_box(-half - outer_depth / 2, -0.34, 0, outer_depth, 0.62, size, "terrain")
        if not souko_coast:
            builder.add_box(half + outer_depth / 2, -0.34, 0, outer_depth, 0.62, size, "terrain")

    if water_stage:
        builder.add_box(0, -0.16, -half - 36, size * 1.35, 0.12, 72, "water")
        # An L-shaped offshore sheet makes the coastline readable from more
        # than one spawn direction.  It stays beyond the playable shell and
        # costs one merged primitive regardless of size.
        if boundary in {"harbor-seawall", "coastal-cliffs", "flooded-port", "lake-shore"}:
            side = -1 if stage["seed"] & 1 else 1
            builder.add_box(side * (half + 36), -0.17, 0, 72, 0.10, size * 1.04, "water")
        elif boundary == "tidal-abbey-shore":
            # Four lightweight sheets make a continuous tidal bay.  A stone
            # causeway crosses the north sheet and visually connects the
            # playable fortress to the distant mainland.
            builder.add_box(0, -0.17, half + 36, size * 1.35, 0.10, 72, "water")
            builder.add_box(-half - 36, -0.18, 0, 72, 0.10, size * 1.02, "water")
            builder.add_box(half + 36, -0.18, 0, 72, 0.10, size * 1.02, "water")
            builder.add_box(0, 0.03, -half - 36, 13.5, 0.18, 74, "road")
            builder.add_box(-7.1, 0.34, -half - 36, 0.55, 0.68, 74, "wall_alt")
            builder.add_box(7.1, 0.34, -half - 36, 0.55, 0.68, 74, "wall_alt")
        add_port_horizon_terrain(builder, stage, lod, half)
        # Quay lip and mooring rhythm stop the water/land junction reading as
        # a razor-straight map edge.
        builder.add_box(0, 0.26, -half - 0.55, size * 0.82, 0.52, 1.1, "trim")
        if lod == 0:
            for index in range(-8, 9):
                builder.add_cylinder(index * size * 0.043, 0.72, -half - 1.2, 0.22, 1.44, "trim", 8, 0.18)

    if souko_coast:
        add_souko_coastal_edge(builder, stage, lod, half)

    for spec in boundary_primary_specs(stage, lod, profile):
        if souko_coast and spec["side"] == 3:
            # The real quay/fence/water edge above replaces the generic east
            # warehouse wall; retaining both would bury the coast in boxes.
            continue
        if spec["kind"] == "rock":
            builder.add_rock(
                spec["x"], spec["y"], spec["z"],
                spec["radius"], spec["height"], spec["key"],
                spec["segments"], spec["seed"],
            )
            if lod == 0 and spec["index"] % (3 if stage["id"] == "chikurin" else 2) == 0:
                shoulder_x = spec["x"] + (
                    1.8 + stable_unit(seed, spec["index"], spec["side"] + 211) * 2.6
                ) * (1 if spec["side"] in {0, 2} else -1)
                shoulder_z = spec["z"] + (
                    stable_unit(seed, spec["index"], spec["side"] + 212) - 0.5
                ) * 3.2
                builder.add_rock(
                    shoulder_x, -0.55, shoulder_z,
                    spec["radius"] * 0.72, spec["height"] * 0.56,
                    "natural", 9, seed + spec["index"] + spec["side"] * 181,
                )
            if (
                lod == 0
                and boundary in {"hill-ramparts", "range-earthworks", "mountain-base"}
                and spec["index"] % 4 == 0
            ):
                builder.add_box(
                    spec["x"], 1.1, spec["z"],
                    spec["radius"] * 1.25, 2.2, spec["radius"] * 0.45,
                    "wall_alt",
                )
        elif spec["kind"] == "arch":
            add_arch(
                builder, spec["x"], spec["y"], spec["z"],
                spec["width"], spec["height"], spec["depth"], spec["key"],
            )
        else:
            builder.add_box(
                spec["x"], spec["y"], spec["z"],
                spec["w"], spec["h"], spec["d"], spec["key"],
            )


def add_skyline(builder, stage, lod):
    size = stage["size"]
    half = size / 2
    seed = stage["seed"]
    profile = PROFILES[stage["id"]]
    skyline = profile["skyline"]
    count = 30 if lod == 0 else 18 if lod == 1 else 10
    natural_skyline = skyline in {
        "sunset-ridges", "desert-mesas", "cut-mountain", "forest-pagoda", "rural-valley",
        "ocean-headland", "red-mesas", "alpine-lake", "volcanic-mine", "volcanic-fairground",
        "eruption-caldera", "alpine-military", "coastal-abbey",
    }
    for i in range(count):
        angle = math.tau * i / count + stable_unit(seed, i, 0x51) * 0.08
        radius = half + 82 + stable_unit(seed, i, 0x72) * 74
        x, z = math.cos(angle) * radius, math.sin(angle) * radius
        if natural_skyline:
            rock_radius = 22 + stable_unit(seed, i, 0x37) * 38
            mountain_scale = 1.38 if skyline in {"red-mesas", "cut-mountain", "eruption-caldera"} else 0.62 if skyline == "coastal-abbey" else 0.88 if skyline == "alpine-military" else 1.0
            height = (22 + stable_unit(seed, i, 0x82) * 42) * mountain_scale
            builder.add_rock(x, -2, z, rock_radius, height, "terrain", 18 if lod == 0 else 10 if lod == 1 else 6, seed ^ i)
            if lod == 0 and skyline in {"forest-pagoda", "rural-valley", "alpine-lake", "alpine-military", "coastal-abbey"} and i % 2 == 0:
                tree_radius = radius - 15
                add_tree(builder, math.cos(angle) * tree_radius, math.sin(angle) * tree_radius, 9 + stable_unit(seed, i, 0x83) * 10, seed ^ (i * 17), True, lod)
        elif skyline == "polar-campus":
            rock_radius = 14 + stable_unit(seed, i, 0x37) * 20
            height = 24 + stable_unit(seed, i, 0x82) * 52
            builder.add_rock(x, -3, z, rock_radius, height, "terrain", 18 if lod == 0 else 10 if lod == 1 else 6, seed ^ i)
            if i % 5 == 0:
                builder.add_cylinder(x * 0.86, 5, z * 0.86, 8, 8, "wall", 12 if lod == 0 else 8, 6)
        else:
            width = 8 + stable_unit(seed, i, 0x11) * 18
            depth = 8 + stable_unit(seed, i, 0x12) * 16
            tall_city = skyline in {"neon-megacity", "dense-highrise", "dead-neon-city", "firestorm-blocks", "broken-spires"}
            low_city = skyline in {"garden-palace", "desert-temple", "steaming-ryokan", "military-campus", "port-logistics", "working-harbor", "ghost-harbor"}
            height = 12 + stable_unit(seed, i, 0x13) * (64 if tall_city else 25 if low_city else 42)
            port_city = skyline in {"port-logistics", "working-harbor", "ghost-harbor"}
            airport_city = skyline == "terminal-airfield"
            if port_city and lod <= 1:
                variant = i % 4
                if variant == 0:
                    # Tank farm: round silhouettes prevent the harbor horizon
                    # collapsing into another generic city wall.
                    tank_h = max(9, height * 0.42)
                    builder.add_cylinder(x, tank_h / 2 - 1, z, width * 0.42, tank_h, "wall_alt", 12 if lod == 0 else 8, width * 0.38)
                    builder.add_cylinder(x, tank_h + 0.35, z, width * 0.44, 0.7, "trim", 12 if lod == 0 else 8, width * 0.20)
                elif variant == 1:
                    add_hangar(builder, x, z, width * 1.55, depth, max(7, height * 0.36), "wall_alt")
                elif variant == 2:
                    stack_h = max(18, height * 0.82)
                    builder.add_cylinder(x, stack_h / 2 - 1, z, max(1.2, width * 0.12), stack_h, "trim", 10 if lod == 0 else 7, max(0.8, width * 0.085))
                    builder.add_cylinder(x, stack_h + 0.5, z, max(1.35, width * 0.14), 1.0, "accent", 10 if lod == 0 else 7)
                else:
                    builder.add_box(x, height * 0.28 - 1, z, width * 1.35, height * 0.56, depth, "wall_alt")
                    add_pipe_rack(builder, x, z - depth * 0.58, min(20, width), min(13, height * 0.44), 3)
            elif airport_city and lod <= 1:
                if i % 5:
                    add_hangar(builder, x, z, width * 1.55, depth * 1.15, max(8, height * 0.32), "wall_alt")
                else:
                    add_tower(builder, x, z, -1, max(22, height * 0.85), "wall_alt", "glass", 10 if lod == 0 else 8)
            elif lod == 2:
                builder.add_box(x, height / 2 - 1, z, width, height, depth, "wall_alt")
            else:
                # Three setback masses give real high-rise/industrial rooflines
                # while remaining a single merged material draw call.
                base_h = height * 0.54
                mid_h = height * 0.29
                top_h = height * 0.17
                builder.add_box(x, base_h / 2 - 1, z, width, base_h, depth, "wall_alt")
                shift_x = (stable_unit(seed, i, 0x91) - 0.5) * width * 0.22
                shift_z = (stable_unit(seed, i, 0x92) - 0.5) * depth * 0.22
                builder.add_box(x + shift_x, base_h + mid_h / 2 - 1, z + shift_z, width * 0.76, mid_h, depth * 0.78, "wall_alt")
                builder.add_box(x + shift_x * 1.25, base_h + mid_h + top_h / 2 - 1, z + shift_z * 1.25, width * 0.48, top_h, depth * 0.52, "wall")
                # Inner-facing window/service bands give scale and stop the
                # skyline reading as floating grey blocks.  They remain one
                # merged glass/emissive material batch for the entire map.
                if lod == 0:
                    band_key = "emissive" if tall_city and i % 3 == 0 else "glass"
                    for level in range(3):
                        band_y = max(2.2, base_h * (0.26 + level * 0.22))
                        if abs(x) > abs(z):
                            face_x = x - math.copysign(width / 2 + 0.045, x)
                            builder.add_box(face_x, band_y, z, 0.09, 0.58, depth * 0.72, band_key)
                        else:
                            face_z = z - math.copysign(depth / 2 + 0.045, z)
                            builder.add_box(x, band_y, face_z, width * 0.72, 0.58, 0.09, band_key)
                    if i % 5 == 0:
                        builder.add_cylinder(x, height + 3.4, z, 0.14, 6.4, "trim", 7, 0.07)
            if lod == 0 and i % 4 == 0 and not (port_city or airport_city):
                cap_key = "emissive" if skyline in {"neon-megacity", "dead-neon-city", "firestorm-blocks"} else "accent"
                # Seat flush on the top tier's own real top surface. The three
                # tiers above are all centred at "<tier top>/2 - 1" (a 1m
                # ground-embed baked into every one of them), so the top
                # tier's actual top surface is height-1, not height. This cap
                # used to float at height+0.8 -- exactly 1.2m of open sky
                # above the roof on every fourth skyline building -- because
                # it never got the same -1 embed as the mass it sits on
                # (measurementDefect3's orphan-emissive class; see
                # tools/blender/a23/orphan.py).
                cap_h = 1.2
                builder.add_box(x, height - 1 + cap_h / 2, z, width * 0.58, cap_h, depth * 0.58, cap_key)
            if lod == 0 and skyline in {"neon-megacity", "dead-neon-city", "firestorm-blocks", "dense-highrise", "broken-spires"} and i % 2 == 0:
                # Seat flush on the base tier's own wall face, the same
                # copysign-flush technique the window/service band above
                # already uses. The previous panel_x/panel_z = x*0.965/z*0.965
                # radial pull-in tracked distance from the map origin, not
                # this building's own half-width/half-depth, so on a building
                # not aligned with a cardinal ray from the origin it commonly
                # missed the wall by several metres -- the dominant orphan-
                # emissive pattern this round's catalogue-wide audit found
                # (145 of 200 surveyed instances).
                panel_h = min(max(1.8, height * 0.16), base_h * 0.4)
                panel_y = base_h * 0.42
                panel_embed = 0.045
                if abs(x) > abs(z):
                    face_x = x - math.copysign(width / 2 + panel_embed, x)
                    builder.add_box(face_x, panel_y, z, panel_embed * 2, panel_h, depth * 0.56, "emissive")
                else:
                    face_z = z - math.copysign(depth / 2 + panel_embed, z)
                    builder.add_box(x, panel_y, face_z, width * 0.56, panel_h, panel_embed * 2, "emissive")
            if lod == 0 and skyline in {"port-logistics", "working-harbor", "ghost-harbor", "furnace-city", "factory-stacks"} and i % 6 == 0:
                add_pipe_rack(builder, x, z - depth * 0.6, min(20, width * 1.1), min(16, height * 0.5), 3)


def add_arch(builder, x, y, z, width, height, depth, key="wall"):
    pillar = max(1.2, width * 0.16)
    builder.add_box(x - width / 2 + pillar / 2, y + height / 2, z, pillar, height, depth, key)
    builder.add_box(x + width / 2 - pillar / 2, y + height / 2, z, pillar, height, depth, key)
    builder.add_box(x, y + height - pillar / 2, z, width, pillar, depth, key)


def add_tower(builder, x, z, base_y, height, key="wall", cap="accent", segments=12):
    builder.add_cylinder(x, base_y + height / 2, z, 3.4, height, key, segments, 2.8)
    builder.add_cylinder(x, base_y + height + 1.2, z, 5.0, 2.4, cap, segments, 4.2)
    builder.add_cylinder(x, base_y + height + 5.0, z, 0.45, 7.6, "trim", 8, 0.22)


def add_hangar(builder, x, z, width=30, depth=18, height=9, key="wall_alt", open_front=True):
    wall = max(0.75, min(1.25, width * 0.035))
    builder.add_box(x - width / 2 + wall / 2, height / 2, z, wall, height, depth, key)
    builder.add_box(x + width / 2 - wall / 2, height / 2, z, wall, height, depth, key)
    builder.add_box(x, height / 2, z - depth / 2 + wall / 2, width, height, wall, key)
    if not open_front:
        builder.add_box(x, height / 2, z + depth / 2 - wall / 2, width, height, wall, key)
    builder.add_box(x, height + 0.4, z, width + 1.4, 0.8, depth + 1.2, "trim")
    builder.add_box(x, height * 0.62, z + depth / 2 + 0.035, width * 0.58, height * 0.42, 0.07, "glass")


def add_tree(builder, x, z, height, seed, conifer=False, lod=0):
    segments = 7 if lod == 0 else 5
    trunk_height = height * (0.38 if conifer else 0.52)
    builder.add_cylinder(x, trunk_height / 2, z, max(0.14, height * 0.025), trunk_height, "trim", segments)
    if conifer:
        tiers = 3 if lod == 0 else 2
        for tier in range(tiers):
            tier_height = height * (0.32 - tier * 0.035)
            tier_y = height * (0.42 + tier * 0.18)
            radius = height * (0.20 - tier * 0.035)
            builder.add_cylinder(x, tier_y, z, radius, tier_height, "natural", segments, 0.06)
    else:
        crown_y = height * 0.58
        builder.add_rock(x, crown_y, z, height * 0.20, height * 0.38, "natural", segments, seed)


def add_bamboo(builder, x, z, height, seed, lod=0):
    # Silhouette-first bamboo: two irregular stalks and three collars read as
    # a cluster at FPS distance.  The older 3x5-collar construction exploded
    # UV-split GLB vertices without a visible gain.
    stalks = 2 if lod == 0 else 1
    for index in range(stalks):
        sx = x + (stable_unit(seed, index, 0xB01) - 0.5) * 1.25
        sz = z + (stable_unit(seed, index, 0xB02) - 0.5) * 1.25
        stalk_height = height * (0.82 + stable_unit(seed, index, 0xB03) * 0.28)
        builder.add_cylinder(sx, stalk_height / 2, sz, 0.11 if lod == 0 else 0.09, stalk_height, "natural", 5, 0.085)
        if lod == 0:
            for node in (2, 4, 6):
                builder.add_cylinder(sx, stalk_height * node / 8, sz, 0.15, 0.045, "trim", 5, 0.15)
            builder.add_rock(sx, stalk_height * 0.74, sz, 1.05, stalk_height * 0.20, "natural", 5, seed + index * 31)


def add_container_stack(builder, x, z, columns=3, levels=2, accent_every=3):
    for column in range(columns):
        for level in range(levels - (1 if column == columns - 1 and levels > 1 else 0)):
            key = "accent" if (column + level) % accent_every == 0 else "wall_alt"
            builder.add_box(x + column * 6.5, 1.45 + level * 3.0, z, 6.0, 2.8, 2.55, key)
            builder.add_box(x + column * 6.5, 1.45 + level * 3.0, z + 1.31, 5.0, 2.1, 0.06, "trim")


def add_vehicle_silhouette(builder, x, z, length=6.0, width=2.8, height=2.2):
    builder.add_box(x, height * 0.38, z, length, height * 0.62, width, "obstacle")
    builder.add_box(x - length * 0.12, height * 0.78, z, length * 0.46, height * 0.46, width * 0.82, "wall_alt")
    for sx in (-length * 0.32, length * 0.32):
        for sz in (-width * 0.47, width * 0.47):
            builder.add_box(x + sx, 0.34, z + sz, length * 0.20, 0.68, 0.24, "trim")


def add_gabled_house(
    builder,
    x,
    z,
    width=10.0,
    depth=8.0,
    storeys=1,
    style="rural",
    lod=0,
    damaged=False,
    yaw=0.0,
):
    """Build a production-style modular house, merged by material.

    Geometry is concentrated on first-person silhouette and contact: stone
    plinth, deep eaves, gutters, framed windows on two facades, door recess,
    chimney, dormer/balcony and optional exposed ruin rafters.  It remains a
    handful of material batches after export instead of one draw call per part.
    """
    storey_h = 3.18 if style in {"rural", "timber"} else 3.48 if style in {"heritage", "ryokan"} else 3.72
    body_h = storeys * storey_h
    heritage = style in {"timber", "heritage", "ryokan"}
    modern = style in {"modern", "urban"}
    material_index = int(abs(x) * 1.7 + abs(z) * 2.3 + storeys * 13)
    wall_key = (
        "wood"
        if style == "timber"
        else "wall_warm"
        if heritage or style == "rural"
        else "wall_alt"
    )
    # Houses are called from many stage-specific passes without a stage
    # argument.  Non-heritage kits therefore alternate between the globally
    # available facade variants using their world placement; every material is
    # still authored from the active stage palette.
    if not heritage and style != "rural":
        wall_key = ("wall_cool", "wall_alt", "wall", "wall_weathered")[material_index % 4]
    roof_key = "roof"
    cosine = math.cos(yaw)
    sine = math.sin(yaw)

    def point(lx, lz):
        return x + lx * cosine - lz * sine, z + lx * sine + lz * cosine

    def box(lx, ly, lz, w, h, d, key):
        px, pz = point(lx, lz)
        builder.add_oriented_box(px, ly, pz, w, h, d, yaw, key)

    # Seated foundation and wall mass.  The darker plinth removes the floating
    # dollhouse read on uneven terrain and wet streets.
    box(0, 0.22, 0, width + 0.34, 0.44, depth + 0.34, "wall_alt")
    box(0, body_h / 2 + 0.42, 0, width, body_h, depth, wall_key)
    overhang = 0.92 if heritage else 0.58
    roof_h = max(1.55, width * (0.21 if heritage else 0.15))
    if not damaged or lod > 0:
        builder.add_oriented_gable_roof(
            x,
            body_h + 0.42,
            z,
            width + overhang * 2,
            roof_h,
            depth + overhang * 2,
            yaw,
            roof_key,
        )
    else:
        # One seated roof fragment plus exposed rafters; damage changes the
        # silhouette, not only its colour.
        fragment_x, fragment_z = point(-width * 0.25, 0)
        builder.add_oriented_gable_roof(
            fragment_x,
            body_h + 0.42,
            fragment_z,
            width * 0.52,
            roof_h,
            depth + overhang,
            yaw,
            roof_key,
        )
        for index in range(5 if lod == 0 else 3):
            lx = -width * 0.05 + index * width * 0.12
            start = point(lx, -depth * 0.48)
            end = point(lx + width * (0.16 if index % 2 else -0.08), depth * 0.28)
            builder.add_beam(
                (start[0], body_h + 0.55, start[1]),
                (end[0], body_h + roof_h * (0.82 - index * 0.08), end[1]),
                0.11,
                0.09,
                "trim",
            )

    front = depth / 2 + 0.056
    # Recessed door, lintel, threshold and canopy.
    door_x = -width * 0.18 if width > 11 else 0
    box(door_x, 1.48, front, min(1.42, width * 0.15), 2.38, 0.11, "trim")
    box(door_x, 2.80, front + 0.02, min(1.72, width * 0.19), 0.16, 0.16, "accent")
    box(door_x, 0.48, front + 0.17, min(1.78, width * 0.19), 0.12, 0.46, "wall_alt")
    if lod == 0:
        box(door_x, 3.03, front + 0.54, min(2.5, width * 0.26), 0.18, 1.08, roof_key)
        for sx in (-0.92, 0.92):
            box(door_x + sx, 1.55, front + 0.48, 0.11, 2.7, 0.11, "trim")

    bays = 2 if lod > 0 else max(3, min(6, int(width // 2.8)))
    for level in range(storeys):
        pane_y = 0.42 + level * storey_h + storey_h * 0.56
        for bay in range(bays):
            lx = (bay - (bays - 1) / 2) * width * 0.76 / max(1, bays - 1)
            if abs(lx - door_x) < width * 0.12 and level == 0:
                continue
            pane_w = min(1.34, width / (bays + 1) * 0.58)
            pane_h = 1.18 if modern else 1.02
            pane_key = "emissive" if (style in {"heritage", "urban"} and (bay + level) % 4 == 0) else "glass"
            box(lx, pane_y, front + 0.014, pane_w, pane_h, 0.08, pane_key)
            if lod == 0:
                box(lx, pane_y, front + 0.067, pane_w + 0.20, 0.10, 0.10, "trim")
                box(lx, pane_y, front + 0.068, 0.08, pane_h + 0.18, 0.10, "trim")
        box(0, 0.42 + level * storey_h + 0.18, front + 0.018, width * 0.94, 0.13, 0.12, "trim")

    # Side facade windows stop houses reading as flat theatrical fronts.
    if lod == 0:
        side_x = width / 2 + 0.055
        for level in range(storeys):
            pane_y = 0.42 + level * storey_h + storey_h * 0.56
            for lz in (-depth * 0.24, depth * 0.24):
                box(side_x, pane_y, lz, 0.08, 1.0, min(1.25, depth * 0.22), "glass")
                box(side_x + 0.02, pane_y, lz, 0.11, 0.08, min(1.45, depth * 0.26), "trim")

    if heritage:
        for lx in (-width * 0.44, 0, width * 0.44):
            box(lx, body_h / 2 + 0.42, front + 0.024, 0.16, body_h * 0.92, 0.13, "trim")
        box(0, body_h + 0.34, front + 0.024, width * 0.96, 0.22, 0.15, "trim")
        if lod == 0 and storeys >= 2:
            # Shallow balcony with posts and four rail segments.
            box(width * 0.20, storey_h + 0.58, front + 0.74, width * 0.48, 0.18, 1.42, "wall_alt")
            for index in range(5):
                box(width * (0.00 + index * 0.10), storey_h + 1.13, front + 1.34, 0.08, 1.0, 0.08, "trim")
            box(width * 0.20, storey_h + 1.52, front + 1.34, width * 0.48, 0.10, 0.10, "trim")

    if lod == 0:
        # Chimney, rain gutters and one dormer provide roof-scale cues.
        chimney_x, chimney_z = point(width * 0.30, -depth * 0.12)
        builder.add_oriented_box(chimney_x, body_h + roof_h * 0.62, chimney_z, 0.72, roof_h * 1.16, 0.72, yaw, "wall_alt")
        for local_z in (-depth / 2 - overhang * 0.72, depth / 2 + overhang * 0.72):
            a = point(-width / 2 - overhang * 0.72, local_z)
            b = point(width / 2 + overhang * 0.72, local_z)
            builder.add_cylinder_between((a[0], body_h + 0.34, a[1]), (b[0], body_h + 0.34, b[1]), 0.075, "trim", 6)
        if storeys >= 2 and width >= 10 and not damaged:
            dormer_x, dormer_z = point(width * 0.18, depth * 0.18)
            builder.add_oriented_box(dormer_x, body_h + roof_h * 0.42, dormer_z, 2.0, 1.55, 1.6, yaw, "wall")
            builder.add_oriented_gable_roof(dormer_x, body_h + roof_h * 0.78, dormer_z, 2.4, 0.85, 2.1, yaw, roof_key)
            pane_x, pane_z = point(width * 0.18, depth * 0.18 + 0.84)
            builder.add_oriented_box(pane_x, body_h + roof_h * 0.43, pane_z, 0.72, 0.82, 0.08, yaw, "glass")


def add_stone_lantern(builder, x, z, height=2.2, emissive=False):
    builder.add_box(x, height * 0.28, z, 0.42, height * 0.56, 0.42, "wall_alt")
    builder.add_box(x, height * 0.61, z, 0.82, 0.22, 0.82, "trim")
    builder.add_box(x, height * 0.76, z, 0.58, 0.42, 0.58, "emissive" if emissive else "wall")
    builder.add_gable_roof(x, height * 0.97, z, 1.05, 0.32, 0.82, "accent", "x")


def add_train_car(builder, x, z, length=24.0, lod=0, ruined=False):
    builder.add_box(x, 1.65, z, length, 3.3, 3.1, "wall_alt")
    builder.add_box(x, 3.48, z, length * 0.92, 0.36, 3.2, "trim")
    windows = 7 if lod == 0 else 4
    for index in range(windows):
        px = x + (index - (windows - 1) / 2) * length * 0.82 / max(1, windows - 1)
        if ruined and index in {2, 5}:
            continue
        builder.add_box(px, 2.15, z + 1.57, length / windows * 0.52, 0.92, 0.08, "glass")
    for wheel_x in (-length * 0.34, length * 0.34):
        builder.add_box(x + wheel_x, 0.30, z - 1.48, length * 0.16, 0.60, 0.28, "trim")
        builder.add_box(x + wheel_x, 0.30, z + 1.48, length * 0.16, 0.60, 0.28, "trim")


def add_workboat(builder, x, z, length=18.0, lod=0, wrecked=False):
    hull_y = -0.02 if wrecked else 0.22
    builder.add_box(x, hull_y + 0.72, z, length, 1.44, 4.2, "wall_alt")
    builder.add_beam((x - length / 2, hull_y + 0.16, z - 2.1), (x + length / 2, hull_y + 0.16, z - 1.45), 0.18, 0.24, "trim")
    builder.add_beam((x - length / 2, hull_y + 0.16, z + 2.1), (x + length / 2, hull_y + 0.16, z + 1.45), 0.18, 0.24, "trim")
    builder.add_box(x - length * 0.12, hull_y + 2.15, z, length * 0.34, 1.65, 3.0, "wall")
    builder.add_box(x - length * 0.12, hull_y + 2.45, z + 1.52, length * 0.23, 0.62, 0.08, "glass")
    builder.add_beam((x, hull_y + 2.4, z), (x + length * 0.24, hull_y + (4.2 if not wrecked else 3.2), z), 0.10, 0.10, "trim")


# Blender replacement connection map (all dimensions are metres):
# - vehicle body bottom <-> wheel crown: 0.08m overlap on Y
# - cab / turret / machine shell <-> chassis top: 0.06m overlap on Y
# - crane mast top <-> boom underside: 0.12m overlap on Y
# - roof underside <-> authoritative district wall top: 0.06m overlap on Y
# - fence/sign cross-member <-> vertical post: 0.04m overlap in plan
# - house wall bottom <-> stone plinth: 0.20m overlap on Y
# Every prop is generated at PropPlacement.cx/cz/rotRad.  Runtime BoxSpec
# colliders remain authoritative and are deliberately not exported from Blender.


def prop_point(placement, lx=0.0, lz=0.0):
    """Transform a local prop point with the placement's continuous yaw."""
    yaw = placement["rotRad"]
    scale = placement.get("scaleJitter", 1.0)
    cosine = math.cos(yaw)
    sine = math.sin(yaw)
    lx *= scale
    lz *= scale
    return (
        placement["cx"] + lx * cosine - lz * sine,
        placement["cz"] + lx * sine + lz * cosine,
    )


def prop_box(builder, placement, lx, y, lz, width, height, depth, key="obstacle"):
    x, z = prop_point(placement, lx, lz)
    scale = placement.get("scaleJitter", 1.0)
    builder.add_oriented_box(
        x,
        y * scale,
        z,
        width * scale,
        height * scale,
        depth * scale,
        placement["rotRad"],
        key,
    )


def prop_cylinder(builder, placement, lx, y, lz, radius, height, key="trim", segments=10, top_radius=None):
    x, z = prop_point(placement, lx, lz)
    scale = placement.get("scaleJitter", 1.0)
    builder.add_cylinder(
        x,
        y * scale,
        z,
        radius * scale,
        height * scale,
        key,
        segments,
        None if top_radius is None else top_radius * scale,
    )


def prop_beam(builder, placement, start, end, width, depth, key="trim"):
    sx, sz = prop_point(placement, start[0], start[2])
    ex, ez = prop_point(placement, end[0], end[2])
    scale = placement.get("scaleJitter", 1.0)
    builder.add_beam(
        (sx, start[1] * scale, sz),
        (ex, end[1] * scale, ez),
        width * scale,
        depth * scale,
        key,
    )


def prop_axle(builder, placement, lx, y, half_width, radius, key="trim", segments=10):
    start_x, start_z = prop_point(placement, lx, -half_width)
    end_x, end_z = prop_point(placement, lx, half_width)
    scale = placement.get("scaleJitter", 1.0)
    builder.add_cylinder_between(
        (start_x, y * scale, start_z),
        (end_x, y * scale, end_z),
        radius * scale,
        key,
        segments,
    )


def add_vehicle_prop(builder, placement, kind, lod):
    """Game-scale vehicles with a readable cabin, glass, running gear and lamps."""
    if kind == "truck":
        length, width, chassis_y = 7.4, 2.55, 0.78
        prop_box(builder, placement, 0.35, chassis_y, 0, 6.9, 0.58, width, "trim")
        prop_box(builder, placement, -2.15, 1.72, 0, 2.05, 2.15, width * 0.94, "obstacle")
        prop_box(builder, placement, 1.55, 1.55, 0, 4.65, 1.75, width * 0.96, "wall_alt")
        prop_box(builder, placement, -3.20, 1.95, 0, 0.08, 0.76, width * 0.72, "glass")
        if lod == 0:
            prop_box(builder, placement, -2.12, 2.08, width * 0.475, 1.16, 0.62, 0.08, "glass")
            prop_box(builder, placement, -2.12, 2.08, -width * 0.475, 1.16, 0.62, 0.08, "glass")
            for rail_x in (-0.2, 1.7, 3.55):
                prop_box(builder, placement, rail_x, 2.42, 0, 0.10, 0.18, width * 1.02, "accent")
            prop_box(builder, placement, 3.76, 1.26, 0, 0.12, 0.56, width * 0.72, "accent")
        wheel_xs = (-2.25, 1.35, 2.85)
    elif kind in {"derelictcar", "barricadecar"}:
        length, width, chassis_y = 4.7, 1.92, 0.62
        prop_box(builder, placement, 0, chassis_y, 0, length, 0.62, width, "obstacle")
        prop_box(builder, placement, -0.20, 1.28, 0, 2.42, 0.92, width * 0.84, "wall_alt")
        prop_box(builder, placement, -1.18, 1.42, 0, 0.10, 0.56, width * 0.68, "glass")
        prop_box(builder, placement, 0.80, 1.42, 0, 0.09, 0.54, width * 0.67, "glass")
        if lod == 0:
            prop_box(builder, placement, 0, 1.02, width * 0.49, length * 0.70, 0.10, 0.08, "trim")
            prop_box(builder, placement, -2.38, 0.74, 0, 0.12, 0.26, width * 0.72, "accent")
            if kind == "barricadecar":
                prop_beam(builder, placement, (-2.25, 0.18, -1.12), (2.15, 1.74, 1.08), 0.10, 0.10, "accent")
        wheel_xs = (-1.48, 1.48)
    else:  # tankhull
        length, width, chassis_y = 6.4, 3.55, 0.78
        prop_box(builder, placement, 0, chassis_y, 0, length, 1.18, width, "obstacle")
        prop_box(builder, placement, -0.25, 1.74, 0, 3.15, 0.92, width * 0.72, "wall_alt")
        prop_cylinder(builder, placement, -0.25, 2.32, 0, 1.10, 0.62, "trim", 12, 0.82)
        prop_beam(builder, placement, (0.15, 2.38, 0), (4.15, 2.32, 0), 0.16, 0.16, "trim")
        if lod == 0:
            for lx in (-2.4, -1.2, 0, 1.2, 2.4):
                prop_axle(builder, placement, lx, 0.50, width * 0.53, 0.34, "trim", 8)
            for side in (-1, 1):
                prop_box(builder, placement, 0, 0.55, side * width * 0.55, length * 0.92, 0.58, 0.28, "wall_alt")
        return
    for wheel_x in wheel_xs:
        prop_axle(builder, placement, wheel_x, 0.48, width * 0.54, 0.42, "trim", 10 if lod == 0 else 6)


def add_crane_prop(builder, placement, kind, lod):
    detail = lod == 0
    if kind == "towercrane":
        height = 18.0
        prop_box(builder, placement, 0, height / 2, 0, 0.72, height, 0.72, "trim")
        cells = 7 if detail else 4
        for index in range(cells):
            y0 = index * height / cells
            y1 = (index + 1) * height / cells
            prop_beam(builder, placement, (-0.44, y0, 0), (0.44, y1, 0), 0.055, 0.055, "accent")
            prop_beam(builder, placement, (0.44, y0, 0), (-0.44, y1, 0), 0.055, 0.055, "accent")
        prop_beam(builder, placement, (-3.0, 17.75, 0), (8.4, 17.75, 0), 0.22, 0.22, "accent")
        prop_beam(builder, placement, (-2.8, 17.72, 0), (0, 20.8, 0), 0.16, 0.16, "trim")
        prop_beam(builder, placement, (0, 20.8, 0), (8.4, 17.72, 0), 0.13, 0.13, "trim")
        prop_box(builder, placement, -0.78, 18.38, 0, 1.55, 1.18, 1.25, "wall_alt")
        if detail:
            prop_beam(builder, placement, (4.9, 17.68, 0), (4.9, 11.2, 0), 0.045, 0.045, "trim")
            prop_box(builder, placement, 4.9, 11.05, 0, 0.58, 0.20, 0.58, "accent")
    else:
        height, span = 8.2, 9.3
        for lx in (-span / 2, span / 2):
            prop_box(builder, placement, lx, height / 2, 0, 0.72, height, 0.72, "trim")
            if detail:
                prop_beam(builder, placement, (lx - 0.8, 0, -1.3), (lx, 8.0, 0), 0.10, 0.10, "accent")
                prop_beam(builder, placement, (lx + 0.8, 0, 1.3), (lx, 8.0, 0), 0.10, 0.10, "accent")
        prop_box(builder, placement, 0, 8.05, 0, span + 0.9, 0.72, 0.86, "accent")
        prop_box(builder, placement, 0, 8.60, 0, 2.0, 0.82, 1.36, "wall_alt")
        if detail:
            for lx in (-3.1, 0, 3.1):
                prop_beam(builder, placement, (lx, 7.75, 0), (lx, 5.15, 0), 0.045, 0.045, "trim")


def add_tree_prop(builder, placement, kind, lod):
    seed = int(abs(placement["cx"] * 31 + placement["cz"] * 17)) + len(kind) * 97
    scale = placement.get("scaleJitter", 1.0)
    if kind == "bamboo":
        count = 5 if lod == 0 else 3
        for index in range(count):
            angle = index * 2.399
            radius = 0.16 + (index % 3) * 0.22
            x, z = prop_point(placement, math.cos(angle) * radius, math.sin(angle) * radius)
            height = (4.8 + (index % 4) * 0.55) * scale
            builder.add_cylinder(x, height / 2, z, 0.075 * scale, height, "natural", 6, 0.055 * scale)
            if lod == 0:
                for level in (0.40, 0.62, 0.82):
                    px, pz = prop_point(placement, math.cos(angle + level * 3) * 0.62, math.sin(angle + level * 3) * 0.62)
                    builder.add_box(px, height * level, pz, 0.92 * scale, 0.07 * scale, 0.24 * scale, "natural")
        return
    if kind == "deadtree":
        prop_cylinder(builder, placement, 0, 2.35, 0, 0.20, 4.7, "natural", 7, 0.10)
        branches = 7 if lod == 0 else 3
        for index in range(branches):
            angle = index * 2.17 + stable_unit(seed, index, 0x17) * 0.8
            start_y = 2.2 + (index % 4) * 0.52
            length = 1.0 + stable_unit(seed, index, 0x52) * 1.25
            prop_beam(
                builder,
                placement,
                (0, start_y, 0),
                (math.cos(angle) * length, start_y + 0.72 + index % 2 * 0.30, math.sin(angle) * length),
                0.07,
                0.06,
                "natural",
            )
        return
    trunk_h = 3.8 if kind == "conifer" else 3.5
    prop_cylinder(builder, placement, 0, trunk_h / 2, 0, 0.22, trunk_h, "natural", 8, 0.13)
    if kind == "conifer":
        crowns = 5 if lod == 0 else 3 if lod == 1 else 2
        for index in range(crowns):
            y = 2.0 + index * 0.72
            radius = 1.65 - index * 0.20
            prop_cylinder(builder, placement, 0, y + 0.68, 0, radius, 1.36, "natural", 9 if lod == 0 else 6, 0.12)
    else:
        crowns = 7 if lod == 0 else 4 if lod == 1 else 2
        key = "accent" if kind == "sakura" else "natural"
        for index in range(crowns):
            angle = index * 2.399
            ring = 0.72 if index else 0
            x, z = prop_point(placement, math.cos(angle) * ring, math.sin(angle) * ring)
            radius = (1.20 + stable_unit(seed, index, 0x88) * 0.38) * scale
            builder.add_rock(x, 2.62 * scale, z, radius, 1.72 * scale, key, 8 if lod == 0 else 6, seed + index)
        if lod == 0:
            for index in range(5):
                angle = index * 1.29
                prop_beam(builder, placement, (0, 2.55, 0), (math.cos(angle) * 1.45, 3.45, math.sin(angle) * 1.45), 0.08, 0.07, "natural")


def add_small_prop(builder, placement, kind, lod):
    detail = lod == 0
    if kind == "concretebarrier":
        prop_box(builder, placement, 0, 0.46, 0, 0.72, 0.92, 2.62, "wall")
        prop_box(builder, placement, 0, 0.98, 0, 0.52, 0.20, 2.42, "trim")
        if detail:
            for lz in (-0.82, 0, 0.82):
                prop_box(builder, placement, 0.37, 0.48, lz, 0.04, 0.54, 0.24, "accent")
    elif kind == "fence":
        for lx in (-2.0, 0, 2.0):
            prop_box(builder, placement, lx, 0.82, 0, 0.12, 1.64, 0.12, "trim")
        for y in (0.26, 0.82, 1.38):
            prop_box(builder, placement, 0, y, 0, 4.12, 0.07, 0.08, "trim")
        if detail:
            for lx in (-1.65, -0.85, 0, 0.85, 1.65):
                prop_beam(builder, placement, (lx - 0.45, 0.18, 0), (lx + 0.45, 1.48, 0), 0.022, 0.022, "wall_alt")
    elif kind == "bench":
        prop_box(builder, placement, 0, 0.48, 0, 1.78, 0.14, 0.58, "accent")
        prop_box(builder, placement, 0, 0.98, -0.27, 1.78, 0.70, 0.11, "accent")
        for lx in (-0.66, 0.66):
            prop_box(builder, placement, lx, 0.25, 0, 0.10, 0.50, 0.46, "trim")
        if detail:
            for lx in (-0.58, -0.20, 0.20, 0.58):
                prop_box(builder, placement, lx, 0.74, -0.34, 0.18, 0.07, 0.08, "trim")
    elif kind == "vendingmachine":
        prop_box(builder, placement, 0, 0.94, 0, 0.92, 1.88, 0.68, "wall_alt")
        prop_box(builder, placement, 0, 1.18, 0.35, 0.68, 0.86, 0.05, "emissive")
        prop_box(builder, placement, 0.22, 0.49, 0.36, 0.20, 0.16, 0.06, "accent")
        if detail:
            for row in range(3):
                for col in range(4):
                    prop_box(builder, placement, -0.25 + col * 0.17, 1.43 - row * 0.21, 0.39, 0.11, 0.12, 0.025, "glass")
    elif kind == "pallet":
        for y in (0.06, 0.20):
            for lz in (-0.38, 0, 0.38):
                prop_box(builder, placement, 0, y, lz, 1.36, 0.09, 0.19, "accent")
        for lx in (-0.48, 0, 0.48):
            prop_box(builder, placement, lx, 0.13, 0, 0.19, 0.18, 1.02, "wall_alt")
    elif kind == "supplycrate":
        for layer, (lx, lz) in enumerate(((0, 0), (0.32, 0.28))):
            prop_box(builder, placement, lx, 0.48 + layer * 0.82, lz, 1.08, 0.86, 1.08, "accent")
            if detail:
                for side in (-0.42, 0.42):
                    prop_beam(builder, placement, (side, 0.12 + layer * 0.82, -0.48), (-side, 0.84 + layer * 0.82, 0.48), 0.035, 0.035, "trim")
    elif kind == "drumgroup":
        for lx, lz, layer in ((-0.48, 0, 0), (0.48, 0, 0), (0, 0.54, 0)):
            prop_cylinder(builder, placement, lx, 0.46 + layer, lz, 0.32, 0.92, "obstacle", 10 if detail else 6)
            if detail:
                for y in (0.11, 0.46, 0.81):
                    prop_cylinder(builder, placement, lx, y, lz, 0.34, 0.05, "trim", 10)
    elif kind == "gasbottlegroup":
        for index, (lx, lz) in enumerate(((-0.42, 0), (0.42, 0), (0, 0.42))):
            prop_cylinder(builder, placement, lx, 0.52, lz, 0.18, 0.92, "obstacle", 8, 0.15)
            prop_cylinder(builder, placement, lx, 1.03, lz, 0.10, 0.12, "trim", 6)
        prop_box(builder, placement, 0, 0.48, 0.18, 1.34, 0.98, 1.08, "trim")
    elif kind == "rubble":
        pieces = 8 if detail else 4 if lod == 1 else 2
        seed = int(abs(placement["cx"] * 13 + placement["cz"] * 19))
        for index in range(pieces):
            angle = stable_unit(seed, index, 0x901) * math.tau
            ring = stable_unit(seed, index, 0x902) * 1.08
            x, z = prop_point(placement, math.cos(angle) * ring, math.sin(angle) * ring)
            radius = 0.34 + stable_unit(seed, index, 0x903) * 0.52
            builder.add_rock(x, 0, z, radius, 0.42 + radius * 0.55, "wall_alt" if index % 3 else "accent", 6, seed + index)


def add_structural_prop(builder, placement, kind, lod):
    detail = lod == 0
    if kind in {"towercrane", "portalkrane"}:
        add_crane_prop(builder, placement, kind, lod)
    elif kind == "smokestack":
        prop_cylinder(builder, placement, 0, 8.0, 0, 0.82, 16.0, "wall_alt", 12 if detail else 8, 0.52)
        bands = 6 if detail else 3
        for index in range(bands):
            prop_cylinder(builder, placement, 0, 2.0 + index * 2.45, 0, 0.87 - index * 0.035, 0.18, "accent", 10)
    elif kind in {"gastank", "watertower"}:
        tank_y = 3.75 if kind == "watertower" else 2.65
        if kind == "watertower":
            for lx, lz in ((-1.25, -1.25), (1.25, -1.25), (-1.25, 1.25), (1.25, 1.25)):
                prop_beam(builder, placement, (lx, 0, lz), (lx * 0.72, 4.2, lz * 0.72), 0.10, 0.10, "trim")
        prop_cylinder(builder, placement, 0, tank_y, 0, 2.15 if kind == "gastank" else 1.70, 3.45 if kind == "gastank" else 2.55, "wall", 14 if detail else 8, 1.92 if kind == "gastank" else 1.58)
        prop_cylinder(builder, placement, 0, tank_y + (1.85 if kind == "gastank" else 1.42), 0, 2.0 if kind == "gastank" else 1.58, 0.18, "accent", 12)
        if detail:
            prop_beam(builder, placement, (-2.3, 0.3, 0), (-2.3, tank_y + 1.2, 0), 0.055, 0.055, "trim")
            for y in (1.1, 2.1, 3.1):
                prop_box(builder, placement, -2.3, y, 0, 0.36, 0.06, 0.75, "trim")
    elif kind == "transformer":
        prop_box(builder, placement, 0, 0.82, 0, 2.25, 1.52, 1.66, "wall_alt")
        for lx in (-0.88, -0.44, 0, 0.44, 0.88):
            prop_box(builder, placement, lx, 0.82, 0.87, 0.12, 1.30, 0.12, "trim")
        for lx in (-0.65, 0.65):
            prop_cylinder(builder, placement, lx, 2.18, 0, 0.15, 1.42, "trim", 7, 0.10)
            if detail:
                for y in (1.72, 2.04, 2.36):
                    prop_cylinder(builder, placement, lx, y, 0, 0.30, 0.10, "accent", 8)
    elif kind in {"antenna", "utilitypole", "streetlight"}:
        height = 12.0 if kind == "antenna" else 8.0 if kind == "utilitypole" else 5.2
        prop_cylinder(builder, placement, 0, height / 2, 0, 0.12 if kind != "utilitypole" else 0.17, height, "trim", 8, 0.07)
        if kind == "antenna":
            for y in (4.0, 7.0, 10.0):
                prop_box(builder, placement, 0, y, 0, 1.8 if detail else 1.1, 0.10, 0.10, "accent")
            if detail:
                for angle in (0, math.pi * 0.5, math.pi, math.pi * 1.5):
                    prop_beam(builder, placement, (0, 10.8, 0), (math.cos(angle) * 2.6, 0, math.sin(angle) * 2.6), 0.025, 0.025, "trim")
        elif kind == "utilitypole":
            prop_box(builder, placement, 0, 7.25, 0, 3.8, 0.14, 0.16, "trim")
            if detail:
                for lx in (-1.4, 0, 1.4):
                    prop_cylinder(builder, placement, lx, 7.52, 0, 0.09, 0.42, "glass", 7, 0.06)
        else:
            prop_beam(builder, placement, (0, 5.0, 0), (0.72, 5.0, 0), 0.08, 0.07, "trim")
            prop_box(builder, placement, 0.78, 4.96, 0, 0.72, 0.18, 0.42, "emissive")
    elif kind == "watchpost":
        for lx, lz in ((-1.35, -1.35), (1.35, -1.35), (-1.35, 1.35), (1.35, 1.35)):
            prop_box(builder, placement, lx, 2.0, lz, 0.18, 4.0, 0.18, "trim")
        prop_box(builder, placement, 0, 4.0, 0, 3.2, 0.26, 3.2, "wall_alt")
        prop_box(builder, placement, 0, 5.03, 0, 2.76, 1.82, 2.76, "wall")
        prop_box(builder, placement, 0, 5.18, 1.42, 1.62, 0.72, 0.08, "glass")
        prop_box(builder, placement, 0, 6.05, 0, 3.5, 0.22, 3.5, "accent")
    elif kind == "scaffold":
        for lx in (-1.45, 1.45):
            for lz in (-0.95, 0.95):
                prop_box(builder, placement, lx, 1.8, lz, 0.10, 3.6, 0.10, "trim")
        for y in (0.25, 1.75, 3.45):
            prop_box(builder, placement, 0, y, 0, 3.1, 0.12, 2.08, "wall_alt")
            if detail:
                prop_beam(builder, placement, (-1.45, y, -0.98), (1.45, y + 1.28, -0.98), 0.035, 0.035, "accent")
                prop_beam(builder, placement, (1.45, y, 0.98), (-1.45, y + 1.28, 0.98), 0.035, 0.035, "accent")
    elif kind == "signboard":
        for lx in (-1.05, 1.05):
            prop_box(builder, placement, lx, 1.7, 0, 0.12, 3.4, 0.12, "trim")
        prop_box(builder, placement, 0, 2.68, 0, 2.72, 1.16, 0.16, "emissive")
        if detail:
            for lx in (-0.72, -0.24, 0.24, 0.72):
                prop_box(builder, placement, lx, 2.68, 0.10, 0.08, 0.72, 0.03, "accent")
    elif kind == "torii":
        for lx in (-1.55, 1.55):
            prop_cylinder(builder, placement, lx, 1.78, 0, 0.22, 3.56, "accent", 9, 0.18)
        prop_box(builder, placement, 0, 3.28, 0, 3.80, 0.28, 0.40, "accent")
        prop_box(builder, placement, 0, 3.70, 0, 4.60, 0.22, 0.52, "accent")
        if detail:
            prop_box(builder, placement, 0, 3.02, 0, 0.70, 0.52, 0.18, "trim")
    elif kind == "stonelantern":
        prop_box(builder, placement, 0, 0.14, 0, 0.72, 0.28, 0.72, "wall_alt")
        prop_cylinder(builder, placement, 0, 0.64, 0, 0.20, 0.86, "wall", 8, 0.17)
        prop_box(builder, placement, 0, 1.17, 0, 0.74, 0.34, 0.74, "wall")
        prop_box(builder, placement, 0, 1.48, 0, 0.62, 0.40, 0.62, "emissive" if detail else "wall_alt")
        prop_cylinder(builder, placement, 0, 1.80, 0, 0.62, 0.22, "accent", 8, 0.10)
    elif kind == "well":
        prop_cylinder(builder, placement, 0, 0.46, 0, 1.02, 0.82, "wall", 14 if detail else 8, 1.02)
        prop_cylinder(builder, placement, 0, 0.70, 0, 0.76, 0.64, "wall_alt", 12 if detail else 8, 0.76)
        for lx in (-0.92, 0.92):
            prop_box(builder, placement, lx, 1.50, 0, 0.14, 2.14, 0.14, "trim")
        prop_beam(builder, placement, (-1.12, 2.54, 0), (1.12, 2.54, 0), 0.08, 0.08, "trim")
        if detail:
            prop_cylinder(builder, placement, 0, 1.55, 0, 0.13, 1.72, "accent", 8)
    elif kind == "pier":
        for lx in (-2.75, -0.92, 0.92, 2.75):
            for lz in (-0.88, 0.88):
                prop_box(builder, placement, lx, 0.34, lz, 0.18, 0.68, 0.18, "trim")
        planks = 12 if detail else 6
        for index in range(planks):
            lx = -2.75 + index * 5.5 / max(1, planks - 1)
            prop_box(builder, placement, lx, 0.70, 0, 5.8 / planks * 0.90, 0.14, 2.12, "accent")
        if detail:
            for lx in (-2.75, 2.75):
                for lz in (-1.04, 1.04):
                    prop_box(builder, placement, lx, 1.10, lz, 0.10, 0.86, 0.10, "trim")


def add_blender_prop(builder, placement, lod):
    kind = placement["kind"]
    if kind in {"conifer", "broadleaf", "deadtree", "sakura", "bamboo"}:
        add_tree_prop(builder, placement, kind, lod)
    elif kind == "rock":
        scale = placement.get("scaleJitter", 1.0)
        builder.add_rock(placement["cx"], 0, placement["cz"], 1.35 * scale, 1.58 * scale, "natural", 9 if lod == 0 else 6, int(abs(placement["cx"] * 17 + placement["cz"] * 29)))
    elif kind in {"truck", "derelictcar", "barricadecar", "tankhull"}:
        add_vehicle_prop(builder, placement, kind, lod)
    elif kind == "forklift":
        prop_box(builder, placement, 0, 0.62, 0, 1.65, 1.05, 2.15, "accent")
        prop_box(builder, placement, -0.34, 1.55, -0.72, 1.10, 1.25, 0.10, "trim")
        for lx in (-0.45, 0.45):
            prop_box(builder, placement, lx, 0.18, 1.45, 0.12, 0.18, 2.55, "trim")
        for lx in (-0.55, 0.55):
            prop_axle(builder, placement, lx, 0.40, 1.18, 0.34, "trim", 8)
    elif kind in {"concretebarrier", "fence", "bench", "vendingmachine", "pallet", "supplycrate", "drumgroup", "gasbottlegroup", "rubble"}:
        add_small_prop(builder, placement, kind, lod)
    else:
        add_structural_prop(builder, placement, kind, lod)


def add_kairou_blender_prop(builder, placement, lod):
    """Stage-aware visual remap for Kairou's legacy prop colliders.

    The TypeScript recipe historically names a torii and stone lanterns.  Their
    collider groups remain authoritative, but shipping recognisably Japanese
    meshes in the caravan city breaks the reference identity.  These variants
    stay inside the same footprint and preserve part counts independently of
    the runtime collision representation.
    """
    kind = placement["kind"]
    detail = lod == 0
    if kind == "torii":
        # Sandstone caravan gate with a shallow pointed crown.
        for lx in (-1.55, 1.55):
            prop_box(builder, placement, lx, 1.78, 0, 0.52, 3.56, 0.52, "wall_weathered")
            prop_box(builder, placement, lx, 3.70, 0, 0.76, 0.32, 0.68, "trim")
        prop_beam(builder, placement, (-1.55, 3.42, 0), (0, 4.34, 0), 0.18, 0.22, "wall_warm")
        prop_beam(builder, placement, (0, 4.34, 0), (1.55, 3.42, 0), 0.18, 0.22, "wall_warm")
        if detail:
            prop_box(builder, placement, 0, 3.76, 0.28, 0.72, 0.82, 0.055, "accent")
        return
    if kind == "stonelantern":
        # Low desert wayfinding plinth/brazier; no pagoda-like cap.
        prop_box(builder, placement, 0, 0.16, 0, 0.82, 0.32, 0.82, "wall_weathered")
        prop_box(builder, placement, 0, 0.62, 0, 0.48, 0.60, 0.48, "wall_warm")
        prop_cylinder(builder, placement, 0, 1.02, 0, 0.46, 0.20, "trim", 10 if detail else 7, 0.38)
        if detail:
            prop_cylinder(builder, placement, 0, 1.23, 0, 0.22, 0.32, "emissive", 8, 0.08)
        return
    if kind == "signboard":
        # Dark timber merchant sign with one restrained blue ceramic seal.
        for lx in (-1.02, 1.02):
            prop_box(builder, placement, lx, 1.62, 0, 0.12, 3.24, 0.12, "trim")
        prop_box(builder, placement, 0, 2.54, 0, 2.62, 1.12, 0.18, "wood")
        prop_box(builder, placement, 0, 2.54, 0.11, 0.48, 0.72, 0.24, "accent")
        if detail:
            for lx in (-0.78, 0.78):
                prop_box(builder, placement, lx, 2.54, 0.105, 0.08, 0.76, 0.035, "wall_warm")
        return
    if kind == "bench":
        prop_box(builder, placement, 0, 0.46, 0, 1.82, 0.16, 0.60, "wood")
        prop_box(builder, placement, 0, 0.96, -0.27, 1.82, 0.66, 0.12, "wood")
        for lx in (-0.68, 0.68):
            prop_box(builder, placement, lx, 0.24, 0, 0.12, 0.48, 0.48, "trim")
        return
    add_blender_prop(builder, placement, lod)


PROP_BOX_COUNTS = {
    "conifer": 2, "broadleaf": 2, "deadtree": 3, "sakura": 2, "bamboo": 3,
    "rock": 1, "towercrane": 3, "portalkrane": 3, "smokestack": 1,
    "gastank": 2, "watertower": 2, "transformer": 3, "antenna": 1,
    "truck": 2, "derelictcar": 1, "forklift": 2, "barricadecar": 2,
    "concretebarrier": 1, "fence": 1, "watchpost": 2, "tankhull": 2,
    "scaffold": 3, "streetlight": 2, "signboard": 2, "bench": 1,
    "vendingmachine": 1, "drumgroup": 3, "pallet": 1, "torii": 3,
    "stonelantern": 3, "well": 2, "pier": 3, "utilitypole": 2,
    "rubble": 2, "gasbottlegroup": 3, "supplycrate": 2,
}


def blender_prop_placements(stage):
    """Mirror planPropVisualsV2's breakable-instance exclusion exactly.

    A breakable runtime prop must retain its individually removable Three.js
    mesh.  Exporting a permanent Blender copy would leave a ghost visual after
    destruction, so only complete, non-breakable placement groups are baked.
    """
    prop_boxes = [box for box in stage["boxes"] if box.get("prop")]
    cursor = 0
    replacements = []
    for placement in stage.get("propPlacements", []):
        count = PROP_BOX_COUNTS[placement["kind"]]
        group = prop_boxes[cursor:cursor + count]
        cursor += count
        if len(group) == count and not any(box.get("breakable") for box in group):
            replacements.append(placement)
    if cursor != len(prop_boxes):
        raise RuntimeError(
            f"{stage['id']}: prop placement/box contract drift ({cursor} != {len(prop_boxes)})"
        )
    return replacements


def add_blender_props(builder, stage, lod):
    """Replace all authored runtime prop visuals while preserving collision."""
    for placement in blender_prop_placements(stage):
        # LOD2 keeps silhouettes and cover-sized props only.
        if lod == 2 and placement["kind"] in {
            "bench", "vendingmachine", "drumgroup", "pallet", "stonelantern",
            "gasbottlegroup", "supplycrate", "rubble",
        }:
            continue
        if stage["id"] == "kairou":
            add_kairou_blender_prop(builder, placement, lod)
        else:
            add_blender_prop(builder, placement, lod)


def add_souko_roof_monitor(builder, box, top, index, lod):
    """Seat one of three logistics monitors onto a real Souko roof slab."""
    width, depth = float(box["w"]), float(box["d"])
    long_x = width >= depth
    long_span, short_span = (width, depth) if long_x else (depth, width)

    def pbox(tangent, y, normal, tangent_span, height, normal_span, key):
        if long_x:
            builder.add_box(
                box["x"] + tangent, y, box["z"] + normal,
                tangent_span, height, normal_span, key,
            )
        else:
            builder.add_box(
                box["x"] + normal, y, box["z"] + tangent,
                normal_span, height, tangent_span, key,
            )

    # Authoritative slab top -> cap: 4cm overlap.  The cap remains the shared
    # contact surface for gutters, curb and the simplified far-LOD monitor.
    cap_height = 0.24
    cap_center = top + 0.08
    cap_top = cap_center + cap_height / 2
    builder.add_box(
        box["x"], cap_center, box["z"],
        width + 0.24, cap_height, depth + 0.24, "trim",
    )

    if lod != 2:
        for side in (-1, 1):
            pbox(
                0, top + 0.27, side * short_span / 2,
                long_span * 0.88, 0.18, 0.24,
                "accent" if side < 0 else "trim",
            )

    # Collision authoritatively keeps all twelve supported monitors at every
    # distance.  Keep the same twelve visual bodies in every LOD so a distant
    # player never encounters an invisible roof obstruction.
    monitor_limit = 12
    if index >= monitor_limit:
        return

    variant = index % 3
    if variant == 0:
        segments = [(0.0, long_span * 0.56, min(6.4, short_span * 0.30), 0.82, 0.42)]
    elif variant == 1:
        offset = min(1.8, long_span * 0.06) * (-1 if (index // 3) % 2 else 1)
        segments = [(offset, long_span * 0.48, min(5.6, short_span * 0.27), 1.05, 0.46)]
    else:
        segment_length = long_span * 0.20
        segment_width = min(4.8, short_span * 0.24)
        gap = max(1.6, long_span * 0.06)
        segment_offset = (segment_length + gap) / 2
        segments = [
            (-segment_offset, segment_length, segment_width, 0.72, 0.34),
            (segment_offset, segment_length, segment_width, 0.72, 0.34),
        ]

    if lod == 2:
        # LOD2 connection map (mirrors buildSoukoRoofMonitorColliders):
        #   support slab top <-> curb bottom: 0.04m overlap
        #   curb top <-> body bottom:         0.05m overlap
        #   body top <-> roof bottom:        0.06m overlap
        # Keep one union curb per support and one closed body/roof proxy per
        # segment.  Across twelve supports this is exactly 12 curbs, 16 bodies
        # and 16 roofs, so the far visual silhouette cannot hide live cover.
        curb_min = min(tangent - length / 2 for tangent, length, *_ in segments)
        curb_max = max(tangent + length / 2 for tangent, length, *_ in segments)
        visual_curb_bottom = cap_top - 0.04
        visual_curb_height = 0.30
        curb_bottom = top - 0.04
        curb_height = visual_curb_bottom + visual_curb_height - curb_bottom
        pbox(
            (curb_min + curb_max) / 2,
            curb_bottom + curb_height / 2,
            0,
            curb_max - curb_min,
            curb_height,
            max(segment_width for _, _, segment_width, *_ in segments),
            "wall_weathered",
        )

        body_bottom = visual_curb_bottom + visual_curb_height - 0.05
        for tangent, segment_length, segment_width, body_height, roof_rise in segments:
            body_top = body_bottom + body_height
            pbox(
                tangent,
                body_bottom + body_height / 2,
                0,
                segment_length,
                body_height,
                segment_width + 0.28,
                "wall_cool",
            )
            pbox(
                tangent,
                body_top - 0.06 + roof_rise / 2,
                0,
                segment_length + 0.50,
                roof_rise,
                segment_width + 0.60,
                "roof",
            )
        return

    for segment_index, (tangent, segment_length, segment_width, body_height, roof_rise) in enumerate(segments):
        curb_bottom = cap_top - 0.04
        curb_height = 0.30
        curb_center = curb_bottom + curb_height / 2
        for side in (-1, 1):
            pbox(
                tangent, curb_center, side * (segment_width / 2 - 0.11),
                segment_length, curb_height, 0.22, "wall_weathered",
            )
            pbox(
                tangent + side * (segment_length / 2 - 0.11), curb_center, 0,
                0.22, curb_height, segment_width, "wall_weathered",
            )

        curb_top = curb_bottom + curb_height
        body_bottom = curb_top - 0.05
        body_top = body_bottom + body_height
        # Solid end caps and a mid-value safety screen match the closed
        # authoritative body AABB.  The screen is visibly ballistic
        # louvre/polycarbonate—not transparent glass or a black card—so a
        # shot stopping here agrees with the runtime collision proxy.
        for end in (-1, 1):
            pbox(
                tangent + end * (segment_length / 2 - 0.11),
                body_bottom + body_height / 2,
                0,
                0.22, body_height, segment_width, "wall_warm",
            )
        for side in (-1, 1):
            side_normal = side * (segment_width / 2 - 0.09)
            pbox(
                tangent,
                body_bottom + body_height / 2,
                side_normal,
                segment_length - 0.30,
                max(0.22, body_height - 0.34),
                0.10,
                "wall_cool",
            )
            pbox(tangent, body_bottom + 0.13, side_normal, segment_length - 0.22, 0.26, 0.18, "wall_cool")
            pbox(tangent, body_top - 0.11, side_normal, segment_length - 0.22, 0.22, 0.18, "wall_cool")
            post_count = (5, 4, 3)[variant] if lod == 0 else 3
            for post in range(post_count):
                offset = (
                    post - (post_count - 1) / 2
                ) * (segment_length - 0.42) / max(1, post_count - 1)
                pbox(
                    tangent + offset,
                    body_bottom + body_height / 2,
                    side_normal,
                    0.16, body_height, 0.22, "wall_cool",
                )
            louver_count = (2, 3, 1)[variant] if lod == 0 else 1
            for louver in range(louver_count):
                louver_y = body_bottom + (louver + 1) * body_height / (louver_count + 1)
                pbox(
                    tangent, louver_y, side * (segment_width / 2 + 0.02),
                    segment_length - 0.32, 0.07, 0.24,
                    "accent" if side < 0 and louver == 0 and segment_index == 0 else "trim",
                )

        roof_base = body_top - 0.06
        roof_x = box["x"] + (tangent if long_x else 0)
        roof_z = box["z"] + (0 if long_x else tangent)
        builder.add_gable_roof(
            roof_x, roof_base, roof_z,
            segment_length + 0.50 if long_x else segment_width + 0.60,
            roof_rise,
            segment_width + 0.60 if long_x else segment_length + 0.50,
            "roof",
            "x" if long_x else "z",
        )


def add_playable_district_rooflines(builder, stage, lod):
    """Seat roof/facade identity onto authoritative playable buildings."""
    if lod == 2 and stage["id"] != "souko":
        return
    family = IDENTITIES[stage["id"]][0]
    profile = PROFILES[stage["id"]]
    landmarks = stage.get("landmarkPlacements", [])
    route_x = [float(item["cx"]) for item in landmarks] if len(landmarks) == 2 else [0.0]
    route_z = [float(item["cz"]) for item in landmarks] if len(landmarks) == 2 else [0.0]
    candidates = [
        box for box in stage["boxes"]
        if box.get("district")
        and not box.get("landmarkId")
        and not box.get("ghost")
        and not box.get("decor")
        and not box.get("legacyHorizon")
        and box["w"] >= 5.5
        and box["d"] >= 5.5
        and (
            box["h"] >= 4.8
            or (
                stage["id"] in {"kunren", "souko", "nakaniwa"}
                and 0.20 <= box["h"] <= (1.0 if stage["id"] == "kunren" else 0.70)
                and box["y"] >= (2.0 if stage["id"] == "kunren" else 4.0)
                and (
                    stage["id"] != "souko"
                    or box.get("roofMonitorSupport") is True
                )
            )
        )
    ]
    candidates = sorted(candidates, key=lambda box: box["w"] * box["d"] * box["h"], reverse=True)
    candidate_limit = 18 if lod == 0 else 12 if stage["id"] == "souko" else 10
    for index, box in enumerate(candidates[:candidate_limit]):
        top = box["y"] + box["h"] / 2
        width, depth = box["w"], box["d"]
        if (
            0.20 <= box["h"] <= 1.0
            and stage["id"] == "kunren"
            and box.get("roofBaffleSupport") is not True
        ):
            continue
        if (
            0.20 <= box["h"] <= 0.70
            and stage["id"] == "nakaniwa"
            and box.get("roofGableSupport") is not True
        ):
            continue
        if stage["id"] == "kairou":
            # Flat sandstone terrace and stepped parapet.  Kairou must never
            # inherit the heritage gable that read as a blue Japanese roof.
            builder.add_box(box["x"], top + 0.16, box["z"], width + 0.34, 0.32, depth + 0.34, "wall_warm")
            builder.add_box(box["x"], top + 0.46, box["z"], width + 0.66, 0.20, depth + 0.66, "trim")
        elif stage["id"] == "kunren":
            # Collision roof -> armored cap: 0.10 m vertical overlap.
            # The largest ordinary blocks then carry an asymmetric observation
            # baffle whose posts begin 0.12 m below the real roof and whose
            # crosshead overlaps both post tops by 0.28 m. This strengthens the
            # first-person military skyline without entering firing lanes.
            builder.add_box(
                box["x"], top + 0.10, box["z"],
                width + 0.26, 0.40, depth + 0.26, "wall_cool",
            )
            crown_limit = 6 if lod == 0 else 4
            if index < crown_limit:
                frame_span = min(8.2, max(5.4, width * 0.62))
                frame_depth = min(4.8, max(3.0, depth * 0.44))
                post_h = 4.20 + (index % 3) * 0.52
                nearest_x = min(route_x, key=lambda road: abs(box["x"] - road))
                nearest_z = min(route_z, key=lambda road: abs(box["z"] - road))
                frame_x = box["x"]
                frame_z = box["z"]
                if abs(box["x"] - nearest_x) <= abs(box["z"] - nearest_z):
                    frame_x += (1 if nearest_x >= box["x"] else -1) * width * 0.18
                else:
                    frame_z += (1 if nearest_z >= box["z"] else -1) * depth * 0.18
                # Four slender corner posts and two open crossheads replace
                # the former full-depth U-shaped solids.  The old volumes read
                # as tiny dark HVAC boxes from the ground; this open range-
                # baffle silhouette keeps sky visible through the structure.
                for side in (-1, 1):
                    for depth_side in (-1, 1):
                        builder.add_box(
                            frame_x + side * (frame_span / 2 - 0.18),
                            top - 0.12 + post_h / 2,
                            frame_z + depth_side * (frame_depth / 2 - 0.18),
                            0.36, post_h, 0.36, "trim",
                        )
                for depth_side in (-1, 1):
                    cross_z = frame_z + depth_side * (frame_depth / 2 - 0.18)
                    builder.add_box(
                        frame_x, top + post_h - 0.22, cross_z,
                        frame_span, 0.36, 0.36,
                        "accent" if depth_side < 0 else "trim",
                    )
                    for direction in (-1, 1):
                        builder.add_beam(
                            (
                                frame_x - direction * (frame_span / 2 - 0.34),
                                top + 0.18,
                                cross_z,
                            ),
                            (
                                frame_x + direction * (frame_span / 2 - 0.34),
                                top + post_h - 0.38,
                                cross_z,
                            ),
                            0.12 if lod == 0 else 0.15,
                            0.10,
                            "accent" if direction < 0 and depth_side < 0 else "wall_alt",
                        )
                if lod == 0:
                    mast_x = frame_x + (-1 if index % 2 else 1) * frame_span * 0.34
                    mast_z = frame_z - frame_depth * 0.30
                    builder.add_cylinder(
                        mast_x, top + post_h + 0.72, mast_z,
                        0.12, 1.80, "trim", 8, 0.08,
                    )
                    builder.add_cylinder(
                        mast_x, top + post_h + 1.68, mast_z,
                        0.24, 0.20, "accent", 8, 0.20,
                    )
        elif stage["id"] == "souko":
            add_souko_roof_monitor(builder, box, top, index, lod)
        elif stage["id"] == "nakaniwa":
            # Low garden-palace gables replace the flat brown roof cards on
            # actual roof slabs.  Only the largest slabs receive the ridge so
            # the district remains varied instead of becoming a tiled clone.
            builder.add_box(
                box["x"], top + 0.08, box["z"],
                width + 0.22, 0.24, depth + 0.22, "wood",
            )
            if index < (10 if lod == 0 else 6):
                long_x = width >= depth
                roof_h = 1.20 + (index % 3) * 0.30
                builder.add_gable_roof(
                    box["x"], top + 0.06, box["z"],
                    width + 0.34, roof_h, depth + 0.34,
                    "roof", "x" if long_x else "z",
                )
                if long_x:
                    builder.add_box(
                        box["x"], top + 0.22, box["z"] - depth / 2,
                        width + 0.70, 0.16, 0.30, "accent",
                    )
                else:
                    builder.add_box(
                        box["x"] - width / 2, top + 0.22, box["z"],
                        0.30, 0.16, depth + 0.70, "accent",
                    )
        elif family in {"heritage", "wilderness"} and profile["dressing"] not in {"armored-outpost", "cliff-fortress"}:
            builder.add_gable_roof(box["x"], top - 0.06, box["z"], width + 0.34, max(0.85, min(2.3, width * 0.12)), depth + 0.44, "roof", "x")
        elif family in {"industrial", "airport", "military", "geothermal", "arctic"}:
            # Saw-tooth / service roof with seated parapet and vents.
            builder.add_box(box["x"], top + 0.08, box["z"], width + 0.18, 0.22, depth + 0.18, "trim")
            if lod == 0 and index % 2 == 0:
                vent_count = max(1, min(4, int(width // 7)))
                for vent in range(vent_count):
                    vx = box["x"] + (vent - (vent_count - 1) / 2) * width * 0.68 / max(1, vent_count - 1)
                    builder.add_cylinder(vx, top + 0.62, box["z"], 0.32, 1.12, "wall_alt", 8, 0.24)
        else:
            builder.add_box(box["x"], top + 0.22, box["z"], width + 0.20, 0.44, depth + 0.20, "wall_alt")
            if lod == 0:
                builder.add_box(box["x"], top + 0.72, box["z"], min(4.5, width * 0.38), 1.0, min(3.2, depth * 0.38), "trim")

        if lod != 0:
            continue
        # Representative first-person silhouettes use stage-owned roof
        # grammar rather than relying on palette alone.  All pieces are seated
        # on an existing structural top and remain small enough to read as
        # roof/crown treatment, never as a promised new traversal volume.
        stage_id = stage["id"]
        if stage_id == "kairou" and index % 2 == 0:
            tower_h = 2.8 + (index % 3) * 0.55
            builder.add_box(box["x"], top + tower_h / 2, box["z"], min(2.8, width * 0.24), tower_h, min(2.5, depth * 0.24), "wall_warm")
            for side in (-1, 1):
                builder.add_box(box["x"] + side * min(0.82, width * 0.08), top + tower_h * 0.70, box["z"] - min(1.28, depth * 0.13), 0.18, tower_h * 0.28, 0.12, "wood")
        elif stage_id in {"chikurin", "takadai"} and index % 2 == 0:
            eave_w = min(width + 0.9, 12.0)
            eave_d = min(depth + 1.0, 10.0)
            builder.add_gable_roof(box["x"], top + 0.18, box["z"], eave_w, 1.45 if stage_id == "takadai" else 0.82, eave_d, "roof", "x")
            builder.add_box(box["x"], top + 0.22, box["z"], eave_w + 0.6, 0.16, eave_d + 0.6, "accent")
        elif stage_id == "setsugen" and index % 3 == 0:
            radius = min(2.2, max(1.15, min(width, depth) * 0.12))
            builder.add_cylinder(box["x"], top + radius * 0.42, box["z"], radius, radius * 0.84, "glass", 12, radius * 0.34)
            for axis in (-1, 1):
                builder.add_beam((box["x"] - radius, top + radius * 0.45, box["z"] + axis * radius * 0.35), (box["x"] + radius, top + radius * 0.45, box["z"] + axis * radius * 0.35), 0.08, 0.07, "trim")
        elif stage_id == "kouwan" and index % 2 == 0:
            span = min(8.0, width * 0.66)
            for side in (-1, 1):
                builder.add_box(box["x"] + side * span / 2, top + 1.35, box["z"], 0.20, 2.70, min(2.8, depth * 0.32), "trim")
            builder.add_beam((box["x"] - span / 2, top + 2.62, box["z"]), (box["x"] + span / 2, top + 2.62, box["z"]), 0.18, 0.16, "accent")
        elif stage_id == "sakyuu" and index % 2 == 0:
            fin_span = min(7.5, width * 0.64)
            for fin in (-1, 0, 1):
                fin_x = box["x"] + fin * fin_span * 0.34
                builder.add_beam((fin_x - 0.65, top + 0.22, box["z"] - depth * 0.18), (fin_x + 0.65, top + 2.18, box["z"] + depth * 0.18), 0.12, 0.10, "accent")
        elif stage_id == "z04" and index % 2 == 0:
            for side in (-1, 1):
                pinnacle_h = 2.8 + ((index + side) % 3) * 0.7
                builder.add_cylinder(box["x"] + side * width * 0.31, top + pinnacle_h / 2, box["z"], 0.52, pinnacle_h, "wall_alt", 8, 0.08)


def add_playable_district_facades(builder, stage, lod):
    """Give collision buildings a four-sided, construction-readable facade.

    Earlier passes laid one uninterrupted glass strip across each storey.  At
    first-person distance that read as a coloured box and also covered the
    smaller window pass.  This version authors individual recessed bays,
    reveals, lintels, sills, floor belts, pilasters, service doors and a small
    family-specific detail layer.  Every protrusion is <=45cm and seated on a
    solid authoritative BoxSpec, so it cannot advertise a playable opening or
    become collider-free cover.
    """
    if lod == 2 or stage["id"] == "kairou":
        # Kairou uses the reference-specific warm-stone arcade pass below.
        # The generic glass/shutter grammar produced thin blue/black cards on
        # top of that pass and must not be layered into this stage.
        return
    family = IDENTITIES[stage["id"]][0]
    mood = stage["palette"].get("mood")
    profile = PROFILES[stage["id"]]
    facade_language = profile["cityProfile"]["facadeLanguage"]
    # All 31 facade-language strings are different.  Fold the phrase into a
    # stable signature so bay width, rhythm and accent placement remain stage-
    # specific even when two maps share a broad material family.
    signature = sum((index + 1) * ord(char) for index, char in enumerate(facade_language)) % 7
    ruined = family in {"undead", "geothermal"}
    heritage = family in {"heritage", "wilderness"}
    industrial = family in {"industrial", "military", "airport"}
    candidates = [
        box for box in stage["boxes"]
        if box.get("district")
        and not box.get("landmarkId")
        and not box.get("ghost")
        and not box.get("decor")
        and not box.get("legacyHorizon")
        and box["h"] >= 4.2
        and box["w"] * box["d"] >= 30
        and (
            min(box["w"], box["d"]) > 1.25
            or stage["id"] in {"kunren", "souko", "nakaniwa"}
        )
    ]
    candidates = sorted(candidates, key=lambda box: box["w"] * box["d"] * box["h"], reverse=True)
    # Only the largest 8-12 collision buildings receive detailed glazing. The
    # previous 26 x four-face pass was structurally valid but still generated
    # an unavoidable spreadsheet of repeated panes across the whole stage.
    candidate_limit = 8 + (signature % 5) if lod == 0 else 6 + (signature % 3)
    landmarks = stage.get("landmarkPlacements", [])
    route_x = [float(item["cx"]) for item in landmarks] if len(landmarks) == 2 else [0.0]
    route_z = [float(item["cz"]) for item in landmarks] if len(landmarks) == 2 else [0.0]
    for index, box in enumerate(candidates[:candidate_limit]):
        base = box["y"] - box["h"] / 2
        levels = max(1, min(3 if lod == 0 else 2, int(box["h"] // (4.75 + signature * 0.06))))
        bays_x = max(2, min(4 if lod == 0 else 3, int(box["w"] // (5.0 + (signature % 3) * 0.48))))
        bays_z = max(2, min(4 if lod == 0 else 3, int(box["d"] // (5.0 + ((signature + 1) % 3) * 0.48))))
        pane_budget = min(12, 8 + (index + signature) % 5) if lod == 0 else 4
        pane_count = 0

        def souko_loading_face(axis, side, span):
            """Author one collision-seated logistics elevation, without glass."""
            wall_plane = box["d"] / 2 if axis == "x" else box["w"] / 2
            bay_count = max(2, min(4, int(round(span / 13.0)))) if lod == 0 else 2
            bay_pitch = span / bay_count
            door_h = min(5.4, box["h"] * 0.64)
            door_y = base + door_h / 2 + 0.12

            def face_box(tangent, panel_y, panel_w, panel_h, depth_center, depth, key):
                if axis == "x":
                    builder.add_box(
                        box["x"] + tangent,
                        panel_y,
                        box["z"] + side * (wall_plane + depth_center),
                        panel_w, panel_h, depth, key,
                    )
                else:
                    builder.add_box(
                        box["x"] + side * (wall_plane + depth_center),
                        panel_y,
                        box["z"] + tangent,
                        depth, panel_h, panel_w, key,
                    )

            for bay in range(bay_count):
                offset = (bay - (bay_count - 1) / 2) * bay_pitch
                door_w = min(9.6, bay_pitch * 0.68)
                marker_key = "accent" if (index + bay) % 3 == 0 else "trim"
                # Four mid-value sectional slabs replace the former near-black
                # single backing card.  Each slab intersects the authoritative
                # wall by 3cm and the portal frame by another 8cm.
                section_count = 4 if lod == 0 else 2
                section_gap = 0.08
                section_height = (door_h - section_gap * (section_count - 1)) / section_count
                for section in range(section_count):
                    section_y = (
                        base + 0.12 + section_height / 2
                        + section * (section_height + section_gap)
                    )
                    face_box(
                        offset, section_y, door_w, section_height,
                        0.04, 0.14,
                        "wall_warm" if (section + bay + index) % 3 == 0 else "wall_weathered",
                    )
                jamb = 0.30
                face_box(offset - door_w / 2 - jamb / 2, door_y, jamb, door_h + jamb, 0.12, 0.30, marker_key)
                face_box(offset + door_w / 2 + jamb / 2, door_y, jamb, door_h + jamb, 0.12, 0.30, "trim")
                face_box(offset, door_y + door_h / 2 + jamb / 2, door_w, jamb, 0.12, 0.30, marker_key)
                # A shallow rain canopy and number blade make the loading bay
                # legible at FPS distance without creating walkable geometry.
                face_box(
                    offset,
                    door_y + door_h / 2 + 0.34,
                    door_w + 0.54,
                    0.20,
                    0.20,
                    0.46,
                    "accent" if (index + bay) % 2 == 0 else "trim",
                )
                face_box(
                    offset + door_w * (0.34 if bay % 2 else -0.34),
                    door_y + door_h * 0.20,
                    0.18,
                    min(1.10, door_h * 0.24),
                    0.13,
                    0.20,
                    "accent",
                )
                for rail in range(1, section_count):
                    rail_y = base + 0.12 + rail * section_height + (rail - 0.5) * section_gap
                    face_box(offset, rail_y, door_w * 0.92, 0.08, 0.14, 0.14, "trim")
                if lod == 0:
                    for bumper_side in (-1, 1):
                        face_box(
                            offset + bumper_side * door_w * 0.39,
                            base + 0.36,
                            0.30,
                            0.72,
                            0.11,
                            0.28,
                            "obstacle",
                        )

            rack_base = base + door_h + 0.56
            rack_top = base + box["h"] - 0.48
            if rack_top > rack_base + 0.8:
                for edge in range(bay_count + 1):
                    offset = (edge - bay_count / 2) * bay_pitch
                    face_box(offset, (rack_base + rack_top) / 2, 0.14, rack_top - rack_base, 0.09, 0.18, "trim")
                shelf_count = 2 if lod == 0 else 1
                for shelf in range(shelf_count):
                    shelf_y = rack_base + (shelf + 1) * (rack_top - rack_base) / (shelf_count + 1)
                    for bay in range(bay_count):
                        offset = (bay - (bay_count - 1) / 2) * bay_pitch
                        face_box(
                            offset,
                            shelf_y,
                            bay_pitch * 0.68,
                            0.14,
                            0.09,
                            0.18,
                            "accent" if shelf == 0 and (index + bay) % 3 == 0 else "trim",
                        )
                face_box(
                    -span * 0.24 if index % 2 else span * 0.24,
                    rack_top - 0.18,
                    min(span * 0.28, 3.8),
                    0.32,
                    0.12,
                    0.20,
                    "accent",
                )

        def strip_service_face(axis, side, span):
            """Add a quiet, sealed reverse elevation to a thin wall strip."""
            wall_plane = box["d"] / 2 if axis == "x" else box["w"] / 2
            panel_count = 2 if lod == 0 else 1
            panel_w = min(4.6, span * 0.24)
            panel_h = min(3.4, box["h"] * 0.38)
            panel_y = base + min(3.2, box["h"] * 0.40)
            panel_key = "wall_weathered" if stage["id"] == "nakaniwa" else "wall_alt"
            frame_key = "wood" if stage["id"] == "nakaniwa" else "trim"

            def service_box(tangent, y, width, height, depth_center, depth, key):
                if axis == "x":
                    builder.add_box(
                        box["x"] + tangent, y,
                        box["z"] + side * (wall_plane + depth_center),
                        width, height, depth, key,
                    )
                else:
                    builder.add_box(
                        box["x"] + side * (wall_plane + depth_center), y,
                        box["z"] + tangent,
                        depth, height, width, key,
                    )

            for panel in range(panel_count):
                offset = (panel - (panel_count - 1) / 2) * span * 0.38
                service_box(offset, panel_y, panel_w, panel_h, 0.032, 0.064, panel_key)
                for edge in (-1, 1):
                    service_box(
                        offset + edge * (panel_w / 2 + 0.08),
                        panel_y,
                        0.16,
                        panel_h + 0.28,
                        0.075,
                        0.15,
                        frame_key,
                    )
                service_box(
                    offset,
                    panel_y + panel_h / 2 + 0.08,
                    panel_w,
                    0.16,
                    0.075,
                    0.15,
                    "accent" if panel == 0 else frame_key,
                )
                if stage["id"] == "kunren":
                    service_box(
                        offset,
                        panel_y + panel_h * 0.18,
                        panel_w * 0.66,
                        0.16,
                        0.09,
                        0.18,
                        "accent",
                    )

        def facade_face(axis, side, span, bays, face_index):
            nonlocal pane_count
            wall_plane = box["d"] / 2 if axis == "x" else box["w"] / 2
            bay_pitch = span / bays
            storey_pitch = box["h"] / levels
            for level in range(levels):
                y = base + (level + 0.56) * storey_pitch
                for bay in range(bays):
                    grammar = (bay * 7 + level * 5 + index * 3 + signature + face_index * 4) % 10
                    offset = (bay - (bays - 1) / 2) * bay_pitch
                    size_jitter = 0.90 + ((bay * 3 + level * 2 + index + signature) % 5) * 0.035
                    pane_w = max(0.72, min(1.54 if not heritage else 1.24, bay_pitch * 0.48)) * size_jitter
                    pane_h = max(0.72, min(1.62 if heritage else 1.38, storey_pitch * 0.36)) * (1.06 - (grammar % 3) * 0.035)
                    glass_codes = {0, 1, 2} if family in {"urban", "airport"} and not ruined else {0, 1}
                    is_glass = grammar in glass_codes and pane_count < pane_budget
                    is_shutter = grammar in {3, 4, 5}
                    is_balcony = grammar == 6 and lod == 0
                    is_arcade = grammar == 7 and lod == 0 and level == 0

                    def add_face_box(tangent_offset, panel_y, panel_w, panel_h, depth_center, depth, key):
                        if axis == "x":
                            builder.add_box(
                                box["x"] + tangent_offset,
                                panel_y,
                                box["z"] + side * (wall_plane + depth_center),
                                panel_w, panel_h, depth, key,
                            )
                        else:
                            builder.add_box(
                                box["x"] + side * (wall_plane + depth_center),
                                panel_y,
                                box["z"] + tangent_offset,
                                depth, panel_h, panel_w, key,
                            )

                    if is_glass:
                        # Four separate frame strips, never a coplanar backing
                        # card. The glass front is 14.7cm behind the frame front
                        # and clears the wall plane by 1.3cm at its nearest face.
                        frame_depth = 0.20
                        frame_center = 0.10
                        glass_depth = 0.026
                        glass_center = 0.026
                        jamb = 0.14
                        add_face_box(offset - pane_w / 2 - jamb / 2, y, jamb, pane_h + jamb * 2, frame_center, frame_depth, "trim")
                        add_face_box(offset + pane_w / 2 + jamb / 2, y, jamb, pane_h + jamb * 2, frame_center, frame_depth, "trim")
                        add_face_box(offset, y - pane_h / 2 - jamb / 2, pane_w, jamb, frame_center, frame_depth, "trim")
                        add_face_box(offset, y + pane_h / 2 + jamb / 2, pane_w, jamb, frame_center, frame_depth, "trim")
                        glass_key = (
                            "emissive"
                            if mood == "night" and (bay + level * 2 + index + signature) % 9 == 0
                            else "glass"
                        )
                        add_face_box(offset, y, pane_w, pane_h, glass_center, glass_depth, glass_key)
                        builder.record_facade_glass(
                            pane_w,
                            pane_h,
                            glass_center - glass_depth / 2,
                            frame_center + frame_depth / 2 - (glass_center + glass_depth / 2),
                        )
                        pane_count += 1
                    elif is_shutter:
                        # Closed shutters/louvres are deliberately non-glass;
                        # together with blind bays they form 50-70% of slots.
                        panel_key = "wall_alt" if ruined or industrial else "accent"
                        add_face_box(offset, y, pane_w * 1.06, pane_h * 1.02, 0.030, 0.055, panel_key)
                        slat_count = 3 if lod == 0 else 2
                        for slat in range(slat_count):
                            slat_y = y + (slat - (slat_count - 1) / 2) * pane_h * 0.27
                            add_face_box(offset, slat_y, pane_w * 0.86, 0.055, 0.066, 0.040, "trim")
                    elif is_balcony:
                        add_face_box(offset, y - pane_h * 0.48, pane_w * 1.46, 0.14, 0.36, 0.72, "accent" if heritage else "trim")
                        add_face_box(offset, y, pane_w * 0.72, pane_h * 0.86, 0.030, 0.055, "wall_alt")
                    elif is_arcade:
                        add_face_box(offset - pane_w * 0.46, y, 0.14, pane_h * 1.26, 0.070, 0.14, "trim")
                        add_face_box(offset + pane_w * 0.46, y, 0.14, pane_h * 1.26, 0.070, 0.14, "trim")
                        add_face_box(offset, y + pane_h * 0.58, pane_w, 0.18, 0.070, 0.14, "accent")

                # A seated floor slab both breaks the large wall and supplies
                # scale when individual panes alias at distance.
                if lod == 0 and level < levels - 1 and (level + signature) % 2 == 0:
                    belt_y = base + (level + 1) * storey_pitch
                    if axis == "x":
                        builder.add_box(box["x"], belt_y, box["z"] + side * (wall_plane + 0.07), span * 0.78, 0.12, 0.14, "accent" if heritage and (level + signature) % 3 == 0 else "trim")
                    else:
                        builder.add_box(box["x"] + side * (wall_plane + 0.07), belt_y, box["z"], 0.14, 0.12, span * 0.78, "accent" if heritage and (level + signature) % 3 == 0 else "trim")

            if lod != 0:
                return
            # Only two structural edges remain: the former centre rib on every
            # facade reinforced the rejected window-grid rhythm.
            structural_edges = (0, bays)
            for edge in structural_edges:
                offset = (edge - bays / 2) * bay_pitch
                if axis == "x":
                    builder.add_box(box["x"] + offset, box["y"], box["z"] + side * (wall_plane + 0.07), 0.11, box["h"] * 0.82, 0.14, "trim")
                else:
                    builder.add_box(box["x"] + side * (wall_plane + 0.07), box["y"], box["z"] + offset, 0.14, box["h"] * 0.82, 0.11, "trim")

        # Route-facing primary facade, plus a perpendicular secondary facade
        # on one third of buildings. Back/service elevations stay deliberately
        # blind instead of receiving the same four-sided window kit.
        face_candidates = []
        for road in route_x:
            face_candidates.append((abs(box["x"] - road), "z", 1 if road >= box["x"] else -1, box["d"], bays_z))
        for road in route_z:
            face_candidates.append((abs(box["z"] - road), "x", 1 if road >= box["z"] else -1, box["w"], bays_x))
        face_candidates.sort(key=lambda item: item[0])
        wall_strip = min(box["w"], box["d"]) <= 1.25 and max(box["w"], box["d"]) >= 8.0
        if wall_strip:
            # Canonical enterable buildings are four 1m wall strips plus a
            # real roof.  Distance-only sorting selected the short end face on
            # Kunren 8/10 and Nakaniwa 4/6 candidates as well as on Souko.
            # Filter to the physically real long elevation before choosing a
            # route-readable side.
            long_faces = [item for item in face_candidates if item[3] >= 4.0]
            if long_faces:
                face_candidates = long_faces
        selected_faces = [face_candidates[0]]
        if wall_strip:
            # Canonical warehouses/bunkers are authored as four long wall
            # strips plus a real roof slab.  Dressing only the route-facing
            # side left most eye-height cameras looking at an untouched blank
            # elevation, so mirror the same collision-seated grammar onto the
            # opposite long face.  Both faces still overlap the real wall.
            distance, axis, side, span, bays = selected_faces[0]
            selected_faces.append((distance, axis, -side, span, bays))
        elif lod == 0 and index % 3 == 0:
            secondary = next((item for item in face_candidates[1:] if item[1] != selected_faces[0][1]), None)
            if secondary is not None:
                selected_faces.append(secondary)
        for face_index, (_, axis, side, span, bays) in enumerate(selected_faces):
            if (
                stage["id"] == "souko"
                and face_index == 0
                and (
                    box.get("district") == "terminal"
                    or (
                        box.get("district") == "hangar"
                        and math.hypot(float(box["x"]), float(box["z"])) < 80.0
                    )
                )
            ):
                souko_loading_face(axis, side, span)
            elif wall_strip and face_index == 1:
                strip_service_face(axis, side, span)
            else:
                facade_face(axis, side, span, bays, face_index)

        if lod == 0:
            # Corners get a slightly heavier structural quoin than the bay
            # pilasters, keeping silhouettes connected from every angle.
            for sx in (-1, 1):
                for sz in (-1, 1):
                    builder.add_box(
                        box["x"] + sx * box["w"] / 2,
                        box["y"],
                        box["z"] + sz * box["d"] / 2,
                        0.16,
                        box["h"] * 0.92,
                        0.16,
                        "trim",
                    )

            if wall_strip:
                # The two long faces already own collision-seated facade kits.
                # The generic door below assumes a broad X-facing volume and
                # would protrude beyond the short end of a 1m wall strip.
                continue

            # Ground-floor service grammar: a clearly closed double door with
            # transom and a shallow canopy on one deterministic face.
            door_side = -1 if (index + signature) % 2 else 1
            door_w = min(3.2, max(1.8, box["w"] * 0.22))
            door_z = box["z"] + door_side * (box["d"] / 2 + 0.112)
            builder.add_box(box["x"], base + 1.42, door_z, door_w + 0.38, 2.72, 0.12, "trim")
            for leaf in (-1, 1):
                builder.add_box(box["x"] + leaf * door_w * 0.245, base + 1.32, door_z + door_side * 0.068, door_w * 0.43, 2.32, 0.052, "wall_alt")
            builder.add_box(box["x"], base + 2.72, door_z + door_side * 0.072, door_w * 0.90, 0.28, 0.048, "accent")
            builder.add_box(box["x"], base + 3.02, door_z + door_side * 0.14, door_w + 0.92, 0.15, 0.30, "accent" if (signature + index) % 3 == 0 else "trim")

            # One readable use-specific cluster, not a universal house kit.
            if heritage or family == "urban":
                balcony_y = base + min(box["h"] - 1.0, 4.25 + (index % 2) * 1.05)
                balcony_w = min(box["w"] * 0.46, 6.8)
                balcony_z = box["z"] - box["d"] / 2 - 0.20
                builder.add_box(box["x"] + (signature % 3 - 1) * box["w"] * 0.12, balcony_y, balcony_z, balcony_w, 0.14, 0.32, "accent" if heritage else "trim")
                for rail in range(-2, 3):
                    builder.add_box(box["x"] + rail * balcony_w * 0.24, balcony_y + 0.46, balcony_z - 0.15, 0.06, 0.86, 0.06, "trim")
                builder.add_box(box["x"], balcony_y + 0.88, balcony_z - 0.15, balcony_w, 0.06, 0.06, "trim")
            elif industrial:
                # Vents, conduit and a small wall-mounted plant cluster give
                # industrial blocks a functional rather than residential read.
                plant_y = base + min(box["h"] - 1.0, 4.4 + (index % 3) * 1.25)
                plant_x = box["x"] + (-1 if index % 2 else 1) * box["w"] * 0.28
                plant_z = box["z"] - box["d"] / 2 - 0.18
                builder.add_box(plant_x, plant_y, plant_z, 1.32, 0.86, 0.32, "wall_alt")
                for slat in range(4):
                    builder.add_box(plant_x, plant_y - 0.24 + slat * 0.16, plant_z - 0.18, 1.0, 0.045, 0.045, "trim")
                builder.add_cylinder(plant_x + 0.82, base + box["h"] * 0.48, plant_z, 0.10, box["h"] * 0.72, "trim", 8, 0.10)
            elif ruined:
                # Real geometry damage cue; it remains a sealed wall because
                # the dark plate sits over the authoritative shell.
                scar_x = box["x"] + (-1 if index % 2 else 1) * box["w"] * 0.22
                scar_z = box["z"] - box["d"] / 2 - 0.17
                builder.add_box(scar_x, base + box["h"] * 0.52, scar_z, min(2.8, box["w"] * 0.24), min(5.6, box["h"] * 0.46), 0.20, "wall_alt")
                for brace in (-1, 1):
                    start = (scar_x - brace * min(1.2, box["w"] * 0.10), base + box["h"] * 0.30, scar_z - 0.12)
                    end = (scar_x + brace * min(1.2, box["w"] * 0.10), base + box["h"] * 0.72, scar_z - 0.12)
                    builder.add_beam(start, end, 0.09, 0.08, "trim")


def add_kairou_reference_city_tier2(builder, stage, lod):
    """Reference-specific sandstone boulevard and four-metre facade kit.

    This pass only decorates collision-backed district walls.  Shallow panels,
    pilasters, lintels, cornices and cloth remain attached to those walls; the
    only ground additions are 18 mm paving skins over the existing floor.  No
    collisionless prop, doorway, or cover mass is placed in a combat lane.
    """
    if stage["id"] != "kairou" or lod == 2:
        return

    # The collision plan now contributes one fully supported second-storey
    # volume to every ordinary district.  Treat those eleven masses as actual
    # merchant houses rather than leaving them as undecorated collider boxes.
    # Every addition below is shallow relief, a roof-edge parapet or a small
    # crown seated on the real structural volume; the gameplay footprint and
    # street clearance remain TypeScript-authoritative.
    urban_volumes = [
        box for box in stage["boxes"]
        if box.get("urbanVolume") and not box.get("ghost")
    ]
    urban_volumes.sort(key=lambda box: (box["z"], box["x"]))
    for volume_index, volume in enumerate(urban_volumes):
        x, z = volume["x"], volume["z"]
        width, depth, height = volume["w"], volume["d"], volume["h"]
        base = volume["y"] - height / 2
        top = volume["y"] + height / 2

        # Projecting bed/string courses and four masonry quoins give the
        # storey contact, construction scale and sun-catching edge response.
        for band_y, band_h, extension in (
            (base + 0.18, 0.28, 0.34),
            (top - 0.24, 0.34, 0.46),
        ):
            builder.add_box(
                x, band_y, z,
                width + extension, band_h, depth + extension,
                "trim" if band_y < volume["y"] else "wall_weathered",
            )
        if lod == 0:
            for sx in (-1, 1):
                for sz in (-1, 1):
                    builder.add_box(
                        x + sx * width / 2,
                        volume["y"],
                        z + sz * depth / 2,
                        0.34,
                        height * 0.88,
                        0.34,
                        "wall_weathered",
                    )

        # Address the nearest authored boulevard.  A blind pointed panel is
        # stone relief, never glass or a dark backing card.  Sparse open timber
        # bars suggest mashrabiya ventilation while the warm collider remains
        # plainly visible between them.
        distance_to_ns_boulevard = abs(x - 2.0)
        distance_to_ew_boulevard = abs(z - 46.0)
        faces_x = distance_to_ew_boulevard <= distance_to_ns_boulevard
        if faces_x:
            side = 1 if 46.0 >= z else -1
        else:
            side = 1 if 2.0 >= x else -1
        span = width if faces_x else depth
        face_plane = (z + side * depth / 2) if faces_x else (x + side * width / 2)
        bay_count = max(1, min(4 if lod == 0 else 2, int(span // 4.4)))
        bay_span = span * 0.72
        panel_w = min(2.2, bay_span / max(1, bay_count) * 0.64)
        panel_h = min(3.0, height * 0.48)
        panel_y = base + height * 0.50
        for bay in range(bay_count):
            tangent = (bay - (bay_count - 1) / 2) * bay_span / max(1, bay_count - 1)
            if faces_x:
                panel_x, panel_z = x + tangent, face_plane + side * 0.034
                builder.add_box(
                    panel_x, panel_y, panel_z,
                    panel_w, panel_h, 0.068, "wall_weathered",
                )
                for edge in (-1, 1):
                    builder.add_box(
                        panel_x + edge * (panel_w / 2 + 0.09), panel_y,
                        panel_z + side * 0.045,
                        0.18, panel_h + 0.34, 0.14, "trim",
                    )
                left = (panel_x - panel_w / 2, panel_y + panel_h / 2, panel_z + side * 0.06)
                apex = (panel_x, panel_y + panel_h / 2 + 0.62, panel_z + side * 0.06)
                right = (panel_x + panel_w / 2, panel_y + panel_h / 2, panel_z + side * 0.06)
                if lod == 0 and (bay + volume_index) % 2 == 0:
                    for bar in (-1, 0, 1):
                        builder.add_box(
                            panel_x + bar * panel_w * 0.24, panel_y,
                            panel_z + side * 0.095,
                            0.055, panel_h * 0.72, 0.055, "wood",
                        )
            else:
                panel_x, panel_z = face_plane + side * 0.034, z + tangent
                builder.add_box(
                    panel_x, panel_y, panel_z,
                    0.068, panel_h, panel_w, "wall_weathered",
                )
                for edge in (-1, 1):
                    builder.add_box(
                        panel_x + side * 0.045, panel_y,
                        panel_z + edge * (panel_w / 2 + 0.09),
                        0.14, panel_h + 0.34, 0.18, "trim",
                    )
                left = (panel_x + side * 0.06, panel_y + panel_h / 2, panel_z - panel_w / 2)
                apex = (panel_x + side * 0.06, panel_y + panel_h / 2 + 0.62, panel_z)
                right = (panel_x + side * 0.06, panel_y + panel_h / 2, panel_z + panel_w / 2)
                if lod == 0 and (bay + volume_index) % 2 == 0:
                    for bar in (-1, 0, 1):
                        builder.add_box(
                            panel_x + side * 0.095, panel_y,
                            panel_z + bar * panel_w * 0.24,
                            0.055, panel_h * 0.72, 0.055, "wood",
                        )
            builder.add_beam(left, apex, 0.075, 0.065, "trim")
            builder.add_beam(apex, right, 0.075, 0.065, "trim")

        # Roof terrace with a stage-specific windcatcher on the broader
        # houses.  The narrow fortress-tower volumes retain only the parapet,
        # which avoids an implausible crown wider than its support.
        parapet_h = 0.78
        parapet_t = 0.30
        builder.add_box(x, top + parapet_h / 2, z - depth / 2, width + 0.46, parapet_h, parapet_t, "wall_weathered")
        builder.add_box(x, top + parapet_h / 2, z + depth / 2, width + 0.46, parapet_h, parapet_t, "wall_weathered")
        builder.add_box(x - width / 2, top + parapet_h / 2, z, parapet_t, parapet_h, depth, "wall_weathered")
        builder.add_box(x + width / 2, top + parapet_h / 2, z, parapet_t, parapet_h, depth, "wall_weathered")
        if lod == 0 and min(width, depth) >= 8.0 and volume_index % 2 == 0:
            catcher_w = min(3.2, width * 0.24)
            catcher_d = min(3.0, depth * 0.24)
            catcher_h = 2.8 + (volume_index % 3) * 0.45
            catcher_x = x + (-1 if volume_index % 4 else 1) * width * 0.19
            catcher_z = z - depth * 0.10
            builder.add_box(
                catcher_x, top + catcher_h / 2, catcher_z,
                catcher_w, catcher_h, catcher_d, "wall_warm",
            )
            builder.add_box(
                catcher_x, top + catcher_h + 0.14, catcher_z,
                catcher_w + 0.34, 0.28, catcher_d + 0.34, "trim",
            )
            for shaft in (-1, 1):
                builder.add_box(
                    catcher_x + shaft * catcher_w * 0.24,
                    top + catcher_h * 0.68,
                    catcher_z - catcher_d / 2 - 0.04,
                    0.10, catcher_h * 0.36, 0.08, "wood",
                )

    # A dedicated two-depth bazaar closes the northward boulevard with actual
    # 3D architecture.  It is deliberately outside the authoritative play
    # boundary, behind terrain/retaining structure, so it cannot advertise a
    # traversable route or replace collision.  Unlike the former raster/circle
    # horizon shortcut, every silhouette has depth, parallax and a real roof.
    half = stage["size"] / 2
    horizon_count = 9 if lod == 0 else 6
    for horizon_index in range(horizon_count):
        lane = horizon_index % 2
        slot = horizon_index // 2
        lane_count = (horizon_count + (1 - lane)) // 2
        x = (
            (slot - (lane_count - 1) / 2) * (22.0 if lane == 0 else 25.0)
            + (8.5 if lane else -2.0)
        )
        depth = 13.0 + (horizon_index % 3) * 1.8
        width = 16.0 + ((horizon_index * 5) % 4) * 1.7
        storeys = 3 + (horizon_index * 3 + lane) % 4
        height = storeys * 4.4
        z = half + 6.0 + lane * 27.0 + depth / 2
        lower_h = height * 0.68
        builder.add_box(
            x, lower_h / 2, z,
            width, lower_h, depth,
            "wall_warm" if horizon_index % 3 else "wall_weathered",
        )
        step_w = width * (0.62 + (horizon_index % 3) * 0.06)
        step_d = depth * (0.60 + ((horizon_index + 1) % 3) * 0.06)
        upper_h = height - lower_h
        builder.add_box(
            x + (-1 if horizon_index % 2 else 1) * width * 0.10,
            lower_h + upper_h / 2,
            z + depth * 0.08,
            step_w, upper_h, step_d,
            "wall_weathered" if horizon_index % 3 else "wall_warm",
        )
        builder.add_box(
            x, lower_h + 0.18, z,
            width + 0.48, 0.36, depth + 0.48, "trim",
        )
        roof_y = height + 0.22
        builder.add_box(
            x, roof_y, z,
            step_w + 0.68, 0.44, step_d + 0.68, "wall_warm",
        )
        # Front (south) blind arcades and floor belts establish 4.4m storeys
        # without any black backing surface or copied window grid.
        facade_z = z - depth / 2 - 0.07
        visible_levels = min(storeys, 4 if lod == 0 else 2)
        for level in range(visible_levels):
            level_y = 2.25 + level * 4.4
            if level_y >= lower_h - 0.4:
                break
            belt_y = (level + 1) * 4.4
            builder.add_box(
                x, belt_y, facade_z + 0.04,
                width * 0.88, 0.18, 0.18, "trim",
            )
            bay_count = max(2, min(4 if lod == 0 else 2, int(width // 4.6)))
            for bay in range(bay_count):
                bay_x = x + (bay - (bay_count - 1) / 2) * width * 0.72 / max(1, bay_count - 1)
                panel_w = min(2.2, width / bay_count * 0.52)
                panel_h = 2.35
                builder.add_box(
                    bay_x, level_y, facade_z,
                    panel_w, panel_h, 0.14,
                    "wall_weathered" if (bay + level + horizon_index) % 4 else "wall_warm",
                )
                builder.add_beam(
                    (bay_x - panel_w / 2, level_y + panel_h / 2, facade_z - 0.04),
                    (bay_x, level_y + panel_h / 2 + 0.58, facade_z - 0.04),
                    0.085, 0.07, "trim",
                )
                builder.add_beam(
                    (bay_x, level_y + panel_h / 2 + 0.58, facade_z - 0.04),
                    (bay_x + panel_w / 2, level_y + panel_h / 2, facade_z - 0.04),
                    0.085, 0.07, "trim",
                )
        if lod == 0:
            # One asymmetrical windcatcher/roof terrace cue per parcel makes
            # the skyline read as a built city rather than cuboid extrusion.
            catcher_h = 3.4 + (horizon_index % 3) * 0.8
            catcher_x = x + (-1 if horizon_index % 2 else 1) * step_w * 0.24
            builder.add_box(
                catcher_x, height + catcher_h / 2, z,
                min(3.4, step_w * 0.24), catcher_h, min(3.0, step_d * 0.32),
                "wall_warm",
            )
            builder.add_box(
                catcher_x, height + catcher_h + 0.18, z,
                min(3.8, step_w * 0.27), 0.36, min(3.4, step_d * 0.36),
                "trim",
            )

    # The road material already carries the stone response.  Two thin ceramic
    # inlays per authored boulevard give direction at a tiny vertex cost; the
    # previous hundreds of individual paving boxes added >0.4 MB while barely
    # changing the first-person render.
    landmarks = stage.get("landmarkPlacements", [])
    if len(landmarks) == 2:
        size = stage["size"] * 0.78
        for landmark_index, landmark in enumerate(landmarks):
            offset = 0.82 if landmark_index == 0 else 0.48
            builder.add_box(
                landmark["cx"] - offset, 0.031, 0,
                0.10, 0.012, size, "wall_alt",
            )
            builder.add_box(
                0, 0.031, landmark["cz"] + offset,
                size, 0.012, 0.10, "wall_warm",
            )

    segments = []
    for box in stage["boxes"]:
        if (
            not box.get("district")
            or box.get("landmarkId")
            or box.get("ghost")
            or box.get("decor")
            or box.get("legacyHorizon")
            or box["h"] < 7.5
        ):
            continue
        along_x = box["w"] >= box["d"]
        length = box["w"] if along_x else box["d"]
        thickness = box["d"] if along_x else box["w"]
        if length < 11.0 or thickness > 3.2:
            continue
        segments.append((length * box["h"], box, along_x, length, thickness))
    segments.sort(key=lambda item: item[0], reverse=True)

    for segment_index, (_, wall, along_x, length, thickness) in enumerate(
        segments[:24 if lod == 0 else 14]
    ):
        base = wall["y"] - wall["h"] / 2
        top = wall["y"] + wall["h"] / 2
        # Select the elevation facing the nearest main boulevard.  The reverse
        # remains a deliberately quieter service wall instead of a duplicate.
        if along_x:
            side = -1 if wall["z"] > 0 else 1
            plane_x = wall["x"]
            plane_z = wall["z"] + side * (thickness / 2 + 0.075)
        else:
            side = -1 if wall["x"] > 0 else 1
            plane_x = wall["x"] + side * (thickness / 2 + 0.075)
            plane_z = wall["z"]

        # Supported base/string/fascia bands break the thin shell into readable
        # storeys and cast real shadows without window-grid repetition.
        for band_index, band_y in enumerate((base + 0.52, base + wall["h"] * 0.48, top - 0.42)):
            if along_x:
                builder.add_box(
                    plane_x, band_y, plane_z,
                    length + (0.38 if band_index == 2 else 0.12),
                    0.22 if band_index != 2 else 0.34,
                    0.16,
                    "trim" if band_index != 1 else "wall_warm",
                )
            else:
                builder.add_box(
                    plane_x, band_y, plane_z,
                    0.16,
                    0.22 if band_index != 2 else 0.34,
                    length + (0.38 if band_index == 2 else 0.12),
                    "trim" if band_index != 1 else "wall_warm",
                )

        bay_pitch = 4.0
        bay_count = max(2, min(7 if lod == 0 else 4, int(length // bay_pitch)))
        used_span = min(length * 0.82, bay_count * bay_pitch)
        for bay in range(bay_count):
            tangent = (
                bay - (bay_count - 1) / 2
            ) * used_span / max(1, bay_count - 1)
            panel_w = min(2.15, used_span / max(1, bay_count) * 0.58)
            panel_h = min(3.15, wall["h"] * 0.30)
            panel_y = base + min(4.0, wall["h"] * 0.36)
            # Blind recessed panel: it supplies door/arch scale but never
            # advertises a collider-free opening.
            panel_key = "wall_warm" if (bay + segment_index) % 3 else "wall_weathered"
            if along_x:
                panel_x, panel_z = plane_x + tangent, plane_z + side * 0.012
                builder.add_box(panel_x, panel_y, panel_z, panel_w, panel_h, 0.065, panel_key)
                for edge in (-1, 1):
                    builder.add_box(
                        panel_x + edge * (panel_w / 2 + 0.10), panel_y,
                        panel_z + side * 0.045,
                        0.18, panel_h + 0.42, 0.13, "wall_weathered",
                    )
                arch_left = (panel_x - panel_w / 2, panel_y + panel_h / 2, panel_z + side * 0.055)
                arch_apex = (panel_x, panel_y + panel_h / 2 + 0.68, panel_z + side * 0.055)
                arch_right = (panel_x + panel_w / 2, panel_y + panel_h / 2, panel_z + side * 0.055)
            else:
                panel_x, panel_z = plane_x + side * 0.012, plane_z + tangent
                builder.add_box(panel_x, panel_y, panel_z, 0.065, panel_h, panel_w, panel_key)
                for edge in (-1, 1):
                    builder.add_box(
                        panel_x + side * 0.045, panel_y,
                        panel_z + edge * (panel_w / 2 + 0.10),
                        0.13, panel_h + 0.42, 0.18, "wall_weathered",
                    )
                arch_left = (panel_x + side * 0.055, panel_y + panel_h / 2, panel_z - panel_w / 2)
                arch_apex = (panel_x + side * 0.055, panel_y + panel_h / 2 + 0.68, panel_z)
                arch_right = (panel_x + side * 0.055, panel_y + panel_h / 2, panel_z + panel_w / 2)
            builder.add_beam(arch_left, arch_apex, 0.08, 0.07, "trim")
            builder.add_beam(arch_apex, arch_right, 0.08, 0.07, "trim")

            # Indigo cloth is omitted here until it has real sag, folded edges
            # and fasteners.  A flat accent box reads as a recoloured black
            # window and is worse than the recessed warm-stone panel.

        if lod == 0:
            # Sparse parapet teeth and a supported fabric shade establish a
            # bazaar skyline while retaining the authoritative wall footprint.
            tooth_count = max(3, min(8, int(length // 4.8)))
            for tooth in range(tooth_count):
                tangent = (
                    tooth - (tooth_count - 1) / 2
                ) * length * 0.86 / max(1, tooth_count - 1)
                if along_x:
                    builder.add_box(
                        wall["x"] + tangent, top + 0.42, wall["z"],
                        1.10, 0.84, thickness + 0.12, "wall_weathered",
                    )
                else:
                    builder.add_box(
                        wall["x"], top + 0.42, wall["z"] + tangent,
                        thickness + 0.12, 0.84, 1.10, "wall_weathered",
                    )
            if segment_index % 4 == 0:
                shade_y = base + min(4.25, wall["h"] * 0.38)
                shade_span = min(6.5, length * 0.42)
                shade_depth = 0.72
                if along_x:
                    builder.add_sagged_awning(
                        wall["x"], shade_y + 0.05, plane_z,
                        shade_span, shade_depth, 0.16,
                        "x", side, "accent",
                    )
                    builder.add_beam(
                        (wall["x"] - shade_span / 2, shade_y, plane_z + side * 0.58),
                        (wall["x"] + shade_span / 2, shade_y, plane_z + side * 0.58),
                        0.07, 0.06, "wood",
                    )
                    for brace in (-1, 1):
                        builder.add_beam(
                            (wall["x"] + brace * shade_span * 0.42, shade_y - 0.62, plane_z),
                            (wall["x"] + brace * shade_span * 0.42, shade_y, plane_z + side * 0.58),
                            0.06, 0.05, "trim",
                        )
                else:
                    builder.add_sagged_awning(
                        plane_x, shade_y + 0.05, wall["z"],
                        shade_span, shade_depth, 0.16,
                        "z", side, "accent",
                    )
                    builder.add_beam(
                        (plane_x + side * 0.58, shade_y, wall["z"] - shade_span / 2),
                        (plane_x + side * 0.58, shade_y, wall["z"] + shade_span / 2),
                        0.07, 0.06, "wood",
                    )
                    for brace in (-1, 1):
                        builder.add_beam(
                            (plane_x, shade_y - 0.62, wall["z"] + brace * shade_span * 0.42),
                            (plane_x + side * 0.58, shade_y, wall["z"] + brace * shade_span * 0.42),
                            0.06, 0.05, "trim",
                        )


def add_authoritative_wall_facades(builder, stage, lod):
    """Articulate the thin collider walls used by enterable buildings.

    StageLayout models interiors as separate wall, roof and floor boxes.  This
    pass decorates only wall segments that already block traversal, so doors
    and route openings remain open and no collider-free facade crosses them.
    """
    if lod == 2 or stage["id"] == "kairou":
        # The Kairou reference kit already articulates these same collision
        # walls; a second generic pane/service layer is duplicate binary cost.
        return
    family = IDENTITIES[stage["id"]][0]
    mood = stage["palette"].get("mood")
    landmarks = stage.get("landmarkPlacements", [])
    route_x = [float(item["cx"]) for item in landmarks] if len(landmarks) == 2 else [0.0]
    route_z = [float(item["cz"]) for item in landmarks] if len(landmarks) == 2 else [0.0]

    # The three active reference stages assign their largest wall strips to
    # add_playable_district_facades for a bespoke two-sided kit. Recompute the
    # exact same ranked claim here and skip only those dictionary objects;
    # every remaining thin collider wall keeps this lighter generic owner.
    claimed_box_ids = set()
    if stage["id"] in {"kunren", "souko", "nakaniwa"}:
        facade_language = PROFILES[stage["id"]]["cityProfile"]["facadeLanguage"]
        signature = sum(
            (char_index + 1) * ord(char)
            for char_index, char in enumerate(facade_language)
        ) % 7
        claimed = [
            box for box in stage["boxes"]
            if box.get("district")
            and not box.get("landmarkId")
            and not box.get("ghost")
            and not box.get("decor")
            and not box.get("legacyHorizon")
            and box["h"] >= 4.2
            and box["w"] * box["d"] >= 30
            and min(box["w"], box["d"]) <= 1.25
            and max(box["w"], box["d"]) >= 8.0
        ]
        claimed.sort(
            key=lambda box: box["w"] * box["d"] * box["h"],
            reverse=True,
        )
        claim_limit = 8 + (signature % 5) if lod == 0 else 6 + (signature % 3)
        claimed_box_ids = {id(box) for box in claimed[:claim_limit]}
    segments = []
    for box in stage["boxes"]:
        if (
            not box.get("district")
            or box.get("landmarkId")
            or box.get("ghost")
            or box.get("decor")
            or box.get("legacyHorizon")
            or id(box) in claimed_box_ids
        ):
            continue
        if box["h"] < 3.2:
            continue
        along_x = box["d"] <= 1.6 and box["w"] >= 4.0
        along_z = box["w"] <= 1.6 and box["d"] >= 4.0
        if along_x or along_z:
            route_distance = min(
                abs(box["z"] - road) for road in route_z
            ) if along_x else min(
                abs(box["x"] - road) for road in route_x
            )
            segments.append((route_distance, box, along_x))
    segments.sort(
        key=lambda item: (
            item[0],
            -max(item[1]["w"], item[1]["d"]) * item[1]["h"],
        )
    )
    for index, (_, box, along_x) in enumerate(segments[:28 if lod == 0 else 16]):
        length = box["w"] if along_x else box["d"]
        bays = max(1, min(2 if lod == 0 else 1, int(length // 6.2)))
        base_y = box["y"] - box["h"] / 2
        y = base_y + min(box["h"] * 0.58, 2.65)
        pane_h = max(0.64, min(1.18, box["h"] * 0.27))
        # Only the inward/route-readable side is articulated. Alternating
        # segments use closed service panels, leaving one third glazed.
        if along_x:
            nearest_route = min(route_z, key=lambda road: abs(box["z"] - road))
            side = 1 if nearest_route >= box["z"] else -1
        else:
            nearest_route = min(route_x, key=lambda road: abs(box["x"] - road))
            side = 1 if nearest_route >= box["x"] else -1
        glazed_segment = index % 3 == 0
        for bay in range(bays):
            offset = (bay - (bays - 1) / 2) * length * 0.58 / max(1, bays - 1)
            pane_span = min(1.34, length / (bays + 0.8) * 0.52) * (0.94 + ((index + bay) % 3) * 0.04)
            if along_x:
                face_z = box["z"] + side * box["d"] / 2
                if glazed_segment:
                    for frame_x, frame_y, frame_w, frame_h in (
                        (box["x"] + offset - pane_span / 2 - 0.07, y, 0.14, pane_h + 0.28),
                        (box["x"] + offset + pane_span / 2 + 0.07, y, 0.14, pane_h + 0.28),
                        (box["x"] + offset, y - pane_h / 2 - 0.07, pane_span, 0.14),
                        (box["x"] + offset, y + pane_h / 2 + 0.07, pane_span, 0.14),
                    ):
                        builder.add_box(frame_x, frame_y, face_z + side * 0.10, frame_w, frame_h, 0.20, "trim")
                    pane_key = "emissive" if mood == "night" and index % 9 == 0 else "glass"
                    builder.add_box(box["x"] + offset, y, face_z + side * 0.026, pane_span, pane_h, 0.026, pane_key)
                    builder.record_facade_glass(pane_span, pane_h, 0.013, 0.147)
                else:
                    builder.add_box(box["x"] + offset, y, face_z + side * 0.03, pane_span, pane_h, 0.055, "accent" if family == "heritage" else "wall_alt")
            else:
                face_x = box["x"] + side * box["w"] / 2
                if glazed_segment:
                    for frame_z, frame_y, frame_d, frame_h in (
                        (box["z"] + offset - pane_span / 2 - 0.07, y, 0.14, pane_h + 0.28),
                        (box["z"] + offset + pane_span / 2 + 0.07, y, 0.14, pane_h + 0.28),
                        (box["z"] + offset, y - pane_h / 2 - 0.07, pane_span, 0.14),
                        (box["z"] + offset, y + pane_h / 2 + 0.07, pane_span, 0.14),
                    ):
                        builder.add_box(face_x + side * 0.10, frame_y, frame_z, 0.20, frame_h, frame_d, "trim")
                    pane_key = "emissive" if mood == "night" and index % 9 == 0 else "glass"
                    builder.add_box(face_x + side * 0.026, y, box["z"] + offset, 0.026, pane_h, pane_span, pane_key)
                    builder.record_facade_glass(pane_span, pane_h, 0.013, 0.147)
                else:
                    builder.add_box(face_x + side * 0.03, y, box["z"] + offset, 0.055, pane_h, pane_span, "accent" if family == "heritage" else "wall_alt")
        # A seated top/bottom belt exposes construction scale even when the
        # wall is seen at a glancing angle from the interior.
        if along_x:
            for y in (base_y + 0.20, base_y + box["h"] - 0.18):
                builder.add_box(box["x"], y, box["z"], length + 0.12, 0.16, box["d"] + 0.14, "trim")
        else:
            for y in (base_y + 0.20, base_y + box["h"] - 0.18):
                builder.add_box(box["x"], y, box["z"], box["w"] + 0.14, 0.16, length + 0.12, "trim")

        if lod == 0:
            # The opposite elevation is often the first surface seen from a
            # street spawn (for example Sakyuu's south bunker wall).  Leaving
            # it completely blank produced a full-screen beige slab when the
            # player reached the real collider.  Add one sparse, closed
            # service composition on that same solid wall.  There is no glass,
            # no repeated grid and only 3-7 cm of facade relief.
            reverse = -side
            panel_count = 2 if length >= 20 else 1
            for panel in range(panel_count):
                offset = (panel - (panel_count - 1) / 2) * min(8.0, length * 0.34)
                panel_w = min(3.8, max(1.8, length * 0.12))
                panel_h = min(2.8, max(1.4, box["h"] * 0.36))
                panel_y = base_y + min(2.5, box["h"] * 0.48)
                if along_x:
                    face_z = box["z"] + reverse * box["d"] / 2
                    builder.add_box(
                        box["x"] + offset, panel_y, face_z + reverse * 0.032,
                        panel_w, panel_h, 0.064,
                        "accent" if (index + panel) % 4 == 0 else "wall_alt",
                    )
                    for slat in (-1, 0, 1):
                        builder.add_box(
                            box["x"] + offset,
                            panel_y + slat * panel_h * 0.25,
                            face_z + reverse * 0.069,
                            panel_w * 0.82, 0.055, 0.038, "trim",
                        )
                else:
                    face_x = box["x"] + reverse * box["w"] / 2
                    builder.add_box(
                        face_x + reverse * 0.032, panel_y, box["z"] + offset,
                        0.064, panel_h, panel_w,
                        "accent" if (index + panel) % 4 == 0 else "wall_alt",
                    )
                    for slat in (-1, 0, 1):
                        builder.add_box(
                            face_x + reverse * 0.069,
                            panel_y + slat * panel_h * 0.25,
                            box["z"] + offset,
                            0.038, 0.055, panel_w * 0.82, "trim",
                        )


def add_dense_city_building(builder, stage, lod, index, x, z, width, depth, height, yaw, high_rise):
    """Create one stage-specific perimeter building from seated components.

    Connection map (runtime Y-up): foundation top=0.48, primary bottom=0.42;
    setback bottoms equal the preceding mass tops; roof/crown bottoms equal the
    final mass top; facade plates sit 4.5cm outside the inward solid face.
    Nothing crosses the authoritative play boundary, so visible architecture
    never advertises a route which lacks a TypeScript collider.
    """
    family = IDENTITIES[stage["id"]][0]
    seed = stage["seed"]
    ruined = family in {"undead", "geothermal"}
    heritage = family in {"heritage", "wilderness"}
    industrial = family in {"industrial", "military", "airport"}
    cold = family == "arctic"
    urban = family == "urban"
    profile = PROFILES[stage["id"]]
    city_profile = profile["cityProfile"]
    skyline = profile["skyline"]
    # The 31 profile phrases are the authored kit identity, not documentation
    # only.  Folding roof/facade/block language into geometry prevents maps in
    # the same broad material family from collapsing into the same eight boxes.
    city_signature = stable_text_signature(
        stage["id"],
        city_profile["blockPattern"],
        city_profile["roofLanguage"],
        city_profile["facadeLanguage"],
    )
    cosine, sine = math.cos(yaw), math.sin(yaw)

    def point(local_x, local_z):
        return x + local_x * cosine - local_z * sine, z + local_x * sine + local_z * cosine

    def box(local_x, local_y, local_z, w, h, d, key):
        px, pz = point(local_x, local_z)
        builder.add_oriented_box(px, local_y, pz, w, h, d, yaw, key)

    variation = (int(stable_unit(seed, index, 0xD3A5) * 16) + city_signature) % 16
    roof_signature = (city_signature >> 5) % 7
    window_rhythm = (city_signature >> 11) % 5
    wall_key = facade_material_key(stage, index, variation + 3)
    box(0, 0.24, 0, width + 0.44, 0.48, depth + 0.44, "terrain" if heritage else "wall_alt")

    primary_h = height * (0.58 if high_rise else 0.78)
    box(0, 0.42 + primary_h / 2, 0, width, primary_h, depth, wall_key)

    # The ground storey is deliberately deeper than the tower body.  It seats
    # the mass, casts a real contact shadow and gives the FPS camera a human-
    # scale datum instead of a texture-only facade.
    podium_h = min(5.4, max(3.6, primary_h * 0.19))
    podium_key = facade_material_key(stage, index, variation + 17)
    box(0, 0.43 + podium_h / 2, depth * 0.025, width + 0.56, podium_h, depth + 0.34, podium_key)
    if lod == 0 and variation % 8 in {1, 3, 6}:
        # A seated side annex breaks the repeated rectangular footprint while
        # overlapping the podium by more than 1m on all axes.
        annex_side = -1 if variation % 2 else 1
        annex_w = width * (0.30 + (variation % 3) * 0.035)
        annex_h = min(primary_h * 0.56, 8.0 + variation * 0.7)
        box(
            annex_side * width * 0.41,
            0.43 + annex_h / 2,
            depth * 0.06,
            annex_w,
            annex_h,
            depth * 0.82,
            facade_material_key(stage, index, variation + 29),
        )
    top_y = 0.42 + primary_h
    top_width, top_depth = width, depth
    if high_rise:
        offset_x = (stable_unit(seed, index, 0xD3A6) - 0.5) * width * 0.24
        offset_z = (stable_unit(seed, index, 0xD3A7) - 0.5) * depth * 0.18
        middle_h = height * 0.27
        top_width, top_depth = width * (0.68 + (variation % 3) * 0.055), depth * (0.70 + (variation % 2) * 0.08)
        box(offset_x, top_y + middle_h / 2, offset_z, top_width, middle_h, top_depth, facade_material_key(stage, index, variation + 41))
        top_y += middle_h
        # LOD1 is a standalone medium-quality transport, not a runtime swap
        # from LOD0. Preserve the skyline crown in both authored qualities.
        if variation % 3 != 1:
            crown_h = max(2.6, height - top_y)
            box(offset_x * 1.24, top_y + crown_h / 2, offset_z * 1.18, top_width * 0.58, crown_h, top_depth * 0.62, facade_material_key(stage, index, variation + 53))
            top_y += crown_h

    roof_height = max(1.2, min(6.8, height * 0.12))
    if stage["id"] == "kairou":
        # Kairou's exterior kit is a layered flat-roof caravan city.  This
        # stage-specific branch prevents the broad heritage path below from
        # generating repeated blue gables and Japanese-looking ridges.
        box(0, top_y + 0.24, 0, top_width + 0.86, 0.48, top_depth + 0.86, "wall_warm")
        box(0, top_y + 0.58, 0, top_width + 1.18, 0.20, top_depth + 1.18, "trim")
        if lod == 0:
            parapet_h = 0.82
            parapet_t = 0.34
            box(0, top_y + 0.99, -top_depth / 2, top_width + 0.82, parapet_h, parapet_t, "wall_weathered")
            box(0, top_y + 0.99, top_depth / 2, top_width + 0.82, parapet_h, parapet_t, "wall_weathered")
            box(-top_width / 2, top_y + 0.99, 0, parapet_t, parapet_h, top_depth, "wall_weathered")
            box(top_width / 2, top_y + 0.99, 0, parapet_t, parapet_h, top_depth, "wall_weathered")
    elif ruined:
        # Broken roof planes and exposed rafters are much more legible than a
        # pristine flat cap on every zombie/geothermal skyline building.
        fragment_side = -1 if variation % 2 else 1
        roof_x, roof_z = point(fragment_side * top_width * 0.16, 0)
        builder.add_oriented_gable_roof(
            roof_x,
            top_y,
            roof_z,
            top_width * (0.56 + (variation % 3) * 0.06),
            roof_height * 0.72,
            top_depth + 0.76,
            yaw,
            "roof",
        )
        if lod == 0:
            for rafter in (-1, 0, 1):
                start = point(rafter * top_width * 0.25, -top_depth * 0.44)
                end = point(rafter * top_width * 0.20, top_depth * 0.22)
                builder.add_beam(
                    (start[0], top_y + 0.18, start[1]),
                    (end[0], top_y + roof_height * (0.48 + 0.08 * (rafter + 1)), end[1]),
                    0.12,
                    0.10,
                    "trim",
                )
    elif heritage or cold:
        roof_x, roof_z = point(0, 0)
        roof_mode = (roof_signature + variation) % 4
        if roof_mode == 0:
            # Offset twin ridges produce townhouses/monastic wings rather than
            # the old universal pyramid-like cap.
            for wing in (-1, 1):
                wing_x, wing_z = point(wing * top_width * 0.22, 0)
                builder.add_oriented_gable_roof(
                    wing_x, top_y, wing_z, top_width * 0.58, roof_height * (0.82 + 0.08 * (wing > 0)),
                    top_depth + 1.0, yaw, "roof",
                )
        elif roof_mode == 1:
            builder.add_oriented_gable_roof(
                roof_x, top_y, roof_z, top_width + 1.1, roof_height, top_depth + 1.0, yaw, "roof",
            )
            if lod == 0 and min(top_width, top_depth) > 9:
                builder.add_oriented_gable_roof(
                    roof_x, top_y + 0.04, roof_z, top_depth * 0.46, roof_height * 0.70,
                    top_width * 0.58, yaw + math.pi / 2, "roof",
                )
        elif roof_mode == 2:
            builder.add_oriented_gable_roof(
                roof_x, top_y, roof_z, top_width * 0.72, roof_height * 1.12,
                top_depth + 1.22, yaw, "roof",
            )
            box(0, top_y + 0.34, 0, top_width + 0.82, 0.68, top_depth + 0.82, "trim")
        else:
            # Deep-eave low ridge for Japanese/rural blocks; the inset ridge
            # keeps it visually separate from Takadai's steep slate roofs.
            builder.add_oriented_gable_roof(
                roof_x, top_y, roof_z, top_width + 1.52, roof_height * 0.58,
                top_depth + 1.68, yaw, "roof",
            )
            box(0, top_y + roof_height * 0.60, 0, top_width * 0.36, roof_height * 0.36, top_depth * 0.42, "wall_alt")
    elif industrial:
        roof_mode = (roof_signature + variation) % 3
        if roof_mode == 0:
            teeth = 3 if lod == 0 else 2
            tooth_span = top_width / teeth
            for tooth in range(teeth):
                local_x = (tooth - (teeth - 1) / 2) * tooth_span
                roof_x, roof_z = point(local_x, 0)
                builder.add_oriented_gable_roof(
                    roof_x, top_y, roof_z, tooth_span + 0.24, roof_height * 0.68,
                    top_depth + 0.84, yaw, "roof",
                )
        elif roof_mode == 1:
            # Raised monitor roof and side clerestory, common to rail, factory
            # and logistics halls but proportioned uniquely by profile seed.
            box(0, top_y + 0.30, 0, top_width + 0.72, 0.60, top_depth + 0.72, "roof")
            monitor_w = top_width * (0.34 + (variation % 3) * 0.055)
            box(0, top_y + roof_height * 0.42, 0, monitor_w, roof_height * 0.72, top_depth * 0.48, "wall_alt")
            monitor_x, monitor_z = point(0, 0)
            builder.add_oriented_gable_roof(
                monitor_x, top_y + roof_height * 0.76, monitor_z,
                monitor_w + 0.54, roof_height * 0.36, top_depth * 0.53,
                yaw, "roof",
            )
        else:
            # Open service crown: real beams give ports/military roofs a clear
            # functional silhouette without expensive curved geometry.
            box(0, top_y + 0.28, 0, top_width + 0.70, 0.56, top_depth + 0.70, "roof")
            if lod == 0:
                for frame in (-1, 1):
                    fx = frame * top_width * 0.31
                    for fz in (-top_depth * 0.28, top_depth * 0.28):
                        start = point(fx, fz)
                        builder.add_cylinder(start[0], top_y + roof_height * 0.42, start[1], 0.10, roof_height * 0.84, "trim", 6, 0.10)
                left = point(-top_width * 0.31, 0)
                right = point(top_width * 0.31, 0)
                builder.add_beam((left[0], top_y + roof_height * 0.82, left[1]), (right[0], top_y + roof_height * 0.82, right[1]), 0.13, 0.11, "accent")
    else:
        roof_mode = (roof_signature + variation) % 3
        box(0, top_y + 0.32, 0, top_width + 0.72, 0.64, top_depth + 0.72, "trim")
        if roof_mode == 1:
            # Slender offset penthouse breaks the repeated centred-box crown.
            crown_side = -1 if variation % 2 else 1
            box(crown_side * top_width * 0.22, top_y + 1.56, -top_depth * 0.08, top_width * 0.28, 2.48, top_depth * 0.42, "wall_alt")
        elif roof_mode == 2 and lod == 0:
            for fin in (-1, 1):
                fin_x, fin_z = point(fin * top_width * 0.28, 0)
                builder.add_beam((fin_x, top_y + 0.56, fin_z), (fin_x, top_y + roof_height * 1.18, fin_z - top_depth * 0.16), 0.12, 0.10, "accent" if fin > 0 else "trim")
        if lod == 0 and (urban or variation % 2 == 0):
            mast_x, mast_z = point(top_width * 0.18, 0)
            builder.add_cylinder(mast_x, top_y + 3.3, mast_z, 0.11, 6.0, "trim", 6, 0.07)

    # Inward facade only. Three fifths of midground buildings use either a
    # sparse punched-opening grammar or one clerestory ribbon; the remainder
    # use blind service walls, shutters, balconies and relief. This prevents a
    # second black grid appearing in the real-3D horizon.
    storey_target = (4.6, 5.4, 4.9, 5.8, 4.3)[window_rhythm]
    facade_levels = max(1, min(3 if lod == 0 else 2, int(height // (storey_target * 1.22))))
    bay_target = (3.0, 4.2, 3.5, 3.8, 2.8)[window_rhythm]
    facade_bays = max(2, min(4 if lod == 0 else 3, int(width // (bay_target * 1.35))))
    pane_ratio = (0.36, 0.70, 0.46, 0.54, 0.40)[window_rhythm]
    pane_width = min(2.10 if window_rhythm == 1 else 1.42, width / (facade_bays + 0.5) * pane_ratio)
    pane_height = (1.72, 0.78, 1.30, 1.12, 1.58)[window_rhythm]
    if industrial:
        pane_height *= 0.82
    elif heritage:
        pane_height *= 1.05
    facade_plane = depth / 2
    facade_mode = 4 if lod == 2 or stage["id"] == "kairou" else (variation + window_rhythm + index) % 5

    def recessed_pane(local_x, panel_y, panel_w, panel_h, pane_key):
        frame_depth = 0.20
        frame_center = 0.10
        glass_depth = 0.026
        glass_center = 0.026
        jamb = 0.14
        box(local_x - panel_w / 2 - jamb / 2, panel_y, facade_plane + frame_center, jamb, panel_h + jamb * 2, frame_depth, "trim")
        box(local_x + panel_w / 2 + jamb / 2, panel_y, facade_plane + frame_center, jamb, panel_h + jamb * 2, frame_depth, "trim")
        box(local_x, panel_y - panel_h / 2 - jamb / 2, facade_plane + frame_center, panel_w, jamb, frame_depth, "trim")
        box(local_x, panel_y + panel_h / 2 + jamb / 2, facade_plane + frame_center, panel_w, jamb, frame_depth, "trim")
        box(local_x, panel_y, facade_plane + glass_center, panel_w, panel_h, glass_depth, pane_key)
        builder.record_facade_glass(
            panel_w,
            panel_h,
            glass_center - glass_depth / 2,
            frame_center + frame_depth / 2 - (glass_center + glass_depth / 2),
        )

    pane_count = 0
    pane_budget = 8 if lod == 0 else 4
    if facade_mode == 0:
        # A single high ribbon replaces dozens of equal punched windows.
        ribbon_w = width * (0.46 + (variation % 3) * 0.055)
        ribbon_h = 0.62 + (window_rhythm % 3) * 0.10
        ribbon_y = min(primary_h - 1.2, max(4.2, primary_h * 0.68))
        recessed_pane(0, ribbon_y, ribbon_w, ribbon_h, "emissive" if stage["palette"].get("mood") == "night" and variation % 4 == 0 else "glass")
    elif facade_mode in {1, 2}:
        for level in range(facade_levels):
            panel_y = 2.6 + level * min(5.4, max(3.8, primary_h / max(1, facade_levels)))
            if panel_y >= primary_h - 0.8:
                break
            for bay in range(facade_bays):
                grammar = (bay * 5 + level * 3 + variation + window_rhythm + index) % 10
                local_x = (bay - (facade_bays - 1) / 2) * width * 0.72 / max(1, facade_bays - 1)
                pane_w = pane_width * (0.90 + ((bay + level + variation) % 4) * 0.045)
                pane_h = pane_height * (0.92 + ((bay * 2 + level + variation) % 3) * 0.045)
                if grammar in {0, 1, 2} and pane_count < pane_budget and not (ruined and grammar == 2):
                    pane_key = "emissive" if stage["palette"].get("mood") == "night" and (bay + level + variation) % 7 == 0 else "glass"
                    recessed_pane(local_x, panel_y, pane_w, pane_h, pane_key)
                    pane_count += 1
                elif grammar in {3, 4, 5, 6}:
                    # Closed shutter/service bay, 4-7cm proud of the wall.
                    box(local_x, panel_y, facade_plane + 0.030, pane_w * 1.05, pane_h, 0.055, "wall_alt" if industrial or ruined else "accent")
                    if lod == 0:
                        for slat in (-1, 0, 1):
                            box(local_x, panel_y + slat * pane_h * 0.27, facade_plane + 0.064, pane_w * 0.84, 0.055, 0.035, "trim")
            if lod == 0 and level < facade_levels - 1 and level % 2 == 0:
                box(0, panel_y - 1.14, facade_plane + 0.07, width * 0.72, 0.14, 0.14, "accent" if heritage else "trim")
    elif lod == 0:
        # Blind/service elevation with a material break and one louvre ribbon.
        service_y = min(primary_h - 1.0, 5.4 + (variation % 3) * 1.4)
        box(
            0, service_y, facade_plane + 0.035,
            width * 0.58, 1.05, 0.065,
            "wall_weathered" if stage["id"] == "kairou" else "wall_alt",
        )
        for slat in (-2, -1, 0, 1, 2):
            box(0, service_y + slat * 0.17, facade_plane + 0.075, width * 0.48, 0.045, 0.045, "trim")

    if lod == 0:
        # Two edge piers frame the elevation without subdividing it into a grid.
        for local_x in (-width * 0.38, width * 0.38):
            box(local_x, primary_h * 0.53, facade_plane + 0.075, 0.13 if industrial else 0.10, primary_h * 0.92, 0.14, "trim")

        # Recessed entrance, double leaves, transom and a projecting canopy.
        entrance_w = min(3.6, max(2.4, width * 0.22))
        box(0, 1.72, facade_plane + 0.058, entrance_w + 0.42, 3.18, 0.13, "trim")
        for leaf in (-1, 1):
            box(
                leaf * entrance_w * 0.255, 1.58, facade_plane + 0.126,
                entrance_w * 0.43, 2.62, 0.055,
                "wood" if stage["id"] == "kairou" else "wall_alt",
            )
        box(0, 3.02, facade_plane + 0.128, entrance_w * 0.92, 0.34, 0.06, "accent")
        canopy_key = "accent" if variation % 3 == 0 else "trim"
        box(0, 3.46, facade_plane + 0.62, entrance_w + 1.30, 0.18, 1.18, canopy_key)
        for post in (-1, 1):
            box(post * (entrance_w + 0.72) * 0.5, 1.72, facade_plane + 1.08, 0.11, 3.42, 0.11, "trim")

        # Use-specific facade grammar.  These silhouette/details are explicit
        # mesh and deterministic per stage/building; they are not a distant
        # raster matte or a repeated all-map house kit.
        if urban or heritage:
            balcony_levels = min(3, max(1, facade_levels - 2))
            balcony_side = -1 if variation % 2 else 1
            for balcony in range(balcony_levels):
                balcony_y = 5.0 + balcony * 4.4
                if balcony_y >= primary_h - 1.0:
                    break
                balcony_x = balcony_side * width * (0.20 + (balcony % 2) * 0.08)
                balcony_w = width * (0.30 if heritage else 0.24)
                box(balcony_x, balcony_y, facade_plane + 0.64, balcony_w, 0.16, 1.22, "accent" if heritage else "trim")
                for rail in (-1, 0, 1):
                    box(balcony_x + rail * balcony_w * 0.44, balcony_y + 0.56, facade_plane + 1.18, 0.07, 1.02, 0.07, "trim")
                box(balcony_x, balcony_y + 1.02, facade_plane + 1.19, balcony_w, 0.07, 0.07, "trim")
        elif industrial:
            # External X-bracing, loading louver and service riser.
            brace_span = width * 0.30
            brace_center = (-1 if variation % 2 else 1) * width * 0.27
            brace_bottom, brace_top = 4.4, min(primary_h - 1.0, 13.5)
            for direction in (-1, 1):
                start = point(brace_center - direction * brace_span / 2, facade_plane + 0.19)
                end = point(brace_center + direction * brace_span / 2, facade_plane + 0.19)
                builder.add_beam((start[0], brace_bottom, start[1]), (end[0], brace_top, end[1]), 0.12, 0.10, "accent" if variation % 3 == 0 else "trim")
            riser_x = (-1 if variation % 2 else 1) * width * 0.42
            riser_world = point(riser_x, facade_plane + 0.20)
            builder.add_cylinder(riser_world[0], primary_h * 0.48, riser_world[1], 0.16, primary_h * 0.82, "trim", 8, 0.16)
        else:
            # Deep sun/rain screens keep desert, arctic and wilderness blocks
            # from collapsing into the same generic concrete facade.
            screen_y = min(primary_h - 1.2, 6.4 + (variation % 3) * 1.6)
            box(0, screen_y, facade_plane + 0.42, width * 0.72, 0.18, 0.72, "accent")
            screen_count = 5 if width > 15 else 3
            for screen in range(screen_count):
                screen_x = (screen - (screen_count - 1) / 2) * width * 0.62 / max(1, screen_count - 1)
                box(screen_x, screen_y - 1.05, facade_plane + 0.67, 0.10, 2.05, 0.48, "trim")

        # Rooftop mechanical cluster / cultural crown.  Real geometry and
        # asymmetry prevent the skyline from repeating even inside one stage.
        equipment_count = 2 + variation % 3
        for equipment in range(equipment_count):
            local_x = (equipment - (equipment_count - 1) / 2) * top_width * 0.22
            local_z = -top_depth * (0.05 + 0.12 * (equipment % 2))
            equipment_w = max(0.9, top_width * (0.07 + 0.01 * ((variation + equipment) % 3)))
            equipment_h = 0.8 + 0.42 * ((variation + equipment) % 3)
            box(local_x, top_y + equipment_h / 2 + 0.36, local_z, equipment_w, equipment_h, max(0.8, top_depth * 0.12), "trim" if equipment % 2 else "wall_alt")

        if skyline in {"neon-megacity", "dead-neon-city", "firestorm-blocks", "dense-highrise"}:
            # Two vertical light/facade fins are enough to create a unique
            # night signature without a large emissive overdraw surface.
            for fin in (-1, 1):
                box(fin * width * (0.32 + 0.02 * (variation % 2)), primary_h * 0.57, facade_plane + 0.16, 0.16, primary_h * 0.72, 0.12, "emissive" if fin == (-1 if variation % 2 else 1) else "accent")

    if lod == 0:
        # A unique service/cultural cue on every second building prevents the
        # four sides from reading as a duplicated house kit.
        if industrial and variation % 2 == 0:
            px, pz = point(width * 0.32, -depth * 0.16)
            builder.add_cylinder(px, top_y + 2.2, pz, 0.42, 4.4, "trim", 8, 0.28)
        elif heritage and variation % 2:
            for post in (-1, 0, 1):
                box(post * width * 0.24, primary_h * 0.54, depth / 2 + 0.19, 0.16, primary_h * 0.86, 0.20, "trim")
        elif ruined:
            start = point(-width * 0.44, depth * 0.52)
            end = point(width * 0.18, depth * 0.52)
            builder.add_beam((start[0], top_y, start[1]), (end[0], max(2.0, top_y - roof_height * 0.9), end[1]), 0.16, 0.12, "trim")

    # Stage-owned skyline signatures.  These are deliberately macro features
    # with a tiny vertex cost; material noise alone cannot distinguish an
    # Egyptian wind-town from a polar campus or a working shipyard.
    signature_detail = lod == 0
    stage_id = stage["id"]
    if stage_id == "kairou" and (signature_detail or index % 2 == 0):
        tower_count = 2 if signature_detail and index % 3 == 0 else 1
        for tower in range(tower_count):
            local_x = (tower - (tower_count - 1) / 2) * top_width * 0.28
            tower_h = min(7.0, 3.6 + (index + tower) % 4 * 0.65)
            box(local_x, top_y + tower_h / 2, -top_depth * 0.08, min(3.0, top_width * 0.18), tower_h, min(2.8, top_depth * 0.24), "wall_warm")
            if signature_detail:
                # Open timber ventilation slits over the warm solid tower;
                # never a shallow black/blue backing card.
                slit_span = min(1.8, top_width * 0.10)
                for slit in (-1, 0, 1):
                    box(
                        local_x + slit * slit_span * 0.28,
                        top_y + tower_h * 0.72,
                        top_depth * 0.075,
                        0.055,
                        tower_h * 0.23,
                        0.055,
                        "wood",
                    )
        if signature_detail and index % 2 == 0:
            box(0, podium_h + 0.42, depth / 2 + 0.28, width * 0.84, 0.26, 0.56, "accent")
    elif stage_id == "chikurin" and (signature_detail or index % 2 == 0):
        roof_x, roof_z = point(0, 0)
        builder.add_oriented_gable_roof(
            roof_x, top_y + 0.12, roof_z,
            top_width + (1.8 if signature_detail else 1.0),
            roof_height * 0.62,
            top_depth + (2.0 if signature_detail else 1.1),
            yaw,
            "roof",
        )
        if signature_detail:
            box(0, top_y + 0.20, 0, top_width + 2.5, 0.18, top_depth + 2.7, "accent")
            for brace_side in (-1, 1):
                start = point(brace_side * width * 0.40, depth * 0.51)
                end = point(brace_side * width * 0.28, depth * 0.51)
                builder.add_beam((start[0], podium_h * 0.55, start[1]), (end[0], primary_h * 0.68, end[1]), 0.12, 0.10, "wood")
    elif stage_id == "setsugen" and (signature_detail or index % 3 == 0):
        radius = min(3.4, max(1.6, top_width * 0.12))
        dome_x, dome_z = point(top_width * (-0.18 if index % 2 else 0.18), 0)
        builder.add_cylinder(dome_x, top_y + radius * 0.48, dome_z, radius, radius * 0.96, "glass", 12 if signature_detail else 8, radius * 0.28)
        if signature_detail and index % 2 == 0:
            left = point(-top_width * 0.36, top_depth * 0.34)
            right = point(top_width * 0.36, top_depth * 0.34)
            builder.add_beam((left[0], primary_h * 0.62, left[1]), (right[0], primary_h * 0.62, right[1]), 0.24, 0.34, "accent")
    elif stage_id == "kouwan" and (signature_detail or index % 2 == 0):
        gantry_span = top_width * 0.72
        for side in (-1, 1):
            px, pz = point(side * gantry_span / 2, 0)
            builder.add_cylinder(px, top_y + 2.5, pz, 0.16, 5.0, "trim", 6, 0.12)
        left = point(-gantry_span / 2, 0)
        right = point(gantry_span / 2, 0)
        builder.add_beam((left[0], top_y + 4.8, left[1]), (right[0], top_y + 4.8, right[1]), 0.20, 0.18, "accent")
        if signature_detail:
            pipe_a = point(-width * 0.42, depth * 0.47)
            pipe_b = point(width * 0.42, depth * 0.47)
            builder.add_beam((pipe_a[0], podium_h * 0.82, pipe_a[1]), (pipe_b[0], podium_h * 0.82, pipe_b[1]), 0.16, 0.16, "trim")
    elif stage_id == "sakyuu" and (signature_detail or index % 2 == 0):
        fin_count = 3 if signature_detail else 1
        for fin in range(fin_count):
            local_x = (fin - (fin_count - 1) / 2) * top_width * 0.24
            start = point(local_x - top_width * 0.055, -top_depth * 0.22)
            end = point(local_x + top_width * 0.055, top_depth * 0.22)
            builder.add_beam((start[0], top_y + 0.4, start[1]), (end[0], top_y + 4.2 + fin * 0.45, end[1]), 0.16, 0.12, "accent")
        if signature_detail:
            box(0, podium_h * 0.28, depth * 0.51, width * 0.86, podium_h * 0.36, 0.52, "terrain")
    elif stage_id in {"z04", "takadai"} and (signature_detail or index % 2 == 0):
        pinnacle_count = 2 if signature_detail else 1
        for pinnacle in range(pinnacle_count):
            local_x = (-1 if pinnacle == 0 else 1) * top_width * 0.30
            px, pz = point(local_x, 0)
            pinnacle_h = 5.0 + (index + pinnacle) % 3 * 1.1
            builder.add_cylinder(px, top_y + pinnacle_h / 2, pz, 0.64, pinnacle_h, "wall_alt", 8, 0.08)
        if stage_id == "z04" and signature_detail:
            broken_start = point(-top_width * 0.42, top_depth * 0.48)
            broken_end = point(top_width * 0.10, top_depth * 0.48)
            builder.add_beam((broken_start[0], top_y + 0.2, broken_start[1]), (broken_end[0], max(primary_h * 0.68, top_y - roof_height), broken_end[1]), 0.18, 0.14, "trim")


def add_exterior_architecture(builder, stage, lod):
    """Build the dense, tall, profile-defined real-3D town around all sides.

    V5 turns the old four-side single ring into two staggered street-wall rows.
    Profile coverage now controls occupied frontage and streetWidthM controls
    the depth between rows.  The north/west districts receive more parcels
    because they are the midground in the safe first-spawn view; east/south
    still retain a complete 360-degree real-mesh exterior when the player
    turns around.
    """
    city = PROFILES[stage["id"]]["cityProfile"]
    half = stage["size"] / 2
    full_count = int(city["targetBuildingCount"][1])
    count = full_count if lod == 0 else max(14, round(full_count * 0.68)) if lod == 1 else max(10, round(full_count * 0.46))
    high_count = max(1, round(count * float(city["highRiseRatio"])))
    ranked = sorted(range(count), key=lambda item: stable_unit(stage["seed"], item, 0xD3B0))
    high_rises = set(ranked[:high_count])
    dominant_min, dominant_max = city["dominantHeightM"]
    secondary_min, secondary_max = city["secondaryHeightM"]
    composition_signature = stable_text_signature(
        stage["id"], city["blockPattern"], city["openSpaceRule"], city["verticalityRule"]
    )
    coverage = float(city["coverageRatio"])
    street_min, street_max = (float(value) for value in city["streetWidthM"])
    street_depth = (street_min + street_max) * 0.5

    # Exact largest-remainder allocation: north/west form the opening vista,
    # while east/south remain dense enough to avoid a one-sided stage set.
    weights = (0.31, 0.31, 0.19, 0.19)
    raw_side_counts = [count * weight for weight in weights]
    side_counts = [int(value) for value in raw_side_counts]
    for side in sorted(
        range(4),
        key=lambda item: (raw_side_counts[item] - side_counts[item], -item),
        reverse=True,
    )[:count - sum(side_counts)]:
        side_counts[side] += 1

    placements = []
    for side, side_count in enumerate(side_counts):
        row_counts = ((side_count + 1) // 2, side_count // 2)
        for slot in range(side_count):
            row = slot & 1
            row_slot = slot // 2
            row_count = max(1, row_counts[row])
            progression = (row_slot + 0.5) / row_count
            # Stagger the outer row by half a parcel so the silhouette has
            # visible parallax instead of two perfectly superposed walls.
            stagger = ((row * 0.5 + (composition_signature % 3) * 0.11) / row_count) * (1 if side < 2 else -1)
            progression = max(0.05, min(0.95, progression + stagger))
            placements.append((side, row, row_slot, row_count, progression))

    landmark_vistas = [
        landmark_spawn_vista(stage, landmark_index, profile_landmark)
        for landmark_index, profile_landmark in enumerate(PROFILES[stage["id"]]["megaLandmarks"])
    ]

    for index, (side, row, slot, side_count, progression) in enumerate(placements):
        along = (progression - 0.5) * half * 1.84
        jitter = (stable_unit(stage["seed"], index, 0xD3B1) - 0.5) * min(4.2, half * 0.028)
        high_rise = index in high_rises
        side_pitch = half * 1.84 / side_count
        frontage = min(0.94, max(0.62, coverage + (stable_unit(stage["seed"], index, 0xD3B2) - 0.5) * 0.12))
        width = max(10.0, min(38.0, side_pitch * frontage))
        depth = 9.5 + stable_unit(stage["seed"], index, 0xD3B3) * 8.0
        height_min, height_max = (dominant_min, dominant_max) if high_rise else (secondary_min, secondary_max)
        height = height_min + stable_unit(stage["seed"], index, 0xD3B4) * (height_max - height_min)
        # Inner face stays >=3m beyond the authoritative boundary.  The second
        # row is separated by the actual authored street band rather than an
        # arbitrary 1.4/4.8m offset.
        outset = half + 3.2 + depth / 2 + row * (street_depth * 0.62 + 4.0)
        yaw_jitter = (stable_unit(stage["seed"], index, 0xD3B5) - 0.5) * (0.10 + (composition_signature % 4) * 0.012)
        # Low foreground shoulders frame—not cover—the two measured landmark
        # vistas.  The outer row remains tall behind them, preserving density.
        north_landmark_corridor = side == 0 and row == 0 and abs(along - landmark_vistas[0]["x"]) < width * 0.74
        west_landmark_corridor = side == 1 and row == 0 and abs(along - landmark_vistas[1]["z"]) < width * 0.74
        if north_landmark_corridor or west_landmark_corridor:
            high_rise = False
            corridor_height = secondary_min + stable_unit(stage["seed"], index, 0xD3B6) * max(1.0, secondary_max - secondary_min)
            height = min(height, corridor_height)
        if side == 0:  # north, inward facade faces +Z
            x, z, yaw = along + jitter, -outset, yaw_jitter
        elif side == 1:  # west, inward facade faces +X
            x, z, yaw = -outset, along + jitter, -math.pi / 2 + yaw_jitter
        elif side == 2:  # east, inward facade faces -X
            x, z, yaw = outset, along - jitter, math.pi / 2 + yaw_jitter
        else:  # south, inward facade faces -Z
            x, z, yaw = along - jitter, outset, math.pi + yaw_jitter
        if (
            stage["id"] == "kairou"
            and side == 3
            and row == 0
            and abs(x) < 64.0
        ):
            # The reference-specific two-depth bazaar owns this northward
            # vanishing-point frontage. Avoid spatially overlapping a generic
            # city parcel with it; the outer row still supplies parallax.
            continue
        add_dense_city_building(builder, stage, lod, index, x, z, width, depth, height, yaw, high_rise)




def add_abbey_visual(builder, stage, lod):
    """Model the visible Gothic shell over the playable abbey collision plan."""
    if not any(box.get("district") == "abbey" for box in stage["boxes"]):
        return
    damaged = stage["id"] == "z04"
    rot = stage["seed"] & 3
    # StageLayout's abbey wall/tower boxes are the physics truth. The former
    # 1.28 hero-shot enlargement pushed roofs, spires and facade planes up to
    # 13m beyond those colliders, so players could visibly enter the shell.
    # Keep the combat-space shell 1:1; skyline scale now comes from the second
    # profile landmark and from vertical crowns, never footprint inflation.
    plan_scale = 1.0

    def point(lx, lz):
        lx *= plan_scale
        lz *= plan_scale
        if rot == 1:
            return lz, -lx
        if rot == 2:
            return -lx, -lz
        if rot == 3:
            return -lz, lx
        return lx, lz

    def gable(lx, lz, base_y, local_w, roof_h, local_d, key="accent"):
        x, z = point(lx, lz)
        if rot & 1:
            builder.add_gable_roof(x, base_y, z, local_d * plan_scale, roof_h, local_w * plan_scale, key, "z")
        else:
            builder.add_gable_roof(x, base_y, z, local_w * plan_scale, roof_h, local_d * plan_scale, key, "x")

    def gable_cross(lx, lz, base_y, local_w, roof_h, local_d, key="accent"):
        """Perpendicular roof used by the cathedral transept."""
        x, z = point(lx, lz)
        if rot & 1:
            builder.add_gable_roof(x, base_y, z, local_w * plan_scale, roof_h, local_d * plan_scale, key, "x")
        else:
            builder.add_gable_roof(x, base_y, z, local_d * plan_scale, roof_h, local_w * plan_scale, key, "z")

    def facade_panel(lx, lz, y, width, height, local_plane="x", key="glass"):
        """Seat a framed Gothic lancet directly on an existing solid wall."""
        x, z = point(lx, lz)
        plane_x = (local_plane == "x") != bool(rot & 1)
        scaled_width = width * plan_scale
        if plane_x:
            builder.add_box(x, y, z, 0.10, height, scaled_width, key)
        else:
            builder.add_box(x, y, z, scaled_width, height, 0.10, key)
        if lod != 0:
            return
        # Two jambs and a pointed head.  These are sub-20cm facade strips,
        # never separate cover or invisible collision.
        if local_plane == "x":
            low_a = point(lx, lz - width * 0.52)
            low_b = point(lx, lz + width * 0.52)
        else:
            low_a = point(lx - width * 0.52, lz)
            low_b = point(lx + width * 0.52, lz)
        for px, pz in (low_a, low_b):
            builder.add_beam((px, y - height * 0.48, pz), (px, y + height * 0.20, pz), 0.09, 0.08, "trim")
        apex = point(lx, lz)
        builder.add_beam((low_a[0], y + height * 0.20, low_a[1]), (apex[0], y + height * 0.50, apex[1]), 0.10, 0.08, "trim")
        builder.add_beam((low_b[0], y + height * 0.20, low_b[1]), (apex[0], y + height * 0.50, apex[1]), 0.10, 0.08, "trim")

    # Nave and east-hall roof masses.  The ruined variant exposes rafters and
    # leaves a large broken section instead of merely recolouring the castle.
    if not damaged or lod > 0:
        gable(-28, 0, 16.05, 36.5, 11.5, 25.5, "accent")
    else:
        gable(-35.5, 0, 16.05, 17.5, 10.8, 25.5, "accent")
        for index in range(7):
            lx = -25 + index * 2.4
            a = point(lx, -11.8)
            b = point(lx + (2.8 if index % 2 else -1.4), 4.8)
            builder.add_beam((a[0], 16.2, a[1]), (b[0], 21.2 - index * 0.32, b[1]), 0.16, 0.14, "trim")
    gable_cross(-28, 0, 16.08, 18.0, 9.2, 30.0, "trim" if damaged else "accent")
    gable(31, 0, 12.1, 24.0, 7.6, 28.0, "trim" if damaged else "accent")

    # Four corner spires and the dominant central bell tower.
    segments = 12 if lod == 0 else 8
    for tower_index, (lx, lz) in enumerate(((-41, -31), (-41, 31), (41, -31), (41, 31))):
        x, z = point(lx, lz)
        spire_h = 16.5 if not damaged else (7.5 if tower_index == 1 else 13.0)
        # The collar's own top is 17.7 + 0.38/2 = 17.89; the spire cone's
        # base must sit exactly there. It previously started at a fixed 18.0
        # regardless of the collar, leaving a constant 0.11 m gap between
        # every corner spire and its own collar -- small, but real (measured
        # via tools/blender/a23/orphan.py's contact_gap) and, at FPS
        # distance with a strong sun, visible as a floating cone with a
        # shadow underneath (measurementDefect3 / fake-contact class).
        collar_top = 17.7 + 0.38 / 2
        if damaged and tower_index == 2 and lod == 0:
            builder.add_beam((x - 2.5, 18.2, z - 2), (x + 3.4, 23.0, z + 2.4), 0.28, 0.24, "trim")
        else:
            builder.add_cylinder(x, collar_top + spire_h / 2, z, 7.2, spire_h, "accent", segments, 0.16)
        builder.add_box(x, 17.7, z, 11.2 * plan_scale, 0.38, 11.2 * plan_scale, "trim")
        if lod == 0:
            for face in (-1, 1):
                if rot & 1:
                    builder.add_box(x, 12.5, z + face * 5.62 * plan_scale, 1.35, 5.2, 0.10, "emissive" if damaged else "glass")
                else:
                    builder.add_box(x + face * 5.62 * plan_scale, 12.5, z, 0.10, 5.2, 1.35, "emissive" if damaged else "glass")

    central_x, central_z = point(14, 0)
    # The central belfry is the stage-scale reference: a 54m silhouette in the
    # normal map and a visibly sheared 43m crown in the ruined map.
    builder.add_box(central_x, 22.0, central_z, 17.0, 20.0, 17.0, "wall_alt")
    builder.add_box(central_x, 33.2, central_z, 14.8, 3.0, 14.8, "trim")
    central_spire_h = 20.0 if not damaged else 11.0
    builder.add_cylinder(
        central_x,
        34.5 + central_spire_h / 2,
        central_z,
        10.2,
        central_spire_h,
        "accent",
        12 if lod == 0 else 8,
        0.22 if not damaged else 2.6,
    )
    builder.add_cylinder(central_x, 48.0 if not damaged else 42.0, central_z, 0.30, 9.0 if not damaged else 4.0, "trim", 8, 0.08)

    # Belfry openings, corner pinnacles and cathedral front windows turn the
    # large masses into readable architecture at FPS distance.
    if lod <= 1:
        for local_plane, (lx, lz) in (("x", (14, -6.68)), ("x", (14, 6.68)), ("z", (7.32, 0)), ("z", (20.68, 0))):
            facade_panel(lx, lz, 25.2, 3.0, 7.6, local_plane, "emissive" if damaged else "glass")
        for ox, oz in ((-7.2, -7.2), (-7.2, 7.2), (7.2, -7.2), (7.2, 7.2)):
            px, pz = point(14 + ox / plan_scale, oz / plan_scale)
            builder.add_cylinder(px, 36.8, pz, 1.18, 9.0 if not damaged else 5.6, "accent", 8, 0.10)
        facade_panel(-44.55, 0, 10.4, 9.0, 9.5, "x", "emissive" if damaged else "glass")
        facade_panel(41.55, 0, 8.1, 7.2, 7.0, "x", "emissive" if damaged else "glass")

    if lod == 0:
        # Dormers and chimneys give the roof line a human construction scale.
        for index, lx in enumerate((-39, -33, -27, -21, -15)):
            for lz in (-9.8, 9.8):
                dx, dz = point(lx, lz)
                builder.add_box(dx, 18.6 + (index % 2) * 0.35, dz, 1.55, 2.7, 1.25, "wall_alt")
                builder.add_cylinder(dx, 21.2, dz, 1.20, 2.6, "accent", 8, 0.10)

    if lod == 0:
        # Flying-buttress rhythm seated against the nave walls.
        for lx in (-40, -34, -28, -22, -16):
            for lz in (-12.4, 12.4):
                outer = point(lx, lz + (2.8 if lz > 0 else -2.8))
                inner = point(lx, lz)
                builder.add_beam((outer[0], 1.0, outer[1]), (inner[0], 11.8, inner[1]), 0.22, 0.20, "trim")
                builder.add_box(outer[0], 2.1, outer[1], 0.92, 4.2, 0.92, "wall_alt")
        # Stained window bands are flush with real walls and illuminate the
        # nave without becoming collider-free cover.
        for lx in (-39, -33, -27, -21, -15):
            for lz in (-11.56, 11.56):
                x, z = point(lx, lz)
                if rot & 1:
                    builder.add_box(x, 10.2, z, 0.10, 4.6, 1.2, "emissive" if damaged else "glass")
                else:
                    builder.add_box(x, 10.2, z, 1.2, 4.6, 0.10, "emissive" if damaged else "glass")
        # Low crenellation trim along the outer walks; 22cm height avoids a
        # misleading invisible gameplay obstacle.
        for index in range(-10, 11):
            for lz in (-35.9, 35.9):
                x, z = point(index * 4.0, lz)
                builder.add_box(x, 8.18, z, 2.1 if not (rot & 1) else 0.40, 0.22, 0.40 if not (rot & 1) else 2.1, "trim")
        for index in range(-7, 8):
            for lx in (-45.9, 45.9):
                x, z = point(lx, index * 4.0)
                builder.add_box(x, 8.18, z, 0.40 if not (rot & 1) else 2.1, 0.22, 2.1 if not (rot & 1) else 0.40, "trim")


def add_pipe_rack(builder, x, z, span=22, height=9, pipes=3):
    for sx in (-span / 2, span / 2):
        builder.add_box(x + sx, height / 2, z, 0.65, height, 0.65, "trim")
    builder.add_beam((x - span / 2, height, z), (x + span / 2, height, z), 0.45, 0.45, "trim")
    for pipe in range(pipes):
        offset = (pipe - (pipes - 1) / 2) * 1.2
        builder.add_beam((x - span / 2, height - 1.2, z + offset), (x + span / 2, height - 1.2, z + offset), 0.22, 0.22, "accent" if pipe == 0 else "obstacle")


def add_ground_character(builder, stage, lod):
    if lod == 2:
        return
    surface = PROFILES[stage["id"]]["surface"]
    size = stage["size"]
    seed = stage["seed"]
    half = size / 2

    if surface == "abbey-causeway":
        # Broad dry-set cobble lanes and rain pockets.  They share the runtime
        # collision plane, so the imported layer cannot snag player movement.
        for index in range(-9 if lod == 0 else -5, 10 if lod == 0 else 6):
            offset = index * size * 0.034
            builder.add_box(offset, 0.036, 0, 0.075, 0.012, size * 0.68, "trim")
            builder.add_box(0, 0.037, offset, size * 0.68, 0.012, 0.075, "trim")
        for index in range(13 if lod == 0 else 6):
            x = (stable_unit(seed, index, 0xA11) - 0.5) * size * 0.62
            z = (stable_unit(seed, index, 0xA12) - 0.5) * size * 0.62
            builder.add_box(x, 0.041, z, 2.4 + index % 4, 0.012, 1.1 + index % 3, "water")
    elif surface in {"range-concrete", "compact-range", "airport-apron", "checkpoint-wet-road"}:
        stripe_count = 11 if lod == 0 else 6
        for index in range(stripe_count):
            offset = -half * 0.36 + index * half * 0.072
            builder.add_box(offset, 0.042, half * 0.20, 0.22, 0.018, size * 0.34, "accent")
        if stage["id"] == "kunren":
            # Three seated blast-test pads replace the empty/debug-grid read
            # without inventing new cover or changing the authoritative floor.
            # Their 14 mm surface layer sits directly on the gameplay plane;
            # sparse red stop bars retain the military range identity.
            for bay in (-1, 0, 1):
                bay_x = bay * half * 0.29
                builder.add_box(
                    bay_x, 0.041, half * 0.18,
                    half * 0.18, 0.014, size * 0.27, "road",
                )
                builder.add_box(
                    bay_x, 0.050, half * 0.045,
                    half * 0.16, 0.014, 0.52, "accent",
                )
        if surface == "airport-apron":
            builder.add_cylinder(-half * 0.12, 0.046, -half * 0.05, 14, 0.018, "accent", 32 if lod == 0 else 16)
            builder.add_cylinder(-half * 0.12, 0.049, -half * 0.05, 10, 0.02, "road", 32 if lod == 0 else 16)
    elif surface in {"wet-logistics", "harbor-concrete", "neon-wet-street", "ruined-wet-asphalt", "wrecked-dock"}:
        puddle_count = 18 if lod == 0 else 8
        for index in range(puddle_count):
            x = (stable_unit(seed, index, 0x311) - 0.5) * size * 0.72
            z = (stable_unit(seed, index, 0x312) - 0.5) * size * 0.72
            width = 3.0 + stable_unit(seed, index, 0x313) * 9.0
            depth = 1.6 + stable_unit(seed, index, 0x314) * 5.0
            builder.add_box(x, 0.038, z, width, 0.012, depth, "water")
        if surface in {"harbor-concrete", "wrecked-dock"}:
            # A shallow flooded service dock catches the sky and crane lights
            # in first-person views while retaining the authoritative runtime
            # floor/collision below it.
            basin_z = -half * 0.34
            basin_x = half * (0.22 if stage["seed"] & 1 else -0.22)
            builder.add_box(basin_x, 0.032, basin_z, half * 0.42, 0.016, half * 0.18, "water")
            builder.add_box(basin_x, 0.07, basin_z - half * 0.095, half * 0.46, 0.14, 0.42, "trim")
            builder.add_box(basin_x, 0.07, basin_z + half * 0.095, half * 0.46, 0.14, 0.42, "trim")
    elif surface in {"palace-stone", "desert-stone", "cathedral-stone", "subway-tile", "onsen-stone"}:
        line_count = 13 if lod == 0 else 7
        for index in range(-line_count, line_count + 1):
            offset = index * size / (line_count * 2.7)
            builder.add_box(offset, 0.035, 0, 0.045, 0.012, size * 0.72, "trim")
            builder.add_box(0, 0.036, offset, size * 0.72, 0.012, 0.045, "trim")
        if surface == "palace-stone":
            builder.add_box(half * 0.24, 0.045, -half * 0.18, half * 0.28, 0.025, half * 0.16, "water")
        elif surface == "onsen-stone":
            for x in (-half * 0.22, half * 0.20):
                builder.add_box(x, 0.05, -half * 0.28, half * 0.20, 0.028, half * 0.13, "water")
    elif surface == "rail-ballast":
        for track in (-half * 0.18, 0, half * 0.18):
            builder.add_beam((-half * 0.45, 0.11, track - 0.72), (half * 0.45, 0.11, track - 0.72), 0.07, 0.09, "trim")
            builder.add_beam((-half * 0.45, 0.11, track + 0.72), (half * 0.45, 0.11, track + 0.72), 0.07, 0.09, "trim")
    elif surface in {"rice-terraces", "lakeside-stone"}:
        for band in range(4 if lod == 0 else 2):
            z = -half * 0.34 + band * half * 0.19
            builder.add_box(half * 0.28, -0.025, z, half * 0.34, 0.045, half * 0.12, "water")
    elif surface in {"lava-mine-floor", "volcanic-fortress"}:
        for index in range(5 if lod == 0 else 3):
            x0 = -half * 0.42 + index * half * 0.19
            bend = (stable_unit(seed, index, 0xF1) - 0.5) * half * 0.12
            builder.add_beam((x0, 0.06, -half * 0.46), (x0 + bend, 0.06, half * 0.46), 0.28, 0.05, "emissive")
    else:
        patch_count = 20 if lod == 0 else 10
        for index in range(patch_count):
            x = (stable_unit(seed, index, 0x201) - 0.5) * size * 0.78
            z = (stable_unit(seed, index, 0x202) - 0.5) * size * 0.78
            radius = 1.8 + stable_unit(seed, index, 0x203) * 4.0
            builder.add_cylinder(x, 0.025, z, radius, 0.018, "natural", 8 if lod == 0 else 6)


def add_stage_dressing(builder, stage, lod):
    if lod == 2:
        return
    profile = PROFILES[stage["id"]]
    dressing = profile["dressing"]
    size = stage["size"]
    half = size / 2
    edge = half + 13
    seed = stage["seed"]
    detail = lod == 0

    if dressing in {"range-targets", "close-range-drills"}:
        add_hangar(builder, -half * 0.48, -edge, 30 if detail else 24, 19, 9, "wall_alt")
        add_hangar(builder, half * 0.16, -edge - 2, 34 if detail else 26, 20, 10, "wall")
        add_hangar(builder, half * 0.60, -edge + 1, 25, 16, 8, "wall_alt")
        add_vehicle_silhouette(builder, -half * 0.12, -half * 0.44, 6.4, 3.0, 2.1)
        if detail:
            add_vehicle_silhouette(builder, half * 0.42, -half * 0.42, 7.2, 3.2, 2.4)
        tree_count = 34 if detail else 18
        for index in range(tree_count):
            angle = math.tau * index / tree_count + stable_unit(seed, index, 0x501) * 0.08
            radius = half + 22 + stable_unit(seed, index, 0x502) * 22
            add_tree(builder, math.cos(angle) * radius, math.sin(angle) * radius, 7 + stable_unit(seed, index, 0x503) * 9, seed + index, True, lod)
        if detail:
            add_gabled_house(builder, -half * 0.28, -edge + 8, 12, 8, 1, "industrial", lod)
            add_gabled_house(builder, half * 0.34, -edge + 6, 10, 7, 1, "industrial", lod)
    elif dressing in {"containers", "dock-equipment", "wreckage"}:
        for index in range(5 if detail else 3):
            add_container_stack(builder, -half * 0.54 + index * half * 0.25, -edge, 2 + index % 2, 2 + (index + 1) % 2)
        if dressing in {"dock-equipment", "wreckage"}:
            # Two additional portal cranes make the harbor identity readable
            # from oblique player spawns instead of only from the QA camera.
            crane_count = 2 if detail else 1
            for crane_index in range(crane_count):
                crane_x = (-0.52 + crane_index * 1.04) * half
                crane_z = -half - 5 - crane_index * 4
                crane_height = 24 if detail else 18
                crane_span = 22 if detail else 17
                for sx in (-crane_span / 2, crane_span / 2):
                    builder.add_beam(
                        (crane_x + sx, 0, crane_z - 4),
                        (crane_x + sx * 0.88, crane_height, crane_z),
                        0.62,
                        0.62,
                        "trim",
                    )
                builder.add_beam(
                    (crane_x - crane_span / 2, crane_height, crane_z),
                    (crane_x + crane_span / 2, crane_height, crane_z),
                    0.76,
                    0.76,
                    "accent" if dressing == "dock-equipment" else "wall_alt",
                )
                builder.add_beam(
                    (crane_x, crane_height, crane_z),
                    (crane_x + crane_span * 0.74, crane_height - 2.6, crane_z),
                    0.44,
                    0.44,
                    "trim",
                )
            add_gabled_house(builder, 0, -edge - 5, 28 if detail else 20, 15, 2 if detail else 1, "industrial", lod, dressing == "wreckage")
            add_workboat(builder, -half * 0.30, -half - 25, 20 if detail else 15, lod, dressing == "wreckage")
            if detail:
                add_workboat(builder, half * 0.30, -half - 34, 15, lod, dressing == "wreckage")
    elif dressing in {"courtyard-gardens", "bamboo-shrine", "irrigation-village", "baths-and-lanterns"}:
        tree_count = (12 if detail else 8) if dressing == "bamboo-shrine" else (24 if detail else 12)
        for index in range(tree_count):
            angle = math.tau * index / tree_count + stable_unit(seed, index, 0x601) * 0.12
            radius = half + 7 + stable_unit(seed, index, 0x602) * 18
            height = 6 + stable_unit(seed, index, 0x603) * 10
            if dressing == "bamboo-shrine":
                add_bamboo(builder, math.cos(angle) * radius, math.sin(angle) * radius, height, seed + index, lod)
            else:
                add_tree(builder, math.cos(angle) * radius, math.sin(angle) * radius, height, seed + index, False, lod)
        for offset in (-half * 0.46, 0, half * 0.46):
            add_arch(builder, offset, 0, -edge, 14, 9, 2.5, "wall")
        house_style = "heritage" if dressing in {"courtyard-gardens", "baths-and-lanterns"} else "timber"
        house_count = 7 if detail else 4
        for index in range(house_count):
            hx = (index - (house_count - 1) / 2) * half * 0.20
            hz = -edge - 7 - abs(index - house_count // 2) * 1.8
            add_gabled_house(
                builder,
                hx,
                hz,
                10 + (index % 3) * 2.4,
                7.5 + (index % 2) * 1.8,
                2 if dressing == "baths-and-lanterns" and index % 2 == 0 else 1,
                house_style,
                lod,
            )
        lantern_count = 12 if detail else 6
        for index in range(lantern_count):
            lx = -half * 0.42 + index * half * 0.84 / max(1, lantern_count - 1)
            add_stone_lantern(builder, lx, -half * 0.38, 2.0 + (index % 3) * 0.18, dressing == "baths-and-lanterns")
        if dressing == "bamboo-shrine" and detail:
            for index in range(-4, 5):
                add_bamboo(
                    builder,
                    index * half * 0.085,
                    -half - 4 - abs(index % 3),
                    14 + index % 4,
                    seed + 900 + index,
                    lod,
                )
    elif dressing in {"abbey-town", "ruined-abbey-town"}:
        ruined = dressing == "ruined-abbey-town"
        # Dense but inaccessible outer borough on three shores.  It is placed
        # beyond the authored play boundary, while the 123x100m central abbey
        # itself remains the fully collidable/enterable combat space.
        house_count = 34 if detail else 17
        for index in range(house_count):
            side = index % 3
            lane = index // 3
            drift = (stable_unit(seed, index, 0xC21) - 0.5) * 7.0
            if side == 0:
                hx = -half * 0.76 + lane * half * 0.145 + drift
                hz = -edge - 8 - (lane % 4) * 4.5
            elif side == 1:
                hx = -edge - 8 - (lane % 4) * 4.4
                hz = -half * 0.72 + lane * half * 0.14 + drift
            else:
                hx = edge + 8 + (lane % 4) * 4.4
                hz = -half * 0.72 + lane * half * 0.14 - drift
            width = 8.2 + (index % 5) * 1.55
            depth = 6.8 + (index % 3) * 1.35
            storeys = 3 if index % 7 == 0 else 2 if index % 3 == 0 else 1
            add_gabled_house(builder, hx, hz, width, depth, storeys, "heritage", lod, ruined and index % 3 != 1)
            if detail and index % 5 == 0:
                # Chimney stacks break up repeated roof silhouettes.
                builder.add_box(hx + width * 0.24, storeys * 3.65 + 1.1, hz, 0.72, 2.2, 0.72, "trim")
        # Terraced retaining walls make the borough climb toward the abbey
        # instead of reading as one row of houses on an empty plane.
        for tier in range(4 if detail else 2):
            tier_width = size * (0.82 - tier * 0.08)
            tier_z = -half - 4.5 - tier * 7.2
            builder.add_box(0, 1.0 + tier * 0.35, tier_z, tier_width, 2.0 + tier * 0.7, 1.2, "wall_alt")
        add_arch(builder, 0, 0, -half - 4.5, 20, 15, 4.5, "wall_alt")
        marker_count = 22 if detail else 10
        for index in range(marker_count):
            mx = -half * 0.43 + index * half * 0.86 / max(1, marker_count - 1)
            mz = -half * 0.34 - (index % 3) * 2.0
            if ruined:
                builder.add_box(mx, 0.72, mz, 0.42, 1.44, 0.18, "wall")
                builder.add_box(mx, 1.18, mz, 0.86, 0.18, 0.20, "wall")
            else:
                add_stone_lantern(builder, mx, mz, 1.8 + (index % 2) * 0.25, False)
    elif dressing in {"colonnades", "cliff-fortress", "fortress-emplacements"}:
        for index in range(-4 if detail else -2, 5 if detail else 3):
            add_arch(builder, index * 12, 0, -edge, 10, 13 + abs(index) % 3 * 2, 3, "wall")
    elif dressing in {"armored-outpost", "research-modules", "bunkers", "ground-support"}:
        for index in range(-2, 3):
            add_hangar(builder, index * half * 0.23, -edge, 24 if detail else 19, 16, 8 + abs(index), "wall_alt")
        add_vehicle_silhouette(builder, half * 0.18, -half * 0.44, 8.5 if dressing == "ground-support" else 6.5, 3.2, 2.2)
    elif dressing in {"pipes-and-vats", "conveyors", "processing-lines", "heat-shields", "mine-equipment"}:
        rack_count = 5 if detail else 3
        for index in range(rack_count):
            add_pipe_rack(builder, -half * 0.45 + index * half * 0.23, -edge, 18, 8 + index % 3 * 2, 3)
            builder.add_cylinder(-half * 0.43 + index * half * 0.22, 6, -edge - 7, 3.5, 12, "wall_alt", 10 if detail else 6, 3.0)
    elif dressing in {"market-stalls", "closed-shops"}:
        for index in range(-5 if detail else -3, 6 if detail else 4):
            x = index * 10
            builder.add_box(x, 2.2, -edge, 8.5, 4.4, 5.5, "wall_alt")
            builder.add_box(x, 4.55, -edge + 2.5, 9.2, 0.3, 2.0, "accent" if index % 2 else "emissive")
        if detail:
            # Lightweight overhead market kit: canopies and hanging signs add
            # first-person density without introducing new collision volumes.
            for row, z in enumerate((-half * 0.24, half * 0.18)):
                for index in range(-5, 6):
                    x = index * half * 0.085 + (row * 2 - 1) * 2.5
                    builder.add_box(x, 3.7 + (index % 3) * 0.14, z, half * 0.075, 0.22, half * 0.055, "accent" if (index + row) % 3 == 0 else "wall_alt")
                    if index % 2 == 0:
                        builder.add_box(x, 4.8, z - half * 0.029, half * 0.035, 1.2, 0.10, "emissive")
            for index in range(-4, 5):
                add_gabled_house(
                    builder,
                    index * half * 0.115,
                    -edge - 8 - abs(index % 3),
                    9.0,
                    7.0,
                    2,
                    "heritage" if dressing == "market-stalls" else "industrial",
                    lod,
                    dressing == "closed-shops" and index % 3 == 0,
                )
    elif dressing in {"roof-mechanical", "urban-debris", "collapsed-arena", "vehicle-barricades", "park-wreckage", "graveyard-rubble"}:
        for index in range(9 if detail else 5):
            x = -half * 0.54 + index * half * 0.14
            height = 3 + stable_unit(seed, index, 0x701) * 8
            builder.add_box(x, height / 2, -edge, 7 + index % 3 * 2, height, 6, "wall_alt" if index % 2 else "obstacle")
            if detail and index % 2:
                builder.add_beam((x - 3, height + 0.4, -edge), (x + 4, height + 4, -edge + 2), 0.22, 0.22, "trim")
        if dressing != "roof-mechanical":
            house_count = 6 if detail else 3
            for index in range(house_count):
                add_gabled_house(
                    builder,
                    (index - (house_count - 1) / 2) * half * 0.22,
                    -edge - 9 - index % 2 * 3,
                    10 + index % 2 * 3,
                    8,
                    1 + index % 2,
                    "industrial",
                    lod,
                    True,
                )
    elif dressing in {"rail-yard", "piers-and-cabins"}:
        for index in range(-3, 4):
            x = index * half * 0.17
            add_hangar(builder, x, -edge, 20, 12, 7, "wall_alt")
            builder.add_beam((x - 8, 0.22, -half * 0.44), (x + 8, 0.22, -half * 0.44), 0.09, 0.08, "trim")
        if dressing == "rail-yard":
            add_train_car(builder, -half * 0.24, -half * 0.35, 26, lod, False)
            add_train_car(builder, half * 0.22, -half * 0.29, 22, lod, True)
            add_gabled_house(builder, 0, -edge - 8, 18, 10, 1, "industrial", lod)
        else:
            cabin_count = 6 if detail else 3
            for index in range(cabin_count):
                add_gabled_house(
                    builder,
                    (index - (cabin_count - 1) / 2) * half * 0.25,
                    -edge - 6 - index % 2 * 2,
                    9.5,
                    7.5,
                    1,
                    "timber",
                    lod,
                )
            add_workboat(builder, -half * 0.28, -half - 28, 16, lod, False)


def _add_legacy_landmark(builder, stage, lod):
    size = stage["size"]
    half = size / 2
    x, z, y = 0, -half - 10, 0
    landmark = IDENTITIES[stage["id"]][1]
    if landmark == "training-tower":
        x = -half * 0.58
        z = -half - 14
    detail = lod == 0
    medium = lod <= 1

    if landmark in {"grand-abbey", "ruined-abbey"}:
        # The playable abbey is centred in the TypeScript layout and receives
        # its exact Blender shell in add_abbey_visual; do not add a second
        # disconnected background castle here.
        return
    if landmark in {"range-radar", "polar-array"}:
        add_tower(builder, x, z, y, 24 if detail else 18, "wall_alt", "accent", 10)
        dish_y = 31 if detail else 24
        builder.add_cylinder(x, dish_y, z, 7 if detail else 5, 1.0, "accent", 14, 3.0)
        for i in range(0, 8 if detail else 4):
            angle = math.tau * i / (8 if detail else 4)
            builder.add_beam((x, dish_y, z), (x + math.cos(angle) * 7, dish_y + 2.4, z + math.sin(angle) * 7), 0.16, 0.16, "trim")
    elif landmark in {"container-crane", "harbor-crane", "quarry-conveyor", "wrecked-port"}:
        span = 34 if detail else 28
        height = 30 if detail else 23
        for sx in (-span / 2, span / 2):
            builder.add_beam((x + sx, y, z - 7), (x + sx, y + height, z - 2), 0.8, 0.8, "trim")
            builder.add_beam((x + sx, y, z + 7), (x + sx, y + height, z + 2), 0.8, 0.8, "trim")
        builder.add_beam((x - span / 2, y + height, z), (x + span / 2, y + height, z), 1.0, 1.0, "accent")
        builder.add_beam((x, y + height, z), (x + span * 0.65, y + height - 2, z), 0.6, 0.6, "trim")
    elif landmark in {"palace-dome", "ruined-cathedral"}:
        add_arch(builder, x, y, z, 24, 18, 8, "wall")
        builder.add_cylinder(x, 20, z, 9, 5, "accent", 16, 2.0)
        if detail:
            for sx in (-9, 9):
                add_tower(builder, x + sx, z, y, 20, "wall_alt", "accent", 8)
    elif landmark in {"desert-gate", "quarantine-gate", "subway-vault"}:
        add_arch(builder, x, y, z, 30, 20, 8, "wall_alt")
        if detail:
            for sx in (-11, -5.5, 0, 5.5, 11):
                builder.add_box(x + sx, 15, z - 4.1, 2.8, 3.5, 0.15, "emissive" if landmark == "quarantine-gate" else "accent")
    elif landmark in {"hill-fortress", "volcano-fortress", "burning-block"}:
        for level in range(3 if medium else 2):
            width = 38 - level * 9
            builder.add_box(x, 4 + level * 7, z, width, 7, 28 - level * 6, "wall_alt" if level % 2 else "wall")
        if detail:
            for sx in (-15, 15):
                add_tower(builder, x + sx, z, y, 25, "wall_alt", "emissive" if landmark != "hill-fortress" else "accent", 8)
    elif landmark in {"desert-rig", "refinery-stack", "lava-mine", "slaughter-stack"}:
        stacks = 4 if detail else 2
        for i in range(stacks):
            sx = x + (i - (stacks - 1) / 2) * 7
            h = 30 + i * 4
            builder.add_cylinder(sx, h / 2, z, 2.1, h, "trim", 10, 1.55)
            builder.add_cylinder(sx, h + 0.8, z, 2.6, 1.6, "emissive" if landmark != "desert-rig" else "accent", 10)
        builder.add_box(x, 4, z, 36, 8, 20, "wall_alt")
    elif landmark in {"neon-spire", "ruined-city"}:
        add_tower(builder, x, z, y, 50 if detail else 38, "wall_alt", "emissive", 12)
        if detail:
            for level in range(5):
                builder.add_box(x, 12 + level * 8, z - 3.0, 8 - level * 0.8, 1.0, 0.18, "emissive")
    elif landmark == "rooftop-helipad":
        builder.add_cylinder(x, 19, z, 19, 2.0, "wall", 20)
        builder.add_cylinder(x, 20.1, z, 13, 0.12, "accent", 20)
        builder.add_box(x, 9, z, 24, 18, 20, "wall_alt")
    elif landmark in {"bamboo-pagoda", "onsen-pagoda", "terrace-village"}:
        levels = 4 if detail else 3
        for level in range(levels):
            width = 26 - level * 4.5
            builder.add_box(x, 2.5 + level * 5, z, width * 0.72, 4.5, width * 0.62, "wall")
            builder.add_box(x, 5.0 + level * 5, z, width, 0.55, width * 0.82, "accent")
        builder.add_cylinder(x, levels * 5 + 4, z, 0.45, 8, "trim", 8, 0.1)
    elif landmark == "coastal-lighthouse":
        add_tower(builder, x, z, y, 38 if detail else 30, "wall", "emissive", 16)
        builder.add_cylinder(x, 42 if detail else 34, z, 6, 3.5, "glass", 16, 5.2)
    elif landmark == "rail-terminal":
        add_arch(builder, x, y, z, 34, 18, 12, "wall_alt")
        for track in (-6, 0, 6):
            builder.add_beam((x - 22, 0.3, z + track), (x + 22, 0.3, z + track), 0.12, 0.09, "trim")
    elif landmark == "canyon-bridge":
        for side in (-1, 1):
            builder.add_box(x + side * 14, 13, z, 5, 26, 8, "wall_alt")
        builder.add_beam((x - 18, 20, z), (x + 18, 20, z), 1.0, 1.0, "accent")
        builder.add_beam((x - 18, 12, z), (x + 18, 12, z), 1.4, 0.5, "wall")
    elif landmark == "lakeside-observatory":
        builder.add_cylinder(x, 9, z, 14, 4, "wall", 16, 12)
        builder.add_cylinder(x, 15, z, 11, 8, "accent", 16, 2)
    elif landmark == "airport-control":
        add_tower(builder, x, z, y, 44 if detail else 34, "wall_alt", "glass", 12)
        builder.add_cylinder(x, 47 if detail else 37, z, 8, 5, "glass", 12, 6)
    elif landmark == "broken-ferris-wheel":
        radius = 22 if detail else 16
        segments = 18 if detail else 10
        center_y = radius + 4
        for i in range(segments):
            a0 = math.tau * i / segments
            a1 = math.tau * (i + 1) / segments
            if detail and i in {3, 4, 11}:
                continue
            p0 = (x + math.cos(a0) * radius, center_y + math.sin(a0) * radius, z)
            p1 = (x + math.cos(a1) * radius, center_y + math.sin(a1) * radius, z)
            builder.add_beam(p0, p1, 0.5, 0.5, "trim")
            if i % 2 == 0:
                builder.add_beam((x, center_y, z), p0, 0.22, 0.22, "accent")
        builder.add_beam((x - 10, 0, z), (x, center_y, z), 0.8, 0.8, "wall_alt")
        builder.add_beam((x + 10, 0, z), (x, center_y, z), 0.8, 0.8, "wall_alt")
    elif landmark == "training-tower":
        height = 38 if detail else 29
        builder.add_box(x, height / 2, z, 9.5, height, 9.5, "wall_alt")
        builder.add_box(x, height - 6.2, z + 4.8, 7.4, 8.5, 0.22, "glass")
        builder.add_box(x, height + 0.65, z, 12.5, 1.3, 12.5, "accent")
        if detail:
            for level in range(1, 6):
                landing_y = level * 5.6
                builder.add_box(x - 5.6, landing_y, z + 5.2, 3.0, 0.32, 2.2, "trim")
                builder.add_beam(
                    (x - 6.8, landing_y - 4.2, z + 5.3),
                    (x - 4.4, landing_y, z + 5.3),
                    0.16,
                    0.16,
                    "trim",
                )
            builder.add_cylinder(x, height + 5.4, z, 0.22, 8.2, "trim", 8, 0.12)
    else:
        add_tower(builder, x, z, y, 32 if detail else 24, "wall_alt", "accent", 10)


def landmark_geometry_group(style):
    """Route a unique design label to a low-level construction grammar."""
    words = set(style.split("-"))
    if "severed" in words or {"ruined", "cathedral"}.issubset(words):
        return "ruined_heritage"
    if words & {"lift", "bridge", "aqueduct", "gate", "headframe", "hoist"}:
        return "bridge"
    if words & {"ferris", "arena", "ring", "observatory", "maze"}:
        return "radial"
    if words & {"hangar", "hall", "terminal", "station", "hospital", "lodge", "pen", "ryokan"}:
        return "hall"
    if words & {"furnace", "smelter", "drill", "crusher", "processing", "drydock", "storage"}:
        return "industrial"
    if words & {"spire", "tower", "arcology"} or any(word.endswith("tower") for word in words):
        return "vertical"
    if words & {"market", "bazaar", "megablock", "hotel", "exchange"}:
        return "megablock"
    if words & {"palace", "cathedral", "pagoda", "monastery", "sanctuary", "academy"}:
        return "heritage"
    return "fortress"


def add_catalog_landmark_signature(builder, stage, lod, placement, style, shell):
    """Preserve the authored identity of the first production rollout maps.

    The collision templates intentionally share a small set of reliable combat
    shells.  They must not also share one visual crown.  This pass converts the
    stage profile prose into large, supported, stage-specific silhouettes while
    keeping every new piece above the authoritative walls or visibly tied into
    their tower/upper-walk supports.
    """
    stage_id = stage["id"]
    landmark_id = placement["id"]
    if stage_id not in {"kunren", "souko", "nakaniwa"}:
        return

    centre_x = float(placement["cx"])
    centre_z = float(placement["cz"])
    entrance_x, entrance_z = (float(value) for value in placement["entrance"])
    forward_x = entrance_x - centre_x
    forward_z = entrance_z - centre_z
    forward_length = max(1e-6, math.hypot(forward_x, forward_z))
    forward_x /= forward_length
    forward_z /= forward_length
    right_x, right_z = forward_z, -forward_x
    yaw = math.atan2(-forward_x, forward_z)
    footprint_width = float(placement["width"])
    footprint_depth = float(placement["depth"])
    if abs(forward_x) >= abs(forward_z):
        lateral_span, forward_span = footprint_depth, footprint_width
    else:
        lateral_span, forward_span = footprint_width, footprint_depth
    height_limit = float(placement["height"])
    walls = [item for item in shell if item.get("landmarkPart") in {"wall", "interior"}]
    towers = [item for item in shell if item.get("landmarkPart") == "tower"]
    upper_walks = [item for item in shell if item.get("landmarkPart") == "upper-walk"]
    support_boxes = walls + towers + upper_walks
    wall_top = max((item["y"] + item["h"] / 2 for item in walls), default=8.0)

    def point(lateral, forward):
        return (
            centre_x + right_x * lateral + forward_x * forward,
            centre_z + right_z * lateral + forward_z * forward,
        )

    def local_box(item):
        """Project one axis-aligned combat box into landmark-local axes."""
        delta_x = float(item["x"]) - centre_x
        delta_z = float(item["z"]) - centre_z
        local_lateral = delta_x * right_x + delta_z * right_z
        local_forward = delta_x * forward_x + delta_z * forward_z
        lateral_extent = (
            abs(right_x) * float(item["w"]) + abs(right_z) * float(item["d"])
        ) / 2
        forward_extent = (
            abs(forward_x) * float(item["w"]) + abs(forward_z) * float(item["d"])
        ) / 2
        return local_lateral, local_forward, lateral_extent, forward_extent

    def overlapping_supports(lateral, forward, width, depth, parts=None):
        matches = []
        for item in support_boxes:
            if parts is not None and item.get("landmarkPart") not in parts:
                continue
            item_lateral, item_forward, item_lateral_extent, item_forward_extent = local_box(item)
            lateral_overlap = (
                width / 2 + item_lateral_extent - abs(lateral - item_lateral)
            )
            forward_overlap = (
                depth / 2 + item_forward_extent - abs(forward - item_forward)
            )
            if lateral_overlap >= 0.20 and forward_overlap >= 0.20:
                matches.append(item)
        return matches

    def supported_base(lateral, forward, width, depth, fallback=None, parts=None):
        matches = overlapping_supports(lateral, forward, width, depth, parts)
        if not matches:
            return wall_top if fallback is None else fallback
        return max(float(item["y"]) + float(item["h"]) / 2 for item in matches) - 0.16

    def support_connectors(
        lateral, base_y, forward, width, depth,
        key="wall_weathered", limit=4, parts=None,
    ):
        """Visibly join a raised mass to real collision-backed supports.

        Each connector remains horizontally inside an existing combat box and
        overlaps its top by 0.20 m.  It can therefore never create a new fake
        ground-level cover promise while still eliminating hovering roofs.
        """
        candidates = overlapping_supports(lateral, forward, width, depth, parts)
        candidates.sort(
            key=lambda item: (
                -float(item["y"]) - float(item["h"]) / 2,
                (float(item["x"]) - centre_x) ** 2 + (float(item["z"]) - centre_z) ** 2,
            )
        )
        used = []
        for item in candidates:
            item_top = float(item["y"]) + float(item["h"]) / 2
            if base_y - item_top <= 0.08:
                continue
            item_lateral, item_forward, item_lateral_extent, item_forward_extent = local_box(item)
            if any(
                abs(item_lateral - previous[0]) < 1.5
                and abs(item_forward - previous[1]) < 1.5
                for previous in used
            ):
                continue
            connector_w = max(0.65, min(1.25, item_lateral_extent * 0.48))
            connector_d = max(0.65, min(1.25, item_forward_extent * 0.48))
            connector_h = base_y - item_top + 0.36
            oriented_box(
                item_lateral,
                item_top - 0.18 + connector_h / 2,
                item_forward,
                connector_w,
                connector_h,
                connector_d,
                key,
            )
            used.append((item_lateral, item_forward))
            if len(used) >= limit:
                break

    def oriented_box(lateral, y, forward, width, height, depth, key):
        x, z = point(lateral, forward)
        builder.add_oriented_box(x, y, z, width, height, depth, yaw, key)

    def gable(lateral, base_y, forward, width, roof_height, depth, key="roof"):
        x, z = point(lateral, forward)
        builder.add_oriented_gable_roof(
            x, base_y, z, width, roof_height, depth, yaw, key,
        )

    def beam(a_lateral, a_y, a_forward, b_lateral, b_y, b_forward, width, depth, key="trim"):
        ax, az = point(a_lateral, a_forward)
        bx, bz = point(b_lateral, b_forward)
        builder.add_beam((ax, a_y, az), (bx, b_y, bz), width, depth, key)

    def sloped_panel(
        a_lateral, a_y, b_lateral, b_y,
        forward_start, forward_end, thickness, key="glass",
    ):
        a0_x, a0_z = point(a_lateral, forward_start)
        b0_x, b0_z = point(b_lateral, forward_start)
        b1_x, b1_z = point(b_lateral, forward_end)
        a1_x, a1_z = point(a_lateral, forward_end)
        builder.add_sloped_panel(
            (
                (a0_x, a_y, a0_z),
                (b0_x, b_y, b0_z),
                (b1_x, b_y, b1_z),
                (a1_x, a_y, a1_z),
            ),
            thickness,
            key,
        )

    def vertical_ring(lateral, centre_y, forward, radius, segments, key="trim"):
        for segment in range(segments):
            angle_a = math.tau * segment / segments
            angle_b = math.tau * (segment + 1) / segments
            beam(
                lateral + math.cos(angle_a) * radius,
                centre_y + math.sin(angle_a) * radius,
                forward,
                lateral + math.cos(angle_b) * radius,
                centre_y + math.sin(angle_b) * radius,
                forward,
                max(0.22, radius * 0.040),
                max(0.16, radius * 0.026),
                key,
            )

    detail = lod == 0

    if stage_id == "souko" and lod < 2:
        # All four production Souko tower colliders (two per landmark) receive
        # the same bounded logistics grammar.  Specs are derived from each
        # tagged tower face, so placement/template changes cannot strand the
        # rails in world space or turn them into independent cover.
        for tower in towers:
            for spec in souko_tower_face_specs(placement, tower, lod):
                oriented_box(
                    spec["lateral"], spec["y"], spec["forward"],
                    spec["w"], spec["h"], spec["d"], spec["key"],
                )

    if landmark_id == "kunren-kurogane-command-bastion":
        # A low, asymmetric C4ISR block grows from the rear wall ring.  The
        # open lattice radar replaces the rejected castle spires and remains
        # legible from both the firing lanes and the roof approach.
        block_w = lateral_span * 0.54
        block_d = forward_span * 0.28
        block_h = min(13.0, height_limit * 0.27)
        block_forward = -forward_span * 0.12
        block_base = supported_base(
            0, block_forward, block_w, block_d,
            parts={"wall", "interior", "upper-walk"},
        )
        support_connectors(
            0, block_base, block_forward, block_w, block_d,
            "wall_weathered", 4, {"wall", "interior", "upper-walk"},
        )
        oriented_box(0, block_base + block_h / 2, block_forward, block_w, block_h, block_d, "wall_cool")
        oriented_box(
            -block_w * 0.13, block_base + block_h + 1.10, block_forward - block_d * 0.06,
            block_w * 0.64, 2.20, block_d * 0.72, "wall_alt",
        )
        deck_y = block_base + block_h + 2.35
        oriented_box(0, deck_y, block_forward, block_w * 0.92, 0.46, block_d * 1.08, "trim")
        if lod <= 1:
            brace_count = 4 if detail else 2
            for brace_index in range(brace_count):
                side = -1 if brace_index % 2 == 0 else 1
                forward_offset = (-0.34 + (brace_index // 2) * 0.68) * block_d
                beam(
                    side * block_w * 0.48, block_base + 0.6, block_forward + forward_offset,
                    side * block_w * 0.35, block_base + block_h * 0.82, block_forward + forward_offset,
                    0.25, 0.20, "accent" if brace_index == 0 else "trim",
                )
        mast_y0 = deck_y + 0.23
        mast_h = max(5.5, height_limit - mast_y0 - 1.0)
        mast_x, mast_z = point(block_w * 0.12, block_forward)
        builder.add_cylinder(
            mast_x, mast_y0 + mast_h / 2, mast_z,
            0.28 if detail else 0.38, mast_h, "trim", 8, 0.12,
        )
        ring_radius = min(7.5, lateral_span * 0.14)
        ring_y = min(height_limit - ring_radius - 0.4, mast_y0 + mast_h * 0.70)
        vertical_ring(block_w * 0.12, ring_y, block_forward, ring_radius, 16 if detail else 10, "trim")
        if detail:
            # A second seated ring and eight spokes read as a built radar dish,
            # not thin red debug linework. Every spoke intersects the mast and
            # both rings, preserving one explicit support chain to the deck.
            vertical_ring(block_w * 0.12, ring_y, block_forward, ring_radius * 0.66, 14, "accent")
            for spoke in range(8):
                angle = math.tau * spoke / 8
                beam(
                    block_w * 0.12, ring_y, block_forward,
                    block_w * 0.12 + math.cos(angle) * ring_radius,
                    ring_y + math.sin(angle) * ring_radius,
                    block_forward,
                    0.18, 0.14, "accent" if spoke % 2 == 0 else "trim",
                )
        return

    if landmark_id == "kunren-hakuen-aerostat-hall":
        vault_width = lateral_span * 0.40
        vault_depth = forward_span * 0.76
        vault_height = min(15.0, height_limit * 0.27)
        ridge_anchors = []
        for side in (-1, 1):
            lateral = side * lateral_span * 0.225
            vault_forward = -forward_span * 0.02
            vault_base = supported_base(
                lateral, vault_forward, vault_width, vault_depth,
                parts={"wall", "interior", "upper-walk"},
            )
            support_connectors(
                lateral, vault_base, vault_forward, vault_width, vault_depth,
                "wall_cool", 4, {"wall", "interior", "upper-walk"},
            )
            gable(lateral, vault_base, vault_forward, vault_width, vault_height, vault_depth, "roof")
            ridge_y = vault_base + vault_height
            ridge_anchors.append((lateral, ridge_y, vault_forward))
            beam(
                lateral, ridge_y, -vault_depth * 0.50,
                lateral, ridge_y, vault_depth * 0.50,
                0.24 if detail else 0.34, 0.18, "trim",
            )
            rib_count = 6 if detail else 3
            for rib in range(rib_count):
                forward = (rib - (rib_count - 1) / 2) * vault_depth * 0.90 / max(1, rib_count - 1)
                beam(lateral - vault_width / 2, vault_base, forward, lateral, ridge_y, forward, 0.24, 0.20, "wall_cool")
                beam(lateral, ridge_y, forward, lateral + vault_width / 2, vault_base, forward, 0.24, 0.20, "wall_cool")
        # Two grounded collider towers carry the tether masts; diagonal stays
        # visually terminate at the twin ridges rather than in open air.
        ordered_towers = sorted(
            ((local_box(tower)[0], local_box(tower)[1], tower) for tower in towers),
            key=lambda item: item[0],
        )
        for tower_index, (mast_lateral, mast_forward, tower) in enumerate(ordered_towers[:2]):
            tower_top = float(tower["y"]) + float(tower["h"]) / 2
            mast_base = tower_top - 0.18
            mast_top = max(mast_base + 4.0, height_limit - 0.45)
            mast_height = mast_top - mast_base
            mast_x, mast_z = point(mast_lateral, mast_forward)
            builder.add_cylinder(
                mast_x, mast_base + mast_height / 2, mast_z,
                0.34 if detail else 0.44, mast_height, "trim", 8, 0.16,
            )
            nearest_ridge = min(ridge_anchors, key=lambda anchor: abs(anchor[0] - mast_lateral))
            beam(
                mast_lateral, mast_base + mast_height * 0.78, mast_forward,
                nearest_ridge[0], nearest_ridge[1], nearest_ridge[2],
                0.12, 0.10, "accent",
            )
        return

    if landmark_id == "souko-shiosai-stackhouse":
        # The two authored 7x7m towers are depth anchors, not the final hero
        # silhouette.  Two broad rack planes now seat on those towers and on
        # the collision-backed side walls at local lateral +/-32m.  All new
        # uprights start 18cm inside the 13m wall top; the occupied rack trays
        # and cargo therefore begin above traversal and never promise phantom
        # ground cover.  The result is a multi-storey logistics megastructure
        # with readable interior parallax instead of two thin needles.
        ordered_towers = sorted(
            ((local_box(tower)[0], local_box(tower)[1], tower) for tower in towers),
            key=lambda item: item[1],
        )
        rack_forwards = tuple(item[1] for item in ordered_towers[:2])
        if len(rack_forwards) != 2:
            raise RuntimeError("Souko stackhouse requires two authored tower supports")
        rack_forwards = tuple(sorted(rack_forwards))
        if lod <= 1:
            # Two human-scale hoist doors are flush with the real front wall
            # segments on either side of the protected 28m opening.
            for door_index, door_lateral in enumerate((-23.5, 23.5)):
                oriented_box(
                    door_lateral,
                    4.35,
                    forward_span / 2 + 0.66,
                    10.8,
                    7.1,
                    0.18,
                    "wall_alt",
                )
                oriented_box(
                    door_lateral,
                    8.15,
                    forward_span / 2 + 0.60,
                    12.4,
                    0.44,
                    1.15,
                    "accent" if door_index == 0 else "trim",
                )
                if lod == 0:
                    for rib in (-1, 0, 1):
                        oriented_box(
                            door_lateral + rib * 2.55,
                            4.35,
                            forward_span / 2 + 0.77,
                            0.18,
                            6.65,
                            0.16,
                            "wall_cool",
                        )
        rack_laterals = (-32.0, 0.0, 32.0)
        rack_base = SOUKO_STACKHOUSE_RACK_BASE_M
        rack_top = min(height_limit - 5.0, 59.0)
        level_sets = {
            0: (13.0, 22.0, 31.0, 40.0, 49.0, 58.0),
            1: (13.0, 28.0, 43.0, 58.0),
            2: (13.0, 35.5, 58.0),
        }
        rack_levels = level_sets[lod]
        column_section = 0.42 if lod == 0 else 0.56 if lod == 1 else 0.76
        chord_section = 0.34 if lod == 0 else 0.48 if lod == 1 else 0.68

        for row_index, rack_forward in enumerate(rack_forwards):
            for lateral in rack_laterals:
                beam(
                    lateral, rack_base, rack_forward,
                    lateral, rack_top, rack_forward,
                    column_section, column_section, "wall_cool",
                )
            for level_index, level_y in enumerate(rack_levels):
                beam(
                    rack_laterals[0], level_y, rack_forward,
                    rack_laterals[-1], level_y, rack_forward,
                    chord_section, chord_section,
                    "accent" if level_index in {1, len(rack_levels) - 2} else "trim",
                )
            brace_levels = range(len(rack_levels) - 1) if lod == 0 else range(0, len(rack_levels) - 1, 2)
            for bay_index, (left_lateral, right_lateral) in enumerate(((-32.0, 0.0), (0.0, 32.0))):
                for level_index in brace_levels:
                    lower = rack_levels[level_index]
                    upper = rack_levels[level_index + 1]
                    if (bay_index + level_index + row_index) % 2:
                        lower_lateral, upper_lateral = left_lateral, right_lateral
                    else:
                        lower_lateral, upper_lateral = right_lateral, left_lateral
                    beam(
                        lower_lateral, lower + 0.25, rack_forward,
                        upper_lateral, upper - 0.25, rack_forward,
                        0.20 if lod == 0 else 0.30,
                        0.16 if lod == 0 else 0.24,
                        "wall_weathered",
                    )

        # Longitudinal chords turn the two supported faces into a deep rack
        # volume.  LOD2 keeps only the roof/base connections needed to preserve
        # the portal silhouette at distance.
        tie_levels = rack_levels if lod == 0 else (rack_levels[0], rack_levels[-1])
        for lateral in rack_laterals:
            for level_y in tie_levels:
                beam(
                    lateral, level_y, rack_forwards[0],
                    lateral, level_y, rack_forwards[1],
                    chord_section, chord_section, "trim",
                )

        if lod <= 1:
            # Open maintenance catwalks sit on the entrance-facing rack chord
            # and expose a 1.1m rail scale against the 64m hero.  They remain
            # far above traversal and connect directly to the supported frame.
            catwalk_levels = (31.0, 49.0) if lod == 0 else (35.5,)
            entrance_row = rack_forwards[1]
            for catwalk_index, catwalk_y in enumerate(catwalk_levels):
                oriented_box(
                    0,
                    catwalk_y + 0.24,
                    entrance_row + 4.45,
                    60.0,
                    0.48,
                    1.8,
                    "wall_weathered",
                )
                beam(
                    -29.5,
                    catwalk_y + 1.38,
                    entrance_row + 5.25,
                    29.5,
                    catwalk_y + 1.38,
                    entrance_row + 5.25,
                    0.10 if lod == 0 else 0.16,
                    0.10 if lod == 0 else 0.16,
                    "accent" if catwalk_index == 0 else "trim",
                )
                post_count = 9 if lod == 0 else 5
                for post_index in range(post_count):
                    post_lateral = -29.5 + post_index * 59.0 / max(1, post_count - 1)
                    beam(
                        post_lateral,
                        catwalk_y + 0.30,
                        entrance_row + 5.25,
                        post_lateral,
                        catwalk_y + 1.43,
                        entrance_row + 5.25,
                        0.08 if lod == 0 else 0.13,
                        0.08 if lod == 0 else 0.13,
                        "trim",
                    )

        # Occupied pallet bays supply the dark internal depth that was absent
        # from A17.  Every pod sits on a rack chord at or above 13m; staggered
        # omissions keep sky and cross-bracing visible through the skeleton.
        cargo_levels = (
            (13.35, 5.6), (22.35, 5.8), (31.35, 5.6),
            (40.35, 5.4), (49.35, 5.2),
        ) if lod == 0 else ((13.45, 6.0), (35.95, 6.0)) if lod == 1 else ((35.95, 6.2),)
        cargo_laterals = (-20.0, -7.0, 7.0, 20.0)
        for row_index, rack_forward in enumerate(rack_forwards):
            for level_index, (cargo_bottom, cargo_height) in enumerate(cargo_levels):
                for bay_index, cargo_lateral in enumerate(cargo_laterals):
                    if (row_index * 3 + level_index + bay_index) % (5 if lod == 0 else 3) == 1:
                        continue
                    cargo_width = 10.4 + ((row_index + bay_index) % 2) * 1.2
                    cargo_depth = 7.2 if lod == 0 else 8.4
                    oriented_box(
                        cargo_lateral,
                        cargo_bottom + cargo_height / 2,
                        rack_forward,
                        cargo_width,
                        cargo_height,
                        cargo_depth,
                        "wall_warm" if (level_index + bay_index) % 3 == 0 else "wall_alt",
                    )
                    if lod == 0 and (level_index + bay_index) % 4 == 0:
                        oriented_box(
                            cargo_lateral,
                            cargo_bottom + cargo_height * 0.62,
                            rack_forward + cargo_depth / 2 + 0.10,
                            cargo_width * 0.72,
                            0.52,
                            0.22,
                            "accent",
                        )

        if lod <= 1:
            # The reference is not an exposed pallet rack alone: tall process
            # houses interrupt its steel cage and create the alternating
            # opaque/open/opaque rhythm of a castle-scale bonded warehouse.
            # Every block begins on a rack tray at 12.82m or 21.82m, and the
            # two largest cores envelop the real authored tower supports.
            process_specs = (
                (-21.5, -20.0, 16.0, 17.0, rack_base, 49.0, "wall_weathered"),
                (0.0, -27.0, 19.0, 18.0, rack_base, 59.0, "wall_cool"),
                (20.0, -10.0, 15.0, 15.0, 21.82, 53.0, "wall_alt"),
                (-16.0, 17.0, 18.0, 18.0, 21.82, 57.0, "wall_weathered"),
                (4.0, 27.0, 20.0, 17.0, rack_base, 62.2, "wall_cool"),
            )
            selected_process_specs = process_specs if lod == 0 else (
                process_specs[0], process_specs[1], process_specs[4],
            )
            for process_index, (
                process_lateral,
                process_forward,
                process_width,
                process_depth,
                process_bottom,
                process_top,
                process_key,
            ) in enumerate(selected_process_specs):
                process_height = process_top - process_bottom
                oriented_box(
                    process_lateral,
                    process_bottom + process_height / 2,
                    process_forward,
                    process_width,
                    process_height,
                    process_depth,
                    process_key,
                )
                oriented_box(
                    process_lateral,
                    process_top + 0.24,
                    process_forward,
                    process_width + 1.1,
                    0.48,
                    process_depth + 1.1,
                    "roof",
                )

                # Deep facade ledges and off-centre risers give construction
                # scale without falling back to a repeated window grid.
                belt_count = 4 if lod == 0 else 2
                entrance_face = process_forward + process_depth / 2 + 0.14
                for belt_index in range(belt_count):
                    belt_y = process_bottom + (
                        belt_index + 1
                    ) * process_height / (belt_count + 1)
                    oriented_box(
                        process_lateral,
                        belt_y,
                        entrance_face,
                        process_width + 0.75,
                        0.30 if lod == 0 else 0.42,
                        0.28,
                        "accent" if belt_index == 1 and process_index % 2 == 0 else "trim",
                    )
                riser_count = 3 if lod == 0 else 1
                for riser_index in range(riser_count):
                    riser_lateral = process_lateral + (
                        riser_index - (riser_count - 1) / 2
                    ) * process_width * 0.58 / max(1, riser_count - 1)
                    riser_x, riser_z = point(riser_lateral, entrance_face + 0.06)
                    builder.add_cylinder(
                        riser_x,
                        process_bottom + process_height * 0.54,
                        riser_z,
                        0.16 if riser_index != 1 else 0.22,
                        process_height * 0.82,
                        "accent" if riser_index == 0 and process_index in {1, 4} else "trim",
                        8 if lod == 0 else 6,
                        0.14,
                    )
                if lod == 0:
                    # One asymmetric maintenance balcony per process house.
                    balcony_y = process_bottom + process_height * (0.62 if process_index % 2 else 0.48)
                    balcony_lateral = process_lateral + (-1 if process_index % 2 else 1) * process_width * 0.18
                    oriented_box(
                        balcony_lateral,
                        balcony_y,
                        entrance_face + 0.70,
                        process_width * 0.58,
                        0.24,
                        1.55,
                        "wall_weathered",
                    )
                    beam(
                        balcony_lateral - process_width * 0.27,
                        balcony_y + 1.08,
                        entrance_face + 1.36,
                        balcony_lateral + process_width * 0.27,
                        balcony_y + 1.08,
                        entrance_face + 1.36,
                        0.08,
                        0.08,
                        "accent" if process_index == 1 else "trim",
                    )
                    for post_index in range(4):
                        post_lateral = balcony_lateral + (
                            post_index - 1.5
                        ) * process_width * 0.18
                        beam(
                            post_lateral,
                            balcony_y + 0.08,
                            entrance_face + 1.36,
                            post_lateral,
                            balcony_y + 1.12,
                            entrance_face + 1.36,
                            0.07,
                            0.07,
                            "trim",
                        )

        # The reference's central event is a transport bridge with real
        # section and interior bays.  Its 10.4m-high frame overlaps both tower
        # supports in plan and remains 22.8m above the declared headroom plane.
        bridge_bottom = SOUKO_STACKHOUSE_SKYBRIDGE_BOTTOM_M
        bridge_top = 46.20
        bridge_half_width = 5.35
        bridge_front = rack_forwards[1] + 2.8
        bridge_rear = rack_forwards[0] - 2.8
        bridge_depth = bridge_front - bridge_rear
        oriented_box(0, bridge_bottom + 0.38, 0, 11.0, 0.76, bridge_depth, "wall_alt")
        oriented_box(0, bridge_top - 0.34, 0, 11.4, 0.68, bridge_depth, "roof")
        bridge_frames = (-31.2, -15.6, 0.0, 15.6, 31.2)
        for frame_index, frame_forward in enumerate(bridge_frames):
            for side in (-1, 1):
                beam(
                    side * bridge_half_width, bridge_bottom + 0.2, frame_forward,
                    side * bridge_half_width, bridge_top - 0.2, frame_forward,
                    0.30 if lod == 0 else 0.44,
                    0.26 if lod == 0 else 0.38,
                    "wall_cool",
                )
            beam(
                -bridge_half_width, bridge_top - 0.24, frame_forward,
                bridge_half_width, bridge_top - 0.24, frame_forward,
                0.30 if lod == 0 else 0.46,
                0.26 if lod == 0 else 0.38,
                "trim",
            )
        for side in (-1, 1):
            beam(
                side * bridge_half_width, bridge_bottom + 0.45, bridge_rear,
                side * bridge_half_width, bridge_bottom + 0.45, bridge_front,
                0.34, 0.30, "trim",
            )
            beam(
                side * bridge_half_width, bridge_top - 0.50, bridge_rear,
                side * bridge_half_width, bridge_top - 0.50, bridge_front,
                0.34, 0.30, "accent" if side < 0 else "trim",
            )
            if lod <= 1:
                for segment in range(len(bridge_frames) - 1):
                    start_forward = bridge_frames[segment]
                    end_forward = bridge_frames[segment + 1]
                    if (segment + (1 if side > 0 else 0)) % 2:
                        start_y, end_y = bridge_bottom + 0.8, bridge_top - 0.8
                    else:
                        start_y, end_y = bridge_top - 0.8, bridge_bottom + 0.8
                    beam(
                        side * bridge_half_width, start_y, start_forward,
                        side * bridge_half_width, end_y, end_forward,
                        0.18 if lod == 0 else 0.28,
                        0.15 if lod == 0 else 0.22,
                        "wall_weathered",
                    )
        # Two enclosed transfer rooms interrupt the bridge lattice and reveal
        # its usable logistics depth without copying a repeated window grid.
        transfer_count = 2 if lod == 0 else 1
        for transfer_index in range(transfer_count):
            transfer_forward = (-10.8, 10.8)[transfer_index]
            oriented_box(
                0,
                bridge_bottom + 4.4,
                transfer_forward,
                7.8,
                6.6,
                10.6,
                "wall_cool" if transfer_index == 0 else "wall_warm",
            )
            oriented_box(
                -3.96,
                bridge_bottom + 4.7,
                transfer_forward,
                0.16,
                3.2,
                5.8,
                "glass",
            )

        # Roof crane rails and three machine houses create the irregular crown
        # visible in the reference while staying under the authored 64m limit.
        for lateral in (-25.0, 25.0):
            beam(lateral, 59.15, rack_forwards[0], lateral, 59.15, rack_forwards[1], 0.40, 0.36, "accent")
        machine_count = 3 if lod == 0 else 2 if lod == 1 else 1
        for machine_index in range(machine_count):
            machine_lateral = (-20.0, 0.0, 19.0)[machine_index]
            machine_forward = -17.0 + machine_index * 15.5
            machine_width = 10.5 if machine_index != 1 else 12.5
            oriented_box(machine_lateral, 61.0, machine_forward, machine_width, 4.0, 8.0, "wall_weathered")
            oriented_box(machine_lateral, 63.1, machine_forward, machine_width + 0.8, 0.30, 8.8, "roof")
        if lod == 0:
            # Supported high-level safety rails and a travelling hoist finish
            # the load path.  The cable ends above the inaccessible rack tray.
            for side in (-1, 1):
                beam(side * 28.5, 59.9, rack_forwards[0], side * 28.5, 59.9, rack_forwards[1], 0.10, 0.10, "accent")
            oriented_box(12.0, 56.8, 4.0, 4.2, 2.8, 4.6, "accent")
            hoist_x, hoist_z = point(12.0, 4.0)
            builder.add_cylinder(hoist_x, 52.8, hoist_z, 0.09, 6.8, "trim", 6, 0.06)
            # Knee-height pallets, drums and dunnage sit against the two real
            # entrance-wall segments. They reproduce the reference's near-
            # field logistics story without entering local +/-14m route space
            # or creating player-height collisionless cover.
            for cluster_index, cluster_lateral in enumerate((-25.5, 25.5)):
                cluster_forward = forward_span / 2 + 2.7
                for plank in (-1, 0, 1):
                    oriented_box(
                        cluster_lateral + plank * 1.45,
                        0.11 + cluster_index * 0.025,
                        cluster_forward,
                        1.18,
                        0.22,
                        2.35,
                        "wood",
                    )
                for runner in (-0.82, 0.82):
                    oriented_box(
                        cluster_lateral,
                        0.24,
                        cluster_forward + runner,
                        4.45,
                        0.14,
                        0.18,
                        "trim",
                    )
                drum_x, drum_z = point(
                    cluster_lateral + (-3.0 if cluster_index == 0 else 3.0),
                    cluster_forward - 0.45,
                )
                builder.add_cylinder(
                    drum_x,
                    0.46,
                    drum_z,
                    0.34,
                    0.92,
                    "accent" if cluster_index == 0 else "wall_warm",
                    10,
                    0.34,
                )
        return

    if landmark_id == "souko-amakado-customs-terminal":
        # Four building-scale /| teeth replace the rejected row of small
        # symmetric gables.  Opaque long slopes and pale FRP north-light drops
        # are separate closed volumes; every eave is linked to a tagged wall,
        # interior or upper-walk support and remains above the 9.87m shell top.
        bay_count = 4
        if lod <= 1:
            # Brick inspection wings receive deep, vertical loading doors on
            # the two real wall segments.  The central +/-14m arrival opening
            # remains completely empty at ground level.
            for door_index, door_lateral in enumerate((-30.0, 30.0)):
                oriented_box(
                    door_lateral,
                    3.75,
                    forward_span / 2 + 0.66,
                    12.0,
                    6.1,
                    0.18,
                    "wall_alt",
                )
                oriented_box(
                    door_lateral,
                    7.15,
                    forward_span / 2 + 0.57,
                    14.2,
                    0.50,
                    1.10,
                    "roof",
                )
                oriented_box(
                    door_lateral + (-4.2 if door_index == 0 else 4.2),
                    5.4,
                    forward_span / 2 + 0.78,
                    2.2,
                    1.05,
                    0.16,
                    "accent",
                )
                if lod == 0:
                    for rib in (-1, 0, 1):
                        oriented_box(
                            door_lateral + rib * 2.8,
                            3.75,
                            forward_span / 2 + 0.77,
                            0.16,
                            5.7,
                            0.15,
                            "trim",
                        )
        roof_left = -lateral_span * 0.445
        roof_right = lateral_span * 0.445
        bay_width = (roof_right - roof_left) / bay_count
        roof_forward_start = -forward_span * 0.405
        roof_forward_end = forward_span * 0.325
        roof_forward = (roof_forward_start + roof_forward_end) / 2
        roof_depth = roof_forward_end - roof_forward_start
        roof_base = SOUKO_CUSTOMS_ROOF_BASE_M
        tooth_rises = (10.8, 12.1, 11.3, 13.0)
        for bay in range(bay_count):
            left = roof_left + bay * bay_width
            right = left + bay_width
            peak_y = roof_base + tooth_rises[bay]
            support_connectors(
                (left + right) / 2,
                roof_base,
                roof_forward,
                bay_width * 0.96,
                roof_depth,
                "wall_weathered",
                3 if lod == 0 else 2,
                {"wall", "interior", "upper-walk"},
            )
            sloped_panel(
                left,
                roof_base,
                right - 0.42,
                peak_y,
                roof_forward_start,
                roof_forward_end,
                0.32 if lod == 0 else 0.44,
                "roof",
            )
            # The vertical north-light is joined 42cm inside the roof peak so
            # the two closed pieces overlap rather than leaving a light leak.
            oriented_box(
                right - 0.21,
                roof_base + (peak_y - roof_base) / 2,
                roof_forward,
                0.42,
                peak_y - roof_base,
                roof_depth,
                "glass",
            )
            beam(
                right - 0.20,
                peak_y - 0.12,
                roof_forward_start,
                right - 0.20,
                peak_y - 0.12,
                roof_forward_end,
                0.24 if lod == 0 else 0.34,
                0.20 if lod == 0 else 0.28,
                "trim",
            )
            beam(
                left,
                roof_base + 0.18,
                roof_forward_start,
                left,
                roof_base + 0.18,
                roof_forward_end,
                0.22 if lod == 0 else 0.34,
                0.18 if lod == 0 else 0.26,
                "wall_weathered",
            )
            if lod <= 1:
                purlin_count = 5 if lod == 0 else 2
                for purlin in range(purlin_count):
                    fraction = (purlin + 1) / (purlin_count + 1)
                    purlin_lateral = left + (right - 0.42 - left) * fraction
                    purlin_y = roof_base + (peak_y - roof_base) * fraction
                    beam(
                        purlin_lateral,
                        purlin_y,
                        roof_forward_start,
                        purlin_lateral,
                        purlin_y,
                        roof_forward_end,
                        0.12 if lod == 0 else 0.20,
                        0.10 if lod == 0 else 0.16,
                        "wall_cool",
                    )
                # Tooth profile frames at both ends prove that the roof is a
                # deep terminal field, not four decorative facade triangles.
                for end_forward in (roof_forward_start, roof_forward_end):
                    beam(left, roof_base, end_forward, right - 0.42, peak_y, end_forward, 0.20, 0.16, "trim")
                    beam(right - 0.42, peak_y, end_forward, right - 0.42, roof_base, end_forward, 0.20, 0.16, "trim")
                # A front FRP clerestory and work-light line give the terminal
                # a human-readable occupied section in entrance views.  Both
                # pieces overlap the front tooth frame and sit above 11.2m.
                oriented_box(
                    (left + right) / 2,
                    roof_base + 3.05,
                    roof_forward_end + 0.10,
                    bay_width * 0.60,
                    4.4,
                    0.20,
                    "glass",
                )
                oriented_box(
                    (left + right) / 2,
                    roof_base + 0.72,
                    roof_forward_end + 0.23,
                    bay_width * 0.66,
                    0.18,
                    0.18,
                    "emissive" if lod == 0 and bay in {1, 2} else "accent",
                )

        if lod <= 1:
            # Two collision-seated maintenance walks expose a 1.1m handrail
            # scale across the broad terminal facade. Their inner ends stop at
            # local +/-18m, leaving the 28m opening plus a 4m visual margin.
            facade_forward = forward_span / 2 + 0.72
            for walk_index, walk_lateral in enumerate((-29.5, 29.5)):
                walk_width = 23.0
                walk_y = 9.15
                oriented_box(
                    walk_lateral,
                    walk_y,
                    facade_forward,
                    walk_width,
                    0.24 if lod == 0 else 0.34,
                    1.42,
                    "wall_weathered",
                )
                beam(
                    walk_lateral - walk_width / 2 + 0.4,
                    walk_y + 1.10,
                    facade_forward + 0.64,
                    walk_lateral + walk_width / 2 - 0.4,
                    walk_y + 1.10,
                    facade_forward + 0.64,
                    0.08 if lod == 0 else 0.13,
                    0.08 if lod == 0 else 0.13,
                    "accent" if walk_index == 0 else "trim",
                )
                post_count = 6 if lod == 0 else 4
                for post_index in range(post_count):
                    post_lateral = walk_lateral - walk_width / 2 + 0.5 + post_index * (
                        walk_width - 1.0
                    ) / max(1, post_count - 1)
                    beam(
                        post_lateral,
                        walk_y + 0.08,
                        facade_forward + 0.64,
                        post_lateral,
                        walk_y + 1.14,
                        facade_forward + 0.64,
                        0.07 if lod == 0 else 0.11,
                        0.07 if lod == 0 else 0.11,
                        "trim",
                    )
                if lod == 0:
                    for drain_offset in (-8.0, 8.0):
                        drain_x, drain_z = point(
                            walk_lateral + drain_offset,
                            facade_forward - 0.54,
                        )
                        builder.add_cylinder(
                            drain_x,
                            5.0,
                            drain_z,
                            0.13,
                            9.8,
                            "trim",
                            8,
                            0.13,
                        )

        # A broad rain canopy defines six customs inspection bays.  Its inner
        # edge overlaps the entrance-wall support zone; the 10.82m underside
        # keeps the complete 28m arrival opening and approach LOS unobstructed.
        canopy_width = lateral_span * 0.90
        canopy_depth = 8.0
        canopy_forward = forward_span * 0.445
        canopy_bottom = SOUKO_CUSTOMS_CANOPY_BOTTOM_M
        support_connectors(
            0,
            canopy_bottom,
            canopy_forward,
            canopy_width,
            canopy_depth,
            "wall_weathered",
            4,
            {"wall", "interior", "upper-walk"},
        )
        oriented_box(
            0,
            canopy_bottom + 0.42,
            canopy_forward,
            canopy_width,
            0.84,
            canopy_depth,
            "wall_alt",
        )
        beam(
            -canopy_width / 2,
            canopy_bottom + 1.05,
            canopy_forward + canopy_depth / 2 - 0.25,
            canopy_width / 2,
            canopy_bottom + 1.05,
            canopy_forward + canopy_depth / 2 - 0.25,
            0.30,
            0.24,
            "accent",
        )
        lane_count = 6 if lod == 0 else 4 if lod == 1 else 2
        for lane in range(lane_count):
            lane_lateral = (
                lane - (lane_count - 1) / 2
            ) * canopy_width * 0.84 / max(1, lane_count - 1)
            oriented_box(
                lane_lateral,
                canopy_bottom - 0.42,
                canopy_forward + 0.8,
                7.0 if lod == 0 else 9.0,
                0.70,
                2.2,
                "wall_cool",
            )
            if lod == 0:
                oriented_box(
                    lane_lateral,
                    canopy_bottom - 1.24,
                    canopy_forward + 1.88,
                    4.8,
                    0.18,
                    0.18,
                    "emissive" if lane in {1, 4} else "accent",
                )

        # Both 31.02m authored towers carry an open truss control bridge.  The
        # previous full-width slab/crown hid the sawtooth field and read as a
        # hovering concrete bar.  Chords, diagonals and a compact central cab
        # preserve the explicit support chain while returning the terminal's
        # four serrated bays to visual primacy.
        tower_frames = sorted(
            ((local_box(tower)[0], local_box(tower)[1], tower) for tower in towers),
            key=lambda item: item[0],
        )
        if len(tower_frames) != 2:
            raise RuntimeError("Souko customs terminal requires two authored tower supports")
        control_forward = sum(item[1] for item in tower_frames) / 2
        control_deck_bottom = min(
            float(item[2]["y"]) + float(item[2]["h"]) / 2
            for item in tower_frames
        ) - 0.42
        truss_bottom = control_deck_bottom
        truss_top = min(height_limit - 8.6, truss_bottom + 6.8)
        left_lateral = tower_frames[0][0]
        right_lateral = tower_frames[1][0]
        bridge_depth_half = 4.2
        for depth_side in (-1, 1):
            truss_forward = control_forward + depth_side * bridge_depth_half
            for chord_y in (truss_bottom + 0.22, truss_top - 0.22):
                beam(
                    left_lateral,
                    chord_y,
                    truss_forward,
                    right_lateral,
                    chord_y,
                    truss_forward,
                    0.32 if lod == 0 else 0.46,
                    0.26 if lod == 0 else 0.38,
                    "accent" if chord_y > truss_bottom + 1.0 and depth_side < 0 else "trim",
                )
            truss_bays = 6 if lod == 0 else 4
            for bay in range(truss_bays + 1):
                lateral = left_lateral + bay * (
                    right_lateral - left_lateral
                ) / truss_bays
                beam(
                    lateral,
                    truss_bottom + 0.18,
                    truss_forward,
                    lateral,
                    truss_top - 0.18,
                    truss_forward,
                    0.20 if lod == 0 else 0.30,
                    0.18 if lod == 0 else 0.26,
                    "wall_cool",
                )
                if bay < truss_bays:
                    next_lateral = left_lateral + (bay + 1) * (
                        right_lateral - left_lateral
                    ) / truss_bays
                    low_y, high_y = (
                        (truss_bottom + 0.44, truss_top - 0.44)
                        if (bay + (1 if depth_side > 0 else 0)) % 2 == 0
                        else (truss_top - 0.44, truss_bottom + 0.44)
                    )
                    beam(
                        lateral,
                        low_y,
                        truss_forward,
                        next_lateral,
                        high_y,
                        truss_forward,
                        0.16 if lod == 0 else 0.25,
                        0.14 if lod == 0 else 0.21,
                        "wall_weathered",
                    )
        for lateral in (left_lateral, right_lateral):
            beam(
                lateral,
                truss_top - 0.25,
                control_forward - bridge_depth_half,
                lateral,
                truss_top - 0.25,
                control_forward + bridge_depth_half,
                0.34,
                0.30,
                "trim",
            )

        # Small tower-top service rooms and one central control cab make the
        # bridge functional without recreating the rejected monolithic bar.
        for tower_index, (lateral, tower_forward, tower) in enumerate(tower_frames):
            tower_top = float(tower["y"]) + float(tower["h"]) / 2
            oriented_box(
                lateral,
                tower_top + 2.35,
                tower_forward,
                8.4,
                4.9,
                8.4,
                "wall_weathered",
            )
            oriented_box(
                lateral,
                tower_top + 5.0,
                tower_forward,
                9.4,
                0.40,
                9.4,
                "roof",
            )
            if lod == 0:
                oriented_box(
                    lateral,
                    tower_top + 2.8,
                    tower_forward + 4.25,
                    4.6,
                    1.55,
                    0.18,
                    "glass",
                )

        cab_bottom = truss_top - 0.28
        cab_height = 6.2
        oriented_box(
            0,
            cab_bottom + cab_height / 2,
            control_forward,
            16.5,
            cab_height,
            11.0,
            "wall_cool",
        )
        oriented_box(
            0,
            cab_bottom + cab_height * 0.62,
            control_forward + 5.55,
            13.0,
            2.2,
            0.20,
            "glass",
        )
        cab_roof_y = cab_bottom + cab_height + 0.24
        oriented_box(0, cab_roof_y, control_forward, 18.0, 0.48, 12.4, "roof")

        # Two rear boiler stacks echo the reference's tall terminal chimneys.
        # Their bases overlap the rear collision wall/roof zone; neither is a
        # gameplay boundary or a ground-level unsupported prop.
        stack_specs = ((-34.5, -29.0, 45.5), (34.0, -26.0, 43.0))
        for stack_index, (stack_lateral, stack_forward, stack_top) in enumerate(stack_specs):
            stack_bottom = roof_base - 0.18
            stack_x, stack_z = point(stack_lateral, stack_forward)
            builder.add_cylinder(
                stack_x,
                stack_bottom + (stack_top - stack_bottom) / 2,
                stack_z,
                1.25 if lod == 0 else 1.55,
                stack_top - stack_bottom,
                "wall_warm",
                12 if lod == 0 else 8,
                0.92,
            )
            for band_y in (stack_top - 7.0, stack_top - 3.2):
                builder.add_cylinder(
                    stack_x,
                    band_y,
                    stack_z,
                    1.32 if lod == 0 else 1.62,
                    0.62,
                    "accent" if stack_index == 0 and band_y > stack_top - 5.0 else "trim",
                    12 if lod == 0 else 8,
                    1.30 if lod == 0 else 1.60,
                )

        crown_x, crown_z = point(0, control_forward)
        beacon_height = max(1.1, height_limit - (cab_roof_y + 0.24))
        builder.add_cylinder(
            crown_x,
            cab_roof_y + 0.24 + beacon_height / 2,
            crown_z,
            0.24 if lod == 0 else 0.34,
            beacon_height,
            "accent",
            8 if lod == 0 else 6,
            0.10,
        )
        if lod == 0:
            # Customs inspection dunnage mirrors the stackhouse foreground but
            # uses smaller, tightly ordered clusters. Both remain outside the
            # protected opening and below knee height.
            for cluster_index, cluster_lateral in enumerate((-28.0, 28.0)):
                cluster_forward = forward_span / 2 + 2.6
                for plank in (-1, 0, 1):
                    oriented_box(
                        cluster_lateral + plank * 1.22,
                        0.10,
                        cluster_forward,
                        1.0,
                        0.20,
                        2.0,
                        "wood",
                    )
                for cone_offset in (-2.3, 2.3):
                    cone_x, cone_z = point(
                        cluster_lateral + cone_offset,
                        cluster_forward - 0.8,
                    )
                    builder.add_cylinder(
                        cone_x,
                        0.31,
                        cone_z,
                        0.20,
                        0.62,
                        "accent",
                        8,
                        0.08,
                    )
        return

    if landmark_id == "nakaniwa-suiren-crown-palace":
        wing_width = lateral_span * 0.36
        wing_depth = forward_span * 0.34
        for side in (-1, 1):
            lateral = side * lateral_span * 0.27
            wing_base = supported_base(
                lateral, 0, wing_width, wing_depth,
                parts={"wall", "interior", "upper-walk"},
            )
            support_connectors(
                lateral, wing_base, 0, wing_width, wing_depth,
                "wood", 4, {"wall", "interior", "upper-walk"},
            )
            gable(lateral, wing_base, 0, wing_width, 5.2 if detail else 4.2, wing_depth, "roof")
            oriented_box(lateral, wing_base + 0.20, 0, wing_width * 1.10, 0.40, wing_depth * 1.14, "wood")
        dome_forward = -forward_span * 0.12
        dome_x, dome_z = point(0, dome_forward)
        drum_radius = min(9.2, lateral_span * 0.105)
        drum_base = supported_base(
            0, dome_forward, drum_radius * 2, drum_radius * 2,
            parts={"wall", "interior", "upper-walk"},
        )
        support_connectors(
            0, drum_base, dome_forward, drum_radius * 2, drum_radius * 2,
            "wall_warm", 4, {"wall", "interior", "upper-walk"},
        )
        available = max(12.0, height_limit - drum_base)
        spire_h = min(4.2, available * 0.12)
        drum_h = available * 0.28
        dome_h = available - drum_h - spire_h
        segments = 18 if detail else 10
        builder.add_cylinder(
            dome_x, drum_base + drum_h / 2, dome_z,
            drum_radius * 0.92, drum_h, "wall_warm", segments, drum_radius,
        )
        radii = (drum_radius, drum_radius * 1.04, drum_radius * 0.94, drum_radius * 0.76, drum_radius * 0.52, drum_radius * 0.25)
        tier_count = len(radii) - 1
        tier_h = dome_h / tier_count
        for tier in range(tier_count):
            builder.add_cylinder(
                dome_x,
                drum_base + drum_h + tier_h * (tier + 0.5),
                dome_z,
                radii[tier],
                tier_h + 0.12,
                "roof",
                segments,
                radii[tier + 1],
            )
        dome_top = drum_base + drum_h + dome_h
        builder.add_cylinder(
            dome_x, dome_top + spire_h / 2 - 0.10, dome_z,
            0.24, spire_h + 0.20, "trim", 8, 0.06,
        )
        return

    if landmark_id == "nakaniwa-kakou-conservatory-citadel":
        fan_rear = -forward_span * 0.30
        fan_front = forward_span * 0.28
        fan_width = lateral_span * 0.78
        fan_depth = fan_front - fan_rear
        roof_base = supported_base(
            0, (fan_rear + fan_front) / 2, fan_width, fan_depth,
            parts={"tower", "wall", "interior", "upper-walk"},
        )
        support_connectors(
            0, roof_base, (fan_rear + fan_front) / 2, fan_width, fan_depth,
            "wall_weathered", 10, {"tower", "wall", "interior", "upper-walk"},
        )
        fan_height = max(12.0, height_limit - roof_base - 0.45)
        for spec in nakaniwa_conservatory_face_specs(
            placement, shell, lod, roof_base, fan_rear, fan_front, fan_width, fan_height,
        ):
            oriented_box(
                spec["lateral"], spec["y"], spec["forward"],
                spec["w"], spec["h"], spec["d"], spec["key"],
            )
        # Thin sloped panel beams replace the monolithic watertight glass
        # gable. Segmenting the old closed prism exposed a repeated triangular
        # end wall in aerial views; these panels have only a 12 cm structural
        # thickness and terminate directly on the eave/ridge rails.
        rib_count = 9 if detail else 5 if lod == 1 else 3
        rib_forwards = [
            fan_rear + rib * fan_depth / (rib_count - 1)
            for rib in range(rib_count)
        ]
        pane_gap = 0.30 if detail else 0.46
        for pane in range(rib_count - 1):
            pane_start = rib_forwards[pane]
            pane_end = rib_forwards[pane + 1]
            pane_depth = max(0.8, pane_end - pane_start - pane_gap)
            pane_forward = (pane_start + pane_end) / 2
            pane_start_visible = pane_forward - pane_depth / 2
            pane_end_visible = pane_forward + pane_depth / 2
            ridge_inset = 0.10
            ridge_panel_y = roof_base + fan_height * (
                1.0 - ridge_inset / max(0.001, fan_width / 2)
            )
            panel_key = (
                "roof"
                if lod == 2
                else "water" if pane % 4 == 0
                else "glass"
            )
            sloped_panel(
                -fan_width / 2, roof_base,
                -ridge_inset, ridge_panel_y,
                pane_start_visible, pane_end_visible,
                0.10, panel_key,
            )
            sloped_panel(
                ridge_inset, ridge_panel_y,
                fan_width / 2, roof_base,
                pane_start_visible, pane_end_visible,
                0.10, panel_key,
            )
        arch_sections = []
        for section_forward in rib_forwards:
            beam(
                -fan_width / 2, roof_base, section_forward,
                0, roof_base + fan_height, section_forward,
                0.26 if detail else 0.34, 0.20, "trim",
            )
            beam(
                0, roof_base + fan_height, section_forward,
                fan_width / 2, roof_base, section_forward,
                0.26 if detail else 0.34, 0.20, "trim",
            )
            arch_sections.append(section_forward)
        # Front/rear portal ties and centre mullions make the giant span read
        # as a conservatory hall rather than an unsupported glass awning. They
        # remain at the existing high roof base and do not enter traversal.
        for section_forward in (fan_rear, fan_front):
            beam(
                -fan_width / 2, roof_base + 0.28, section_forward,
                fan_width / 2, roof_base + 0.28, section_forward,
                0.34 if detail else 0.42, 0.26, "wood",
            )
            beam(
                0, roof_base + 0.18, section_forward,
                0, roof_base + fan_height - 0.18, section_forward,
                0.30 if detail else 0.38, 0.24, "trim",
            )
        for lateral_fraction, course_y in (
            (-0.50, roof_base),
            (-0.25, roof_base + fan_height * 0.50),
            (0.0, roof_base + fan_height),
            (0.25, roof_base + fan_height * 0.50),
            (0.50, roof_base),
        ):
            beam(
                fan_width * lateral_fraction, course_y, fan_rear,
                fan_width * lateral_fraction, course_y, fan_front,
                0.22 if detail else 0.28, 0.17,
                "accent" if lateral_fraction == 0 else "wood" if abs(lateral_fraction) == 0.25 else "trim",
            )
        # Three flat lantern drums, not generic cones, punctuate the ridge and
        # stay below the authored height cap.
        lantern_count = 3 if detail else 2
        for lantern in range(lantern_count):
            lantern_forward = fan_rear + (lantern + 1) * fan_depth / (lantern_count + 1)
            x, z = point(0, lantern_forward)
            builder.add_cylinder(
                x, roof_base + fan_height - 0.30, z,
                1.35 if detail else 1.10, 0.60, "accent",
                12 if detail else 8, 1.10 if detail else 0.90,
            )
        return


def add_kairou_reference_landmark_tier1(builder, lod, placement, style, walls, towers, columns, upper_walls):
    """Reference-matched silhouette and supported structure for Kairou.

    Connection map (all runtime metres):
      sanctuary wall -> engaged shaft (>=0.30 m embedded) -> capital
        -> entablature (>=0.12 m vertical overlap) -> stepped tower crown;
      four observatory collider towers -> four diagonal truss legs
        -> 14.4 m support square at Y=40 -> central mast -> armillary rings.

    No new ground contact enters either 28 m route.  Facade columns remain
    <=0.25 m relief while eight central columns are real TS colliders.  All
    larger visual-only masses are visibly seated on those columns or the four
    observatory towers and start far above player height.
    """
    if not placement["id"].startswith("kairou-") or lod == 2:
        return

    centre_x = float(placement["cx"])
    centre_z = float(placement["cz"])
    width = float(placement["width"])
    depth = float(placement["depth"])

    if "hypostyle" in style:
        # Eight engaged columns on each long entrance elevation.  Four shafts
        # sit on each real wall segment; the central 28 m gate stays untouched.
        facade_walls = [
            wall for wall in walls
            if wall["w"] >= wall["d"]
            and wall["h"] > 4.0
            and abs(abs(wall["z"] - centre_z) - depth / 2) <= 1.0
        ]
        for wall in facade_walls:
            outward = 1 if wall["z"] >= centre_z else -1
            radius = 0.55
            # wall face + 0.25 m maximum relief; the remaining 0.30 m of the
            # shaft radius is embedded in the authoritative collider.
            column_z = wall["z"] + outward * (wall["d"] / 2 - radius + 0.25)
            column_count = 4 if lod == 0 else 2
            shaft_h = min(7.75, wall["h"] - 0.90)
            for column_index in range(column_count):
                column_x = wall["x"] + (
                    column_index - (column_count - 1) / 2
                ) * wall["w"] * 0.72 / max(1, column_count - 1)
                builder.add_cylinder(
                    column_x, 0.18, column_z,
                    0.72, 0.36, "wall_weathered", 12 if lod == 0 else 8, 0.66,
                )
                builder.add_cylinder(
                    column_x, 0.36 + shaft_h / 2, column_z,
                    0.62, shaft_h, "wall_warm", 12 if lod == 0 else 8, 0.48,
                )
                builder.add_cylinder(
                    column_x, 0.36 + shaft_h + 0.22, column_z,
                    0.76, 0.44, "wall_weathered", 12 if lod == 0 else 8, 0.70,
                )
                if lod == 0:
                    for band in (0.28, 0.68):
                        builder.add_cylinder(
                            column_x,
                            0.36 + shaft_h * band,
                            column_z,
                            0.64 - band * 0.08,
                            0.12,
                            "trim",
                            12,
                        )

            wall_top = wall["y"] + wall["h"] / 2
            builder.add_box(
                wall["x"], wall_top + 0.25, wall["z"],
                wall["w"] + 0.34, 0.74, wall["d"] + 0.42, "wall_warm",
            )
            builder.add_box(
                wall["x"], wall_top + 0.78, wall["z"],
                wall["w"] + 0.78, 0.32, wall["d"] + 0.72, "trim",
            )
            if lod == 0:
                # Sparse 4 m metope rhythm.  The panels are warm stone relief,
                # never glass cards, and are supported by the entablature.
                panel_count = max(4, min(10, int(wall["w"] // 4)))
                for panel in range(panel_count):
                    panel_x = wall["x"] + (
                        panel - (panel_count - 1) / 2
                    ) * wall["w"] * 0.82 / max(1, panel_count - 1)
                    builder.add_box(
                        panel_x,
                        wall_top + 0.34,
                        wall["z"] + outward * (wall["d"] / 2 + 0.08),
                        min(2.15, wall["w"] / panel_count * 0.62),
                        0.28,
                        0.16,
                        "wall_weathered" if panel % 7 == 0 else "wall_warm",
                    )

        # Two open hypostyle wings sit on the eight real combat columns.  Each
        # wing is independent, so the full 28 m north/south street and the full
        # east/west cross remain open to sky and player traversal.  The broad
        # architrave, parapet and recessed upper hall reproduce the reference's
        # horizontal sanctuary silhouette without a floating decorative roof.
        if len(columns) == 8:
            column_top = max(column["y"] + column["h"] / 2 for column in columns)
            entrance_z = float(placement["entrance"][1])
            front_sign = 1 if entrance_z > centre_z else -1
            for side in (-1, 1):
                wing_columns = [
                    column for column in columns
                    if (column["x"] - centre_x) * side > 0
                ]
                wing_min_x = min(column["x"] - column["w"] / 2 for column in wing_columns)
                wing_max_x = max(column["x"] + column["w"] / 2 for column in wing_columns)
                wing_min_z = min(column["z"] - column["d"] / 2 for column in wing_columns)
                wing_max_z = max(column["z"] + column["d"] / 2 for column in wing_columns)
                wing_x = (wing_min_x + wing_max_x) / 2
                # One real front colonnade at local Z=+32 is paired with the
                # collision-authoritative interior wall around local Z=+14.
                # The deep portico therefore has support at both edges instead
                # of cantilevering a roof from a single row of posts.
                rear_support_z = centre_z + front_sign * 14.5
                front_edge_z = wing_max_z if front_sign > 0 else wing_min_z
                wing_z = (rear_support_z + front_edge_z) / 2
                wing_w = wing_max_x - wing_min_x + 1.2
                wing_d = abs(front_edge_z - rear_support_z) + 1.0

                # Architraves connect actual column capitals in both axes.
                for row_z in sorted({round(column["z"], 4) for column in wing_columns}):
                    row = sorted(
                        (column for column in wing_columns if abs(column["z"] - row_z) < 0.01),
                        key=lambda column: column["x"],
                    )
                    builder.add_beam(
                        (row[0]["x"], column_top + 0.30, row_z),
                        (row[-1]["x"], column_top + 0.30, row_z),
                        0.52 if lod == 0 else 0.68,
                        0.70,
                        "wall_weathered",
                    )
                    if lod == 0:
                        # Stone arch ribs directly under the physical upper
                        # walk turn its thin gameplay slab into a supported
                        # colonnade rather than a naked horizontal beam.
                        for left, right in zip(row, row[1:]):
                            spring_y = 3.75
                            apex_y = 5.05
                            mid_x = (left["x"] + right["x"]) / 2
                            builder.add_beam(
                                (left["x"], spring_y, row_z),
                                (mid_x, apex_y, row_z),
                                0.15, 0.13, "trim",
                            )
                            builder.add_beam(
                                (mid_x, apex_y, row_z),
                                (right["x"], spring_y, row_z),
                                0.15, 0.13, "trim",
                            )
                for column_x in sorted({round(column["x"], 4) for column in wing_columns}):
                    builder.add_beam(
                        (column_x, column_top + 0.22, rear_support_z),
                        (
                            column_x,
                            column_top + 0.22,
                            front_edge_z - front_sign * 0.10,
                        ),
                        0.44 if lod == 0 else 0.60,
                        0.58,
                        "trim",
                    )

                builder.add_box(
                    wing_x, column_top + 0.78, wing_z,
                    wing_w + 0.9, 1.18, wing_d + 0.9, "wall_warm",
                )
                builder.add_box(
                    wing_x, column_top + 1.52, wing_z,
                    wing_w + 1.55, 0.32, wing_d + 1.55, "trim",
                )

                upper_base = column_top + 1.68
                upper_w = max(8.0, wing_w - 4.0)
                upper_d = max(12.0, wing_d - 3.0)
                upper_h = 5.8
                upper_z = wing_z - front_sign * 1.6
                builder.add_box(
                    wing_x, upper_base + upper_h / 2, upper_z,
                    upper_w, upper_h, upper_d, "wall_weathered",
                )
                builder.add_box(
                    wing_x, upper_base + upper_h + 0.24, upper_z,
                    upper_w + 1.0, 0.48, upper_d + 1.0, "trim",
                )
                if lod == 0:
                    # Four-metre blind-arch rhythm and deep pilasters; relief is
                    # shallow and supported by the closed upper hall.
                    bay_count = max(3, min(6, int(upper_d // 6)))
                    face_x = wing_x - side * (upper_w / 2 + 0.10)
                    for bay in range(bay_count):
                        bay_z = upper_z + (
                            bay - (bay_count - 1) / 2
                        ) * upper_d * 0.78 / max(1, bay_count - 1)
                        builder.add_box(
                            face_x,
                            upper_base + upper_h * 0.49,
                            bay_z,
                            0.20,
                            upper_h * 0.72,
                            min(2.0, upper_d / bay_count * 0.54),
                            "wall_warm" if bay % 3 else "wall_weathered",
                        )
                        builder.add_box(
                            face_x - side * 0.09,
                            upper_base + upper_h * 0.90,
                            bay_z,
                            0.34,
                            0.22,
                            min(2.5, upper_d / bay_count * 0.70),
                            "trim",
                        )

                    # The player-facing north elevation gets a separate
                    # column-scale rhythm.  It is shallow relief on the closed
                    # upper hall, not a row of fake black windows.
                    player_face_z = upper_z + front_sign * (upper_d / 2 + 0.10)
                    north_bays = 4
                    for bay in range(north_bays):
                        bay_x = wing_x + (
                            bay - (north_bays - 1) / 2
                        ) * upper_w * 0.78 / (north_bays - 1)
                        builder.add_box(
                            bay_x,
                            upper_base + upper_h * 0.48,
                            player_face_z,
                            min(2.5, upper_w / north_bays * 0.54),
                            upper_h * 0.68,
                            0.20,
                            "wall_warm" if bay % 3 else "wall_weathered",
                        )
                        builder.add_beam(
                            (
                                bay_x - 1.15,
                                upper_base + upper_h * 0.82,
                                player_face_z + front_sign * 0.08,
                            ),
                            (
                                bay_x,
                                upper_base + upper_h * 0.98,
                                player_face_z + front_sign * 0.08,
                            ),
                            0.09, 0.07, "trim",
                        )
                        builder.add_beam(
                            (
                                bay_x,
                                upper_base + upper_h * 0.98,
                                player_face_z + front_sign * 0.08,
                            ),
                            (
                                bay_x + 1.15,
                                upper_base + upper_h * 0.82,
                                player_face_z + front_sign * 0.08,
                            ),
                            0.09, 0.07, "trim",
                        )

                # One modest rear lantern per wing adds skyline depth while
                # staying well below the sanctuary's 38 m authored envelope.
                lantern_h = 5.8 if lod == 0 else 4.2
                builder.add_box(
                    wing_x,
                    upper_base + upper_h + 0.48 + lantern_h / 2,
                    upper_z - upper_d * 0.18,
                    upper_w * 0.42,
                    lantern_h,
                    upper_d * 0.26,
                    "wall_warm",
                )
                builder.add_box(
                    wing_x,
                    upper_base + upper_h + 0.48 + lantern_h + 0.22,
                    upper_z - upper_d * 0.18,
                    upper_w * 0.52,
                    0.44,
                    upper_d * 0.34,
                    "accent",
                )

                # A rear stepback and a small sanctuary lantern complete a
                # 30–37m silhouette.  Both sit directly over the upper hall,
                # and each wing remains independent across the 28m sky gap.
                step_h = 6.2 if lod == 0 else 4.6
                step_z = upper_z - front_sign * upper_d * 0.20
                step_bottom = upper_base + upper_h + 0.48
                builder.add_box(
                    wing_x,
                    step_bottom + step_h / 2,
                    step_z,
                    upper_w * 0.66,
                    step_h,
                    upper_d * 0.46,
                    "wall_warm",
                )
                builder.add_box(
                    wing_x,
                    step_bottom + step_h + 0.28,
                    step_z,
                    upper_w * 0.78,
                    0.56,
                    upper_d * 0.58,
                    "trim",
                )
                if lod == 0:
                    for tooth in range(5):
                        tooth_x = wing_x + (tooth - 2) * upper_w * 0.13
                        builder.add_box(
                            tooth_x,
                            step_bottom + step_h + 0.82,
                            step_z,
                            0.82,
                            1.08,
                            upper_d * 0.50,
                            "wall_weathered",
                        )

    # The paired composition is viewed down the 21 m civic boulevard, so the
    # two *inner* side elevations are as important as the south entrances.
    # Turn those formerly blank board walls into deep engaged arcades and one
    # monumental supported gate arch.  Each shaft overlaps a real wall segment
    # and every arch begins above the wall top; the central 28 m cross remains
    # physically and visually open at player height.
    boulevard_x = 2.0
    inward_sign = 1 if centre_x < boulevard_x else -1
    inner_side_walls = [
        wall for wall in walls
        if wall["d"] > wall["w"]
        and abs((wall["x"] - centre_x) - inward_sign * width / 2) <= 2.0
        and wall["h"] >= 4.0
    ]
    inner_side_walls.sort(key=lambda wall: wall["z"])
    for side_index, wall in enumerate(inner_side_walls):
        wall_face_x = wall["x"] + inward_sign * (wall["w"] / 2 - 0.22)
        wall_base = wall["y"] - wall["h"] / 2
        wall_top = wall["y"] + wall["h"] / 2
        shaft_count = 4 if lod == 0 else 2
        for shaft in range(shaft_count):
            shaft_z = wall["z"] + (
                shaft - (shaft_count - 1) / 2
            ) * wall["d"] * 0.72 / max(1, shaft_count - 1)
            shaft_h = (
                max(14.0, min(17.0, float(placement["height"]) * 0.42))
                if "hypostyle" in style
                else max(7.5, wall["h"] - 0.65)
            )
            builder.add_cylinder(
                wall_face_x,
                wall_base + 0.22,
                shaft_z,
                0.74,
                0.44,
                "wall_weathered",
                12 if lod == 0 else 8,
                0.66,
            )
            builder.add_cylinder(
                wall_face_x,
                wall_base + 0.44 + shaft_h / 2,
                shaft_z,
                0.62,
                shaft_h,
                "wall_warm",
                12 if lod == 0 else 8,
                0.50,
            )
            builder.add_cylinder(
                wall_face_x,
                wall_base + 0.44 + shaft_h + 0.22,
                shaft_z,
                0.78,
                0.44,
                "wall_weathered",
                12 if lod == 0 else 8,
                0.70,
            )
        facade_crown_y = max(
            wall_top,
            wall_base + 0.44 + shaft_h,
        )
        builder.add_box(
            wall["x"] + inward_sign * 0.10,
            facade_crown_y + 0.34,
            wall["z"],
            wall["w"] + 0.58,
            0.68,
            wall["d"] + 0.44,
            "wall_warm",
        )
        builder.add_box(
            wall["x"] + inward_sign * 0.16,
            facade_crown_y + 0.82,
            wall["z"],
            wall["w"] + 0.74,
            0.28,
            wall["d"] + 0.82,
            "trim",
        )
        if lod == 0:
            panel_count = max(2, min(4, int(wall["d"] // 5.0)))
            for panel in range(panel_count):
                panel_z = wall["z"] + (
                    panel - (panel_count - 1) / 2
                ) * wall["d"] * 0.70 / max(1, panel_count - 1)
                panel_y = wall_base + wall["h"] * 0.55
                panel_h = min(3.4, wall["h"] * 0.42)
                panel_w = min(2.25, wall["d"] / panel_count * 0.52)
                panel_x = wall["x"] + inward_sign * (wall["w"] / 2 + 0.075)
                builder.add_box(
                    panel_x, panel_y, panel_z,
                    0.15, panel_h, panel_w,
                    "wall_weathered" if (panel + side_index) % 3 else "wall_warm",
                )
                builder.add_beam(
                    (panel_x + inward_sign * 0.04, panel_y + panel_h / 2, panel_z - panel_w / 2),
                    (panel_x + inward_sign * 0.04, panel_y + panel_h / 2 + 0.64, panel_z),
                    0.09, 0.075, "trim",
                )
                builder.add_beam(
                    (panel_x + inward_sign * 0.04, panel_y + panel_h / 2 + 0.64, panel_z),
                    (panel_x + inward_sign * 0.04, panel_y + panel_h / 2, panel_z + panel_w / 2),
                    0.09, 0.075, "trim",
                )

    if len(inner_side_walls) >= 2:
        lower_wall = inner_side_walls[0]
        upper_wall = inner_side_walls[-1]
        left_z = lower_wall["z"] + lower_wall["d"] / 2
        right_z = upper_wall["z"] - upper_wall["d"] / 2
        if right_z - left_z >= 18.0:
            arch_x = centre_x + inward_sign * (width / 2 + 0.10)
            spring_y = max(
                lower_wall["y"] + lower_wall["h"] / 2,
                upper_wall["y"] + upper_wall["h"] / 2,
            ) + (2.0 if "hypostyle" in style else 3.0)
            arch_rise = min(7.2, (right_z - left_z) * 0.24)
            apex_z = (left_z + right_z) / 2
            arch_segments = 6 if lod == 0 else 4
            for endpoint_z in (left_z, right_z):
                previous = (arch_x, spring_y, endpoint_z)
                for segment in range(1, arch_segments + 1):
                    t = segment / arch_segments
                    point = (
                        arch_x,
                        spring_y + arch_rise * math.sin(t * math.pi / 2) ** 0.92,
                        endpoint_z + (apex_z - endpoint_z) * t,
                    )
                    builder.add_beam(
                        previous, point,
                        0.36 if lod == 0 else 0.46,
                        0.42,
                        "wall_warm" if segment % 3 else "wall_weathered",
                    )
                    previous = point
            # Deep masonry spring blocks visibly connect the high arch to the
            # two collision walls instead of leaving another floating truss.
            for support_z in (left_z, right_z):
                builder.add_box(
                    arch_x,
                    spring_y - 1.2,
                    support_z,
                    1.30,
                    2.8,
                    2.10,
                    "wall_weathered",
                )
            builder.add_box(
                arch_x,
                spring_y + arch_rise + 0.18,
                apex_z,
                0.88,
                1.18,
                1.20,
                "accent" if lod == 0 else "trim",
            )

    if "observatory" in style:
        entrance_z = float(placement["entrance"][1])
        front_sign = 1 if entrance_z > centre_z else -1
        front_walls = [
            wall for wall in walls
            if wall["w"] > wall["d"]
            and abs((wall["z"] - centre_z) - front_sign * depth / 2) <= 2.0
            and wall["h"] >= 4.0
        ]
        front_walls.sort(key=lambda wall: wall["x"])
        for wall in front_walls:
            face_z = wall["z"] + front_sign * (wall["d"] / 2 - 0.22)
            wall_base = wall["y"] - wall["h"] / 2
            wall_top = wall["y"] + wall["h"] / 2
            shaft_count = 4 if lod == 0 else 2
            for shaft in range(shaft_count):
                shaft_x = wall["x"] + (
                    shaft - (shaft_count - 1) / 2
                ) * wall["w"] * 0.72 / max(1, shaft_count - 1)
                shaft_h = max(4.6, wall["h"] - 0.60)
                builder.add_cylinder(
                    shaft_x, wall_base + 0.23, face_z,
                    0.76, 0.46, "wall_weathered",
                    12 if lod == 0 else 8, 0.68,
                )
                builder.add_cylinder(
                    shaft_x, wall_base + 0.46 + shaft_h / 2, face_z,
                    0.64, shaft_h, "wall_warm",
                    12 if lod == 0 else 8, 0.50,
                )
                builder.add_cylinder(
                    shaft_x, wall_base + 0.46 + shaft_h + 0.22, face_z,
                    0.80, 0.44, "wall_weathered",
                    12 if lod == 0 else 8, 0.72,
                )
            builder.add_box(
                wall["x"], wall_top + 0.40,
                wall["z"] + front_sign * 0.10,
                wall["w"] + 0.54, 0.80, wall["d"] + 0.58,
                "wall_warm",
            )
        if len(front_walls) >= 2:
            left_wall, right_wall = front_walls[0], front_walls[-1]
            left_x = left_wall["x"] + left_wall["w"] / 2
            right_x = right_wall["x"] - right_wall["w"] / 2
            if right_x - left_x >= 18.0:
                arch_z = centre_z + front_sign * (depth / 2 + 0.10)
                spring_y = max(
                    left_wall["y"] + left_wall["h"] / 2,
                    right_wall["y"] + right_wall["h"] / 2,
                ) + 3.0
                apex_x = (left_x + right_x) / 2
                arch_rise = min(7.2, (right_x - left_x) * 0.24)
                arch_segments = 6 if lod == 0 else 4
                for endpoint_x in (left_x, right_x):
                    previous = (endpoint_x, spring_y, arch_z)
                    for segment in range(1, arch_segments + 1):
                        t = segment / arch_segments
                        point = (
                            endpoint_x + (apex_x - endpoint_x) * t,
                            spring_y + arch_rise * math.sin(t * math.pi / 2) ** 0.92,
                            arch_z,
                        )
                        builder.add_beam(
                            previous, point,
                            0.38 if lod == 0 else 0.48,
                            0.44,
                            "wall_warm" if segment % 3 else "wall_weathered",
                        )
                        previous = point
                for support_x in (left_x, right_x):
                    builder.add_box(
                        support_x, spring_y - 1.25, arch_z,
                        2.10, 3.0, 1.35, "wall_weathered",
                    )
                builder.add_box(
                    apex_x, spring_y + arch_rise + 0.20, arch_z,
                    1.25, 1.25, 0.92,
                    "accent" if lod == 0 else "trim",
                )

    if "observatory" not in style or len(towers) < 4:
        return

    # Four real collider towers support the ring crown; there is deliberately
    # no collisionless central tower in the open combat cross.
    ring_x = centre_x
    ring_z = centre_z
    support_y = 39.0
    ring_y = 43.0
    ring_radius = 10.4

    # The TypeScript shell includes one 30x12x30 high central proxy from
    # Y=27.8–39.8.  Render it as a tapered three-tier stone observatory rather
    # than exposing the square proxy; every visible drum point remains inside
    # that authoritative collider and the player cross remains open below.
    central_cores = [
        wall for wall in upper_walls
        if wall["w"] > 10.0 and wall["d"] > 10.0
    ]
    if len(central_cores) != 1:
        raise RuntimeError(
            f"{placement['id']}: expected one collision-authoritative central core"
        )
    core = central_cores[0]
    core_bottom = core["y"] - core["h"] / 2
    builder.add_cylinder(
        ring_x, core_bottom + 3.2, ring_z,
        14.6, 6.4, "wall_weathered", 16 if lod == 0 else 12, 13.4,
    )
    builder.add_cylinder(
        ring_x, core_bottom + 8.5, ring_z,
        12.5, 4.2, "wall_warm", 16 if lod == 0 else 12, 10.9,
    )
    builder.add_cylinder(
        ring_x, core_bottom + 11.3, ring_z,
        10.8, 1.4, "trim", 16 if lod == 0 else 12, 9.8,
    )
    for belt_y, belt_radius in (
        (core_bottom + 0.30, 14.9),
        (core_bottom + 6.35, 13.8),
        (core_bottom + 10.55, 11.5),
        (core_bottom + 11.75, 10.2),
    ):
        builder.add_cylinder(
            ring_x, belt_y, ring_z,
            belt_radius, 0.38, "trim", 16 if lod == 0 else 12,
        )

    # The south collision-authoritative upper wall carries a true stepped
    # observatory facade.  The rejected proof exposed only the thin gameplay
    # walk and read as scaffolding; these masses begin on the real wall top,
    # stay above traversal, and lead the eye from human-scale arches to the
    # central armillary crown without inventing ground collision.
    entrance_z = float(placement["entrance"][1])
    front_sign = 1 if entrance_z > centre_z else -1
    front_upper_candidates = [
        wall for wall in upper_walls
        if wall["w"] > wall["d"]
        and abs((wall["z"] - centre_z) - front_sign * depth / 2) <= 2.0
    ]
    if len(front_upper_candidates) != 1:
        raise RuntimeError(
            f"{placement['id']}: expected one front collision upper wall"
        )
    front_upper = front_upper_candidates[0]
    facade_bottom = front_upper["y"] + front_upper["h"] / 2
    facade_z = front_upper["z"] + front_sign * 0.18
    lower_w = min(36.0, front_upper["w"] * 0.46)
    lower_d = front_upper["d"] + 1.1
    lower_h = 11.8
    builder.add_box(
        centre_x, facade_bottom + lower_h / 2, facade_z,
        lower_w, lower_h, lower_d, "wall_warm",
    )
    builder.add_box(
        centre_x, facade_bottom + lower_h + 0.25, facade_z,
        lower_w + 1.5, 0.50, lower_d + 0.70, "trim",
    )
    middle_w = lower_w * 0.74
    middle_h = 7.4
    middle_bottom = facade_bottom + lower_h + 0.50
    builder.add_box(
        centre_x, middle_bottom + middle_h / 2,
        facade_z - front_sign * 0.26,
        middle_w, middle_h, lower_d * 0.90, "wall_weathered",
    )
    builder.add_box(
        centre_x, middle_bottom + middle_h + 0.24,
        facade_z - front_sign * 0.26,
        middle_w + 1.2, 0.48, lower_d + 0.18, "trim",
    )
    if lod == 0:
        # Two stacked arcade bands, with deep jambs and pointed heads, replace
        # the former broad cyan plate while remaining solid blind relief.
        front_plane_z = facade_z + front_sign * (lower_d / 2 + 0.08)
        for level, (panel_y, panel_h, bay_count) in enumerate((
            (facade_bottom + 3.7, 4.4, 7),
            (facade_bottom + 8.8, 3.2, 5),
        )):
            used_w = lower_w * (0.80 if level == 0 else 0.66)
            for bay in range(bay_count):
                panel_x = centre_x + (
                    bay - (bay_count - 1) / 2
                ) * used_w / max(1, bay_count - 1)
                panel_w = 2.55 if level == 0 else 2.20
                builder.add_box(
                    panel_x, panel_y, front_plane_z,
                    panel_w, panel_h, 0.16,
                    "wall_weathered" if (bay + level) % 4 else "wall_warm",
                )
                for edge in (-1, 1):
                    builder.add_box(
                        panel_x + edge * (panel_w / 2 + 0.12), panel_y,
                        front_plane_z + front_sign * 0.08,
                        0.22, panel_h + 0.46, 0.18, "trim",
                    )
                builder.add_beam(
                    (panel_x - panel_w / 2, panel_y + panel_h / 2, front_plane_z + front_sign * 0.12),
                    (panel_x, panel_y + panel_h / 2 + 0.78, front_plane_z + front_sign * 0.12),
                    0.10, 0.085, "trim",
                )
                builder.add_beam(
                    (panel_x, panel_y + panel_h / 2 + 0.78, front_plane_z + front_sign * 0.12),
                    (panel_x + panel_w / 2, panel_y + panel_h / 2, front_plane_z + front_sign * 0.12),
                    0.10, 0.085, "trim",
                )
        for pier in (-1, 1):
            pier_x = centre_x + pier * lower_w * 0.43
            builder.add_box(
                pier_x, facade_bottom + lower_h * 0.52,
                front_plane_z + front_sign * 0.10,
                0.72, lower_h * 0.92, 0.48, "wall_weathered",
            )
        # Paired windcatchers seat on the stepped facade and flank, rather
        # than hide, the larger armillary behind it.
        for catcher in (-1, 1):
            catcher_x = centre_x + catcher * middle_w * 0.30
            catcher_h = 7.0
            catcher_bottom = middle_bottom + middle_h + 0.48
            builder.add_box(
                catcher_x, catcher_bottom + catcher_h / 2,
                facade_z - front_sign * 0.36,
                4.4, catcher_h, 4.0, "wall_warm",
            )
            builder.add_box(
                catcher_x, catcher_bottom + catcher_h + 0.20,
                facade_z - front_sign * 0.36,
                5.0, 0.40, 4.6, "trim",
            )
            for slit in (-1, 0, 1):
                builder.add_box(
                    catcher_x + slit * 0.88,
                    catcher_bottom + catcher_h * 0.62,
                    facade_z + front_sign * (1.72),
                    0.12, catcher_h * 0.42, 0.10, "wood",
                )

    # Mirror the completed hierarchy onto the west/east inner elevation that
    # actually faces the paired boulevard.  This mass is seated on the real
    # 80 m upper-wall collider and is what turns the reference-match view from
    # an open roof frame into a readable observatory palace.
    inner_upper_candidates = [
        wall for wall in upper_walls
        if wall["d"] > wall["w"]
        and abs((wall["x"] - centre_x) - inward_sign * width / 2) <= 2.0
    ]
    if len(inner_upper_candidates) != 1:
        raise RuntimeError(
            f"{placement['id']}: expected one boulevard-facing collision upper wall"
        )
    inner_upper = inner_upper_candidates[0]
    side_bottom = inner_upper["y"] + inner_upper["h"] / 2
    side_x = inner_upper["x"] + inward_sign * 0.18
    side_length = min(38.0, inner_upper["d"] * 0.48)
    side_thickness = inner_upper["w"] + 1.1
    side_lower_h = 11.2
    builder.add_box(
        side_x, side_bottom + side_lower_h / 2, centre_z,
        side_thickness, side_lower_h, side_length, "wall_warm",
    )
    builder.add_box(
        side_x, side_bottom + side_lower_h + 0.25, centre_z,
        side_thickness + 0.70, 0.50, side_length + 1.5, "trim",
    )
    side_middle_length = side_length * 0.72
    side_middle_h = 7.2
    side_middle_bottom = side_bottom + side_lower_h + 0.50
    builder.add_box(
        side_x - inward_sign * 0.24,
        side_middle_bottom + side_middle_h / 2,
        centre_z,
        side_thickness * 0.92,
        side_middle_h,
        side_middle_length,
        "wall_weathered",
    )
    builder.add_box(
        side_x - inward_sign * 0.24,
        side_middle_bottom + side_middle_h + 0.24,
        centre_z,
        side_thickness + 0.30,
        0.48,
        side_middle_length + 1.2,
        "trim",
    )
    if lod == 0:
        side_face_x = side_x + inward_sign * (side_thickness / 2 + 0.08)
        for level, (panel_y, panel_h, bay_count) in enumerate((
            (side_bottom + 3.6, 4.3, 7),
            (side_bottom + 8.6, 3.1, 5),
        )):
            used_span = side_length * (0.80 if level == 0 else 0.66)
            for bay in range(bay_count):
                panel_z = centre_z + (
                    bay - (bay_count - 1) / 2
                ) * used_span / max(1, bay_count - 1)
                panel_w = 2.5 if level == 0 else 2.15
                builder.add_box(
                    side_face_x, panel_y, panel_z,
                    0.16, panel_h, panel_w,
                    "wall_weathered" if (bay + level) % 4 else "wall_warm",
                )
                for edge in (-1, 1):
                    builder.add_box(
                        side_face_x + inward_sign * 0.08,
                        panel_y,
                        panel_z + edge * (panel_w / 2 + 0.12),
                        0.18, panel_h + 0.46, 0.22, "trim",
                    )
                builder.add_beam(
                    (side_face_x + inward_sign * 0.12, panel_y + panel_h / 2, panel_z - panel_w / 2),
                    (side_face_x + inward_sign * 0.12, panel_y + panel_h / 2 + 0.76, panel_z),
                    0.10, 0.085, "trim",
                )
                builder.add_beam(
                    (side_face_x + inward_sign * 0.12, panel_y + panel_h / 2 + 0.76, panel_z),
                    (side_face_x + inward_sign * 0.12, panel_y + panel_h / 2, panel_z + panel_w / 2),
                    0.10, 0.085, "trim",
                )
        for catcher in (-1, 1):
            catcher_z = centre_z + catcher * side_middle_length * 0.30
            catcher_h = 6.8
            catcher_bottom = side_middle_bottom + side_middle_h + 0.48
            builder.add_box(
                side_x - inward_sign * 0.28,
                catcher_bottom + catcher_h / 2,
                catcher_z,
                4.0, catcher_h, 4.4, "wall_warm",
            )
            builder.add_box(
                side_x - inward_sign * 0.28,
                catcher_bottom + catcher_h + 0.20,
                catcher_z,
                4.6, 0.40, 5.0, "trim",
            )
    if lod == 0:
        # Twelve engaged shafts provide real metre-scale facade rhythm.  They
        # overlap the tapered drum and never become detached freestanding props.
        for bay in range(12):
            angle = math.tau * bay / 12
            column_x = ring_x + math.cos(angle) * 13.55
            column_z = ring_z + math.sin(angle) * 13.55
            builder.add_cylinder(
                column_x, core_bottom + 3.25, column_z,
                0.46, 5.5, "wall_warm", 10, 0.39,
            )
            builder.add_cylinder(
                column_x, core_bottom + 6.12, column_z,
                0.62, 0.38, "wall_weathered", 10, 0.54,
            )
    nodes = []
    for tower in towers[:4]:
        sign_x = -1 if tower["x"] < centre_x else 1
        sign_z = -1 if tower["z"] < centre_z else 1
        node = (ring_x + sign_x * ring_radius, support_y, ring_z + sign_z * ring_radius)
        nodes.append(node)
        tower_top = tower["y"] + tower["h"] / 2
        builder.add_beam(
            (tower["x"], tower_top - 0.20, tower["z"]),
            node,
            0.34 if lod == 0 else 0.46,
            0.28,
            "trim",
        )
        builder.add_beam(
            node,
            (ring_x, support_y, ring_z),
            0.24 if lod == 0 else 0.34,
            0.20,
            "accent",
        )
        # Massive inward corbel seated inside each physical tower supports the
        # high central drum at its collision-authoritative lower edge.
        builder.add_beam(
            (tower["x"], core_bottom + 0.35, tower["z"]),
            (
                ring_x + sign_x * 10.0,
                core_bottom + 0.35,
                ring_z + sign_z * 10.0,
            ),
            0.78 if lod == 0 else 0.96,
            0.68,
            "wall_weathered",
        )
    # Square perimeter ties prevent the supports reading as floating sticks.
    ordered_nodes = sorted(nodes, key=lambda point: math.atan2(point[2] - ring_z, point[0] - ring_x))
    for index, node in enumerate(ordered_nodes):
        builder.add_beam(
            node,
            ordered_nodes[(index + 1) % len(ordered_nodes)],
            0.28 if lod == 0 else 0.38,
            0.22,
            "trim",
        )
    builder.add_cylinder(
        ring_x, (support_y + ring_y) / 2, ring_z,
        0.42, ring_y - support_y + 0.20, "trim", 10 if lod == 0 else 7, 0.30,
    )

    segments = 24 if lod == 0 else 14

    def ring_point(plane, angle):
        cosine = math.cos(angle)
        sine = math.sin(angle)
        if plane == 0:  # X/Y meridian
            return ring_x + cosine * ring_radius, ring_y + sine * ring_radius, ring_z
        if plane == 1:  # Z/Y meridian
            return ring_x, ring_y + sine * ring_radius, ring_z + cosine * ring_radius
        if plane == 2:
            diagonal = cosine * ring_radius / math.sqrt(2)
            return ring_x + diagonal, ring_y + sine * ring_radius, ring_z + diagonal
        return ring_x + cosine * ring_radius, ring_y, ring_z + sine * ring_radius

    for plane in range(4):
        for segment in range(segments):
            angle_a = math.tau * segment / segments
            angle_b = math.tau * (segment + 1) / segments
            builder.add_beam(
                ring_point(plane, angle_a),
                ring_point(plane, angle_b),
                0.14 if lod == 0 else 0.20,
                0.10,
                "accent" if plane in {2, 3} else "trim",
            )
    builder.add_cylinder(
        ring_x, ring_y, ring_z,
        1.10, 2.20, "accent", 12 if lod == 0 else 8, 0.82,
    )

    # Observatory tower facade tiers and a high supported gallery make the
    # four collision towers read as one caravan observatory instead of four
    # detached chimneys.  All spans are >=18 m above the combat cross.
    if lod <= 1:
        # The four collision-authoritative upper walls are a closed citadel
        # ring.  Shallow blind arches, cornices and sparse parapet teeth turn
        # the large projectile-blocking surfaces into designed architecture.
        perimeter_upper_walls = [
            wall for wall in upper_walls
            if min(wall["w"], wall["d"]) <= 4.0
        ]
        for upper_index, wall in enumerate(perimeter_upper_walls):
            along_x = wall["w"] >= wall["d"]
            length = wall["w"] if along_x else wall["d"]
            thickness = wall["d"] if along_x else wall["w"]
            top = wall["y"] + wall["h"] / 2
            base = wall["y"] - wall["h"] / 2
            outward = (
                1 if wall["z"] >= centre_z else -1
            ) if along_x else (1 if wall["x"] >= centre_x else -1)
            for belt_y, belt_h in ((base + 0.28, 0.42), (top - 0.26, 0.46)):
                if along_x:
                    builder.add_box(
                        wall["x"], belt_y, wall["z"],
                        length + 0.62, belt_h, thickness + 0.44, "trim",
                    )
                else:
                    builder.add_box(
                        wall["x"], belt_y, wall["z"],
                        thickness + 0.44, belt_h, length + 0.62, "trim",
                    )
            bay_count = max(4, min(9 if lod == 0 else 5, int(length // 9)))
            for bay in range(bay_count):
                tangent = (
                    bay - (bay_count - 1) / 2
                ) * length * 0.82 / max(1, bay_count - 1)
                panel_y = base + wall["h"] * 0.48
                panel_w = min(3.6, length / bay_count * 0.52)
                panel_h = min(3.8, wall["h"] * 0.48)
                if along_x:
                    panel_x = wall["x"] + tangent
                    panel_z = wall["z"] + outward * (thickness / 2 + 0.07)
                    builder.add_box(
                        panel_x, panel_y, panel_z,
                        panel_w, panel_h, 0.13,
                        "wall_warm" if (bay + upper_index) % 4 else "wall_weathered",
                    )
                    builder.add_beam(
                        (panel_x - panel_w / 2, panel_y + panel_h / 2, panel_z + outward * 0.04),
                        (panel_x, panel_y + panel_h / 2 + 0.72, panel_z + outward * 0.04),
                        0.10, 0.08, "wall_weathered",
                    )
                    builder.add_beam(
                        (panel_x, panel_y + panel_h / 2 + 0.72, panel_z + outward * 0.04),
                        (panel_x + panel_w / 2, panel_y + panel_h / 2, panel_z + outward * 0.04),
                        0.10, 0.08, "wall_weathered",
                    )
                else:
                    panel_x = wall["x"] + outward * (thickness / 2 + 0.07)
                    panel_z = wall["z"] + tangent
                    builder.add_box(
                        panel_x, panel_y, panel_z,
                        0.13, panel_h, panel_w,
                        "wall_warm" if (bay + upper_index) % 4 else "wall_weathered",
                    )
                    builder.add_beam(
                        (panel_x + outward * 0.04, panel_y + panel_h / 2, panel_z - panel_w / 2),
                        (panel_x + outward * 0.04, panel_y + panel_h / 2 + 0.72, panel_z),
                        0.10, 0.08, "wall_weathered",
                    )
                    builder.add_beam(
                        (panel_x + outward * 0.04, panel_y + panel_h / 2 + 0.72, panel_z),
                        (panel_x + outward * 0.04, panel_y + panel_h / 2, panel_z + panel_w / 2),
                        0.10, 0.08, "wall_weathered",
                    )
            if lod == 0:
                tooth_count = max(5, min(10, int(length // 7)))
                for tooth in range(tooth_count):
                    tangent = (
                        tooth - (tooth_count - 1) / 2
                    ) * length * 0.88 / max(1, tooth_count - 1)
                    if along_x:
                        builder.add_box(
                            wall["x"] + tangent, top + 0.52, wall["z"],
                            1.40, 1.04, thickness + 0.34, "wall_warm",
                        )
                    else:
                        builder.add_box(
                            wall["x"], top + 0.52, wall["z"] + tangent,
                            thickness + 0.34, 1.04, 1.40, "wall_warm",
                        )

        for tower_index, tower in enumerate(towers[:4]):
            top = tower["y"] + tower["h"] / 2
            for fraction in (0.34, 0.62, 0.84):
                belt_y = tower["y"] - tower["h"] / 2 + tower["h"] * fraction
                builder.add_box(
                    tower["x"], belt_y, tower["z"],
                    tower["w"] + 0.46, 0.30, tower["d"] + 0.46,
                    "trim" if (tower_index + int(fraction * 100)) % 2 else "accent",
                )
            if lod == 0:
                face_sign_x = -1 if tower["x"] < centre_x else 1
                face_sign_z = -1 if tower["z"] < centre_z else 1
                for level in (0.42, 0.68):
                    panel_y = tower["y"] - tower["h"] / 2 + tower["h"] * level
                    builder.add_box(
                        tower["x"] - face_sign_x * (tower["w"] / 2 + 0.06),
                        panel_y,
                        tower["z"],
                        0.12,
                        min(3.8, tower["h"] * 0.13),
                        tower["d"] * 0.42,
                        "wall_weathered",
                    )
                    builder.add_box(
                        tower["x"],
                        panel_y,
                        tower["z"] - face_sign_z * (tower["d"] / 2 + 0.06),
                        tower["w"] * 0.42,
                        min(3.8, tower["h"] * 0.13),
                        0.12,
                        "wall_weathered",
                    )

        gallery_y = 27.8
        for axis in ("x", "z"):
            grouped = {}
            for tower in towers[:4]:
                key = round(tower["z"] if axis == "x" else tower["x"], 2)
                grouped.setdefault(key, []).append(tower)
            for pair in grouped.values():
                if len(pair) != 2:
                    continue
                pair.sort(key=lambda tower: tower[axis])
                builder.add_beam(
                    (pair[0]["x"], gallery_y, pair[0]["z"]),
                    (pair[1]["x"], gallery_y, pair[1]["z"]),
                    0.42 if lod == 0 else 0.58,
                    0.54,
                    "wall_warm",
                )
        # Central service platform is visibly tied into all four towers and
        # carries the mast; it is high enough never to promise traversal.
        platform_y = support_y - 2.15
        builder.add_box(
            ring_x, platform_y, ring_z,
            17.2 if lod == 0 else 15.0,
            0.70,
            17.2 if lod == 0 else 15.0,
            "wall_weathered",
        )
        builder.add_box(
            ring_x, platform_y + 0.48, ring_z,
            18.2 if lod == 0 else 16.0,
            0.26,
            18.2 if lod == 0 else 16.0,
            "trim",
        )


ARRIVAL_FRAME_STAGE_IDS = frozenset({"kunren", "souko", "nakaniwa"})
ARRIVAL_FRAME_OPENING_M = 28.0
ARRIVAL_FRAME_POST_INSET_M = 1.20
ARRIVAL_FRAME_POST_SECTION_M = 1.48
ARRIVAL_FRAME_HEADER_HEIGHT_M = 0.50
ARRIVAL_FRAME_HEADER_WALL_OVERLAP_M = 0.10
ARRIVAL_FRAME_APPROACH_LENGTH_M = 20.0
ARRIVAL_FRAME_LAMP_WIDTH_M = 0.24
ARRIVAL_FRAME_LAMP_HEIGHT_M = 1.80
ARRIVAL_FRAME_LAMP_DEPTH_M = 0.10
ARRIVAL_FRAME_LAMP_OVERLAP_M = 0.02
ARRIVAL_FRAME_GUIDE_WIDTH_M = 0.18
ARRIVAL_FRAME_GUIDE_CROSS_LIMIT_M = 10.60
ARRIVAL_FRAME_GUIDE_LANE_MARGIN_M = 0.40
ARRIVAL_FRAME_GUIDE_PROGRESS = (0.18, 0.55, 0.90)
ARRIVAL_FRAME_GUIDE_Y_M = 0.0355
ARRIVAL_FRAME_GUIDE_HEIGHT_M = 0.019


def landmark_arrival_frame_specs(placement, gate_walls):
    """Derive a collision-safe arrival frame from the two real gate walls.

    Assembly connection map (runtime X/Y/Z metres):
      ground Y=0 <-> post bottoms Y=0                       seated
      gate-wall plan A/B <-> post plan A/B                  overlap >=1.40m
      gate-wall tops <-> header bottom                      overlap 0.10m
      post tops <-> header                                  full 0.50m overlap
      post approach faces <-> LOD0 guide lamps              overlap 0.02m

    The wall pair, approach direction, opening edges and wall top are all
    measured from StageLayout data.  Constants below are construction-contract
    dimensions, never per-stage positions.  Posts sit on the *solid* side of
    each opening edge, so the authoritative 28m traversal gap is unchanged.
    """
    if len(gate_walls) != 2:
        raise RuntimeError(f"{placement['id']}: arrival frame needs exactly two gate walls")

    entrance_x, entrance_z = (float(value) for value in placement["entrance"])
    approach = placement["approach"]
    start_x, start_z = (float(value) for value in approach["start"])
    end_x, end_z = (float(value) for value in approach["end"])
    approach_dx, approach_dz = end_x - start_x, end_z - start_z
    approach_length = math.hypot(approach_dx, approach_dz)
    if approach_length <= 1e-6:
        raise RuntimeError(f"{placement['id']}: zero-length landmark approach")
    normal_x, normal_z = approach_dx / approach_length, approach_dz / approach_length
    tangent_x, tangent_z = -normal_z, normal_x
    if math.hypot(end_x - entrance_x, end_z - entrance_z) > 1e-4:
        raise RuntimeError(f"{placement['id']}: approach end does not match entrance")
    if abs(approach_length - ARRIVAL_FRAME_APPROACH_LENGTH_M) > 1e-4:
        raise RuntimeError(
            f"{placement['id']}: arrival approach {approach_length:.4f}m "
            f"!= {ARRIVAL_FRAME_APPROACH_LENGTH_M:.1f}m"
        )

    measured_walls = []
    for wall in gate_walls:
        relative_x = float(wall["x"]) - entrance_x
        relative_z = float(wall["z"]) - entrance_z
        tangent_center = relative_x * tangent_x + relative_z * tangent_z
        normal_center = relative_x * normal_x + relative_z * normal_z
        tangent_half = (
            abs(tangent_x) * float(wall["w"]) + abs(tangent_z) * float(wall["d"])
        ) / 2
        normal_span = abs(normal_x) * float(wall["w"]) + abs(normal_z) * float(wall["d"])
        if abs(tangent_center) <= 1e-6:
            raise RuntimeError(f"{placement['id']}: gate wall lies on entrance centreline")
        side = 1.0 if tangent_center > 0 else -1.0
        inner_edge = tangent_center - side * tangent_half
        measured_walls.append({
            "source": wall,
            "side": side,
            "innerEdge": inner_edge,
            "normalCenter": normal_center,
            "normalSpan": normal_span,
            "top": float(wall["y"]) + float(wall["h"]) / 2,
        })
    measured_walls.sort(key=lambda item: item["innerEdge"])
    if measured_walls[0]["side"] == measured_walls[1]["side"]:
        raise RuntimeError(f"{placement['id']}: gate walls do not bracket the entrance")

    opening_width = measured_walls[1]["innerEdge"] - measured_walls[0]["innerEdge"]
    if abs(opening_width - ARRIVAL_FRAME_OPENING_M) > 1e-4:
        raise RuntimeError(
            f"{placement['id']}: measured gate opening {opening_width:.4f}m "
            f"!= {ARRIVAL_FRAME_OPENING_M:.1f}m"
        )
    gate_top = max(item["top"] for item in measured_walls)
    if max(item["top"] for item in measured_walls) - min(item["top"] for item in measured_walls) > 1e-4:
        raise RuntimeError(f"{placement['id']}: arrival gate wall tops are not level")
    header_bottom = gate_top - ARRIVAL_FRAME_HEADER_WALL_OVERLAP_M
    header_top = header_bottom + ARRIVAL_FRAME_HEADER_HEIGHT_M
    yaw_tangent = math.atan2(tangent_z, tangent_x)

    posts = []
    for item in measured_walls:
        post_tangent = item["innerEdge"] + item["side"] * ARRIVAL_FRAME_POST_INSET_M
        normal_outset = (ARRIVAL_FRAME_POST_SECTION_M - item["normalSpan"]) / 2
        if normal_outset < -1e-4 or normal_outset > 0.0401:
            raise RuntimeError(
                f"{placement['id']}: post/wall normal outset {normal_outset:.4f}m is unsafe"
            )
        # Move the slightly thicker post inward by the half-thickness delta.
        # Its route-facing plane then matches the real wall plane exactly,
        # retaining the full 1.40m overlap without inflating landmark bounds
        # toward the authored approach.
        post_normal = item["normalCenter"] + normal_outset
        post_x = entrance_x + tangent_x * post_tangent + normal_x * post_normal
        post_z = entrance_z + tangent_z * post_tangent + normal_z * post_normal
        route_face_outset = (
            item["normalCenter"] - item["normalSpan"] / 2
            - (post_normal - ARRIVAL_FRAME_POST_SECTION_M / 2)
        )
        posts.append({
            "x": post_x,
            "y": header_top / 2,
            "z": post_z,
            "w": ARRIVAL_FRAME_POST_SECTION_M,
            "h": header_top,
            "d": ARRIVAL_FRAME_POST_SECTION_M,
            "yaw": yaw_tangent,
            "tangent": post_tangent,
            "normal": post_normal,
            "wallNormal": item["normalCenter"],
            "innerEdge": item["innerEdge"],
            "openingClearance": abs(post_tangent) - ARRIVAL_FRAME_POST_SECTION_M / 2,
            "normalOutset": normal_outset,
            "routeFaceOutset": route_face_outset,
        })
    posts.sort(key=lambda item: item["tangent"])

    header_tangent = (posts[0]["tangent"] + posts[1]["tangent"]) / 2
    header_normal = (posts[0]["normal"] + posts[1]["normal"]) / 2
    header = {
        "x": entrance_x + tangent_x * header_tangent + normal_x * header_normal,
        "y": header_bottom + ARRIVAL_FRAME_HEADER_HEIGHT_M / 2,
        "z": entrance_z + tangent_z * header_tangent + normal_z * header_normal,
        "w": posts[1]["tangent"] - posts[0]["tangent"] + ARRIVAL_FRAME_POST_SECTION_M,
        "h": ARRIVAL_FRAME_HEADER_HEIGHT_M,
        "d": ARRIVAL_FRAME_POST_SECTION_M,
        "yaw": yaw_tangent,
        "bottom": header_bottom,
        "top": header_top,
    }
    return {
        "normal": (normal_x, normal_z),
        "tangent": (tangent_x, tangent_z),
        "openingWidth": opening_width,
        "gateTop": gate_top,
        "approachLength": approach_length,
        "posts": posts,
        "header": header,
    }


def add_landmark_arrival_frame(builder, stage, lod, placement, gate_walls):
    """Emit the first-rollout arrival frame without adding gameplay cover."""
    if stage["id"] not in ARRIVAL_FRAME_STAGE_IDS or lod > 1:
        return
    specs = landmark_arrival_frame_specs(placement, gate_walls)
    post_key = {
        "kunren": "wall_cool",
        "souko": "wall_alt",
        "nakaniwa": "wood",
    }[stage["id"]]
    header_key = "roof" if stage["id"] == "nakaniwa" else "accent"
    for post in specs["posts"]:
        builder.add_oriented_box(
            post["x"], post["y"], post["z"],
            post["w"], post["h"], post["d"], post["yaw"], post_key,
        )
    header = specs["header"]
    builder.add_oriented_box(
        header["x"], header["y"], header["z"],
        header["w"], header["h"], header["d"], header["yaw"], header_key,
    )
    if lod == 0:
        normal_x, normal_z = specs["normal"]
        tangent_x, tangent_z = specs["tangent"]
        lamp_y = min(2.60, header["bottom"] * 0.34)
        for post in specs["posts"]:
            lamp_normal = post["normal"] - (
                ARRIVAL_FRAME_POST_SECTION_M / 2
                + ARRIVAL_FRAME_LAMP_DEPTH_M / 2
                - ARRIVAL_FRAME_LAMP_OVERLAP_M
            )
            lamp_x = float(placement["entrance"][0]) + tangent_x * post["tangent"] + normal_x * lamp_normal
            lamp_z = float(placement["entrance"][1]) + tangent_z * post["tangent"] + normal_z * lamp_normal
            builder.add_oriented_box(
                lamp_x, lamp_y, lamp_z,
                ARRIVAL_FRAME_LAMP_WIDTH_M,
                ARRIVAL_FRAME_LAMP_HEIGHT_M,
                ARRIVAL_FRAME_LAMP_DEPTH_M,
                math.atan2(tangent_z, tangent_x), "emissive",
            )


def add_landmark_approach_guidance(builder, stage, lod):
    """Lay a direction-readable, contact-seated pattern on each approach.

    Connection map (runtime X/Y/Z metres):
      authored road top Y=0.031 <-> guide bottom Y=0.026  overlap 0.005m
      20m lane centreline <-> longitudinal guide            contained 1:1
      lane side edges <-> three transverse guides           margin >=0.20m

    The low strip pattern is emitted by the ordinary LOD builder, not the
    landmark builder, so it cannot inflate ``hibanaLandmarkBounds``.
    """
    if stage["id"] not in ARRIVAL_FRAME_STAGE_IDS or lod > 1:
        return
    for placement in stage.get("landmarkPlacements", []):
        approach = placement["approach"]
        start_x, start_z = (float(value) for value in approach["start"])
        end_x, end_z = (float(value) for value in approach["end"])
        dx, dz = end_x - start_x, end_z - start_z
        length = math.hypot(dx, dz)
        if abs(length - ARRIVAL_FRAME_APPROACH_LENGTH_M) > 1e-4:
            raise RuntimeError(
                f"{placement['id']}: arrival approach {length:.4f}m "
                f"!= {ARRIVAL_FRAME_APPROACH_LENGTH_M:.1f}m"
            )
        normal_x, normal_z = dx / length, dz / length
        lane_width = float(approach["width"])
        transverse_length = min(
            ARRIVAL_FRAME_GUIDE_CROSS_LIMIT_M,
            lane_width - ARRIVAL_FRAME_GUIDE_LANE_MARGIN_M,
        )
        if transverse_length <= ARRIVAL_FRAME_GUIDE_WIDTH_M:
            raise RuntimeError(f"{placement['id']}: approach is too narrow for guide bands")
        midpoint_x = (start_x + end_x) / 2
        midpoint_z = (start_z + end_z) / 2
        guide_key = "roof" if stage["id"] == "nakaniwa" else "accent"
        builder.add_oriented_box(
            midpoint_x,
            ARRIVAL_FRAME_GUIDE_Y_M,
            midpoint_z,
            length,
            ARRIVAL_FRAME_GUIDE_HEIGHT_M,
            ARRIVAL_FRAME_GUIDE_WIDTH_M,
            math.atan2(dz, dx),
            guide_key,
        )
        for progress in ARRIVAL_FRAME_GUIDE_PROGRESS:
            builder.add_oriented_box(
                start_x + normal_x * length * progress,
                ARRIVAL_FRAME_GUIDE_Y_M,
                start_z + normal_z * length * progress,
                transverse_length,
                ARRIVAL_FRAME_GUIDE_HEIGHT_M,
                ARRIVAL_FRAME_GUIDE_WIDTH_M,
                math.atan2(dz, dx) + math.pi / 2,
                guide_key,
            )


def add_inbounds_landmark_visual(builder, stage, lod, placement, style, profile_landmark):
    """Render one hero directly from its TypeScript combat shell.

    The tagged BoxSpecs are the only ground-level masses.  Decorative roofs,
    crowns and facade relief are seated on those colliders and never span the
    four 28m door/interior routes.  This prevents the previous external solid
    plinth from becoming an impressive but non-enterable visual promise.
    """
    landmark_id = placement["id"]
    if landmark_id != profile_landmark["id"]:
        raise RuntimeError(
            f"{stage['id']}: profile/layout landmark drift "
            f"({profile_landmark['id']} != {landmark_id})"
        )
    shell = [box for box in stage["boxes"] if box.get("landmarkId") == landmark_id]
    if not shell:
        raise RuntimeError(f"{stage['id']}: {landmark_id} has no tagged combat shell")

    for index, box_spec in enumerate(shell):
        material = choose_box_material(box_spec, stage, index)
        if placement["id"].startswith("kairou-"):
            # District-family hashing is useful across the 31-map catalog but
            # it made individual collision slabs in the paired Kairou heroes
            # alternate blue/charcoal.  Their identity is carved limestone;
            # blue is reserved for sparse cloth/ceramic micro-accents.
            part = box_spec.get("landmarkPart")
            material = (
                "wall_weathered"
                if part in {"floor", "stair"}
                else "wall_warm"
            )
        elif stage["id"] == "souko":
            # Give the two logistics programs different construction reads on
            # their real collider shells.  Customs owns a wet brick plinth;
            # Stackhouse owns zinc/steel rack bases.  Upper walks stay dark
            # service steel, and every assignment remains on the exact solid.
            part = box_spec.get("landmarkPart")
            if placement["id"] == "souko-amakado-customs-terminal":
                material = (
                    "wall_warm"
                    if part in {"wall", "interior"}
                    else "wall_cool"
                    if part == "tower"
                    else "trim"
                    if part == "upper-walk"
                    else "wall_weathered"
                )
            else:
                material = (
                    "wall_cool"
                    if part == "tower"
                    else "trim"
                    if part == "upper-walk"
                    else "wall_weathered"
                )
        if (
            placement["id"] == "kairou-windcrown-caravan-observatory"
            and box_spec.get("landmarkPart") == "upper-wall"
            and box_spec["w"] > 10.0
            and box_spec["d"] > 10.0
        ):
            # This square is the conservative projectile proxy for the tapered
            # drum emitted by add_kairou_reference_landmark_tier1 below.
            continue
        if box_spec.get("landmarkPart") in {"column", "gate-column"}:
            # The square Rapier proxy fully contains this tapered visual shaft:
            # radius <= min(w,d)/2 and vertical extents are byte-for-byte the
            # BoxSpec bounds.  These are the eight real Kairou combat columns,
            # not facade-only decoration.  The same containment rule applies
            # to Kairou's four real three-bay gateway supports.
            if lod == 2:
                builder.add_box(
                    box_spec["x"], box_spec["y"], box_spec["z"],
                    box_spec["w"], box_spec["h"], box_spec["d"], material,
                )
                continue
            base_y = box_spec["y"] - box_spec["h"] / 2
            radius = min(box_spec["w"], box_spec["d"]) / 2
            base_h = 0.42
            capital_h = 0.54
            shaft_h = box_spec["h"] - base_h - capital_h
            segments = 14 if lod == 0 else 9
            builder.add_cylinder(
                box_spec["x"], base_y + base_h / 2, box_spec["z"],
                radius * 0.98, base_h, "wall_weathered", segments, radius * 0.91,
            )
            builder.add_cylinder(
                box_spec["x"], base_y + base_h + shaft_h / 2, box_spec["z"],
                radius * 0.88, shaft_h, "wall_warm", segments, radius * 0.72,
            )
            builder.add_cylinder(
                box_spec["x"], base_y + base_h + shaft_h + capital_h / 2, box_spec["z"],
                radius * 0.98, capital_h, "wall_weathered", segments, radius * 0.92,
            )
            if lod == 0:
                for band in (0.28, 0.66):
                    builder.add_cylinder(
                        box_spec["x"],
                        base_y + base_h + shaft_h * band,
                        box_spec["z"],
                        radius * (0.90 - band * 0.12),
                        0.14,
                        "trim",
                        segments,
                    )
            continue
        expansion = 0.045 if lod == 0 else 0.025
        builder.add_box(
            box_spec["x"], box_spec["y"], box_spec["z"],
            box_spec["w"] + expansion,
            box_spec["h"] + expansion,
            box_spec["d"] + expansion,
            material,
        )

    if lod == 2:
        # Preserve the stage-specific hero silhouette in the far LOD.  The
        # shell above remains the collision-shaped mass; this branch adds only
        # the minimal roof/crown language authored for this catalogue entry.
        add_catalog_landmark_signature(
            builder, stage, lod, placement, style, shell,
        )
        return

    walls = [
        box for box in shell
        if box.get("landmarkPart") in {"wall", "interior"}
        and box["h"] >= 4.0
    ]
    walls.sort(key=lambda box: max(box["w"], box["d"]) * box["h"], reverse=True)
    detail_limit = 18 if lod == 0 else 9
    for index, wall in enumerate(walls[:detail_limit]):
        along_x = wall["w"] >= wall["d"]
        length = wall["w"] if along_x else wall["d"]
        top = wall["y"] + wall["h"] / 2
        base = wall["y"] - wall["h"] / 2
        # Flush belts and one or two warm relief panels provide human scale
        # without recreating the rejected black window-grid pattern.
        if along_x:
            builder.add_box(wall["x"], base + wall["h"] * 0.62, wall["z"], length + 0.08, 0.16, wall["d"] + 0.12, "trim")
        else:
            builder.add_box(wall["x"], base + wall["h"] * 0.62, wall["z"], wall["w"] + 0.12, 0.16, length + 0.08, "trim")
        if lod == 0 and length >= 10 and index % 2 == 0:
            panel_count = 2 if length >= 24 else 1
            for panel in range(panel_count):
                offset = (panel - (panel_count - 1) / 2) * min(length * 0.42, 8.0)
                panel_y = base + min(4.6, wall["h"] * 0.48)
                if along_x:
                    builder.add_box(
                        wall["x"] + offset, panel_y,
                        wall["z"] - wall["d"] / 2 - 0.055,
                        min(2.2, length * 0.12), min(2.8, wall["h"] * 0.28), 0.11,
                        "accent" if (index + panel) % 3 == 0 else "wall_alt",
                    )
                else:
                    builder.add_box(
                        wall["x"] + wall["w"] / 2 + 0.055, panel_y,
                        wall["z"] + offset,
                        0.11, min(2.8, wall["h"] * 0.28), min(2.2, length * 0.12),
                        "accent" if (index + panel) % 3 == 0 else "wall_alt",
                    )
        # Roof strips are supported by the exact wall segment; doorway gaps
        # remain gaps because no roof spans separate segments.
        if index < (10 if lod == 0 else 5) and length >= 8:
            if stage["id"] == "kairou":
                # The reference uses stone beams, parapets and windcatchers;
                # blue pyramidal roof strips were the dominant blockout cue.
                builder.add_box(
                    wall["x"], top + 0.16, wall["z"],
                    wall["w"] + 0.46, 0.40, wall["d"] + 0.46, "wall_warm",
                )
                builder.add_box(
                    wall["x"], top + 0.46, wall["z"],
                    wall["w"] + 0.76, 0.20, wall["d"] + 0.70, "trim",
                )
            elif stage["id"] in {"kunren", "souko", "nakaniwa"}:
                # The first rollout maps own large profile-specific roofs in
                # add_catalog_landmark_signature.  Repeating the old gable on
                # every collider wall made all six heroes read as one castle.
                # A shallow, supported coping preserves wall weatherproofing
                # without competing with the authored silhouette.
                builder.add_box(
                    wall["x"], top + 0.14, wall["z"],
                    wall["w"] + (0.66 if stage["id"] == "nakaniwa" else 0.38),
                    0.28,
                    wall["d"] + (0.66 if stage["id"] == "nakaniwa" else 0.38),
                    "roof" if stage["id"] == "nakaniwa" else "trim",
                )
            else:
                roof_h = max(0.7, min(2.6, length * 0.055))
                if along_x:
                    builder.add_gable_roof(
                        wall["x"], top - 0.02, wall["z"],
                        wall["w"] + 0.45, roof_h, wall["d"] + 0.75,
                        "roof", "x",
                    )
                else:
                    builder.add_gable_roof(
                        wall["x"], top - 0.02, wall["z"],
                        wall["w"] + 0.75, roof_h, wall["d"] + 0.45,
                        "roof", "z",
                    )

    towers = [box for box in shell if box.get("landmarkPart") == "tower"]
    towers.sort(key=lambda box: box["h"], reverse=True)
    height_limit = float(placement["height"])
    group = landmark_geometry_group(style)
    for index, tower in enumerate(towers[:4 if lod == 0 else 2]):
        top = tower["y"] + tower["h"] / 2
        remaining = max(1.2, height_limit - top)
        crown_h = min(remaining * (0.72 if index == 0 else 0.48), height_limit * 0.24)
        radius = max(1.1, min(tower["w"], tower["d"]) * 0.56)
        if stage["id"] == "kunren":
            # Military towers terminate in supported blast decks, radar rails
            # and beacons—not the generic conical crown that made the command
            # base and aerostat hall read as a fantasy castle.
            builder.add_box(
                tower["x"], top + 0.22, tower["z"],
                tower["w"] + 0.70, 0.44, tower["d"] + 0.70, "trim",
            )
            deck_h = min(max(1.4, remaining * 0.20), 3.1)
            builder.add_box(
                tower["x"], top + 0.44 + deck_h / 2, tower["z"],
                tower["w"] * 0.76, deck_h, tower["d"] * 0.76,
                "wall_cool" if index % 2 else "wall_alt",
            )
            if lod == 0:
                builder.add_cylinder(
                    tower["x"], top + deck_h + 1.35, tower["z"],
                    0.16, 2.4, "accent", 8, 0.10,
                )
        elif stage["id"] == "souko":
            # Rack/crane towers use square service caps with exposed rails.
            builder.add_box(
                tower["x"], top + 0.20, tower["z"],
                tower["w"] + 0.82, 0.40, tower["d"] + 0.82, "accent",
            )
            builder.add_box(
                tower["x"], top + 1.05, tower["z"],
                tower["w"] * 0.70, 1.70, tower["d"] * 0.70, "wall_cool",
            )
            if lod == 0:
                for side in (-1, 1):
                    builder.add_box(
                        tower["x"] + side * tower["w"] * 0.42,
                        top + 1.55,
                        tower["z"],
                        0.12, 2.50, tower["d"] * 0.82, "trim",
                    )
        elif stage["id"] == "nakaniwa" and "palace" in style:
            # Deep verdigris eaves and a small lantern preserve the palace's
            # horizontal crown silhouette without another needle cone.
            builder.add_gable_roof(
                tower["x"], top - 0.04, tower["z"],
                radius * 3.10, max(0.85, crown_h * 0.18), radius * 3.10,
                "roof", "x",
            )
            builder.add_box(
                tower["x"], top + max(0.85, crown_h * 0.18) + 0.45,
                tower["z"], radius * 1.10, 0.90, radius * 1.10, "wall_warm",
            )
        elif stage["id"] == "nakaniwa":
            builder.add_box(
                tower["x"], top + 0.20, tower["z"],
                tower["w"] + 0.72, 0.40, tower["d"] + 0.72, "roof",
            )
            irrigation_h = min(remaining * 0.52, 6.2)
            builder.add_cylinder(
                tower["x"], top + irrigation_h / 2, tower["z"],
                radius * 0.48, irrigation_h, "wall_warm",
                10 if lod == 0 else 7, radius * 0.30,
            )
            builder.add_cylinder(
                tower["x"], top + irrigation_h + 0.18, tower["z"],
                radius * 0.66, 0.36, "roof", 10 if lod == 0 else 7,
                radius * 0.58,
            )
        elif stage["id"] == "kairou" and "hypostyle" in style:
            # Flat, stepped sanctuary crowns seated on the real corner towers.
            builder.add_box(
                tower["x"], top + 0.24, tower["z"],
                tower["w"] + 0.72, 0.48, tower["d"] + 0.72, "trim",
            )
            tier_h = min(3.8, max(2.2, remaining * 0.34))
            builder.add_box(
                tower["x"], top + 0.44 + tier_h / 2, tower["z"],
                tower["w"] * 0.78, tier_h, tower["d"] * 0.78, "wall_warm",
            )
            builder.add_box(
                tower["x"], top + 0.44 + tier_h + 0.18, tower["z"],
                tower["w"] * 0.94, 0.36, tower["d"] * 0.94, "accent",
            )
        elif stage["id"] == "kairou" and "observatory" in style:
            # Open windcatcher crown: four blades rise from the collider tower
            # top and remain visually distinct from a generic cone roof.
            wind_h = min(6.2, max(3.6, remaining * 0.58))
            blade_t = 0.52
            blade_span = min(tower["w"], tower["d"]) * 0.82
            blade_y = top + wind_h / 2
            for side in (-1, 1):
                builder.add_box(
                    tower["x"] + side * (blade_span / 2 - blade_t / 2),
                    blade_y,
                    tower["z"],
                    blade_t,
                    wind_h,
                    blade_span,
                    "wall_warm" if (index + side) % 3 else "wall_alt",
                )
                builder.add_box(
                    tower["x"],
                    blade_y,
                    tower["z"] + side * (blade_span / 2 - blade_t / 2),
                    blade_span,
                    wind_h,
                    blade_t,
                    "wall_alt" if (index + side) % 3 else "wall_warm",
                )
            builder.add_box(
                tower["x"], top + wind_h + 0.22, tower["z"],
                tower["w"] + 0.64, 0.44, tower["d"] + 0.64, "accent",
            )
        elif "pagoda" in style:
            for tier in range(3 if lod == 0 else 2):
                tier_y = top + tier * max(1.5, crown_h * 0.22)
                tier_scale = 1.75 - tier * 0.24
                builder.add_gable_roof(
                    tower["x"], tier_y, tower["z"],
                    radius * 2 * tier_scale, max(0.8, crown_h * 0.15),
                    radius * 2 * tier_scale, "roof", "x",
                )
            builder.add_cylinder(tower["x"], min(height_limit - 0.5, top + crown_h), tower["z"], 0.24, max(1.0, crown_h * 0.30), "trim", 8, 0.06)
        elif group in {"vertical", "heritage", "fortress", "ruined_heritage"}:
            top_radius = 0.18 if group != "ruined_heritage" or index % 2 == 0 else radius * 0.46
            builder.add_cylinder(
                tower["x"], top + crown_h / 2 - 0.08, tower["z"],
                radius, crown_h + 0.16, "roof", 10 if lod == 0 else 7, top_radius,
            )
        else:
            builder.add_box(tower["x"], top + 0.22, tower["z"], tower["w"] + 0.50, 0.44, tower["d"] + 0.50, "accent")
            builder.add_cylinder(
                tower["x"], top + crown_h / 2, tower["z"],
                max(0.55, radius * 0.32), crown_h, "trim", 8, 0.15,
            )

    # Style-name geometry is deliberately sparse and supported.  It supplies
    # the unique 14 silhouettes without adding a second hidden solid building.
    if len(towers) >= 2 and group == "bridge":
        left, right = towers[0], towers[1]
        bridge_y = min(left["y"] + left["h"] / 2, right["y"] + right["h"] / 2) * 0.72
        builder.add_beam(
            (left["x"], bridge_y, left["z"]),
            (right["x"], bridge_y, right["z"]),
            0.62 if lod == 0 else 0.78, 0.54, "accent",
        )
    if (
        towers
        and any(token in style for token in ("drill", "data", "observatory", "exchange"))
        and not (stage["id"] == "kairou" and "observatory" in style)
    ):
        anchor = towers[0]
        top = anchor["y"] + anchor["h"] / 2
        mast_h = max(3.0, min(height_limit - top, height_limit * 0.22))
        if mast_h > 0.5:
            builder.add_cylinder(anchor["x"], top + mast_h / 2, anchor["z"], 0.34, mast_h, "trim", 8, 0.12)
            if lod == 0:
                for side in (-1, 1):
                    builder.add_beam(
                        (anchor["x"], top + mast_h * 0.44, anchor["z"]),
                        (anchor["x"] + side * 3.2, top + mast_h * 0.70, anchor["z"]),
                        0.12, 0.10, "accent",
                    )

    # Profile-name signatures remain physically seated on the authored shell.
    # They are intentionally overhead or wall-overlapping so the exact 28 m
    # entrance and interior cross stay visually and physically open.
    entrance_x, entrance_z = (float(value) for value in placement["entrance"])
    centre_x, centre_z = float(placement["cx"]), float(placement["cz"])
    entrance_dx, entrance_dz = entrance_x - centre_x, entrance_z - centre_z

    # Make the collision-authoritative opening legible from its authored
    # approach.  The two uprights overlap the existing wall segments on the
    # *solid* side of the 28 m gap; the crosshead remains above the wall top.
    # Consequently this portal never narrows the physical entrance and never
    # creates collider-free cover at player height.  It also avoids the old
    # black-window-grid shortcut: identity comes from silhouette, construction
    # joints and a single warm header, not a matrix of dark cards.
    entrance_walls = []
    for wall in walls:
        along_x = wall["w"] >= wall["d"]
        if abs(entrance_dx) >= abs(entrance_dz):
            matches_face = not along_x and entrance_dx * (wall["x"] - centre_x) > 0
        else:
            matches_face = along_x and entrance_dz * (wall["z"] - centre_z) > 0
        if matches_face:
            entrance_walls.append(wall)
    entrance_walls.sort(
        key=lambda wall: (wall["x"] - entrance_x) ** 2 + (wall["z"] - entrance_z) ** 2
    )
    gate_walls = entrance_walls[:2]
    if len(gate_walls) == 2 and stage["id"] in ARRIVAL_FRAME_STAGE_IDS:
        add_landmark_arrival_frame(builder, stage, lod, placement, gate_walls)
    elif len(gate_walls) == 2:
        jamb_points = []
        gate_top = max(wall["y"] + wall["h"] / 2 for wall in gate_walls)
        for wall in gate_walls:
            along_x = wall["w"] >= wall["d"]
            # Kairou's 28 m opening is intentionally monumental.  A narrow,
            # articulated stone jamb leaves the scale legible; the old 1.55 m
            # post plus 1.72 m straight crosshead read as a construction beam.
            jamb_width = (
                1.18 if lod == 0 else 1.42
            ) if stage["id"] == "kairou" else (1.55 if lod == 0 else 1.85)
            jamb_extra = (
                3.20 if "hypostyle" in style else 0.72
            ) if stage["id"] == "kairou" else 2.20
            jamb_key = "wall_weathered" if stage["id"] == "kairou" else "wall_alt"
            if along_x:
                tangent_sign = 1 if wall["x"] >= centre_x else -1
                inner_edge = wall["x"] - tangent_sign * wall["w"] / 2
                jamb_x = inner_edge + tangent_sign * jamb_width / 2
                jamb_z = wall["z"]
                builder.add_box(
                    jamb_x, (gate_top + jamb_extra) / 2, jamb_z,
                    jamb_width, gate_top + jamb_extra, wall["d"] + 0.34, jamb_key,
                )
            else:
                tangent_sign = 1 if wall["z"] >= centre_z else -1
                inner_edge = wall["z"] - tangent_sign * wall["d"] / 2
                jamb_x = wall["x"]
                jamb_z = inner_edge + tangent_sign * jamb_width / 2
                builder.add_box(
                    jamb_x, (gate_top + jamb_extra) / 2, jamb_z,
                    wall["w"] + 0.34, gate_top + jamb_extra, jamb_width, jamb_key,
                )
            jamb_points.append((jamb_x, jamb_z))

        if stage["id"] == "kairou":
            horizontal_gate = abs(jamb_points[0][0] - jamb_points[1][0]) >= abs(jamb_points[0][1] - jamb_points[1][1])
            jamb_points.sort(key=lambda point: point[0] if horizontal_gate else point[1])
            # The sanctuary uses two real 2m gate columns to form a 16m central
            # road and two ~6m side arches.  The observatory keeps one broad
            # high arch because its gate has no physical intermediate support.
            face_gate_columns = []
            if "hypostyle" in style:
                for column in shell:
                    if column.get("landmarkPart") != "gate-column":
                        continue
                    if horizontal_gate and abs(column["z"] - entrance_z) <= 2.0:
                        face_gate_columns.append(column)
                    elif not horizontal_gate and abs(column["x"] - entrance_x) <= 2.0:
                        face_gate_columns.append(column)
            supports = [(point[0], point[1], gate_top + jamb_extra) for point in jamb_points]
            supports.extend(
                (column["x"], column["z"], column["y"] + column["h"] / 2)
                for column in face_gate_columns
            )
            supports.sort(key=lambda point: point[0] if horizontal_gate else point[1])
            arch_pairs = list(zip(supports, supports[1:])) if len(supports) >= 2 else []
            for arch_index, (left, right) in enumerate(arch_pairs):
                spring_y = max(left[2], right[2])
                span = math.hypot(right[0] - left[0], right[1] - left[1])
                rise = min(5.2 if lod == 0 else 4.4, max(2.4, span * 0.30))
                apex_y = spring_y + rise
                midpoint = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
                arch_segments = 4 if lod == 0 else 3
                for endpoint in (left, right):
                    previous = (endpoint[0], spring_y, endpoint[1])
                    for segment in range(1, arch_segments + 1):
                        t = segment / arch_segments
                        eased = math.sin(t * math.pi / 2) ** 0.92
                        point = (
                            endpoint[0] + (midpoint[0] - endpoint[0]) * t,
                            spring_y + (apex_y - spring_y) * eased,
                            endpoint[1] + (midpoint[1] - endpoint[1]) * t,
                        )
                        builder.add_beam(
                            previous,
                            point,
                            0.27 if lod == 0 else 0.36,
                            0.38,
                            "wall_warm" if segment % 3 else "wall_weathered",
                        )
                        previous = point
                builder.add_box(
                    midpoint[0], apex_y + 0.10, midpoint[1],
                    0.62 if horizontal_gate else 0.38,
                    0.88,
                    0.38 if horizontal_gate else 0.62,
                    "accent" if arch_index == len(arch_pairs) // 2 else "trim",
                )
            # Impost blocks seat every arch spring on either a real gate column
            # or the collision-backed outer wall jamb.
            for support_x, support_z, support_y in supports:
                builder.add_box(
                    support_x, support_y, support_z,
                    2.10 if horizontal_gate else 0.58,
                    0.44,
                    0.58 if horizontal_gate else 2.10,
                    "trim",
                )
        else:
            header_y = gate_top + 1.72
            builder.add_beam(
                (jamb_points[0][0], header_y, jamb_points[0][1]),
                (jamb_points[1][0], header_y, jamb_points[1][1]),
                0.86 if lod == 0 else 1.04,
                0.72,
                "accent",
            )
            if lod == 0:
                # A raised centre crest and two short braces read as one gateway
                # at distance while staying several metres above traversal.
                midpoint = (
                    (jamb_points[0][0] + jamb_points[1][0]) / 2,
                    (jamb_points[0][1] + jamb_points[1][1]) / 2,
                )
                crest_y = header_y + 2.35
                builder.add_beam(
                    (jamb_points[0][0], header_y + 0.18, jamb_points[0][1]),
                    (midpoint[0], crest_y, midpoint[1]),
                    0.34, 0.28, "trim",
                )
                builder.add_beam(
                    (midpoint[0], crest_y, midpoint[1]),
                    (jamb_points[1][0], header_y + 0.18, jamb_points[1][1]),
                    0.34, 0.28, "trim",
                )
                builder.add_box(
                    midpoint[0], crest_y + 0.12, midpoint[1],
                    1.15 if abs(entrance_dx) < abs(entrance_dz) else 0.18,
                    1.05,
                    0.18 if abs(entrance_dx) < abs(entrance_dz) else 1.15,
                    "emissive" if stage["palette"].get("mood") == "night" else "accent",
                )

    columns = [box for box in shell if box.get("landmarkPart") == "column"]
    upper_walls = [box for box in shell if box.get("landmarkPart") == "upper-wall"]
    add_kairou_reference_landmark_tier1(
        builder, lod, placement, style, walls, towers, columns, upper_walls,
    )
    add_catalog_landmark_signature(
        builder, stage, lod, placement, style, shell,
    )

    if "hypostyle" in style and stage["id"] != "kairou":
        # A split colonnade sits against the two real entrance-wall segments;
        # no column is generated in the central gate opening.
        for wall in entrance_walls[:2]:
            along_x = wall["w"] >= wall["d"]
            length = wall["w"] if along_x else wall["d"]
            column_count = 5 if lod == 0 and length >= 30 else 3
            column_h = min(wall["h"] * 0.82, height_limit * 0.28)
            radius = max(0.42, min(0.78, length * 0.022))
            for column_index in range(column_count):
                offset = (column_index - (column_count - 1) / 2) * length * 0.72 / max(1, column_count - 1)
                if along_x:
                    column_x = wall["x"] + offset
                    column_z = wall["z"] + math.copysign(wall["d"] / 2 + radius * 0.32, entrance_dz)
                else:
                    column_x = wall["x"] + math.copysign(wall["w"] / 2 + radius * 0.32, entrance_dx)
                    column_z = wall["z"] + offset
                builder.add_cylinder(
                    column_x, column_h / 2, column_z,
                    radius, column_h, "wall_alt", 10 if lod == 0 else 7,
                    radius * 0.82,
                )

    if towers and "observatory" in style and stage["id"] != "kairou":
        for dome_index, tower in enumerate(towers[:3 if lod == 0 else 2]):
            top = tower["y"] + tower["h"] / 2
            radius = max(1.4, min(tower["w"], tower["d"]) * (0.46 - dome_index * 0.05))
            dome_h = min(radius * 0.82, max(1.0, height_limit - top - 0.3))
            if dome_h > 0.75:
                builder.add_cylinder(
                    tower["x"], top + dome_h / 2 - 0.04, tower["z"],
                    radius, dome_h, "glass", 14 if lod == 0 else 9, 0.22,
                )

    if towers and "windtower" in style and stage["id"] != "kairou":
        for wind_index, tower in enumerate(towers[:4 if lod == 0 else 2]):
            top = tower["y"] + tower["h"] / 2
            wind_h = min(height_limit - top - 0.25, height_limit * (0.11 + wind_index * 0.012))
            if wind_h <= 0.8:
                continue
            fin_w = max(0.24, min(tower["w"], tower["d"]) * 0.08)
            builder.add_box(
                tower["x"], top + wind_h / 2, tower["z"],
                tower["w"] * 0.66, wind_h, fin_w, "wall_alt",
            )
            builder.add_box(
                tower["x"], top + wind_h / 2, tower["z"],
                fin_w, wind_h, tower["d"] * 0.66, "accent",
            )

    if len(towers) >= 3 and ("tripod" in style or "arcology" in style):
        supports = towers[:3]
        support_tops = [tower["y"] + tower["h"] / 2 for tower in supports]
        apex_y = min(height_limit - 0.8, max(support_tops) + height_limit * 0.18)
        apex = (
            sum(tower["x"] for tower in supports) / len(supports),
            apex_y,
            sum(tower["z"] for tower in supports) / len(supports),
        )
        for tower, support_top in zip(supports, support_tops):
            builder.add_beam(
                (tower["x"], support_top - 0.20, tower["z"]),
                apex,
                0.68 if lod == 0 else 0.82,
                0.52,
                "accent",
            )
        builder.add_cylinder(
            apex[0], apex_y + 0.45, apex[2],
            1.10 if lod == 0 else 0.86, 0.90, "emissive", 10 if lod == 0 else 7, 0.32,
        )

    if len(towers) >= 2 and "ship-lift" in style:
        left, right = towers[0], towers[1]
        left_top = left["y"] + left["h"] / 2
        right_top = right["y"] + right["h"] / 2
        gantry_y = min(left_top, right_top) - 0.45
        # Two grounded towers carry the lifting crosshead. Cables terminate on
        # the shell's upper walk rather than floating into the combat lane.
        builder.add_beam(
            (left["x"], gantry_y, left["z"]),
            (right["x"], gantry_y, right["z"]),
            1.18 if lod == 0 else 1.36, 0.82, "trim",
        )
        if lod == 0:
            mid_x = (left["x"] + right["x"]) / 2
            mid_z = (left["z"] + right["z"]) / 2
            for cable_offset in (-4.4, 4.4):
                cable_x = mid_x + cable_offset if abs(left["x"] - right["x"]) >= abs(left["z"] - right["z"]) else mid_x
                cable_z = mid_z if cable_x != mid_x else mid_z + cable_offset
                builder.add_cylinder(cable_x, gantry_y - 4.2, cable_z, 0.10, 8.4, "trim", 6, 0.08)

    if towers and any(token in style for token in ("drill", "needle")):
        anchor = towers[0]
        tower_top = anchor["y"] + anchor["h"] / 2
        drill_h = max(2.0, height_limit - tower_top - 0.5)
        drill_radius = max(1.5, min(anchor["w"], anchor["d"]) * 0.48)
        turns = 12 if lod == 0 else 7
        for turn in range(turns):
            angle_a = math.tau * turn * 0.42
            angle_b = math.tau * (turn + 1) * 0.42
            y_a = tower_top + drill_h * turn / turns
            y_b = tower_top + drill_h * (turn + 1) / turns
            builder.add_beam(
                (
                    anchor["x"] + math.cos(angle_a) * drill_radius,
                    y_a,
                    anchor["z"] + math.sin(angle_a) * drill_radius,
                ),
                (
                    anchor["x"] + math.cos(angle_b) * drill_radius,
                    y_b,
                    anchor["z"] + math.sin(angle_b) * drill_radius,
                ),
                0.20 if lod == 0 else 0.28,
                0.16,
                "accent",
            )


def add_profile_mega_landmark(builder, stage, lod, landmark_index, style, profile_landmark):
    """Build one profile-defined castle-scale structure as seated real mesh.

    Assembly connection map:
      ground -> plinth (0..10% H) -> primary masses (8%..62% H)
      -> upper masses/bridges (58%..84% H) -> crown (82%..100% H).
    Every tower overlaps its plinth by 0.18m; every bridge penetrates both
    supports by >=0.45m; roof bottoms equal the wall tops.  Landmark footprints
    are placed fully outside the authoritative play square, so these visual
    volumes cannot create walk-through collision or block a live route.
    """
    dimensions = profile_landmark["dimensionsM"]
    vista = landmark_spawn_vista(stage, landmark_index, profile_landmark)
    width = vista["width"]
    depth = vista["depth"]
    height = vista["height"]
    x, z, yaw = vista["x"], vista["z"], vista["yaw"]
    variant = MEGA_LANDMARK_ORDER[(stage["id"], landmark_index)]
    detail = lod == 0
    medium = lod <= 1
    group = landmark_geometry_group(style)
    cosine, sine = math.cos(yaw), math.sin(yaw)

    def point(local_x, local_z):
        return x + local_x * cosine - local_z * sine, z + local_x * sine + local_z * cosine

    def box(local_x, local_y, local_z, w, h, d, key):
        px, pz = point(local_x, local_z)
        builder.add_oriented_box(px, local_y, pz, w, h, d, yaw, key)

    def cylinder(local_x, local_y, local_z, radius, cylinder_height, key, segments=10, top_radius=None):
        px, pz = point(local_x, local_z)
        builder.add_cylinder(px, local_y, pz, radius, cylinder_height, key, segments, top_radius)

    def beam(start, end, beam_width, beam_depth, key="trim"):
        sx, sz = point(start[0], start[2])
        ex, ez = point(end[0], end[2])
        builder.add_beam((sx, start[1], sz), (ex, end[1], ez), beam_width, beam_depth, key)

    def vertical_ring(local_x, center_y, local_z, radius, ring_segments=14, key="trim"):
        for ring_index in range(ring_segments):
            angle_a = math.tau * ring_index / ring_segments
            angle_b = math.tau * (ring_index + 1) / ring_segments
            beam(
                (local_x + math.cos(angle_a) * radius, center_y + math.sin(angle_a) * radius, local_z),
                (local_x + math.cos(angle_b) * radius, center_y + math.sin(angle_b) * radius, local_z),
                max(0.18, radius * 0.025),
                max(0.14, radius * 0.018),
                key,
            )

    def gable(local_x, base_y, local_z, roof_width, roof_height, roof_depth, key="accent"):
        px, pz = point(local_x, local_z)
        builder.add_oriented_gable_roof(px, base_y, pz, roof_width, roof_height, roof_depth, yaw, key)

    # Two overlapping foundation tiers make the contact unambiguous from all
    # six QA directions and give every landmark a human-scale entrance datum.
    base_h = max(3.6, height * 0.095)
    box(0, base_h * 0.34, 0, width, base_h * 0.68, depth, "terrain")
    box(0, base_h * 0.78, 0, width * 0.92, base_h * 0.52, depth * 0.90, "wall_alt")

    segments = 12 if detail else 8 if medium else 6
    asymmetry = (stable_unit(stage["seed"], variant, 0xA771) - 0.5) * width * 0.10
    primary_top = base_h

    if group == "bridge":
        pylon_h = height * (0.72 + (variant % 3) * 0.045)
        pylon_w = max(6.0, width * (0.11 + (variant % 2) * 0.025))
        spacing = width * (0.29 + (variant % 4) * 0.018)
        for side in (-1, 1):
            box(side * spacing, base_h + pylon_h / 2, 0, pylon_w, pylon_h, depth * 0.34, "wall_alt" if side < 0 else "wall")
            if detail:
                for brace in (-1, 1):
                    beam((side * spacing - pylon_w * 0.42, base_h + pylon_h * 0.18, brace * depth * 0.15),
                         (side * spacing + pylon_w * 0.42, base_h + pylon_h * 0.66, brace * depth * 0.15), 0.34, 0.28, "trim")
        for level in (0.36, 0.68):
            bridge_y = base_h + pylon_h * level
            box(0, bridge_y, 0, spacing * 2 + pylon_w * 1.10, max(1.2, height * 0.035), depth * (0.20 if level < 0.5 else 0.13), "accent" if level > 0.5 else "wall")
        primary_top = base_h + pylon_h
    elif group == "radial":
        radius = min(width, depth) * (0.31 + (variant % 3) * 0.018)
        cylinder(0, base_h + height * 0.16, 0, radius, height * 0.32, "wall_alt", segments, radius * 0.88)
        tower_h = height * 0.60
        cylinder(asymmetry * 0.35, base_h + tower_h / 2, 0, radius * 0.34, tower_h, "wall", segments, radius * 0.20)
        arms = 5 + variant % 4 if detail else 4
        for arm in range(arms):
            angle = math.tau * arm / arms + (variant % 5) * 0.07
            ax, az = math.cos(angle) * radius * 0.64, math.sin(angle) * radius * 0.64
            wing_x, wing_z = point(ax, az)
            builder.add_oriented_box(wing_x, base_h + height * 0.23, wing_z, radius * 0.72, height * 0.24, radius * 0.28, yaw - angle, "wall_alt" if arm % 2 else "wall")
        if "ferris" in style:
            wheel_radius = min(width * 0.30, height * 0.38)
            wheel_center_y = base_h + wheel_radius + height * 0.08
            wheel_segments = 18 if detail else 10
            for item in range(wheel_segments):
                a0, a1 = math.tau * item / wheel_segments, math.tau * (item + 1) / wheel_segments
                if detail and item in {(variant + 3) % wheel_segments, (variant + 4) % wheel_segments}:
                    continue
                beam((math.cos(a0) * wheel_radius, wheel_center_y + math.sin(a0) * wheel_radius, -depth * 0.23),
                     (math.cos(a1) * wheel_radius, wheel_center_y + math.sin(a1) * wheel_radius, -depth * 0.23), 0.32, 0.28, "trim")
        primary_top = base_h + tower_h
    elif group == "hall":
        hall_h = height * (0.48 + (variant % 4) * 0.035)
        box(0, base_h + hall_h / 2, 0, width * 0.90, hall_h, depth * 0.74, "wall")
        roof_bays = 2 + variant % 4 if detail else 2
        bay_width = width * 0.92 / roof_bays
        for bay in range(roof_bays):
            gable((bay - (roof_bays - 1) / 2) * bay_width, base_h + hall_h, 0, bay_width + 0.32, height * 0.12, depth * 0.78, "accent" if bay % 2 == variant % 2 else "trim")
        tower_w = width * (0.16 + (variant % 3) * 0.018)
        tower_h = height * (0.72 + (variant % 2) * 0.10)
        box(width * 0.29 + asymmetry, base_h + tower_h / 2, -depth * 0.08, tower_w, tower_h, depth * 0.28, "wall_alt")
        primary_top = base_h + tower_h
    elif group == "industrial":
        hall_h = height * 0.40
        box(-width * 0.08, base_h + hall_h / 2, 0, width * 0.78, hall_h, depth * 0.72, "wall_alt")
        stack_count = 2 + variant % 3 if detail else 2
        for stack in range(stack_count):
            local_x = (stack - (stack_count - 1) / 2) * width * 0.15 + asymmetry
            stack_h = height * (0.62 + stack * 0.06 + (variant % 2) * 0.05)
            cylinder(local_x, base_h + stack_h / 2, -depth * 0.12, width * 0.025 + 0.8, stack_h, "trim", segments, width * 0.018 + 0.55)
            cylinder(local_x, base_h + stack_h + 0.7, -depth * 0.12, width * 0.034 + 0.9, 1.4, "emissive" if stage["id"].startswith("z") else "accent", segments)
        if medium:
            for level in (0.28, 0.52):
                beam((-width * 0.44, base_h + height * level, depth * 0.28),
                     (width * 0.42, base_h + height * level, depth * 0.28), 0.34, 0.30, "accent" if level > 0.4 else "trim")
        primary_top = base_h + height * 0.82
    elif group == "vertical":
        tier_specs = ((0.58, 0.42), (0.38, 0.27), (0.22, 0.18))
        tier_y = base_h
        for tier, (scale_x, scale_z) in enumerate(tier_specs):
            tier_h = height * (0.27 if tier < 2 else 0.22)
            local_x = asymmetry * tier * 0.36
            local_z = ((variant + tier) % 3 - 1) * depth * 0.035
            box(local_x, tier_y + tier_h / 2, local_z, width * scale_x, tier_h, depth * scale_z, "wall_alt" if tier % 2 == 0 else "wall")
            tier_y += tier_h
        cylinder(asymmetry * 0.9, tier_y + height * 0.08, 0, max(1.2, width * 0.045), height * 0.16, "accent", segments, 0.20)
        primary_top = tier_y + height * 0.16
    elif group == "megablock":
        block_count = 3 if medium else 2
        block_centers = []
        for block in range(block_count):
            local_x = (block - (block_count - 1) / 2) * width * 0.25
            local_z = ((block + variant) % 3 - 1) * depth * 0.12
            block_h = height * (0.48 + ((block + variant) % 4) * 0.09)
            block_centers.append((local_x, local_z, block_h))
            box(local_x, base_h + block_h / 2, local_z, width * 0.30, block_h, depth * 0.46, "wall_alt" if block % 2 else "wall")
        if medium:
            for left, right in zip(block_centers, block_centers[1:]):
                bridge_y = base_h + min(left[2], right[2]) * (0.54 + (variant % 2) * 0.10)
                beam((left[0], bridge_y, left[1]), (right[0], bridge_y, right[1]), 0.62, 1.15, "accent")
        primary_top = base_h + max(item[2] for item in block_centers)
    elif group == "ruined_heritage":
        # Z04 must not reuse Takadai's intact abbey.  Build an original,
        # asymmetrical ruin whose missing nave and snapped twin spires are
        # readable as negative space from the playable square.  Every surviving
        # mass remains seated in the common plinth; the diagonal buttresses
        # penetrate their supports, so the ruin never reads as exploded parts.
        nave_h = height * 0.38
        box(-width * 0.19, base_h + nave_h / 2, 0, width * 0.30, nave_h, depth * 0.58, "wall")
        box(width * 0.24, base_h + nave_h * 0.42, -depth * 0.05, width * 0.22, nave_h * 0.84, depth * 0.48, "wall_alt")
        gable(-width * 0.19, base_h + nave_h, 0, width * 0.31, height * 0.10, depth * 0.61, "accent")

        tower_specs = (
            (-width * 0.34, -depth * 0.22, height * 0.78),
            (width * 0.30, depth * 0.20, height * 0.55),
            (width * 0.36, -depth * 0.22, height * 0.68),
        )
        for tower_index, (tx, tz, tower_h) in enumerate(tower_specs):
            box(tx, base_h + tower_h / 2, tz, width * 0.105, tower_h, depth * 0.13, "wall_alt" if tower_index == 1 else "wall")
            if tower_index != 1:
                # One cap is deliberately absent; the others are different
                # heights and pitches instead of copies of Takadai's cone set.
                gable(tx, base_h + tower_h, tz, width * 0.13, height * (0.07 + tower_index * 0.012), depth * 0.16, "accent")

        if medium:
            # Broken flying buttresses and a suspended rose-window ring frame
            # the missing central volume without filling the combat horizon.
            for side in (-1, 1):
                beam(
                    (side * width * 0.31, base_h + height * 0.18, depth * 0.23),
                    (side * width * 0.19, base_h + height * (0.49 if side < 0 else 0.40), depth * 0.06),
                    0.42,
                    0.34,
                    "trim",
                )
            rose_radius = min(width, height) * 0.105
            vertical_ring(0, base_h + height * 0.47, depth * 0.25, rose_radius, 14 if detail else 9, "accent")
        primary_top = base_h + height * 0.86
    elif group == "heritage":
        hall_h = height * 0.43
        box(0, base_h + hall_h / 2, 0, width * 0.72, hall_h, depth * 0.58, "wall")
        gable(0, base_h + hall_h, 0, width * 0.76, height * 0.14, depth * 0.63, "accent")
        tower_count = 2 + 2 * (variant % 2) if detail else 2
        for tower in range(tower_count):
            side = -1 if tower % 2 == 0 else 1
            row = -1 if tower < 2 else 1
            tx, tz = side * width * 0.34, row * depth * 0.24
            tower_h = height * (0.62 + (tower + variant) % 3 * 0.08)
            box(tx, base_h + tower_h / 2, tz, width * 0.12, tower_h, depth * 0.14, "wall_alt")
            cylinder(tx, base_h + tower_h + height * 0.055, tz, width * 0.09, height * 0.11, "accent", segments, 0.18)
        primary_top = base_h + height * 0.86
    else:  # fortress
        tier_y = base_h
        for tier in range(3 if medium else 2):
            tier_h = height * (0.18 + tier * 0.025)
            scale = 0.86 - tier * 0.17
            box(asymmetry * tier * 0.24, tier_y + tier_h / 2, 0, width * scale, tier_h, depth * scale, "wall_alt" if tier % 2 == 0 else "wall")
            tier_y += tier_h
        tower_count = 4 if detail else 2
        for tower in range(tower_count):
            side_x = -1 if tower % 2 == 0 else 1
            side_z = -1 if tower < 2 else 1
            tx, tz = side_x * width * 0.36, side_z * depth * 0.34
            tower_h = height * (0.58 + ((tower + variant) % 3) * 0.07)
            cylinder(tx, base_h + tower_h / 2, tz, width * 0.055 + 1.8, tower_h, "wall", segments, width * 0.045 + 1.2)
        primary_top = max(tier_y, base_h + height * 0.78)

    # Profile-name signatures are explicit geometry, not texture decals. They
    # make the 62 catalog entries recognisable even when several share the same
    # basic construction grammar.
    if "pagoda" in style:
        pagoda_x = -width * 0.17
        for tier in range(4 if detail else 3):
            tier_y = base_h + height * (0.30 + tier * 0.12)
            tier_width = width * (0.34 - tier * 0.045)
            box(pagoda_x, tier_y, -depth * 0.06, tier_width, max(0.55, height * 0.018), depth * (0.30 - tier * 0.025), "accent")
        cylinder(pagoda_x, base_h + height * 0.83, -depth * 0.06, 0.34, height * 0.20, "trim", 8, 0.08)
    if "conservatory" in style:
        fan_count = 7 if detail else 4
        fan_y = base_h + height * 0.34
        for fan in range(fan_count):
            local_x = (fan - (fan_count - 1) / 2) * width * 0.055
            beam((local_x, base_h + height * 0.12, depth * 0.24), (local_x * 0.42, fan_y + height * 0.22, -depth * 0.04), 0.20, 0.16, "accent")
            box(local_x, fan_y, depth * 0.13, width * 0.045, height * 0.34, 0.10, "glass")
    if "observatory" in style:
        for dome_index in range(3):
            local_x = (dome_index - 1) * width * 0.19
            dome_radius = width * (0.095 + (dome_index % 2) * 0.018)
            cylinder(local_x, base_h + height * (0.58 + dome_index * 0.035), -depth * 0.08, dome_radius, dome_radius * 0.76, "glass", segments, 0.18)
    if "lighthouse" in style:
        light_x = width * 0.28
        light_h = height * 0.78
        cylinder(light_x, base_h + light_h / 2, -depth * 0.06, width * 0.055, light_h, "wall", segments, width * 0.036)
        cylinder(light_x, base_h + light_h + height * 0.035, -depth * 0.06, width * 0.075, height * 0.07, "glass", segments, width * 0.065)
    if any(token in style for token in ("waterwheel", "clock", "ferris")) and "firewatch" not in style:
        wheel_radius = min(width, height) * (0.15 if "clock" in style else 0.22)
        wheel_x = width * (-0.24 if variant % 2 else 0.24)
        wheel_y = base_h + height * (0.48 if "clock" in style else 0.32)
        wheel_z = depth * 0.38
        vertical_ring(wheel_x, wheel_y, wheel_z, wheel_radius, 16 if detail else 10, "accent")
        if detail:
            for spoke in range(0, 8, 2):
                angle = math.tau * spoke / 8
                beam((wheel_x, wheel_y, wheel_z), (wheel_x + math.cos(angle) * wheel_radius, wheel_y + math.sin(angle) * wheel_radius, wheel_z), 0.13, 0.11, "trim")
    if any(token in style for token in ("drill", "needle")):
        drill_x = width * 0.24
        drill_base_y = base_h + height * 0.20
        drill_h = height * 0.67
        cylinder(drill_x, drill_base_y + drill_h / 2, -depth * 0.10, width * 0.045, drill_h, "trim", segments, 0.16)
        if detail:
            turns = 10
            for turn in range(turns):
                angle_a = math.tau * turn * 0.46
                angle_b = math.tau * (turn + 1) * 0.46
                y_a = drill_base_y + drill_h * turn / turns
                y_b = drill_base_y + drill_h * (turn + 1) / turns
                radius = width * 0.072
                beam((drill_x + math.cos(angle_a) * radius, y_a, -depth * 0.10 + math.sin(angle_a) * radius),
                     (drill_x + math.cos(angle_b) * radius, y_b, -depth * 0.10 + math.sin(angle_b) * radius), 0.15, 0.12, "accent")
    if "tripod" in style or "arcology" in style:
        apex = (asymmetry * 0.4, base_h + height * 0.82, 0)
        for leg in range(3):
            angle = math.tau * leg / 3 + 0.4
            beam((math.cos(angle) * width * 0.31, base_h, math.sin(angle) * depth * 0.30), apex, width * 0.018, width * 0.014, "trim")
    if any(token in style for token in ("broadcast", "data-cathedral", "control-citadel")):
        mast_count = 3 + variant % 3 if detail else 2
        for mast in range(mast_count):
            mast_x = (mast - (mast_count - 1) / 2) * width * 0.08
            mast_base = base_h + height * (0.68 + (mast % 2) * 0.05)
            beam((mast_x, mast_base, -depth * 0.04), (mast_x + asymmetry * 0.08, mast_base + height * (0.18 + mast * 0.015), -depth * 0.04), 0.16, 0.13, "emissive" if stage["palette"].get("mood") == "night" else "accent")
    if any(token in style for token in ("mirror", "glass")) and "storm-glass" not in style:
        panel_count = 5 if detail else 3
        for panel in range(panel_count):
            local_x = (panel - (panel_count - 1) / 2) * width * 0.11
            panel_h = height * (0.24 + (panel + variant) % 3 * 0.05)
            box(local_x, base_h + panel_h / 2, depth * 0.39, width * 0.065, panel_h, 0.16, "glass")
    if any(token in style for token in ("target", "quarantine")):
        panel_count = 5 if detail else 3
        for panel in range(panel_count):
            local_x = (panel - (panel_count - 1) / 2) * width * 0.13
            panel_h = height * (0.18 + (panel % 2) * 0.06)
            box(local_x, base_h + panel_h / 2, depth * 0.47, width * 0.075, panel_h, 0.24, "accent" if panel % 2 else "wall_alt")
    if any(token in style for token in ("palace", "opera")):
        dome_radius = width * 0.11
        cylinder(-width * 0.16, base_h + height * 0.68, -depth * 0.08, dome_radius, dome_radius * 0.88, "accent", segments, 0.20)
        cylinder(width * 0.17, base_h + height * 0.60, depth * 0.02, dome_radius * 0.72, dome_radius * 0.64, "accent", segments, 0.16)
    if "hypostyle" in style:
        # The desert sanctuary needs a column forest silhouette, not merely a
        # generic palace hall. Keep it outside traversal but readable through
        # the north vista at human scale.
        column_count = 9 if detail else 5
        column_y = base_h + height * 0.18
        for column_index in range(column_count):
            column_x = (column_index - (column_count - 1) / 2) * width * 0.62 / max(1, column_count - 1)
            cylinder(column_x, column_y, depth * 0.39, width * 0.012 + 0.30, height * 0.31, "wall_alt", 8 if detail else 6, width * 0.009 + 0.22)
        box(0, base_h + height * 0.345, depth * 0.39, width * 0.76, height * 0.035, depth * 0.08, "accent")
    if "windtower" in style:
        for tower_index, tower_x in enumerate((-0.30, -0.10, 0.14, 0.31)):
            tower_h = height * (0.44 + tower_index * 0.055)
            box(tower_x * width, base_h + tower_h / 2, -depth * 0.08, width * 0.075, tower_h, depth * 0.12, "wall_alt" if tower_index % 2 else "wall")
            if detail:
                box(tower_x * width, base_h + tower_h * 0.82, depth * 0.01, width * 0.050, tower_h * 0.16, depth * 0.025, "glass")

    # Player-facing entry, windows and one variant-specific crown make scale
    # and identity readable in the actual FPS camera, not only in hero renders.
    entry_w = max(4.4, width * 0.10)
    box(0, base_h + height * 0.105, depth * 0.452, entry_w, height * 0.21, 0.32, "trim")
    window_levels = 4 if detail else 2 if medium else 1
    window_bays = 7 if detail else 4 if medium else 2
    for level in range(window_levels):
        pane_y = base_h + height * (0.22 + level * 0.105)
        for bay in range(window_bays):
            local_x = (bay - (window_bays - 1) / 2) * width * 0.60 / max(1, window_bays - 1)
            if (bay + level + variant) % 9 == 0 and stage["id"].startswith("z"):
                continue
            box(local_x, pane_y, depth * 0.456, max(0.9, width * 0.045), max(1.1, height * 0.035), 0.18,
                "emissive" if stage["palette"].get("mood") == "night" and (bay + level + variant) % 4 == 0 else "glass")

    if detail:
        # Side elevations and floor belts keep castle-scale masses from reading
        # as one decorated front card. The unique profile prose controls the
        # rhythm, while all pieces stay flush to the solid authored volume.
        landmark_signature = stable_text_signature(
            style,
            profile_landmark["silhouette"],
            profile_landmark["facade"],
        )
        side_levels = 2 + landmark_signature % 3
        side_bays = 3 + (landmark_signature >> 3) % 3
        side_pane_h = max(1.2, height * (0.027 + ((landmark_signature >> 6) % 3) * 0.004))
        for level in range(side_levels):
            pane_y = base_h + height * (0.23 + level * 0.115)
            belt_y = pane_y + side_pane_h * 0.78
            box(0, belt_y, 0, width * 0.82, 0.18, depth * 0.74, "trim" if level % 2 else "accent")
            for side in (-1, 1):
                pane_x = side * width * 0.412
                for bay in range(side_bays):
                    if stage["id"].startswith("z") and (bay + level + variant) % 7 == 0:
                        continue
                    pane_z = (bay - (side_bays - 1) / 2) * depth * 0.58 / max(1, side_bays - 1)
                    box(pane_x, pane_y, pane_z, 0.18, side_pane_h + 0.30, max(1.0, depth * 0.050), "trim")
                    box(pane_x + side * 0.11, pane_y, pane_z, 0.08, side_pane_h, max(0.78, depth * 0.039), "glass")

        # Four seated corner piers provide contact scale and a different
        # buttress rhythm for every profile-derived signature.
        buttress_h = height * (0.31 + ((landmark_signature >> 9) % 4) * 0.025)
        for side_x in (-1, 1):
            for side_z in (-1, 1):
                box(
                    side_x * width * 0.415,
                    base_h + buttress_h / 2,
                    side_z * depth * 0.365,
                    max(0.62, width * 0.022),
                    buttress_h,
                    max(0.62, depth * 0.025),
                    "wall_alt" if (side_x + side_z + variant) % 3 else "accent",
                )

    fin_count = 2 + variant % 5 if detail else 1
    crown_y = min(height, max(primary_top, base_h + height * 0.72))
    for fin in range(fin_count):
        local_x = (fin - (fin_count - 1) / 2) * width * 0.10
        fin_h = height * (0.08 + ((variant + fin) % 4) * 0.018)
        beam((local_x, crown_y - 0.35, 0), (local_x + asymmetry * 0.14, crown_y + fin_h, 0), 0.20, 0.17, "accent" if fin == variant % fin_count else "trim")


def build_landmark_objects(collection, materials, stage, lod):
    """Build and label two independently auditable landmark mesh groups.

    Each landmark gets its own material-batched mesh namespace.  This costs a
    small, bounded number of draw calls but lets release validation prove that
    both profile IDs own non-empty, spatially distinct geometry instead of
    trusting a comma-separated declaration copied onto unrelated meshes.
    """
    profile_landmarks = PROFILES[stage["id"]]["megaLandmarks"]
    styles = MEGA_LANDMARK_STYLES[stage["id"]]
    if len(profile_landmarks) != 2 or len(styles) != 2:
        raise RuntimeError(f"{stage['id']} must define exactly two mega-landmarks")
    inbounds_placements = stage.get("landmarkPlacements", [])
    if inbounds_placements and len(inbounds_placements) != 2:
        raise RuntimeError(f"{stage['id']} exported {len(inbounds_placements)} in-bounds landmarks")
    result = []
    for landmark_index, (style, profile_landmark) in enumerate(zip(styles, profile_landmarks)):
        landmark_builder = MeshBuilder(
            collection,
            f"HB_{stage['id']}_LOD{lod}_LANDMARK_{landmark_index}",
            materials,
            0.055 if stage["id"] == "souko" and lod == 0 else 0.0,
        )
        placement = inbounds_placements[landmark_index] if inbounds_placements else None
        if placement and placement.get("collisionTemplate") == "abbey":
            # Takadai/Z04's central abbey is built 1:1 against the authored TS
            # collider plan.  First emit those exact tagged boxes, then seat the
            # Gothic roof/crown treatment over them.
            add_inbounds_landmark_visual(
                landmark_builder,
                stage,
                2,
                placement,
                style,
                profile_landmark,
            )
            add_abbey_visual(landmark_builder, stage, lod)
        elif placement:
            add_inbounds_landmark_visual(
                landmark_builder,
                stage,
                lod,
                placement,
                style,
                profile_landmark,
            )
        elif style.startswith("existing-"):
            add_abbey_visual(landmark_builder, stage, lod)
        else:
            add_profile_mega_landmark(
                landmark_builder,
                stage,
                lod,
                landmark_index,
                style,
                profile_landmark,
            )
        objects = landmark_builder.flush()
        if not objects:
            raise RuntimeError(
                f"{stage['id']} LOD{lod} landmark {profile_landmark['id']} produced no mesh"
            )
        runtime_points = []
        for obj in objects:
            for vertex in obj.data.vertices:
                coordinate = vertex.co
                runtime_points.append((coordinate.x, coordinate.z, -coordinate.y))
        minimum = [min(point[axis] for point in runtime_points) for axis in range(3)]
        maximum = [max(point[axis] for point in runtime_points) for axis in range(3)]
        bounds = [round(value, 4) for value in minimum + maximum]
        spawn_metrics = landmark_bounds_spawn_metrics(stage, bounds)
        dimensions = (
            {
                "width": placement["width"],
                "height": placement["height"],
                "depth": placement["depth"],
            }
            if placement
            else profile_landmark["dimensionsM"]
        )
        for obj in objects:
            obj["hibanaLandmarkId"] = placement["id"] if placement else profile_landmark["id"]
            obj["hibanaLandmarkIndex"] = landmark_index
            obj["hibanaLandmarkStyle"] = style
            obj["hibanaLandmarkBounds"] = bounds
            obj["hibanaLandmarkTargetDimensionsXYZ"] = [
                float(dimensions["width"]),
                float(dimensions["height"]),
                float(dimensions["depth"]),
            ]
            obj["hibanaLandmarkPlacement"] = (
                "in-bounds-collision-authoritative" if placement else profile_landmark["placement"]
            )
            obj["hibanaLandmarkCombatSpace"] = bool(placement and placement.get("combatSpace"))
            obj["hibanaLandmarkGrounded"] = bool(placement and placement.get("grounded"))
            if placement:
                obj["hibanaLandmarkEntranceXZ"] = list(placement["entrance"])
                obj["hibanaLandmarkApproachStartXZ"] = list(placement["approach"]["start"])
                obj["hibanaLandmarkApproachEndXZ"] = list(placement["approach"]["end"])
            obj["hibanaLandmarkSpawnBearingDeg"] = spawn_metrics["bearingDeg"]
            obj["hibanaLandmarkSpawnDistanceM"] = spawn_metrics["distanceM"]
            obj["hibanaLandmarkAngularHeightDeg"] = spawn_metrics["angularHeightDeg"]
            obj["hibanaLandmarkVistaReadable"] = spawn_metrics["readable"]
        result.extend(objects)
    return result


# Per-stage build_nakaniwa_a23_specs() info dicts (nakaniwa_a23_reconciliation),
# keyed by stage id. Populated by build_nakaniwa_reference_lod at LOD0 only
# (the A23 round never touched LOD1/2) and available for any future
# metadata/report consumer that wants the palace-fix/district-plan detail
# without recomputing the whole LOD0 chain.
NAKANIWA_A23_RECONCILIATION_REPORTS = {}


def build_nakaniwa_reference_lod(stage, lod, collection, materials):
    """Build the A21-R6 Nakaniwa kit as city plus two auditable hero batches.

    LOD0 goes through NAKANIWA_A23_RECONCILIATION.build_nakaniwa_a23_specs,
    which reproduces the A23 round's proven best build (near-field garden,
    reclamation, material split, hero-defect fixes, district infill and the
    Tier 1 palace-occlusion recovery -- see that module's docstring). LOD1/2
    were never touched by the A23 round and use NAKANIWA_REFERENCE_A21_R6's
    own base build_specs(lod) unmodified, matching every LOD's behaviour
    before this reconciliation.
    """
    if len(stage.get("landmarkPlacements", [])) != 2:
        raise RuntimeError("Nakaniwa A21-R6 requires exactly two canonical landmark placements")
    if lod == 0:
        specs, a23_info = NAKANIWA_A23_RECONCILIATION.build_nakaniwa_a23_specs(lod)
        NAKANIWA_A23_RECONCILIATION_REPORTS[stage["id"]] = a23_info
    else:
        specs = NAKANIWA_REFERENCE_A21_R6.build_specs(lod)
    expected_landmarks = {
        placement["id"]: placement
        for placement in stage["landmarkPlacements"]
    }
    module_landmarks = {item["id"] for item in NAKANIWA_REFERENCE_A21_R6.LANDMARKS}
    if set(expected_landmarks) != module_landmarks:
        raise RuntimeError(
            "Nakaniwa A21-R6 landmark IDs do not match the canonical solver layout: "
            f"module={sorted(module_landmarks)} layout={sorted(expected_landmarks)}"
        )

    # The H26 hero-defect-fix arcade-glazing rebuild re-tags its new specs
    # under its own private group (HERO_FIX_GROUP) rather than the palace's
    # landmark group id, faithfully matching the ported private study (see
    # nakaniwa_a23_reconciliation.py's module docstring). Attribute those
    # specs back to the palace landmark bucket here, at the integration
    # point, so hibanaLandmarkBounds/spawn-metrics stay accurate without
    # changing the ported fix's own geometry or group tagging.
    hero_fix_group = NAKANIWA_A23_RECONCILIATION.HERO_FIX_GROUP
    palace_id = NAKANIWA_REFERENCE_A21_R6.PALACE_ID

    def spec_landmark_id(spec):
        if spec["group"] in expected_landmarks:
            return spec["group"]
        if lod == 0 and spec["group"] == hero_fix_group:
            return palace_id
        return None

    # R6's own DEFAULT_INTEGRATION_MATERIAL_MAP is an identity map (correct
    # only for R6's own Blender render harness -- see
    # NAKANIWA_A23_RECONCILIATION.INTEGRATION_MATERIAL_MAP's own docstring).
    # This MeshBuilder integration needs the hand-built remap onto
    # build_all_stages.py's own material vocabulary instead, mirroring the
    # retired A18 kit's own DEFAULT_INTEGRATION_MATERIAL_MAP.
    integration_material_map = NAKANIWA_A23_RECONCILIATION.INTEGRATION_MATERIAL_MAP
    city_specs = [spec for spec in specs if spec_landmark_id(spec) is None]
    city_builder = MeshBuilder(collection, f"HB_nakaniwa_LOD{lod}_A21R6_CITY", materials, 0.0)
    city_material_map = dict(integration_material_map)
    # moss_stone is the ground/paving material after the A23 material split
    # (H7/H8's ground remap; see materials.NAKANIWA_GROUND_TARGET_MATERIAL).
    # The plaza/canal foundation is the authored real 3D ground and horizon
    # shell.  Tagging only the city copy as terrain satisfies the release
    # ownership contract without reclassifying landmark stonework.
    city_material_map["moss_stone"] = "terrain"
    # R6's own emit_specs_to_builder assumes R6's own A21MeshBuilder shape
    # (add_chamfer_box/add_sweep/add_leaf_cluster), which build_all_stages.py's
    # MeshBuilder does not implement -- see
    # NAKANIWA_A23_RECONCILIATION.emit_specs_to_mesh_builder's own docstring.
    NAKANIWA_A23_RECONCILIATION.emit_specs_to_mesh_builder(
        city_builder, city_specs, city_material_map
    )
    objects = city_builder.flush()

    for landmark_index, landmark in enumerate(NAKANIWA_REFERENCE_A21_R6.LANDMARKS):
        landmark_id = landmark["id"]
        placement = expected_landmarks[landmark_id]
        landmark_specs = [spec for spec in specs if spec_landmark_id(spec) == landmark_id]
        if not landmark_specs:
            raise RuntimeError(f"Nakaniwa A21-R6 {landmark_id} emitted no geometry")
        landmark_builder = MeshBuilder(
            collection,
            f"HB_nakaniwa_LOD{lod}_LANDMARK_{landmark_index}",
            materials,
            0.0,
        )
        NAKANIWA_A23_RECONCILIATION.emit_specs_to_mesh_builder(
            landmark_builder, landmark_specs, integration_material_map
        )
        landmark_objects = landmark_builder.flush()
        # Metadata must match the exported mesh accessor bounds, including the
        # true-normal thickness of tapered surface panels.  Spec envelopes are
        # intentionally conservative and therefore cannot serve as an exact
        # release declaration.
        runtime_corners = []
        for landmark_object in landmark_objects:
            for local_corner in landmark_object.bound_box:
                world_corner = landmark_object.matrix_world @ Vector(local_corner)
                runtime_corners.append(
                    (world_corner.x, world_corner.z, -world_corner.y)
                )
        if not runtime_corners:
            raise RuntimeError(f"Nakaniwa A21-R6 {landmark_id} has no mesh bounds")
        bounds = [
            min(item[0] for item in runtime_corners),
            min(item[1] for item in runtime_corners),
            min(item[2] for item in runtime_corners),
            max(item[0] for item in runtime_corners),
            max(item[1] for item in runtime_corners),
            max(item[2] for item in runtime_corners),
        ]
        spawn_metrics = landmark_bounds_spawn_metrics(stage, bounds)
        for obj in landmark_objects:
            obj["hibanaLandmarkId"] = landmark_id
            obj["hibanaLandmarkIndex"] = landmark_index
            obj["hibanaLandmarkStyle"] = MEGA_LANDMARK_STYLES["nakaniwa"][landmark_index]
            obj["hibanaLandmarkBounds"] = [round(value, 4) for value in bounds]
            obj["hibanaLandmarkTargetDimensionsXYZ"] = [
                float(placement["width"]),
                float(placement["height"]),
                float(placement["depth"]),
            ]
            obj["hibanaLandmarkPlacement"] = "in-bounds-collision-authoritative"
            obj["hibanaLandmarkCombatSpace"] = bool(placement.get("combatSpace"))
            obj["hibanaLandmarkGrounded"] = bool(placement.get("grounded"))
            obj["hibanaLandmarkEntranceXZ"] = list(placement["entrance"])
            obj["hibanaLandmarkApproachStartXZ"] = list(placement["approach"]["start"])
            obj["hibanaLandmarkApproachEndXZ"] = list(placement["approach"]["end"])
            obj["hibanaLandmarkSpawnBearingDeg"] = spawn_metrics["bearingDeg"]
            obj["hibanaLandmarkSpawnDistanceM"] = spawn_metrics["distanceM"]
            obj["hibanaLandmarkAngularHeightDeg"] = spawn_metrics["angularHeightDeg"]
            obj["hibanaLandmarkVistaReadable"] = spawn_metrics["readable"]
        objects.extend(landmark_objects)
    return objects


# Per-stage plan_district_infill() reports (a23_bridge), keyed by stage id.
# Populated by add_a23_district_infill at LOD0 and read back by build_lod's
# metadata-stamping loop for every LOD of the same stage build. See
# add_a23_district_infill's own docstring for why this is LOD0-only.
A23_DISTRICT_INFILL_REPORTS = {}


def add_a23_district_infill(builder, stage, lod):
    """Emit the promoted tools/blender/a23 toolchain's district-infill layer
    (districts.plan_district + reclamation.run_chain, i.e. occlusion-aware
    articulation priority, the contract-derived window rhythm, and
    reclamation passes 3+4 with pass 3 -- the mandatory correctness fix --
    always in the chain) for whichever stage this call is building, unless
    that stage is opted out via a23_bridge.STAGE_POLICY.

    LOD0 only: like every other fine-detail pass in this file (see
    add_architectural_skin's own `if lod == 2: return`), the infill is
    purely decorative recessed-window/cornice/roof detail with no collision
    meaning -- src/game/stage.ts and stages.ts remain the sole collision
    authority, and this layer's own scanline packer only ever places new
    mass in map cells stage_boxes_as_specs + the canonical-road/spawn
    exclusion grid have already marked genuinely empty (see
    tools/blender/a23_bridge.py's module docstring).

    nakaniwa is excluded structurally (its build never calls this function
    at all -- see build_lod below) as well as via the opt-in table, so it
    can never be double-treated even if a future edit changes call order.
    """
    if lod != 0:
        return
    stage_id = stage["id"]
    if not a23_bridge.stage_enabled(stage_id):
        return
    profile = PROFILES[stage_id]
    family = IDENTITIES[stage_id][0]
    mood = stage["palette"].get("mood")
    plan = a23_bridge.plan_district_infill(stage, profile, family, mood)
    a23_bridge.emit_specs_to_mesh_builder(builder, plan["specs"])
    A23_DISTRICT_INFILL_REPORTS[stage_id] = {key: value for key, value in plan.items() if key != "specs"}


def build_lod(stage, lod, collection, materials):
    # The merged PBR normal/roughness maps provide edge breakup at FPS scale.
    # A mesh bevel on a material-wide batch duplicates vertices for thousands
    # of disconnected boxes and costs megabytes while being sub-pixel in play.
    # Silhouette roofs, fins, arches and beams remain explicit geometry.
    bevel = 0.0
    if stage["id"] == "nakaniwa":
        objects = build_nakaniwa_reference_lod(stage, lod, collection, materials)
    else:
        builder = MeshBuilder(collection, f"HB_{stage['id']}_LOD{lod}", materials, bevel)
        builder.add_box(0, -0.09, 0, stage["size"] + 2, 0.18, stage["size"] + 2, "floor")
        add_routes(builder, stage, lod)
        add_landmark_approach_guidance(builder, stage, lod)
        add_route_set_dressing(builder, stage, lod)
        add_district_public_realm(builder, stage, lod)
        add_ground_character(builder, stage, lod)
        add_layout_shell(builder, stage, lod)
        # add_playable_district_facades supersedes the former single-face window
        # strip pass. Keeping both produced coplanar panes and unnecessary draw
        # density on the exact buildings players inspect most closely.
        add_playable_district_rooflines(builder, stage, lod)
        add_playable_district_facades(builder, stage, lod)
        add_kairou_reference_city_tier2(builder, stage, lod)
        add_authoritative_wall_facades(builder, stage, lod)
        add_stage_authoritative_wayfinding(builder, stage, lod)
        add_blender_props(builder, stage, lod)
        add_boundary(builder, stage, lod)
        add_stage_dressing(builder, stage, lod)
        add_exterior_architecture(builder, stage, lod)
        add_skyline(builder, stage, lod)
        add_a23_district_infill(builder, stage, lod)
        objects = builder.flush()
        objects.extend(build_landmark_objects(collection, materials, stage, lod))
    landmark_ids = [item["id"] for item in PROFILES[stage["id"]]["megaLandmarks"]]
    city_profile = PROFILES[stage["id"]]["cityProfile"]
    kairou_ordinary_districts = sum(
        1
        for placement in stage.get("districtPlacements", [])
        if not any(
            placement["cx"] == landmark["cx"]
            and placement["cz"] == landmark["cz"]
            and placement["width"] == landmark["width"]
            and placement["depth"] == landmark["depth"]
            for landmark in stage.get("landmarkPlacements", [])
        )
    )
    a23_policy = a23_bridge.STAGE_POLICY.get(stage["id"])
    a23_report = A23_DISTRICT_INFILL_REPORTS.get(stage["id"]) if lod == 0 else None
    for obj in objects:
        obj["hibanaStage"] = stage["id"]
        obj["hibanaLod"] = lod
        obj["hibanaMegaLandmarks"] = ",".join(landmark_ids)
        obj["hibanaA23DistrictInfillEnabled"] = bool(a23_policy and a23_policy.enabled)
        obj["hibanaA23DistrictInfillReason"] = a23_policy.reason if a23_policy else ""
        obj["hibanaA23DistrictInfillApplied"] = a23_report is not None
        if a23_report is not None:
            obj["hibanaA23DistrictInfillBlocks"] = int(a23_report["districtPlan"]["blockCount"])
            obj["hibanaA23DistrictInfillTriangles"] = int(a23_report["estimatedTriangles"])
            obj["hibanaA23DistrictInfillAuditsPassed"] = bool(a23_report["auditsPassed"])
        obj["hibanaCityArchetype"] = city_profile["archetype"]
        obj["hibanaDenseBuildingTarget"] = int(city_profile["targetBuildingCount"][1])
        obj["hibanaGeneratorVersion"] = GENERATOR_VERSION
        obj["hibanaGeneratorSha"] = GENERATOR_SHA
        obj["hibanaPlacementSource"] = LAYOUT_PLACEMENT_SOURCE
        if LAYOUT_PLACEMENT_SOLVER_SHA:
            obj["hibanaPlacementSolverSha256"] = LAYOUT_PLACEMENT_SOLVER_SHA
        if LAYOUT_STAGE_WORLD_CATALOG_SHA:
            obj["hibanaStageWorldCatalogSha256"] = LAYOUT_STAGE_WORLD_CATALOG_SHA
        obj["hibanaStageLayoutSha256"] = STAGE_LAYOUT_SHA_BY_ID[stage["id"]]
        if stage["id"] == "souko":
            obj["hibanaSoukoReferenceMatchVersion"] = SOUKO_REFERENCE_MATCH_VERSION
            obj["hibanaSoukoStackhouseSkybridgeBottomM"] = SOUKO_STACKHOUSE_SKYBRIDGE_BOTTOM_M
            obj["hibanaSoukoCustomsRoofBaseM"] = SOUKO_CUSTOMS_ROOF_BASE_M
            obj["hibanaSoukoEastCoast3D"] = True
        if stage["id"] == "nakaniwa":
            obj["hibanaNakaniwaReferenceMatchVersion"] = NAKANIWA_REFERENCE_A21_R6.KIT_VERSION
            obj["hibanaNakaniwaReferenceSourceSha256"] = NAKANIWA_REFERENCE_SOURCE_SHA
            obj["hibanaNakaniwaReferenceGate"] = "NO-SHIP-pending-independent-post-tier1-review"
            a23_nakaniwa_report = NAKANIWA_A23_RECONCILIATION_REPORTS.get(stage["id"]) if lod == 0 else None
            obj["hibanaNakaniwaA23ReconciliationApplied"] = a23_nakaniwa_report is not None
            if a23_nakaniwa_report is not None:
                obj["hibanaNakaniwaA23PalaceOcclusionFixSpecsMoved"] = int(
                    a23_nakaniwa_report["palaceFix"]["totalSpecsMoved"]
                )
                obj["hibanaNakaniwaA23DistrictInfillBlocks"] = int(
                    a23_nakaniwa_report["districtPlan"]["blockCount"]
                )
        if stage["id"] == "kairou":
            obj["hibanaKairouCollisionBackedVisualBuildingCount"] = kairou_ordinary_districts * 2
    return objects


def set_collection_visible(collection, visible):
    collection.hide_viewport = not visible
    collection.hide_render = not visible


def select_collection(collection):
    bpy.ops.object.select_all(action="DESELECT")
    selected = []
    def visit(current):
        for obj in current.objects:
            # The full floor is useful for deterministic Blender QA renders,
            # but Hibana already has a richer gameplay floor shader. Exporting
            # this shell would cover that shader and create a flat duplicate.
            if obj.type == "MESH" and obj.get("hibanaMaterial") != "floor":
                obj.hide_set(False)
                obj.select_set(True)
                selected.append(obj)
        for child in current.children:
            visit(child)
    visit(collection)
    if selected:
        bpy.context.view_layer.objects.active = selected[0]
    return selected


def export_lod(stage, lod, collection):
    set_collection_visible(collection, True)
    selected = select_collection(collection)
    filepath = OUTPUT_DIR + f"/{stage['id']}-lod{lod}.glb"
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        # Normal-mapped PBR materials need a stable tangent frame.  Relying
        # on each WebGL implementation to synthesize it produced 1,953
        # Khronos portability warnings across the 93 stage LODs.  Export the
        # Blender/MikkTSpace frame once so lighting is deterministic in the
        # browser and in downstream tools.
        # The release optimizer generates MikkTSpace tangents only for
        # normal-mapped primitives. Exporting them indiscriminately here adds
        # unused GPU attributes to glass, emissive and untextured surfaces.
        export_tangents=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )
    bpy.ops.object.select_all(action="DESELECT")
    return {"path": filepath, "objects": len(selected)}


def point_camera(camera, target):
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def configure_presentation(stage, qa_collection):
    scene = bpy.context.scene
    size = stage["size"]
    palette = stage["palette"]
    profile = PROFILES[stage["id"]]
    camera_data = bpy.data.cameras.new(f"HB_{stage['id']}_QA_CAMERA_DATA")
    camera = bpy.data.objects.new(f"HB_{stage['id']}_QA_CAMERA", camera_data)
    qa_collection.objects.link(camera)
    is_abbey = IDENTITIES[stage["id"]][1] in {"grand-abbey", "ruined-abbey"}
    camera_data.lens = 44 if is_abbey else 38
    camera_data.sensor_width = 36
    camera_angle = math.radians(profile["cameraAzimuth"])
    camera_radius = size * min(profile["cameraRadius"], 0.64 if is_abbey else 0.50)
    camera.location = runtime_point(
        math.cos(camera_angle) * camera_radius,
        size * min(profile["cameraHeight"], 0.30 if is_abbey else 0.20),
        math.sin(camera_angle) * camera_radius,
    )
    # All hero landmarks sit beyond the north route.  Aim partway toward that
    # district so the QA render proves the stage identity instead of framing
    # only the center-floor collision shell.
    point_camera(
        camera,
        runtime_point(0, profile["targetHeight"], -size * (0.04 if is_abbey else 0.27)),
    )
    scene.camera = camera

    sun_data = bpy.data.lights.new(f"HB_{stage['id']}_SUN_DATA", "SUN")
    sun_data.energy = max(1.8, stage["palette"].get("lightIntensity", 2.4))
    sun_data.angle = math.radians(8)
    if stage["id"] == "kairou":
        sun_data.color = hex_rgb("#f2c18c")
        sun_data.energy = 3.15
        sun_data.angle = math.radians(4.0)
    elif stage["id"] == "nakaniwa":
        # Warm garden sun and a broad penumbra separate ivory stone, honey
        # masonry, verdigris and translucent glass without a raster HDRI.
        sun_data.color = hex_rgb("#f4cf98")
        sun_data.energy = 3.05
        sun_data.angle = math.radians(4.2)
    elif stage["id"] == "souko":
        # Low golden coastal sun against a cool overcast world reproduces the
        # reference's wet specular separation without a raster HDRI/matte.
        sun_data.color = hex_rgb("#f3c58f")
        sun_data.energy = 3.30
        sun_data.angle = math.radians(4.8)
    sun = bpy.data.objects.new(f"HB_{stage['id']}_SUN", sun_data)
    qa_collection.objects.link(sun)
    sun_azimuth = math.radians(profile["sunAzimuth"])
    sun_elevation = math.radians(profile["sunElevation"])
    sun.location = runtime_point(
        math.cos(sun_azimuth) * math.cos(sun_elevation) * size,
        math.sin(sun_elevation) * size,
        math.sin(sun_azimuth) * math.cos(sun_elevation) * size,
    )
    point_camera(sun, runtime_point(0, 0, 0))

    fill_data = bpy.data.lights.new(f"HB_{stage['id']}_FILL_DATA", "AREA")
    mood = palette.get("mood")
    fill_data.energy = 2200 if mood == "night" else 1550 if mood == "dusk" else 1050 if stage["id"].startswith("z") else 780
    fill_data.shape = "DISK"
    fill_data.size = size * 0.6
    fill_data.color = (
        hex_rgb("#aab7c8")
        if stage["id"] == "kairou"
        else hex_rgb("#a7c0b6")
        if stage["id"] == "nakaniwa"
        else hex_rgb("#9fb2c2")
        if stage["id"] == "souko"
        else hex_rgb(palette["lightColor"])
    )
    if stage["id"] == "kairou":
        fill_data.energy = 980
    elif stage["id"] == "nakaniwa":
        fill_data.energy = 1280
    elif stage["id"] == "souko":
        fill_data.energy = 1780
    fill = bpy.data.objects.new(f"HB_{stage['id']}_FILL", fill_data)
    qa_collection.objects.link(fill)
    fill.location = runtime_point(-size * 0.25, size * 0.3, -size * 0.1)
    point_camera(fill, runtime_point(0, 4, 0))

    if mood in {"night", "dusk"}:
        accent_color = hex_rgb(palette["accent"])
        for index, (x, z) in enumerate(((-0.28, -0.30), (0.24, -0.22), (0.04, 0.18))):
            accent_data = bpy.data.lights.new(f"HB_{stage['id']}_ACCENT_{index}_DATA", "AREA")
            accent_data.energy = 1250 if mood == "night" else 760
            accent_data.shape = "DISK"
            accent_data.size = size * 0.12
            accent_data.color = accent_color
            accent_light = bpy.data.objects.new(f"HB_{stage['id']}_ACCENT_{index}", accent_data)
            qa_collection.objects.link(accent_light)
            accent_light.location = runtime_point(size * x, size * 0.12, size * z)
            point_camera(accent_light, runtime_point(0, 3, -size * 0.12))

    world = scene.world or bpy.data.worlds.new(f"HB_{stage['id']}_WORLD")
    scene.world = world
    world.use_nodes = True
    presentation_sky = (
        "#aab7c8"
        if stage["id"] == "kairou"
        else "#9eb9b5"
        if stage["id"] == "nakaniwa"
        else "#8fa7b5"
        if stage["id"] == "souko"
        else palette["sky"]
    )
    world.color = hex_rgb(presentation_sky)
    background = next(
        (node for node in world.node_tree.nodes if node.bl_idname == "ShaderNodeBackground"),
        None,
    )
    if background:
        background.inputs[0].default_value = (*hex_rgb(presentation_sky), 1.0)
        mood_strength = {
            "day": 0.30,
            "overcast": 0.38,
            "dusk": 0.23,
            "night": 0.28,
            "snow": 0.42,
        }.get(palette.get("mood"), 0.26)
        background.inputs[1].default_value = mood_strength
        if stage["id"] in {"kairou", "nakaniwa", "souko"}:
            # A procedural physical sky adds horizon/zenith depth and a warm
            # atmospheric shoulder without relying on a distant raster matte.
            sky_name = (
                "HB_KAIROU_NISHITA"
                if stage["id"] == "kairou"
                else "HB_NAKANIWA_NISHITA"
                if stage["id"] == "nakaniwa"
                else "HB_SOUKO_NISHITA"
            )
            sky = world.node_tree.nodes.get(sky_name)
            if sky is None:
                sky = world.node_tree.nodes.new("ShaderNodeTexSky")
                sky.name = sky_name
            sky_types = {
                item.identifier
                for item in sky.bl_rna.properties["sky_type"].enum_items
            }
            # Blender 5.2's headless Eevee path currently evaluates the new
            # MULTIPLE_SCATTERING world as near-black.  HOSEK_WILKIE remains a
            # physical analytic sky and is stable in both headless QA and the
            # interactive viewport, so prefer it until that regression clears.
            sky.sky_type = (
                "HOSEK_WILKIE"
                if "HOSEK_WILKIE" in sky_types
                else "PREETHAM"
                if "PREETHAM" in sky_types
                else next(iter(sky_types))
            )
            sky.sun_disc = True
            sky.sun_size = math.radians(1.8 if stage["id"] == "souko" else 1.1)
            sky.sun_intensity = 0.48 if stage["id"] == "souko" else 0.55
            sky.sun_elevation = math.radians(20 if stage["id"] == "souko" else 24)
            sky.sun_rotation = math.radians(126 if stage["id"] == "souko" else 138)
            sky.altitude = 0.10 if stage["id"] == "souko" else 0.25
            sky.air_density = 1.02 if stage["id"] == "souko" else 1.05
            if hasattr(sky, "dust_density"):
                sky.dust_density = 1.9 if stage["id"] == "souko" else 2.4
            sky.ozone_density = 1.0
            sky.turbidity = 3.2 if stage["id"] == "souko" else 3.4
            sky.ground_albedo = 0.22 if stage["id"] == "souko" else 0.24
            world.node_tree.links.new(sky.outputs["Color"], background.inputs[0])
            background.inputs[1].default_value = 1.08 if stage["id"] == "souko" else 0.72
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = RENDER_DIR + f"/{stage['id']}.png"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.look = (
        "AgX - Medium Low Contrast"
        if stage["id"] == "kairou"
        else "AgX - Medium High Contrast"
    )
    scene.view_settings.exposure = (
        0.68
        if stage["id"] == "kairou"
        else 0.52
        if stage["id"] == "nakaniwa"
        else 0.88
        if stage["id"] == "souko"
        else 1.48 if mood == "night"
        else 0.42 if mood == "dusk"
        else 0.12 if mood == "overcast"
        else 0.0
    )
    return camera


def focus_visible_viewport():
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            area.spaces.active.shading.type = "MATERIAL"
            region = next((item for item in area.regions if item.type == "WINDOW"), None)
            if region:
                with bpy.context.temp_override(window=window, screen=screen, area=area, region=region):
                    try:
                        bpy.ops.view3d.view_camera()
                    except RuntimeError:
                        pass


def write_progress(payload):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def stage_metrics(stage, lod_collections):
    metrics = {"stage": stage["id"], "lods": {}}
    for lod, collection in enumerate(lod_collections):
        vertices = 0
        polygons = 0
        objects = 0
        facade_panes = 0
        max_equal_size_repeat = 0
        min_wall_clearance = 1.0
        max_wall_clearance = 0.0
        min_frame_recess = 1.0
        near_coplanar = 0
        floating = 0
        embedded = 0
        dark_cards = 0
        for obj in collection.objects:
            if obj.type != "MESH":
                continue
            objects += 1
            vertices += len(obj.data.vertices)
            polygons += len(obj.data.polygons)
            facade_panes += int(obj.get("hibanaFacadeGlassPaneCount", 0))
            max_equal_size_repeat = max(
                max_equal_size_repeat,
                int(obj.get("hibanaFacadeGlassMaxEqualSizeRepeat", 0)),
            )
            min_wall_clearance = min(
                min_wall_clearance,
                float(obj.get("hibanaFacadeGlassMinWallClearanceM", 1.0)),
            )
            max_wall_clearance = max(
                max_wall_clearance,
                float(obj.get("hibanaFacadeGlassMaxWallClearanceM", 0.0)),
            )
            min_frame_recess = min(
                min_frame_recess,
                float(obj.get("hibanaFacadeGlassMinFrameRecessM", 1.0)),
            )
            near_coplanar += int(obj.get("hibanaFacadeGlassNearCoplanarCount", 0))
            floating += int(obj.get("hibanaFacadeGlassFloatingCount", 0))
            embedded += int(obj.get("hibanaFacadeGlassEmbeddedCount", 0))
            dark_cards += int(obj.get("hibanaFacadeDarkCardCount", 0))
        metrics["lods"][str(lod)] = {
            "objects": objects,
            "vertices": vertices,
            "polygons": polygons,
            "facadeGlassPanes": facade_panes,
            "facadeGlassMaxEqualSizeRepeat": max_equal_size_repeat,
            "facadeGlassMinWallClearanceM": min_wall_clearance,
            "facadeGlassMaxWallClearanceM": max_wall_clearance,
            "facadeGlassMinFrameRecessM": min_frame_recess,
            "facadeGlassNearCoplanarCount": near_coplanar,
            "facadeGlassFloatingCount": floating,
            "facadeGlassEmbeddedCount": embedded,
            "facadeDarkCardCount": dark_cards,
        }
    return metrics


def validate_facade_glass_metrics(stage, metrics):
    """Fail generation if the rejected global pane-grid pattern regresses."""
    # Mirror the stricter independent post-export release gate.  Keeping the
    # generator looser would waste a complete Blender/meshopt cycle only for
    # the shipped GLB to be rejected later.
    pane_limits = (120, 48, 0)
    # LOD reduction must also simplify dark/shallow facade plates rather than
    # carrying an LOD0 card wall into every distance tier. Kairou is the
    # production proof and therefore ships with the stricter no-card contract
    # at every tier; the staged limits are the explicit gate for the remaining
    # 30 maps during their later rollout.
    dark_card_limits = (0, 0, 0) if stage["id"] == "kairou" else (96, 32, 0)
    for lod, pane_limit in enumerate(pane_limits):
        report = metrics["lods"][str(lod)]
        if report["facadeGlassPanes"] > pane_limit:
            raise RuntimeError(
                f"{stage['id']} LOD{lod}: facade glass pane count "
                f"{report['facadeGlassPanes']} exceeds {pane_limit}"
            )
        if report["facadeGlassMaxEqualSizeRepeat"] > 16:
            raise RuntimeError(
                f"{stage['id']} LOD{lod}: repeated equal-size pane run "
                f"{report['facadeGlassMaxEqualSizeRepeat']} exceeds 16"
            )
        if report["facadeGlassNearCoplanarCount"] != 0:
            raise RuntimeError(
                f"{stage['id']} LOD{lod}: {report['facadeGlassNearCoplanarCount']} "
                "near-coplanar facade panes"
            )
        if report["facadeGlassFloatingCount"] != 0:
            raise RuntimeError(
                f"{stage['id']} LOD{lod}: {report['facadeGlassFloatingCount']} "
                "floating facade panes"
            )
        if report["facadeGlassEmbeddedCount"] != 0:
            raise RuntimeError(
                f"{stage['id']} LOD{lod}: {report['facadeGlassEmbeddedCount']} "
                "embedded facade panes"
            )
        if report["facadeGlassPanes"] > 0:
            if report["facadeGlassMinWallClearanceM"] < 0.008:
                raise RuntimeError(f"{stage['id']} LOD{lod}: facade pane wall clearance below 8mm")
            if report["facadeGlassMaxWallClearanceM"] > 0.060:
                raise RuntimeError(f"{stage['id']} LOD{lod}: facade pane wall clearance above 60mm")
            if report["facadeGlassMinFrameRecessM"] < 0.080:
                raise RuntimeError(f"{stage['id']} LOD{lod}: facade frame recess below 80mm")
        dark_card_limit = dark_card_limits[lod]
        if report["facadeDarkCardCount"] > dark_card_limit:
            raise RuntimeError(
                f"{stage['id']} LOD{lod}: thin dark facade-card count "
                f"{report['facadeDarkCardCount']} exceeds {dark_card_limit}"
            )


def build_stage(stage, index, total):
    clear_generated()
    root = new_collection(f"HB_{stage['id']}_ROOT")
    guides = new_collection(f"HB_{stage['id']}_00_GUIDES", root)
    lod0 = new_collection(f"HB_{stage['id']}_90_EXPORT_LOD0", root)
    lod1 = new_collection(f"HB_{stage['id']}_90_EXPORT_LOD1", root)
    lod2 = new_collection(f"HB_{stage['id']}_90_EXPORT_LOD2", root)
    qa = new_collection(f"HB_{stage['id']}_QA", guides)
    materials = build_materials(stage)
    build_lod(stage, 0, lod0, materials)
    build_lod(stage, 1, lod1, materials)
    build_lod(stage, 2, lod2, materials)
    configure_presentation(stage, qa)

    exports = []
    for lod, collection in enumerate((lod0, lod1, lod2)):
        exports.append(export_lod(stage, lod, collection))
        set_collection_visible(collection, lod == 0)
    focus_visible_viewport()
    bpy.context.scene.render.filepath = RENDER_DIR + f"/{stage['id']}.png"
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=WORK_DIR + f"/{stage['id']}.blend", copy=True)
    metrics = stage_metrics(stage, (lod0, lod1, lod2))
    validate_facade_glass_metrics(stage, metrics)
    metrics["exports"] = exports
    write_progress({
        "status": "building",
        "current": index + 1,
        "total": total,
        "stage": stage["id"],
        "name": stage["name"],
        "metrics": metrics,
    })
    return metrics


def stage_asset_min_tier():
    """Lowest tier whose selected stage LOD fits the authored budget."""
    # Runtime sourcePlanForTier selects LOD1 for medium and LOD0 for high; it
    # does not load LOD0 merely because the entry is medium-eligible. Keep the
    # entry available on medium, then gate LOD1 <=3.0 MB and LOD0 <=5.5 MB in
    # the post-build audit.
    return "medium"


def write_manifest(stages):
    assets = []
    for stage in stages:
        assets.append({
            "id": "stage-" + stage["id"],
            "url": f"stages/{stage['id']}-lod0.glb",
            "stages": [stage["id"]],
            "instances": [{"position": [0, 0, 0]}],
            # Runtime resolves this entry to LOD1 on medium and LOD0 on high.
            # Post-build QA measures each selected file against its own tier.
            "minTier": stage_asset_min_tier(),
            "castShadow": False,
            "receiveShadow": True,
            # Every stage now owns a layered 360-degree Blender boundary,
            # midground district and skyline.  The old thumbnail cylinder is
            # intentionally removed only after this GLB reports load success.
            "replacesDistantMatte": True,
            # Exact PropPlacement coordinates are represented by the merged
            # Blender 40_PROPS batches.  Runtime keeps the collider/fallback
            # geometry until this asset has loaded and compiled successfully.
            "replacesProceduralProps": True,
            # LOD0 also contains every non-ghost authoritative BoxSpec shell
            # plus its facade/roof treatment. Runtime physics stays active,
            # while the duplicate Three.js shell is hidden only after compile.
            "replacesProceduralStageShell": True,
            "stageProvenance": {
                "placementSource": LAYOUT_PLACEMENT_SOURCE,
                "placementSolverSha256": LAYOUT_PLACEMENT_SOLVER_SHA,
                "stageWorldCatalogSha256": LAYOUT_STAGE_WORLD_CATALOG_SHA,
                # Stage-scoped cache/provenance identity.  Unlike generatedAt
                # or pretty-printing, this changes only when this stage's
                # authoritative Blender input changes.
                "stageLayoutSha256": STAGE_LAYOUT_SHA_BY_ID[stage["id"]],
            },
            "lods": [
                {"url": f"stages/{stage['id']}-lod1.glb", "distance": 260},
                {"url": f"stages/{stage['id']}-lod2.glb", "distance": 460},
            ],
        })
    with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "version": 1,
                "generatorVersion": GENERATOR_VERSION,
                "generatorSha": GENERATOR_SHA,
                "placementSource": LAYOUT_PLACEMENT_SOURCE,
                "placementSolverSha256": LAYOUT_PLACEMENT_SOLVER_SHA,
                "stageWorldCatalogSha256": LAYOUT_STAGE_WORLD_CATALOG_SHA,
                "assets": assets,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")


with open(LAYOUT_PATH, "r", encoding="utf-8") as handle:
    LAYOUT_DOCUMENT = json.load(handle)

LAYOUT_PLACEMENT_SOURCE = LAYOUT_DOCUMENT.get("placementSource", "runtime-release")
LAYOUT_PLACEMENT_SOLVER_SHA = LAYOUT_DOCUMENT.get("placementSolverSha256", "")
LAYOUT_STAGE_WORLD_CATALOG_SHA = LAYOUT_DOCUMENT.get("stageWorldCatalogSha256", "")
if LAYOUT_PLACEMENT_SOURCE not in ("runtime-release", "canonical-solver-v2-authoring"):
    raise RuntimeError(f"invalid layout placementSource: {LAYOUT_PLACEMENT_SOURCE}")
if (
    not isinstance(LAYOUT_PLACEMENT_SOLVER_SHA, str)
    or len(LAYOUT_PLACEMENT_SOLVER_SHA) != 64
    or not isinstance(LAYOUT_STAGE_WORLD_CATALOG_SHA, str)
    or len(LAYOUT_STAGE_WORLD_CATALOG_SHA) != 64
):
    raise RuntimeError("layout is missing solver/catalog SHA provenance")

ALL_STAGES = LAYOUT_DOCUMENT["stages"]
STAGE_LAYOUT_SHA_BY_ID = {
    stage["id"]: canonical_json_sha256(stage)
    for stage in ALL_STAGES
}
if len(STAGE_LAYOUT_SHA_BY_ID) != len(ALL_STAGES):
    raise RuntimeError("layout contains duplicate stage IDs")

STAGES = list(ALL_STAGES)

with open(PROFILE_PATH, "r", encoding="utf-8") as handle:
    PROFILES = json.load(handle)["profiles"]

stage_ids = {stage["id"] for stage in ALL_STAGES}
profile_ids = set(PROFILES)
if stage_ids != profile_ids:
    missing = sorted(stage_ids - profile_ids)
    extra = sorted(profile_ids - stage_ids)
    raise RuntimeError(f"stage profile mismatch: missing={missing}, extra={extra}")

# Per-stage opt-in for the a23 district-infill layer, defaulting to on for
# every stage except nakaniwa (see add_a23_district_infill's docstring).
# EXEC_ARGS may carry {"a23_stage_overrides": {"<id>": {"enabled": bool,
# "reason": str}}} for QA/dry-run callers that need to force a stage off
# without editing this file; production runs pass none and get the default
# table.
_a23_raw_overrides = EXEC_ARGS.get("a23_stage_overrides") if isinstance(EXEC_ARGS, dict) else None
_a23_overrides = None
if _a23_raw_overrides:
    _a23_overrides = {
        stage_id: a23_bridge.StageA23Policy(bool(entry["enabled"]), str(entry["reason"]))
        for stage_id, entry in _a23_raw_overrides.items()
    }
a23_bridge.configure_policy_table(sorted(stage_ids), _a23_overrides)

requested_stage_ids = EXEC_ARGS.get("stage_ids") if isinstance(EXEC_ARGS, dict) else None
if requested_stage_ids:
    requested_stage_ids = set(requested_stage_ids)
    STAGES = [stage for stage in STAGES if stage["id"] in requested_stage_ids]

previous_timer = bpy.app.driver_namespace.get("hibana_stage_build_timer")
if previous_timer and bpy.app.timers.is_registered(previous_timer):
    bpy.app.timers.unregister(previous_timer)

STATE = {"index": 0, "metrics": []}


def build_timer():
    index = STATE["index"]
    if index >= len(STAGES):
        # A filtered Blender QA build must never truncate the production
        # manifest.  Paths are deterministic for all 31 stage IDs.
        write_manifest(ALL_STAGES)
        write_progress({
            "status": "complete",
            "current": len(STAGES),
            "total": len(STAGES),
            "stage": STAGES[-1]["id"],
            "metrics": STATE["metrics"],
        })
        bpy.context.scene["hibanaBuildStatus"] = "complete"
        bpy.context.scene["hibanaBuildCount"] = len(STAGES)
        return None
    stage = STAGES[index]
    try:
        bpy.context.scene["hibanaBuildStatus"] = f"{index + 1}/{len(STAGES)} {stage['id']}"
        metrics = build_stage(stage, index, len(STAGES))
        STATE["metrics"].append(metrics)
        STATE["index"] += 1
        return 0.65
    except Exception as exc:
        write_progress({
            "status": "error",
            "current": index + 1,
            "total": len(STAGES),
            "stage": stage["id"],
            "error": repr(exc),
        })
        bpy.context.scene["hibanaBuildStatus"] = "error: " + repr(exc)
        return None


bpy.app.driver_namespace["hibana_stage_build_timer"] = build_timer
bpy.app.driver_namespace["hibana_stage_build_state"] = STATE
write_progress({"status": "queued", "current": 0, "total": len(STAGES)})
bpy.app.timers.register(build_timer, first_interval=0.2, persistent=False)
__result__ = {"queued": len(STAGES), "progress": PROGRESS_PATH}
