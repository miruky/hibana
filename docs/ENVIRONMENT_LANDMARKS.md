# Hibana dense-world landmark catalog

This document is the production brief and identity ledger for the 31-stage dense-world pack. The machine-readable contract lives in `tools/blender/stage-profiles.json` version 2. `src/game/stage.ts` and `src/game/stages.ts` remain authoritative for collision, spawn safety, routes, openings, and deterministic layout. The Blender pack is a visual replacement; this catalog does not create gameplay routes by declaration.

## Non-negotiable composition contract

- Every stage is a dense settlement with a majority of tall buildings. Roads, small plazas, water, firing lanes, and spawn clearance are deliberate negative space, not leftover emptiness.
- Every stage owns exactly two castle-scale mega-landmarks. All 62 IDs and Japanese names are unique. A landmark may share low-level engineering logic internally, but its silhouette, roof, facade, material cues, narrative purpose, and stage composition must remain stage-specific.
- `takadai` alone retains the existing Celestine tidal abbey identity; its second landmark is the distinct Akatsuki royal fortress. Neither identity may be reused on another stage.
- The authored horizon is layered real 3D: foreground boundary, midground districts, and aggressively simplified distant buildings/terrain/infrastructure. Raster skyline mattes and cylindrical picture walls are forbidden.
- `combatFlow` is an art-direction brief for entrances, flanks, and vertical readability. It is not proof that a landmark is enterable. Only openings and routes backed by the TypeScript layout and collision contract are playable; the remaining landmark mass is visual-only and must not silently invent collision or traversal.
- Tall-building density is expressed by `highRiseRatio`, `dominantHeightM`, `targetBuildingCount`, and `coverageRatio`. Low-rise structures are reserved for cover, route legibility, or silhouette contrast.
- LOD0 spends geometry on visible entrances, contact faces, rooflines, stairs, and first-person silhouettes. LOD1 removes secondary facade and roof detail. LOD2 is a material-batched, HLOD-style distant representation that preserves the landmark crown, roof rhythm, major voids, and district massing; it is not a separate collision mesh.

## Catalog

| Stage       | Dense-city identity    | Mega-landmark A          | Mega-landmark B          |
| ----------- | ---------------------- | ------------------------ | ------------------------ |
| `kunren`    | 統合軍事学園都市       | 黒鋼統合指揮堡           | 白煙エアロスタット格納殿 |
| `souko`     | 雨港立体物流都市       | 潮騒自動積層庫           | 雨門税関メガターミナル   |
| `nakaniwa`  | 水庭宮殿密集街         | 睡蓮冠宮                 | 花香温室楼塞             |
| `kairou`    | 砂岩列柱交易都市       | 子午線大列柱聖域         | 風冠隊商天測城           |
| `kouwan`    | 船渠工業高層港都       | 防波船昇降殿             | 海帆港務取引塔           |
| `takadai`   | 潮汐修道城下高密街     | セレスティン潮汐大修道城 | 暁冠王立城塞             |
| `sakyuu`    | 埋没装甲掘削都市       | 砂没移動城格納庫         | 日輪螺旋掘削冠           |
| `setsugen`  | 極地連結研究高層区     | 北光三脚アーコロジー     | 極光データ聖堂           |
| `koushou`   | 溶鋼立体工業都市       | 双炉熔鉄城               | 紅河連続鋳造殿           |
| `yoichi`    | 雨夜垂直市場都市       | 千看板垂直市場塔         | 雨華歌劇取引殿           |
| `okujou`    | 空中連結超高層区       | 雲端放送尖塔             | 天軌アトリウムホテル     |
| `saisekiba` | 段丘採石工業町         | 地層破砕階塔             | 谺梁石材加工殿           |
| `chikurin`  | 山寺門前高密木造町     | 九蓋翠雲寺               | 竹海修学院城             |
| `tanada`    | 水階農業高層集落       | 雲稲段倉城               | 千輪水渠院               |
| `misaki`    | 海蝕軍港城塞町         | 嵐硝子灯台城             | 鯨背潜水艦庫             |
| `haieki`    | 霧鉄道会社都市         | 鉄霧大終着殿             | 時鐘給水庫城             |
| `kyokoku`   | 赤崖段丘要塞都市       | 赤門懸崖宮               | 天鎖水道要塞             |
| `kohan`     | 湖畔観測学園都市       | 鏡星三連天文殿           | 水崖水力大山荘           |
| `kuko`      | 航空都市型高層エプロン | 翼冠国際空港殿           | 軌道航空管制城           |
| `onsengai`  | 湯煙山岳旅館高密街     | 千湯大旅籠               | 蒸気時計湯塔             |
| `z01`       | 停電後浸水メガブロック | 停電市政メガブロック     | 折冠立体交通城           |
| `z02`       | 延焼競技都市区         | 火葬競技大殿             | 火見集合塔城             |
| `z03`       | 沈降霧港廃都           | 転覆船渠大殿             | 霧鐘揚貨城               |
| `z04`       | 崩落修道城下墓都       | 断薔薇大修道城           | 骸鐘納骨城楼             |
| `z05`       | 溶岩坑道立体鉱都       | 熔脈立坑昇降城           | 黒曜熔錬方舟             |
| `z06`       | 封鎖食肉工業高層区     | 冷鎖凍結塔城             | 鉄索懸送加工殿           |
| `z07`       | 隔離検疫ゲート都市     | 封疫大関門城             | 白盾除染病院塔           |
| `z08`       | 地下商業駅郭都市       | 地下環状交易宮           | 残灯防潮駅大殿           |
| `z09`       | 降灰娯楽都市廃園       | 灰冠大観覧城             | 蝕影鏡迷宮殿             |
| `z10`       | 火口環状防衛鉱都       | 火輪遮蔽司令環           | 地熱針塔城               |
| `renshujo`  | 山岳訓練基地町         | 連峰統合指揮館           | 双稜可変標的城           |

## Research translation

The catalog uses real architectural and infrastructure principles as shape research, then recombines them into original fictional facilities. No third-party mesh, texture, plan, or facade is copied.

- Dense historic-city logic comes from the relationship between tightly packed houses, gated streets, wells, and public institutions described for the [Historic City of Ahmadabad](https://whc.unesco.org/en/list/1551/). Hibana translates this into narrow route networks and landmark-led public space rather than copying any individual building.
- The rock-supported abbey, staggered convent buildings, fortified village, tidal approach, and inseparable landscape silhouette documented for [Mont-Saint-Michel and its Bay](https://whc.unesco.org/en/list/80) inform `takadai`'s vertical settlement logic. Hibana recombines those principles into an original tidal fortress and keeps both stage landmarks distinct from the source monument and from every other stage.
- The landform-first silhouette and continuous tall facade wall of the [Erbil Citadel](https://whc.unesco.org/en/list/1437) informs cliff, hill, and crater stages. The parallel defensive walls and differentiated waterfront/residential sectors of [Derbent](https://whc.unesco.org/en/list/1070/) inform route hierarchy.
- [Pergamon](https://whc.unesco.org/en/list/1457/) demonstrates how temples, theatres, porticoes, and civic structures can step with steep terrain. This becomes the vertical combat logic for quarry, rice-terrace, canyon, and mountain stages.
- The pedestrian staircase, mixed-use upper floors, infrastructure, and slope-adapted industrial buildings of [Sewell Mining Town](https://whc.unesco.org/en/list/1214/) inform dense industrial hillside settlements. The linked mine–rail–port system of [Ombilin](https://whc.unesco.org/en/list/1610/) supports functional storytelling across mine, railway, quarry, and harbor stages.
- NASA's [Vehicle Assembly Building](https://public.ksc.nasa.gov/partnerships/capabilities-and-testing/physical-assets/vehicle-assembly-building-vab/) demonstrates that a hero industrial landmark reads through a small number of enormous bays, doors, cranes, and work cells. Hibana uses that scale hierarchy for airport, military, and logistics landmarks without reproducing the VAB.
- The extremely remote, compact research program represented by ESA's [Concordia station floor plan](https://www.esa.int/ESA_Multimedia/Images/2013/03/Concordia_floor_plan) informs the enclosed bridges and tightly connected volumes of the polar stage.

## Data contract

Each profile contains:

- `cityProfile`: density archetype, building-count target, coverage, high-rise ratio, height bands, street-width range, block/roof/facade language, real-3D horizon rule, negative-space rule, verticality rule, and forbidden motifs.
- `megaLandmarks[2]`: stable ID, Japanese name, narrative purpose, dimensions in meters, placement intent, silhouette, roof, facade, material cues, three-part flow brief, and common LOD policy.

`tools/blender/build_all_stages.py` generates three delivery GLBs per stage. Every LOD contains two separate, non-empty landmark mesh groups. Their glTF `extras` carry `hibanaLandmarkId`, index, style, measured bounds, target dimensions, and placement. The generator version and SHA-256 are written to both the manifest and GLBs so a script change cannot be released with stale binaries unnoticed.

The Blender generator does not duplicate or replace gameplay collision. It consumes the TypeScript-authored layout for visual alignment and preserves the procedural gameplay walls, breakables, spawns, and walkable openings. Landmark identity and visible geometry are therefore release claims; universal landmark interiors are not.

## Runtime and fail-open contract

- `public/assets/aaa/manifest.json` contains exactly one stage asset entry per authoritative stage ID and exactly three LOD URLs per entry.
- Stage GLBs are enabled for medium/high graphics tiers. Low quality intentionally keeps the procedural renderer.
- A monolithic stage replacement selects one transport source before loading: LOD0 on high, LOD1 on medium, and no external GLB on low. The selected GLB must load, validate, clone, and compile before the old raster matte, non-breakable procedural props, procedural shell/decor, and stage kit may be hidden. Unselected LODs are never fetched or retained.
- Invalid manifest data, missing GLBs, decode/compile failure, or disposal during load leaves the deterministic TypeScript fallback visible. Gameplay collision, spawn logic, routes, breakables, and physics are never sourced from the Blender meshes.
- The real-3D horizon must remain layered geometry after commit. A hidden fallback matte may exist solely for the fail-open path.

## LOD and delivery budgets

| Gate                      |   Release limit |
| ------------------------- | --------------: |
| File size, each stage GLB | 5,500,000 bytes |
| LOD0 triangles            |         260,000 |
| LOD1 / LOD0 triangles     |             45% |
| LOD2 / LOD0 triangles     |             12% |
| Materials, each stage GLB |              24 |

Material-wide merged meshes and separate landmark namespaces keep draw calls bounded while retaining auditable landmark identity. Passing these static limits does not prove real-device performance; the headless browser audit and the real-browser benchmark remain separate release gates.

## Validation

```bash
node tools/blender/validate-stage-profiles.mjs
python3 tools/blender/validate_dense_stage_assets.py
python3 tools/blender/validate-glb.py public/assets/aaa/stages/*-lod0.glb \
  --manifest public/assets/aaa/manifest.json --expect-count 31
python3 -m unittest tools.blender.test_validate_dense_stage_assets

python3 tools/blender/audit_blender_render_set.py \
  --render-dir /private/tmp/hibana-blender/<candidate>/renders \
  --output /private/tmp/hibana-blender/<candidate>/render-pre-gate.json

npm run audit:stages -- --quality=high
```

Copy `tools/blender/stage-reference-scorecard.template.json` into the private candidate's scorecard directory and bind it to the exact reference/render SHA-256 values. A scorecard for a different render is invalid even if the filename is reused.

The profile validator rejects missing or duplicate stage/landmark identities. The dense validator checks the exact 31-stage manifest and thumbnail sets, literal replacement flags, generator provenance, all 93 GLBs, PBR surface metadata, two real landmark groups per LOD, finite bounds, non-zero triangle contribution, and the LOD/file budgets. The render pre-gate rejects missing/duplicate views, cameras inside walls, clipped or crushed frames, large flat-black/flat-white voids connected to the lower image border, and aligned grids of copied near-black facade rectangles. It is only a technical filter: a human still compares every candidate to its ImageGen reference and may reject a technically valid asset. The signed human scorecard explicitly covers facade/opening quality, terrain/world continuity and landmark-interior legibility in addition to composition, identity, materials, density, gameplay readability and atmosphere; every category must score at least 7/10 and the average at least 8/10. The browser audit then opens each stage in a muted headless Chromium session, waits for an exact successful asset commit, checks that the match remains alive, and captures the real in-game result.

Article and milestone captures belong under the ignored `tools/blender/screenshots/` tree (or `/tmp` for disposable audits). They must never be added to GitHub.
