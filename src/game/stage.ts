import { mulberry32, type Rand } from '../core/rng';
import {
  GENERATED_STAGE_PLACEMENT_PROVENANCE,
  resolveGeneratedStagePlacement,
} from './stage-placement-runtime';
import type { RuntimeStagePlacement } from './stage-placement-runtime-core';

// ── 映画的アトモスフィア(R11): THREE非依存の純型。render/atmosphere.ts と共有する ──
export type MoodId = 'day' | 'dusk' | 'night' | 'overcast' | 'snow';
export type GrassKind = 'none' | 'blade' | 'dry' | 'reed' | 'snowtuft';
// 'lava'(溶岩の火の粉/加算) と 'ash'(降灰/非加算) は ⑥ゾンビ荒廃ステージ用に追加。
// atmosphere.ts 側の PARTICLE_SPECS へ対応エントリを追加するまでは exhaustive Record が赤くなる(別担当対応)。
export type ParticleKind = 'none' | 'snow' | 'dust' | 'ember' | 'firefly' | 'lava' | 'ash';
export type SilhouetteKind = 'none' | 'mountain' | 'ridge' | 'skyline';

// カラーグレードのパラメータ束(表示前段の色収差/ビネット/グレイン/コントラスト/彩度/ティント)。
export interface GradeParams {
  tint: [number, number, number];
  contrast: number;
  saturation: number;
  vignette: number;
  vignetteR: number;
  grain: number;
  chroma: number;
}

export interface StagePalette {
  sky: string;
  fog: string;
  floor: string;
  wall: string;
  obstacle: string;
  accent: string;
  lightColor: string;
  lightIntensity: number;
  ambientIntensity: number;
  fogDensity: number;
  emissiveAccent: boolean;
  // ── リアル化(R5): 大気散乱/露出/Bloom。全optionalで既存パレットは無改変のままコンパイルできる ──
  turbidity?: number;
  rayleigh?: number;
  mieCoefficient?: number;
  mieDirectionalG?: number;
  elevation?: number;
  azimuth?: number;
  exposure?: number;
  environmentIntensity?: number;
  bloomStrength?: number;
  bloomThreshold?: number;
  // ── 映画的アトモスフィア(R11) ──
  mood?: MoodId;
  groundFog?: number;
  groundFogTop?: number;
  grassKind?: GrassKind;
  grassDensity?: number;
  particle?: ParticleKind;
  particleAmount?: number;
  silhouette?: SilhouetteKind;
  grade?: Partial<GradeParams>;
}

// ── 建造物アーキタイプ(R21 エリア超拡大) ──
/**
 * 衝突・内部動線・登坂経路まで持つプレイアブル建造物。
 * 後半9種はR65で追加したテーマ固有地区で、遠景のハリボテではない。
 */
export type BuildingKind =
  | 'arena' | 'hangar' | 'tower' | 'warehouse' | 'cathedral'
  | 'bunker' | 'terminal' | 'refinery' | 'villa' | 'pagoda'
  | 'fortress' | 'station' | 'checkpoint' | 'metro' | 'abbey';

// ── 環境オブジェクト36種 ──────────────────────────────────────────────────
export type PropKind =
  | 'conifer' | 'broadleaf' | 'deadtree' | 'sakura' | 'bamboo'
  | 'rock' | 'towercrane' | 'portalkrane' | 'smokestack' | 'gastank'
  | 'watertower' | 'transformer' | 'antenna' | 'truck' | 'derelictcar'
  | 'forklift' | 'barricadecar' | 'concretebarrier' | 'fence' | 'watchpost'
  | 'tankhull' | 'scaffold' | 'streetlight' | 'signboard' | 'bench'
  | 'vendingmachine' | 'drumgroup' | 'pallet' | 'torii' | 'stonelantern'
  | 'well' | 'pier' | 'utilitypole' | 'rubble' | 'gasbottlegroup' | 'supplycrate';

/**
 * ミニシーン(超リアル化Layer C, R53-S2)のテンプレートID。
 * 各シーンは 2〜5 プロップの相対配置テンプレート(SCENE_TEMPLATES参照)を持ち、
 * シード決定論のアンカー位置+連続回転(シード回転)で配置される「物語性のある小場面」。
 */
export type MiniSceneId = 'shizai' | 'kenmon' | 'sandou' | 'jiko' | 'idobata' | 'kouba' | 'kyuukei';

export interface ObjectEntry {
  /** scatter='scene' の時は無視される(型都合上の代表prop。実際に置かれるkind群はsceneId側で決まる)。 */
  kind: PropKind;
  /** scatter='scene' の時は「シーンを何箇所配置するか」を表す。 */
  count: number;
  /**
   * 配置方式。'scene' はミニシーン(複数プロップの相対配置テンプレート)を count 回試行配置する。
   * scene 指定時は sceneId が必須(未設定ならそのエントリは無視される)。
   */
  scatter: 'random' | 'perimeter' | 'cluster' | 'scene';
  clusterRadius?: number;
  /** scatter='scene' の時のみ使用。ミニシーンテンプレートID(SCENE_TEMPLATES参照)。 */
  sceneId?: MiniSceneId;
}

/** ステージ個性レシピ。StageDef の任意フィールド。後方互換(未設定時は汎用配置) */
export interface StageRecipe {
  /** テーマ説明(1行) */
  theme: string;
  /** 配置する建造物アーキタイプ(1〜3棟) */
  buildings: BuildingKind[];
  notes?: string;
  /** 環境オブジェクト配置リスト(パイロット段階: DC+40箱/ステージ以内) */
  objects?: ObjectEntry[];
}

export interface StageDef {
  id: string;
  name: string;
  subtitle: string;
  seed: number;
  size: number;
  obstacleCount: number;
  maxHeight: number;
  botCount: number;
  palette: StagePalette;
  /** 任意: テーマ別レシピ(未設定なら汎用プロシージャル配置) */
  recipe?: StageRecipe;
}

export interface BoxSpec {
  x: number;
  y: number;
  z: number;
  w: number;
  h: number;
  d: number;
  color: string;
  emissive: boolean;
  /**
   * true = 物理コライダーのみ生成・メッシュなし。
   * match.ts が isGhost フラグで scene.add をスキップ済み(R21 不可視境界壁)。
   */
  ghost?: boolean;
  /**
   * true = プレイアブル境界外の装飾ボックス。
   * 物理コライダーは存在するが ghost 壁の外側なので到達不可。
   * テスト・ミニマップのスポーン距離チェックでスキップ対象。
   */
  decor?: boolean;
  /**
   * 破壊可能プロップ(BF5簡易版)。
   * ghost/decor/構造壁/床以外の小〜中型遮蔽プロップの約35%に決定論的に付与。
   * match.ts が個別メッシュ+コライダーを生成し HP0 で破壊演出+消滅を担う。
   */
  breakable?: { hp: number };
  structural?: boolean; // V31: 構造支持材(キャットウォーク支柱等)=絶対に破壊不可
  /** 環境オブジェクト由来のボックス。将来のマージ描画振り分け用マーカー */
  prop?: boolean;
  /** R64以前の箱型遠景。新しい連続地形/遠景メッシュが描画を引き継ぐため物理・描画とも省略する。 */
  legacyHorizon?: boolean;
  /** h > 3 の大型プロップに自動付与。シャドウキャスター対象フラグ */
  shadowCaster?: boolean;
  /** 実際に内部を戦えるテーマ建築の所属。描画最適化と全ステージ監査に使う。 */
  district?: BuildingKind;
  /** 衝突付きの窓／ガラス手すり。Blenderとfail-open描画の双方で半透明材を使う。 */
  glazing?: boolean;
  /** V5: このコライダーが属する、戦闘可能な巨大ランドマークの一意ID。 */
  landmarkId?: string;
  /** V5: Blender/validatorが接地・入口・上階路を区別するための部位。 */
  landmarkPart?: 'floor' | 'wall' | 'interior' | 'upper-wall' | 'upper-walk' | 'stair' | 'tower' | 'column' | 'gate-column';
  /** V5: 単なる遠景ではなく、内部へ入って戦える衝突空間。 */
  combatSpace?: true;
  /** Kairou: 既存の実屋根/実塔上に収まる、衝突付き上層商館。 */
  urbanVolume?: true;
  /** Souko: Blenderの物流モニターを載せる、実際の建物屋根スラブ。 */
  roofMonitorSupport?: true;
  /** Souko: モニターの閉じた衝突包絡。視覚メッシュと独立して決定的に生成する。 */
  roofMonitor?:
    | { supportIndex: number; variant: 0 | 1 | 2; part: 'curb' }
    | { supportIndex: number; variant: 0 | 1 | 2; part: 'body' | 'roof-proxy'; segmentIndex: number };
  /** 衝突箱の箱描画を、同じIDのBlender視覚へ置換する契約。 */
  visualReplacement?: 'souko-roof-monitor-v1';
}

export type SpawnPoint = [number, number, number];

/**
 * 環境プロップ1インスタンス分の「視覚配置」メタデータ(R53-S2 / M2c契約)。
 * コライダー生成(BoxSpec, buildProp() 経由)とは完全に独立した並行データ列だが、
 * generateStage() 内で同時に生成されるため常にboxesと同期している(座標系・インスタンス対応も同一)。
 *
 * ── M2c(match.ts オーナー)向け配線メモ ──────────────────────────────────
 * 1インスタンス = 1回の prop-visuals.buildPropVisual(kind, cx, cz, baseY=0, rotRad, scale, rand, palette)
 * 呼び出しに対応する。rand は呼び出し側(match.ts)が用意する決定論RNG(例: instance毎に
 * mulberry32(def.seed ^ index) 等)で構わない — 本フィールドはその「入力」だけを提供する。
 * kind が prop-visuals.PROP_VISUAL_KINDS に含まれない場合は、既存の箱ビジュアル
 * (buildProp() が生成した BoxSpec群、boxes 側にそのまま存在)へフォールバックすること。
 */
export interface PropPlacement {
  kind: PropKind;
  /** ワールドX座標(該当インスタンスの中心。boxesの対応ボックス群と同じ地上点)。 */
  cx: number;
  /** ワールドZ座標。 */
  cz: number;
  /**
   * ヨー回転(ラジアン, 0-2π に正規化済み)。**視覚専用**。
   * コライダー(buildProp() が使う 0-3 の90°刻み量子化回転)には一切影響しない
   * — colliderは従来どおり軸整列のボックスのまま。rotRad は量子化回転を基準に
   * ±0.45rad(約26°)の範囲でジッタさせた値(標準化ジッタ, R53-S2)。
   */
  rotRad: number;
  /** スケール倍率(1.0 ± 0.12 の一様ジッタ)。視覚専用 — コライダー寸法は不変。 */
  scaleJitter: number;
}

/** Blender/実画面QAが、配置済み建築の中心と向きを推測せず共有するための配置契約。 */
export interface DistrictPlacement {
  kind: BuildingKind;
  cx: number;
  cz: number;
  /** 0/90/180/270度の量子化回転。コライダーと完全に同じ向き。 */
  rot: number;
  width: number;
  depth: number;
}

export type LandmarkCollisionTemplate = 'abbey' | 'courtyard' | 'hall' | 'bridge' | 'vertical';

export interface LandmarkApproach {
  /** 建物外側から入口へ向かう、衝突物を置かない実ゲーム路。 */
  start: [number, number];
  end: [number, number];
  width: number;
}

/**
 * Blenderとゲーム衝突が共有する、境界内巨大ランドマークの唯一の配置真実。
 * `width/depth` は当たり判定を含む実フットプリント、`height` はBlenderが
 * その接地フットプリント上へ組む主シルエットの上限である。
 */
export interface LandmarkPlacement {
  id: string;
  districtKind: BuildingKind;
  collisionTemplate: LandmarkCollisionTemplate;
  cx: number;
  cz: number;
  rot: number;
  width: number;
  depth: number;
  height: number;
  entrance: [number, number];
  approach: LandmarkApproach;
  grounded: true;
  combatSpace: true;
}

export interface StageLayout {
  /** Runtime visual assets must match the exact layout family and generator inputs. */
  placementProvenance: {
    placementSource: 'runtime-release' | 'canonical-solver-v2-authoring';
    placementSolverSha256: string;
    stageWorldCatalogSha256: string;
  };
  boxes: BoxSpec[];
  playerSpawns: SpawnPoint[];
  botSpawns: SpawnPoint[];
  /**
   * 環境プロップの視覚配置一覧(R53-S2)。recipe.objects が無いステージでは空配列。
   * boxes とは独立した列だが同一の generateStage() 呼び出しから生成されるため常に同期する。
   */
  propPlacements: PropPlacement[];
  /** 実際に配置に成功した、戦闘可能な建築地区。 */
  districtPlacements: DistrictPlacement[];
  /** V5: 遠景画像/境界外シルエットを数えない、衝突付きの境界内巨大建築。 */
  landmarkPlacements: LandmarkPlacement[];
}

export interface Aabb {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

function overlaps(a: Aabb, b: Aabb, margin: number): boolean {
  return (
    a.minX - margin < b.maxX &&
    a.maxX + margin > b.minX &&
    a.minZ - margin < b.maxZ &&
    a.maxZ + margin > b.minZ
  );
}

function aabbOf(x: number, z: number, w: number, d: number): Aabb {
  return { minX: x - w / 2, maxX: x + w / 2, minZ: z - d / 2, maxZ: z + d / 2 };
}

const SPAWN_CLEARANCE = 6;
/** 建造物センターからスポーンまでの最低距離 */
// 建物外壁からスポーンまでの実距離。10mあれば開始直後の衝突を防ぎつつ、
// 300m級マップへ3つ以上の地区を分散配置できる。
const BUILD_SPAWN_CLEAR = 10;
const GRID = 2;
/** 不可視境界壁の高さ(m)。ジャンプ/ウォールランでも越えられない */
const GHOST_WALL_H = 24;

// ── 建造物配置ヘルパー ──────────────────────────────────────────────────

/**
 * ローカルオフセット (dx, dz) を rotSteps × 90° 回転させる。
 * rotSteps=1: 90°CW, 2: 180°, 3: 270°CW
 */
function rotXZ(dx: number, dz: number, rot: number): [number, number] {
  switch (rot & 3) {
    case 1:
      return [dz, -dx];
    case 2:
      return [-dx, -dz];
    case 3:
      return [-dz, dx];
    default:
      return [dx, dz];
  }
}

/**
 * 建造物ローカル座標 → ワールド BoxSpec。
 * @param cx,cz  ワールド建造物中心
 * @param rot    回転ステップ(0-3)
 * @param lx,lz  ローカルオフセット(回転前)
 * @param yBot   ボックスの底 Y 座標
 * @param lw,lh,ld ローカル幅(X軸)/高さ/奥行き(Z軸)。奇数回転時に w/d を入れ替え
 */
function pb(
  cx: number,
  cz: number,
  rot: number,
  lx: number,
  lz: number,
  yBot: number,
  lw: number,
  lh: number,
  ld: number,
  color: string,
  emissive = false,
): BoxSpec {
  const [rx, rz] = rotXZ(lx, lz, rot);
  const [fw, fd] = rot & 1 ? [ld, lw] : [lw, ld];
  return { x: cx + rx, y: yBot + lh / 2, z: cz + rz, w: fw, h: lh, d: fd, color, emissive };
}

/** 建造物の軸平行バウンディングボックスサイズ [w, d] を返す(AABB 重複チェック用) */
function getBuildingFootprint(kind: BuildingKind, rot: number): [number, number] {
  const dims: Record<BuildingKind, [number, number]> = {
    arena: [44, 30],
    hangar: [40, 22],
    tower: [22, 22],
    warehouse: [56, 14],
    cathedral: [36, 22],
    // 南側の屋上階段（外縁 z=±15.1m）まで含む。
    bunker: [40, 32],
    terminal: [60, 26],
    refinery: [48, 36],
    villa: [46, 34],
    pagoda: [38, 38],
    fortress: [56, 38],
    station: [60, 30],
    checkpoint: [50, 28],
    metro: [54, 32],
    // 外郭城壁、四隅塔、内部階段を含む巨大修道城。
    abbey: [124, 100],
  };
  const [lw, ld] = dims[kind];
  return rot & 1 ? [ld, lw] : [lw, ld];
}

// V5 dense-world proof is intentionally limited to the representative audit
// set until its real-browser collision/LOS/performance gate passes.  The
// remaining fixed stages continue through the proven v4 planner; expanding
// this set is therefore an explicit production decision rather than an
// accidental all-catalog gameplay migration.
const DENSE_WORLD_V5_PROOF_STAGES = new Set([
  'kairou', 'chikurin', 'setsugen', 'kouwan', 'sakyuu', 'z04', 'takadai',
]);
const DENSE_WORLD_V5_TARGET_COVERAGE = 0.245;
const DENSE_WORLD_V5_MAX_COVERAGE = 0.34;
const DENSE_WORLD_V5_PRIMARY_STREET_HALF = 8; // 16m combat street
const DENSE_WORLD_V5_ALLEY_HALF = 3.5; // 7m connected service alley
const DENSE_WORLD_V5_BUILDING_GAP = 6; // 6m walkable gap inside one block
const DENSE_WORLD_V5_PLAYER_CLEAR = 30;
const DENSE_WORLD_V5_BOT_CLEAR = 8;

interface LandmarkPrototype {
  id: string;
  districtKind: BuildingKind;
  collisionTemplate: LandmarkCollisionTemplate;
  width: number;
  depth: number;
  height: number;
}

/** Representative slice of the profile-authored 62-ID catalog.
 *
 * These values are copied into gameplay code deliberately: browser physics
 * must not read a Blender-only JSON file at runtime.  The production follow-up
 * will generate both TS and Blender catalogs from one checked source before
 * this proof set can expand to all 31 stages.
 */
const DENSE_WORLD_V5_LANDMARKS: Record<string, readonly [LandmarkPrototype, LandmarkPrototype]> = {
  kairou: [
    { id: 'kairou-meridian-hypostyle-sanctuary', districtKind: 'cathedral', collisionTemplate: 'courtyard', width: 114, depth: 74, height: 38 },
    { id: 'kairou-windcrown-caravan-observatory', districtKind: 'fortress', collisionTemplate: 'vertical', width: 88, depth: 80, height: 54 },
  ],
  chikurin: [
    { id: 'chikurin-nine-canopy-temple', districtKind: 'pagoda', collisionTemplate: 'vertical', width: 94, depth: 78, height: 60 },
    { id: 'chikurin-bamboo-scholar-citadel', districtKind: 'villa', collisionTemplate: 'courtyard', width: 110, depth: 70, height: 44 },
  ],
  setsugen: [
    { id: 'setsugen-borealis-tripod-arcology', districtKind: 'tower', collisionTemplate: 'bridge', width: 90, depth: 80, height: 58 },
    { id: 'setsugen-aurora-data-cathedral', districtKind: 'terminal', collisionTemplate: 'hall', width: 108, depth: 60, height: 44 },
  ],
  kouwan: [
    { id: 'kouwan-breakwater-ship-lift-basilica', districtKind: 'terminal', collisionTemplate: 'bridge', width: 134, depth: 66, height: 60 },
    { id: 'kouwan-umiho-exchange-tower', districtKind: 'tower', collisionTemplate: 'vertical', width: 98, depth: 84, height: 72 },
  ],
  sakyuu: [
    { id: 'sakyuu-sunken-crawler-vault', districtKind: 'refinery', collisionTemplate: 'hall', width: 138, depth: 76, height: 40 },
    { id: 'sakyuu-helios-drill-crown', districtKind: 'tower', collisionTemplate: 'vertical', width: 86, depth: 72, height: 78 },
  ],
  z04: [
    { id: 'z04-severed-rose-abbey', districtKind: 'abbey', collisionTemplate: 'abbey', width: 124, depth: 100, height: 72 },
    { id: 'z04-ossuary-bell-keep', districtKind: 'cathedral', collisionTemplate: 'vertical', width: 94, depth: 84, height: 80 },
  ],
  takadai: [
    { id: 'takadai-celestine-tidal-abbey', districtKind: 'abbey', collisionTemplate: 'abbey', width: 124, depth: 100, height: 70 },
    { id: 'takadai-dawnkeep-crown-citadel', districtKind: 'fortress', collisionTemplate: 'courtyard', width: 96, depth: 86, height: 76 },
  ],
};

interface DenseWorldBlock {
  ix: number;
  iz: number;
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
  cx: number;
  cz: number;
}

/** Distance from a point to the outside of a footprint (zero when inside). */
function pointAabbDistance(x: number, z: number, box: Aabb): number {
  const dx = Math.max(0, box.minX - x, x - box.maxX);
  const dz = Math.max(0, box.minZ - z, z - box.maxZ);
  return Math.hypot(dx, dz);
}

function approachAabb(approach: LandmarkApproach): Aabb {
  const halfWidth = approach.width / 2;
  return {
    minX: Math.min(approach.start[0], approach.end[0]) - halfWidth,
    maxX: Math.max(approach.start[0], approach.end[0]) + halfWidth,
    minZ: Math.min(approach.start[1], approach.end[1]) - halfWidth,
    maxZ: Math.max(approach.start[1], approach.end[1]) + halfWidth,
  };
}

/** Place the exact two profile identities fully inside the combat bounds. */
function buildDenseWorldV5Landmarks(
  def: StageDef,
  playerSpawns: SpawnPoint[],
  botSpawns: SpawnPoint[],
): LandmarkPlacement[] {
  const prototypes = DENSE_WORLD_V5_LANDMARKS[def.id];
  if (!prototypes) return [];
  const half = def.size / 2;
  const abbeyStage = prototypes[0].collisionTemplate === 'abbey';
  const result: LandmarkPlacement[] = [];
  // Kairou's two reference heroes deliberately share one monumental northern
  // plaza.  Reserving the legacy origin fortress forced them into opposite
  // corners and made the reference composition physically impossible: from
  // every truthful first-person route one hero was hidden behind an ordinary
  // district.  The open origin is therefore part of Kairou's authored street
  // graph, while every other proof map retains the compatibility reservation.
  const centralReservation = !abbeyStage && def.id !== 'kairou' && def.recipe?.buildings.length
    ? (() => {
        const centralKind = [...def.recipe.buildings].sort((a, b) => {
          const [aw, ad] = getBuildingFootprint(a, 0);
          const [bw, bd] = getBuildingFootprint(b, 0);
          return bw * bd - aw * ad;
        })[0]!;
        const [width, depth] = getBuildingFootprint(centralKind, def.seed & 3);
        return { footprint: aabbOf(0, 0, width, depth), depth };
      })()
    : null;
  const footprints: Aabb[] = centralReservation ? [centralReservation.footprint] : [];
  const approaches: Aabb[] = [];

  for (const [index, prototype] of prototypes.entries()) {
    const desired: [number, number] = def.id === 'kairou'
      // Both castle-scale silhouettes face the same southern civic plaza.
      // Their collision footprints remain twenty-one metres apart, fully in bounds,
      // and the two 32/28m combat halls stay independent and enterable.
      ? index === 0
        ? [-66, 45]
        : [56, 45]
      : abbeyStage
      ? index === 0
        ? [0, 0]
        : [-half + 4 + prototype.width / 2, -half + 4 + prototype.depth / 2]
      : index === 0
        // Keep the legacy origin hero, then seat landmark one directly beyond
        // its north firebreak.  The landmark centre becomes the actual road
        // axis, so the street runs through its open combat hall.
        ? [
            -half * 0.28,
            (centralReservation?.depth ?? 0) / 2
              + DENSE_WORLD_V5_BUILDING_GAP + prototype.depth / 2 + 2,
          ]
        // Landmark two mirrors that clearance south of the origin and owns a
        // different service-road junction.
        : [
            half * 0.38,
            -((centralReservation?.depth ?? 0) / 2
              + DENSE_WORLD_V5_BUILDING_GAP + prototype.depth / 2 + 2),
          ];
    // The primary door faces a guaranteed open street rather than another
    // landmark.  Abbey 0 retains its established east-gate approach.
    const entranceDirection: [number, number] = def.id === 'kairou'
      ? [0, -1]
      : abbeyStage && index === 0
      ? [1, 0]
      : index === 0
        ? [0, 1]
        : [1, 0];
    let placed: LandmarkPlacement | null = null;

    // Deterministic square-ring search around the art-directed anchor.  Most
    // anchors succeed at radius zero; the search protects future spawn-count
    // changes without introducing random placement.
    for (let radius = 0; radius <= 56 && !placed; radius += GRID) {
      const offsets: [number, number][] = [];
      if (radius === 0) {
        offsets.push([0, 0]);
      } else {
        for (let delta = -radius; delta <= radius; delta += GRID) {
          offsets.push([delta, -radius], [radius, delta], [-delta, radius], [-radius, -delta]);
        }
      }
      for (const [offsetX, offsetZ] of offsets) {
        const cx = Math.round((desired[0] + offsetX) / GRID) * GRID;
        const cz = Math.round((desired[1] + offsetZ) / GRID) * GRID;
        const footprint = aabbOf(cx, cz, prototype.width, prototype.depth);
        if (
          footprint.minX < -half + 4 || footprint.maxX > half - 4
          || footprint.minZ < -half + 4 || footprint.maxZ > half - 4
        ) continue;
        if (footprints.some((other) => overlaps(other, footprint, DENSE_WORLD_V5_BUILDING_GAP))) {
          continue;
        }
        if (playerSpawns.some(([sx, , sz]) =>
          pointAabbDistance(sx, sz, footprint) < DENSE_WORLD_V5_PLAYER_CLEAR)) {
          continue;
        }
        if (botSpawns.some(([sx, , sz]) =>
          pointAabbDistance(sx, sz, footprint) < DENSE_WORLD_V5_BOT_CLEAR)) {
          continue;
        }
        const faceDistance = entranceDirection[0] !== 0
          ? prototype.width / 2 + 0.8
          : prototype.depth / 2 + 0.8;
        const entrance: [number, number] = [
          cx + entranceDirection[0] * faceDistance,
          cz + entranceDirection[1] * faceDistance,
        ];
        const approach: LandmarkApproach = {
          start: [
            entrance[0] + entranceDirection[0] * 22,
            entrance[1] + entranceDirection[1] * 22,
          ],
          end: entrance,
          width: 12,
        };
        const routeBounds = approachAabb(approach);
        if (
          routeBounds.minX < -half || routeBounds.maxX > half
          || routeBounds.minZ < -half || routeBounds.maxZ > half
        ) continue;
        if (approaches.some((other) => overlaps(other, footprint, 0))) continue;
        if (footprints.some((other) => overlaps(other, routeBounds, 0))) continue;
        placed = {
          ...prototype,
          cx,
          cz,
          rot: 0,
          entrance,
          approach,
          grounded: true,
          combatSpace: true,
        };
        footprints.push(footprint);
        approaches.push(routeBounds);
        break;
      }
    }
    if (!placed) throw new Error(`${def.id}: unable to place in-bounds landmark ${prototype.id}`);
    result.push(placed);
  }

  if (result.length !== 2 || new Set(result.map((item) => item.id)).size !== 2) {
    throw new Error(`${def.id}: v5 requires exactly two distinct landmark identities`);
  }
  return result;
}

interface DenseWorldStreetAxes {
  primaryX: number;
  primaryZ: number;
  alleyX: number;
  alleyZ: number;
}

/** The road graph is derived from the two collision-authoritative buildings. */
function denseWorldStreetAxes(
  def: StageDef,
  landmarks: LandmarkPlacement[],
): DenseWorldStreetAxes {
  const half = def.size / 2;
  if (def.id === 'kairou' && landmarks.length === 2) {
    const westEdge = landmarks[0]!.cx + landmarks[0]!.width / 2;
    const eastEdge = landmarks[1]!.cx - landmarks[1]!.width / 2;
    return {
      // The measured 21m gap between both heroes is the principal north/south
      // boulevard; the shared centreline still gives a complete east/west
      // route through both open combat halls.
      primaryX: Math.round(((westEdge + eastEdge) / 2) / GRID) * GRID,
      primaryZ: landmarks[0]!.cz,
      alleyX: landmarks[1]!.cx,
      alleyZ: -30,
    };
  }
  return {
    primaryX: landmarks[0]?.cx ?? -half * 0.28,
    primaryZ: landmarks[0]?.cz ?? half * 0.28,
    alleyX: landmarks[1]?.cx ?? half * 0.38,
    alleyZ: landmarks[1]?.cz ?? -half * 0.38,
  };
}

/** Select four real player starts on the open street graph before lot packing. */
function buildDenseWorldV5PlayerSpawns(
  def: StageDef,
  landmarks: LandmarkPlacement[],
): SpawnPoint[] {
  const half = def.size / 2;
  const abbeyStage = def.recipe?.buildings[0] === 'abbey';
  const axes = denseWorldStreetAxes(def, landmarks);
  const candidateLines: Array<['x' | 'z', number]> = abbeyStage
    ? [['x', 0], ['z', 0], ['x', -half * 0.72], ['z', half * 0.72]]
    : [
        ['x', axes.primaryX],
        ['z', axes.primaryZ],
        ['x', axes.alleyX],
        ['z', axes.alleyZ],
      ];
  const candidates: [number, number][] = [];
  for (const [axis, fixed] of candidateLines) {
    for (const travel of [-half + 12, half - 12]) {
      candidates.push(axis === 'x' ? [fixed, travel] : [travel, fixed]);
    }
  }
  for (const [axis, fixed] of candidateLines) {
    for (let travel = -half + 24; travel <= half - 24; travel += 12) {
      candidates.push(axis === 'x' ? [fixed, travel] : [travel, fixed]);
    }
  }

  const result: SpawnPoint[] = [];
  for (const [rawX, rawZ] of candidates) {
    if (result.length >= 4) break;
    const x = Math.round(rawX / GRID) * GRID;
    const z = Math.round(rawZ / GRID) * GRID;
    if (result.some(([px, , pz]) => Math.hypot(x - px, z - pz) < 40)) continue;
    if (landmarks.some((landmark) =>
      pointAabbDistance(x, z, aabbOf(landmark.cx, landmark.cz, landmark.width, landmark.depth))
        < DENSE_WORLD_V5_PLAYER_CLEAR)) continue;
    result.push([x, 0, z]);
  }
  if (result.length !== 4) {
    throw new Error(`${def.id}: dense street graph produced ${result.length}/4 player spawns`);
  }
  return result;
}

/**
 * Produce an aligned, collision-authoritative town plan for the v5 proof.
 *
 * Normal maps use one 16m north/south street, one 16m east/west street and
 * two connected 7m service alleys.  They divide the stage into nine real city
 * blocks.  Buildings are packed from street corners on the existing 2m grid
 * with a measured 6m gap; this is deterministic block planning, not random
 * scattering.  The central authored hero building stays first and at origin.
 *
 * Abbey maps retain the four gate axes and pack a castle town only into the
 * four exterior corner wards.  Every returned footprint is a real BoxSpec
 * building generated by the normal collider path, so Blender never advertises
 * collisionless doors or cover.
 */
function buildDenseWorldV5Plan(
  def: StageDef,
  playerSpawns: SpawnPoint[],
  botSpawns: SpawnPoint[],
  landmarks: LandmarkPlacement[],
): DistrictPlacement[] {
  const authored = def.recipe?.buildings ?? [];
  if (authored.length === 0) return [];
  const half = def.size / 2;
  const abbeyStage = authored[0] === 'abbey';
  const vocabulary: BuildingKind[] = abbeyStage
    ? def.id === 'z04'
      ? ['cathedral', 'fortress', 'villa']
      : ['villa', 'cathedral', 'fortress']
    : [...authored];
  const centralKind: BuildingKind = abbeyStage
    ? 'abbey'
    : [...authored].sort((a, b) => {
        const [aw, ad] = getBuildingFootprint(a, 0);
        const [bw, bd] = getBuildingFootprint(b, 0);
        return bw * bd - aw * ad;
      })[0]!;

  const placements: DistrictPlacement[] = [];
  const occupied: Aabb[] = landmarks.map((landmark) =>
    aabbOf(landmark.cx, landmark.cz, landmark.width, landmark.depth));
  const reservedApproaches = landmarks.map((landmark) => approachAabb(landmark.approach));
  const stageArea = def.size * def.size;
  // Two castle-scale footprints replace many ordinary lots.  Fourteen total
  // districts keeps even the 288m/300m proof maps legibly urban while the
  // mandatory six-metre firebreaks and both entrance streets remain open.
  // Kairou's paired 114x74 / 88x80 heroes cover the same measured area as
  // several normal lots; thirteen total districts retain the 24.5% density
  // contract without squeezing a fake building into their civic plaza.
  const minimumTotalDistricts = abbeyStage
    ? 9
    : def.id === 'kairou' || def.size < 300
      ? 13
      : 14;
  const minimumPlanDistricts = Math.max(0, minimumTotalDistricts - landmarks.length);
  let occupiedArea = landmarks.reduce(
    (sum, landmark) => sum + landmark.width * landmark.depth,
    0,
  );

  const tryPlacement = (
    kind: BuildingKind,
    cx: number,
    cz: number,
    rot: number,
  ): boolean => {
    const [width, depth] = getBuildingFootprint(kind, rot);
    if ((occupiedArea + width * depth) / stageArea > DENSE_WORLD_V5_MAX_COVERAGE) {
      return false;
    }
    if (Math.abs(cx) + width / 2 > half - 4 || Math.abs(cz) + depth / 2 > half - 4) {
      return false;
    }
    const footprint = aabbOf(cx, cz, width, depth);
    if (occupied.some((other) => overlaps(other, footprint, DENSE_WORLD_V5_BUILDING_GAP))) {
      return false;
    }
    if (reservedApproaches.some((route) => overlaps(route, footprint, 2))) return false;
    if (playerSpawns.some(([sx, , sz]) =>
      pointAabbDistance(sx, sz, footprint) < DENSE_WORLD_V5_PLAYER_CLEAR)) {
      return false;
    }
    if (botSpawns.some(([sx, , sz]) =>
      pointAabbDistance(sx, sz, footprint) < DENSE_WORLD_V5_BOT_CLEAR)) {
      return false;
    }
    placements.push({ kind, cx, cz, rot, width, depth });
    occupied.push(footprint);
    occupiedArea += width * depth;
    return true;
  };

  // All existing central placements already pass the spawn contract.  Keep
  // this first for minimap/Blender consumers and for the origin landmark test.
  if (!abbeyStage && def.id !== 'kairou' && !tryPlacement(centralKind, 0, 0, def.seed & 3)) {
    throw new Error(`${def.id}: v5 central district could not be placed around landmarks`);
  }

  const edgeInset = 4;
  let xBands: [number, number][];
  let zBands: [number, number][];
  if (abbeyStage) {
    // The abbey footprint is 124x100m.  A 9m shoulder outside each wall keeps
    // the east/west and north/south gate approaches visibly and physically
    // open while leaving four substantial town wards.
    xBands = [
      [-half + edgeInset, -62 - 9],
      [62 + 9, half - edgeInset],
    ];
    zBands = [
      [-half + edgeInset, -50 - 9],
      [50 + 9, half - edgeInset],
    ];
  } else {
    // Offset the primary cross so the origin hero building does not block it.
    // The secondary axes are narrower alleys and connect all nine blocks.
    const { primaryX, primaryZ, alleyX, alleyZ } = denseWorldStreetAxes(def, landmarks);
    const low = -half + edgeInset;
    const high = half - edgeInset;
    xBands = [
      [low, primaryX - DENSE_WORLD_V5_PRIMARY_STREET_HALF],
      [primaryX + DENSE_WORLD_V5_PRIMARY_STREET_HALF, alleyX - DENSE_WORLD_V5_ALLEY_HALF],
      [alleyX + DENSE_WORLD_V5_ALLEY_HALF, high],
    ];
    zBands = [
      [low, alleyZ - DENSE_WORLD_V5_ALLEY_HALF],
      [alleyZ + DENSE_WORLD_V5_ALLEY_HALF, primaryZ - DENSE_WORLD_V5_PRIMARY_STREET_HALF],
      [primaryZ + DENSE_WORLD_V5_PRIMARY_STREET_HALF, high],
    ];
  }

  const blocks: DenseWorldBlock[] = [];
  for (const [ix, [minX, maxX]] of xBands.entries()) {
    for (const [iz, [minZ, maxZ]] of zBands.entries()) {
      if (maxX - minX < 22 || maxZ - minZ < 22) continue;
      blocks.push({
        ix,
        iz,
        minX,
        maxX,
        minZ,
        maxZ,
        cx: (minX + maxX) / 2,
        cz: (minZ + maxZ) / 2,
      });
    }
  }
  // Fill the first-spawn vista before rear wards.  Ties are stable by band,
  // giving exact JSON determinism across engines.
  const [firstSpawnX, , firstSpawnZ] = playerSpawns[0]!;
  blocks.sort((a, b) =>
    Math.hypot(a.cx - firstSpawnX, a.cz - firstSpawnZ)
      - Math.hypot(b.cx - firstSpawnX, b.cz - firstSpawnZ)
    || a.ix - b.ix
    || a.iz - b.iz);

  const targetArea = stageArea * DENSE_WORLD_V5_TARGET_COVERAGE;
  const compactVocabulary = [...vocabulary].sort((a, b) => {
    const [aw, ad] = getBuildingFootprint(a, 0);
    const [bw, bd] = getBuildingFootprint(b, 0);
    return aw * ad - bw * bd;
  });
  let serial = 0;
  // One placement per block per pass keeps density distributed.  Inside a
  // block, the row-major corner pack creates 6m walkable alleys and avoids the
  // inaccessible pockets produced by arbitrary centre scattering.
  for (
    let pass = 0;
    pass < 20 && (occupiedArea < targetArea || placements.length < minimumPlanDistricts);
    pass += 1
  ) {
    for (const block of blocks) {
      if (occupiedArea >= targetArea && placements.length >= minimumPlanDistricts) break;
      let placedInBlock = false;
      const activeVocabulary = placements.length < minimumPlanDistricts
        ? compactVocabulary
        : vocabulary;
      for (let choice = 0; choice < activeVocabulary.length * 4 && !placedInBlock; choice += 1) {
        const kind = activeVocabulary[(serial + choice) % activeVocabulary.length]!;
        const rot = (def.seed + serial + choice) & 3;
        const [width, depth] = getBuildingFootprint(kind, rot);
        const minX = Math.ceil((block.minX + width / 2) / GRID) * GRID;
        const maxX = Math.floor((block.maxX - width / 2) / GRID) * GRID;
        const minZ = Math.ceil((block.minZ + depth / 2) / GRID) * GRID;
        const maxZ = Math.floor((block.maxZ - depth / 2) / GRID) * GRID;
        if (minX > maxX || minZ > maxZ) continue;
        const xValues: number[] = [];
        const zValues: number[] = [];
        for (let x = minX; x <= maxX; x += GRID) xValues.push(x);
        for (let z = minZ; z <= maxZ; z += GRID) zValues.push(z);
        if ((block.ix + pass) & 1) xValues.reverse();
        if ((block.iz + pass) & 1) zValues.reverse();
        for (const z of zValues) {
          for (const x of xValues) {
            if (tryPlacement(kind, x, z, rot)) {
              placedInBlock = true;
              break;
            }
          }
          if (placedInBlock) break;
        }
      }
      serial += 1;
    }
  }

  const coverage = occupiedArea / (def.size * def.size);
  if (placements.length < minimumPlanDistricts) {
    throw new Error(
      `${def.id}: v5 placed ${placements.length}/${minimumPlanDistricts} ordinary districts`,
    );
  }
  if (coverage < DENSE_WORLD_V5_TARGET_COVERAGE || coverage > DENSE_WORLD_V5_MAX_COVERAGE) {
    throw new Error(
      `${def.id}: v5 district coverage ${(coverage * 100).toFixed(2)}% outside `
      + `${(DENSE_WORLD_V5_TARGET_COVERAGE * 100).toFixed(1)}-`
      + `${(DENSE_WORLD_V5_MAX_COVERAGE * 100).toFixed(1)}%`,
    );
  }
  return placements;
}

/** Place bots on the measured street graph after the dense colliders exist. */
function buildDenseWorldV5BotSpawns(
  def: StageDef,
  playerSpawns: SpawnPoint[],
  districts: DistrictPlacement[],
  landmarks: LandmarkPlacement[],
): SpawnPoint[] {
  const half = def.size / 2;
  const abbeyStage = def.recipe?.buildings[0] === 'abbey';
  const candidates: [number, number][] = [];
  const appendLine = (axis: 'x' | 'z', fixed: number) => {
    for (let travel = -half + 12; travel <= half - 12; travel += 10) {
      candidates.push(axis === 'x' ? [fixed, travel] : [travel, fixed]);
    }
  };
  if (abbeyStage) {
    appendLine('x', 0);
    appendLine('z', 0);
    appendLine('x', -half * 0.72);
    appendLine('x', half * 0.72);
    appendLine('z', -half * 0.72);
    appendLine('z', half * 0.72);
  } else {
    const { primaryX, primaryZ, alleyX, alleyZ } = denseWorldStreetAxes(def, landmarks);
    appendLine('x', primaryX);
    appendLine('z', primaryZ);
    appendLine('x', alleyX);
    appendLine('z', alleyZ);
  }

  const result: SpawnPoint[] = [];
  for (const [x, z] of candidates) {
    if (result.length >= def.botCount) break;
    if (playerSpawns.some(([px, , pz]) => Math.hypot(x - px, z - pz) < 16)) continue;
    if (result.some(([bx, , bz]) => Math.hypot(x - bx, z - bz) < 5)) continue;
    const blocked = districts.some((district) =>
      pointAabbDistance(
        x,
        z,
        aabbOf(district.cx, district.cz, district.width, district.depth),
      ) < DENSE_WORLD_V5_BOT_CLEAR);
    if (blocked) continue;
    result.push([Math.round(x / GRID) * GRID, 0, Math.round(z / GRID) * GRID]);
  }
  if (result.length !== def.botCount) {
    throw new Error(`${def.id}: dense street graph produced ${result.length}/${def.botCount} bot spawns`);
  }
  return result;
}

/**
 * Split one coarse Kairou district footprint into a base plus one real upper
 * merchant volume.  The support is selected from the existing highest solid
 * roof/tower box and the new collider is fully contained by that support in
 * X/Z, so the Blender skyline never advertises a projectile-through building.
 */
function buildKairouUrbanVolume(
  district: DistrictPlacement,
  districtIndex: number,
  baseBoxes: BoxSpec[],
  palette: StagePalette,
): BoxSpec {
  const roofTop = Math.max(...baseBoxes.map((box) => box.y + box.h / 2));
  const supports = baseBoxes
    .filter((box) =>
      Math.abs(box.y + box.h / 2 - roofTop) < 1e-6
      && box.w >= 4
      && box.d >= 4)
    .sort((a, b) => b.w * b.d - a.w * a.d || a.x - b.x || a.z - b.z);
  const support = supports[districtIndex % Math.max(1, supports.length)];
  if (!support) {
    throw new Error(`kairou: ${district.kind} at ${district.cx},${district.cz} has no upper support`);
  }
  const narrowSupport = Math.min(support.w, support.d) <= 6;
  const width = Math.min(
    support.w - 0.6,
    Math.max(3.8, support.w * (narrowSupport ? 0.82 : 0.52)),
  );
  const depth = Math.min(
    support.d - 0.6,
    Math.max(3.8, support.d * (narrowSupport ? 0.82 : 0.52)),
  );
  const height = narrowSupport
    ? 7.2 + (districtIndex % 3) * 0.8
    : 5.8 + (districtIndex % 3) * 0.9;
  const offsetRoomX = Math.max(0, (support.w - width) / 2 - 0.3);
  const offsetRoomZ = Math.max(0, (support.d - depth) / 2 - 0.3);
  const offsetX = (districtIndex & 1 ? -1 : 1) * offsetRoomX * 0.42;
  const offsetZ = (districtIndex & 2 ? -1 : 1) * offsetRoomZ * 0.34;
  return {
    x: support.x + offsetX,
    y: roofTop + height / 2,
    z: support.z + offsetZ,
    w: width,
    h: height,
    d: depth,
    color: palette.obstacle,
    emissive: false,
    structural: true,
    district: district.kind,
    urbanVolume: true,
  };
}

// ── 建造物アーキタイプ実装 ─────────────────────────────────────────────

/**
 * 直階段ボックス列を生成するヘルパー。
 * @param cx,cz  ワールド建造物中心
 * @param rot    回転ステップ(0-3)
 * @param lxStart,lzStart ローカル開始座標(step 0 の中心)
 * @param lxStep,lzStep  各ステップごとのローカル移動量(どちらか一方が 0.8m)
 * @param yBotStart  最初の段の底 Y
 * @param lw,ld  各段の幅/奥行き(m)
 * @param steps  段数
 * @param color  マテリアル色
 * 蹴上は固定 0.3m(autostep 0.4m 未満)。
 */
function buildStair(
  cx: number,
  cz: number,
  rot: number,
  lxStart: number,
  lzStart: number,
  lxStep: number,
  lzStep: number,
  yBotStart: number,
  lw: number,
  ld: number,
  steps: number,
  color: string,
): BoxSpec[] {
  const result: BoxSpec[] = [];
  for (let i = 0; i < steps; i++) {
    result.push(
      pb(cx, cz, rot, lxStart + i * lxStep, lzStart + i * lzStep, yBotStart + i * 0.3, lw, 0.3, ld, color),
    );
  }
  return result;
}

/**
 * アリーナ/体育館 (44×30×10m)
 * 短辺2面に10m×5.5m 開口。2Fキャットウォーク + 支柱6本。
 */
function buildArena(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const e = p.emissiveAccent;
  return [
    pb(cx, cz, rot, 0, 0, -0.25, 44, 0.5, 30, c), // 床(上面 y=+0.25m → autostep0.4 で入場可)
    pb(cx, cz, rot, 0, -15, 0, 44, 10, 1, c), // N長辺壁
    pb(cx, cz, rot, 0, +15, 0, 44, 10, 1, c), // S長辺壁
    // W短辺壁: 左フランク/右フランク/まぐさ(開口 10m×5.5m)
    pb(cx, cz, rot, -22, -10, 0, 1, 10, 10, c),
    pb(cx, cz, rot, -22, +10, 0, 1, 10, 10, c),
    pb(cx, cz, rot, -22, 0, 5.5, 1, 4.5, 10, c),
    // E短辺壁
    pb(cx, cz, rot, +22, -10, 0, 1, 10, 10, c),
    pb(cx, cz, rot, +22, +10, 0, 1, 10, 10, c),
    pb(cx, cz, rot, +22, 0, 5.5, 1, 4.5, 10, c),
    pb(cx, cz, rot, 0, 0, 10, 44, 0.5, 30, c), // 屋根
    // 2F キャットウォーク (y=5)
    pb(cx, cz, rot, 0, -11, 5, 40, 0.5, 8, ac, e),
    pb(cx, cz, rot, 0, +11, 5, 40, 0.5, 8, ac, e),
    // 支柱 × 6 (V31: structural=キャットウォークの支持材なので破壊不可)
    { ...pb(cx, cz, rot, -13, -11, 0, 1, 5, 1, c), structural: true },
    { ...pb(cx, cz, rot, 0, -11, 0, 1, 5, 1, c), structural: true },
    { ...pb(cx, cz, rot, +13, -11, 0, 1, 5, 1, c), structural: true },
    { ...pb(cx, cz, rot, -13, +11, 0, 1, 5, 1, c), structural: true },
    { ...pb(cx, cz, rot, 0, +11, 0, 1, 5, 1, c), structural: true },
    { ...pb(cx, cz, rot, +13, +11, 0, 1, 5, 1, c), structural: true },
    // ── キャットウォーク登坂階段(N壁内側沿い, 東端 lx+0→+14, 18段×0.3m蹴上) ──
    // 上面y=5.4m で catwalk 上面 y=5.5m まで autostep 0.1m の1ステップ
    ...buildStair(cx, cz, rot, +0.4, -14, 0.8, 0, 0, 0.8, 2, 18, c),
    // ── キャットウォーク登坂階段(S壁内側沿い, 西端 lx-0→-14, 18段×0.3m蹴上) ──
    // N側と左右対称。上面y=5.4m → catwalk 上面 y=5.5m autostep 0.1m で乗れる
    ...buildStair(cx, cz, rot, -0.4, +14, -0.8, 0, 0, 0.8, 2, 18, c),
  ];
}

/**
 * 格納庫 (40×22×10m)
 * 前面(W)全開口。奥にコンテナ積み5個。
 */
function buildHangar(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  return [
    pb(cx, cz, rot, 0, 0, -0.25, 40, 0.5, 22, c), // 床(上面 y=+0.25m → autostep0.4 で入場可)
    pb(cx, cz, rot, +20, 0, 0, 1, 10, 22, c), // バック壁
    pb(cx, cz, rot, 0, -11, 0, 40, 10, 1, c), // N壁
    pb(cx, cz, rot, 0, +11, 0, 40, 10, 1, c), // S壁
    { ...pb(cx, cz, rot, 0, 0, 10, 40, 0.5, 22, c), structural: true, roofMonitorSupport: true }, // 屋根
    // コンテナ群
    pb(cx, cz, rot, +10, -4, 0, 5, 4, 5, c),
    pb(cx, cz, rot, +10, -4, 4, 5, 4, 5, c),
    pb(cx, cz, rot, +10, +4, 0, 5, 4, 5, c),
    pb(cx, cz, rot, +10, +4, 4, 5, 3, 5, c),
    pb(cx, cz, rot, +2, -4, 0, 5, 4, 5, c),
  ];
}

/**
 * 多層タワー (22×22×16m, 3フロア + コーナーピラー)
 * 4隅ピラーに挟まれたオープンフロア構造。
 * 地上から各フロアは BO3 移動(ジャンプ+マントル)でアクセス可能。
 */
function buildTower(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const e = p.emissiveAccent;
  return [
    // フロアスラブ (G/1F/2F)
    pb(cx, cz, rot, 0, 0, -0.25, 16, 0.5, 16, c), // G床(上面 y=+0.25m → autostep0.4 で入場可)
    pb(cx, cz, rot, 0, 0, 6, 16, 0.5, 16, ac, e),
    pb(cx, cz, rot, 0, 0, 12, 16, 0.5, 16, c),
    // 4隅コーナーピラー (高さ16m)
    pb(cx, cz, rot, -7, -7, 0, 2, 16, 2, c),
    pb(cx, cz, rot, +7, -7, 0, 2, 16, 2, c),
    pb(cx, cz, rot, -7, +7, 0, 2, 16, 2, c),
    pb(cx, cz, rot, +7, +7, 0, 2, 16, 2, c),
    // N/S 低遮蔽バリア × 各2段 (プレイヤーが伏せて隠れる)
    pb(cx, cz, rot, 0, -7.5, 0.5, 12, 1, 1, c),
    pb(cx, cz, rot, 0, +7.5, 0.5, 12, 1, 1, c),
    pb(cx, cz, rot, 0, -7.5, 6.5, 12, 1, 1, c),
    pb(cx, cz, rot, 0, +7.5, 6.5, 12, 1, 1, c),
    // ── 登坂階段 A: 東外周, G→1F (y=0→6.5m, 21段×0.3m蹴上) ──
    // 上面y=6.3m で 1F 上面 y=6.5m まで autostep 0.2m の1ステップ
    ...buildStair(cx, cz, rot, +8.8, +6.6, 0, -0.72, 0, 2, 0.8, 21, c),
    // ── 登坂階段 B: 西外周, 1F→2F (y=6.2→12.5m, 21段×0.3m蹴上) ──
    // yBotStart=6.2 → step0 上面=6.5m(1F床面合わせ), step20 上面=12.5m(2F床面ちょうど)
    ...buildStair(cx, cz, rot, -8.8, +6.6, 0, -0.72, 6.2, 2, 0.8, 21, c),
  ];
}

/**
 * 倉庫街ブロック (56×14×7m × 2連 + 貫通通路)
 * 建物 A(lx=-14) + 建物 B(lx=+14) + 中央通路。
 * 両端面は開口(入退場自由)。通路幅 4m × 高 7m。
 */
function buildWarehouse(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  return [
    // 倉庫 A (lx=-14 中心, 24m長×12m幅×7m高)
    pb(cx, cz, rot, -14, -6, 0, 24, 7, 1, c),
    pb(cx, cz, rot, -14, +6, 0, 24, 7, 1, c),
    pb(cx, cz, rot, -26, 0, 0, 1, 7, 12, c), // A 奥端壁
    { ...pb(cx, cz, rot, -14, 0, 7, 24, 0.5, 12, c), structural: true, roofMonitorSupport: true }, // A 屋根
    // 倉庫 B (lx=+14 中心)
    pb(cx, cz, rot, +14, -6, 0, 24, 7, 1, c),
    pb(cx, cz, rot, +14, +6, 0, 24, 7, 1, c),
    pb(cx, cz, rot, +26, 0, 0, 1, 7, 12, c),
    { ...pb(cx, cz, rot, +14, 0, 7, 24, 0.5, 12, c), structural: true, roofMonitorSupport: true },
    // 貫通通路 (A-B 間, 4m幅)
    pb(cx, cz, rot, 0, -2.5, 0, 6, 3, 1, c),
    pb(cx, cz, rot, 0, +2.5, 0, 6, 3, 1, c),
    pb(cx, cz, rot, 0, 0, 3, 6, 0.5, 5, c),
    // 内部シェルフ(遮蔽)
    pb(cx, cz, rot, -18, -3, 0, 4, 3, 3, c),
    pb(cx, cz, rot, -10, +3, 0, 4, 3, 3, c),
    pb(cx, cz, rot, +18, -3, 0, 4, 3, 3, c),
    pb(cx, cz, rot, +10, +3, 0, 4, 3, 3, c),
  ];
}

/**
 * 神殿/大聖堂ホール (36×22×14m)
 * 両端に 8m×10m 開口。列柱 8 本 + 祭壇。
 */
function buildCathedral(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const e = p.emissiveAccent;
  return [
    pb(cx, cz, rot, 0, 0, -0.25, 36, 0.5, 22, c), // 床(上面 y=+0.25m → autostep0.4 で入場可)
    pb(cx, cz, rot, 0, -11, 0, 36, 14, 1, c), // N長辺壁
    pb(cx, cz, rot, 0, +11, 0, 36, 14, 1, c), // S長辺壁
    // W短辺壁 (開口 8m×10m)
    pb(cx, cz, rot, -18, -7.5, 0, 1, 14, 7, c),
    pb(cx, cz, rot, -18, +7.5, 0, 1, 14, 7, c),
    pb(cx, cz, rot, -18, 0, 10, 1, 4, 8, c),
    // E短辺壁 (同)
    pb(cx, cz, rot, +18, -7.5, 0, 1, 14, 7, c),
    pb(cx, cz, rot, +18, +7.5, 0, 1, 14, 7, c),
    pb(cx, cz, rot, +18, 0, 10, 1, 4, 8, c),
    pb(cx, cz, rot, 0, 0, 14, 36, 0.5, 22, c), // 屋根
    // 列柱 4 ペア (N/S, y=0-12)
    pb(cx, cz, rot, -10, -7, 0, 2, 12, 2, ac, e),
    pb(cx, cz, rot, -10, +7, 0, 2, 12, 2, ac, e),
    pb(cx, cz, rot, -3, -7, 0, 2, 12, 2, ac, e),
    pb(cx, cz, rot, -3, +7, 0, 2, 12, 2, ac, e),
    pb(cx, cz, rot, +4, -7, 0, 2, 12, 2, ac, e),
    pb(cx, cz, rot, +4, +7, 0, 2, 12, 2, ac, e),
    pb(cx, cz, rot, +11, -7, 0, 2, 12, 2, ac, e),
    pb(cx, cz, rot, +11, +7, 0, 2, 12, 2, ac, e),
    // 祭壇台座 + オブジェ (台座は structural=true: 破壊すると上部オブジェが浮くため)
    { ...pb(cx, cz, rot, +14, 0, 0, 8, 1.5, 6, c), structural: true },
    pb(cx, cz, rot, +14, 0, 1.5, 2, 3, 2, ac, e),
  ];
}

/** 低層軍用バンカー。内部2ルートと実際に登れる屋上射点を持つ。 */
function buildBunker(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  return [
    pb(cx, cz, rot, 0, 0, -0.2, 38, 0.4, 26, c),
    pb(cx, cz, rot, 0, -12.5, 0, 38, 5.8, 1, c),
    pb(cx, cz, rot, 0, 12.5, 0, 38, 5.8, 1, c),
    pb(cx, cz, rot, 18.5, -8.5, 0, 1, 5.8, 8, c),
    pb(cx, cz, rot, 18.5, 8.5, 0, 1, 5.8, 8, c),
    pb(cx, cz, rot, 18.5, 0, 4.2, 1, 1.6, 9, ac, p.emissiveAccent),
    pb(cx, cz, rot, -18.5, -8.5, 0, 1, 5.8, 8, c),
    pb(cx, cz, rot, -18.5, 8.5, 0, 1, 5.8, 8, c),
    pb(cx, cz, rot, -18.5, 0, 4.2, 1, 1.6, 9, ac, p.emissiveAccent),
    pb(cx, cz, rot, 0, 0, 5.8, 38, 0.6, 26, c),
    // 中央壁は左右に4mの抜けを残し、近距離の回り込みを成立させる。
    pb(cx, cz, rot, -8, 0, 0, 12, 3.2, 0.8, c),
    pb(cx, cz, rot, 8, 0, 0, 12, 3.2, 0.8, c),
    pb(cx, cz, rot, 0, -6, 0, 4.2, 1.2, 2.2, ac),
    pb(cx, cz, rot, 0, 6, 0, 4.2, 1.2, 2.2, ac),
    // 外階段から屋上へ連続アクセス。
    ...buildStair(cx, cz, rot, -15, 14, 0.85, 0, 0, 0.85, 2.2, 21, c),
    pb(cx, cz, rot, 0, -11.6, 6.1, 18, 1.0, 0.6, ac),
    pb(cx, cz, rot, 0, 11.6, 6.1, 18, 1.0, 0.6, ac),
  ].map((box) => ({ ...box, structural: true }));
}

/** 空港・港・都市で使う横長ターミナル。大ホール、庇、外周デッキの3射線。 */
function buildTerminal(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const boxes: BoxSpec[] = [
    pb(cx, cz, rot, 0, 0, -0.2, 58, 0.4, 24, c),
    pb(cx, cz, rot, 0, -11.5, 0, 58, 8, 1, c),
    pb(cx, cz, rot, 0, 11.5, 0, 58, 2.1, 1, c),
    { ...pb(cx, cz, rot, 0, 0, 8, 58, 0.5, 24, c), roofMonitorSupport: true },
    // 両端は中央入口を残したサービス棟。
    pb(cx, cz, rot, -28.5, -8, 0, 1, 8, 7, c),
    pb(cx, cz, rot, -28.5, 8, 0, 1, 8, 7, c),
    pb(cx, cz, rot, 28.5, -8, 0, 1, 8, 7, c),
    pb(cx, cz, rot, 28.5, 8, 0, 1, 8, 7, c),
    pb(cx, cz, rot, -28.5, 0, 5.5, 1, 2.5, 9, ac, p.emissiveAccent),
    pb(cx, cz, rot, 28.5, 0, 5.5, 1, 2.5, 9, ac, p.emissiveAccent),
    // ホール内のカウンター列は腰高で、射線とスライドルートを両立。
    pb(cx, cz, rot, -15, -4, 0, 9, 1.1, 1.4, ac),
    pb(cx, cz, rot, 0, 3.5, 0, 10, 1.1, 1.4, ac),
    pb(cx, cz, rot, 15, -4, 0, 9, 1.1, 1.4, ac),
    // 南側の屋外プラットフォームと庇。
    pb(cx, cz, rot, 0, 15, 0, 54, 0.35, 6, c),
    pb(cx, cz, rot, 0, 14.5, 5.5, 50, 0.35, 5, ac),
  ];
  for (const x of [-22, -11, 0, 11, 22]) boxes.push(pb(cx, cz, rot, x, 13.2, 0, 0.7, 5.5, 0.7, c));
  return boxes.map((box) => ({ ...box, structural: true }));
}

/** 製油・採掘地区。地上3レーンと登れる配管キャットウォーク。 */
function buildRefinery(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const boxes: BoxSpec[] = [
    pb(cx, cz, rot, -13, -8, 0, 10, 4.8, 10, c),
    pb(cx, cz, rot, 13, 8, 0, 10, 6.5, 10, c),
    pb(cx, cz, rot, 0, 0, 6, 42, 0.55, 5, ac, p.emissiveAccent),
    pb(cx, cz, rot, -20, 0, 0, 1.2, 6, 5, c),
    pb(cx, cz, rot, 20, 0, 0, 1.2, 6, 5, c),
    pb(cx, cz, rot, 0, -15, 0, 42, 1.2, 1.2, ac),
    pb(cx, cz, rot, 0, 15, 0, 42, 1.2, 1.2, ac),
    pb(cx, cz, rot, 0, -7.5, 2.8, 38, 0.55, 0.8, ac, p.emissiveAccent),
    pb(cx, cz, rot, 0, 7.5, 3.8, 38, 0.55, 0.8, ac, p.emissiveAccent),
    pb(cx, cz, rot, -8, 0, 0, 2, 1.2, 7, c),
    pb(cx, cz, rot, 8, 0, 0, 2, 1.2, 7, c),
    ...buildStair(cx, cz, rot, -18, 3.4, 0.85, 0, 0, 0.85, 2, 21, c),
  ];
  for (const x of [-16, -8, 0, 8, 16]) boxes.push(pb(cx, cz, rot, x, 0, 0, 0.7, 6, 0.7, c));
  return boxes.map((box) => ({ ...box, structural: true }));
}

/** 近未来邸宅。L字棟、開放中庭、二階バルコニーを実プレイ可能にする。 */
function buildVilla(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  return [
    pb(cx, cz, rot, -8, -7, -0.2, 28, 0.4, 18, c),
    pb(cx, cz, rot, 13, 7, -0.2, 14, 0.4, 16, c),
    pb(cx, cz, rot, -8, -15.5, 0, 28, 8, 1, c),
    pb(cx, cz, rot, -21.5, -7, 0, 1, 8, 18, c),
    pb(cx, cz, rot, 5.5, -11, 0, 1, 8, 9, c),
    pb(cx, cz, rot, 5.5, 2, 0, 1, 3.2, 7, c),
    // 南面は二つの4m開口を残して実壁を追加する。旧構成は28mの屋根下が
    // ほぼ全面開放で、邸宅ではなく建設途中の柱梁に見えていた。
    pb(cx, cz, rot, -16.5, 1.5, 0, 11, 8, 1, c),
    pb(cx, cz, rot, -4.5, 1.5, 0, 5, 8, 1, c),
    pb(cx, cz, rot, 13, 14.5, 0, 14, 6, 1, c),
    pb(cx, cz, rot, 19.5, 7, 0, 1, 6, 16, c),
    // 東翼北面も中央4mを玄関として空け、左右を床から屋根へ接続する。
    pb(cx, cz, rot, 9, -0.5, 0, 4, 6, 1, c),
    pb(cx, cz, rot, 17, -0.5, 0, 4, 6, 1, c),
    pb(cx, cz, rot, -8, -7, 8, 28, 0.5, 18, c),
    pb(cx, cz, rot, 13, 7, 6, 14, 0.5, 16, c),
    // 上階のカーテンウォール。床・屋根へ実際に接続し、中央の引戸開口を残す。
    { ...pb(cx, cz, rot, -16.5, 1.55, 4.5, 9, 3.45, 0.28, ac), glazing: true },
    { ...pb(cx, cz, rot, -5.0, 1.55, 4.5, 6, 3.45, 0.28, ac), glazing: true },
    { ...pb(cx, cz, rot, 2.5, 1.55, 4.5, 5, 3.45, 0.28, ac), glazing: true },
    { ...pb(cx, cz, rot, 9.0, -0.55, 3.25, 4, 2.75, 0.28, ac), glazing: true },
    { ...pb(cx, cz, rot, 17.0, -0.55, 3.25, 4, 2.75, 0.28, ac), glazing: true },
    pb(cx, cz, rot, -2, 7, 4.2, 20, 0.5, 5, ac, p.emissiveAccent),
    // 二階バルコニーの実コライダー付き腰壁。視覚だけの手すりではないため、
    // プレイヤー／BOT／弾道の読みに食い違いを作らない。
    { ...pb(cx, cz, rot, -2, 9.4, 4.65, 20, 1.05, 0.3, ac), glazing: true },
    { ...pb(cx, cz, rot, -11.85, 7, 4.65, 0.3, 1.05, 5, ac), glazing: true },
    { ...pb(cx, cz, rot, 7.85, 7, 4.65, 0.3, 1.05, 5, ac), glazing: true },
    // 屋上端部のパラペット。浮いた平板を建築的な屋根面へ変える。
    pb(cx, cz, rot, -8, -15.35, 8.25, 28, 1.0, 0.3, c),
    pb(cx, cz, rot, -21.35, -7, 8.25, 0.3, 1.0, 18, c),
    pb(cx, cz, rot, 5.35, -7, 8.25, 0.3, 1.0, 18, c),
    pb(cx, cz, rot, 13, 14.35, 6.25, 14, 1.0, 0.3, c),
    pb(cx, cz, rot, 19.35, 7, 6.25, 0.3, 1.0, 16, c),
    pb(cx, cz, rot, -1, 10, 0, 8, 1.1, 1.2, ac),
    pb(cx, cz, rot, 8, 4, 0, 1.2, 1.2, 7, ac),
    ...buildStair(cx, cz, rot, -12, 4.2, 0.8, 0, 0, 0.8, 2.2, 15, c),
  ].map((box) => ({ ...box, structural: true }));
}

/** 寺社・温泉用の開放楼閣。回廊と二層の射点を持つ。 */
function buildPagoda(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const boxes: BoxSpec[] = [
    pb(cx, cz, rot, 0, 0, -0.15, 34, 0.3, 34, c),
    pb(cx, cz, rot, 0, 0, 4.5, 30, 0.45, 30, ac),
    pb(cx, cz, rot, 0, 0, 9, 22, 0.5, 22, c),
    pb(cx, cz, rot, 0, 0, 12.2, 27, 0.35, 27, ac, p.emissiveAccent),
    pb(cx, cz, rot, 0, -8.5, 0, 16, 3.2, 1, c),
    pb(cx, cz, rot, 0, 8.5, 0, 16, 3.2, 1, c),
    pb(cx, cz, rot, -8.5, 0, 0, 1, 3.2, 16, c),
    pb(cx, cz, rot, 8.5, 0, 0, 1, 3.2, 16, c),
    ...buildStair(cx, cz, rot, -14, 14.5, 0.85, 0, 0, 0.85, 2.1, 16, c),
    ...buildStair(cx, cz, rot, 14, -7.8, -0.85, 0, 4.4, 0.85, 2.1, 17, c),
  ];
  for (const x of [-13, -5, 5, 13]) {
    for (const z of [-13, 13]) boxes.push(pb(cx, cz, rot, x, z, 0, 0.8, 12, 0.8, c));
  }
  return boxes.map((box) => ({ ...box, structural: true }));
}

/** 丘陵・峡谷・火口用の要塞。二つの門、城壁上、中央広場が循環する。 */
function buildFortress(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const boxes: BoxSpec[] = [
    pb(cx, cz, rot, 0, -18, 0, 20, 6, 1.4, c),
    pb(cx, cz, rot, -21, -18, 0, 12, 6, 1.4, c),
    pb(cx, cz, rot, 21, -18, 0, 12, 6, 1.4, c),
    pb(cx, cz, rot, 0, 18, 0, 20, 6, 1.4, c),
    pb(cx, cz, rot, -21, 18, 0, 12, 6, 1.4, c),
    pb(cx, cz, rot, 21, 18, 0, 12, 6, 1.4, c),
    pb(cx, cz, rot, -27, 0, 0, 1.4, 6, 36, c),
    pb(cx, cz, rot, 27, 0, 0, 1.4, 6, 36, c),
    pb(cx, cz, rot, 0, -17, 5.7, 54, 0.55, 3.5, ac),
    pb(cx, cz, rot, 0, 17, 5.7, 54, 0.55, 3.5, ac),
    pb(cx, cz, rot, -25.5, 0, 5.7, 3.5, 0.55, 30, ac),
    pb(cx, cz, rot, 25.5, 0, 5.7, 3.5, 0.55, 30, ac),
    pb(cx, cz, rot, 0, 0, 0, 12, 1.2, 6, ac, p.emissiveAccent),
    ...buildStair(cx, cz, rot, -22, 14.1, 0.85, 0, 0, 0.85, 2.4, 21, c),
    ...buildStair(cx, cz, rot, 22, -14.1, -0.85, 0, 0, 0.85, 2.4, 21, c),
  ];
  for (const x of [-24, 24]) for (const z of [-15, 15]) boxes.push(pb(cx, cz, rot, x, z, 0, 5, 10, 5, c));
  return boxes.map((box) => ({ ...box, structural: true }));
}

/**
 * 西洋ゴシック巨大修道城 (約123×100m)。
 *
 * 背景のハリボテではなく、北南の城門、外郭、回廊中庭、大聖堂身廊、
 * 二階ギャラリー、城壁上、四隅塔の地上室を実際に戦闘で使える。
 * 見た目の尖塔・切妻屋根・控壁はBlender側が同じ平面図に座らせる。
 */
function buildAbbey(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const stone = p.obstacle;
  const trim = p.accent;
  const glow = p.emissiveAccent;
  const boxes: BoxSpec[] = [];

  // 外郭: 南北に14mの門、東西に8mの通用口。
  for (const z of [-36, 36]) {
    boxes.push(pb(cx, cz, rot, -27.5, z, 0, 33, 8, 2, stone));
    boxes.push(pb(cx, cz, rot, 27.5, z, 0, 33, 8, 2, stone));
    boxes.push(pb(cx, cz, rot, 0, z, 6.2, 22, 1.8, 2.4, trim, glow));
    boxes.push(pb(cx, cz, rot, 0, z - Math.sign(z) * 1.2, 7.5, 88, 0.55, 4.2, trim));
  }
  for (const x of [-46, 46]) {
    boxes.push(pb(cx, cz, rot, x, -22, 0, 2, 8, 28, stone));
    boxes.push(pb(cx, cz, rot, x, 22, 0, 2, 8, 28, stone));
    boxes.push(pb(cx, cz, rot, x, 0, 6.0, 2.4, 2, 16, trim, glow));
    boxes.push(pb(cx, cz, rot, x - Math.sign(x) * 1.2, 0, 7.5, 4.2, 0.55, 68, trim));
  }

  // 四隅塔の地上室。中庭側に3mの開口を残す。
  for (const tx of [-41, 41]) {
    for (const tz of [-31, 31]) {
      const inwardX = -Math.sign(tx);
      const inwardZ = -Math.sign(tz);
      boxes.push(pb(cx, cz, rot, tx, tz + inwardZ * 4.5, 0, 10, 18, 1.4, stone));
      boxes.push(pb(cx, cz, rot, tx + inwardX * 4.5, tz, 0, 1.4, 18, 10, stone));
      boxes.push(pb(cx, cz, rot, tx - inwardX * 4.5, tz - inwardZ * 3.5, 0, 1.4, 18, 3, stone));
      boxes.push(pb(cx, cz, rot, tx - inwardX * 4.5, tz + inwardZ * 3.5, 0, 1.4, 18, 3, stone));
      boxes.push(pb(cx, cz, rot, tx, tz, -0.2, 10, 0.4, 10, stone));
    }
  }

  // 回廊中庭: 中央18×16mは開放。四辺の回廊を循環できる。
  boxes.push(pb(cx, cz, rot, 0, -14, -0.15, 48, 0.3, 8, stone));
  boxes.push(pb(cx, cz, rot, 0, 14, -0.15, 48, 0.3, 8, stone));
  boxes.push(pb(cx, cz, rot, -19, 0, -0.15, 10, 0.3, 20, stone));
  boxes.push(pb(cx, cz, rot, 19, 0, -0.15, 10, 0.3, 20, stone));
  for (const x of [-21, -14, -7, 7, 14, 21]) {
    boxes.push(pb(cx, cz, rot, x, -17.4, 0, 0.9, 7.2, 0.9, stone));
    boxes.push(pb(cx, cz, rot, x, 17.4, 0, 0.9, 7.2, 0.9, stone));
  }
  for (const z of [-9, -3, 3, 9]) {
    boxes.push(pb(cx, cz, rot, -23.4, z, 0, 0.9, 7.2, 0.9, stone));
    boxes.push(pb(cx, cz, rot, 23.4, z, 0, 0.9, 7.2, 0.9, stone));
  }
  boxes.push(pb(cx, cz, rot, 0, -17.2, 7.1, 48, 0.5, 5.6, trim));
  boxes.push(pb(cx, cz, rot, 0, 17.2, 7.1, 48, 0.5, 5.6, trim));
  boxes.push(pb(cx, cz, rot, -23.2, 0, 7.1, 5.6, 0.5, 28, trim));
  boxes.push(pb(cx, cz, rot, 23.2, 0, 7.1, 5.6, 0.5, 28, trim));

  // 西翼の大聖堂身廊。両端門、中央通路、二階側廊を持つ。
  boxes.push(pb(cx, cz, rot, -28, 0, -0.2, 34, 0.4, 24, stone));
  boxes.push(pb(cx, cz, rot, -28, -11.5, 0, 34, 16, 1, stone));
  boxes.push(pb(cx, cz, rot, -28, 11.5, 0, 34, 16, 1, stone));
  boxes.push(pb(cx, cz, rot, -44.5, -7.5, 0, 1, 16, 7, stone));
  boxes.push(pb(cx, cz, rot, -44.5, 7.5, 0, 1, 16, 7, stone));
  boxes.push(pb(cx, cz, rot, -44.5, 0, 10.5, 1, 5.5, 8, trim, glow));
  boxes.push(pb(cx, cz, rot, -11.5, -7.5, 0, 1, 16, 7, stone));
  boxes.push(pb(cx, cz, rot, -11.5, 7.5, 0, 1, 16, 7, stone));
  boxes.push(pb(cx, cz, rot, -11.5, 0, 10.5, 1, 5.5, 8, trim, glow));
  boxes.push(pb(cx, cz, rot, -28, -8.5, 6.3, 30, 0.5, 5, trim));
  boxes.push(pb(cx, cz, rot, -28, 8.5, 6.3, 30, 0.5, 5, trim));
  for (const x of [-40, -34, -28, -22, -16]) {
    boxes.push(pb(cx, cz, rot, x, -6.2, 0, 1.1, 11.5, 1.1, trim, glow));
    boxes.push(pb(cx, cz, rot, x, 6.2, 0, 1.1, 11.5, 1.1, trim, glow));
  }

  // 東翼の内部ホールと中央塔基部。周回しながら上階へ向かう。
  boxes.push(pb(cx, cz, rot, 31, 0, -0.2, 22, 0.4, 26, stone));
  boxes.push(pb(cx, cz, rot, 31, -12.5, 0, 22, 12, 1, stone));
  boxes.push(pb(cx, cz, rot, 31, 12.5, 0, 22, 12, 1, stone));
  boxes.push(pb(cx, cz, rot, 41.5, -8, 0, 1, 12, 8, stone));
  boxes.push(pb(cx, cz, rot, 41.5, 8, 0, 1, 12, 8, stone));
  boxes.push(pb(cx, cz, rot, 41.5, 0, 8.5, 1, 3.5, 9, trim, glow));
  boxes.push(pb(cx, cz, rot, 20.5, -8, 0, 1, 12, 8, stone));
  boxes.push(pb(cx, cz, rot, 20.5, 8, 0, 1, 12, 8, stone));
  boxes.push(pb(cx, cz, rot, 20.5, 0, 8.5, 1, 3.5, 9, trim, glow));
  boxes.push(pb(cx, cz, rot, 31, 0, 11.8, 22, 0.55, 26, trim));
  boxes.push(pb(cx, cz, rot, 31, 0, 0, 8, 1.2, 5, trim, glow));

  // 入城後すぐに城壁上へ上がる2系統。最終段は歩廊上面に連続。
  boxes.push(...buildStair(cx, cz, rot, -40, -31.2, 0.85, 0, 0, 0.85, 2.4, 26, stone));
  boxes.push(...buildStair(cx, cz, rot, 40, 31.2, -0.85, 0, 0, 0.85, 2.4, 26, stone));
  // 身廊二階ギャラリーへの内部階段。
  boxes.push(...buildStair(cx, cz, rot, -42, -8.2, 0.8, 0, 0, 0.8, 1.8, 22, stone));
  boxes.push(...buildStair(cx, cz, rot, -14, 8.2, -0.8, 0, 0, 0.8, 1.8, 22, stone));

  // 326m級のフルサイズマップ中央でも「建物が一つある」ではなく、
  // 地域全体を占める城塞として読めるスケールへ拡張する。等方スケールなので
  // 回転済みの建物でも開口、射線、階段の接続関係は保たれる。
  const planScale = 1.28;
  return boxes.map((box) => ({
    ...box,
    x: cx + (box.x - cx) * planScale,
    z: cz + (box.z - cz) * planScale,
    w: box.w * planScale,
    d: box.d * planScale,
    structural: true,
  }));
}

/** 駅・廃駅。二面ホーム、線路帯、実際に渡れる跨線橋。 */
function buildStation(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const boxes: BoxSpec[] = [
    pb(cx, cz, rot, 0, -10, 0, 58, 0.35, 6, c),
    pb(cx, cz, rot, 0, 10, 0, 58, 0.35, 6, c),
    pb(cx, cz, rot, 0, -10, 5.2, 52, 0.35, 5, ac),
    pb(cx, cz, rot, 0, 10, 5.2, 52, 0.35, 5, ac),
    pb(cx, cz, rot, 0, 0, 6.4, 5, 0.55, 25, c),
    pb(cx, cz, rot, -25, -10, 0, 7, 3.5, 5, c),
    pb(cx, cz, rot, 25, 10, 0, 7, 3.5, 5, c),
    ...buildStair(cx, cz, rot, -3, -9.2, 0, 0.8, 0, 2.2, 0.8, 23, c),
    ...buildStair(cx, cz, rot, 3, 9.2, 0, -0.8, 0, 2.2, 0.8, 23, c),
  ];
  for (const x of [-22, -11, 0, 11, 22]) {
    boxes.push(pb(cx, cz, rot, x, -10, 0, 0.7, 5.2, 0.7, c));
    boxes.push(pb(cx, cz, rot, x, 10, 0, 0.7, 5.2, 0.7, c));
  }
  return boxes.map((box) => ({ ...box, structural: true }));
}

/** 車線が読みやすい封鎖検問。ゲート下3レーンと左右監視所。 */
function buildCheckpoint(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const boxes: BoxSpec[] = [
    pb(cx, cz, rot, 0, 0, 6.2, 48, 0.7, 3, ac, p.emissiveAccent),
    pb(cx, cz, rot, -23, 0, 0, 2, 11, 4, c),
    pb(cx, cz, rot, 23, 0, 0, 2, 11, 4, c),
    pb(cx, cz, rot, -13, -5, 0, 5, 3.2, 7, c),
    pb(cx, cz, rot, 13, 5, 0, 5, 3.2, 7, c),
    pb(cx, cz, rot, 0, -9, 0, 15, 1.1, 1.2, ac),
    pb(cx, cz, rot, 0, 9, 0, 15, 1.1, 1.2, ac),
    pb(cx, cz, rot, -17, 9, 4.5, 10, 0.5, 7, c),
    pb(cx, cz, rot, 17, -9, 4.5, 10, 0.5, 7, c),
    ...buildStair(cx, cz, rot, -8, 11.5, -0.8, 0, 0, 0.8, 2, 17, c),
  ];
  for (const x of [-7, 7]) boxes.push(pb(cx, cz, rot, x, 0, 0, 0.8, 6.2, 0.8, c));
  return boxes.map((box) => ({ ...box, structural: true }));
}

/** 地下街・地下鉄風の長大ヴォールト。開放ホームと中央メザニンを持つ。 */
function buildMetro(cx: number, cz: number, rot: number, p: StagePalette): BoxSpec[] {
  const c = p.obstacle;
  const ac = p.accent;
  const boxes: BoxSpec[] = [
    pb(cx, cz, rot, 0, 0, -0.2, 52, 0.4, 30, c),
    pb(cx, cz, rot, 0, -14.5, 0, 52, 8.5, 1, c),
    pb(cx, cz, rot, 0, 14.5, 0, 52, 8.5, 1, c),
    pb(cx, cz, rot, -25.5, -10, 0, 1, 8.5, 9, c),
    pb(cx, cz, rot, -25.5, 10, 0, 1, 8.5, 9, c),
    pb(cx, cz, rot, 25.5, -10, 0, 1, 8.5, 9, c),
    pb(cx, cz, rot, 25.5, 10, 0, 1, 8.5, 9, c),
    pb(cx, cz, rot, 0, -9, 0, 48, 0.45, 5, ac),
    pb(cx, cz, rot, 0, 9, 0, 48, 0.45, 5, ac),
    pb(cx, cz, rot, 0, 0, 5.4, 18, 0.5, 8, c),
    pb(cx, cz, rot, 0, 0, 8.5, 52, 0.5, 30, c),
    ...buildStair(cx, cz, rot, -8, -4.5, 0.8, 0, 0, 0.8, 2, 20, c),
    ...buildStair(cx, cz, rot, 8, 4.5, -0.8, 0, 0, 0.8, 2, 20, c),
  ];
  for (const x of [-18, -9, 0, 9, 18]) boxes.push(pb(cx, cz, rot, x, 0, 0, 0.8, 5.4, 0.8, c));
  return boxes.map((box) => ({ ...box, structural: true }));
}

/** 建造物の BoxSpec 配列を生成するディスパッチャー */
function generateBuilding(
  kind: BuildingKind,
  cx: number,
  cz: number,
  rot: number,
  p: StagePalette,
): BoxSpec[] {
  switch (kind) {
    case 'arena':
      return buildArena(cx, cz, rot, p);
    case 'hangar':
      return buildHangar(cx, cz, rot, p);
    case 'tower':
      return buildTower(cx, cz, rot, p);
    case 'warehouse':
      return buildWarehouse(cx, cz, rot, p);
    case 'cathedral':
      return buildCathedral(cx, cz, rot, p);
    case 'bunker':
      return buildBunker(cx, cz, rot, p);
    case 'terminal':
      return buildTerminal(cx, cz, rot, p);
    case 'refinery':
      return buildRefinery(cx, cz, rot, p);
    case 'villa':
      return buildVilla(cx, cz, rot, p);
    case 'pagoda':
      return buildPagoda(cx, cz, rot, p);
    case 'fortress':
      return buildFortress(cx, cz, rot, p);
    case 'station':
      return buildStation(cx, cz, rot, p);
    case 'checkpoint':
      return buildCheckpoint(cx, cz, rot, p);
    case 'metro':
      return buildMetro(cx, cz, rot, p);
    case 'abbey':
      return buildAbbey(cx, cz, rot, p);
  }
}

interface SoukoRoofMonitorSegment {
  tangent: number;
  length: number;
  width: number;
  bodyHeight: number;
  roofRise: number;
}

/**
 * Mirror the A9 Souko roof-monitor envelope with deterministic closed AABBs.
 *
 * The source slabs are selected by volume descending and then by their
 * original BoxSpec order.  Keeping the tie-break explicit is important for
 * the paired warehouse roofs, whose volumes are intentionally identical.
 * This path is used only by canonical generated placements; the live release
 * allow-list remains the independent adoption gate.
 */
function buildSoukoRoofMonitorColliders(
  districtBoxes: readonly BoxSpec[],
  palette: StagePalette,
): BoxSpec[] {
  const supportCount = 12;
  const supports = districtBoxes
    .map((box, originalIndex) => ({ box, originalIndex }))
    .filter((candidate): candidate is { box: BoxSpec & { district: BuildingKind }; originalIndex: number } => (
      candidate.box.roofMonitorSupport === true && candidate.box.district !== undefined
    ))
    .sort((a, b) => {
      const volumeDelta = b.box.w * b.box.h * b.box.d - a.box.w * a.box.h * a.box.d;
      return volumeDelta || a.originalIndex - b.originalIndex;
    });
  if (supports.length < supportCount) {
    throw new Error(`souko roof-monitor support drift: expected at least ${supportCount}, got ${supports.length}`);
  }

  const colliders: BoxSpec[] = [];
  for (const [supportIndex, { box }] of supports.slice(0, supportCount).entries()) {
    const variant = (supportIndex % 3) as 0 | 1 | 2;
    const longX = box.w >= box.d;
    const longSpan = longX ? box.w : box.d;
    const shortSpan = longX ? box.d : box.w;
    let segments: SoukoRoofMonitorSegment[];
    if (variant === 0) {
      segments = [{
        tangent: 0,
        length: longSpan * 0.56,
        width: Math.min(6.4, shortSpan * 0.30),
        bodyHeight: 0.82,
        roofRise: 0.42,
      }];
    } else if (variant === 1) {
      const direction = Math.floor(supportIndex / 3) % 2 === 1 ? -1 : 1;
      segments = [{
        tangent: Math.min(1.8, longSpan * 0.06) * direction,
        length: longSpan * 0.48,
        width: Math.min(5.6, shortSpan * 0.27),
        bodyHeight: 1.05,
        roofRise: 0.46,
      }];
    } else {
      const length = longSpan * 0.20;
      const width = Math.min(4.8, shortSpan * 0.24);
      const gap = Math.max(1.6, longSpan * 0.06);
      const offset = (length + gap) / 2;
      segments = [
        { tangent: -offset, length, width, bodyHeight: 0.72, roofRise: 0.34 },
        { tangent: offset, length, width, bodyHeight: 0.72, roofRise: 0.34 },
      ];
    }

    const makeBox = (
      tangent: number,
      y: number,
      tangentSpan: number,
      height: number,
      normalSpan: number,
      color: string,
      roofMonitor: NonNullable<BoxSpec['roofMonitor']>,
    ): BoxSpec => ({
      x: box.x + (longX ? tangent : 0),
      y,
      z: box.z + (longX ? 0 : tangent),
      w: longX ? tangentSpan : normalSpan,
      h: height,
      d: longX ? normalSpan : tangentSpan,
      color,
      emissive: false,
      structural: true,
      district: box.district,
      roofMonitor,
      visualReplacement: 'souko-roof-monitor-v1',
    });

    // A9 has one cap per support.  Variant 2 owns two separated monitor rooms,
    // so its single conservative curb proxy also spans the protected gap.
    const curbMin = Math.min(...segments.map((segment) => segment.tangent - segment.length / 2));
    const curbMax = Math.max(...segments.map((segment) => segment.tangent + segment.length / 2));
    const roofSlabTop = box.y + box.h / 2;
    const capTop = roofSlabTop + 0.20;
    const visualCurbBottom = capTop - 0.04;
    const visualCurbHeight = 0.30;
    // One authoritative curb AABB unions the cap contact beneath the monitor
    // with its four visual curb walls.  Its bottom overlaps the real slab by
    // 4cm and its top overlaps the body by 5cm, so no unsupported island is
    // introduced while the public BoxSpec count stays exactly 12 curbs.
    const curbBottom = roofSlabTop - 0.04;
    const curbHeight = visualCurbBottom + visualCurbHeight - curbBottom;
    colliders.push(makeBox(
      (curbMin + curbMax) / 2,
      curbBottom + curbHeight / 2,
      curbMax - curbMin,
      curbHeight,
      Math.max(...segments.map((segment) => segment.width)),
      palette.obstacle,
      { supportIndex, variant, part: 'curb' },
    ));

    const bodyBottom = visualCurbBottom + visualCurbHeight - 0.05;
    for (const [segmentIndex, segment] of segments.entries()) {
      const bodyTop = bodyBottom + segment.bodyHeight;
      // The +0.28m normal envelope includes the A9 louvers that project
      // 0.14m beyond each nominal side.  This remains one closed AABB even
      // though the Blender side wall is an open sill/header/post assembly.
      colliders.push(makeBox(
        segment.tangent,
        bodyBottom + segment.bodyHeight / 2,
        segment.length,
        segment.bodyHeight,
        segment.width + 0.28,
        palette.wall,
        { supportIndex, variant, part: 'body', segmentIndex },
      ));

      const roofBase = bodyTop - 0.06;
      colliders.push(makeBox(
        segment.tangent,
        roofBase + segment.roofRise / 2,
        segment.length + 0.50,
        segment.roofRise,
        segment.width + 0.60,
        palette.obstacle,
        { supportIndex, variant, part: 'roof-proxy', segmentIndex },
      ));
    }
  }

  return colliders;
}

/**
 * Build the authoritative collision/interior shell under one Blender hero.
 * Four centred doorways, a cross-shaped interior circulation spine, an upper
 * perimeter route and a physical 0.3m-step stair make every prototype
 * enterable and combat-usable; no visual doorway exists without a matching
 * collider opening.
 */
function buildLandmarkCombatShell(
  placement: LandmarkPlacement,
  palette: StagePalette,
): BoxSpec[] {
  const mark = (
    box: BoxSpec,
    part: NonNullable<BoxSpec['landmarkPart']>,
  ): BoxSpec => ({
    ...box,
    structural: true,
    district: placement.districtKind,
    landmarkId: placement.id,
    landmarkPart: part,
    combatSpace: true,
  });
  if (placement.collisionTemplate === 'abbey') {
    return generateBuilding('abbey', placement.cx, placement.cz, placement.rot, palette)
      .map((box) => mark(
        box,
        Math.abs(box.h - 0.3) < 1e-6
          ? 'stair'
          : box.h <= 0.6
            ? box.y > 3 ? 'upper-walk' : 'floor'
            : box.h >= 14 && box.w <= 16 && box.d <= 16
              ? 'tower'
              : 'wall',
      ));
  }

  const { cx, cz, rot, width, depth } = placement;
  const wall = palette.obstacle;
  const accent = palette.accent;
  const wallHeight = Math.max(9, Math.min(13, placement.height * 0.21));
  const wallThickness = 1.4;
  // A 28m grand opening carries either the complete 16m primary road or a
  // service alley offset by ten metres through the hero footprint.
  // Kairou's sanctuary uses a 32m outer opening.  Two 2m real gate columns
  // subdivide its north/south faces into a 16m central road and two ~6m side
  // arches; every other landmark keeps the shared 28m opening contract.
  const door = placement.id === 'kairou-meridian-hypostyle-sanctuary'
    ? 32
    : Math.max(28, placement.approach.width);
  const boxes: BoxSpec[] = [];
  const add = (box: BoxSpec, part: NonNullable<BoxSpec['landmarkPart']>) => {
    boxes.push(mark(box, part));
  };

  add(pb(cx, cz, rot, 0, 0, -0.25, width, 0.5, depth, wall), 'floor');

  // East/west walls: each is two seated segments with a real central opening.
  const sideSegmentDepth = (depth - door) / 2;
  const sideOffsetZ = door / 2 + sideSegmentDepth / 2;
  for (const localX of [-width / 2, width / 2]) {
    for (const localZ of [-sideOffsetZ, sideOffsetZ]) {
      add(pb(cx, cz, rot, localX, localZ, 0, wallThickness, wallHeight, sideSegmentDepth, wall), 'wall');
    }
  }
  // North/south walls have the same physical doorway contract.
  const endSegmentWidth = (width - door) / 2;
  const endOffsetX = door / 2 + endSegmentWidth / 2;
  for (const localZ of [-depth / 2, depth / 2]) {
    for (const localX of [-endOffsetX, endOffsetX]) {
      // Kairou's authored north entrance is an open hypostyle portico, not a
      // blind eight-metre wall.  A 1.4m collision plinth keeps believable
      // cover/stair scale while the eight real columns behind it carry the
      // sanctuary silhouette.  The opposite elevation remains a full wall.
      const endWallHeight = placement.id === 'kairou-meridian-hypostyle-sanctuary'
        && localZ < 0
        ? 1.4
        : wallHeight;
      add(pb(cx, cz, rot, localX, localZ, 0, endSegmentWidth, endWallHeight, wallThickness, wall), 'wall');
    }
  }

  // Eight quadrant walls form four combat rooms without occupying the central
  // 28m cross.  Both authored streets therefore pass continuously from one
  // exterior doorway to the opposite doorway.
  const interiorGap = 28;
  const interiorXSpan = (width * 0.68 - interiorGap) / 2;
  const interiorZSpan = (depth * 0.62 - interiorGap) / 2;
  for (const xSide of [-1, 1]) {
    for (const zSide of [-1, 1]) {
      add(pb(
        cx,
        cz,
        rot,
        xSide * (interiorGap / 2 + interiorXSpan / 2),
        zSide * (interiorGap / 2 + 0.45),
        0,
        interiorXSpan,
        wallHeight * 0.58,
        0.9,
        wall,
      ), 'interior');
      add(pb(
        cx,
        cz,
        rot,
        xSide * (interiorGap / 2 + 0.45),
        zSide * (interiorGap / 2 + interiorZSpan / 2),
        0,
        0.9,
        wallHeight * 0.58,
        interiorZSpan,
        wall,
      ), 'interior');
    }
  }

  if (placement.id === 'kairou-meridian-hypostyle-sanctuary') {
    // Eight collision-authoritative hero columns turn the sanctuary
    // into a real hypostyle combat space instead of a facade illusion.  Their
    // local centres are deliberately outside both arms of the open 28 m cross:
    // X = ±16/±22/±28/±34m, Z = -32m.  The broad single front row sits
    // directly behind the low entrance plinth, so the hypostyle reads before
    // entry; a 2.6m square proxy
    // contains the matching
    // Blender cylinder and still leaves >=3m to the nearest tower collider.
    // The 16m collision height matches the monumental visual shaft, so bullets
    // cannot pass through the upper half of a column that the player can see.
    // No column touches the entrance approach, stair or upper-walk connection.
    for (const localX of [-34, -28, -22, -16, 16, 22, 28, 34]) {
      add(pb(
        cx,
        cz,
        rot,
        localX,
        -32,
        0,
        2.6,
        18,
        2.6,
        wall,
      ), 'column');
    }

    // Four collision-authoritative gate columns support the north/south upper
    // walks and the three-bay arch treatment.  Inner faces at X=±8m leave the
    // complete 16m primary boulevard open; outer 32m gate edges leave ~6m
    // side passages.  These are never decorative collider-free posts.
    for (const localZ of [-depth / 2, depth / 2]) {
      for (const localX of [-9, 9]) {
        add(pb(
          cx,
          cz,
          rot,
          localX,
          localZ,
          0,
          2,
          12.2,
          2,
          wall,
        ), 'gate-column');
      }
    }
  }

  if (placement.id === 'kairou-windcrown-caravan-observatory') {
    // A physical upper citadel ring turns the four tower colliders into one
    // readable observatory.  Its bottom sits above the 11.34m perimeter walls,
    // so all four 28m gates and the complete ground-level combat cross remain
    // open.  Keeping this layer in TypeScript prevents projectiles from passing
    // through the substantial upper architecture rendered by Blender.
    const upperBottom = wallHeight + 0.3;
    const upperHeight = 8;
    const upperThickness = 3.2;
    add(pb(cx, cz, rot, -width / 2, 0, upperBottom, upperThickness, upperHeight, depth, wall), 'upper-wall');
    add(pb(cx, cz, rot, width / 2, 0, upperBottom, upperThickness, upperHeight, depth, wall), 'upper-wall');
    add(pb(cx, cz, rot, 0, -depth / 2, upperBottom, width, upperHeight, upperThickness, wall), 'upper-wall');
    add(pb(cx, cz, rot, 0, depth / 2, upperBottom, width, upperHeight, upperThickness, wall), 'upper-wall');
    // A high central proxy contains the tapered observatory drum rendered by
    // Blender.  Its 27.8m bottom preserves all player/AI routes, while bullets
    // can no longer pass through the castle-scale stone mass above them.
    add(pb(cx, cz, rot, 0, 0, 27.8, 30, 12, 30, wall), 'upper-wall');
  }

  // Continuous upper perimeter firing route.  The open centre preserves sky
  // visibility and avoids a collisionless opaque roof over the combat floor.
  const walkY = 5.6;
  const walkWidth = 3.4;
  add(pb(cx, cz, rot, 0, -depth / 2 + walkWidth / 2 + wallThickness, walkY - 0.2, width - 2, 0.4, walkWidth, accent), 'upper-walk');
  add(pb(cx, cz, rot, 0, depth / 2 - walkWidth / 2 - wallThickness, walkY - 0.2, width - 2, 0.4, walkWidth, accent), 'upper-walk');
  add(pb(cx, cz, rot, -width / 2 + walkWidth / 2 + wallThickness, 0, walkY - 0.2, walkWidth, 0.4, depth - 2, accent), 'upper-walk');
  add(pb(cx, cz, rot, width / 2 - walkWidth / 2 - wallThickness, 0, walkY - 0.2, walkWidth, 0.4, depth - 2, accent), 'upper-walk');

  // One fully physical stair terminates exactly at the south upper walk.
  const stairSteps = 18;
  const stairStartZ = -depth / 2 + 18;
  for (let step = 0; step < stairSteps; step += 1) {
    add(pb(
      cx,
      cz,
      rot,
      width * 0.20,
      stairStartZ - step * 0.8,
      step * 0.3,
      2.4,
      0.3,
      0.86,
      wall,
    ), 'stair');
  }

  // Template-specific grounded supports expose the same macro grammar that
  // Blender uses for the silhouette, without filling the traversable centre.
  if (placement.collisionTemplate === 'bridge') {
    for (const localX of [-width * 0.30, width * 0.30]) {
      add(pb(
        cx,
        cz,
        rot,
        localX,
        0,
        0,
        7,
        Math.max(wallHeight + 4, placement.height * 0.72),
        7,
        wall,
      ), 'tower');
    }
    add(pb(cx, cz, rot, 0, 0, wallHeight * 0.72, width * 0.64, 0.6, 4.2, accent), 'upper-walk');
  } else if (placement.collisionTemplate === 'vertical') {
    for (const [localX, localZ] of [[-1, -1], [1, -1], [-1, 1], [1, 1]] as const) {
      add(pb(
        cx,
        cz,
        rot,
        localX * width * 0.34,
        localZ * depth * 0.32,
        0,
        6.5,
        placement.height * (localX === localZ ? 0.72 : 0.62),
        6.5,
        wall,
      ), 'tower');
    }
  } else if (placement.collisionTemplate === 'hall') {
    add(pb(cx, cz, rot, 0, -depth * 0.23, wallHeight * 0.62, width * 0.62, 0.5, 4.0, accent), 'upper-walk');
    add(pb(cx, cz, rot, 0, depth * 0.23, wallHeight * 0.62, width * 0.62, 0.5, 4.0, accent), 'upper-walk');
    for (const localX of [-width * 0.34, width * 0.34]) {
      add(pb(cx, cz, rot, localX, depth * 0.28, 0, 7, placement.height * 0.66, 7, wall), 'tower');
    }
  } else if (placement.collisionTemplate === 'courtyard') {
    for (const [localX, localZ] of [[-1, -1], [1, -1], [-1, 1], [1, 1]] as const) {
      add(pb(
        cx,
        cz,
        rot,
        localX * width * 0.37,
        localZ * depth * 0.34,
        0,
        7,
        placement.height * (localX === localZ ? 0.64 : 0.56),
        7,
        wall,
      ), 'tower');
    }
  }
  return boxes;
}

// ── 遠景シルエット(プレイアブル境界外の装飾) ────────────────────────────

function generateSilhouette(
  def: StageDef,
  half: number,
  rand: () => number,
): BoxSpec[] {
  const sil = def.palette.silhouette ?? 'none';
  if (sil === 'none') return [];
  const boxes: BoxSpec[] = [];
  // シルエット帯: half の 2.5〜2.86 倍の距離に配置(= camera.far 調整は統合担当)
  const outerR = half * 2.5;
  const col = def.palette.obstacle;

  if (sil === 'skyline') {
    const count = 6 + Math.floor(rand() * 3);
    for (let i = 0; i < count; i++) {
      const ang = (i / count) * Math.PI * 2 + rand() * 0.4;
      const dist = outerR + rand() * half * 0.36;
      const sx = Math.cos(ang) * dist;
      const sz = Math.sin(ang) * dist;
      const sw = 12 + rand() * 28;
      const sh = 18 + rand() * 50;
      const sd = 4 + rand() * 4;
      boxes.push({ x: sx, y: sh / 2, z: sz, w: sw, h: sh, d: sd, color: col, emissive: false, decor: true });
    }
  } else if (sil === 'mountain') {
    const count = 4 + Math.floor(rand() * 2);
    for (let i = 0; i < count; i++) {
      const ang = (i / count) * Math.PI * 2 + rand() * 0.5;
      const dist = outerR + rand() * half * 0.36;
      const sx = Math.cos(ang) * dist;
      const sz = Math.sin(ang) * dist;
      const baseW = 50 + rand() * 60;
      const baseH = 20 + rand() * 30;
      const midW = baseW * 0.55;
      const midH = baseH * 0.45;
      boxes.push({ x: sx, y: baseH / 2, z: sz, w: baseW, h: baseH, d: 8, color: col, emissive: false, decor: true });
      boxes.push({ x: sx, y: baseH + midH / 2, z: sz, w: midW, h: midH, d: 6, color: col, emissive: false, decor: true });
    }
  } else if (sil === 'ridge') {
    const count = 3 + Math.floor(rand() * 2);
    for (let i = 0; i < count; i++) {
      const ang = (i / count) * Math.PI * 2 + rand() * 0.3;
      const dist = outerR + rand() * half * 0.36;
      const sx = Math.cos(ang) * dist;
      const sz = Math.sin(ang) * dist;
      const length = 90 + rand() * 70;
      const height = 10 + rand() * 22;
      // 尾根は放射方向に対して直交して配置
      const useZ = Math.abs(Math.cos(ang)) > Math.abs(Math.sin(ang));
      const sw = useZ ? 6 : length;
      const sd = useZ ? length : 6;
      boxes.push({ x: sx, y: height / 2, z: sz, w: sw, h: height, d: sd, color: col, emissive: false, decor: true });
    }
  }

  for (const box of boxes) box.legacyHorizon = true;
  return boxes;
}

// ── 拡張視覚地形(境界外の装飾床, 4 ストリップ) ────────────────────────

function generateExtendedTerrain(def: StageDef, half: number): BoxSpec[] {
  const ext = Math.round(half * 0.65);
  const h = 0.3;
  const c = def.palette.floor;
  const fullW = def.size + ext * 2;
  return [
    { x: 0, y: h / 2, z: -(half + ext / 2), w: fullW, h, d: ext, color: c, emissive: false, decor: true },
    { x: 0, y: h / 2, z: half + ext / 2, w: fullW, h, d: ext, color: c, emissive: false, decor: true },
    { x: -(half + ext / 2), y: h / 2, z: 0, w: ext, h, d: def.size, color: c, emissive: false, decor: true },
    { x: half + ext / 2, y: h / 2, z: 0, w: ext, h, d: def.size, color: c, emissive: false, decor: true },
  ];
}

// ── 環境プロップ フットプリント近似 [w, d] (クリアランス計算用) ────────────
const PROP_FOOTPRINTS: Record<PropKind, [number, number]> = {
  conifer: [3, 3], broadleaf: [5, 5], deadtree: [2, 2], sakura: [5, 5], bamboo: [2, 2],
  rock: [3, 3], towercrane: [15, 5], portalkrane: [11, 4], smokestack: [2.5, 2.5],
  gastank: [5, 5], watertower: [4.5, 4.5], transformer: [3, 2.5], antenna: [1.5, 1.5],
  truck: [8, 3.5], derelictcar: [3, 5], forklift: [2.5, 3], barricadecar: [5, 5],
  concretebarrier: [1.5, 3], fence: [5, 1], watchpost: [4, 4], tankhull: [5, 7],
  scaffold: [4, 3], streetlight: [1, 1], signboard: [3, 1], bench: [2, 1],
  vendingmachine: [1.2, 0.8], drumgroup: [2, 2], pallet: [1.5, 1.2], torii: [4.5, 1.5],
  stonelantern: [1, 1], well: [2, 2], pier: [7, 3], utilitypole: [1, 1],
  rubble: [3, 3], gasbottlegroup: [1.5, 1.5], supplycrate: [2, 2],
};

/**
 * 環境プロップ36種の BoxSpec 配列を生成する。
 * - 全ボックスに prop:true
 * - h > 3 のボックスに shadowCaster:true
 * - 幹=world / 樹冠=decor / 構造材=structural / 小物=通常(breakable自動付与対象)
 */
export function buildProp(
  kind: PropKind,
  cx: number,
  cz: number,
  rot: number,
  _rand: () => number,
  palette: StagePalette,
): BoxSpec[] {
  const c = palette.obstacle;
  const ac = palette.accent;
  const e = palette.emissiveAccent;
  const BROWN = '#5a3a1a';
  const D_GREEN = '#2a5220';
  const GREEN = '#3a7a2a';
  const PINK = '#e8b4c8';
  const BAMBOO = '#6a9a4a';
  const STONE = '#8a8278';

  function p(
    lx: number,
    lz: number,
    yBot: number,
    lw: number,
    lh: number,
    ld: number,
    color: string,
    emissive = false,
    opts: { decor?: boolean; structural?: boolean } = {},
  ): BoxSpec {
    const base = pb(cx, cz, rot, lx, lz, yBot, lw, lh, ld, color, emissive);
    const box: BoxSpec = { ...base, prop: true };
    if (lh > 3) box.shadowCaster = true;
    if (opts.decor) box.decor = true;
    if (opts.structural) box.structural = true;
    return box;
  }

  switch (kind) {
    case 'conifer':
      return [
        p(0, 0, 0, 0.5, 3.5, 0.5, BROWN),
        p(0, 0, 2, 2.5, 4, 2.5, D_GREEN, false, { decor: true }),
      ];
    case 'broadleaf':
      return [
        p(0, 0, 0, 0.5, 3.5, 0.5, BROWN),
        p(0, 0, 2.5, 4.5, 3, 4.5, GREEN, false, { decor: true }),
      ];
    case 'deadtree':
      return [
        p(0, 0, 0, 0.4, 4.5, 0.4, BROWN),
        p(1, 0, 3.5, 2, 0.3, 0.3, BROWN, false, { decor: true }),
        p(0, 0.8, 3, 0.3, 0.3, 1.5, BROWN, false, { decor: true }),
      ];
    case 'sakura':
      return [
        p(0, 0, 0, 0.5, 3.5, 0.5, BROWN),
        p(0, 0, 2.5, 4.5, 3, 4.5, PINK, false, { decor: true }),
      ];
    case 'bamboo':
      return [
        p(0, 0, 0, 0.2, 6, 0.2, BAMBOO),
        p(0.5, 0.3, 0, 0.2, 5, 0.2, BAMBOO),
        p(-0.4, 0.5, 0, 0.2, 5.5, 0.2, BAMBOO),
      ];
    case 'rock':
      return [p(0, 0, 0, 2.2, 1.4, 2.2, STONE)];
    case 'towercrane':
      return [
        p(0, 0, 0, 1, 18, 1, c, false, { structural: true }),
        p(5, 0, 17, 10, 0.6, 0.8, c, false, { structural: true }),
        p(-2.5, 0, 17, 5, 0.6, 0.8, c, false, { structural: true }),
      ];
    case 'portalkrane':
      return [
        p(-4, 0, 0, 1, 8, 1, c, false, { structural: true }),
        p(4, 0, 0, 1, 8, 1, c, false, { structural: true }),
        p(0, 0, 8, 9.5, 0.8, 1, c, false, { structural: true }),
      ];
    case 'smokestack':
      return [p(0, 0, 0, 1.5, 16, 1.5, c, false, { structural: true })];
    case 'gastank':
      return [
        p(0, 0, 0, 3, 2, 3, c, false, { structural: true }),
        p(0, 0, 2, 4, 3.5, 4, c, false, { structural: true }),
      ];
    case 'watertower':
      return [
        p(0, 0, 0, 1.5, 5, 1.5, c, false, { structural: true }),
        p(0, 0, 5, 3.5, 3, 3.5, c, false, { structural: true }),
      ];
    case 'transformer':
      return [
        p(0, 0, 0, 2, 1.5, 1.5, c),
        p(-0.6, 0, 1.5, 0.2, 2, 0.2, c),
        p(0.6, 0, 1.5, 0.2, 2, 0.2, c),
      ];
    case 'antenna':
      return [p(0, 0, 0, 0.3, 12, 0.3, c, false, { structural: true })];
    case 'truck':
      return [
        p(-2, 0, 0, 2, 2.5, 2.5, c),
        p(1.5, 0, 0, 5, 2.2, 2.5, c),
      ];
    case 'derelictcar':
      return [p(0, 0, 0, 2, 1.3, 4, c)];
    case 'forklift':
      return [
        p(0, 0, 0, 1.5, 2, 2, c),
        p(0, 1.2, 0, 1, 2.5, 0.3, c),
      ];
    case 'barricadecar':
      return [
        p(-1.5, 0, 0, 2, 1.2, 4, c),
        p(1.5, 0, 0, 2, 1.2, 4, c),
      ];
    case 'concretebarrier':
      return [p(0, 0, 0, 0.6, 1, 2.4, c)];
    case 'fence':
      return [p(0, 0, 0, 4, 1.5, 0.15, c)];
    case 'watchpost':
      return [
        p(0, 0, 0, 0.5, 4, 0.5, c, false, { structural: true }),
        p(0, 0, 4, 3, 0.3, 3, c, false, { structural: true }),
      ];
    case 'tankhull':
      return [
        p(0, 0, 0, 4, 1.5, 6, c),
        p(0, 0, 1.5, 2, 0.8, 2, c),
      ];
    case 'scaffold':
      return [
        p(-1.4, 0, 0, 0.15, 3.5, 0.15, c, false, { structural: true }),
        p(1.4, 0, 0, 0.15, 3.5, 0.15, c, false, { structural: true }),
        p(0, 0, 3.5, 3.2, 0.2, 2, c, false, { structural: true }),
      ];
    case 'streetlight':
      return [
        p(0, 0, 0, 0.15, 5, 0.15, c),
        p(0.4, 0, 4.8, 0.8, 0.2, 0.4, ac, e),
      ];
    case 'signboard':
      return [
        p(0, 0, 0, 0.15, 3.5, 0.15, c),
        p(0, 0, 2.8, 2.5, 1, 0.1, ac, e),
      ];
    case 'bench':
      return [p(0, 0, 0, 1.5, 0.45, 0.5, c)];
    case 'vendingmachine':
      return [p(0, 0, 0, 0.7, 1.8, 0.4, c, e)];
    case 'drumgroup':
      return [
        p(-0.5, 0, 0, 0.6, 0.9, 0.6, c),
        p(0.5, 0, 0, 0.6, 0.9, 0.6, c),
        p(0, 0.6, 0, 0.6, 0.9, 0.6, c),
      ];
    case 'pallet':
      return [p(0, 0, 0, 1.2, 0.15, 0.8, c)];
    case 'torii':
      return [
        p(-1.5, 0, 0, 0.4, 3.5, 0.4, c),
        p(1.5, 0, 0, 0.4, 3.5, 0.4, c),
        p(0, 0, 3.3, 3.6, 0.3, 0.4, c),
      ];
    case 'stonelantern':
      return [
        p(0, 0, 0, 0.5, 0.3, 0.5, STONE),
        p(0, 0, 0.3, 0.35, 0.7, 0.35, STONE),
        p(0, 0, 1, 0.6, 0.3, 0.6, STONE),
      ];
    case 'well':
      return [
        p(0, 0, 0, 1.5, 0.6, 1.5, STONE),
        p(0, 0, 0.6, 0.15, 1, 0.15, c),
      ];
    case 'pier':
      return [
        p(-2, 0, 0, 0.3, 0.6, 0.3, c),
        p(2, 0, 0, 0.3, 0.6, 0.3, c),
        p(0, 0, 0.6, 6, 0.3, 2, c),
      ];
    case 'utilitypole':
      return [
        p(0, 0, 0, 0.25, 8, 0.25, c),
        p(0, 0, 7, 2, 0.15, 0.15, c),
      ];
    case 'rubble':
      return [
        p(0, 0, 0, 2.2, 0.8, 2.2, c),
        p(0.3, 0.3, 0.8, 1.4, 0.6, 1.4, c),
      ];
    case 'gasbottlegroup':
      return [
        p(-0.4, 0, 0, 0.3, 1.0, 0.3, c),
        p(0.4, 0, 0, 0.3, 1.0, 0.3, c),
        p(0, 0.4, 0, 0.3, 1.0, 0.3, c),
      ];
    case 'supplycrate':
      return [
        p(0, 0, 0, 1, 0.8, 1, ac),
        p(0.1, 0.1, 0.8, 1, 0.8, 1, ac),
      ];
    default: {
      const _exhaustive: never = kind;
      void _exhaustive;
      return [];
    }
  }
}

// ── ミニシーン(超リアル化Layer C, R53-S2) ──────────────────────────────
// 複数プロップの相対配置テンプレート(座標はシーン中心=アンカーからのローカルオフセット、
// dRotSteps はテンプレ内の相対量子化回転)。generateThemeObjects が
// アンカー位置+シーン全体の連続回転(シード回転)を独立RNGで決定し、
// 各メンバーへ buildProp() を1回ずつ呼んでboxes/propPlacedへ積む。
interface SceneMember {
  kind: PropKind;
  /** シーンアンカーからのローカルXオフセット(m, シーン回転前)。 */
  dx: number;
  /** シーンアンカーからのローカルZオフセット(m, シーン回転前)。 */
  dz: number;
  /** シーン基準角に対する相対量子化回転(0-3, コライダー生成にのみ使用)。 */
  dRotSteps: number;
}

const SCENE_TEMPLATES: Record<MiniSceneId, readonly SceneMember[]> = {
  // 資材置場: パレット2+補給箱+傾いたドラム缶群
  shizai: [
    { kind: 'pallet', dx: -1.2, dz: 0, dRotSteps: 0 },
    { kind: 'pallet', dx: 1.2, dz: 0.3, dRotSteps: 1 },
    { kind: 'supplycrate', dx: 0, dz: -1.8, dRotSteps: 2 },
    { kind: 'drumgroup', dx: 2.0, dz: -1.0, dRotSteps: 0 },
  ],
  // 検問: バリケード車+コンクリバリア列+フェンス
  kenmon: [
    { kind: 'barricadecar', dx: 0, dz: 0, dRotSteps: 0 },
    { kind: 'concretebarrier', dx: -3.2, dz: -2.5, dRotSteps: 1 },
    { kind: 'concretebarrier', dx: -3.2, dz: 0.5, dRotSteps: 1 },
    { kind: 'fence', dx: -3.2, dz: 3.5, dRotSteps: 1 },
  ],
  // 参道: 鳥居+石灯籠対+ベンチ
  sandou: [
    { kind: 'torii', dx: 0, dz: 0, dRotSteps: 0 },
    { kind: 'stonelantern', dx: -2.5, dz: -3, dRotSteps: 0 },
    { kind: 'stonelantern', dx: 2.5, dz: -3, dRotSteps: 0 },
    { kind: 'bench', dx: 0, dz: -6, dRotSteps: 2 },
  ],
  // 車両事故: 放置車+トラック+瓦礫
  jiko: [
    { kind: 'derelictcar', dx: -2, dz: 1, dRotSteps: 1 },
    { kind: 'truck', dx: 2.5, dz: -1, dRotSteps: 3 },
    { kind: 'rubble', dx: 0, dz: -3, dRotSteps: 0 },
  ],
  // 井戸端: 井戸+ベンチ+広葉樹
  idobata: [
    { kind: 'well', dx: 0, dz: 0, dRotSteps: 0 },
    { kind: 'bench', dx: 2.2, dz: 0.5, dRotSteps: 1 },
    { kind: 'broadleaf', dx: -2.5, dz: -1.5, dRotSteps: 0 },
  ],
  // 工場一角: 変圧器+ドラム缶+ガスボンベ+フェンス
  kouba: [
    { kind: 'transformer', dx: 0, dz: 0, dRotSteps: 0 },
    { kind: 'drumgroup', dx: 2.2, dz: -0.5, dRotSteps: 1 },
    { kind: 'gasbottlegroup', dx: -2.0, dz: 1.0, dRotSteps: 2 },
    { kind: 'fence', dx: 0, dz: 2.8, dRotSteps: 0 },
  ],
  // 休憩所: ベンチ対+自販機+街灯
  kyuukei: [
    { kind: 'bench', dx: -1.8, dz: 0, dRotSteps: 0 },
    { kind: 'bench', dx: 1.8, dz: 0, dRotSteps: 2 },
    { kind: 'vendingmachine', dx: 0, dz: -1.6, dRotSteps: 0 },
    { kind: 'streetlight', dx: 0, dz: 1.8, dRotSteps: 0 },
  ],
};

/** テストや将来の拡張向けにミニシーンID一覧を列挙(prop-visuals.tsのPROP_VISUAL_KINDSと同じ流儀)。 */
export const MINI_SCENE_IDS: readonly MiniSceneId[] = Object.keys(SCENE_TEMPLATES) as MiniSceneId[];

/** 視覚ジッタの標準値(R53-S2): ヨーは量子化回転±ROT_JITTER(kindごとに縮小されうる)、
 * スケールは±SCALE_JITTERの一様分布。 */
const ROT_JITTER = 0.45; // rad(約26°)。量子化回転(0/90/180/270°)を軸に振れる範囲の"上限"
// ★R57-⑥ 根治(V-C再確証対応): ジッタ振幅の決定を PROP_FOOTPRINTS のアスペクト比(近似値・
// クリアランス計算専用の粗い数字)から、各kindの実 buildProp() コライダー箱群(union AABB)へ
// 差し替える。旧アスペクト比方式には3つの穴があった:
//   (a) footprint比 ≠ 実コライダー比(例: concretebarrier footprint[1.5,3]=2.00だが実コライダーは
//       0.6×2.4=4.00、tankhullは footprint[5,7]=1.4だが判定式は絶対長を見ないため素通り)
//   (b) 絶対はみ出し量(m)を無視(barricadecarは2箱オフセット構成でアスペクト1.25でも約0.89mの
//       はみ出しが出る = アスペクト比だけでは検出できない)
//   (c) アスペクト丁度2.0を strict > 2 が取りこぼす(derelictcarの実コライダーは2×4=2.00丁度)
// 結果、concretebarrier/derelictcar/barricadecar/tankhull(いずれも最頻の遮蔽物)で視覚が
// 軸整列コライダーからはみ出し、ファントム遮蔽(弾すり抜け)/見えない壁が残存していた。
//
// 判定式(コーナー回転の厳密版): 局所原点(0,0)基準のコライダー箱群の全頂点を角度θだけ回転させ、
// 元の軸整列AABBからのはみ出し量 max(0, はみ出しx, はみ出しz) を求める。この式で
// 「はみ出しが許容 OVERHANG_ALLOWANCE_M(既定0.25m)以内に収まる最大角」を kind ごとに
// 二分探索し、ROT_JITTER(0.45)を上限としてジッタ振幅を個別化する。コライダー自体は不変
// (90°量子化・軸整列のまま) — 視覚回転角(このジッタ振幅)のみを縮小してはみ出しを解消する。
// 小型プロップ(0.45radでもはみ出しが0.25m未満)は実質無変更で「回転OK」のまま残る。
const OVERHANG_ALLOWANCE_M = 0.25;

/** buildProp() は色情報(obstacle/accent/emissiveAccent)しか読まないため、ジッタ振幅の
 * 事前計算(モジュール読込時に1回だけ)専用のダミーパレットで安全に呼び出せる。 */
const JITTER_CALC_PALETTE: StagePalette = {
  sky: '#000000', fog: '#000000', floor: '#000000', wall: '#000000',
  obstacle: '#000000', accent: '#000000', lightColor: '#000000',
  lightIntensity: 1, ambientIntensity: 1, fogDensity: 0, emissiveAccent: false,
};

/** kind単体をrot=0(量子化なし)でbuildProp()した際の、局所原点(0,0)基準コライダー箱群の
 * 全頂点(コーナー)と軸整列AABB。90°量子化は軸整列を保つ相似変換なので、この rot=0 の形状が
 * どの quantSteps でも(辺の入れ替えを除き)そのまま通用する。 */
function propColliderCorners(kind: PropKind): {
  corners: Array<[number, number]>;
  xMin: number; xMax: number; zMin: number; zMax: number;
} {
  const boxes = buildProp(kind, 0, 0, 0, () => 0, JITTER_CALC_PALETTE);
  let xMin = Infinity, xMax = -Infinity, zMin = Infinity, zMax = -Infinity;
  const corners: Array<[number, number]> = [];
  for (const box of boxes) {
    const x0 = box.x - box.w / 2, x1 = box.x + box.w / 2;
    const z0 = box.z - box.d / 2, z1 = box.z + box.d / 2;
    xMin = Math.min(xMin, x0); xMax = Math.max(xMax, x1);
    zMin = Math.min(zMin, z0); zMax = Math.max(zMax, z1);
    corners.push([x0, z0], [x0, z1], [x1, z0], [x1, z1]);
  }
  return { corners, xMin, xMax, zMin, zMax };
}

/** 原点周りに角度θ回転させたコライダー箱群コーナーが、元の軸整列AABBからはみ出す最大量(m)。
 * ジッタは±amp対称なので呼び出し側で+θ/-θ双方の最大を取ること。 */
function worstOverhang(
  data: { corners: Array<[number, number]>; xMin: number; xMax: number; zMin: number; zMax: number },
  theta: number,
): number {
  const c = Math.cos(theta);
  const s = Math.sin(theta);
  let maxOver = 0;
  for (const [x, z] of data.corners) {
    const rx = x * c - z * s;
    const rz = x * s + z * c;
    maxOver = Math.max(maxOver, rx - data.xMax, data.xMin - rx, rz - data.zMax, data.zMin - rz);
  }
  return maxOver;
}

/** kindごとに「はみ出しがOVERHANG_ALLOWANCE_M以内に収まる最大角」を二分探索で求め、
 * ROT_JITTERを上限としてジッタ振幅を確定する(R57-⑥ 根治)。純関数・モジュール読込時に1回だけ
 * 実行(36kind×40回の二分探索は起動コストとして無視できる)。 */
function computePropJitterAmps(): Readonly<Record<PropKind, number>> {
  const entries = (Object.keys(PROP_FOOTPRINTS) as PropKind[]).map((kind) => {
    const data = propColliderCorners(kind);
    const worstBothSigns = (theta: number) => Math.max(worstOverhang(data, theta), worstOverhang(data, -theta));
    if (worstBothSigns(ROT_JITTER) <= OVERHANG_ALLOWANCE_M) {
      return [kind, ROT_JITTER] as const;
    }
    let lo = 0;
    let hi = ROT_JITTER;
    for (let i = 0; i < 40; i += 1) {
      const mid = (lo + hi) / 2;
      if (worstBothSigns(mid) > OVERHANG_ALLOWANCE_M) hi = mid; else lo = mid;
    }
    return [kind, lo] as const;
  });
  return Object.fromEntries(entries) as Record<PropKind, number>;
}

const PROP_JITTER_AMP: Readonly<Record<PropKind, number>> = computePropJitterAmps();
const SCALE_JITTER = 0.12; // ±12%

/** 任意の角度を [0, 2π) へ正規化する。 */
function normalizeAngle(rad: number): number {
  const twoPi = Math.PI * 2;
  return ((rad % twoPi) + twoPi) % twoPi;
}

/**
 * 量子化回転(0-3, 90°刻み)を基準に ±PROP_JITTER_AMP[kind] の視覚専用ヨーを引く。
 * コライダーは常にこの quantSteps のまま軸整列(rotRadは一切参照されない)。
 */
function jitterRotRad(quantSteps: number, visRand: Rand, kind: PropKind): number {
  // visRand は kind に依らず必ず1回消費(決定論ストリームの安定性維持)
  const amp = PROP_JITTER_AMP[kind];
  return normalizeAngle(quantSteps * (Math.PI / 2) + (visRand() * 2 - 1) * amp);
}

function jitterScale(visRand: Rand): number {
  return 1 + (visRand() * 2 - 1) * SCALE_JITTER;
}

/**
 * ミニシーン1箇所を試行配置する。アンカー位置+シーン全体の連続回転(sceneRot)を
 * visRand(独立RNG)で決め、テンプレのローカルオフセットを sceneRot で回転させて
 * 各メンバーのワールド座標を得る。全メンバーが境界内・クリアランスOKな試行が
 * 見つかるまで最大20回リトライ(既存の建造物/障害物配置と同じ方針)。
 * 失敗時は静かに諦める(シーンが1つ減るだけで既存配置には一切影響しない)。
 */
function tryPlaceScene(
  sceneId: MiniSceneId,
  def: StageDef,
  half: number,
  allSpawns: readonly [number, number][],
  buildingPlaced: Aabb[],
  propPlaced: Aabb[],
  boxes: BoxSpec[],
  visRand: Rand,
  placementsOut: PropPlacement[] | undefined,
): void {
  const template = SCENE_TEMPLATES[sceneId];
  const anchorMargin = 14; // 最遠オフセット(参道の-6m等)+プロップ半径を見込んだ安全マージン

  for (let attempt = 0; attempt < 20; attempt += 1) {
    const ax = Math.round(((visRand() * 2 - 1) * (half - anchorMargin)) / GRID) * GRID;
    const az = Math.round(((visRand() * 2 - 1) * (half - anchorMargin)) / GRID) * GRID;
    const sceneRot = visRand() * Math.PI * 2;
    const cos = Math.cos(sceneRot);
    const sin = Math.sin(sceneRot);

    const resolved: Array<{ kind: PropKind; px: number; pz: number; rotSteps: number }> = [];
    let ok = true;
    for (const member of template) {
      const px = ax + member.dx * cos - member.dz * sin;
      const pz = az + member.dx * sin + member.dz * cos;
      const fp = PROP_FOOTPRINTS[member.kind];

      if (Math.abs(px) + fp[0] / 2 > half - 3 || Math.abs(pz) + fp[1] / 2 > half - 3) {
        ok = false;
        break;
      }
      const nearSpawn = allSpawns.some(([sx, sz]) => Math.hypot(px - sx, pz - sz) < SPAWN_CLEARANCE);
      if (nearSpawn) {
        ok = false;
        break;
      }
      const propAabb = aabbOf(px, pz, fp[0] + 3, fp[1] + 3);
      if (buildingPlaced.some((b) => overlaps(b, propAabb, 0))) {
        ok = false;
        break;
      }
      const propFootAabb = aabbOf(px, pz, fp[0], fp[1]);
      if (propPlaced.some((b) => overlaps(b, propFootAabb, 1.5))) {
        ok = false;
        break;
      }
      // シーン内の既配置メンバー同士のクリアランス(テンプレ座標の想定内なら通常発生しない)
      if (resolved.some((r) => Math.hypot(r.px - px, r.pz - pz) < 1.5)) {
        ok = false;
        break;
      }

      const rotSteps = (Math.round(sceneRot / (Math.PI / 2)) + member.dRotSteps) & 3;
      resolved.push({ kind: member.kind, px, pz, rotSteps });
    }
    if (!ok || resolved.length === 0) continue;

    for (const r of resolved) {
      const propBoxes = buildProp(r.kind, r.px, r.pz, r.rotSteps, visRand, def.palette);
      boxes.push(...propBoxes);
      const fp = PROP_FOOTPRINTS[r.kind];
      propPlaced.push(aabbOf(r.px, r.pz, fp[0], fp[1]));
      if (placementsOut) {
        placementsOut.push({
          kind: r.kind,
          cx: r.px,
          cz: r.pz,
          rotRad: jitterRotRad(r.rotSteps, visRand, r.kind),
          scaleJitter: jitterScale(visRand),
        });
      }
    }
    return; // 配置成功
  }
  // 20回失敗 → このシーン箇所は諦める(既存の建造物配置と同じ方針。他配置は無傷)
}

/**
 * StageRecipe.objects に従い環境プロップを配置する。
 * 別シード(def.seed ^ 0x7e57ab1e)を使用→既存レイアウトRNG非汚染。
 * クリアランス: スポーン6m / 建造物AABB+2m / プロップ間1.5m
 *
 * placementsOut を渡すと、配置した全インスタンス(既存スキャッタ+ミニシーン共通)の
 * 視覚メタデータ(PropPlacement: kind/cx/cz/rotRad/scaleJitter)を追記する。
 * rotRad/scaleJitter は本関数内部で独立に導出した visRand(def.seedから派生する別の
 * mulberry32)でのみ消費するため、既存の rand(位置決定/量子化回転)の消費列には一切影響しない
 * — 既存ステージの配置結果(boxes)は placementsOut の有無に関わらず完全に同一。
 */
export function generateThemeObjects(
  def: StageDef,
  buildingPlaced: Aabb[],
  rand: () => number,
  placementsOut?: PropPlacement[],
  spawnOverride?: SpawnPoint[],
): BoxSpec[] {
  const objects = def.recipe?.objects;
  if (!objects?.length) return [];

  const half = def.size / 2;
  const boxes: BoxSpec[] = [];
  const propPlaced: Aabb[] = [];
  // 視覚ジッタ+ミニシーン専用の独立RNG(既存rand非汚染)。def.seedから派生する固定シード。
  const visRand = mulberry32(def.seed ^ 0x9e3779b9);

  // 固定スポーン座標を決定論的に再現(rand消費なし)
  // 境界壁の4m手前は、開始直後から不可視壁へ触れやすく「箱の内側」感を強めていた。
  // 22%内側へ入れ、背景世界を見渡せる余白と初動ルートを確保する。物理境界自体は従来位置。
  const edge = Math.round((half * 0.78) / GRID) * GRID;
  const allSpawns: [number, number][] = spawnOverride
    ? spawnOverride.map(([x, , z]) => [x, z])
    : [
        [edge, edge], [-edge, edge], [edge, -edge], [-edge, -edge],
        [0, edge], [0, -edge], [edge, 0], [-edge, 0],
        [edge / 2, -edge / 2], [-edge / 2, edge / 2],
      ];
  if (!spawnOverride) {
    const extraCount = Math.max(0, def.botCount - 6);
    for (let i = 0; i < extraCount; i++) {
      const ang = (i / Math.max(1, extraCount)) * Math.PI * 2 + 0.3;
      const r = edge * 0.6;
      allSpawns.push([
        Math.round((Math.cos(ang) * r) / GRID) * GRID,
        Math.round((Math.sin(ang) * r) / GRID) * GRID,
      ]);
    }
  }

  for (const entry of objects) {
    // ミニシーン(R53-S2): 独立RNG(visRand)のみを消費するため既存randの消費列は無傷。
    // count は「シーンを何箇所配置するか」。sceneId未設定のエントリは黙って無視する。
    if (entry.scatter === 'scene') {
      if (entry.sceneId) {
        for (let i = 0; i < entry.count; i += 1) {
          tryPlaceScene(entry.sceneId, def, half, allSpawns, buildingPlaced, propPlaced, boxes, visRand, placementsOut);
        }
      }
      continue;
    }

    const fp = PROP_FOOTPRINTS[entry.kind];

    // クラスター中心を1エントリにつき1回決定
    let clusterCx = 0;
    let clusterCz = 0;
    if (entry.scatter === 'cluster') {
      clusterCx = Math.round(((rand() * 2 - 1) * (half - 20)) / GRID) * GRID;
      clusterCz = Math.round(((rand() * 2 - 1) * (half - 20)) / GRID) * GRID;
    }

    // 300m級マップで十数個しか無かった生活物を増やす。GLB側は素材単位へ
    // マージされるため、密度を上げてもdraw callは増えず、衝突は既存の小型Boxだけを使う。
    const placementCount = Math.ceil(entry.count * 1.45);
    for (let n = 0; n < placementCount; n++) {
      let placedOk = false;
      for (let attempt = 0; attempt < 20; attempt++) {
        let px: number;
        let pz: number;

        if (entry.scatter === 'random') {
          px = Math.round(((rand() * 2 - 1) * (half - 10)) / GRID) * GRID;
          pz = Math.round(((rand() * 2 - 1) * (half - 10)) / GRID) * GRID;
        } else if (entry.scatter === 'perimeter') {
          const side = Math.floor(rand() * 4);
          const along = Math.round(((rand() * 2 - 1) * (half - 12)) / GRID) * GRID;
          const depth = Math.round((half - 8 - rand() * 12) / GRID) * GRID;
          switch (side) {
            case 0: px = along; pz = -depth; break;
            case 1: px = along; pz = depth; break;
            case 2: px = -depth; pz = along; break;
            default: px = depth; pz = along; break;
          }
        } else {
          // cluster
          const r = entry.clusterRadius ?? 10;
          px = Math.round((clusterCx + (rand() * 2 - 1) * r) / GRID) * GRID;
          pz = Math.round((clusterCz + (rand() * 2 - 1) * r) / GRID) * GRID;
          px = Math.max(-(half - 8), Math.min(half - 8, px));
          pz = Math.max(-(half - 8), Math.min(half - 8, pz));
        }

        // 建造物と同じく、プロップの実フットプリント全体を境界内へ収める。
        // perimeter/clusterの中心だけを制限していた旧経路では、塔型クレーンの
        // 片持ちブームが不可視壁を越える場合があった。
        if (Math.abs(px) + fp[0] / 2 > half - 3 || Math.abs(pz) + fp[1] / 2 > half - 3) continue;

        // スポーンクリアランス
        const nearSpawn = allSpawns.some(([sx, sz]) => Math.hypot(px - sx, pz - sz) < SPAWN_CLEARANCE);
        if (nearSpawn) continue;

        // 建造物クリアランス
        const propAabb = aabbOf(px, pz, fp[0] + 3, fp[1] + 3);
        if (buildingPlaced.some((b) => overlaps(b, propAabb, 0))) continue;

        // プロップ間クリアランス(1.5m)
        const propFootAabb = aabbOf(px, pz, fp[0], fp[1]);
        if (propPlaced.some((b) => overlaps(b, propFootAabb, 1.5))) continue;

        const propRot = Math.floor(rand() * 4);
        const propBoxes = buildProp(entry.kind, px, pz, propRot, rand, def.palette);
        boxes.push(...propBoxes);
        propPlaced.push(aabbOf(px, pz, fp[0], fp[1]));
        placedOk = true;
        // 視覚ジッタ(R53-S2): visRandのみ消費(既存randの消費列に影響しない=既存配置ビット不変)
        if (placementsOut) {
          placementsOut.push({
            kind: entry.kind,
            cx: px,
            cz: pz,
            rotRad: jitterRotRad(propRot, visRand, entry.kind),
            scaleJitter: jitterScale(visRand),
          });
        }
        break;
      }
      void placedOk;
    }
  }

  return boxes;
}

// シードから決定論的にレイアウトを生成する。障害物は原点対称に複製し、
// 対戦時にどのスポーンからも地形条件が同じになるようにする。

/**
 * Build a canonical placement from clean collections.  Branch selection
 * happens before this function, so a generated stage can never retain a
 * procedural district, prop, spawn, or cover from the legacy path.
 * @internal Exported only so this path can be audited without enabling a live stage.
 */
export function generateStageFromGeneratedPlacement(
  def: StageDef,
  placement: RuntimeStagePlacement,
): StageLayout {
  const rand = mulberry32(def.seed);
  const half = placement.mapSize / 2;
  const boxes: BoxSpec[] = [];
  const placed: Aabb[] = [];
  let numPlaced = 0;

  // Collision-authoritative ghost boundary at the canonical map size.
  for (const [x, z, w, d] of [
    [0, -(half + 0.5), placement.mapSize + 2, 1],
    [0, half + 0.5, placement.mapSize + 2, 1],
    [-(half + 0.5), 0, 1, placement.mapSize + 2],
    [half + 0.5, 0, 1, placement.mapSize + 2],
  ] as [number, number, number, number][]) {
    boxes.push({
      x,
      y: GHOST_WALL_H / 2,
      z,
      w,
      h: GHOST_WALL_H,
      d,
      color: def.palette.wall,
      emissive: false,
      ghost: true,
    });
  }

  // 1) Exactly two validated, playable landmark shells.
  const landmarkPlacements: LandmarkPlacement[] = placement.landmarks.map((landmark) => ({
    ...landmark,
    entrance: [...landmark.entrance],
    approach: {
      start: [...landmark.approach.start],
      end: [...landmark.approach.end],
      width: landmark.approach.width,
    },
  }));
  const districtPlacements: DistrictPlacement[] = landmarkPlacements.map((landmark) => ({
    kind: landmark.districtKind,
    cx: landmark.cx,
    cz: landmark.cz,
    rot: landmark.rot,
    width: landmark.width,
    depth: landmark.depth,
  }));
  for (const landmark of landmarkPlacements) {
    boxes.push(...buildLandmarkCombatShell(landmark, def.palette));
    placed.push(aabbOf(landmark.cx, landmark.cz, landmark.width, landmark.depth));
  }

  // 2) Reserve road capsules and authored entrance approaches before districts.
  for (const road of placement.roads) placed.push({ ...road.bounds });
  for (const landmark of landmarkPlacements) placed.push(approachAabb(landmark.approach));

  // 3) Rebuild ordinary districts exclusively from the canonical placement.
  const ordinaryDistrictBoxes: BoxSpec[] = [];
  for (const [districtIndex, district] of placement.ordinaryDistricts.entries()) {
    const runtimeDistrict: DistrictPlacement = { ...district };
    const baseBoxes = generateBuilding(
      runtimeDistrict.kind,
      runtimeDistrict.cx,
      runtimeDistrict.cz,
      runtimeDistrict.rot,
      def.palette,
    );
    const districtBoxes: BoxSpec[] = baseBoxes.map((box) => ({
      ...box,
      district: runtimeDistrict.kind,
    }));
    if (def.id === 'kairou') {
      districtBoxes.push(buildKairouUrbanVolume(
        runtimeDistrict,
        districtIndex,
        baseBoxes,
        def.palette,
      ));
    }
    boxes.push(...districtBoxes);
    ordinaryDistrictBoxes.push(...districtBoxes);
    districtPlacements.push(runtimeDistrict);
    placed.push(aabbOf(
      runtimeDistrict.cx,
      runtimeDistrict.cz,
      runtimeDistrict.width,
      runtimeDistrict.depth,
    ));
  }
  if (def.id === 'souko') {
    boxes.push(...buildSoukoRoofMonitorColliders(ordinaryDistrictBoxes, def.palette));
  }

  // 4) Canonical spawns are adopted only after every structural lot exists.
  const playerSpawns: SpawnPoint[] = placement.playerSpawns.map((spawn) => [...spawn]);
  const botSpawns: SpawnPoint[] = placement.botSpawns.map((spawn) => [...spawn]);
  const spawnGuards = [...playerSpawns, ...botSpawns];

  // 5) Props and cover are freshly regenerated against all reservations.
  const propRand = mulberry32(def.seed ^ 0x7e57ab1e);
  const propPlacements: PropPlacement[] = [];
  boxes.push(...generateThemeObjects(def, placed, propRand, propPlacements, spawnGuards));
  boxes.push(...generateExtendedTerrain(def, half));
  boxes.push(...generateSilhouette(def, half, rand));

  let attempts = 0;
  while (numPlaced < def.obstacleCount && attempts < def.obstacleCount * 30) {
    attempts += 1;
    const x = Math.round(((rand() * 2 - 1) * (half - 5)) / GRID) * GRID;
    const z = Math.round(((rand() * 2 - 1) * (half - 5)) / GRID) * GRID;
    const w = Math.round(2 + rand() * 6);
    const d = Math.round(2 + rand() * 6);
    const heightRoll = rand();
    const h = heightRoll < 0.58
      ? 1 + rand() * 0.35
      : heightRoll < 0.92
        ? 1.8 + rand() * Math.max(0.2, Math.min(3.2, def.maxHeight) - 1.8)
        : 3.5 + rand() * Math.max(0.2, Math.min(6.5, def.maxHeight) - 3.5);
    if (spawnGuards.some(([sx, , sz]) => Math.hypot(x - sx, z - sz) < SPAWN_CLEARANCE)) continue;
    const cover = aabbOf(x, z, w, d);
    if (placed.some((reserved) => overlaps(reserved, cover, 1))) continue;
    const accent = rand() < 0.18;
    const color = accent ? def.palette.accent : def.palette.obstacle;
    boxes.push({
      x,
      y: h / 2,
      z,
      w,
      h,
      d,
      color,
      emissive: accent && def.palette.emissiveAccent,
    });
    placed.push(cover);
    numPlaced += 1;

    const mirror = aabbOf(-x, -z, w, d);
    const mirrorNearSpawn = spawnGuards.some(
      ([sx, , sz]) => Math.hypot(-x - sx, -z - sz) < SPAWN_CLEARANCE,
    );
    if (
      (x !== 0 || z !== 0)
      && !mirrorNearSpawn
      && !placed.some((reserved) => overlaps(reserved, mirror, 1))
    ) {
      boxes.push({
        x: -x,
        y: h / 2,
        z: -z,
        w,
        h,
        d,
        color,
        emissive: accent && def.palette.emissiveAccent,
      });
      placed.push(mirror);
      numPlaced += 1;
    }
  }

  const breakRng = mulberry32(def.seed ^ 0x1a2b3c4d);
  for (const box of boxes) {
    if (box.ghost || box.decor || box.structural) continue;
    const maxXZ = Math.max(box.w, box.d);
    const minXZ = Math.min(box.w, box.d);
    if (maxXZ > 8 || box.h < 0.8 || box.h > 10) continue;
    if (minXZ > 0 && maxXZ / minXZ > 5) continue;
    if (breakRng() > 0.35) continue;
    const volume = box.w * box.h * box.d;
    box.breakable = {
      hp: Math.max(120, Math.min(260, Math.round(120 + Math.sqrt(volume) * 10))),
    };
  }

  return {
    placementProvenance: {
      placementSource: 'canonical-solver-v2-authoring',
      placementSolverSha256: GENERATED_STAGE_PLACEMENT_PROVENANCE.solverSha256,
      stageWorldCatalogSha256: GENERATED_STAGE_PLACEMENT_PROVENANCE.catalogSha256,
    },
    boxes,
    playerSpawns,
    botSpawns,
    propPlacements,
    districtPlacements,
    landmarkPlacements,
  };
}

export function generateStage(def: StageDef): StageLayout {
  const generated = resolveGeneratedStagePlacement(def);
  if (generated.placement) return generateStageFromGeneratedPlacement(def, generated.placement);
  const rand = mulberry32(def.seed);
  const half = def.size / 2;
  const boxes: BoxSpec[] = [];

  // ① 不可視境界コライダーリング (ghost walls)
  // 高さ GHOST_WALL_H=24m の透明壁。コライダーのみ生成(match.ts が isGhost でスキップ)。
  for (const [x, z, w, d] of [
    [0, -(half + 0.5), def.size + 2, 1],
    [0, half + 0.5, def.size + 2, 1],
    [-(half + 0.5), 0, 1, def.size + 2],
    [half + 0.5, 0, 1, def.size + 2],
  ] as [number, number, number, number][]) {
    boxes.push({
      x,
      y: GHOST_WALL_H / 2,
      z,
      w,
      h: GHOST_WALL_H,
      d,
      color: def.palette.wall,
      emissive: false,
      ghost: true,
    });
  }

  // ② スポーン配置
  // 不可視境界の直前で開始する「箱の中」感と開始直後の壁接触を避ける。
  // generateThemeObjectsと完全に同じ式にし、建物/プロップのスポーン離隔契約を一致させる。
  const edge = Math.round((half * 0.78) / GRID) * GRID;
  const abbeyStage = def.recipe?.buildings[0] === 'abbey';
  // Keep at least 30m between the approach spawn and the abbey's 62m east/
  // west wall extent.  Z04's slightly smaller map previously produced 86m
  // (24m clearance); 92m preserves the same gate-axis composition while
  // satisfying the dense-world release clearance gate.
  const abbeyApproach = Math.round(Math.max(half * 0.56, 92) / GRID) * GRID;
  const corners: SpawnPoint[] = abbeyStage
    ? [
        // 修道城の回転はシードで固定され、東西軸に幅広の城門がある。
        // 第1スポーンを東門街道上に置き、プレイ開始時に城壁ではなく門を見せる。
        [abbeyApproach, 0, 0],
        [-abbeyApproach, 0, 0],
        [0, 0, abbeyApproach],
        [0, 0, -abbeyApproach],
      ]
    : [
        [edge, 0, edge],
        [-edge, 0, edge],
        [edge, 0, -edge],
        [-edge, 0, -edge],
      ];
  const botSpawns: SpawnPoint[] = [
    [0, 0, edge],
    [0, 0, -edge],
    [edge, 0, 0],
    [-edge, 0, 0],
    [edge / 2, 0, -edge / 2],
    [-edge / 2, 0, edge / 2],
  ];
  const baseCount = botSpawns.length; // 6
  const extra = Math.max(0, def.botCount - baseCount);
  // 巨大修道城は中心だけで123×100mを占める。通常面の多人数ボット用
  // 内周リングをそのまま使うと、ボット位置が城壁に重なり中央ランドマーク
  // 自体が配置拒否される。城面だけ外周の入城ルート側へ初期位置を退避する。
  const extraSpawnRadius = abbeyStage ? edge * 0.84 : edge * 0.6;
  for (let i = 0; i < extra; i += 1) {
    const ang = (i / Math.max(1, extra)) * Math.PI * 2 + 0.3;
    const r = extraSpawnRadius;
    botSpawns.push([
      Math.round((Math.cos(ang) * r) / GRID) * GRID,
      0,
      Math.round((Math.sin(ang) * r) / GRID) * GRID,
    ]);
  }
  let spawnGuards: SpawnPoint[] = [...corners, ...botSpawns];
  const landmarkPlacements = DENSE_WORLD_V5_PROOF_STAGES.has(def.id)
    ? buildDenseWorldV5Landmarks(def, [], [])
    : [];
  if (DENSE_WORLD_V5_PROOF_STAGES.has(def.id)) {
    const streetPlayers = buildDenseWorldV5PlayerSpawns(def, landmarkPlacements);
    corners.splice(0, corners.length, ...streetPlayers);
    spawnGuards = [...corners, ...botSpawns];
  }

  // ③ 建造物の配置 (recipe 指定時)
  // 建造物 AABB は placed にも追加し、後続の障害物が重ならないようにする。
  const placed: Aabb[] = [];
  const districtPlacements: DistrictPlacement[] = [];
  let numPlaced = 0; // 障害物の配置数カウント(建造物は含まない)

  if (def.recipe && DENSE_WORLD_V5_PROOF_STAGES.has(def.id)) {
    const plan = buildDenseWorldV5Plan(def, corners, [], landmarkPlacements);
    const landmarkDistricts: DistrictPlacement[] = landmarkPlacements.map((landmark) => ({
      kind: landmark.districtKind,
      cx: landmark.cx,
      cz: landmark.cz,
      rot: landmark.rot,
      width: landmark.width,
      depth: landmark.depth,
    }));
    // Preserve the established origin-first district contract where possible;
    // abbey landmark 0 itself owns the origin.
    if (landmarkPlacements[0]?.collisionTemplate === 'abbey') {
      districtPlacements.push(...landmarkDistricts, ...plan);
    } else {
      districtPlacements.push(...plan.slice(0, 1), ...landmarkDistricts, ...plan.slice(1));
    }
    for (const landmark of landmarkPlacements) {
      boxes.push(...buildLandmarkCombatShell(landmark, def.palette));
      placed.push(aabbOf(landmark.cx, landmark.cz, landmark.width, landmark.depth));
      // Entrance approaches are authored gameplay streets, not spare lots.
      // Reserve them from both themed props and generic symmetric cover.
      placed.push(approachAabb(landmark.approach));
    }
    for (const [districtIndex, district] of plan.entries()) {
      const baseBoxes = generateBuilding(
        district.kind,
        district.cx,
        district.cz,
        district.rot,
        def.palette,
      );
      // Keep the mutable collection at the public BoxSpec contract.  The
      // mapped base boxes all have a district, while the supported upper
      // volume is returned as a BoxSpec whose district is intentionally
      // optional at the interface boundary.
      const buildBoxes: BoxSpec[] = baseBoxes.map((box) => ({
        ...box,
        district: district.kind,
      }));
      if (def.id === 'kairou') {
        buildBoxes.push(buildKairouUrbanVolume(
          district,
          districtIndex,
          baseBoxes,
          def.palette,
        ));
      }
      boxes.push(...buildBoxes);
      placed.push(aabbOf(district.cx, district.cz, district.width, district.depth));
    }
  } else if (def.recipe) {
    // 300m級マップへ2〜4棟だけを散らしていた旧構成は、ランドマークの周囲だけが豪華で
    // 残りが空き地に見える主因だった。固有の建築語彙はそのまま循環再利用し、通常面を
    // 10〜12地区へ拡張する。配置は既存のAABB重複／スポーンクリアランス判定を全て通るため、
    // 見た目だけの通り抜ける家や初期スポーン埋まりは作らない。巨大abbey面は中央の
    // 123×100m城郭自体が複数地区相当なので、重複生成せず従来の1棟を維持する。
    const authoredBuildings = def.recipe.buildings;
    const targetDistrictCount = authoredBuildings.includes('abbey')
      ? authoredBuildings.length
      : Math.min(12, Math.max(10, authoredBuildings.length * 3));
    // 各ステージの開始視線に、倉庫より大聖堂、バンカーよりアリーナのような
    // 最も大きい固有建築を置く。残りは元の語彙順で循環し、全棟同じ外観にはしない。
    const centralBuilding = [...authoredBuildings].sort((a, b) => {
      const [aw, ad] = getBuildingFootprint(a, 0);
      const [bw, bd] = getBuildingFootprint(b, 0);
      return bw * bd - aw * ad;
    })[0]!;
    const districtVocabulary = [centralBuilding, ...authoredBuildings.filter((kind) => kind !== centralBuilding)];
    const districtPlan = Array.from(
      { length: targetDistrictCount },
      (_, index) => districtVocabulary[index % districtVocabulary.length]!,
    );
    for (const [buildingIndex, bk] of districtPlan.entries()) {
      let placed_ok = false;
      for (let attempt = 0; attempt < 180; attempt++) {
        // 巨大な固定マップでは中心48%だけに建物を詰めると同じ箱庭に見える。
        // 62%まで地区を広げ、外周スポーンとの距離は下のAABB実距離で厳密に守る。
        // 各面の先頭地区は中心の実体ランドマークとする。常に開始視線の先にテーマ建築があり、
        // 遠景画像だけで場所を表すことを避ける。衝突・階段・屋上・AI導線は通常建築と同じ。
        const centralLandmark = buildingIndex === 0 && attempt === 0;
        // 中央固定時もRNGを3回消費し、後続地区/遮蔽の決定論ストリームをずらさない。
        const randomBx = Math.round(((rand() * 2 - 1) * half * 0.70) / GRID) * GRID;
        const randomBz = Math.round(((rand() * 2 - 1) * half * 0.70) / GRID) * GRID;
        const randomRot = Math.floor(rand() * 4);
        const bx = centralLandmark ? 0 : randomBx;
        const bz = centralLandmark ? 0 : randomBz;
        const rot = centralLandmark ? (def.seed & 3) : randomRot;
        const [fpW, fpD] = getBuildingFootprint(bk, rot);

        // 境界内チェック (フットプリント全体が half-3 以内)
        if (Math.abs(bx) + fpW / 2 > half - 3 || Math.abs(bz) + fpD / 2 > half - 3) continue;

        const bAabb = aabbOf(bx, bz, fpW + 3, fpD + 3);

        // スポーン近接チェック
        const nearSpawn = spawnGuards.some(([sx, , sz]) => {
          const dx = Math.max(0, Math.abs(bx - sx) - fpW / 2);
          const dz = Math.max(0, Math.abs(bz - sz) - fpD / 2);
          return Math.hypot(dx, dz) < BUILD_SPAWN_CLEAR;
        });
        if (nearSpawn) continue;

        // 他建造物との重複チェック
        if (placed.some((p) => overlaps(p, bAabb, 0))) continue;

        // 配置成功
        const buildBoxes = generateBuilding(bk, bx, bz, rot, def.palette).map((box) => ({
          ...box,
          district: bk,
        }));
        boxes.push(...buildBoxes);
        placed.push(aabbOf(bx, bz, fpW, fpD));
        districtPlacements.push({ kind: bk, cx: bx, cz: bz, rot, width: fpW, depth: fpD });
        placed_ok = true;
        break;
      }
      // 配置失敗時はスキップ(180回試行で安全な地区アンカーが見つからない場合のみ)
      void placed_ok;
    }
  }

  // The legacy spawn ring predates collision-authoritative dense districts and
  // can land inside their footprints.  Once all v5 colliders exist, replace it
  // with deterministic points on the preserved street graph, then reuse that
  // same truth for prop and random-cover clearance checks.
  if (DENSE_WORLD_V5_PROOF_STAGES.has(def.id)) {
    const streetBots = buildDenseWorldV5BotSpawns(
      def,
      corners,
      districtPlacements,
      landmarkPlacements,
    );
    botSpawns.splice(0, botSpawns.length, ...streetBots);
    spawnGuards = [...corners, ...botSpawns];
  }

  // ③.5 テーマ環境オブジェクト(別シード・既存レイアウトRNG非汚染)
  const propRand = mulberry32(def.seed ^ 0x7e57ab1e);
  const propPlacements: PropPlacement[] = [];
  boxes.push(...generateThemeObjects(
    def,
    placed,
    propRand,
    propPlacements,
    DENSE_WORLD_V5_PROOF_STAGES.has(def.id) ? spawnGuards : undefined,
  ));

  // ④ 拡張視覚地形 + 遠景シルエット(decor = 境界外装飾)
  boxes.push(...generateExtendedTerrain(def, half));
  boxes.push(...generateSilhouette(def, half, rand));

  // ⑤ ランダム障害物 (原点対称複製)
  let attempts = 0;
  while (numPlaced < def.obstacleCount && attempts < def.obstacleCount * 30) {
    attempts += 1;
    const x = Math.round(((rand() * 2 - 1) * (half - 5)) / GRID) * GRID;
    const z = Math.round(((rand() * 2 - 1) * (half - 5)) / GRID) * GRID;
    const w = Math.round(2 + rand() * 6);
    const d = Math.round(2 + rand() * 6);
    // ランダム遮蔽は背の低い実用カバー中心にする。高さの主役は建築地区が担う。
    const heightRoll = rand();
    const h = heightRoll < 0.58
      ? 1 + rand() * 0.35
      : heightRoll < 0.92
        ? 1.8 + rand() * Math.max(0.2, Math.min(3.2, def.maxHeight) - 1.8)
        : 3.5 + rand() * Math.max(0.2, Math.min(6.5, def.maxHeight) - 3.5);

    const nearSpawn = spawnGuards.some(
      ([sx, , sz]) => Math.hypot(x - sx, z - sz) < SPAWN_CLEARANCE,
    );
    if (nearSpawn) continue;

    const box = aabbOf(x, z, w, d);
    if (placed.some((p) => overlaps(p, box, 1))) continue;

    const accent = rand() < 0.18;
    const color = accent ? def.palette.accent : def.palette.obstacle;
    boxes.push({ x, y: h / 2, z, w, h, d, color, emissive: accent && def.palette.emissiveAccent });
    placed.push(box);
    numPlaced += 1;

    // 原点対称複製
    const mirror = aabbOf(-x, -z, w, d);
    const mirrorNearSpawn = spawnGuards.some(
      ([sx, , sz]) => Math.hypot(-x - sx, -z - sz) < SPAWN_CLEARANCE,
    );
    if ((x !== 0 || z !== 0) && !mirrorNearSpawn && !placed.some((p) => overlaps(p, mirror, 1))) {
      boxes.push({
        x: -x,
        y: h / 2,
        z: -z,
        w,
        h,
        d,
        color,
        emissive: accent && def.palette.emissiveAccent,
      });
      placed.push(mirror);
      numPlaced += 1;
    }
  }

  // ⑥ breakable 付与 ── 小〜中型遮蔽プロップの約35%に決定論的にHP付与する。
  // 別シード(def.seed ^ 0x1a2b3c4d)を使うことで既存レイアウトRNGに影響を与えない。
  // 除外基準: ghost / decor / 幅>8(構造壁) / h<0.8(床・屋根スラブ) / h>10(巨大柱)
  //           / 縦横アスペクト>5(細長い壁パネル)
  // HP: 120-260 の範囲で体積の平方根に比例(小さい箱は折れやすく、大きい箱は頑丈)。
  const breakRng = mulberry32(def.seed ^ 0x1a2b3c4d);
  for (const box of boxes) {
    if (box.ghost || box.decor || box.structural) continue;
    const maxXZ = Math.max(box.w, box.d);
    const minXZ = Math.min(box.w, box.d);
    if (maxXZ > 8 || box.h < 0.8 || box.h > 10) continue;
    if (minXZ > 0 && maxXZ / minXZ > 5) continue;
    if (breakRng() > 0.35) continue;
    const vol = box.w * box.h * box.d;
    box.breakable = { hp: Math.max(120, Math.min(260, Math.round(120 + Math.sqrt(vol) * 10))) };
  }

  return {
    placementProvenance: {
      placementSource: 'runtime-release',
      placementSolverSha256: GENERATED_STAGE_PLACEMENT_PROVENANCE.solverSha256,
      stageWorldCatalogSha256: GENERATED_STAGE_PLACEMENT_PROVENANCE.catalogSha256,
    },
    boxes,
    playerSpawns: corners,
    botSpawns,
    propPlacements,
    districtPlacements,
    landmarkPlacements,
  };
}
