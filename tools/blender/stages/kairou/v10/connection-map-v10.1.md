# Kairou V10.1 collision-aligned connection map

This connection map is the geometry contract for promoting the approved V10
art language onto Hibana's current Kairou runtime layout. `stage.ts` and the
legacy-release Kairou `BoxSpec` export remain authoritative.

## Contact skeleton

- Base: a fresh isolated Kairou export from `tools/blender/build_all_stages.py`.
- Player-contact geometry, transforms, hierarchy and node extras are immutable
  during the PBR pass.
- The two landmark footprints are fixed at:
  - Meridian sanctuary: centre `(-66, 46)`, `114 x 74 m`.
  - Windcrown observatory: centre `(56, 46)`, `88 x 80 m`.
- Protected routes are the two 12 m landmark approaches and the central
  north/south boulevard. Their unsupported blocker count must remain zero.

## V10 upper-art transfer

The original integrated V10 used an obsolete local frame. Only its named hero
landmark meshes are eligible; its district/contact mesh is rejected.

| Group | Runtime translation XYZ | Minimum retained height | Support rule |
| --- | ---: | ---: | --- |
| Meridian sanctuary | `(-11.5, 0, 79.665)` | `7.0 m` | Upper silhouette must overlap the current landmark roof/column envelope. |
| Windcrown observatory | `(-11.5, 0, 83.18)` | `7.0 m` | Upper silhouette must overlap the current fortress roof/upper-wall envelope. |

Triangles touching a vertex below the minimum height are removed. This leaves
the current collision-aligned lower architecture wholly responsible for player
contact. The transferred meshes may not add district walls, low props, water,
foliage, picture horizons, or player-height cover.

LOD1 uses the approved V10 LOD2 hero topology. LOD2 uses the same source with a
measured collapse reduction, while preserving both landmark silhouettes.

## Release gates

- Supported collision-significant area: at least `99.8%` (target `100%`).
- Unsupported player-height samples: `0`.
- Unsupported samples in all three protected routes: `0`.
- Upper transfer minimum height: at least `7.0 m` before LOD processing.
- Kairou dark facade cards: `0` at all LODs.
- Eight-view render set: exactly 8 frames, at least 6 at `1.65 m` eye height,
  no blank/duplicate/inside-wall frame.
- Public GLBs and manifest remain untouched until every gate passes.

