# Stage-world canonical catalog and placement audit

Hibana's 31-stage environment contract now has a checked-in, deterministic
catalog and an all-stage placement audit. This integration is deliberately
**audit-only**: no runtime file imports either generated TypeScript module, and
the existing procedural fail-open path remains unchanged.

## Canonical ownership

`tools/blender/stage-world.catalog.json` is the proposed authored source for:

- the fixed 31 stage IDs;
- exactly two stage-exclusive mega-landmarks per stage (62 unique IDs);
- collision footprints kept separate from larger visual envelopes;
- stage-specific concept, silhouette, facade, roof, entrance, non-glass-window,
  and LOD-preservation grammars;
- the explicit `renshujo` 236 m recommendation and 200 m exception gate.

When a legacy label or generic generated style conflicts with a landmark's
`geometryGrammar.conceptPriority`, the canonical concept priority wins. Raster
horizons and LOD2 window cards remain prohibited by the catalog contract.

The normalized catalog SHA-256 is:

```text
b8bb0fc5ef3ab0399c8137b34a63c118c7a219eb8fe4af059ccc30b914dacf3f
```

The normalization removes only the top-level `catalogSha256`, recursively sorts
object keys, preserves array order, serializes without insignificant whitespace,
and hashes the UTF-8 bytes. Generated TypeScript, Blender JSON, every Blender
stage record, and the manifest embed this same SHA.

## Placement audit

`tools/blender/stage-placement-solver.mjs` reads the canonical catalog, exported
stage layouts, and the checked-in mode-coordinate sources. It deterministically
produces an adoption proposal and independent evidence; it does not change
runtime construction or add a runtime import.

The current audited result is:

| Gate | Result |
| --- | ---: |
| Stages | 31 / 31 PASS |
| Landmarks | 62 / 62 validated and unique |
| Landmarks per stage | exactly 2 |
| Existing ordinary districts | 315 / 315 retained |
| Proof-stage collision differences | 0 across 7 stages / 14 landmarks |
| Proof-stage semantic fields | 0 differences across 6 fields |
| Independent spawn / route mode audit | 31 / 31 PASS; 0 failure codes |
| All-mode objective audit | 31 / 31 PASS; 0 violations |
| Fixed objective reservations | 294 |
| Flexible zombie-shop groups | 203 |
| Migration heuristic tags | 0 |
| `renshujo` recommended 236 m plan | PASS |
| `renshujo` compact 200 m plan | NO-SHIP, with no fabricated coordinates |

The solver SHA-256 is:

```text
5f1ffefdd21506e884fd0d5efb401cfe5a1a68e00228c706d2b083268a345361
```

The proposal reserves 16 m primary roads, 12 m capsule clearance, 12 m landmark
approaches of at least 20 m, 30 m player-spawn clearance, 8 m bot-spawn
clearance, 20 m opposing-team anchor separation, and a preferred 60–120 m FFA
anchor band. It also audits all eight S&D formation rounds, zombie ring
candidates, one reachable navigation component, grounded collision-backed combat
spaces, and first-spawn landmark visibility. Existing ordinary districts retain
their kind, dimensions, measured height evidence, and count; only a future gated
migration may adopt the proposed placement.

Mode reservations are derived from the checked-in formulas for Domination,
Hardpoint, S&D, campaign anchors, zombie-shop candidates, and the complete
training-target sample. CTF is not wired into the current runtime mode list; the
report labels its Domination A/C reservation as a forward projection, not as
runtime coverage.

## Generated files

Do not edit generated outputs by hand.

- `src/game/generated/stage-landmarks.generated.ts`
- `src/game/generated/stage-placements.generated.ts`
- `tools/blender/generated/stage-world.blender.generated.json`
- `tools/blender/generated/stage-world.manifest-sha.json`
- `tools/blender/generated/representative7-semantic-diff.json`
- `tools/blender/generated/stage-placement-audit.json`
- `tools/blender/generated/stage-placement.manifest.json`
- `tools/blender/generated/proof7-breaking-diff.json`
- `tools/blender/generated/all-mode-objective-audit.json`
- `tools/blender/generated/mode-spawn-route-audit.json`

## Reproduce and detect drift

Run from the repository root:

```bash
node tools/blender/codegen-stage-world.mjs --check
node tools/blender/compare-stage-world-proof7.mjs
node tools/blender/stage-placement-solver.mjs --check
./node_modules/.bin/tsx tools/blender/audit-stage-placement-modes.ts --check
node --test \
  tools/blender/tests/stage-world-catalog.test.mjs \
  tools/blender/tests/stage-placement-solver.test.mjs

./node_modules/.bin/tsc --noEmit \
  --target ES2022 \
  --module ESNext \
  --moduleResolution Bundler \
  --skipLibCheck \
  src/game/generated/stage-landmarks.generated.ts \
  src/game/generated/stage-placements.generated.ts
```

The test suite validates cardinality, uniqueness, schema-critical rules,
canonical/profile joins, byte-deterministic code generation, embedded SHA
equality, live hashes for every coordinate-bearing source, road and approach
clearance, player and bot spawn clearance, all-mode objectives, S&D formations,
navigation, visibility, occupancy, grounding, proof7 compatibility, and the
honest compact-map rejection. The TS mode audit imports only repository sources
and therefore reproduces its report without an external workspace.

To intentionally edit the catalog, change only
`tools/blender/stage-world.catalog.json`, then run:

```bash
node tools/blender/codegen-stage-world.mjs --stamp
node tools/blender/codegen-stage-world.mjs
node tools/blender/compare-stage-world-proof7.mjs
node tools/blender/stage-placement-solver.mjs
./node_modules/.bin/tsx tools/blender/audit-stage-placement-modes.ts
```

Any semantic change produces a new catalog SHA. Any change to the current stage
layout or TypeScript sources produces a placement-source hash mismatch until the
solver is reviewed and regenerated.

## Adoption boundary

Passing this audit proves the 2D collision, spawn, navigation, visibility, and
identity proposal is internally consistent. It does not approve Blender visuals,
GLB provenance, browser traversal, or performance. The earlier full structural
adapter experiment remains isolated evidence rather than a checked-in runtime-v2
contract. In particular, the checked-in `renshujo` definition is still 200 m,
while the proposal honestly requires 236 m; this audit does not silently mutate
that definition. Runtime adoption must remain feature-gated stage by stage and
requires Blender bounds and catalog-SHA checks, muted background browser
captures, real performance metrics, and preserved procedural rollback before
deployment.

## Reference-match visual gate

Every Blender candidate first passes `tools/blender/audit_blender_render_set.py`.
This technical pre-gate requires eight unique views, at least four explicitly
named 1.65 m eye-height views, and rejects blank, near-uniform, heavily clipped,
crushed, or probable inside-wall camera frames. It is a camera/completeness
gate only and never substitutes for the human reference review below.

```bash
python3 tools/blender/audit_blender_render_set.py \
  --render-dir "$HIBANA_AUDIT_ROOT/stage-renders/kairou" \
  --output "$HIBANA_AUDIT_ROOT/kairou-render-set.json"

python3 -m unittest tools.blender.test_audit_blender_render_set
```

`tools/blender/audit_stage_reference_match.py` compares an approved 1.65 m
first-person render with the private ImageGen modeling reference. Edge density,
middle-band structure, tonal range, dark/highlight clipping, entropy, and coarse
palette occupancy are diagnostic signals only. They can reject an empty or
crushed blockout, but they cannot approve art quality.

A release therefore also needs a hash-bound human scorecard for every stage.
All ten categories must score at least 7/10, the mean must be at least 8/10, and
the reviewer verdict must be `SHIP`. Missing or stale scorecards always fail.
Concepts, comparison renders, scorecards, and article evidence remain under
Git-ignored paths and must never be pushed.

```bash
HIBANA_AUDIT_ROOT=tools/blender/screenshots/release-audit
python3 tools/blender/audit_stage_reference_match.py \
  --reference-dir tools/blender/concepts \
  --render-dir "$HIBANA_AUDIT_ROOT/stage-release-renders" \
  --scorecard-dir "$HIBANA_AUDIT_ROOT/stage-scorecards" \
  --output "$HIBANA_AUDIT_ROOT/stage-reference-audit.json"

python3 -m unittest tools.blender.test_audit_stage_reference_match
```

The separate geometry/material gate for the repeated black-window defect is:

```bash
HIBANA_AUDIT_ROOT=tools/blender/screenshots/release-audit
node tools/blender/validate-black-window-release-gate.mjs \
  --assets-dir public/assets/aaa/stages \
  --manifest public/assets/aaa/manifest.json \
  --generator tools/blender/build_all_stages.py \
  --report "$HIBANA_AUDIT_ROOT/black-window-release.json"

node --test tools/blender/tests/black-window-release-gate.test.mjs
```

It distinguishes the visual defect from stale generator provenance and rejects
thin dark cards, floating/embedded/near-coplanar panes, long identical opening
runs, excessively dark glass, and any LOD2 facade-window cards. Legitimate deep
entrances, interior back walls, vehicle glass, and observatory domes require an
explicit semantic role instead of bypassing the audit by shape alone.

Generated PBR files must also pass an encoded-pixel signal check before any
look-development render is reviewed:

```bash
python3 tools/blender/validate_texture_signal.py path/to/texture-directory \
  --report path/to/texture-signal-audit.json
python3 -m unittest tools.blender.test_validate_texture_signal
```

This catches a Blender-specific silent failure where `Image.pixels.foreach_set`
is followed by a save without `Image.update()`: the PNG exists and loads, but
its encoded pixels can be entirely black. The gate checks base colour tonal
signal, tangent-normal blue baseline, and the glTF ORM roughness channel.

## Canonical Blender authoring layout

The live game keeps an empty placement release allow-list until each stage has
passed visual, collision, mode and real-browser QA. Blender authoring still
needs to build against all 62 solver-v2 landmarks instead of the legacy layout,
so export a separate, explicit candidate file:

```bash
npx tsx tools/blender/export-stage-layouts.ts \
  --canonical-placements \
  --output /private/tmp/hibana-blender/stage-layouts.canonical.json
node tools/blender/validate-canonical-stage-layouts.mjs \
  /private/tmp/hibana-blender/stage-layouts.canonical.json \
  /private/tmp/hibana-blender/stage-layouts.canonical.audit.json
```

Pass that file to `build_all_stages.py` as MCP argument `layout_path`. This
route is authoring-only and cannot silently enable a live stage. It also makes
the audited `renshujo` 200 m → 236 m candidate explicit while preserving the
live 200 m definition until its release gate passes.
