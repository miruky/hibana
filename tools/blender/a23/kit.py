"""Shared stage-kit adapter for ``tools/blender/a23`` — the promoted A23
toolchain (reclamation, districts, materials, measure, evidence).

Provenance
----------
The A23 round (see the round-state log carried over from the private study,
summarised in each sibling module's own docstring) produced its passes,
placement planner, material transforms and measurement/evidence harness
entirely against one stage's kit module,
``tools/blender/stage_kits/nakaniwa_reference_a21_r6.py`` ("R6"), imported by
name. That made every private script a *fork* rather than a *tool*: nothing
could run against another stage without copy-pasting it first.

Every ``tools/blender/stage_kits/*_reference_*.py`` module written to R6's
own contract already exposes the same primitive-emitting and measurement
functions:

  - ``_box(specs, role, material, group, x, y, z, w, h, d)``
  - ``_chamfer_box(specs, role, material, group, x, y, z, w, h, d, bevel, segments=1)``
  - ``_panel(specs, role, material, group, corners, thickness=0.06)``
  - ``_sweep(specs, role, material, group, points, radius, sides)``
  - ``_cylinder(specs, role, material, group, x, y, z, radius, height, segments=12, top_radius=None)``
  - ``_leaf_cluster(specs, role, material, group, x, y, z, radius, height, leaves, seed)``
  - ``spec_bounds(spec) -> (x0, y0, z0, x1, y1, z1)``
  - ``estimated_triangles(specs) -> int``
  - ``_project_spec_frame(spec, camera, aspect) -> {"bounds": (x0,y0,x1,y1), "nearDepthM": .., "farDepthM": ..} | None``

and, for the Blender-side render harness only:

  - ``_reset_scene()`` / ``_configure_scene() -> scene``
  - ``_make_camera(collection, camera_spec) -> bpy camera object``
  - ``_add_world_and_lights(lighting_collection)``
  - ``_make_blender_materials() -> dict[str, bpy material]``
  - a mesh-builder class exposing ``.flush() -> objects`` (R6's is named
    ``A21MeshBuilder``; the name is per-kit, the shape is not)
  - ``emit_specs_to_builder(builder, specs, material_map) -> specs``
  - ``_triangle_count(objects) -> int``

``SpecKit``/``RenderKit`` below are thin, duck-typed bundles of exactly those
callables, built once per stage kit module via ``SpecKit.from_module()`` /
``RenderKit.from_module()``. Nothing in ``tools/blender/a23`` imports a
specific stage's kit module by name — that binding happens only at the call
site (a per-stage build/study script), which is what makes reclamation.py,
districts.py, materials.py, measure.py and evidence.py stage-agnostic even
though they have so far only been *proven* against nakaniwa's kit (see each
module's fidelity notes).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Optional, Sequence

Spec = Mapping[str, object]
SpecList = list  # list[dict]; specs are plain dicts, kept untyped on purpose.
Bounds6 = tuple  # (x0, y0, z0, x1, y1, z1)
Frame = Optional[dict]  # {"bounds": (x0,y0,x1,y1), "nearDepthM": f, "farDepthM": f} | None


@dataclass(frozen=True)
class SpecKit:
    """Geometry-emitting primitives + measurement helpers for one stage kit."""

    box: Callable[..., None]
    chamfer_box: Callable[..., None]
    panel: Callable[..., None]
    sweep: Callable[..., None]
    cylinder: Callable[..., None]
    leaf_cluster: Callable[..., None]
    spec_bounds: Callable[[Spec], Bounds6]
    estimated_triangles: Callable[[Sequence[Spec]], int]
    project_spec_frame: Callable[[Spec, Mapping[str, object], float], Frame]

    @classmethod
    def from_module(cls, module) -> "SpecKit":
        return cls(
            box=module._box,
            chamfer_box=module._chamfer_box,
            panel=module._panel,
            sweep=module._sweep,
            cylinder=module._cylinder,
            leaf_cluster=module._leaf_cluster,
            spec_bounds=module.spec_bounds,
            estimated_triangles=module.estimated_triangles,
            project_spec_frame=module._project_spec_frame,
        )


@dataclass(frozen=True)
class RenderKit:
    """Blender-side scene/material/camera helpers for one stage kit. Only
    needed by evidence.py's actual render harness; every other a23 module
    works from a SpecKit alone and never touches bpy.
    """

    reset_scene: Callable[[], None]
    configure_scene: Callable[[], object]
    make_camera: Callable[[object, Mapping[str, object]], object]
    add_world_and_lights: Callable[[object], None]
    make_blender_materials: Callable[[], dict]
    mesh_builder: Callable[..., object]
    emit_specs_to_builder: Callable[[object, Iterable[Spec], Mapping[str, str]], list]
    triangle_count: Callable[[Sequence[object]], int]

    @classmethod
    def from_module(cls, module) -> "RenderKit":
        return cls(
            reset_scene=module._reset_scene,
            configure_scene=module._configure_scene,
            make_camera=module._make_camera,
            add_world_and_lights=module._add_world_and_lights,
            make_blender_materials=module._make_blender_materials,
            mesh_builder=module.A21MeshBuilder,
            emit_specs_to_builder=module.emit_specs_to_builder,
            triangle_count=module._triangle_count,
        )


def aspect_of(resolution: Sequence[float]) -> float:
    return float(resolution[0]) / float(resolution[1])


def spec_center(kit: SpecKit, spec: Spec) -> tuple[float, float, float]:
    b = kit.spec_bounds(spec)
    return (b[0] + b[3]) / 2.0, (b[1] + b[4]) / 2.0, (b[2] + b[5]) / 2.0


def distance_to_point(kit: SpecKit, spec: Spec, point: Sequence[float]) -> float:
    cx, cy, cz = spec_center(kit, spec)
    return math.sqrt((cx - point[0]) ** 2 + (cy - point[1]) ** 2 + (cz - point[2]) ** 2)


def distance_to_camera(kit: SpecKit, spec: Spec, camera: Mapping[str, object]) -> float:
    return distance_to_point(kit, spec, camera["location"])


def is_onscreen(frame: Frame) -> bool:
    """True if a ``project_spec_frame`` result's conservative AABB intersects
    the [0,1]x[0,1] frame at all. Shared so every pass in this package uses
    the exact same on-screen convention (a spec straddling the frame edge is
    "onscreen"; nothing behind the camera or entirely outside it is).
    """
    if frame is None:
        return False
    x0, y0, x1, y1 = frame["bounds"]
    return not (x1 <= 0.0 or y1 <= 0.0 or x0 >= 1.0 or y0 >= 1.0)


def frame_cells(
    bounds: tuple[float, float, float, float], grid_w: int, grid_h: int,
) -> Iterable[tuple[int, int]]:
    """Rasterise an NDC AABB onto a ``grid_w`` x ``grid_h`` screen grid.

    Shared by every occlusion-grid builder in this package (reclamation.py's
    pass 2/3 and districts.py's occlusion-aware priority test) so they stay
    pixel-identical by construction rather than by copy-pasted arithmetic —
    the original private study duplicated this exact function three times
    across three files, which is exactly the kind of drift promotion should
    remove.
    """
    x0, y0, x1, y1 = bounds
    if x1 <= 0.0 or y1 <= 0.0 or x0 >= 1.0 or y0 >= 1.0:
        return ()
    ix0 = max(0, min(grid_w - 1, math.floor(x0 * grid_w)))
    iy0 = max(0, min(grid_h - 1, math.floor(y0 * grid_h)))
    ix1 = max(0, min(grid_w - 1, math.ceil(x1 * grid_w) - 1))
    iy1 = max(0, min(grid_h - 1, math.ceil(y1 * grid_h) - 1))
    return ((ix, iy) for iy in range(iy0, iy1 + 1) for ix in range(ix0, ix1 + 1))
