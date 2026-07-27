import * as THREE from 'three';
import type { GraphicsQuality } from '../core/settings';
import type { PropPlacement } from '../game/stage';

const TIER_RANK: Record<GraphicsQuality, number> = { low: 0, medium: 1, high: 2 };

export interface AaaAssetInstance {
  readonly position: readonly [number, number, number];
  readonly rotation?: readonly [number, number, number];
  readonly scale?: number | readonly [number, number, number];
}

export interface AaaAssetLod {
  readonly url: string;
  readonly distance: number;
}

export interface AaaStagePlacementProvenance {
  readonly placementSource: 'runtime-release' | 'canonical-solver-v2-authoring';
  readonly placementSolverSha256: string;
  readonly stageWorldCatalogSha256: string;
  /** Stable hash of this stage's normalized authoritative layout payload. */
  readonly stageLayoutSha256?: string;
  /** Optional content hash for a manifest producer that fingerprints the GLB. */
  readonly assetSha256?: string;
}

export interface AaaAssetEntry {
  readonly id: string;
  readonly url: string;
  readonly stages?: readonly string[];
  readonly propKind?: string;
  readonly instances?: readonly AaaAssetInstance[];
  readonly minTier?: GraphicsQuality;
  readonly yOffset?: number;
  readonly scale?: number;
  readonly rotationOffset?: number;
  readonly maxInstances?: number;
  readonly castShadow?: boolean;
  readonly receiveShadow?: boolean;
  readonly replacesDistantMatte?: boolean;
  readonly replacesProceduralProps?: boolean;
  /**
   * The imported stage contains the authoritative BoxSpec visual shell and
   * cinematic architecture layers. Physics remains owned by Match, but the
   * procedural meshes must be hidden after a successful shader compile to
   * avoid coplanar/z-fighting duplicates.
   */
  readonly replacesProceduralStageShell?: boolean;
  /**
   * Stage-scoped placement identity. Global manifest SHA fields are not enough:
   * a partially deployed manifest may otherwise authorize a GLB built from a
   * different stage layout while retaining the same stable URL.
   */
  readonly stageProvenance?: AaaStagePlacementProvenance;
  readonly lods?: readonly AaaAssetLod[];
}

export interface AaaAssetManifest {
  readonly version: 1;
  readonly generatorVersion?: string;
  readonly generatorSha?: string;
  readonly ktx2TranscoderPath?: string;
  readonly dracoDecoderPath?: string;
  readonly assets: readonly AaaAssetEntry[];
}

export interface AaaAssetLoadOptions {
  readonly stageId: string;
  readonly tier: GraphicsQuality;
  readonly propPlacements: readonly PropPlacement[];
  readonly placementProvenance?: AaaStagePlacementProvenance;
  readonly manifestUrl?: string;
}

export interface AaaAssetLoadReport {
  readonly requested: number;
  readonly loaded: number;
  readonly failed: number;
  readonly errors: readonly string[];
}

interface AaaAssetSourcePlan {
  readonly url: string;
  readonly lods: readonly AaaAssetLod[];
}

/**
 * A monolithic stage GLB already contains the complete playable world. Keeping
 * all three variants resident defeats its LOD budget, so quality selects one
 * transport/decode source up front: high=LOD0 and medium=LOD1. Low never reaches
 * this function because load() keeps the procedural fail-open world.
 *
 * Non-stage assets retain distance-based THREE.LOD behaviour.
 */
function sourcePlanForTier(
  entry: AaaAssetEntry,
  tier: GraphicsQuality,
): AaaAssetSourcePlan {
  if (tier === 'low') {
    throw new Error('external stage assets are disabled on low tier');
  }
  if (!entry.replacesProceduralStageShell) {
    return { url: entry.url, lods: entry.lods ?? [] };
  }
  if (tier === 'high') return { url: entry.url, lods: [] };
  const mediumSource = entry.lods?.[0];
  if (!mediumSource) {
    throw new Error('monolithic stage requires LOD1 for medium tier');
  }
  return { url: mediumSource.url, lods: [] };
}

function isFiniteTuple(value: unknown, length: number): value is readonly number[] {
  return (
    Array.isArray(value) &&
    value.length === length &&
    value.every((part) => typeof part === 'number' && Number.isFinite(part))
  );
}

function isSafeLocalPath(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length > 0 &&
    !value.startsWith('/') &&
    !value.includes('..') &&
    !/[?#]/.test(value) &&
    !/^[a-z][a-z\d+.-]*:/i.test(value)
  );
}

function readTier(value: unknown): GraphicsQuality | undefined {
  return value === 'low' || value === 'medium' || value === 'high' ? value : undefined;
}

const SHA256_PATTERN = /^[a-f\d]{64}$/;

function readSha256(value: unknown, field: string): string {
  if (typeof value !== 'string' || !SHA256_PATTERN.test(value)) {
    throw new Error(`${field} must be a lowercase SHA-256`);
  }
  return value;
}

function readOptionalNonEmptyString(value: unknown, field: string): string | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error(`${field} is invalid`);
  }
  return value;
}

function readStageProvenance(
  value: unknown,
  field: string,
): AaaStagePlacementProvenance {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${field} must be an object`);
  }
  const raw = value as Record<string, unknown>;
  if (
    raw.placementSource !== 'runtime-release' &&
    raw.placementSource !== 'canonical-solver-v2-authoring'
  ) {
    throw new Error(`${field}.placementSource is invalid`);
  }
  const stageLayoutSha256 = raw.stageLayoutSha256 === undefined
    ? undefined
    : readSha256(raw.stageLayoutSha256, `${field}.stageLayoutSha256`);
  const assetSha256 = raw.assetSha256 === undefined
    ? undefined
    : readSha256(raw.assetSha256, `${field}.assetSha256`);
  if (!stageLayoutSha256 && !assetSha256) {
    throw new Error(`${field} requires stageLayoutSha256 or assetSha256`);
  }
  return {
    placementSource: raw.placementSource,
    placementSolverSha256: readSha256(
      raw.placementSolverSha256,
      `${field}.placementSolverSha256`,
    ),
    stageWorldCatalogSha256: readSha256(
      raw.stageWorldCatalogSha256,
      `${field}.stageWorldCatalogSha256`,
    ),
    stageLayoutSha256,
    assetSha256,
  };
}

/** ネットワーク入力を信用せず、ロード前にmanifestを狭いスキーマへ正規化する。 */
export function parseAaaAssetManifest(value: unknown): AaaAssetManifest {
  if (!value || typeof value !== 'object') throw new Error('AAA asset manifest must be an object');
  const raw = value as Record<string, unknown>;
  if (raw.version !== 1) throw new Error('unsupported AAA asset manifest version');
  if (!Array.isArray(raw.assets)) throw new Error('AAA asset manifest.assets must be an array');
  const assets: AaaAssetEntry[] = raw.assets.map((candidate, index) => {
    if (!candidate || typeof candidate !== 'object') throw new Error(`asset[${index}] must be an object`);
    const item = candidate as Record<string, unknown>;
    if (typeof item.id !== 'string' || item.id.length === 0) throw new Error(`asset[${index}].id is invalid`);
    if (!isSafeLocalPath(item.url)) throw new Error(`asset[${index}].url must be a safe relative path`);
    const minTier = item.minTier === undefined ? undefined : readTier(item.minTier);
    if (item.minTier !== undefined && !minTier) throw new Error(`asset[${index}].minTier is invalid`);
    const stages = item.stages === undefined
      ? undefined
      : Array.isArray(item.stages) && item.stages.every((part) => typeof part === 'string')
        ? item.stages as string[]
        : null;
    if (stages === null) throw new Error(`asset[${index}].stages is invalid`);
    const instances = item.instances === undefined
      ? undefined
      : Array.isArray(item.instances)
        ? item.instances.map((entry, instanceIndex): AaaAssetInstance => {
            if (!entry || typeof entry !== 'object') {
              throw new Error(`asset[${index}].instances[${instanceIndex}] is invalid`);
            }
            const instance = entry as Record<string, unknown>;
            if (!isFiniteTuple(instance.position, 3)) {
              throw new Error(`asset[${index}].instances[${instanceIndex}].position is invalid`);
            }
            if (instance.rotation !== undefined && !isFiniteTuple(instance.rotation, 3)) {
              throw new Error(`asset[${index}].instances[${instanceIndex}].rotation is invalid`);
            }
            const scale = instance.scale;
            if (
              scale !== undefined &&
              !(typeof scale === 'number' && Number.isFinite(scale) && scale > 0) &&
              !isFiniteTuple(scale, 3)
            ) {
              throw new Error(`asset[${index}].instances[${instanceIndex}].scale is invalid`);
            }
            return {
              position: instance.position as unknown as readonly [number, number, number],
              rotation: instance.rotation as readonly [number, number, number] | undefined,
              scale: scale as number | readonly [number, number, number] | undefined,
            };
          })
        : null;
    if (instances === null) throw new Error(`asset[${index}].instances is invalid`);
    const lods = item.lods === undefined
      ? undefined
      : Array.isArray(item.lods)
        ? item.lods.map((entry, lodIndex): AaaAssetLod => {
            if (!entry || typeof entry !== 'object') throw new Error(`asset[${index}].lods[${lodIndex}] is invalid`);
            const lod = entry as Record<string, unknown>;
            if (!isSafeLocalPath(lod.url) || typeof lod.distance !== 'number' || !Number.isFinite(lod.distance) || lod.distance <= 0) {
              throw new Error(`asset[${index}].lods[${lodIndex}] is invalid`);
            }
            return { url: lod.url, distance: lod.distance };
          })
        : null;
    if (lods === null) throw new Error(`asset[${index}].lods is invalid`);
    if (lods?.some((lod, lodIndex) => lodIndex > 0 && lod.distance <= lods[lodIndex - 1]!.distance)) {
      throw new Error(`asset[${index}].lods distances must be strictly increasing`);
    }
    if (item.replacesDistantMatte !== undefined && typeof item.replacesDistantMatte !== 'boolean') {
      throw new Error(`asset[${index}].replacesDistantMatte is invalid`);
    }
    if (item.replacesProceduralProps !== undefined && typeof item.replacesProceduralProps !== 'boolean') {
      throw new Error(`asset[${index}].replacesProceduralProps is invalid`);
    }
    if (
      item.replacesProceduralStageShell !== undefined &&
      typeof item.replacesProceduralStageShell !== 'boolean'
    ) {
      throw new Error(`asset[${index}].replacesProceduralStageShell is invalid`);
    }
    const positiveNumber = (field: string): number | undefined => {
      const fieldValue = item[field];
      if (fieldValue === undefined) return undefined;
      if (typeof fieldValue !== 'number' || !Number.isFinite(fieldValue) || fieldValue <= 0) {
        throw new Error(`asset[${index}].${field} is invalid`);
      }
      return fieldValue;
    };
    const finiteNumber = (field: string): number | undefined => {
      const fieldValue = item[field];
      if (fieldValue === undefined) return undefined;
      if (typeof fieldValue !== 'number' || !Number.isFinite(fieldValue)) {
        throw new Error(`asset[${index}].${field} is invalid`);
      }
      return fieldValue;
    };
    return {
      id: item.id,
      url: item.url,
      stages,
      propKind: typeof item.propKind === 'string' ? item.propKind : undefined,
      instances,
      minTier,
      yOffset: finiteNumber('yOffset'),
      scale: positiveNumber('scale'),
      rotationOffset: finiteNumber('rotationOffset'),
      maxInstances: positiveNumber('maxInstances'),
      castShadow: typeof item.castShadow === 'boolean' ? item.castShadow : undefined,
      receiveShadow: typeof item.receiveShadow === 'boolean' ? item.receiveShadow : undefined,
      replacesDistantMatte: item.replacesDistantMatte as boolean | undefined,
      replacesProceduralProps: item.replacesProceduralProps as boolean | undefined,
      replacesProceduralStageShell: item.replacesProceduralStageShell as boolean | undefined,
      stageProvenance: item.stageProvenance === undefined
        ? undefined
        : readStageProvenance(item.stageProvenance, `asset[${index}].stageProvenance`),
      lods,
    };
  });
  const optionalPath = (field: string): string | undefined => {
    const path = raw[field];
    if (path === undefined) return undefined;
    if (!isSafeLocalPath(path)) throw new Error(`${field} must be a safe relative path`);
    return path.endsWith('/') ? path : `${path}/`;
  };
  return {
    version: 1,
    generatorVersion: readOptionalNonEmptyString(raw.generatorVersion, 'generatorVersion'),
    generatorSha: raw.generatorSha === undefined
      ? undefined
      : readSha256(raw.generatorSha, 'generatorSha'),
    ktx2TranscoderPath: optionalPath('ktx2TranscoderPath'),
    dracoDecoderPath: optionalPath('dracoDecoderPath'),
    assets,
  };
}

function replacesProceduralStage(entry: AaaAssetEntry): boolean {
  return entry.replacesDistantMatte === true ||
    entry.replacesProceduralProps === true ||
    entry.replacesProceduralStageShell === true;
}

function stageReplacementPreflightError(
  entry: AaaAssetEntry,
  manifest: AaaAssetManifest,
  options: AaaAssetLoadOptions,
): string | null {
  if (!replacesProceduralStage(entry)) return null;
  if (entry.stages?.length !== 1 || entry.stages[0] !== options.stageId) {
    return 'replacement entry must target exactly the active stage';
  }
  if (!options.placementProvenance) return 'active stage placement provenance is missing';
  if (!entry.stageProvenance) return 'manifest stageProvenance is missing';
  for (const key of [
    'placementSource',
    'placementSolverSha256',
    'stageWorldCatalogSha256',
  ] as const) {
    if (entry.stageProvenance[key] !== options.placementProvenance[key]) {
      return `manifest stageProvenance.${key} does not match the active layout`;
    }
  }
  if (!manifest.generatorVersion) return 'manifest generatorVersion is missing';
  if (!manifest.generatorSha) return 'manifest generatorSha is missing';
  return null;
}

function validateStageSourceProvenance(
  source: THREE.Object3D,
  entry: AaaAssetEntry,
  manifest: AaaAssetManifest,
  options: AaaAssetLoadOptions,
): void {
  if (!replacesProceduralStage(entry)) return;
  const placement = entry.stageProvenance;
  if (!placement || !manifest.generatorVersion || !manifest.generatorSha) {
    throw new Error('stage replacement provenance preflight was not completed');
  }
  const expected = {
    hibanaStage: options.stageId,
    hibanaPlacementSource: placement.placementSource,
    hibanaPlacementSolverSha256: placement.placementSolverSha256,
    hibanaStageWorldCatalogSha256: placement.stageWorldCatalogSha256,
    hibanaGeneratorVersion: manifest.generatorVersion,
    hibanaGeneratorSha: manifest.generatorSha,
    ...(placement.stageLayoutSha256
      ? { hibanaStageLayoutSha256: placement.stageLayoutSha256 }
      : {}),
  } as const;
  const nodes: THREE.Object3D[] = [];
  for (const child of source.children) child.traverse((node) => nodes.push(node));
  if (nodes.length === 0) throw new Error('GLB has no stage nodes');
  for (const [index, node] of nodes.entries()) {
    for (const [key, expectedValue] of Object.entries(expected)) {
      if (node.userData[key] !== expectedValue) {
        throw new Error(`GLB node[${index}].${key} provenance mismatch`);
      }
    }
  }
}

interface ObjectResources {
  readonly skeletons: Set<THREE.Skeleton>;
  readonly textures: Set<THREE.Texture>;
  readonly imageBitmaps: Set<ImageBitmap>;
  readonly geometries: Set<THREE.BufferGeometry>;
  readonly materials: Set<THREE.Material>;
}

function collectMaterialTextures(material: THREE.Material, textures: Set<THREE.Texture>): void {
  const add = (value: unknown): void => {
    if (value instanceof THREE.Texture) textures.add(value);
    else if (Array.isArray(value)) for (const entry of value) add(entry);
  };
  for (const value of Object.values(material)) add(value);
  if (material instanceof THREE.ShaderMaterial) {
    for (const uniform of Object.values(material.uniforms)) add(uniform.value);
  }
}

function collectObjectResources(roots: Iterable<THREE.Object3D>): ObjectResources {
  const skeletons = new Set<THREE.Skeleton>();
  const textures = new Set<THREE.Texture>();
  const imageBitmaps = new Set<ImageBitmap>();
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  for (const root of new Set(roots)) {
    root.traverse((node) => {
      if (node instanceof THREE.SkinnedMesh) skeletons.add(node.skeleton);
      const renderable = node as THREE.Object3D & {
        geometry?: unknown;
        material?: unknown;
      };
      if (renderable.geometry instanceof THREE.BufferGeometry) geometries.add(renderable.geometry);
      const source = Array.isArray(renderable.material) ? renderable.material : [renderable.material];
      for (const material of source) {
        if (material instanceof THREE.Material) materials.add(material);
      }
    });
  }
  for (const material of materials) collectMaterialTextures(material, textures);
  if (typeof ImageBitmap !== 'undefined') {
    for (const texture of textures) {
      const data = texture.source.data;
      if (data instanceof ImageBitmap) imageBitmaps.add(data);
    }
  }
  return { skeletons, textures, imageBitmaps, geometries, materials };
}

/**
 * glTF sourceとSkeletonUtils cloneはgeometry/material/textureを共有する。そのため
 * rootごとではなくpipeline単位のunique集合とledgerで一度だけ解放する。
 */
function disposeObjectResources(
  roots: Iterable<THREE.Object3D>,
  disposedResources: WeakSet<object>,
  protectedRoots: Iterable<THREE.Object3D> = [],
): void {
  const resources = collectObjectResources(roots);
  const protectedResources = collectObjectResources(protectedRoots);
  const protectedSet = new Set<object>([
    ...protectedResources.skeletons,
    ...protectedResources.textures,
    ...protectedResources.imageBitmaps,
    ...protectedResources.geometries,
    ...protectedResources.materials,
  ]);
  const release = (resource: object, cleanup: () => void): void => {
    if (protectedSet.has(resource) || disposedResources.has(resource)) return;
    disposedResources.add(resource);
    cleanup();
  };
  for (const skeleton of resources.skeletons) release(skeleton, () => skeleton.dispose());
  for (const texture of resources.textures) release(texture, () => texture.dispose());
  for (const image of resources.imageBitmaps) release(image, () => image.close());
  for (const geometry of resources.geometries) release(geometry, () => geometry.dispose());
  for (const material of resources.materials) release(material, () => material.dispose());
}

function clearObjectRoots(roots: Iterable<THREE.Object3D>): void {
  for (const root of new Set(roots)) root.clear();
}

const LEGACY_DISTANT_FALLBACK_NAMES = new Set([
  'aaa:distant-world',
  'aaa:distant-stage-matte-root',
  'aaa:distant-stage-matte',
]);

function isDescendantOf(node: THREE.Object3D, ancestor: THREE.Object3D): boolean {
  for (let parent = node.parent; parent; parent = parent.parent) {
    if (parent === ancestor) return true;
  }
  return false;
}

/**
 * Blenderの実3D遠景と重複する旧フォールバックrootだけを識別する。
 * 新しいstage kitはuserData契約、古いビルドは安定した名前で移行できる。
 */
export function isProceduralDistantWorldFallback(node: THREE.Object3D): boolean {
  return node.userData.proceduralDistantWorldFallback === true || LEGACY_DISTANT_FALLBACK_NAMES.has(node.name);
}

export function tuneImportedStageMaterial(node: THREE.Mesh): void {
  const kind = typeof node.userData.hibanaMaterial === 'string'
    ? node.userData.hibanaMaterial
    : undefined;
  if (!kind) return;
  const materials = Array.isArray(node.material) ? node.material : [node.material];
  for (const material of materials) {
    if (!(material instanceof THREE.MeshStandardMaterial)) continue;
    if (kind === 'water') {
      // 軽量な実時間水面: scene.environment のIBLを強く拾う。画面全体を
      // 再レンダーする平面反射を使わないため、大面積でも追加パスは発生しない。
      material.roughness = 0.072;
      material.metalness = 0.34;
      material.envMapIntensity = 1.9;
      material.transparent = true;
      material.opacity = 0.72;
      material.dithering = true;
      material.depthWrite = false;
      material.side = THREE.DoubleSide;
      if (material.normalMap) {
        material.normalScale.set(0.52, 0.52);
        material.normalMap.wrapS = THREE.RepeatWrapping;
        material.normalMap.wrapT = THREE.RepeatWrapping;
        material.normalMap.repeat.set(1.7, 1.7);
        material.normalMap.anisotropy = 4;
        material.normalMap.needsUpdate = true;
      }
      if (material.roughnessMap) {
        material.roughnessMap.wrapS = THREE.RepeatWrapping;
        material.roughnessMap.wrapT = THREE.RepeatWrapping;
        material.roughnessMap.repeat.set(1.7, 1.7);
        material.roughnessMap.needsUpdate = true;
      }
      material.needsUpdate = true;
      node.castShadow = false;
      node.receiveShadow = true;
      node.renderOrder = 1;
    } else if (kind === 'glass') {
      material.roughness = Math.min(material.roughness, 0.18);
      material.metalness = Math.max(material.metalness, 0.24);
      material.envMapIntensity = Math.max(material.envMapIntensity, 0.92);
      material.needsUpdate = true;
      // 窓パネルは壁と同じマクロ影を二重に作らない。Blender側は
      // material batch毎に結合済みなので、透明/反射ファサードが大面積だと
      // shadow passのコストと黒い窓影が目立つ。受光は残し、投影だけ止める。
      node.castShadow = false;
      node.receiveShadow = true;
    } else if (kind === 'emissive') {
      // UnrealBloomPassはOutputPass前のHDR値を拾う。大きな看板・窓・火口帯に
      // BlenderのbaseColor + emissiveStrengthがそのまま入ると、発光面全体が
      // 白い面になる。色相は保ちつつ、最大チャンネルで線形値を
      // 制限し、ネオンの局所的な輝きだけを残す。追加pass/DCはゼロ。
      const basePeak = Math.max(material.color.r, material.color.g, material.color.b);
      if (basePeak > 0.28) material.color.multiplyScalar(0.28 / basePeak);
      const emissivePeak = Math.max(
        material.emissive.r,
        material.emissive.g,
        material.emissive.b,
      );
      if (emissivePeak > 0) {
        material.emissiveIntensity = Math.min(
          material.emissiveIntensity,
          0.42 / emissivePeak,
        );
      }
      material.roughness = Math.max(material.roughness, 0.44);
      material.metalness = Math.min(material.metalness, 0.12);
      material.envMapIntensity = Math.min(material.envMapIntensity, 0.45);
      material.needsUpdate = true;
      // 発光面の形状は建築本体の影に内包される。大面積の看板バッチを
      // shadow mapへ再描画せず、光害対策とフレーム予算を両立する。
      node.castShadow = false;
      node.receiveShadow = true;
    }
  }
}

/**
 * 高密度glTFを非同期で追加する本番パイプライン。
 * - manifest/個別asset失敗は既存プロシージャル景観へfail-open
 * - Meshopt、任意KTX2/Draco、SkinnedMesh clone、LODをサポート
 * - 表示前compileAsyncで初見シェーダヒッチを防止
 */
export class AaaStageAssetPipeline {
  readonly root = new THREE.Group();
  private readonly controller = new AbortController();
  private disposed = false;
  private distantWorldReplacementLoaded = false;
  private proceduralPropReplacementLoaded = false;
  private proceduralStageShellReplacementLoaded = false;
  private readonly hiddenDistantFallbacks = new Map<THREE.Object3D, boolean>();
  private readonly sourceRoots = new Set<THREE.Object3D>();
  private readonly disposedResources = new WeakSet<object>();
  private loadPromise: Promise<AaaAssetLoadReport> | null = null;

  get hasDistantWorldReplacement(): boolean {
    return this.distantWorldReplacementLoaded;
  }

  get hasProceduralPropReplacement(): boolean {
    return this.proceduralPropReplacementLoaded;
  }

  get hasProceduralStageShellReplacement(): boolean {
    return this.proceduralStageShellReplacementLoaded;
  }

  constructor(
    private readonly scene: THREE.Scene,
    private readonly renderer: THREE.WebGLRenderer,
    private readonly camera: THREE.Camera,
  ) {
    this.root.name = 'aaa:external-stage-assets';
    this.root.visible = false;
    this.scene.add(this.root);
  }

  private hideProceduralDistantWorldFallbacks(): void {
    this.scene.traverse((node) => {
      // GLB内部の名前が旧fallback名と偶然一致しても、置換asset自身は隠さない。
      if (node === this.root || isDescendantOf(node, this.root)) return;
      if (!isProceduralDistantWorldFallback(node) || this.hiddenDistantFallbacks.has(node)) return;
      this.hiddenDistantFallbacks.set(node, node.visible);
      node.visible = false;
    });
  }

  private restoreProceduralDistantWorldFallbacks(): void {
    for (const [node, wasVisible] of this.hiddenDistantFallbacks) node.visible = wasVisible;
    this.hiddenDistantFallbacks.clear();
  }

  load(options: AaaAssetLoadOptions): Promise<AaaAssetLoadReport> {
    if (this.disposed) {
      return Promise.resolve({ requested: 0, loaded: 0, failed: 0, errors: [] });
    }
    if (!this.loadPromise) {
      this.loadPromise = options.tier === 'low'
        ? Promise.resolve({ requested: 0, loaded: 0, failed: 0, errors: [] })
        : this.loadInternal(options);
    }
    return this.loadPromise;
  }

  private async loadInternal(options: AaaAssetLoadOptions): Promise<AaaAssetLoadReport> {
    const errors: string[] = [];
    const empty = (): AaaAssetLoadReport => ({ requested: 0, loaded: 0, failed: 0, errors });
    const base = import.meta.env.BASE_URL;
    const manifestUrl = options.manifestUrl ?? `${base}assets/aaa/manifest.json`;
    let manifest: AaaAssetManifest;
    try {
      // manifestはstable URLでもdeploy単位に再検証する。GLB本体は下で
      // generator SHAをqueryへ付け、旧manifest/新GLBのcache混在をextras照合で拒否する。
      const response = await fetch(manifestUrl, { signal: this.controller.signal, cache: 'no-cache' });
      if (!response.ok) throw new Error(`manifest HTTP ${response.status}`);
      manifest = parseAaaAssetManifest(await response.json());
    } catch (error) {
      if (!this.disposed) errors.push(error instanceof Error ? error.message : String(error));
      return { requested: 0, loaded: 0, failed: errors.length, errors };
    }
    const entries = manifest.assets.filter((entry) => {
      if (entry.stages && !entry.stages.includes(options.stageId)) return false;
      return TIER_RANK[options.tier] >= TIER_RANK[entry.minTier ?? 'medium'];
    });
    if (entries.length === 0 || this.disposed) return empty();
    const replacementEntries = entries.filter(replacesProceduralStage);
    if (replacementEntries.length > 1) {
      const error = `active stage replacement entry count must be exactly 1 (got ${replacementEntries.length})`;
      return {
        requested: replacementEntries.length,
        loaded: 0,
        failed: replacementEntries.length,
        errors: [error],
      };
    }

    // glTF/Draco/KTX2/Meshoptはassetが実在する時だけ別chunkから読む。小さな型facadeを
    // 挟む理由は gltf-runtime.js 冒頭参照(実体はすべてThree公式addon)。
    const { createGltfRuntime } = await import('./gltf-runtime.js');
    if (this.disposed) return empty();
    const runtime = createGltfRuntime(this.renderer, base, manifest);
    const cache = new Map<string, Promise<THREE.Object3D>>();
    const loadedSources = new Set<THREE.Object3D>();
    const retainedSources = new Set<THREE.Object3D>();
    const createdHolders: THREE.Object3D[] = [];
    let committed = false;
    let requested = 0;
    let loaded = 0;
    let failed = 0;
    let stagedDistantWorldReplacement = false;
    let stagedProceduralPropReplacement = false;
    let stagedProceduralStageShellReplacement = false;
    try {
      const loadModel = (url: string, entry: AaaAssetEntry): Promise<THREE.Object3D> => {
        // A generator-wide SHA alone aliases different stage layouts during a
        // partially deployed catalog. Prefer the entry's content/layout
        // identity, while retaining generatorSha so geometry-only generator
        // changes still invalidate browser caches.
        const stageIdentity = entry.stageProvenance?.assetSha256 ??
          entry.stageProvenance?.stageLayoutSha256;
        const version = [stageIdentity, manifest.generatorSha].filter(Boolean).join('-');
        const cacheKey = `${url}?v=${version}`;
        let pending = cache.get(cacheKey);
        if (!pending) {
          const versionSuffix = version ? `?v=${version}` : '';
          pending = runtime.loadScene(
            `${base}assets/aaa/${url}${versionSuffix}`,
            this.controller.signal,
          ).then((source) => {
            loadedSources.add(source);
            // gltf-runtimeはfetchをAbortSignalで停止するが、parseAsync開始後の
            // decoder/texture処理は同期的に取り消せない。dispose後に遅れて
            // resolveしたsourceはここで即時回収し、rootへの再付与を防ぐ。
            if (this.disposed) {
              disposeObjectResources(
                [source],
                this.disposedResources,
                [this.root, ...this.sourceRoots],
              );
              source.clear();
              loadedSources.delete(source);
              throw new Error('AAA stage asset load aborted');
            }
            return source;
          });
          cache.set(cacheKey, pending);
        }
        return pending;
      };

      for (const entry of entries) {
        if (this.disposed) break;
        const generated = entry.propKind
          ? options.propPlacements
              .filter((placement) => placement.kind === entry.propKind)
              .slice(0, entry.maxInstances ?? Number.POSITIVE_INFINITY)
              .map((placement): AaaAssetInstance => ({
                position: [placement.cx, entry.yOffset ?? 0, placement.cz],
                rotation: [0, placement.rotRad + (entry.rotationOffset ?? 0), 0],
                scale: placement.scaleJitter * (entry.scale ?? 1),
              }))
          : [...(entry.instances ?? [])];
        requested += generated.length;
        if (generated.length === 0) continue;
        const entryHolders: THREE.Object3D[] = [];
        try {
          const provenanceError = stageReplacementPreflightError(entry, manifest, options);
          if (provenanceError) throw new Error(provenanceError);
          const sourcePlan = sourcePlanForTier(entry, options.tier);
          const source = await loadModel(sourcePlan.url, entry);
          validateStageSourceProvenance(source, entry, manifest, options);
          const lodSources = sourcePlan.lods.length > 0
            ? await Promise.all(sourcePlan.lods.map(async (lod) => {
                const lodSource = await loadModel(lod.url, entry);
                validateStageSourceProvenance(lodSource, entry, manifest, options);
                return { source: lodSource, distance: lod.distance };
              }))
            : [];
          for (const instance of generated) {
            if (this.disposed) throw new Error('AAA stage asset load aborted');
            const holder: THREE.Object3D = lodSources.length > 0 ? new THREE.LOD() : new THREE.Group();
            try {
              const primary = runtime.clone(source);
              if (holder instanceof THREE.LOD) {
                holder.addLevel(primary, 0, 0.1);
                for (const lod of lodSources) {
                  holder.addLevel(runtime.clone(lod.source), lod.distance, 0.1);
                }
              } else {
                holder.add(primary);
              }
              holder.name = `aaa:${entry.id}`;
              holder.position.fromArray(instance.position);
              if (instance.rotation) {
                holder.rotation.set(instance.rotation[0], instance.rotation[1], instance.rotation[2]);
              }
              const scale = instance.scale ?? entry.scale ?? 1;
              if (typeof scale === 'number') holder.scale.setScalar(scale);
              else holder.scale.fromArray(scale);
              holder.traverse((node) => {
                if (!(node instanceof THREE.Mesh)) return;
                node.castShadow = entry.castShadow ?? true;
                node.receiveShadow = entry.receiveShadow ?? true;
                tuneImportedStageMaterial(node);
              });
              if (this.disposed) {
                throw new Error('AAA stage asset load aborted');
              }
              entryHolders.push(holder);
            } catch (error) {
              // clone途中で失敗した場合はsource共有resourceを保護し、
              // このholderに固有のSkeletonだけも取り残さない。
              disposeObjectResources(
                [holder],
                this.disposedResources,
                [this.root, ...this.sourceRoots, ...loadedSources],
              );
              holder.clear();
              throw error;
            }
          }
          // Entry-level atomic commit: one failed clone must not hide a whole
          // procedural fallback behind an incomplete replacement set.
          for (const holder of entryHolders) this.root.add(holder);
          createdHolders.push(...entryHolders);
          retainedSources.add(source);
          for (const lod of lodSources) retainedSources.add(lod.source);
          loaded += entryHolders.length;
          if (entry.replacesDistantMatte) stagedDistantWorldReplacement = true;
          if (entry.replacesProceduralProps) stagedProceduralPropReplacement = true;
          if (entry.replacesProceduralStageShell) {
            stagedProceduralStageShellReplacement = true;
          }
        } catch (error) {
          for (const holder of entryHolders) holder.parent?.remove(holder);
          disposeObjectResources(
            entryHolders,
            this.disposedResources,
            [this.root, ...this.sourceRoots, ...loadedSources],
          );
          clearObjectRoots(entryHolders);
          if (!this.disposed) {
            failed += generated.length;
            errors.push(`${entry.id}: ${error instanceof Error ? error.message : String(error)}`);
          }
        }
      }

      // Promise.allの早期reject後も、別LODのloadSceneは継続しうる。
      // 全てsettleさせてから未使用sourceを回収することでpartial-load leakを塞ぐ。
      await Promise.allSettled([...cache.values()]);
      const unretainedSources = [...loadedSources].filter((source) => !retainedSources.has(source));
      disposeObjectResources(
        unretainedSources,
        this.disposedResources,
        [this.root, ...this.sourceRoots, ...retainedSources],
      );
      clearObjectRoots(unretainedSources);
      for (const source of unretainedSources) loadedSources.delete(source);

      if (!this.disposed && loaded > 0) {
        try {
          await this.renderer.compileAsync(this.scene, this.camera);
        } catch {
          this.renderer.compile(this.scene, this.camera);
        }
        if (!this.disposed) {
          this.root.visible = true;
          // 置換フラグはモデルcloneだけで確定させない。表示前compileを完了したGLBだけを
          // コミットし、その時点で画像matteと簡易3D遠景の重複を一括で隠す。
          this.distantWorldReplacementLoaded ||= stagedDistantWorldReplacement;
          this.proceduralPropReplacementLoaded ||= stagedProceduralPropReplacement;
          this.proceduralStageShellReplacementLoaded ||=
            stagedProceduralStageShellReplacement;
          if (this.distantWorldReplacementLoaded) this.hideProceduralDistantWorldFallbacks();
          for (const source of retainedSources) this.sourceRoots.add(source);
          committed = true;
        }
      }
      return { requested, loaded, failed, errors };
    } finally {
      try {
        if (!committed) {
          // compile失敗・dispose中断はこのloadで追加したツリーだけをrollbackする。
          // 過去にcommit済みのroot/sourceはprotectedRootsで保護する。
          for (const holder of createdHolders) holder.parent?.remove(holder);
          const rollbackRoots = [...createdHolders, ...loadedSources];
          disposeObjectResources(
            rollbackRoots,
            this.disposedResources,
            [this.root, ...this.sourceRoots],
          );
          clearObjectRoots(rollbackRoots);
        }
      } finally {
        runtime.dispose();
      }
    }
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.distantWorldReplacementLoaded = false;
    this.proceduralPropReplacementLoaded = false;
    this.proceduralStageShellReplacementLoaded = false;
    this.controller.abort();
    this.restoreProceduralDistantWorldFallbacks();
    this.scene.remove(this.root);
    const ownedRoots = [this.root, ...this.sourceRoots];
    disposeObjectResources(ownedRoots, this.disposedResources);
    clearObjectRoots(ownedRoots);
    this.sourceRoots.clear();
  }
}
