"""A23 evidence: the multi-camera render harness, parameterised by a
stage's own proof cameras.

Promoted from the private study under
``/private/tmp/hibana-blender/claude-a23-nakaniwa-h17/run_a23_h17_multicamera.py``.

Measurement defect this exists to avoid
-----------------------------------------
Round-state's "single-camera judgement" defect (see ``reclamation.py``'s
pass 3 docstring): every visual decision before H17 was judged from one
camera, while the kit defines several proof cameras. Near-field detail is
small and distant at a wide establishing shot and dominant at a close one,
so judging only the flattering camera silently biases every downstream
decision. ``render_multi_camera`` makes "render every camera in the safety
contract" the default action for evaluating a build, rather than a one-off
script written after the fact.

Two layers
----------
The pure functions (``build_camera_index``, ``slugify_camera_name``,
``select_wanted_cameras``) do camera bookkeeping only and need no Blender —
they are what this module's unit tests exercise. ``render_multi_camera``
actually drives Blender (``bpy``) and can only run inside a real Blender
process; it imports ``bpy`` lazily so importing this module elsewhere never
fails.

On the temporary materials-dict swap
--------------------------------------
The existing per-stage kit contract's ``_make_blender_materials()`` (see
``kit.RenderKit``) takes no materials-dict parameter — it reads a
module-level ``MATERIALS`` global on the kit module, by a convention this
promotion is not chartered to redesign (the kit modules under
``tools/blender/stage_kits/`` are out of scope; only the new a23 package is
being promoted). The private study worked around this by permanently
reassigning ``R6.MATERIALS`` for the rest of the process. ``render_multi_camera``
instead swaps it in a ``try/finally`` for exactly the duration of one render
call and always restores the kit module's original dict afterwards, so
calling this function never leaves a stage kit module mutated.
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Mapping, Optional, Sequence

from tools.blender.a23.kit import RenderKit, Spec


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_camera_index(
    proof_cameras: Sequence[Mapping[str, object]], overrides: Sequence[Mapping[str, object]] = (),
) -> dict[str, dict]:
    """Camera name -> camera spec, with ``overrides`` taking priority over
    ``proof_cameras`` (matching the private study's pattern of substituting
    a study-only camera variant, e.g. a retargeted main camera, ahead of the
    kit's own proof camera of the same intent).
    """
    index: dict[str, dict] = {}
    for camera in overrides:
        index[str(camera["name"])] = dict(camera)
    for camera in proof_cameras:
        index.setdefault(str(camera["name"]), dict(camera))
    return index


def slugify_camera_name(name: str, *, strip_prefix: str = "") -> str:
    slug = name[len(strip_prefix):] if strip_prefix and name.startswith(strip_prefix) else name
    return slug.lower()


def select_wanted_cameras(
    wanted_names: Sequence[str], camera_index: Mapping[str, dict],
) -> tuple[list[dict], list[str]]:
    """Split ``wanted_names`` into (found camera specs, names not present in
    ``camera_index``) so a caller can report a missing camera instead of
    silently skipping it.
    """
    found: list[dict] = []
    missing: list[str] = []
    for name in wanted_names:
        camera = camera_index.get(name)
        if camera is None:
            missing.append(name)
        else:
            found.append(camera)
    return found, missing


@contextmanager
def _materials_override(kit_module, materials: Optional[dict]):
    if materials is None:
        yield
        return
    original = kit_module.MATERIALS
    kit_module.MATERIALS = materials
    try:
        yield
    finally:
        kit_module.MATERIALS = original


def render_multi_camera(
    specs: Sequence[Spec],
    *,
    kit_module,
    render_kit: RenderKit,
    wanted_camera_names: Sequence[str],
    camera_index: Mapping[str, dict],
    output_dir: Path,
    collection_prefix: str,
    materials_override: Optional[dict] = None,
    integration_material_map: Optional[Mapping[str, str]] = None,
    camera_name_strip_prefix: str = "",
    save_blend_path: Optional[Path] = None,
    color_depth: Optional[str] = None,
) -> dict:
    """Build ``specs`` into a fresh Blender scene, render every camera in
    ``wanted_camera_names`` found in ``camera_index``, optionally save the
    ``.blend``, and return a report with per-render paths/hashes.

    ``kit_module`` is the stage kit module itself (needed only for the
    temporary ``MATERIALS`` swap — see module docstring); ``render_kit`` is
    the ``RenderKit`` adapter built from that same module via
    ``RenderKit.from_module()``. Requires a real Blender process (imports
    ``bpy`` lazily).
    """
    import bpy  # type: ignore

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    found_cameras, missing = select_wanted_cameras(wanted_camera_names, camera_index)

    with _materials_override(kit_module, materials_override):
        render_kit.reset_scene()
        scene = render_kit.configure_scene()
        if color_depth is not None:
            try:
                scene.render.image_settings.color_depth = color_depth
            except (TypeError, ValueError):
                pass

        root = bpy.data.collections.new(f"{collection_prefix}_ROOT_LOD0")
        scene.collection.children.link(root)
        geometry = bpy.data.collections.new(f"{collection_prefix}_GEOMETRY_LOD0")
        cameras_collection = bpy.data.collections.new(f"{collection_prefix}_CAMERAS")
        lighting = bpy.data.collections.new(f"{collection_prefix}_LIGHTING")
        for child in (geometry, cameras_collection, lighting):
            root.children.link(child)

        materials = render_kit.make_blender_materials()
        builder = render_kit.mesh_builder(geometry, materials)
        material_map = (
            integration_material_map if integration_material_map is not None
            else {key: key for key in materials}
        )
        emitted = render_kit.emit_specs_to_builder(builder, specs, material_map)
        objects = builder.flush()
        evaluated_triangles = render_kit.triangle_count(objects)

        render_kit.add_world_and_lights(lighting)

        renders: dict[str, dict] = {}
        for camera_spec in found_cameras:
            name = str(camera_spec["name"])
            camera_obj = render_kit.make_camera(cameras_collection, camera_spec)
            scene.camera = camera_obj
            slug = slugify_camera_name(name, strip_prefix=camera_name_strip_prefix)
            path = output_dir / f"{slug}.png"
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            renders[name] = {"path": str(path), "sha256": _sha256(path), "bytes": path.stat().st_size}

        blend_info = None
        if save_blend_path is not None:
            bpy.ops.wm.save_as_mainfile(filepath=str(save_blend_path))
            blend_info = {"path": str(save_blend_path), "sha256": _sha256(save_blend_path)}

    return {
        "schema": "hibana.a23.evidence.multi-camera-render.v1",
        "specCount": len(emitted),
        "missingCameras": missing,
        "triangles": evaluated_triangles,
        "materialCount": len(materials),
        "drawCallCount": len(objects),
        "renders": renders,
        "blend": blend_info,
    }
