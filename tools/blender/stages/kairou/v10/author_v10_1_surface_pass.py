#!/usr/bin/env python3
"""Author Kairou V10.1's collision-backed architectural surface pass.

This script deliberately treats the GLB passed with ``--input`` as immutable
contact geometry.  It adds grouped, low-draw-call visual meshes whose lower
details remain inside (or within 20 cm of) the authoritative BoxSpecs in
``stage-layouts.json``.  Large silhouette work starts safely above player
height.  The result is a private raw GLB for collision, route and visual QA;
publishing is a separate release-gate step.

Run with Blender in background mode.  It has no dependency on an open .blend
file or /private/tmp source after the input GLB has been supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import bpy
from mathutils import Vector


SANCTUARY = "kairou-meridian-hypostyle-sanctuary"
OBSERVATORY = "kairou-windcrown-caravan-observatory"


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--layouts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--lod", type=int, choices=(0, 1, 2), required=True)
    return parser.parse_args(argv)


def stable_unit(*values: object) -> float:
    digest = hashlib.sha256("|".join(map(str, values)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") / float(2**64 - 1)


def runtime_to_blender(value: Sequence[float]) -> tuple[float, float, float]:
    """Hibana X/Y-up/Z to Blender X/Y/Z-up."""
    return float(value[0]), -float(value[2]), float(value[1])


def rgb(hex_value: str) -> tuple[float, float, float, float]:
    value = hex_value.lstrip("#")
    channels = []
    for offset in (0, 2, 4):
        encoded = int(value[offset:offset + 2], 16) / 255.0
        channels.append(encoded / 12.92 if encoded <= 0.04045 else ((encoded + 0.055) / 1.055) ** 2.4)
    return channels[0], channels[1], channels[2], 1.0


@dataclass
class MeshAccumulator:
    role: str
    vertices: list[tuple[float, float, float]] = field(default_factory=list)
    faces: list[tuple[int, ...]] = field(default_factory=list)
    uvs: list[tuple[tuple[float, float], ...]] = field(default_factory=list)
    smooth: list[bool] = field(default_factory=list)

    def quad(
        self,
        values: Sequence[Sequence[float]],
        uv_width: float = 1.0,
        uv_height: float = 1.0,
        smooth: bool = False,
    ) -> None:
        start = len(self.vertices)
        self.vertices.extend(runtime_to_blender(value) for value in values)
        self.faces.append((start, start + 1, start + 2, start + 3))
        self.uvs.append(((0.0, 0.0), (uv_width, 0.0), (uv_width, uv_height), (0.0, uv_height)))
        self.smooth.append(smooth)

    def triangle(
        self,
        values: Sequence[Sequence[float]],
        smooth: bool = False,
    ) -> None:
        start = len(self.vertices)
        self.vertices.extend(runtime_to_blender(value) for value in values)
        self.faces.append((start, start + 1, start + 2))
        self.uvs.append(((0.0, 0.0), (1.0, 0.0), (0.5, 1.0)))
        self.smooth.append(smooth)

    def box(
        self,
        centre: Sequence[float],
        dimensions: Sequence[float],
        yaw: float = 0.0,
    ) -> None:
        cx, cy, cz = map(float, centre)
        width, height, depth = map(float, dimensions)
        hx, hy, hz = width * 0.5, height * 0.5, depth * 0.5
        cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)

        def point(x: float, y: float, z: float) -> tuple[float, float, float]:
            return (
                cx + x * cos_yaw + z * sin_yaw,
                cy + y,
                cz - x * sin_yaw + z * cos_yaw,
            )

        p = {
            "lbf": point(-hx, -hy, -hz), "rbf": point(hx, -hy, -hz),
            "rtf": point(hx, hy, -hz), "ltf": point(-hx, hy, -hz),
            "lbb": point(-hx, -hy, hz), "rbb": point(hx, -hy, hz),
            "rtb": point(hx, hy, hz), "ltb": point(-hx, hy, hz),
        }
        self.quad((p["lbf"], p["ltf"], p["rtf"], p["rbf"]), width, height)
        self.quad((p["rbb"], p["rtb"], p["ltb"], p["lbb"]), width, height)
        self.quad((p["lbb"], p["ltb"], p["ltf"], p["lbf"]), depth, height)
        self.quad((p["rbf"], p["rtf"], p["rtb"], p["rbb"]), depth, height)
        self.quad((p["ltf"], p["ltb"], p["rtb"], p["rtf"]), width, depth)
        self.quad((p["lbb"], p["lbf"], p["rbf"], p["rbb"]), width, depth)

    def horizontal_panel(
        self,
        centre: Sequence[float],
        dimensions_xz: Sequence[float],
        yaw: float = 0.0,
        upward: bool = True,
    ) -> None:
        """Single visible face for paving/coffers; avoids ten hidden triangles."""
        cx, cy, cz = map(float, centre)
        width, depth = map(float, dimensions_xz)
        hx, hz = width * 0.5, depth * 0.5
        cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)

        def point(x: float, z: float) -> tuple[float, float, float]:
            return (
                cx + x * cos_yaw + z * sin_yaw,
                cy,
                cz - x * sin_yaw + z * cos_yaw,
            )

        values = (
            point(-hx, -hz), point(-hx, hz), point(hx, hz), point(hx, -hz),
        )
        if not upward:
            values = tuple(reversed(values))
        self.quad(values, width, depth)

    def vertical_panel(
        self,
        centre: Sequence[float],
        dimensions: Sequence[float],
        facing: str,
    ) -> None:
        """Single recessed facade face; depth comes from the projecting frame.

        The old window treatment used a thin six-faced cuboid at the same
        depth as its trim and therefore read as a brown card.  This back face
        sits against the authored wall while the frame/lattice projects in
        front, creating a measurable 12--20 cm reveal for two triangles.
        """
        cx, cy, cz = map(float, centre)
        width, height = map(float, dimensions)
        hw, hh = width * 0.5, height * 0.5
        if facing == "z":
            values = (
                (cx - hw, cy - hh, cz), (cx + hw, cy - hh, cz),
                (cx + hw, cy + hh, cz), (cx - hw, cy + hh, cz),
            )
        elif facing == "x":
            values = (
                (cx, cy - hh, cz + hw), (cx, cy - hh, cz - hw),
                (cx, cy + hh, cz - hw), (cx, cy + hh, cz + hw),
            )
        else:
            raise ValueError(f"unsupported vertical-panel facing: {facing}")
        self.quad(values, width, height)

    def oriented_box(
        self,
        centre: Sequence[float],
        axes: Sequence[Sequence[float]],
        dimensions: Sequence[float],
    ) -> None:
        centre_v = Vector(centre)
        basis = [Vector(value).normalized() for value in axes]
        half = [float(value) * 0.5 for value in dimensions]

        def point(a: float, b: float, c: float) -> tuple[float, float, float]:
            value = centre_v + basis[0] * (a * half[0]) + basis[1] * (b * half[1]) + basis[2] * (c * half[2])
            return value.x, value.y, value.z

        corners = {
            "lbf": point(-1, -1, -1), "rbf": point(1, -1, -1),
            "rtf": point(1, 1, -1), "ltf": point(-1, 1, -1),
            "lbb": point(-1, -1, 1), "rbb": point(1, -1, 1),
            "rtb": point(1, 1, 1), "ltb": point(-1, 1, 1),
        }
        a, b, c = map(float, dimensions)
        self.quad((corners["lbf"], corners["ltf"], corners["rtf"], corners["rbf"]), a, b)
        self.quad((corners["rbb"], corners["rtb"], corners["ltb"], corners["lbb"]), a, b)
        self.quad((corners["lbb"], corners["ltb"], corners["ltf"], corners["lbf"]), c, b)
        self.quad((corners["rbf"], corners["rtf"], corners["rtb"], corners["rbb"]), c, b)
        self.quad((corners["ltf"], corners["ltb"], corners["rtb"], corners["rtf"]), a, c)
        self.quad((corners["lbb"], corners["lbf"], corners["rbf"], corners["rbb"]), a, c)

    def vertical_prism(
        self,
        centre_xz: Sequence[float],
        bottom: float,
        top: float,
        radius: float,
        segments: int,
        phase: float = 0.0,
        smooth: bool = True,
    ) -> None:
        cx, cz = map(float, centre_xz)
        lower = []
        upper = []
        for index in range(segments):
            angle = phase + math.tau * index / segments
            lower.append((cx + radius * math.cos(angle), bottom, cz + radius * math.sin(angle)))
            upper.append((cx + radius * math.cos(angle), top, cz + radius * math.sin(angle)))
        for index in range(segments):
            following = (index + 1) % segments
            self.quad(
                (lower[index], lower[following], upper[following], upper[index]),
                radius,
                top - bottom,
                smooth,
            )
        for index in range(1, segments - 1):
            self.triangle((lower[0], lower[index + 1], lower[index]), False)
            self.triangle((upper[0], upper[index], upper[index + 1]), False)

    def cone(
        self,
        centre_xz: Sequence[float],
        bottom: float,
        top: float,
        radius: float,
        segments: int,
    ) -> None:
        cx, cz = map(float, centre_xz)
        apex = (cx, top, cz)
        ring = [
            (cx + radius * math.cos(math.tau * index / segments), bottom, cz + radius * math.sin(math.tau * index / segments))
            for index in range(segments)
        ]
        for index in range(segments):
            self.triangle((ring[index], ring[(index + 1) % segments], apex), True)
        for index in range(1, segments - 1):
            self.triangle((ring[0], ring[index + 1], ring[index]), False)

    def dome(
        self,
        centre_xz: Sequence[float],
        base: float,
        radius: float,
        height: float,
        rings: int,
        segments: int,
    ) -> None:
        cx, cz = map(float, centre_xz)
        rows: list[list[tuple[float, float, float]]] = []
        for row in range(rings + 1):
            latitude = (math.pi * 0.5) * row / rings
            ring_radius = radius * math.cos(latitude)
            y = base + height * math.sin(latitude)
            rows.append([
                (cx + ring_radius * math.cos(math.tau * index / segments), y, cz + ring_radius * math.sin(math.tau * index / segments))
                for index in range(segments)
            ])
        for row in range(rings):
            for index in range(segments):
                following = (index + 1) % segments
                self.quad((rows[row][index], rows[row][following], rows[row + 1][following], rows[row + 1][index]), 1.0, 1.0, True)

    def ellipsoid(
        self,
        centre: Sequence[float],
        radii: Sequence[float],
        rings: int,
        segments: int,
    ) -> None:
        """Low-cost organic cluster for wall vines and roof planting."""
        cx, cy, cz = map(float, centre)
        rx, ry, rz = map(float, radii)
        rows: list[list[tuple[float, float, float]]] = []
        for row in range(rings + 1):
            latitude = -math.pi * 0.5 + math.pi * row / rings
            ring_scale = math.cos(latitude)
            rows.append([
                (
                    cx + rx * ring_scale * math.cos(math.tau * index / segments),
                    cy + ry * math.sin(latitude),
                    cz + rz * ring_scale * math.sin(math.tau * index / segments),
                )
                for index in range(segments)
            ])
        for row in range(rings):
            for index in range(segments):
                following = (index + 1) % segments
                self.quad((rows[row][index], rows[row][following], rows[row + 1][following], rows[row + 1][index]), 1.0, 1.0, True)

    def torus(
        self,
        centre: Sequence[float],
        major_radius: float,
        minor_radius: float,
        plane: str,
        major_segments: int,
        minor_segments: int,
    ) -> None:
        cx, cy, cz = map(float, centre)

        def point(u: float, v: float) -> tuple[float, float, float]:
            radial = major_radius + minor_radius * math.cos(v)
            tube = minor_radius * math.sin(v)
            if plane == "xy":
                return cx + radial * math.cos(u), cy + radial * math.sin(u), cz + tube
            if plane == "yz":
                return cx + tube, cy + radial * math.cos(u), cz + radial * math.sin(u)
            return cx + radial * math.cos(u), cy + tube, cz + radial * math.sin(u)

        for major_index in range(major_segments):
            u0 = math.tau * major_index / major_segments
            u1 = math.tau * (major_index + 1) / major_segments
            for minor_index in range(minor_segments):
                v0 = math.tau * minor_index / minor_segments
                v1 = math.tau * (minor_index + 1) / minor_segments
                self.quad((point(u0, v0), point(u1, v0), point(u1, v1), point(u0, v1)), 1.0, 1.0, True)

    @property
    def triangles(self) -> int:
        return sum(max(0, len(face) - 2) for face in self.faces)


def create_simple_material(name: str, colour: str, roughness: float, metallic: float = 0.0) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    shader = next((node for node in material.node_tree.nodes if node.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if shader is None:
        for node in list(material.node_tree.nodes):
            material.node_tree.nodes.remove(node)
        output = material.node_tree.nodes.new("ShaderNodeOutputMaterial")
        shader = material.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    shader.inputs["Base Color"].default_value = rgb(colour)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return material


def find_material(*tokens: str) -> bpy.types.Material:
    for token in tokens:
        material = bpy.data.materials.get(token)
        if material is not None:
            return material
    for material in bpy.data.materials:
        lowered = material.name.lower()
        if any(token.lower() in lowered for token in tokens):
            return material
    raise RuntimeError(f"missing imported material: {tokens}")


def build_object(
    accumulator: MeshAccumulator,
    material: bpy.types.Material,
    lod: int,
    provenance: dict[str, object],
) -> bpy.types.Object | None:
    if not accumulator.faces:
        return None
    mesh = bpy.data.meshes.new(f"SM_Kairou_V10_1_Surface_{accumulator.role}_LOD{lod}_MESH")
    mesh.from_pydata(accumulator.vertices, [], accumulator.faces)
    mesh.update(calc_edges=True)
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for polygon, face_uv, smooth in zip(mesh.polygons, accumulator.uvs, accumulator.smooth, strict=True):
        polygon.use_smooth = smooth
        for loop_index, value in zip(polygon.loop_indices, face_uv, strict=True):
            uv_layer.data[loop_index].uv = value
    mesh.materials.append(material)
    obj = bpy.data.objects.new(f"SM_Kairou_V10_1_Surface_{accumulator.role}_LOD{lod}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj["hibanaStage"] = "kairou"
    obj["hibanaLod"] = lod
    obj["hibanaMaterial"] = accumulator.role
    obj["hibanaRole"] = "collision-backed-surface-detail"
    obj["hibanaExport"] = True
    obj["hibanaKairouArtRevision"] = "v10.1-surface-pass-v6.3.3"
    obj["hibanaKairouContactSkeleton"] = "current-release-legacy-boxspec"
    obj["hibanaKairouPlayerHeightContainmentM"] = 0.20
    obj["hibanaFacadeDarkCardCount"] = 0
    obj["hibanaFacadeGlassPaneCount"] = 0
    for key, value in provenance.items():
        if key not in obj:
            obj[key] = value
    return obj


def stage_layout(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return next(stage for stage in document["stages"] if stage["id"] == "kairou")


def arch(
    acc: MeshAccumulator,
    centre: Sequence[float],
    radius: float,
    radial_thickness: float,
    depth: float,
    facing: str,
    segments: int,
) -> None:
    """Build a voussoir arch in an X/Y or Z/Y facade plane."""
    cx, spring_y, cz = map(float, centre)
    arc_length = math.pi * (radius + radial_thickness * 0.5) / segments * 1.08
    for index in range(segments):
        theta = math.pi * (index + 0.5) / segments
        radial = radius + radial_thickness * 0.5
        if facing == "z":
            position = (cx + radial * math.cos(theta), spring_y + radial * math.sin(theta), cz)
            tangent = (-math.sin(theta), math.cos(theta), 0.0)
            outward = (0.0, 0.0, 1.0)
        else:
            position = (cx, spring_y + radial * math.sin(theta), cz + radial * math.cos(theta))
            tangent = (0.0, math.cos(theta), -math.sin(theta))
            outward = (1.0, 0.0, 0.0)
        radial_axis = Vector(tangent).cross(Vector(outward)).normalized()
        acc.oriented_box(position, (tangent, radial_axis, outward), (arc_length, radial_thickness, depth))


def beam_between(
    acc: MeshAccumulator,
    start: Sequence[float],
    end: Sequence[float],
    thickness: float,
) -> None:
    """Create a connected square beam from measured endpoints without Euler rotation."""
    start_v, end_v = Vector(start), Vector(end)
    forward = end_v - start_v
    length = forward.length
    if length <= 1e-6:
        raise ValueError("beam endpoints must be distinct")
    forward.normalize()
    reference = Vector((0.0, 1.0, 0.0)) if abs(forward.y) < 0.92 else Vector((1.0, 0.0, 0.0))
    side = forward.cross(reference).normalized()
    up = side.cross(forward).normalized()
    acc.oriented_box((start_v + end_v) * 0.5, (forward, side, up), (length, thickness, thickness))


def add_column_sleeve(
    accumulators: dict[str, MeshAccumulator],
    box: dict[str, object],
    lod: int,
    role: str = "wall_warm",
) -> None:
    bottom = float(box["y"]) - float(box["h"]) * 0.5
    top = float(box["y"]) + float(box["h"]) * 0.5
    radius = min(float(box["w"]), float(box["d"])) * 0.42
    segments = (14, 10, 8)[lod]
    accumulators[role].vertical_prism((box["x"], box["z"]), bottom, top, radius, segments, math.pi / segments)
    accumulators["trim"].box((box["x"], bottom + 0.38, box["z"]), (radius * 2.18, 0.56, radius * 2.18))
    accumulators["trim"].box((box["x"], top - 0.38, box["z"]), (radius * 2.25, 0.62, radius * 2.25))
    if lod == 0 and top - bottom > 8.0:
        for y in (bottom + (top - bottom) * 0.34, bottom + (top - bottom) * 0.68):
            accumulators["accent"].vertical_prism((box["x"], box["z"]), y - 0.12, y + 0.12, radius * 1.035, segments)


def wall_panels(
    accumulators: dict[str, MeshAccumulator],
    box: dict[str, object],
    lod: int,
    identity: str,
) -> int:
    width = float(box["w"])
    depth = float(box["d"])
    height = float(box["h"])
    bottom = float(box["y"]) - height * 0.5
    top = float(box["y"]) + height * 0.5
    if height < 4.4 or top < 3.0 or min(width, depth) > 2.1:
        return 0
    along_x = width >= depth
    length = width if along_x else depth
    if length < 5.4:
        return 0
    step = (3.7, 7.2, 1000.0)[lod]
    count = min((8, 4, 0)[lod], max(1, int(length // step)))
    if count <= 0:
        return 0
    panel_height = min(2.9, max(1.8, top - max(bottom + 1.0, 2.4) - 0.7))
    centre_y = min(top - panel_height * 0.5 - 0.45, max(bottom + panel_height * 0.5 + 0.55, 3.65))
    if centre_y - panel_height * 0.5 < bottom + 0.15:
        return 0
    panel_width = min(2.7, max(1.7, length / (count * 2.9)))
    frame_role = "wall_warm" if stable_unit(identity, "frame") > 0.30 else "trim"
    created = 0
    for side in (-1.0, 1.0):
        for index in range(count):
            along = (-length * 0.5) + length * (index + 1) / (count + 1)
            jitter = (stable_unit(identity, side, index) - 0.5) * min(0.65, length / 18.0)
            along += jitter
            if along_x:
                x = float(box["x"]) + along
                surface_z = float(box["z"]) + side * depth * 0.5
                back_z = surface_z + side * 0.018
                # The complete frame must stay within the measured 20 cm
                # player-height relief allowance.  Its back edge is 3 cm in
                # front of the collider and its front edge is exactly 20 cm;
                # the mineral back plane therefore reads as a real 18 cm
                # reveal without becoming a floating applique.
                frame_z = surface_z + side * 0.115
                lattice_z = surface_z + side * 0.10
                accumulators["wall_warm"].vertical_panel(
                    (x, centre_y, back_z),
                    (panel_width * 0.84, panel_height * 0.84),
                    "z",
                )
                accumulators[frame_role].box((x, centre_y + panel_height * 0.5 + 0.12, frame_z), (panel_width + 0.48, 0.24, 0.17))
                accumulators[frame_role].box((x, centre_y - panel_height * 0.5 - 0.12, frame_z), (panel_width + 0.48, 0.24, 0.17))
                for direction in (-1.0, 1.0):
                    accumulators[frame_role].box((x + direction * (panel_width * 0.5 + 0.12), centre_y, frame_z), (0.24, panel_height + 0.48, 0.17))
                if lod == 0:
                    # Two vertical timber bars and one stone cross rail sit in
                    # front of the mineral back plane.  The visible reveal is
                    # real geometry, but no black void/card is introduced.
                    for slat in (-0.23, 0.23):
                        accumulators["wood"].box((x + slat * panel_width, centre_y, lattice_z), (0.10, panel_height * 0.72, 0.08))
                    accumulators["trim"].box((x, centre_y, lattice_z + side * 0.02), (panel_width * 0.80, 0.09, 0.09))
                    if stable_unit(identity, side, index, "arch") > 0.44:
                        arch(
                            accumulators[frame_role],
                            (x, centre_y + panel_height * 0.12, surface_z + side * 0.14),
                            panel_width * 0.43,
                            0.16,
                            0.12,
                            "z",
                            7,
                        )
                if lod <= 1:
                    accumulators["wood"].box(
                        (x, centre_y + panel_height * 0.5 + 0.34, float(box["z"]) + side * (depth * 0.5 + 0.34)),
                        (panel_width + 0.64, 0.16, 0.58),
                    )
            else:
                surface_x = float(box["x"]) + side * width * 0.5
                back_x = surface_x + side * 0.018
                frame_x = surface_x + side * 0.115
                lattice_x = surface_x + side * 0.10
                z = float(box["z"]) + along
                accumulators["wall_warm"].vertical_panel(
                    (back_x, centre_y, z),
                    (panel_width * 0.84, panel_height * 0.84),
                    "x",
                )
                accumulators[frame_role].box((frame_x, centre_y + panel_height * 0.5 + 0.12, z), (0.17, 0.24, panel_width + 0.48))
                accumulators[frame_role].box((frame_x, centre_y - panel_height * 0.5 - 0.12, z), (0.17, 0.24, panel_width + 0.48))
                for direction in (-1.0, 1.0):
                    accumulators[frame_role].box((frame_x, centre_y, z + direction * (panel_width * 0.5 + 0.12)), (0.17, panel_height + 0.48, 0.24))
                if lod == 0:
                    for slat in (-0.23, 0.23):
                        accumulators["wood"].box((lattice_x, centre_y, z + slat * panel_width), (0.08, panel_height * 0.72, 0.10))
                    accumulators["trim"].box((lattice_x + side * 0.02, centre_y, z), (0.09, 0.09, panel_width * 0.80))
                    if stable_unit(identity, side, index, "arch") > 0.44:
                        arch(
                            accumulators[frame_role],
                            (surface_x + side * 0.14, centre_y + panel_height * 0.12, z),
                            panel_width * 0.43,
                            0.16,
                            0.12,
                            "x",
                            7,
                        )
                if lod <= 1:
                    accumulators["wood"].box(
                        (float(box["x"]) + side * (width * 0.5 + 0.34), centre_y + panel_height * 0.5 + 0.34, z),
                        (0.58, 0.16, panel_width + 0.64),
                    )
            created += 1
    # Recessed entry on one deterministic public face.  It is a material layer
    # on the existing wall collider, never a fake opening into non-playable
    # space.
    if lod <= 1 and bottom <= 0.25 and top >= 4.4 and stable_unit(identity, "entry") > 0.53:
        entry_sign = 1.0 if stable_unit(identity, "entry-face") >= 0.5 else -1.0
        entry_y = bottom + 1.72
        entry_width = min(2.35, length * 0.28)
        if along_x:
            entry_x = float(box["x"]) + (stable_unit(identity, "entry-pos") - 0.5) * length * 0.44
            entry_z = float(box["z"]) + entry_sign * (depth * 0.5 + 0.10)
            accumulators["wood"].box((entry_x, entry_y, entry_z), (entry_width, 3.35, 0.14))
            arch(accumulators[frame_role], (entry_x, entry_y + 0.40, entry_z + entry_sign * 0.05), entry_width * 0.52, 0.24, 0.22, "z", (9, 6, 5)[lod])
            for direction in (-1.0, 1.0):
                accumulators[frame_role].box((entry_x + direction * (entry_width * 0.5 + 0.14), entry_y, entry_z + entry_sign * 0.04), (0.28, 3.55, 0.22))
        else:
            entry_x = float(box["x"]) + entry_sign * (width * 0.5 + 0.10)
            entry_z = float(box["z"]) + (stable_unit(identity, "entry-pos") - 0.5) * length * 0.44
            accumulators["wood"].box((entry_x, entry_y, entry_z), (0.14, 3.35, entry_width))
            arch(accumulators[frame_role], (entry_x + entry_sign * 0.05, entry_y + 0.40, entry_z), entry_width * 0.52, 0.24, 0.22, "x", (9, 6, 5)[lod])
            for direction in (-1.0, 1.0):
                accumulators[frame_role].box((entry_x + entry_sign * 0.04, entry_y, entry_z + direction * (entry_width * 0.5 + 0.14)), (0.22, 3.55, 0.28))

    # Wall-attached pilasters add real contact shadow and break the repeated
    # cuboid read at a 2--4 m cadence in LOD0.
    pilaster_spacing = (4.0, 8.0, 1000.0)[lod]
    pilaster_count = min((10, 5, 0)[lod], max(0, int(length // pilaster_spacing)))
    if pilaster_count:
        pilaster_height = max(1.0, height - 0.7)
        for side in (-1.0, 1.0):
            for index in range(pilaster_count + 1):
                along = -length * 0.5 + length * index / max(1, pilaster_count)
                if along_x:
                    accumulators["trim"].box(
                        (float(box["x"]) + along, bottom + 0.35 + pilaster_height * 0.5, float(box["z"]) + side * (depth * 0.5 + 0.10)),
                        (0.26, pilaster_height, 0.18),
                    )
                else:
                    accumulators["trim"].box(
                        (float(box["x"]) + side * (width * 0.5 + 0.10), bottom + 0.35 + pilaster_height * 0.5, float(box["z"]) + along),
                        (0.18, pilaster_height, 0.26),
                    )
    # A shallow projecting cornice breaks the cuboid silhouette without
    # becoming a new collision volume; it stays within the 20 cm audit budget.
    cornice_y = top - 0.28
    if along_x:
        accumulators[frame_role].box((box["x"], cornice_y, box["z"]), (width + 0.28, 0.38, min(depth + 0.28, 2.28)))
    else:
        accumulators[frame_role].box((box["x"], cornice_y, box["z"]), (min(width + 0.28, 2.28), 0.38, depth + 0.28))
    return created


def landmark_surface_pass(
    accumulators: dict[str, MeshAccumulator],
    boxes: list[dict[str, object]],
    lod: int,
) -> dict[str, int]:
    statistics = {"columnSleeves": 0, "portalVoussoirs": 0, "cofferBeams": 0}
    sanctuary_boxes = [box for box in boxes if box.get("landmarkId") == SANCTUARY]
    observatory_boxes = [box for box in boxes if box.get("landmarkId") == OBSERVATORY]

    for box in sanctuary_boxes:
        if box.get("landmarkPart") in {"column", "gate-column"}:
            add_column_sleeve(accumulators, box, lod)
            statistics["columnSleeves"] += 1
        elif box.get("landmarkPart") in {"wall", "interior"}:
            wall_panels(accumulators, box, lod, f"sanctuary:{box['x']}:{box['z']}")
    for box in observatory_boxes:
        if box.get("landmarkPart") in {"wall", "interior"}:
            wall_panels(accumulators, box, lod, f"observatory:{box['x']}:{box['z']}")
    # V6.3 connection map (runtime X/Y-up/Z):
    #   south gate columns top Y=12.2 -> outer/inner stone piers bottom
    #     Y=11.6 (0.6 m overlap) -> two concentric arches -> corbel table;
    #   corbel table top Y=27.0 -> stepped 12-sided chapel bottom Y=25.0
    #     (2.0 m overlap) -> faceted upper chapel -> dome;
    #   inner stone piers bottom Y=11.8 -> broad minaret plinths -> shafts
    #     -> two balcony stages -> conical crowns.
    # All upper mass is collisionless, but every visible chain intersects the
    # authored collision shell.  The landmark is intentionally at the SOUTH
    # entrance so the approach views cannot be blocked by the north upper walk.
    dome_segments = (24, 16, 12)[lod]
    monument_arch_segments = (22, 15, 10)[lod]
    gate_z = 8.92
    arch(accumulators["wall_weathered"], (-66.0, 12.35, gate_z), 12.0, 1.80, 5.8, "z", monument_arch_segments)
    arch(accumulators["wall_warm"], (-66.0, 12.50, gate_z - 0.22), 9.25, 1.28, 6.25, "z", max(10, monument_arch_segments - 4))
    arch(accumulators["wall_warm"], (-66.0, 29.0, gate_z), 5.80, 1.10, 5.2, "z", max(10, monument_arch_segments - 3))
    arch(accumulators["trim"], (-66.0, 29.0, gate_z - 0.32), 4.55, 0.34, 5.65, "z", max(8, monument_arch_segments - 7))
    statistics["portalVoussoirs"] += monument_arch_segments + max(10, monument_arch_segments - 4)

    # Piers, stepped buttresses and a corbel table expose a continuous load
    # path in views 01--03.  Nothing now reads as a cylinder suspended over a
    # thin lintel; every tier visibly overlaps the authored gate supports.
    for x in (-80.0, -52.0):
        accumulators["wall_warm"].box((x, 18.2, 10.2), (5.8, 13.2, 7.4))
        accumulators["wall_weathered"].box((x, 15.0, 6.25), (7.0, 6.8, 2.2))
        accumulators["trim"].box((x, 23.6, 10.2), (6.8, 1.15, 8.2))
        accumulators["trim"].box((x, 25.0, 10.2), (8.2, 1.05, 8.7))
    for x in (-75.0, -57.0):
        accumulators["wall_weathered"].vertical_prism((x, 9.0), 11.8, 17.0, 2.80, (14, 10, 8)[lod])
        accumulators["trim"].vertical_prism((x, 9.0), 16.5, 18.0, 3.05, (14, 10, 8)[lod])
    for index, x in enumerate((-75.0, -70.5, -66.0, -61.5, -57.0)):
        # Pale, staggered brackets transmit the chapel load into the two arch
        # rings.  Equal dark blocks previously read as five suspended teeth
        # and also triggered the near-black facade-grid audit.
        bracket_height = (3.7, 4.15, 4.65, 4.15, 3.7)[index]
        bracket_width = (1.45, 1.70, 2.05, 1.70, 1.45)[index]
        bracket_top = 25.50
        accumulators["wall_warm"].box(
            (x, bracket_top - bracket_height * 0.5, 10.8),
            (bracket_width, bracket_height, 6.4),
        )
        accumulators["trim"].box((x, 25.75, 10.8), (bracket_width + 0.72, 0.75, 7.0))
    accumulators["wall_warm"].box((-66.0, 26.45, 11.0), (30.0, 1.15, 7.4))

    chapel_segments = (10, 8, 6)[lod]
    # Flat-shaded, deliberately low-sided drums expose a stepped chapel
    # silhouette.  The previous smooth normals visually restored a cylinder
    # even after the geometry had been tiered, preserving the tank-like read.
    accumulators["wall_weathered"].vertical_prism((-66.0, 11.8), 25.0, 31.2, 10.35, chapel_segments, math.pi / chapel_segments, False)
    accumulators["wall_warm"].vertical_prism((-66.0, 11.8), 30.8, 36.7, 8.95, chapel_segments, math.pi / chapel_segments, False)
    accumulators["wall_warm"].vertical_prism((-66.0, 11.8), 36.3, 42.1, 7.65, chapel_segments, math.pi / chapel_segments, False)
    for band_y, band_radius in ((26.2, 10.7), (30.8, 9.55), (36.3, 8.35), (41.6, 8.05)):
        accumulators["trim"].vertical_prism((-66.0, 11.8), band_y - 0.34, band_y + 0.34, band_radius, chapel_segments, math.pi / chapel_segments, False)
    # Front buttresses and arched mineral niches break the tank-like read.
    chapel_front_z = 4.05
    for x in (-71.6, -66.0, -60.4):
        accumulators["wall_weathered"].box((x, 34.0, chapel_front_z + 0.38), (1.10, 10.6, 1.15))
        accumulators["trim"].box((x, 28.7, chapel_front_z + 0.12), (1.75, 0.75, 1.65))
        accumulators["wall_weathered"].vertical_panel((x, 35.0, chapel_front_z - 0.22), (1.65, 3.7), "z")
        arch(accumulators["trim"], (x, 35.1, chapel_front_z - 0.42), 0.92, 0.18, 0.34, "z", (7, 6, 5)[lod])
    accumulators["wall_warm"].dome((-66.0, 11.8), 41.7, 8.35, 10.4, (6, 5, 4)[lod], dome_segments)
    accumulators["accent"].vertical_prism((-66.0, 11.8), 51.0, 56.8, 0.42, max(10, dome_segments // 2))
    accumulators["accent"].cone((-66.0, 11.8), 56.6, 59.8, 0.96, max(10, dome_segments // 2))

    minaret_segments = (16, 11, 8)[lod]
    for x in (-75.0, -57.0):
        accumulators["wall_weathered"].vertical_prism((x, 9.0), 16.6, 19.0, 2.45, minaret_segments)
        accumulators["wall_warm"].vertical_prism((x, 9.0), 18.7, 46.0, 1.78, minaret_segments)
        for balcony_y in (29.0, 42.5):
            accumulators["trim"].vertical_prism((x, 9.0), balcony_y - 0.55, balcony_y + 0.15, 2.72, minaret_segments)
            accumulators["accent"].vertical_prism((x, 9.0), balcony_y + 0.05, balcony_y + 0.92, 2.26, minaret_segments)
        accumulators["wall_weathered"].vertical_prism((x, 9.0), 45.6, 49.8, 2.12, minaret_segments)
        accumulators["trim"].vertical_prism((x, 9.0), 49.2, 50.2, 2.58, minaret_segments)
        accumulators["accent"].cone((x, 9.0), 49.8, 60.6, 2.66, minaret_segments)
    statistics["sanctuaryHeroHeightM"] = 60.6
    statistics["sanctuaryHeroSupportHeightM"] = 11.8

    # Tower lanterns sit directly over the four authored tower colliders.
    for box in (item for item in sanctuary_boxes if item.get("landmarkPart") == "tower"):
        top = float(box["y"]) + float(box["h"]) * 0.5
        radius = min(float(box["w"]), float(box["d"])) * 0.44
        accumulators["trim"].vertical_prism((box["x"], box["z"]), top - 0.55, top + 0.45, radius * 1.06, max(8, dome_segments // 2))
        accumulators["wall_warm"].vertical_prism((box["x"], box["z"]), top + 0.4, top + 4.3, radius * 0.66, max(8, dome_segments // 2))
        accumulators["accent"].cone((box["x"], box["z"]), top + 4.1, top + 7.4, radius * 1.0, max(8, dome_segments // 2))
        if lod <= 1:
            banner_y = min(top - 3.0, 8.0)
            for side in (-1.0, 1.0):
                banner_z = float(box["z"]) + side * (float(box["d"]) * 0.5 + 0.09)
                accumulators["cloth"].box((box["x"], banner_y, banner_z), (1.55, 4.8, 0.07))
                accumulators["accent"].box((box["x"], banner_y + 2.55, banner_z + side * 0.04), (1.95, 0.16, 0.12))
        if lod <= 1:
            # Deep mineral-backed openings replace the old timber cards.  The
            # back face hugs the collider and the grille/frame projects, so
            # even the oblique aerial view reads a reveal instead of a decal.
            for y in (min(top - 2.4, 4.2), min(top - 2.4, 8.4)):
                for side in (-1.0, 1.0):
                    offset = radius / 0.44 * 0.5 + 0.08
                    back_x = box["x"] + side * (offset - 0.06)
                    back_z = box["z"] + side * (offset - 0.06)
                    face_x = box["x"] + side * (offset + 0.14)
                    face_z = box["z"] + side * (offset + 0.14)
                    grille_x = box["x"] + side * (offset + 0.10)
                    grille_z = box["z"] + side * (offset + 0.10)
                    accumulators["wall_warm"].vertical_panel((back_x, y, box["z"]), (1.35, 1.82), "x")
                    accumulators["wall_warm"].vertical_panel((box["x"], y, back_z), (1.35, 1.82), "z")
                    for direction in (-1.0, 1.0):
                        accumulators["trim"].box((face_x, y + direction * 1.1, box["z"]), (0.12, 0.20, 1.78))
                        accumulators["trim"].box((face_x, y, box["z"] + direction * 0.82), (0.12, 2.20, 0.20))
                        accumulators["trim"].box((box["x"], y + direction * 1.1, face_z), (1.78, 0.20, 0.12))
                        accumulators["trim"].box((box["x"] + direction * 0.82, y, face_z), (0.20, 2.20, 0.12))
                        accumulators["wood"].box((grille_x, y, box["z"] + direction * 0.28), (0.08, 1.56, 0.10))
                        accumulators["wood"].box((box["x"] + direction * 0.28, y, grille_z), (0.10, 1.56, 0.08))

    # Observatory portal and wind-catcher silhouette.
    obs_segments = (16, 11, 7)[lod]
    arch(accumulators["trim"], (56.0, 11.0, 5.9), 7.2, 0.72, 1.8, "z", obs_segments)
    arch(accumulators["accent"], (56.0, 11.0, 5.72), 6.05, 0.28, 1.96, "z", max(7, obs_segments - 4))
    statistics["portalVoussoirs"] += obs_segments + max(7, obs_segments - 4)
    accumulators["wall_weathered"].box((56.0, 19.2, 6.0), (19.5, 1.0, 2.0))
    for x in (49.0, 52.5, 56.0, 59.5, 63.0):
        accumulators["accent"].box((x, 23.0, 6.0), (0.36, 7.0, 1.2))
    for y in (20.1, 23.0, 25.9):
        accumulators["wood"].box((56.0, y, 6.0), (18.0, 0.28, 1.1))

    # V6 observatory connection map:
    #   authored NE tower top Y=38.88 -> octagonal crown bottom Y=38.55
    #     (0.33 m overlap) -> stepped drum -> mast and four braces -> rings.
    # Two orthogonal astrolabe
    # faces make the instrument legible from both the southern approach (04)
    # and the west/east courtyard axis (06), rather than presenting an edge-on
    # floating circle in one of those views.
    astro_x, astro_z = 26.08, 20.40
    crown_segments = (16, 12, 8)[lod]
    accumulators["trim"].vertical_prism((astro_x, astro_z), 38.55, 40.2, 6.55, crown_segments, math.pi / 8.0)
    accumulators["wall_weathered"].vertical_prism((astro_x, astro_z), 39.85, 43.9, 5.65, crown_segments, math.pi / 8.0)
    accumulators["wall_warm"].vertical_prism((astro_x, astro_z), 43.55, 47.1, 4.55, crown_segments, math.pi / 8.0)
    accumulators["trim"].vertical_prism((astro_x, astro_z), 46.75, 49.8, 3.45, crown_segments, math.pi / 8.0)
    accumulators["accent"].vertical_prism((astro_x, astro_z), 49.3, 52.1, 1.62, (14, 10, 8)[lod])
    accumulators["wood"].box((astro_x, 51.25, astro_z), (7.0, 0.42, 7.0))
    # Four stepped buttresses overlap both the authored tower top and the
    # octagonal plinth.  Their broad corbel caps make the astrolabe's weight
    # believable from the low 04/06 angles without changing the ring itself.
    for axis, direction in (("x", -1.0), ("x", 1.0), ("z", -1.0), ("z", 1.0)):
        if axis == "x":
            bx, bz = astro_x + direction * 4.90, astro_z
            dims, cap_dims = (4.0, 6.8, 4.2), (4.5, 0.72, 4.8)
        else:
            bx, bz = astro_x, astro_z + direction * 4.90
            dims, cap_dims = (4.2, 6.8, 4.0), (4.8, 0.72, 4.5)
        accumulators["wall_weathered"].box((bx, 42.0, bz), dims)
        accumulators["trim"].box((bx, 45.45, bz), cap_dims)

    astrolabe_segments = (34, 22, 14)[lod]
    astrolabe_minor = (6, 5, 4)[lod]
    astrolabe_centre = (astro_x, 61.4, astro_z)
    for plane in ("xy", "yz"):
        accumulators["accent"].torus(astrolabe_centre, 10.2, 0.42, plane, astrolabe_segments, astrolabe_minor)
        accumulators["trim"].torus(astrolabe_centre, 7.8, 0.20, plane, max(18, astrolabe_segments - 6), max(4, astrolabe_minor - 1))
    for axes in (
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
    ):
        for angle in (0.0, math.pi / 4.0, math.pi / 2.0, math.pi * 3.0 / 4.0):
            radial = Vector(axes[0]) * math.cos(angle) + Vector(axes[1]) * math.sin(angle)
            tangent = Vector(axes[0]) * -math.sin(angle) + Vector(axes[1]) * math.cos(angle)
            accumulators["accent"].oriented_box(
                astrolabe_centre,
                (radial, tangent, axes[2]),
                (15.8, 0.24, 0.38),
            )
    accumulators["accent"].vertical_prism((astro_x, astro_z), 50.8, 72.0, 0.56, max(10, astrolabe_minor * 2))
    for start, end in (
        ((astro_x - 2.7, 49.0, astro_z), (astro_x - 7.1, 55.0, astro_z)),
        ((astro_x + 2.7, 49.0, astro_z), (astro_x + 7.1, 55.0, astro_z)),
        ((astro_x, 49.0, astro_z - 2.7), (astro_x, 55.0, astro_z - 7.1)),
        ((astro_x, 49.0, astro_z + 2.7), (astro_x, 55.0, astro_z + 7.1)),
    ):
        beam_between(accumulators["accent"], start, end, (0.34, 0.30, 0.26)[lod])
    accumulators["accent"].cone((astro_x, astro_z), 71.7, 75.4, 1.20, max(10, astrolabe_minor * 2))
    statistics["observatoryHeroHeightM"] = 75.4
    statistics["observatoryHeroSupportHeightM"] = 38.55

    for box in (item for item in observatory_boxes if item.get("landmarkPart") == "tower"):
        top = float(box["y"]) + float(box["h"]) * 0.5
        x, z = float(box["x"]), float(box["z"])
        accumulators["trim"].box((x, top - 0.45, z), (6.2, 0.70, 6.2))
        # Crossed vertical fins read as functioning wind catchers, not generic
        # minaret caps.
        accumulators["accent"].box((x, top + 3.3, z), (0.38, 7.0, 5.2))
        accumulators["accent"].box((x, top + 3.3, z), (5.2, 7.0, 0.38))
        accumulators["wood"].box((x, top + 6.9, z), (6.4, 0.32, 6.4))
        if lod <= 1:
            banner_y = min(top - 3.2, 9.0)
            for side in (-1.0, 1.0):
                banner_z = z + side * (float(box["d"]) * 0.5 + 0.09)
                accumulators["cloth"].box((x, banner_y, banner_z), (1.4, 5.2, 0.07))
                accumulators["accent"].box((x, banner_y + 2.75, banner_z + side * 0.04), (1.78, 0.16, 0.12))
        if lod <= 1:
            for y in (min(top - 2.4, 4.4), min(top - 2.4, 9.0)):
                for side in (-1.0, 1.0):
                    half = min(float(box["w"]), float(box["d"])) * 0.5 + 0.08
                    back_x = x + side * (half - 0.06)
                    back_z = z + side * (half - 0.06)
                    face_x = x + side * (half + 0.14)
                    face_z = z + side * (half + 0.14)
                    grille_x = x + side * (half + 0.10)
                    grille_z = z + side * (half + 0.10)
                    accumulators["wall_warm"].vertical_panel((back_x, y, z), (1.22, 2.0), "x")
                    accumulators["wall_warm"].vertical_panel((x, y, back_z), (1.22, 2.0), "z")
                    for direction in (-1.0, 1.0):
                        accumulators["trim"].box((face_x, y + direction * 1.22, z), (0.12, 0.20, 1.66))
                        accumulators["trim"].box((face_x, y, z + direction * 0.74), (0.12, 2.44, 0.20))
                        accumulators["trim"].box((x, y + direction * 1.22, face_z), (1.66, 0.20, 0.12))
                        accumulators["trim"].box((x + direction * 0.74, y, face_z), (0.20, 2.44, 0.12))
                        accumulators["wood"].box((grille_x, y, z + direction * 0.25), (0.08, 1.72, 0.10))
                        accumulators["wood"].box((x + direction * 0.25, y, grille_z), (0.10, 1.72, 0.08))

    # Coffers beneath the authored upper walks replace the monolithic dark
    # slab read while leaving the collision shell unchanged.
    for box in (item for item in boxes if item.get("landmarkPart") == "upper-walk"):
        x, z = float(box["x"]), float(box["z"])
        width, depth = float(box["w"]), float(box["d"])
        underside = float(box["y"]) - float(box["h"]) * 0.5 - 0.08
        long_x = width >= depth
        interval = (4.8, 7.6, 12.0)[lod]
        length = width if long_x else depth
        count = max(2, int(length // interval))
        for index in range(count + 1):
            offset = -length * 0.5 + length * index / count
            if long_x:
                accumulators["wood"].box((x + offset, underside, z), (0.25, 0.25, depth + 0.18))
            else:
                accumulators["wood"].box((x, underside, z + offset), (width + 0.18, 0.25, 0.25))
            statistics["cofferBeams"] += 1
        # Parallel stringers create a real lattice rather than merely painting
        # dark lines onto the slab.
        for side in (-0.28, 0.28):
            if long_x:
                accumulators["accent"].box((x, underside - 0.06, z + side * depth), (width, 0.16, 0.18))
            else:
                accumulators["accent"].box((x + side * width, underside - 0.06, z), (0.18, 0.16, depth))

    return statistics


def district_surface_pass(
    accumulators: dict[str, MeshAccumulator],
    boxes: list[dict[str, object]],
    lod: int,
) -> dict[str, int]:
    facade_count = 0
    banner_count = 0
    vine_count = 0
    cornice_candidates = []
    for index, box in enumerate(boxes):
        if box.get("landmarkId") or box.get("ghost") or box.get("legacyHorizon"):
            continue
        if not box.get("district"):
            continue
        identity = f"{box.get('district')}:{index}:{box['x']}:{box['z']}"
        facade_count += wall_panels(accumulators, box, lod, identity)
        width, depth, height = float(box["w"]), float(box["d"]), float(box["h"])
        top = float(box["y"]) + height * 0.5
        if lod <= 1 and height >= 6.0 and min(width, depth) <= 2.1 and max(width, depth) >= 7.0:
            along_x = width >= depth
            face_sign = 1.0 if stable_unit(identity, "face") >= 0.5 else -1.0
            if stable_unit(identity, "banner") > (0.72 if lod == 0 else 0.88):
                along = (stable_unit(identity, "banner-pos") - 0.5) * max(width, depth) * 0.48
                banner_y = min(top - 1.7, max(4.1, top - 2.2))
                if along_x:
                    bx, bz = float(box["x"]) + along, float(box["z"]) + face_sign * (depth * 0.5 + 0.11)
                    accumulators["cloth"].box((bx, banner_y, bz), (1.35, 3.1, 0.06))
                    accumulators["accent"].box((bx, banner_y + 1.68, bz + face_sign * 0.04), (1.72, 0.16, 0.12))
                else:
                    bx, bz = float(box["x"]) + face_sign * (width * 0.5 + 0.11), float(box["z"]) + along
                    accumulators["cloth"].box((bx, banner_y, bz), (0.06, 3.1, 1.35))
                    accumulators["accent"].box((bx + face_sign * 0.04, banner_y + 1.68, bz), (0.12, 0.16, 1.72))
                banner_count += 1
            if lod == 0 and stable_unit(identity, "vine") > 0.76:
                along = (stable_unit(identity, "vine-pos") - 0.5) * max(width, depth) * 0.54
                vine_y = max(3.8, top - 1.15)
                if along_x:
                    centre = (float(box["x"]) + along, vine_y, float(box["z"]) + face_sign * (depth * 0.5 + 0.34))
                    radii = (0.95, 1.2, 0.48)
                else:
                    centre = (float(box["x"]) + face_sign * (width * 0.5 + 0.34), vine_y, float(box["z"]) + along)
                    radii = (0.48, 1.2, 0.95)
                accumulators["natural"].ellipsoid(centre, radii, 4, 8)
                vine_count += 1
        if float(box["h"]) >= 5.0 and min(float(box["w"]), float(box["d"])) <= 1.8:
            cornice_candidates.append(box)

    # District-specific roof language prevents the settlement reading as one
    # repeated generic kit.  These accents are overhead and use the authored
    # wall segments as their visible support.
    stride = (2, 4, 8)[lod]
    roof_accents = 0
    for index, box in enumerate(cornice_candidates[::stride]):
        top = float(box["y"]) + float(box["h"]) * 0.5
        district = str(box.get("district"))
        x, z = float(box["x"]), float(box["z"])
        width, depth = float(box["w"]), float(box["d"])
        if district == "cathedral":
            # Shallow stone crest with alternating mineral caps.
            if width >= depth:
                accumulators["wall_warm"].box((x, top + 0.25, z), (width + 0.35, 0.5, min(2.0, depth + 0.35)))
            else:
                accumulators["wall_warm"].box((x, top + 0.25, z), (min(2.0, width + 0.35), 0.5, depth + 0.35))
        elif district == "fortress":
            # Teal metal louver bands break up sandstone massing.
            if width >= depth:
                accumulators["accent"].box((x, top - 0.72, z), (width * 0.88, 0.24, min(1.8, depth + 0.22)))
            else:
                accumulators["accent"].box((x, top - 0.72, z), (min(1.8, width + 0.22), 0.24, depth * 0.88))
        else:
            # Projecting timber eaves retain the caravan-city vocabulary.
            if width >= depth:
                accumulators["wood"].box((x, top + 0.12, z), (width + 0.38, 0.22, min(2.2, depth + 0.38)))
            else:
                accumulators["wood"].box((x, top + 0.12, z), (min(2.2, width + 0.38), 0.22, depth + 0.38))
        roof_accents += 1
    return {
        "facadePanelCount": facade_count,
        "roofAccentCount": roof_accents,
        "bannerCount": banner_count,
        "wallVineCount": vine_count,
    }


def district_rooftop_pass(
    accumulators: dict[str, MeshAccumulator],
    stage: dict[str, object],
    lod: int,
) -> dict[str, int]:
    """Give every non-hero district a distinct, grounded roof silhouette."""
    boxes = list(stage["boxes"])
    rooftop_count = 0
    for placement in stage.get("districtPlacements", []):
        cx, cz = float(placement["cx"]), float(placement["cz"])
        if (abs(cx + 66.0) < 0.1 and abs(cz - 46.0) < 0.1) or (abs(cx - 56.0) < 0.1 and abs(cz - 46.0) < 0.1):
            continue
        width, depth = float(placement["width"]), float(placement["depth"])
        candidates = [
            box for box in boxes
            if box.get("district") == placement.get("kind")
            and abs(float(box["x"]) - cx) <= width * 0.54
            and abs(float(box["z"]) - cz) <= depth * 0.54
            and not box.get("landmarkId")
        ]
        if not candidates:
            continue
        roof_y = max(float(box["y"]) + float(box["h"]) * 0.5 for box in candidates)
        style = str(placement["kind"])
        radial_segments = (14, 10, 8)[lod]
        if style == "cathedral":
            radius = min(width, depth) * 0.115
            accumulators["wall_warm"].vertical_prism((cx, cz), roof_y - 0.15, roof_y + 1.55, radius, radial_segments)
            accumulators["wall_weathered"].dome((cx, cz), roof_y + 1.45, radius * 1.08, radius * 0.72, (5, 4, 3)[lod], radial_segments)
            accumulators["accent"].vertical_prism((cx, cz), roof_y + 1.45 + radius * 0.66, roof_y + 2.55 + radius * 0.72, 0.22, max(8, radial_segments))
            accumulators["accent"].cone((cx, cz), roof_y + 2.45 + radius * 0.72, roof_y + 3.75 + radius * 0.72, 0.72, max(8, radial_segments))
        elif style == "fortress":
            offset = min(width, depth) * 0.18
            for direction in (-1.0, 1.0):
                x = cx + direction * offset
                accumulators["wall_weathered"].box((x, roof_y + 2.0, cz), (3.0, 4.0, 3.0))
                accumulators["accent"].box((x, roof_y + 3.0, cz), (0.26, 4.6, 3.6))
                accumulators["accent"].box((x, roof_y + 3.0, cz), (3.6, 4.6, 0.26))
                accumulators["wood"].box((x, roof_y + 5.35, cz), (4.0, 0.28, 4.0))
        else:
            # A compact stepped caravan-pagoda cap: broad timber eaves with a
            # much smaller stone core, avoiding another generic box tower.
            accumulators["wall_warm"].vertical_prism((cx, cz), roof_y - 0.1, roof_y + 3.0, 1.45, max(8, radial_segments))
            for tier, scale in enumerate((1.0, 0.72, 0.50)):
                y = roof_y + 1.0 + tier * 1.35
                span = min(width, depth) * 0.28 * scale
                accumulators["wood"].box((cx, y, cz), (span, 0.24, span))
                accumulators["accent"].cone((cx, cz), y + 0.08, y + 0.72, span * 0.54, max(8, radial_segments))
        if lod == 0:
            # One soft roof-garden cluster supplies living colour without a
            # player-height trunk or collider mismatch.
            accumulators["natural"].ellipsoid(
                (cx + width * 0.18, roof_y + 0.8, cz - depth * 0.17),
                (1.6, 1.1, 1.4),
                4,
                8,
            )
        rooftop_count += 1
    return {"districtRooftopIdentityCount": rooftop_count}


def coffer_ceiling_pass(
    accumulators: dict[str, MeshAccumulator],
    boxes: list[dict[str, object]],
    lod: int,
) -> dict[str, int]:
    """Skin large slab undersides as beams and inset ceiling cells."""
    if lod == 2:
        return {"cofferCellCount": 0}
    cell_target = (4.4, 6.4)[lod]
    candidates = [
        box for box in boxes
        if not box.get("legacyHorizon")
        and float(box["h"]) <= 0.76
        and float(box["y"]) - float(box["h"]) * 0.5 >= 3.0
        and float(box["w"]) >= 3.0
        and float(box["d"]) >= 3.0
    ]
    count = 0
    for candidate_index, box in enumerate(candidates):
        x, z = float(box["x"]), float(box["z"])
        width, depth = float(box["w"]), float(box["d"])
        underside = float(box["y"]) - float(box["h"]) * 0.5 - 0.055
        nx = max(1, min(14, int(math.ceil(width / cell_target))))
        nz = max(1, min(14, int(math.ceil(depth / cell_target))))
        cell_w, cell_d = width / nx, depth / nz
        for ix in range(nx):
            for iz in range(nz):
                cx = x - width * 0.5 + cell_w * (ix + 0.5)
                cz = z - depth * 0.5 + cell_d * (iz + 0.5)
                role = "wall_warm" if (ix + iz + candidate_index) % 3 else "wood"
                accumulators[role].horizontal_panel(
                    (cx, underside, cz),
                    (max(0.35, cell_w - 0.20), max(0.35, cell_d - 0.20)),
                    upward=False,
                )
                count += 1
        for ix in range(nx + 1):
            cx = x - width * 0.5 + cell_w * ix
            accumulators["accent"].box((cx, underside - 0.055, z), (0.12, 0.12, depth))
        for iz in range(nz + 1):
            cz = z - depth * 0.5 + cell_d * iz
            accumulators["accent"].box((x, underside - 0.055, cz), (width, 0.12, 0.12))
    return {"cofferCellCount": count}


def paving_pass(accumulators: dict[str, MeshAccumulator], lod: int) -> dict[str, int]:
    """Lay irregular coursed limestone over the previous orange plane.

    V6 uses larger, staggered stones with deterministic per-row width/depth
    changes.  Besides avoiding the tiled-board-game read, the lower module
    count pays for the hero silhouettes without increasing the LOD0 budget.
    """
    if lod == 2:
        return {"pavingStoneCount": 0, "sandPatchCount": 0}
    tile_x, tile_z = ((5.4, 6.2), (8.2, 9.0))[lod]
    zones = (
        (-8.2, 11.2, -145.0, 145.0),
        (-121.0, -11.0, 10.0, 82.0),
        (14.0, 98.0, 8.0, 84.0),
    )
    stone_count = 0
    for zone_index, (min_x, max_x, min_z, max_z) in enumerate(zones):
        row = 0
        cursor_z = min_z
        while cursor_z < max_z - 0.01:
            row_identity = f"paving-row:{zone_index}:{row}"
            row_depth = tile_z * (0.82 + 0.34 * stable_unit(row_identity, "depth"))
            end_z = min(max_z, cursor_z + row_depth)
            phase = (0.0, 0.50, 0.24)[row % 3]
            cursor_x = min_x - phase * tile_x
            column = 0
            while cursor_x < max_x - 0.01:
                identity = f"paving:{zone_index}:{row}:{column}"
                stone_width = tile_x * (0.74 + 0.50 * stable_unit(identity, "width"))
                start_x = max(min_x, cursor_x)
                end_x = min(max_x, cursor_x + stone_width)
                visible_width = end_x - start_x
                visible_depth = end_z - cursor_z
                if visible_width > 1.15 and visible_depth > 1.15:
                    cx = (start_x + end_x) * 0.5 + (stable_unit(identity, "x") - 0.5) * 0.05
                    cz = (cursor_z + end_z) * 0.5 + (stable_unit(identity, "z") - 0.5) * 0.05
                    yaw = (stable_unit(identity, "yaw") - 0.5) * 0.018
                    # Material value changes in broad 2-row × 3-stone fields,
                    # not per-tile noise.  This creates low-frequency dust and
                    # wear zones while retaining coursing and route legibility.
                    selector = stable_unit("paving-cluster", zone_index, row // 2, column // 3)
                    role = "road" if selector < 0.58 else "wall_warm" if selector < 0.86 else "wall_weathered"
                    accumulators[role].horizontal_panel(
                        (cx, 0.026 + stable_unit(identity, "height") * 0.012, cz),
                        (visible_width - 0.13, visible_depth - 0.13),
                        yaw,
                    )
                    stone_count += 1
                cursor_x += stone_width
                column += 1
            cursor_z = end_z
            row += 1
    # Soft sand deposits at court edges break the perfect paving coverage.
    sand_patches = (
        (-115.0, 0.055, 16.0, 4.2, 0.04, 2.3), (-18.0, 0.055, 76.0, 3.8, 0.04, 2.0),
        (19.0, 0.055, 14.0, 3.5, 0.04, 2.4), (92.0, 0.055, 78.0, 4.0, 0.04, 2.2),
        (-6.2, 0.055, -92.0, 2.4, 0.04, 4.4), (9.0, 0.055, 92.0, 2.2, 0.04, 4.0),
        (-105.0, 0.052, 42.0, 7.2, 0.035, 2.1), (-25.0, 0.052, 55.0, 6.0, 0.035, 1.8),
        (26.0, 0.052, 33.0, 5.4, 0.035, 2.0), (86.0, 0.052, 61.0, 6.5, 0.035, 1.9),
        (-91.0, 0.050, -20.0, 4.8, 0.030, 1.6), (-37.0, 0.050, -34.0, 5.2, 0.030, 1.7),
    )
    for x, y, z, rx, ry, rz in sand_patches:
        accumulators["terrain"].ellipsoid((x, y, z), (rx, ry, rz), 3, (12, 8)[lod])
    return {"pavingStoneCount": stone_count, "sandPatchCount": len(sand_patches)}


def weathering_pass(
    accumulators: dict[str, MeshAccumulator],
    boxes: list[dict[str, object]],
    lod: int,
) -> dict[str, int]:
    """Add broad mineral stains and worn base courses without new materials.

    These are intentionally low-frequency clusters rather than a repeated
    grime decal on every module.  The back faces remain within 2 cm of the
    authoritative wall and the 8 cm edge courses remain under the 20 cm visual
    relief allowance.
    """
    if lod == 2:
        return {"mineralStainCount": 0, "wornEdgeCourseCount": 0}
    candidates = [
        box for box in boxes
        if not box.get("ghost")
        and not box.get("legacyHorizon")
        and float(box["h"]) >= 4.4
        and min(float(box["w"]), float(box["d"])) <= 2.1
        and max(float(box["w"]), float(box["d"])) >= 7.0
    ]
    stride = (7, 13)[lod]
    stain_count = 0
    edge_count = 0
    for candidate_index, box in enumerate(candidates[::stride]):
        width, depth, height = float(box["w"]), float(box["d"]), float(box["h"])
        bottom = float(box["y"]) - height * 0.5
        top = float(box["y"]) + height * 0.5
        if top < 2.0:
            continue
        along_x = width >= depth
        length = width if along_x else depth
        identity = f"weathering:{candidate_index}:{box['x']}:{box['z']}"
        side = 1.0 if stable_unit(identity, "side") >= 0.5 else -1.0
        patch_width = min(length * 0.46, 5.0 + stable_unit(identity, "span") * 4.0)
        patch_height = 0.72 + stable_unit(identity, "height") * 0.75
        along = (stable_unit(identity, "offset") - 0.5) * max(0.0, length - patch_width) * 0.72
        centre_y = max(0.08 + patch_height * 0.5, bottom + patch_height * 0.5 + 0.04)
        if along_x:
            surface = float(box["z"]) + side * depth * 0.5
            accumulators["wall_weathered"].vertical_panel(
                (float(box["x"]) + along, centre_y, surface + side * 0.016),
                (patch_width, patch_height),
                "z",
            )
            accumulators["trim"].box(
                (float(box["x"]) + along * 0.62, centre_y + patch_height * 0.50, surface + side * 0.055),
                (patch_width * 0.36, 0.10, 0.08),
            )
        else:
            surface = float(box["x"]) + side * width * 0.5
            accumulators["wall_weathered"].vertical_panel(
                (surface + side * 0.016, centre_y, float(box["z"]) + along),
                (patch_width, patch_height),
                "x",
            )
            accumulators["trim"].box(
                (surface + side * 0.055, centre_y + patch_height * 0.50, float(box["z"]) + along * 0.62),
                (0.08, 0.10, patch_width * 0.36),
            )
        stain_count += 1
        edge_count += 1
    return {"mineralStainCount": stain_count, "wornEdgeCourseCount": edge_count}


def collision_prop_pass(
    accumulators: dict[str, MeshAccumulator],
    stage: dict[str, object],
    lod: int,
) -> dict[str, int]:
    """Turn existing prop/breakable colliders into readable market objects."""
    boxes = [box for box in stage["boxes"] if box.get("breakable")]
    if lod == 2:
        boxes = boxes[::4]
    elif lod == 1:
        boxes = boxes[::2]
    cart_count = 0
    clutter_count = 0
    wheel_segments = (16, 10, 7)[lod]
    for index, box in enumerate(boxes):
        x, z = float(box["x"]), float(box["z"])
        width, depth, height = float(box["w"]), float(box["d"]), float(box["h"])
        bottom = float(box["y"]) - height * 0.5
        if height <= 1.65 and max(width, depth) >= 3.8:
            long_x = width >= depth
            body_w = width * (0.70 if long_x else 0.72)
            body_d = depth * (0.72 if long_x else 0.70)
            body_h = min(0.72, height * 0.58)
            accumulators["wood"].box((x, bottom + body_h * 0.5 + 0.34, z), (body_w, body_h, body_d))
            accumulators["trim"].box((x, bottom + body_h + 0.40, z), (body_w * 0.96, 0.10, body_d * 0.96))
            radius = min(0.52, max(0.32, height * 0.36))
            if long_x:
                for wx in (-body_w * 0.32, body_w * 0.32):
                    for wz in (-body_d * 0.53, body_d * 0.53):
                        accumulators["wood"].torus((x + wx, bottom + radius, z + wz), radius, 0.09, "xy", wheel_segments, 4)
            else:
                for wz in (-body_d * 0.32, body_d * 0.32):
                    for wx in (-body_w * 0.53, body_w * 0.53):
                        accumulators["wood"].torus((x + wx, bottom + radius, z + wz), radius, 0.09, "yz", wheel_segments, 4)
            cart_count += 1
        else:
            # Nested crates and ceramic jars remain fully inside the existing
            # breakable volume.
            if height >= 0.75:
                crate_h = min(height * 0.62, 1.15)
                accumulators["wood"].box((x, bottom + crate_h * 0.5, z), (width * 0.72, crate_h, depth * 0.72))
                for side in (-1.0, 1.0):
                    if width >= depth:
                        accumulators["accent"].box((x + side * width * 0.28, bottom + crate_h * 0.58, z), (0.12, crate_h * 0.82, depth * 0.76))
                    else:
                        accumulators["accent"].box((x, bottom + crate_h * 0.58, z + side * depth * 0.28), (width * 0.76, crate_h * 0.82, 0.12))
            if lod == 0 and width >= 1.8 and depth >= 1.8:
                for jar_index in range(2):
                    angle = math.tau * (stable_unit(index, jar_index, "angle"))
                    radius = min(width, depth) * 0.21
                    px, pz = x + math.cos(angle) * radius, z + math.sin(angle) * radius
                    jar_top = min(bottom + height * 0.92, bottom + 1.25)
                    accumulators["ceramic"].vertical_prism((px, pz), bottom, jar_top, 0.32 + jar_index * 0.06, 10)
                    accumulators["ceramic"].vertical_prism((px, pz), jar_top - 0.12, jar_top + 0.08, 0.20, 10)
            clutter_count += 1

    lantern_count = 0
    for placement in stage.get("propPlacements", []):
        kind = placement.get("kind")
        if kind != "stonelantern" or (lod == 2 and lantern_count % 2):
            continue
        x, z = float(placement["cx"]), float(placement["cz"])
        accumulators["wall_weathered"].box((x, 0.15, z), (0.48, 0.30, 0.48))
        accumulators["wall_warm"].vertical_prism((x, z), 0.28, 1.02, 0.17, (10, 8, 6)[lod])
        accumulators["trim"].box((x, 1.12, z), (0.66, 0.22, 0.66))
        accumulators["accent"].cone((x, z), 1.18, 1.48, 0.43, (10, 8, 6)[lod])
        lantern_count += 1
    return {"cartCount": cart_count, "crateOrJarClusterCount": clutter_count, "stoneLanternCount": lantern_count}


def horizon_city_pass(accumulators: dict[str, MeshAccumulator], lod: int) -> dict[str, int]:
    """Layer real unreachable 3D city and rock silhouettes beyond the map."""
    per_side = (8, 7, 5)[lod]
    building_count = 0
    radial_segments = (10, 8, 6)[lod]
    for side_index, side in enumerate(("north", "south", "west", "east")):
        for index in range(per_side):
            along = -205.0 + 410.0 * (index + 0.5) / per_side
            depth_layer = index % 2
            distance = 205.0 + depth_layer * 34.0
            if side == "north":
                x, z = along, distance
            elif side == "south":
                x, z = along, -distance
            elif side == "west":
                x, z = -distance, along
            else:
                x, z = distance, along
            identity = f"horizon:{side}:{index}"
            width = 14.0 + stable_unit(identity, "w") * 13.0
            depth = 13.0 + stable_unit(identity, "d") * 13.0
            height = 13.0 + stable_unit(identity, "h") * 20.0 + (7.0 if index % 5 == 0 else 0.0)
            role = "horizon_cool" if index % 3 == 0 else "horizon_warm"
            accumulators[role].box((x, height * 0.5, z), (width, height, depth))
            crown_w, crown_d = width * 0.58, depth * 0.58
            crown_h = 2.5 + stable_unit(identity, "crown") * 4.5
            accumulators["trim"].box((x, height + crown_h * 0.5, z), (crown_w, crown_h, crown_d))
            # Distant but real facade depth: pale belt courses and vertical
            # buttresses keep the skyline from reading as placeholder cubes.
            for band_y in (height * 0.35, height * 0.70):
                accumulators["horizon_trim"].box((x, band_y, z), (width + 0.22, 0.24, depth + 0.22))
            for direction in (-0.28, 0.28):
                if side in {"north", "south"}:
                    face_z = z - math.copysign(depth * 0.5 + 0.08, z)
                    accumulators["horizon_trim"].box((x + direction * width, height * 0.48, face_z), (0.22, height * 0.84, 0.16))
                else:
                    face_x = x - math.copysign(width * 0.5 + 0.08, x)
                    accumulators["horizon_trim"].box((face_x, height * 0.48, z + direction * depth), (0.16, height * 0.84, 0.22))
            if index % 3 == 1:
                accumulators["accent"].cone((x, z), height + crown_h, height + crown_h + 5.5, min(crown_w, crown_d) * 0.34, radial_segments)
            elif index % 3 == 2:
                accumulators["wood"].box((x, height + crown_h + 0.25, z), (crown_w * 1.28, 0.42, crown_d * 1.28))
            building_count += 1
    hill_count = 0
    hills = (
        (-226.0, -5.0, -220.0, 62.0, 30.0, 48.0), (220.0, -7.0, -214.0, 70.0, 34.0, 50.0),
        (-232.0, -8.0, 218.0, 68.0, 31.0, 52.0), (224.0, -6.0, 226.0, 64.0, 28.0, 46.0),
        (-76.0, -10.0, 224.0, 52.0, 25.0, 42.0), (88.0, -9.0, -226.0, 58.0, 27.0, 44.0),
    )
    for index, (x, y, z, rx, ry, rz) in enumerate(hills[::(1 if lod == 0 else 2)]):
        accumulators["terrain"].ellipsoid((x, y, z), (rx, ry, rz), (5, 4, 3)[lod], (14, 10, 8)[lod])
        hill_count += 1
    return {"horizonBuildingCount": building_count, "horizonRockHillCount": hill_count}


def set_dressing(accumulators: dict[str, MeshAccumulator], lod: int) -> dict[str, int]:
    # Rugs/mosaics are 3 cm high and therefore never become a collision step.
    rugs = (
        (-88.0, 0.025, 40.0, 8.0, 12.0), (-44.0, 0.025, 52.0, 8.0, 12.0),
        (36.0, 0.025, 40.0, 7.0, 12.0), (78.0, 0.025, 52.0, 7.0, 12.0),
        # Flush south-plaza mosaics activate the previously blank approach
        # without narrowing the protected road/firing lanes.
        (-94.0, 0.025, -34.0, 8.5, 7.0), (-40.0, 0.025, -34.0, 8.0, 7.0),
        (40.0, 0.025, -32.0, 8.0, 7.0), (72.0, 0.025, -32.0, 8.5, 7.0),
        (-66.0, 0.025, -108.0, 7.5, 8.5), (-66.0, 0.025, -62.0, 7.5, 8.5),
    )
    for index, (x, y, z, width, depth) in enumerate(rugs):
        accumulators["road"].box((x, y, z), (width, 0.05, depth))
        if lod <= 1:
            for stripe in (-0.28, 0.0, 0.28):
                accumulators["accent"].box((x + stripe * width, y + 0.03, z), (0.18, 0.035, depth * 0.88))

    # Thin reflective channels are decorative floor insets, not an expensive
    # planar-reflection pass.  They sit in side courts rather than routes.
    channels = (
        (-112.0, 0.035, 46.0, 1.35, 42.0), (-20.0, 0.035, 46.0, 1.35, 42.0),
        (21.0, 0.035, 46.0, 1.35, 46.0), (91.0, 0.035, 46.0, 1.35, 46.0),
    )
    for x, y, z, width, depth in channels:
        accumulators["water"].box((x, y, z), (width, 0.06, depth))
        accumulators["trim"].box((x - width * 0.62, 0.08, z), (0.18, 0.16, depth + 0.4))
        accumulators["trim"].box((x + width * 0.62, 0.08, z), (0.18, 0.16, depth + 0.4))

    # The central avenue keeps its full traversal width, but receives inset
    # stone/brass courses so it no longer reads as one untextured tan plane.
    course_step = (10.0, 18.0, 32.0)[lod]
    course_count = int(270.0 // course_step)
    for index in range(course_count + 1):
        z = -135.0 + 270.0 * index / max(1, course_count)
        accumulators["trim"].box((1.5, 0.025, z), (18.0, 0.05, 0.13))
        if lod == 0 and index % 2 == 0:
            accumulators["accent"].box((1.5, 0.045, z), (5.2, 0.035, 0.08))
    medallion_segments = (28, 18, 12)[lod]
    for z in (-78.0, -26.0, 106.0):
        accumulators["accent"].torus((1.5, 0.055, z), 2.35, 0.09, "xz", medallion_segments, 4)

    if lod == 2:
        return {
            "rugCount": len(rugs), "waterChannelCount": len(channels),
            "planterCount": 0, "hangingGreeneryCount": 0, "wallBenchCount": 0,
            "potteryClusterCount": 0, "shadeCount": 0, "basinCount": 0,
            "wallTreeCount": 0,
        }

    # Cantilevered market awnings activate side plazas without adding posts to
    # firing lanes.  Every beam starts inside an authored perimeter wall and
    # the cloth remains above the 2.35 m player band.
    awnings = (
        (-122.35, -115.20, 22.0), (-9.65, -16.80, 70.0),
        (12.35, 19.50, 22.0), (99.65, 92.50, 70.0),
    )
    for index, (anchor_x, edge_x, z) in enumerate(awnings):
        centre_x = (anchor_x + edge_x) * 0.5
        span = abs(edge_x - anchor_x) + 0.6
        accumulators["cloth"].box((centre_x, 3.72, z), (span, 0.10, 8.2))
        for z_offset in (-3.35, 3.35):
            beam_between(accumulators["wood"], (anchor_x, 3.58, z + z_offset), (edge_x, 3.58, z + z_offset), 0.14)
            beam_between(accumulators["wood"], (anchor_x, 2.10, z + z_offset), (edge_x, 3.52, z + z_offset), 0.12)
        # Alternating oxidised leading edges prevent a copied red-roof read.
        if index % 2 == 0:
            accumulators["accent"].box((edge_x, 3.62, z), (0.14, 0.22, 8.5))

    # Two shallow reflective basins sit well outside the principal axes.  The
    # rim is 18 cm high, below the collision relief threshold.
    basins = ((-94.0, 55.0), (77.0, 38.0))
    basin_segments = (24, 16)[lod]
    for x, z in basins:
        accumulators["trim"].torus((x, 0.15, z), 2.35, 0.18, "xz", basin_segments, 4)
        accumulators["water"].vertical_prism((x, z), 0.045, 0.065, 2.15, basin_segments)

    # Wall-overlapping trunks preserve deterministic collision while broad,
    # soft crowns add shade and vertical scale to the empty courts.
    wall_trees = ((-122.55, 22.0), (-9.45, 70.0), (12.55, 22.0), (99.45, 70.0))
    tree_segments = 8 if lod == 0 else 6
    for index, (x, z) in enumerate(wall_trees):
        accumulators["trim"].box((x, 0.09, z), (1.55, 0.18, 1.55))
        accumulators["wood"].vertical_prism((x, z), 0.12, 4.65, 0.24, tree_segments, index * 0.21)
        accumulators["natural"].ellipsoid(
            (x + (0.18 if index % 2 else -0.18), 5.35, z),
            (2.25, 2.20, 2.05),
            (5, 4)[lod],
            (10, 8)[lod],
        )

    # Planters hug already-colliding outer/interior wall corners.  Foliage is
    # soft, visually permeable dressing and never sits in an approach route.
    planters = (
        (-116.6, 1.0, 27.0), (-116.6, 1.0, 65.0), (-15.4, 1.0, 27.0), (-15.4, 1.0, 65.0),
        (18.0, 1.0, 25.0), (18.0, 1.0, 67.0), (94.0, 1.0, 25.0), (94.0, 1.0, 67.0),
    )
    foliage_segments = 8 if lod == 0 else 6
    for index, (x, y, z) in enumerate(planters):
        # The curb is only 18 cm high, below the gate's raised-floor audit
        # threshold.  Leaves remain soft/permeable natural dressing.
        accumulators["trim"].box((x, 0.09, z), (1.45, 0.18, 1.45))
        accumulators["natural"].vertical_prism((x - 0.28, z + 0.12), 0.16, 1.55, 0.52, foliage_segments, index * 0.19)
        accumulators["natural"].vertical_prism((x + 0.28, z - 0.12), 0.16, 1.38, 0.46, foliage_segments, index * 0.31)

    hanging_greenery = (
        (-121.95, 4.8, 30.0, 0.50, 1.45, 1.15), (-121.95, 5.3, 63.0, 0.50, 1.75, 1.20),
        (-10.05, 5.1, 31.0, 0.50, 1.55, 1.15), (-10.05, 4.7, 64.0, 0.50, 1.35, 1.20),
        (12.05, 5.5, 30.0, 0.50, 1.75, 1.20), (12.05, 4.9, 64.0, 0.50, 1.45, 1.15),
        (99.95, 5.2, 31.0, 0.50, 1.55, 1.20), (99.95, 5.6, 64.0, 0.50, 1.80, 1.15),
    )
    if lod == 0:
        for x, y, z, rx, ry, rz in hanging_greenery:
            accumulators["natural"].ellipsoid((x, y, z), (rx, ry, rz), 4, 8)

    # Wall-hugging benches and pottery activate the previously empty courts.
    # Their backs overlap authored outer-wall collision, while the seats stay
    # shallow enough not to narrow firing lanes.
    benches = (
        (-121.55, 35.0, True), (-10.45, 60.0, True),
        (13.55, 34.0, True), (98.45, 60.0, True),
    )
    for x, z, along_z in benches:
        if along_z:
            accumulators["wood"].box((x, 0.43, z), (0.54, 0.18, 4.2))
            back_x = x - 0.24 if x < 0 else x + 0.24
            accumulators["wood"].box((back_x, 1.02, z), (0.16, 1.18, 4.2))
            for offset in (-1.65, 1.65):
                accumulators["accent"].box((x, 0.25, z + offset), (0.18, 0.5, 0.18))

    pottery = (
        (-120.7, 26.0), (-120.5, 68.0), (-11.2, 26.0), (-11.0, 68.0),
        (14.2, 24.0), (14.0, 70.0), (97.8, 24.0), (98.0, 70.0),
        (-102.0, 80.6), (-30.0, 80.6), (28.0, 83.5), (84.0, 83.5),
    )
    for index, (x, z) in enumerate(pottery):
        radius = 0.25 + 0.05 * (index % 3)
        height = 0.48 + 0.08 * (index % 2)
        accumulators["ceramic"].vertical_prism((x, z), 0.0, height, radius, (10, 8)[lod])
        accumulators["ceramic"].vertical_prism((x, z), height - 0.08, height + 0.06, radius * 0.64, (10, 8)[lod])
        if lod == 0 and index % 2 == 0:
            accumulators["ceramic"].vertical_prism((x + 0.48, z + 0.18), 0.0, height * 0.72, radius * 0.72, 8)

    return {
        "rugCount": len(rugs),
        "waterChannelCount": len(channels),
        "planterCount": len(planters),
        "hangingGreeneryCount": len(hanging_greenery) if lod == 0 else 0,
        "wallBenchCount": len(benches),
        "potteryClusterCount": len(pottery),
        "shadeCount": len(awnings),
        "basinCount": len(basins),
        "wallTreeCount": len(wall_trees),
    }


def triangles(obj: bpy.types.Object) -> int:
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def main() -> None:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    layouts_path = args.layouts.expanduser().resolve()
    if not input_path.is_file() or not layouts_path.is_file():
        raise RuntimeError("input GLB or stage layout is missing")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(input_path))
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    # The procedural contact shell historically exported tiny black glass and
    # emissive cards.  They are not openings and were the source of the stage's
    # misaligned black-window defect, so V6 deliberately omits those visual
    # cards while retaining every wall/collider surface behind them.
    removed_dark_cards = [
        obj for obj in imported
        if "_glass" in obj.name.lower() or "_emissive" in obj.name.lower()
    ]
    removed_dark_card_names = [obj.name for obj in removed_dark_cards]
    removed_dark_card_name_set = set(removed_dark_card_names)
    base = [obj for obj in imported if obj.name not in removed_dark_card_name_set]
    for obj in removed_dark_cards:
        bpy.data.objects.remove(obj, do_unlink=True)
    if not base:
        raise RuntimeError("input GLB contains no mesh")
    provenance_keys = (
        "hibanaStage", "hibanaLod", "hibanaMegaLandmarks", "hibanaCityArchetype",
        "hibanaDenseBuildingTarget", "hibanaGeneratorVersion", "hibanaGeneratorSha",
        "hibanaPlacementSource", "hibanaKairouCollisionBackedVisualBuildingCount",
    )
    provenance = {key: base[0][key] for key in provenance_keys if key in base[0]}
    stage = stage_layout(layouts_path)
    boxes = list(stage["boxes"])

    accumulators = {
        role: MeshAccumulator(role)
        for role in (
            "wall_warm", "wall_weathered", "trim", "wood", "accent",
            "natural", "road", "terrain", "water", "cloth", "ceramic",
            "horizon_cool", "horizon_warm", "horizon_trim",
        )
    }
    landmark_stats = landmark_surface_pass(accumulators, boxes, args.lod)
    district_stats = district_surface_pass(accumulators, boxes, args.lod)
    district_stats.update(district_rooftop_pass(accumulators, stage, args.lod))
    ceiling_stats = coffer_ceiling_pass(accumulators, boxes, args.lod)
    paving_stats = paving_pass(accumulators, args.lod)
    weathering_stats = weathering_pass(accumulators, boxes, args.lod)
    prop_stats = collision_prop_pass(accumulators, stage, args.lod)
    horizon_stats = horizon_city_pass(accumulators, args.lod)
    dressing_stats = set_dressing(accumulators, args.lod)

    water = create_simple_material("HBMAT_kairou_water_teal", "#236d75", 0.20, 0.06)
    water["hibanaPbrFamily"] = "shallow-reflective-water"
    water["hibanaPlanarReflection"] = False
    cloth = create_simple_material("HBMAT_kairou_market_cloth", "#a63f35", 0.72, 0.0)
    cloth["hibanaPbrFamily"] = "woven-market-textile"
    teal_metal = create_simple_material("HBMAT_kairou_surface_teal_metal", "#2c7775", 0.38, 0.54)
    teal_metal["hibanaPbrFamily"] = "oxidised-teal-bronze"
    ceramic = create_simple_material("HBMAT_kairou_terracotta_ceramic", "#95543d", 0.62, 0.0)
    ceramic["hibanaPbrFamily"] = "unglazed-terracotta"
    # Reuse the three tracked, textured stone values for hero surfaces.  Their
    # normal/ORM response is substantially richer than a flat colour material;
    # neutral QA daylight supplies the requested limestone read.
    limestone_light = find_material("HBMAT_kairou_wall_warm")
    limestone_mid = find_material("HBMAT_kairou_wall_weathered")
    limestone_trim = find_material("HBMAT_kairou_trim")
    dark_wood = find_material("HBMAT_kairou_wood")
    foliage = create_simple_material("HBMAT_kairou_surface_foliage", "#356144", 0.86, 0.0)
    foliage["hibanaPbrFamily"] = "dry-climate-greenery"
    role_materials = {
        "wall_warm": limestone_light,
        "wall_weathered": limestone_mid,
        "trim": limestone_trim,
        "wood": dark_wood,
        "accent": teal_metal,
        "natural": foliage,
        "road": limestone_light,
        "terrain": find_material("HBMAT_kairou_terrain"),
        "water": water,
        "cloth": cloth,
        "ceramic": ceramic,
        "horizon_cool": limestone_mid,
        "horizon_warm": limestone_light,
        "horizon_trim": limestone_trim,
    }
    surface_objects = [
        obj
        for role, accumulator in accumulators.items()
        if (obj := build_object(accumulator, role_materials[role], args.lod, provenance)) is not None
    ]

    selected = base + surface_objects
    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base[0]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(args.output.expanduser().resolve()),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_tangents=False,
        export_cameras=False,
        export_lights=False,
        export_extras=True,
    )

    base_triangles = sum(triangles(obj) for obj in base)
    surface_triangles = sum(triangles(obj) for obj in surface_objects)
    report = {
        "schemaVersion": 1,
        "status": "PASS",
        "stage": "kairou",
        "artRevision": "v10.1-surface-pass-v6.3.3",
        "lod": args.lod,
        "input": str(input_path),
        "output": str(args.output.expanduser().resolve()),
        "collisionAuthority": str(layouts_path),
        "baseObjectCount": len(base),
        "surfaceObjectCount": len(surface_objects),
        "baseTriangles": base_triangles,
        "surfaceTriangles": surface_triangles,
        "totalTriangles": base_triangles + surface_triangles,
        "surfaceTrianglesByRole": {role: accumulator.triangles for role, accumulator in accumulators.items()},
        "materialCount": len({material.name for obj in selected for material in obj.data.materials if material}),
        "blackWindowPolicy": {
            "newDarkCards": 0,
            "newGlassPanes": 0,
            "removedLegacyDarkCardCount": len(removed_dark_card_names),
            "removedLegacyDarkCards": removed_dark_card_names,
            "replacementLanguage": "warm framed timber/teal lattice shutters",
        },
        "playerHeightPolicy": "BoxSpec-contained or <=0.20m relief; hero silhouettes start overhead",
        "landmarkStatistics": landmark_stats,
        "districtStatistics": district_stats,
        "ceilingStatistics": ceiling_stats,
        "pavingStatistics": paving_stats,
        "weatheringStatistics": weathering_stats,
        "collisionPropStatistics": prop_stats,
        "horizonStatistics": horizon_stats,
        "setDressingStatistics": dressing_stats,
        "provenance": provenance,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
