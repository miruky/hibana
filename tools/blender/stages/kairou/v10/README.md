# Kairou V10.1 reproducible candidate pipeline

This directory contains every authored input required to rebuild Kairou's
private release candidate. It does not read source assets from `/private/tmp`
and never writes to `public/`.

The collision skeleton is regenerated from
`tools/blender/generated/stage-layouts.json`. The three `source/*.raw.glb`
files contain only the vetted, overhead landmark components from the earlier
V10 art pass. The six `textures/*.png` files are the project-original PBR
source atlases. Their hashes and release thresholds are pinned in
`asset-contract.json`.

Run the complete candidate build with:

```bash
python3 tools/blender/stages/kairou/v10/build_v10_1.py --render
```

Outputs stay below the ignored `tools/blender/work/kairou-v10.1/` directory.
Article and collision proof images stay below the ignored
`tools/blender/screenshots/077-kairou-v10-repo-integration/` directory. Neither
directory may be committed.

The pipeline regenerates the collision-backed shell, applies PBR textures,
verifies material-only geometry identity, combines safe upper landmark art,
authors the collision-contained surface pass, audits all three player routes,
renders the fixed eight-view visual set, then optionally creates optimized
release candidates. A successful technical build is not permission to publish:
the fixed-view visual score must independently reach 8.0/10.

`src/game/stage.ts` and `src/game/stages.ts` remain authoritative for gameplay
collision, spawns and routes. The GLBs produced here are visuals only.
