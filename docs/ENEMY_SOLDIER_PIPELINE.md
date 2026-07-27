# Hibana enemy-soldier Blender pipeline

## Source and licensing policy

The two user-provided enemy GLBs and PNGs are observation references only. Their
redistribution license is unknown, so Hibana does not import, copy, embed, or ship
their meshes, textures, materials, or binary data. The release pack is generated
from original deterministic Blender geometry in
`tools/blender/build_enemy_soldiers.py`.

## Reference analysis

**Target:** browser FPS standard NPC, visible at close and mid combat range
**Match goal:** preserve believable military proportions, layered kit, and rifle
handling while replacing the unusable source topology and static pose.

### Visual reference

- Both PNGs are 848 × 1264 front three-quarter/full-body studies on white.
- The primary reference reads as a modern 1.78–1.84 m operator: ballistic helmet,
  face covering, plate carrier, MOLLE pouches, radio, backpack, knee protection,
  gloves, boots, and a shouldered magazine-fed rifle.
- The second reference contributes a lighter irregular-force silhouette: scarf,
  soft headgear, simpler chest rig, woodland trousers, utility pouches, and a
  wood-furnished rifle. It is used only for role variety, not copied literally.
- Shape hierarchy is head protection → shoulder/vest mass → crossed rifle/arms →
  cargo trouser silhouette → compact boot contact.
- Camera feel is a 55–85 mm portrait lens, slightly above pelvis height, with low
  perspective distortion and soft frontal fill.
- Material response is deliberately subdued: matte woven fabric (roughness
  0.68–0.88), polymer/painted armor (0.42–0.62), rubber (0.78+), worn weapon metal
  (metallic 0.7, roughness 0.34), and restrained lens highlights.

### Reference palette

| Role           | Hex       | Use                                          |
| -------------- | --------- | -------------------------------------------- |
| charcoal cloth | `#343D3B` | urban rifleman base                          |
| muted slate    | `#4A5551` | digital-camo secondary                       |
| woodland olive | `#566040` | scout/support base                           |
| sand fabric    | `#8A795A` | marksman secondary                           |
| armor          | `#252C29` | common plate/helmet family                   |
| gear           | `#31362F` | webbing, pouches, backpack                   |
| rubber         | `#101719` | balaclava and recessed smoked eye protection |
| medic accent   | `#A52D2D` | compact identification only                  |

## Input GLB measurement

| Metric               |      Enemy 1 |      Enemy 2 |
| -------------------- | -----------: | -----------: |
| File size            | 34,461,592 B | 23,054,836 B |
| Meshes / primitives  |        1 / 1 |        1 / 1 |
| Vertices             |      480,403 |      258,700 |
| Triangles            |      835,738 |      446,355 |
| Materials / textures |        1 / 3 |        1 / 3 |
| Skins / joints       |        0 / 0 |        0 / 0 |
| Animations           |            0 |            0 |
| Measured height      |      1.899 m |      1.898 m |

These are static presentation meshes, not repairable animated game characters.
Their lack of a skin and skeleton explains why joint motion cannot be corrected in
place. Their triangle counts are also unsuitable for repeated WebGL enemies.

## Production brief

- **Type:** original rigged third-person character pack
- **Target:** Hibana WebGL FPS
- **Scale:** 1 Blender unit = 1 metre; 1.80 m authored skeleton
- **Forward:** Blender `+Y`, exported glTF `-Z`
- **Export:** binary glTF 2.0 (`.glb`) with Meshopt delivery compression
- **LOD0 budget:** ≤90k triangles for all six variants in one loaded pack
- **Material budget:** eight authored material slots (seven retained after unused
  skin-slot pruning) and one 4 × 2 POT fabric atlas
- **Rig budget:** 22 deform joints, one common bone hierarchy
- **Animation:** 30 fps, sampled glTF clips

The exporter follows Blender's official [glTF 2.0 animation and skinning workflow](https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html): named actions become independent clips, pose-bone transforms are sampled, deformation bones are exported, and vertex influence count stays within the broadly interoperable four-joint limit. Delivery decisions also follow the Khronos [Asset Creation Guidelines 2.0](https://www.khronos.org/blog/introducing-asset-creation-guidelines-2.0-siggraph-2025) principles for real-world units, stable origins, shared/instanced content, GPU-ready triangles, animation efficiency, and Meshopt compression.

## Six variants

1. `rifleman` — urban digital camouflage, standard plate carrier and rifle.
2. `breacher` — dark heavy protection, full visor and short breaching weapon.
3. `scout` — woodland pattern, hood/scarf, light rig and carbine.
4. `marksman` — sand pattern, boonie silhouette and scoped long rifle.
5. `support` — heavy carrier, ammunition backpack and supported automatic weapon.
6. `medic` — muted field uniform, medical backpack/helmet identifiers and carbine.

All six authored skinned-mesh assets target the same named 22-joint hierarchy.
Because each asset uses several material primitives, `GLTFLoader` represents the
tagged variant node as a `Group` containing six or seven `SkinnedMesh` primitive
children rather than putting `extras.variantId` on every primitive. Runtime
selection therefore keeps the complete tagged group and all its primitives;
checking only the primitive `userData` would incorrectly fail open. Meshopt may
emit one equivalent skin descriptor per primitive, but all descriptors reference
the same joint nodes; `validate_enemy_glb.py` explicitly verifies this invariant.

The final anatomy pass replaces stacked cylinders and body-sized cuboids with
continuous elliptical lofts. It establishes a pelvis-to-waist-to-ribcage taper,
sloped shoulder/deltoid transitions, biceps-to-elbow-to-forearm profiles,
thigh-to-knee-to-calf continuity, and rounded heel-to-toe combat boots with no
slab outsole. Watertight two-bone gradient sleeves bridge both shoulders, elbows,
knees, and ankles so deformation does not expose black cuts or open sockets.
Close LOD gloves include a palm, knuckle volume, four curled fingers, and a
crossing thumb curled below the weapon contact rather than through it.
Shoulder-width feet, a forward combat knee break, shortened tapered boot toes, a
high blended neck gaiter plus shallow front collar bib, and recessed opaque
goggles remove the former mannequin stance, isolated cylinder neck, and spherical
eye highlights. Armor, cloth, webbing, and packs
remain separate layers with visible thickness. Helmet, hood, boonie, visor,
shoulder, pack, ammunition, cape, and medic-kit silhouettes keep every role
recognisable before camouflage detail resolves.

## Motion set

The pack exports fourteen clips:

- idle, rifle-ready, aim, fire, and a 48-frame magazine reload;
- forward walk, backward walk, left/right strafe, and forward run;
- front/back hit reactions and front/back deaths.

Idle, rifle-ready, and locomotion retain a distinct low-ready silhouette. Aim and
fire raise the rifle about 0.265 m: a single tapered faceted stock closes onto the
shoulder pocket, the raised optic meets the dominant-eye line, the cheek settles
onto the stock, the head leans slightly forward, the
support elbow stays under the handguard, and the firing elbow resolves outboard.
Contacts are measured against the actual pistol-grip and handguard geometry rather
than the weapon control bone. Reload hand and moving-magazine targets are solved
from upper/forearm lengths and an explicit shoulder-relative elbow hint instead of
arbitrary Euler offsets. Action keys are baked from armature-space targets only
while animation evaluation is detached, preventing earlier F-curves from silently
overwriting later contact poses. The built-in audit rejects backwards/vertical
weapon axes, broken grip contacts, changed bone lengths, non-finite transforms,
crossed static feet, and unreachable reload contacts.

## Release budgets and derived metrics

| LOD | Triangle limit | File-size limit |
| --- | -------------: | --------------: |
| 0   |         90,000 |     5,500,000 B |
| 1   |         42,000 |     3,500,000 B |
| 2   |         18,000 |     2,500,000 B |

Every LOD must contain all six appearances, the same named 22-joint hierarchy,
all fourteen clips, no more than eight materials, no more than 32 joints, and no
external URI. The 4 × 2 power-of-two fabric atlas is embedded in the GLB; unused
material slots may be pruned by optimization.

The final 2026-07-19 delivery gate measured:

| LOD | Triangles | Meshopt GLB bytes | Materials | Textures | Joints | Clips |
| --- | --------: | ----------------: | --------: | -------: | -----: | ----: |
| 0   |    84,152 |         1,071,472 |         7 |        3 |     22 |    14 |
| 1   |    25,056 |           611,592 |         7 |        3 |     22 |    14 |
| 2   |    16,736 |           521,260 |         7 |        3 |     22 |    14 |

These values are derived build outputs rather than hand-authored manifest claims.
After any regeneration, use `validate_enemy_glb.py` and the generated report to
replace this snapshot and confirm that every row remains inside its budget.

## Runtime contract

- Manifest: `public/assets/aaa/enemies/manifest.json`
- LOD0/1/2: `soldier-pack-lod{0,1,2}.glb`
- Variant parent nodes carry `extras.variantId` and `extras.sharedSkeleton`.
- Runtime uses `SkeletonUtils.clone`, selects one complete tagged variant group
  per actor (including every material primitive below it), rejects untagged or
  cross-tagged primitives, and builds a Three.js `LOD` from the corresponding
  variant in each loaded source pack.
- The display replacement currently applies only to enemy humanoids in medium/high
  graphics tiers outside zombie and training modes. Low quality and excluded modes
  continue to use the procedural visual path.
- All three source LODs are fetched, structurally validated, and shader-prewarmed
  before any procedural actor visual is hidden. A pack failure keeps every actor
  on the fallback; an individual clone/update failure restores that actor only.
- AI, Rapier collision, hitboxes, team state, spawning, targeting, and damage remain
  TypeScript-owned. This pack is a visual/animation adapter, not a gameplay-rig or
  collision migration.
- Idle/ready/aim and locomotion are selected from live bot state and measured motion.
  Fire, reload, hit, and death are one-shot clips. Killcam replay can request fire
  and seek through the relevant death clip without making the Blender model the
  replay authority.
- LOD selection changes visible source level without changing variant, bone names,
  or clip names. Geometry/materials are shared by the source clones while skeleton
  state and animation mixers remain actor-local.

## Validation and article captures

Run:

```bash
python3 tools/blender/validate_enemy_glb.py \
  public/assets/aaa/enemies/soldier-pack-lod0.glb \
  public/assets/aaa/enemies/soldier-pack-lod1.glb \
  public/assets/aaa/enemies/soldier-pack-lod2.glb \
  --release --manifest public/assets/aaa/enemies/manifest.json

npx vitest run src/render/enemy-asset-pipeline.test.ts \
  src/game/enemy-visual-bot.test.ts src/game/enemy-variants.test.ts

npm run audit:enemies
```

Release validation checks the per-LOD byte/triangle limits, material and joint
budgets, the single shared joint hierarchy, exact six-variant set, required clip
set, non-zero animation channels/durations, embedded-resource policy, and plausible
bounds. Runtime tests cover untrusted manifest parsing, LOD thresholds, tagged
multi-primitive clone selection, cross-variant rejection, local skeleton clones,
shared geometry/material ownership, state-to-clip mapping, one-shots, fail-open
behavior, and disposal. `audit:enemies` then runs high/medium TDM, FFA, and S&D in
a muted background Chromium, drives all fourteen real clips and all three LOD
roots, and verifies first-person final-killcam continuity. Its PNG/JSON evidence
stays ignored under `tools/blender/screenshots/054-enemy-browser-audit/`.

The generator audits 50 critical animation samples in every LOD for bone lengths,
finite transforms, rifle direction, pistol-grip/handguard contacts,
stock-to-shoulder, optic-to-eye, cheek-to-stock, reload reach, magazine contact,
and hit-reaction grip drift. It separately checks all twelve role/death-direction
end poses in every LOD against the floor, measuring both the full skinned mesh and
the body without rifle or magazine vertices. The final gate reported zero errors
in both audits. LOD2's final death-body floor samples ranged from -0.0044 m to
0.0459 m, inside the release tolerance.

The article-ready visual pass renders front and rear aim views for all six roles,
six reload timestamps, forward/backward/strafe/run gait samples, fire, both hit
directions, both death directions, and dedicated front/side/support-grip,
stock/shoulder, and leg-joint close reviews under
`tools/blender/screenshots/enemies/`. The ignored captures are production
evidence, not release assets, and must never be pushed to GitHub. A passing
structural validator does not replace visual inspection of these views or a muted
headless in-game capture of the external actor.

Both the project release validator and Khronos glTF Validator were run against the
post-Meshopt files. All three LODs returned zero errors and zero warnings; each
file uses `EXT_meshopt_compression` and `KHR_mesh_quantization` with no external
URI.

## Regeneration

```bash
'/Applications/Blender.app/Contents/MacOS/Blender' \
  --background --factory-startup \
  --python "$PWD/tools/blender/build_enemy_soldiers.py"

node tools/blender/optimize-glbs.mjs \
  public/assets/aaa/enemies/soldier-pack-lod0.glb \
  public/assets/aaa/enemies/soldier-pack-lod1.glb \
  public/assets/aaa/enemies/soldier-pack-lod2.glb
```

The Blender authoring file and generation report are stored under
`tools/blender/work/enemies/`, which is ignored.
