# Black-window release gate

`validate-black-window-release-gate.mjs` is an independent post-export audit for
the repeated black facade-card defect. It reads the final compressed GLBs, welds
normal/UV-split vertices by world position, reconstructs connected components,
and classifies thin vertical card geometry from its oriented bounds.

Run the complete 31-stage / three-LOD gate with:

```sh
node tools/blender/validate-black-window-release-gate.mjs \
  --report /private/tmp/hibana-black-window-release.json
```

Run a focused iteration with one or more `--stage` arguments:

```sh
node tools/blender/validate-black-window-release-gate.mjs \
  --stage kairou --stage kunren
```

The JSON has three independent decisions:

- `visualGateOk`: facade-card, pane placement, repetition, material, LOD, and
  31 x 3 coverage checks;
- `provenanceOk`: manifest/node generator SHA checks;
- `releaseOk`: both decisions pass.

This separation is intentional. A stale generator SHA must not hide black-window
counts, and a current SHA must not make broken geometry acceptable.

## Export metadata contract

Merged meshes lose the distinction between facade panes, vehicle glazing,
interior walls, and observatory glass. Each independent `MeshBuilder` scope must
write the following values on one exported owner node:

- `hibanaFacadeAuditVersion = "black-window-v1"`
- `hibanaFacadeGlassPaneCount`
- `hibanaFacadeGlassMaxEqualSizeRepeat`
- `hibanaFacadeGlassMinWallClearanceM`
- `hibanaFacadeGlassMaxWallClearanceM`
- `hibanaFacadeGlassMinFrameRecessM`
- `hibanaFacadeGlassNearCoplanarCount`
- `hibanaFacadeGlassFloatingCount`
- `hibanaFacadeGlassEmbeddedCount`
- `hibanaFacadeDarkCardCount`

The maximum-clearance and explicit floating/embedded values are required. A
minimum clearance alone can detect coplanar/embedded placement but cannot prove
that a different pane is floating away from its wall.

Unmerged semantic nodes may additionally use `hibanaFacadeAuditRole` with one
of these controlled values:

- `facade-pane`
- `facade-support`
- `deep-entrance`
- `interior-wall` (also requires `hibanaInteriorZone = true`)
- `observatory-dome`
- `vehicle-glass`
- `decorative-glass`

An exemption name alone is insufficient. Dimensions and topology must match its
role; for example, a small box-shaped card named `observatory-dome` still fails.

## Release limits

| Check                       | LOD0 | LOD1 | LOD2 |
| --------------------------- | ---: | ---: | ---: |
| authored facade panes       |  120 |   48 |    0 |
| shallow facade cards        |   96 |   32 |    0 |
| Kairou shallow facade cards |    0 |    0 |    0 |

Additional blockers:

- more than 16 equal-size facade panes;
- wall clearance below 8 mm;
- wall clearance above 60 mm;
- frame recess below 80 mm;
- any reported floating or embedded pane;
- opaque glass with linear luminance below 0.055;
- missing aggregate metadata on a merged asset;
- any LOD2 facade window card.

Tests use actual in-memory GLB geometry rather than counter-only fixtures:

```sh
node --test tools/blender/tests/black-window-release-gate.test.mjs
```
