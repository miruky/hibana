# Kouwan R10 reproducibility status

Kouwan R10 is a private visual candidate. It must not be copied to `public/`
or added to the runtime manifest yet.

The R10 wrappers now use `HIBANA_KOUWAN_R10_ROOT` and default to the ignored
`tools/blender/work/kouwan-r10/` directory. They no longer bind the candidate
to one machine's temporary directory. This does not make the build repository
self-contained: R10 is an incremental pass on an untracked R9.5 Blender scene,
and its optimizer and release audit execute untracked inherited scripts.

Run the fail-closed audit with:

```bash
python3 tools/blender/stages/kouwan/r10/audit_reproducibility.py
```

To inspect the known private artifact set without changing it:

```bash
export HIBANA_KOUWAN_R10_ROOT=/path/to/kouwan-current-v5
python3 tools/blender/stages/kouwan/r10/audit_reproducibility.py \
  --artifact-root "$HIBANA_KOUWAN_R10_ROOT" \
  --require-known-outputs
```

`reproduction-contract.json` pins the expected hashes. A valid supplied
artifact set is still not `integrationReady`; the repository must first gain
a deterministic way to regenerate the R9.5 baseline, its PBR sources, the
optimizer, and the release audit from tracked inputs. The optimized GLBs are
byte-stable across relocated roots; the `.blend` is not because it records
artifact paths.

Two QA semantics also remain blockers. `finalize_r10.py` embeds the five human
scores rather than reading an independently reviewed scorecard, and it does
not require the full five-view diagnostic to be clean. The known aerial view
is flagged by that diagnostic, so a private `SHIP` record is not authorization
for browser or public integration.

The standalone GLBs also fail the repository's shared `validate-glb.py` gate:
their root extras do not carry the current central `hibanaGeneratorVersion`
and `hibanaGeneratorSha`. Do not stamp those values onto a separately authored
asset merely to silence the gate; integration needs an explicit, truthful
provenance migration.

Once those inputs exist in the repository, the historical R10 execution order
is the following. Run it from the repository root; `HIBANA_KOUWAN_R10_ROOT`
must be either an external scratch directory or a descendant of the ignored
`tools/blender/work/` directory.

```bash
export HIBANA_KOUWAN_R10_ROOT=/path/to/kouwan-r10-work
export HIBANA_KOUWAN_R10_OPTIMIZER_BASE="$HIBANA_KOUWAN_R10_ROOT/optimize_export_r7_2.py"
export HIBANA_KOUWAN_R10_RELEASE_AUDIT_BASE="$HIBANA_KOUWAN_R10_ROOT/optimized-r7-2/audit_release_r7_2.py"
KOUWAN_R10_SCRIPTS="$PWD/tools/blender/stages/kouwan/r10"
BLENDER_BIN=/Applications/Blender.app/Contents/MacOS/Blender

"$BLENDER_BIN" --background \
  "$HIBANA_KOUWAN_R10_ROOT/kouwan-current-v5-r9-5.blend" \
  --python "$KOUWAN_R10_SCRIPTS/polish_r10.py"
"$BLENDER_BIN" --background \
  "$HIBANA_KOUWAN_R10_ROOT/kouwan-current-v5-r10.blend" \
  --python "$KOUWAN_R10_SCRIPTS/audit_r10_contacts.py"
"$BLENDER_BIN" --background \
  "$HIBANA_KOUWAN_R10_ROOT/kouwan-current-v5-r10.blend" \
  --python "$KOUWAN_R10_SCRIPTS/optimize_export_r10.py"
node "$KOUWAN_R10_SCRIPTS/postprocess_r10.mjs"
python3 "$KOUWAN_R10_SCRIPTS/audit_release_r10.py"
node "$KOUWAN_R10_SCRIPTS/validate_khronos_r10.mjs" \
  "$HIBANA_KOUWAN_R10_ROOT/optimized-r10/stages/kouwan-r10-lod0.glb" \
  "$HIBANA_KOUWAN_R10_ROOT/optimized-r10/stages/kouwan-r10-lod1.glb" \
  "$HIBANA_KOUWAN_R10_ROOT/optimized-r10/stages/kouwan-r10-lod2.glb"
"$BLENDER_BIN" --background --factory-startup \
  --python "$KOUWAN_R10_SCRIPTS/render_lod_audit.py"
```

Then:

1. Open the pinned R9.5 `.blend` and run `polish_r10.py`.
2. Run `audit_r10_contacts.py` on the resulting R10 `.blend`.
3. Run `optimize_export_r10.py` on that `.blend`.
4. Run `postprocess_r10.mjs` from the repository root.
5. Run `audit_release_r10.py` and `validate_khronos_r10.mjs`.
6. Run `render_lod_audit.py`, then the shared render-set audits:

   ```bash
   python3 tools/blender/audit_blender_render_set.py \
     --render-dir "$HIBANA_KOUWAN_R10_ROOT/render-pre-gate-eye" \
     --output "$HIBANA_KOUWAN_R10_ROOT/kouwan-r10-eye-render-set-audit.json" \
     --expect-count 4 --minimum-eye-height-views 4
   python3 tools/blender/audit_blender_render_set.py \
     --render-dir "$HIBANA_KOUWAN_R10_ROOT/renders/final-v5-r10" \
     --output "$HIBANA_KOUWAN_R10_ROOT/kouwan-r10-render-set-audit.json" \
     --expect-count 5 --minimum-eye-height-views 0
   ```

7. Run `finalize_r10.py` on the R10 `.blend`:

   ```bash
   "$BLENDER_BIN" --background \
     "$HIBANA_KOUWAN_R10_ROOT/kouwan-current-v5-r10.blend" \
     --python "$KOUWAN_R10_SCRIPTS/finalize_r10.py"
   ```

All Blender Python must be executed by absolute `script_path`, with Blender
MCP on localhost, safe mode enabled, and inline Python disabled.
