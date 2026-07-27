"""A23 orphan-emissive / fake-contact audit — the direct-measurement fix for
``measurementDefect3`` (see the round-state log and
``docs/A23_TOOLCHAIN.md``'s "4. change detection blindness"):

    "flat emissive rectangles with open sky on all four sides and no parent
    surface" survived twenty-plus iterations because every metric in the
    round was a diff against a control render, and a defect present in
    *both* frames produces zero delta and is invisible to a diff by
    construction.

This module measures one absolute geometric fact per primitive, never a
diff: does it touch something solid? It has two front ends over the same
core (``_audit_components``):

  - ``audit_mesh_parts`` — the release/build-time gate. Takes
    ``build_all_stages.py``'s own ``MeshBuilder`` part storage
    (``{material_key: {"verts": [...], "faces": [...]}}``, already in world/
    Blender-space at that point) with **no bpy import required**: welding,
    connected-component reconstruction and AABB extraction are pure
    Python/arithmetic. Wired into ``MeshBuilder.flush()`` so every one of
    the ~40 ``add_*`` authoring functions across 31 stages is covered by a
    single call site, and into the release GLB gate independently, mirroring
    ``validate-black-window-release-gate.mjs``'s dual Python-build-time /
    post-export-JS defence for the sibling black-window defect class.
  - ``audit_specs`` — the dry-run front end for spec-list architectures
    (``tools/blender/a23_bridge.py``'s district-infill planner, and any
    ``SpecKit``-conforming stage kit such as nakaniwa's). Needs no bpy and no
    built mesh at all, so ``a23_bridge.plan_district_infill`` can reject a
    plan before a single triangle reaches Blender.

Contact model
-------------
Two axis-aligned world bounds ``(x0, y0, z0, x1, y1, z1)`` are in *contact*
-- the first (``a_bounds``, the prop being tested) resting against the
second (``b_bounds``, the candidate host) -- if, for some axis (the
"normal" axis), their extents are separated by no more than
``touch_tolerance_m`` (0 = flush, positive = a real but small gap; negative
= overlapping/embedded, always accepted) **and**, on both of the other two
("tangent") axes, their extents overlap by a physically meaningful amount
(``min_overlap_abs_m`` absolute floor, or ``min_overlap_fraction`` of
``a_bounds``' *own* extent on that axis, whichever is larger) — a corner or
edge graze, or a large prop merely grazing a much smaller candidate, is not
support (see ``contact_gap``'s own docstring for the confirmed false
negative this asymmetric rule fixes: a 48 m emissive beam counted as
"supported" by 2 m of embedding in one end pillar under a symmetric rule).
This single primitive (``contact_gap``) answers both questions this round's
catalogue-wide defect list asks:

  - "does this emissive card touch a wall/deck/post/bracket?" (the normal
    axis is usually the card's thin depth axis), and
  - "does this roof/stair actually rest on what it appears to sit on?"
    (the normal axis is usually vertical) — the fake-contact sweep
    (z04's hovering roof, takadai's stacks, onsengai's gapped stair) reuses
    this exact function rather than a second, differently-tuned check.

``touch_tolerance_m`` defaults to 0.06 m, matching the wall-clearance upper
bound the black-window release gate already established
(``MAX_WALL_CLEARANCE_M`` in ``validate-black-window-release-gate.mjs``) so
this module does not invent a second, drifting definition of "close enough
to read as attached" for the same GLB family.

A component whose own material key is itself in ``excluded_parent_keys``
(emissive by default) can never satisfy another emissive component's
contact requirement — two glowing cards that only touch each other, with
sky on the far side of both, are exactly the defect this exists to catch,
not a self-supporting pair.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

Point3 = tuple  # (x, y, z)
Bounds6 = tuple  # (x0, y0, z0, x1, y1, z1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OrphanAuditConfig:
    weld_precision_m: float = 0.0001  # matches WELD_PRECISION_M in the JS gate
    touch_tolerance_m: float = 0.06  # matches MAX_WALL_CLEARANCE_M precedent
    min_overlap_abs_m: float = 0.05
    min_overlap_fraction: float = 0.2
    emissive_keys: frozenset = field(default_factory=lambda: frozenset({"emissive"}))
    # Roles that may never stand in as another emissive prop's sole support.
    excluded_parent_keys: frozenset = field(default_factory=lambda: frozenset({"emissive"}))
    # Elongated-object guard (see _major_axis_overlap_ok's docstring): a beam/
    # strip whose longest extent is at least this many times its two other
    # extents must also clear a fraction of ITS OWN LONGEST AXIS specifically,
    # not merely the two tangent axes contact_gap happened to pick for its
    # best-scoring normal axis. Without this, an elongated object can pass
    # contact_gap by treating its own long axis as the "normal" (gap) axis,
    # where a shallow end-embed into a candidate that fully contains the
    # object's thin cross-section satisfies the tangent checks trivially.
    elongation_ratio: float = 6.0
    major_axis_min_overlap_fraction: float = 0.25


# ---------------------------------------------------------------------------
# Welding + connected components (mesh front end only).
# ---------------------------------------------------------------------------
class _DisjointSet:
    __slots__ = ("parent", "rank")

    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            nxt = self.parent[value]
            self.parent[value] = root
            value = nxt
        return root

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left == right:
            return
        if self.rank[left] < self.rank[right]:
            left, right = right, left
        self.parent[right] = left
        if self.rank[left] == self.rank[right]:
            self.rank[left] += 1


def _rounded_key(point: Point3, precision: float) -> tuple:
    return tuple(round(coordinate / precision) for coordinate in point)


def _bounds_of(points: Sequence[Point3]) -> Bounds6:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    zs = [p[2] for p in points]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def extract_components(
    verts: Sequence[Point3], faces: Sequence[Sequence[int]], *, weld_precision_m: float = 0.0001,
) -> list[dict]:
    """Weld ``verts`` by rounded world position, union faces into connected
    islands, and return one component per island: ``{"bounds", "center",
    "pointCount", "faceCount", "vertexIndices", "faceIndices"}``. Mirrors
    ``validate-black-window-release-gate.mjs``'s ``extractPrimitiveComponents``
    (weld -> disjoint-set over face indices -> per-root AABB), operating on
    ``MeshBuilder``'s own pre-export Python vertex/face lists instead of a
    decoded glTF primitive, so this needs no bpy and no export round-trip.

    ``vertexIndices``/``faceIndices`` are the *original* (pre-weld) indices
    into ``verts``/``faces`` that belong to this component -- not needed for
    the audit itself, but ``vertexIndices`` is required by
    ``remediate_parts`` to translate exactly one component's geometry (a
    seat) without disturbing any other component sharing the same
    material's merged vertex/face lists. ``faceIndices`` is kept for the
    same per-component addressability even though the current remediation
    (seat or brace, never delete or reindex faces) does not need it.
    """
    if not verts:
        return []
    point_by_key: dict[tuple, int] = {}
    unique_points: list[Point3] = []
    original_to_point = [0] * len(verts)
    for index, vertex in enumerate(verts):
        key = _rounded_key(vertex, weld_precision_m)
        point_index = point_by_key.get(key)
        if point_index is None:
            point_index = len(unique_points)
            unique_points.append(vertex)
            point_by_key[key] = point_index
        original_to_point[index] = point_index

    sets = _DisjointSet(len(unique_points))
    face_count_by_root: dict[int, int] = {}
    for face in faces:
        if len(face) < 3:
            continue
        mapped = [original_to_point[i] for i in face]
        for other in mapped[1:]:
            sets.union(mapped[0], other)
        # A quad face is 2 triangles; an n-gon is n-2. Either way this is
        # only used for the mesh front end's own box-ness bookkeeping, not
        # for correctness of the weld/contact test itself.
        root = sets.find(mapped[0])
        face_count_by_root[root] = face_count_by_root.get(root, 0) + max(1, len(face) - 2)

    points_by_root: dict[int, list[Point3]] = {}
    for point_index, point in enumerate(unique_points):
        root = sets.find(point_index)
        points_by_root.setdefault(root, []).append(point)

    vertex_indices_by_root: dict[int, list[int]] = {}
    for original_index in range(len(verts)):
        root = sets.find(original_to_point[original_index])
        vertex_indices_by_root.setdefault(root, []).append(original_index)

    face_indices_by_root: dict[int, list[int]] = {}
    for face_index, face in enumerate(faces):
        if len(face) < 3:
            continue
        root = sets.find(original_to_point[face[0]])
        face_indices_by_root.setdefault(root, []).append(face_index)

    components = []
    for root, points in points_by_root.items():
        bounds = _bounds_of(points)
        components.append({
            "bounds": bounds,
            "center": tuple((bounds[axis] + bounds[axis + 3]) / 2.0 for axis in range(3)),
            "pointCount": len(points),
            "faceCount": face_count_by_root.get(root, 0),
            "vertexIndices": vertex_indices_by_root.get(root, []),
            "faceIndices": face_indices_by_root.get(root, []),
        })
    return components


# ---------------------------------------------------------------------------
# Contact geometry (shared by both front ends).
# ---------------------------------------------------------------------------
def _interval_overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _interval_gap(a0: float, a1: float, b0: float, b1: float) -> float:
    """Positive = separated by this much; negative = overlapping/embedded by
    this much (magnitude); zero = flush."""
    if a0 >= b1:
        return a0 - b1
    if b0 >= a1:
        return b0 - a1
    return -min(a1, b1) + max(a0, b0)


def contact_gap(
    a_bounds: Bounds6, b_bounds: Bounds6, *,
    min_overlap_abs_m: float = 0.05, min_overlap_fraction: float = 0.2,
) -> Optional[dict]:
    """Best face-to-face reading of whether ``b_bounds`` plausibly supports
    ``a_bounds``, or ``None`` if no axis produces a physically meaningful
    2-axis overlap at all (e.g. the boxes only share a corner or an edge).
    See module docstring for the contact model.

    Deliberately asymmetric: on each pair of tangent axes, the required
    overlap is a fraction of ``a_bounds``' *own* extent, not the smaller of
    the two boxes' extents. A symmetric (smaller-of-both) rule looks correct
    for the overwhelmingly common case (a small prop against a large wall)
    but is wrong the other way around -- a 48 m emissive beam that only
    touches a 2 m pillar at one end covers just 4% of its own length, yet a
    smaller-of-both rule sees "2 m overlap on a 2 m candidate" and calls
    that flush support. That was a real, confirmed miss (a A23-round
    catalogue-wide-audit false negative on z06's own layout-shell geometry,
    "long pink emissive slabs fly across the mid-ground with open sky behind
    them"): the beam registered zero orphans under the old symmetric rule
    because one end was genuinely embedded in a narrow tower. Every caller in
    this module passes the potential orphan as ``a_bounds`` and the
    candidate host as ``b_bounds`` (``find_support`` preserves this order),
    so "a fraction of the orphan's own face" is always the effective rule.
    """
    best = None
    for normal_axis in range(3):
        tangents = [axis for axis in range(3) if axis != normal_axis]
        gap = _interval_gap(
            a_bounds[normal_axis], a_bounds[normal_axis + 3],
            b_bounds[normal_axis], b_bounds[normal_axis + 3],
        )
        ok = True
        overlaps = []
        for axis in tangents:
            overlap = _interval_overlap(
                a_bounds[axis], a_bounds[axis + 3], b_bounds[axis], b_bounds[axis + 3],
            )
            reference_extent = a_bounds[axis + 3] - a_bounds[axis]
            required = max(min_overlap_abs_m, min_overlap_fraction * reference_extent)
            overlaps.append(overlap)
            if overlap < required:
                ok = False
        if ok and (best is None or gap < best["gap"]):
            best = {"normalAxis": normal_axis, "gap": gap, "tangentOverlapsM": overlaps}
    return best


def _major_axis_overlap_ok(
    a_bounds: Bounds6, b_bounds: Bounds6, *, elongation_ratio: float, major_axis_min_overlap_fraction: float,
) -> bool:
    """Extra guard for HORIZONTAL beam/strip-shaped objects (see
    ``OrphanAuditConfig``'s ``elongation_ratio`` field for the confirmed
    defect this closes): even after ``contact_gap`` finds a technically-
    valid axis pairing, an elongated ``a_bounds`` must also show real
    overlap along its own longest HORIZONTAL axis specifically. Not needed
    (returns True) for anything that is not clearly elongated -- for a
    roughly cubic object this coincides with ``contact_gap``'s own per-axis
    checks and would only ever agree with them, so there is no behaviour
    change for the common card/box case.

    Deliberately never applies when the LONGEST axis is axis 2 (Blender Z,
    this codebase's fixed vertical axis -- ``runtime_point`` always maps
    runtime height there). Gravity makes vertical elongation a fundamentally
    different shape than horizontal elongation: every real tower, pole,
    spire or antenna is anchored at its base and legitimately extends far
    upward with nothing else touching it along the rest of its height. That
    is normal architecture, not the z06 beam defect (a HORIZONTAL span with
    only one END embedded). Guarding vertical elongation too was a confirmed
    false positive found while re-sweeping the catalogue after this guard
    first shipped: nakaniwa and z04's own landmark builders both place
    slender vertical columns/finials whose entire measured support is a
    small base footprint, correctly touching a wall or the ground -- exactly
    what "anchored at the base" should look like.
    """
    extents = [a_bounds[axis + 3] - a_bounds[axis] for axis in range(3)]
    horizontal_axes = (0, 1)
    major_axis = max(horizontal_axes, key=lambda axis: extents[axis])
    if extents[2] >= extents[major_axis]:
        return True
    other_extents = [extents[axis] for axis in range(3) if axis != major_axis]
    if max(other_extents, default=0.0) <= 1e-9:
        return True
    if extents[major_axis] < elongation_ratio * max(other_extents):
        return True
    overlap = _interval_overlap(
        a_bounds[major_axis], a_bounds[major_axis + 3], b_bounds[major_axis], b_bounds[major_axis + 3],
    )
    return overlap >= major_axis_min_overlap_fraction * extents[major_axis]


def find_support(
    bounds: Bounds6, candidates: Sequence[Mapping[str, object]], *,
    touch_tolerance_m: float = 0.06, min_overlap_abs_m: float = 0.05, min_overlap_fraction: float = 0.2,
    elongation_ratio: float = 6.0, major_axis_min_overlap_fraction: float = 0.25,
) -> dict:
    """Search ``candidates`` (components with a ``"bounds"`` key) for the
    nearest one that puts ``bounds`` in contact. Always returns the closest
    candidate found (by gap) even when it does not clear the tolerance, so
    callers can report "nearest but N m short" rather than only pass/fail.
    """
    supported = False
    best_contact = None
    best_candidate = None
    for candidate in candidates:
        contact = contact_gap(
            bounds, candidate["bounds"],
            min_overlap_abs_m=min_overlap_abs_m, min_overlap_fraction=min_overlap_fraction,
        )
        if contact is None:
            continue
        if not _major_axis_overlap_ok(
            bounds, candidate["bounds"],
            elongation_ratio=elongation_ratio, major_axis_min_overlap_fraction=major_axis_min_overlap_fraction,
        ):
            continue
        if best_contact is None or contact["gap"] < best_contact["gap"]:
            best_contact = contact
            best_candidate = candidate
        if contact["gap"] <= touch_tolerance_m:
            supported = True
    return {"supported": supported, "contact": best_contact, "candidate": best_candidate}


# ---------------------------------------------------------------------------
# Shared audit core.
# ---------------------------------------------------------------------------
def _audit_components(components: Sequence[dict], *, config: OrphanAuditConfig) -> dict:
    orphans = []
    emissive_count = 0
    for index, component in enumerate(components):
        if component["key"] not in config.emissive_keys:
            continue
        emissive_count += 1
        candidates = [
            other for other_index, other in enumerate(components)
            if other_index != index and other["key"] not in config.excluded_parent_keys
        ]
        result = find_support(
            component["bounds"], candidates,
            touch_tolerance_m=config.touch_tolerance_m,
            min_overlap_abs_m=config.min_overlap_abs_m,
            min_overlap_fraction=config.min_overlap_fraction,
            elongation_ratio=config.elongation_ratio,
            major_axis_min_overlap_fraction=config.major_axis_min_overlap_fraction,
        )
        if result["supported"]:
            continue
        bounds = component["bounds"]
        size = tuple(round(bounds[axis + 3] - bounds[axis], 4) for axis in range(3))
        nearest = result["candidate"]
        orphans.append({
            "role": component.get("role"),
            "key": component["key"],
            "center": tuple(round(value, 3) for value in component["center"]),
            "bounds": tuple(round(value, 3) for value in bounds),
            "sizeM": size,
            "nearestNeighborKey": nearest["key"] if nearest else None,
            "nearestNeighborRole": nearest.get("role") if nearest else None,
            "nearestGapM": round(result["contact"]["gap"], 4) if result["contact"] else None,
        })
    return {
        "schema": "hibana.a23.orphan.audit.v1",
        "componentCount": len(components),
        "emissiveComponentCount": emissive_count,
        "orphanCount": len(orphans),
        "orphans": orphans,
    }


# ---------------------------------------------------------------------------
# Mesh front end (build_all_stages.py's MeshBuilder.parts).
# ---------------------------------------------------------------------------
def audit_mesh_parts(
    parts: Mapping[str, Mapping[str, Sequence]], *, config: OrphanAuditConfig = OrphanAuditConfig(),
) -> dict:
    """Audit one ``MeshBuilder`` instance's ``self.parts`` (material key ->
    ``{"verts": [...], "faces": [...]}``) for emissive components with no
    non-emissive component touching them. Needs no bpy: ``parts`` is plain
    Python data already present before ``flush()`` creates any Blender mesh.
    """
    components = []
    for key, data in parts.items():
        for component in extract_components(
            data["verts"], data["faces"], weld_precision_m=config.weld_precision_m,
        ):
            component["key"] = key
            component["role"] = key
            components.append(component)
    return _audit_components(components, config=config)


def assert_no_orphan_emissive(
    parts: Mapping[str, Mapping[str, Sequence]], *, config: OrphanAuditConfig = OrphanAuditConfig(),
    context: str = "",
) -> dict:
    """Build-time assertion: raise if ``audit_mesh_parts`` finds any orphan.
    Intended call site: the end of ``MeshBuilder.flush()``, once per stage
    per LOD, so every one of the ~40 ``add_*`` authoring functions is
    covered by this single hook rather than needing per-call-site
    instrumentation across an 11,000+ line file.
    """
    report = audit_mesh_parts(parts, config=config)
    if report["orphanCount"] > 0:
        prefix = f"{context}: " if context else ""
        raise RuntimeError(
            f"{prefix}{report['orphanCount']} orphan emissive prop(s) with no supporting surface "
            f"within {config.touch_tolerance_m} m (measurementDefect3 class). "
            f"First offender: {report['orphans'][0]}"
        )
    return report


@dataclass(frozen=True)
class RemediationConfig(OrphanAuditConfig):
    # A gap this small is almost always a placement bug against a real,
    # already-built neighbour (e.g. a baked-in ground-embed offset applied to
    # one primitive but not another) rather than a meaningless addition, so
    # it is safe to close automatically. The seat translation only ever
    # moves a component the exact measured gap, onto a candidate that
    # already passed the same 20%/0.05m tangent-overlap requirement the
    # audit itself uses, so it cannot invent a new, worse-looking placement
    # -- it only removes the sky visible behind an already-plausible host.
    max_seat_gap_m: float = 0.5
    # Bracing (see _brace_pylon_bounds) is the fallback for anything too far
    # to seat. Deliberately never deletes or moves the orphan's own geometry:
    # some emissive components reaching this construction rule are
    # add_layout_shell's direct, 1:1 rendering of a TypeScript-authored
    # collision box (choose_box_material's box.get("emissive") path) --
    # deleting or translating that mesh would desync the visual GLB from the
    # still-authoritative, unrelated collision, trading a floating light for
    # an invisible wall or a light that visibly no longer matches where the
    # player collides. Bracing only ever adds new geometry, so it is safe
    # for both collision-tied and purely decorative emissive components.
    pylon_width_m: float = 0.30
    pylon_max_span_m: float = 10.0
    pylon_material_key: str = "trim"
    ground_z: float = 0.0


def _seat_delta(orphan_bounds: Bounds6, candidate_bounds: Bounds6, axis: int, gap: float) -> float:
    """Signed translation along ``axis`` that closes ``gap`` by moving the
    orphan onto the candidate (candidate is assumed stationary)."""
    orphan_hi = orphan_bounds[axis + 3]
    candidate_lo = candidate_bounds[axis]
    if orphan_hi <= candidate_lo:
        return gap
    return -gap


def _brace_pylon_bounds(
    bounds: Bounds6, *, pylon_width_m: float = 0.30, max_span_per_pylon_m: float = 10.0, ground_z: float = 0.0,
) -> list:
    """One continuous vertical support from grade (this codebase's universal
    ground plane -- ``build_all_stages.py``'s own floor spans Blender Z 0
    down to -0.18) up to ``bounds``' own bottom face, running the *entire*
    length of ``bounds``' longer horizontal axis (a real support wall/fin,
    not a row of independent posts).

    This must be a single continuous piece rather than several narrower
    posts spread along the span: this same module's own asymmetric overlap
    rule (``contact_gap``) and major-axis guard (``_major_axis_overlap_ok``)
    require a candidate to cover a real fraction of the orphan's *own*
    extent, precisely to reject the confirmed z06 defect where a beam
    "touching" a candidate at only one narrow end registered as supported.
    A brace must clear that same bar to prove it actually fixed the orphan
    (``remediate_parts`` re-audits after remediation) -- several independent
    narrow posts, each covering only a fraction of the span, would each fail
    that bar individually exactly the way the original narrow pillar did.
    Purely additive: never reads or changes ``bounds`` itself.

    Returns an empty list when ``bounds`` is already at/near grade (nothing
    to bridge -- if this happens for a genuine orphan, the ground plane
    itself should normally have already supplied contact, so an empty
    result here signals a case worth a human look rather than one this rule
    can safely paper over). ``max_span_per_pylon_m`` is accepted for config
    compatibility but unused by the single-fin design.
    """
    del max_span_per_pylon_m
    x0, y0, z0, x1, y1, z1 = bounds
    if z0 <= ground_z + 0.06:
        return []
    extent_x, extent_y = x1 - x0, y1 - y0
    if extent_x >= extent_y:
        width_y = max(pylon_width_m, extent_y * 0.6)
        center_y = (y0 + y1) / 2.0
        pylon = (x0, center_y - width_y / 2.0, ground_z, x1, center_y + width_y / 2.0, z0)
    else:
        width_x = max(pylon_width_m, extent_x * 0.6)
        center_x = (x0 + x1) / 2.0
        pylon = (center_x - width_x / 2.0, y0, ground_z, center_x + width_x / 2.0, y1, z0)
    return [pylon]


def _box_verts_faces_at(bounds: Bounds6, base_index: int) -> tuple:
    """The same 8-vertex / 6-quad-face box topology
    ``MeshBuilder.add_box_blender`` emits, generated directly in the target
    coordinate space (already Blender-space at this point in the pipeline,
    so no runtime_point conversion is needed)."""
    x0, y0, z0, x1, y1, z1 = bounds
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (base_index + 0, base_index + 3, base_index + 2, base_index + 1),
        (base_index + 4, base_index + 5, base_index + 6, base_index + 7),
        (base_index + 0, base_index + 1, base_index + 5, base_index + 4),
        (base_index + 1, base_index + 2, base_index + 6, base_index + 5),
        (base_index + 2, base_index + 3, base_index + 7, base_index + 6),
        (base_index + 3, base_index + 0, base_index + 4, base_index + 7),
    ]
    return verts, faces


def remediate_parts(
    parts: Mapping[str, Mapping[str, Sequence]], *, config: RemediationConfig = RemediationConfig(),
) -> tuple[dict, dict]:
    """The generator-side construction rule for the orphan-emissive defect
    class (the mesh-front-end sibling of ``_sanitize_facade_key``, which
    already performs the equivalent construction-time fix-up for the dark-
    card defect in ``MeshBuilder``): every emissive component is checked for
    a supporting neighbour exactly as ``audit_mesh_parts`` does, and:

      - if unsupported but a plausible host sits within ``max_seat_gap_m``,
        the component is translated along the measured contact axis by
        exactly the measured gap so it becomes flush (zero-gap) against that
        host -- "seat each card against a real surface with measured
        zero-gap contact";
      - otherwise, vertical support pylons are added from grade up to the
        component's own bottom face (see ``_brace_pylon_bounds``) -- a real,
        measured, zero-gap surface built specifically to hold it up, rather
        than deleting or moving geometry this function cannot prove is safe
        to touch (see ``RemediationConfig.pylon_width_m``'s docstring on the
        add_layout_shell/collision-authoritative case this must not delete).

    Returns ``(new_parts, report)``; ``parts`` itself is never mutated.
    Intended call site: the start of ``MeshBuilder.flush()``, before any bpy
    mesh is created, so the shipped GLB never contains an orphan in the
    first place (the subsequent ``assert_no_orphan_emissive`` call is then a
    self-consistency trap, not the primary fix).
    """
    parts_components: dict[str, list[dict]] = {}
    for key, data in parts.items():
        components = extract_components(data["verts"], data["faces"], weld_precision_m=config.weld_precision_m)
        for component in components:
            component["key"] = key
        parts_components[key] = components

    all_components = [component for components in parts_components.values() for component in components]

    seated: list[dict] = []
    braced: list[dict] = []
    seat_delta_by_key: dict[str, dict[int, tuple[int, float]]] = {}
    new_pylon_bounds: list[Bounds6] = []

    for key, components in parts_components.items():
        if key not in config.emissive_keys:
            continue
        for component in components:
            candidates = [
                other for other in all_components
                if other is not component and other["key"] not in config.excluded_parent_keys
            ]
            result = find_support(
                component["bounds"], candidates,
                touch_tolerance_m=config.touch_tolerance_m,
                min_overlap_abs_m=config.min_overlap_abs_m,
                min_overlap_fraction=config.min_overlap_fraction,
                elongation_ratio=config.elongation_ratio,
                major_axis_min_overlap_fraction=config.major_axis_min_overlap_fraction,
            )
            if result["supported"]:
                continue
            bounds = component["bounds"]
            size = tuple(round(bounds[axis + 3] - bounds[axis], 4) for axis in range(3))
            contact = result["contact"]
            candidate = result["candidate"]
            record = {
                "key": key,
                "bounds": tuple(round(value, 3) for value in bounds),
                "sizeM": size,
                "nearestNeighborKey": candidate["key"] if candidate else None,
                "nearestGapM": round(contact["gap"], 4) if contact else None,
            }
            if contact is not None and 0.0 <= contact["gap"] <= config.max_seat_gap_m:
                axis = contact["normalAxis"]
                delta = _seat_delta(bounds, candidate["bounds"], axis, contact["gap"])
                seat_delta_by_key.setdefault(key, {})
                for vertex_index in component["vertexIndices"]:
                    seat_delta_by_key[key][vertex_index] = (axis, delta)
                record["seatedAxis"] = axis
                record["seatedDeltaM"] = round(delta, 4)
                seated.append(record)
            else:
                pylons = _brace_pylon_bounds(
                    bounds, pylon_width_m=config.pylon_width_m,
                    max_span_per_pylon_m=config.pylon_max_span_m, ground_z=config.ground_z,
                )
                record["bracePylonCount"] = len(pylons)
                new_pylon_bounds.extend(pylons)
                braced.append(record)

    new_parts: dict = {}
    for key, data in parts.items():
        deltas = seat_delta_by_key.get(key)
        if not deltas:
            new_parts[key] = data
            continue
        new_verts = []
        for vertex in data["verts"]:
            new_verts.append(vertex)
        for original_index, (axis, delta) in deltas.items():
            vertex = new_verts[original_index]
            new_verts[original_index] = tuple(
                (coordinate + delta) if component_axis == axis else coordinate
                for component_axis, coordinate in enumerate(vertex)
            )
        new_parts[key] = {"verts": new_verts, "faces": list(data["faces"])}

    if new_pylon_bounds:
        pylon_key = config.pylon_material_key
        existing = new_parts.get(pylon_key) or parts.get(pylon_key) or {"verts": [], "faces": []}
        pylon_verts = list(existing["verts"])
        pylon_faces = list(existing["faces"])
        for pylon_bounds in new_pylon_bounds:
            base_index = len(pylon_verts)
            verts, faces = _box_verts_faces_at(pylon_bounds, base_index)
            pylon_verts.extend(verts)
            pylon_faces.extend(faces)
        new_parts[pylon_key] = {"verts": pylon_verts, "faces": pylon_faces}

    return new_parts, {
        "schema": "hibana.a23.orphan.remediation.v1",
        "seatedCount": len(seated),
        "bracedCount": len(braced),
        "bracePylonCount": len(new_pylon_bounds),
        "seated": seated,
        "braced": braced,
    }


# ---------------------------------------------------------------------------
# Spec front end (SpecKit-conforming stage kits, e.g. a23_bridge's
# district-infill planner and nakaniwa's own kit).
# ---------------------------------------------------------------------------
def audit_specs(
    specs: Sequence[Mapping[str, object]], *, kit, config: OrphanAuditConfig = OrphanAuditConfig(),
) -> dict:
    """Audit a spec list (``kit.SpecKit``-shaped: each spec has ``"material"``
    and is understood by ``kit.spec_bounds``) with no mesh export required at
    all — usable from a pure dry-run (``a23_bridge.plan_district_infill``)
    before a single triangle reaches Blender.
    """
    components = []
    for spec in specs:
        bounds = kit.spec_bounds(spec)
        components.append({
            "bounds": bounds,
            "center": tuple((bounds[axis] + bounds[axis + 3]) / 2.0 for axis in range(3)),
            "key": str(spec["material"]),
            "role": str(spec.get("role", spec["material"])),
        })
    return _audit_components(components, config=config)
