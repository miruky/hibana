import * as THREE from 'three';
import type { EnemyVisualState } from '../game/bot';
import type { GltfRuntime } from './gltf-runtime.js';

export const ENEMY_VARIANT_IDS = [
  'rifleman',
  'breacher',
  'scout',
  'marksman',
  'support',
  'medic',
] as const;

export type EnemyVariantId = (typeof ENEMY_VARIANT_IDS)[number];

export const ENEMY_CLIP_NAMES = [
  'AN_Soldier_Idle',
  'AN_Soldier_RifleReady',
  'AN_Soldier_Aim',
  'AN_Soldier_Fire',
  'AN_Soldier_Reload',
  'AN_Soldier_WalkForward',
  'AN_Soldier_WalkBackward',
  'AN_Soldier_StrafeLeft',
  'AN_Soldier_StrafeRight',
  'AN_Soldier_RunForward',
  'AN_Soldier_HitFront',
  'AN_Soldier_HitBack',
  'AN_Soldier_DeathFront',
  'AN_Soldier_DeathBack',
] as const;

export type EnemyClipName = (typeof ENEMY_CLIP_NAMES)[number];

export interface EnemyAssetManifestLod {
  readonly level: 0 | 1 | 2;
  readonly url: string;
  readonly screenHeightMin: number;
}

export interface EnemyAssetManifest {
  readonly schemaVersion: 1;
  readonly packVersion: number;
  readonly id: string;
  readonly sharedSkeleton: string;
  readonly heightMeters: number;
  readonly forwardAxis: '-Z';
  readonly variants: readonly EnemyVariantId[];
  readonly animations: readonly EnemyClipName[];
  readonly lods: readonly EnemyAssetManifestLod[];
}

export interface EnemyVisualTarget {
  readonly uid: number;
  readonly team: number;
  readonly group: THREE.Group;
  readonly crowdSlot: number;
  readonly shadowCasting: boolean;
  readonly enemyVisualFloorOffsetY: number;
  getEnemyVisualState(out: EnemyVisualState): void;
  getEnemyVisualVisibilityAudit(): EnemyVisualVisibilityAudit;
  setExternalEnemyVisual(root: THREE.Object3D | null): void;
}

export interface EnemyVisualVisibilityAudit {
  readonly proceduralRigVisible: boolean;
  readonly externalVisualPresent: boolean;
  readonly externalVisualVisible: boolean;
  readonly crowdSlot: number;
}

export interface EnemyAssetLoadOptions {
  readonly manifestUrl?: string;
}

export interface EnemyAssetLoadReport {
  readonly ready: boolean;
  readonly sourceLods: number;
  readonly variants: number;
  readonly actors: number;
  readonly failedActors: number;
  readonly errors: readonly string[];
}

export interface EnemyActorAuditSnapshot {
  readonly uid: number;
  readonly team: number;
  readonly variantId: EnemyVariantId;
  readonly alive: boolean;
  readonly killcamReplay: boolean;
  readonly killcamDeath01: number;
  readonly distanceM: number;
  readonly lodIndex: number;
  readonly visibleLods: readonly number[];
  readonly skinnedMeshesPerLod: readonly number[];
  readonly currentClip: EnemyClipName | null;
  readonly actionTimeS: number;
  readonly actionDurationS: number;
  readonly actionRunning: boolean;
  readonly debugFramed: boolean;
  readonly externalParented: boolean;
  readonly externalVisible: boolean;
  readonly proceduralRigVisible: boolean;
  readonly crowdSlot: number;
  readonly inView: boolean;
  readonly screenX01: number;
  readonly screenY01: number;
}

export interface EnemyAssetAuditSnapshot {
  readonly ready: boolean;
  readonly sourceLods: number;
  readonly sourceVariants: number;
  readonly actorCount: number;
  readonly variants: readonly EnemyVariantId[];
  readonly activeClips: readonly EnemyClipName[];
  readonly activeLods: readonly number[];
  readonly actors: readonly EnemyActorAuditSnapshot[];
}

interface LoadedLod {
  readonly level: 0 | 1 | 2;
  readonly source: THREE.Object3D;
  readonly clips: ReadonlyMap<EnemyClipName, THREE.AnimationClip>;
  readonly distance: number;
}

interface ActorLevel {
  readonly level: 0 | 1 | 2;
  readonly root: THREE.Object3D;
  readonly mixer: THREE.AnimationMixer;
  readonly clips: ReadonlyMap<EnemyClipName, THREE.AnimationClip>;
  readonly actions: Map<EnemyClipName, THREE.AnimationAction>;
}

interface OneShotState {
  clip: EnemyClipName;
  elapsed: number;
}

interface EnemyActor {
  readonly target: EnemyVisualTarget;
  readonly variantId: EnemyVariantId;
  readonly lod: THREE.LOD;
  readonly levels: readonly ActorLevel[];
  readonly state: EnemyVisualState;
  lodIndex: number;
  currentClip: EnemyClipName | null;
  currentAction: THREE.AnimationAction | null;
  currentActionLod: number;
  oneShot: OneShotState | null;
  pendingReload: boolean;
  lastShotSerial: number;
  lastReloadSerial: number;
  lastHitSerial: number;
  replayShotSerial: number;
  handledReplayShotSerial: number;
  wasAlive: boolean;
  previousX: number;
  previousZ: number;
  hasPreviousPosition: boolean;
  lastShadowCasting: boolean;
  debugClip: EnemyClipName | null;
  debugClipRemainingS: number;
  debugLodIndex: number | null;
  debugLodRemainingS: number;
  debugFrameRemainingS: number;
  debugFrameYawRad: number;
  debugFrameDistanceM: number;
  debugFrameThroughReplay: boolean;
  debugFramed: boolean;
}

const LOOPING_CLIPS = new Set<EnemyClipName>([
  'AN_Soldier_Idle',
  'AN_Soldier_RifleReady',
  'AN_Soldier_Aim',
  'AN_Soldier_WalkForward',
  'AN_Soldier_WalkBackward',
  'AN_Soldier_StrafeLeft',
  'AN_Soldier_StrafeRight',
  'AN_Soldier_RunForward',
]);

const REQUIRED_CLIP_SET = new Set<string>(ENEMY_CLIP_NAMES);
const REQUIRED_VARIANT_SET = new Set<string>(ENEMY_VARIANT_IDS);
const DEFAULT_MANIFEST = 'assets/aaa/enemies/manifest.json';
const LOD_BIAS = 1.8;
const RUN_SPEED_MPS = 5.2;
const MOVE_EPSILON_MPS = 0.22;
const STATE_CROSSFADE_S = 0.12;

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function isSafeLocalPath(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.length > 0 &&
    !value.startsWith('/') &&
    !value.includes('..') &&
    !/^[a-z][a-z\d+.-]*:/i.test(value)
  );
}

function readUniqueStringArray(value: unknown, label: string): string[] {
  if (!Array.isArray(value) || !value.every((part) => typeof part === 'string')) {
    throw new Error(`${label} must be a string array`);
  }
  const result = value as string[];
  if (new Set(result).size !== result.length) throw new Error(`${label} must not contain duplicates`);
  return result;
}

/** Treat the network manifest as untrusted and narrow it before any GLB request. */
export function parseEnemyAssetManifest(value: unknown): EnemyAssetManifest {
  if (!isRecord(value)) throw new Error('enemy manifest must be an object');
  if (value.schemaVersion !== 1) throw new Error('unsupported enemy manifest schemaVersion');
  if (!Number.isInteger(value.packVersion) || (value.packVersion as number) < 1) {
    throw new Error('enemy manifest.packVersion is invalid');
  }
  if (typeof value.id !== 'string' || value.id.length === 0) {
    throw new Error('enemy manifest.id is invalid');
  }
  if (typeof value.sharedSkeleton !== 'string' || value.sharedSkeleton.length === 0) {
    throw new Error('enemy manifest.sharedSkeleton is invalid');
  }
  if (typeof value.heightMeters !== 'number' || !Number.isFinite(value.heightMeters) || value.heightMeters <= 0) {
    throw new Error('enemy manifest.heightMeters is invalid');
  }
  if (value.forwardAxis !== '-Z') throw new Error('enemy manifest.forwardAxis must be -Z');

  const variants = readUniqueStringArray(value.variants, 'enemy manifest.variants');
  if (
    variants.length !== ENEMY_VARIANT_IDS.length ||
    variants.some((variant) => !REQUIRED_VARIANT_SET.has(variant))
  ) {
    throw new Error('enemy manifest must contain the six supported variantId values');
  }
  const animations = readUniqueStringArray(value.animations, 'enemy manifest.animations');
  if (ENEMY_CLIP_NAMES.some((clip) => !animations.includes(clip))) {
    throw new Error('enemy manifest is missing a required animation');
  }
  if (!Array.isArray(value.lods) || value.lods.length !== 3) {
    throw new Error('enemy manifest.lods must contain exactly three entries');
  }
  const lods = value.lods.map((candidate, index): EnemyAssetManifestLod => {
    if (!isRecord(candidate)) throw new Error(`enemy manifest.lods[${index}] is invalid`);
    if (candidate.level !== 0 && candidate.level !== 1 && candidate.level !== 2) {
      throw new Error(`enemy manifest.lods[${index}].level is invalid`);
    }
    if (!isSafeLocalPath(candidate.url)) {
      throw new Error(`enemy manifest.lods[${index}].url must be a safe relative path`);
    }
    if (
      typeof candidate.screenHeightMin !== 'number' ||
      !Number.isFinite(candidate.screenHeightMin) ||
      candidate.screenHeightMin < 0 ||
      candidate.screenHeightMin > 1
    ) {
      throw new Error(`enemy manifest.lods[${index}].screenHeightMin is invalid`);
    }
    return {
      level: candidate.level,
      url: candidate.url,
      screenHeightMin: candidate.screenHeightMin,
    };
  }).sort((a, b) => a.level - b.level);
  if (new Set(lods.map((lod) => lod.level)).size !== 3) {
    throw new Error('enemy manifest.lods must contain levels 0, 1 and 2 exactly once');
  }
  const lod0 = lods[0];
  const lod1 = lods[1];
  const lod2 = lods[2];
  if (!lod0 || !lod1 || !lod2 || lod0.screenHeightMin <= lod1.screenHeightMin || lod1.screenHeightMin <= 0 || lod2.screenHeightMin !== 0) {
    throw new Error('enemy manifest LOD screenHeightMin thresholds are invalid');
  }
  return {
    schemaVersion: 1,
    packVersion: value.packVersion as number,
    id: value.id,
    sharedSkeleton: value.sharedSkeleton,
    heightMeters: value.heightMeters,
    forwardAxis: '-Z',
    variants: variants as EnemyVariantId[],
    animations: animations.filter((clip): clip is EnemyClipName => REQUIRED_CLIP_SET.has(clip)),
    lods,
  };
}

/** Sequential bot ids deliberately form a full permutation of the six authored variants. */
export function enemyVariantFor(
  uid: number,
  team: number,
  variants: readonly EnemyVariantId[] = ENEMY_VARIANT_IDS,
): EnemyVariantId {
  if (variants.length === 0) throw new Error('enemy variants cannot be empty');
  const hash = Math.trunc(uid) * 5 + Math.trunc(team) * 3;
  const index = ((hash % variants.length) + variants.length) % variants.length;
  const result = variants[index];
  if (!result) throw new Error('enemy variant selection failed');
  return result;
}

export function enemyLodDistances(
  manifest: EnemyAssetManifest,
  verticalFovDeg: number,
): readonly [number, number, number] {
  const fov = THREE.MathUtils.degToRad(THREE.MathUtils.clamp(verticalFovDeg, 25, 120));
  const distanceFor = (screenHeight: number): number =>
    manifest.heightMeters / (2 * Math.tan(fov / 2) * screenHeight) * LOD_BIAS;
  const lod0 = manifest.lods[0];
  const lod1 = manifest.lods[1];
  if (!lod0 || !lod1) throw new Error('enemy LOD thresholds are incomplete');
  const first = THREE.MathUtils.clamp(distanceFor(lod0.screenHeightMin), 6, 24);
  const second = THREE.MathUtils.clamp(distanceFor(lod1.screenHeightMin), first + 8, 60);
  return [0, first, second];
}

export function selectEnemyLod(
  distance: number,
  thresholds: readonly [number, number, number],
  current: number,
): number {
  const near = thresholds[1];
  const far = thresholds[2];
  if (current <= 0) {
    if (distance > far * 1.08) return 2;
    return distance > near * 1.08 ? 1 : 0;
  }
  if (current === 1) {
    if (distance < near * 0.9) return 0;
    return distance > far * 1.08 ? 2 : 1;
  }
  if (distance < near * 0.9) return 0;
  return distance < far * 0.9 ? 1 : 2;
}

export interface EnemyBaseAnimationInput {
  readonly aiState: 'patrol' | 'search' | 'combat';
  readonly speedMps: number;
  readonly movementX: number;
  readonly movementZ: number;
  readonly heading: number;
}

/** Maps the existing AI and actual displacement to the authored locomotion state. */
export function selectEnemyBaseAnimation(input: EnemyBaseAnimationInput): EnemyClipName {
  if (input.speedMps <= MOVE_EPSILON_MPS) {
    if (input.aiState === 'combat') return 'AN_Soldier_Aim';
    if (input.aiState === 'search') return 'AN_Soldier_RifleReady';
    return 'AN_Soldier_Idle';
  }
  const length = Math.hypot(input.movementX, input.movementZ);
  if (length <= 1e-5) {
    return input.speedMps >= RUN_SPEED_MPS ? 'AN_Soldier_RunForward' : 'AN_Soldier_WalkForward';
  }
  const inv = 1 / length;
  const dx = input.movementX * inv;
  const dz = input.movementZ * inv;
  const forwardX = -Math.sin(input.heading);
  const forwardZ = -Math.cos(input.heading);
  const rightX = Math.cos(input.heading);
  const rightZ = -Math.sin(input.heading);
  const forwardDot = dx * forwardX + dz * forwardZ;
  const rightDot = dx * rightX + dz * rightZ;
  if (input.speedMps >= RUN_SPEED_MPS && forwardDot > 0.25) return 'AN_Soldier_RunForward';
  if (forwardDot < -0.45) return 'AN_Soldier_WalkBackward';
  if (Math.abs(rightDot) > 0.5) {
    return rightDot < 0 ? 'AN_Soldier_StrafeLeft' : 'AN_Soldier_StrafeRight';
  }
  return 'AN_Soldier_WalkForward';
}

function clipsFor(source: THREE.Object3D): ReadonlyMap<EnemyClipName, THREE.AnimationClip> {
  const clips = new Map<EnemyClipName, THREE.AnimationClip>();
  for (const clip of source.animations) {
    if (REQUIRED_CLIP_SET.has(clip.name)) clips.set(clip.name as EnemyClipName, clip);
  }
  for (const required of ENEMY_CLIP_NAMES) {
    if (!clips.has(required)) throw new Error(`GLB is missing animation ${required}`);
  }
  return clips;
}

function taggedVariantNode(node: THREE.Object3D): EnemyVariantId | null {
  const variant = node.userData.variantId;
  return typeof variant === 'string' && REQUIRED_VARIANT_SET.has(variant)
    ? variant as EnemyVariantId
    : null;
}

function skinnedMeshCount(root: THREE.Object3D): number {
  let count = 0;
  root.traverse((node) => {
    if (node instanceof THREE.SkinnedMesh) count += 1;
  });
  return count;
}

function validateVariantNodes(source: THREE.Object3D, variants: readonly EnemyVariantId[]): void {
  const counts = new Map<string, number>();
  const taggedRoots = new Set<THREE.Object3D>();
  source.traverse((node) => {
    if (!Object.hasOwn(node.userData, 'variantId')) return;
    const variant = taggedVariantNode(node);
    if (!variant) throw new Error(`${node.name || '(unnamed)'} has an invalid variantId`);
    if (skinnedMeshCount(node) < 1) {
      throw new Error(`variant root ${node.name || '(unnamed)'} has no SkinnedMesh`);
    }
    taggedRoots.add(node);
    counts.set(variant, (counts.get(variant) ?? 0) + 1);
  });
  for (const variant of variants) {
    if (counts.get(variant) !== 1) throw new Error(`GLB must contain exactly one ${variant} variant root`);
  }
  source.traverse((node) => {
    if (!(node instanceof THREE.SkinnedMesh)) return;
    let owner: THREE.Object3D | null = node;
    while (owner && !taggedRoots.has(owner)) owner = owner.parent;
    if (!owner) {
      throw new Error(`SkinnedMesh ${node.name || '(unnamed)'} has no tagged variant root`);
    }
  });
}

function variantRoots(source: THREE.Object3D): THREE.Object3D[] {
  const roots: THREE.Object3D[] = [];
  source.traverse((node) => {
    if (taggedVariantNode(node)) roots.push(node);
  });
  return roots;
}

function applySelectedVariantMetadata(root: THREE.Object3D, variantId: EnemyVariantId, lodLevel: 0 | 1 | 2): number {
  let selectedMeshes = 0;
  root.traverse((node) => {
    if (!(node instanceof THREE.SkinnedMesh)) return;
    selectedMeshes += 1;
    node.userData.variantId = variantId;
    node.userData.enemyAssetLod = lodLevel;
    node.receiveShadow = true;
  });
  return selectedMeshes;
}

function removeVariantRoot(root: THREE.Object3D): void {
  root.parent?.remove(root);
  // Each glTF primitive owns a Skeleton wrapper. Disposing removed wrappers
  // prevents later bone-texture allocation while preserving the selected
  // sibling's cloned bones and geometry/material sources.
  disposeSkeletons(root);
}

function selectedVariantRoot(source: THREE.Object3D, variantId: EnemyVariantId): THREE.Object3D {
  const matches = variantRoots(source).filter((root) => taggedVariantNode(root) === variantId);
  if (matches.length !== 1 || !matches[0]) {
    throw new Error(`variant ${variantId} was not cloned exactly once`);
  }
  return matches[0];
}

function disposeSkeletons(root: THREE.Object3D): void {
  const skeletons = new Set<THREE.Skeleton>();
  root.traverse((node) => {
    if (node instanceof THREE.SkinnedMesh) skeletons.add(node.skeleton);
  });
  for (const skeleton of skeletons) skeleton.dispose();
}

function cloneVariant(
  runtime: GltfRuntime,
  source: THREE.Object3D,
  variantId: EnemyVariantId,
  lodLevel: 0 | 1 | 2,
): THREE.Object3D {
  const clone = runtime.clone(source);
  const selectedRoot = selectedVariantRoot(clone, variantId);
  for (const root of variantRoots(clone)) {
    if (root !== selectedRoot) removeVariantRoot(root);
  }
  const selectedMeshes = applySelectedVariantMetadata(selectedRoot, variantId, lodLevel);
  if (selectedMeshes < 1) {
    disposeSkeletons(clone);
    throw new Error(`variant ${variantId} has no SkinnedMesh at LOD${lodLevel}`);
  }
  return clone;
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

function disposeSourceRoots(roots: Iterable<THREE.Object3D>): void {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  const textures = new Set<THREE.Texture>();
  const imageBitmaps = new Set<ImageBitmap>();
  const skeletons = new Set<THREE.Skeleton>();
  for (const root of new Set(roots)) {
    root.traverse((node) => {
      if (node instanceof THREE.SkinnedMesh) skeletons.add(node.skeleton);
      if (!(node instanceof THREE.Mesh)) return;
      geometries.add(node.geometry);
      const sourceMaterials = Array.isArray(node.material) ? node.material : [node.material];
      for (const material of sourceMaterials) materials.add(material);
    });
  }
  for (const material of materials) collectMaterialTextures(material, textures);
  if (typeof ImageBitmap !== 'undefined') {
    for (const texture of textures) {
      const data = texture.source.data;
      if (data instanceof ImageBitmap) imageBitmaps.add(data);
    }
  }
  for (const skeleton of skeletons) skeleton.dispose();
  for (const texture of textures) texture.dispose();
  for (const image of imageBitmaps) image.close();
  for (const geometry of geometries) geometry.dispose();
  for (const material of materials) material.dispose();
}

function disposeSources(sources: readonly LoadedLod[]): void {
  disposeSourceRoots(sources.map((entry) => entry.source));
}

function emptyState(): EnemyVisualState {
  return {
    alive: true,
    visible: true,
    aiState: 'patrol',
    speedMps: 0,
    shotSerial: 0,
    reloadSerial: 0,
    hitSerial: 0,
    hitFromBack: false,
    dying01: 0,
    killcamReplay: false,
    killcamDeath01: 0,
  };
}

export class EnemyAssetPipeline {
  private readonly controller = new AbortController();
  private readonly targets = new Map<number, EnemyVisualTarget>();
  private readonly actors = new Map<number, EnemyActor>();
  private loadedLods: readonly LoadedLod[] = [];
  private runtime: GltfRuntime | null = null;
  private manifest: EnemyAssetManifest | null = null;
  private loadPromise: Promise<EnemyAssetLoadReport> | null = null;
  private disposed = false;
  private ready = false;
  private debugActorUid: number | null = null;

  constructor(
    private readonly scene: THREE.Scene,
    private readonly renderer: THREE.WebGLRenderer,
    private readonly camera: THREE.PerspectiveCamera,
  ) {}

  get isReady(): boolean {
    return this.ready && !this.disposed;
  }

  register(target: EnemyVisualTarget): void {
    if (this.disposed) return;
    this.targets.set(target.uid, target);
    if (this.ready) this.attachTargetFailOpen(target);
  }

  unregister(target: EnemyVisualTarget): void {
    this.targets.delete(target.uid);
    const actor = this.actors.get(target.uid);
    if (actor) this.releaseActor(actor);
  }

  async load(options: EnemyAssetLoadOptions = {}): Promise<EnemyAssetLoadReport> {
    if (!this.loadPromise) this.loadPromise = this.loadInternal(options);
    return this.loadPromise;
  }

  private async loadInternal(options: EnemyAssetLoadOptions): Promise<EnemyAssetLoadReport> {
    const errors: string[] = [];
    const base = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : `${import.meta.env.BASE_URL}/`;
    const manifestUrl = options.manifestUrl ?? `${base}${DEFAULT_MANIFEST}`;
    let runtime: GltfRuntime | null = null;
    const loaded: LoadedLod[] = [];
    // A source can fail variant/clip validation before it becomes a LoadedLod.
    // Track it immediately after loadScene resolves so every successful GLB
    // allocation is still reclaimed by the fail-open path.
    const loadedSourceRoots = new Set<THREE.Object3D>();
    try {
      const response = await fetch(manifestUrl, {
        signal: this.controller.signal,
        cache: 'force-cache',
      });
      if (!response.ok) throw new Error(`enemy manifest HTTP ${response.status}`);
      const manifest = parseEnemyAssetManifest(await response.json());
      if (this.disposed) throw new DOMException('enemy pipeline disposed', 'AbortError');
      const { createGltfRuntime } = await import('./gltf-runtime.js');
      runtime = createGltfRuntime(this.renderer, base, {});
      const slash = manifestUrl.lastIndexOf('/');
      const assetBase = slash >= 0 ? manifestUrl.slice(0, slash + 1) : '';
      const distances = enemyLodDistances(manifest, this.camera.fov);
      for (const lod of manifest.lods) {
        const source = await runtime.loadScene(`${assetBase}${lod.url}`, this.controller.signal);
        loadedSourceRoots.add(source);
        if (this.disposed) throw new DOMException('enemy pipeline disposed', 'AbortError');
        validateVariantNodes(source, manifest.variants);
        loaded.push({
          level: lod.level,
          source,
          clips: clipsFor(source),
          distance: distances[lod.level],
        });
      }
      if (this.disposed) throw new DOMException('enemy pipeline disposed', 'AbortError');
      await this.prewarm(runtime, manifest, loaded);
      if (this.disposed) throw new DOMException('enemy pipeline disposed', 'AbortError');
      this.runtime = runtime;
      this.manifest = manifest;
      this.loadedLods = loaded;
      this.ready = true;
      let failedActors = 0;
      for (const target of this.targets.values()) {
        if (!this.attachTargetFailOpen(target)) failedActors += 1;
      }
      return {
        ready: true,
        sourceLods: loaded.length,
        variants: manifest.variants.length,
        actors: this.actors.size,
        failedActors,
        errors,
      };
    } catch (error) {
      if (!this.disposed) errors.push(error instanceof Error ? error.message : String(error));
      disposeSourceRoots(loadedSourceRoots);
      runtime?.dispose();
      return {
        ready: false,
        sourceLods: 0,
        variants: 0,
        actors: 0,
        failedActors: 0,
        errors,
      };
    }
  }

  private async prewarm(
    runtime: GltfRuntime,
    manifest: EnemyAssetManifest,
    loaded: readonly LoadedLod[],
  ): Promise<void> {
    const root = new THREE.Group();
    root.name = 'aaa:enemy-soldier-prewarm';
    root.position.set(0, -0.8, -4);
    this.camera.add(root);
    const clones: THREE.Object3D[] = [];
    try {
      for (const lod of loaded) {
        for (const variant of manifest.variants) {
          const clone = cloneVariant(runtime, lod.source, variant, lod.level);
          clone.traverse((node) => {
            if (node instanceof THREE.Mesh) {
              node.castShadow = lod.level === 0;
              node.receiveShadow = true;
              node.frustumCulled = false;
            }
          });
          root.add(clone);
          clones.push(clone);
        }
      }
      try {
        await this.renderer.compileAsync(this.scene, this.camera);
      } catch {
        this.renderer.compile(this.scene, this.camera);
      }
    } finally {
      this.camera.remove(root);
      for (const clone of clones) disposeSkeletons(clone);
      root.clear();
    }
  }

  private attachTargetFailOpen(target: EnemyVisualTarget): boolean {
    if (this.disposed || !this.ready || this.actors.has(target.uid)) return this.actors.has(target.uid);
    try {
      const actor = this.createActor(target);
      this.actors.set(target.uid, actor);
      target.setExternalEnemyVisual(actor.lod);
      this.updateActor(actor, 0);
      return true;
    } catch {
      const actor = this.actors.get(target.uid);
      if (actor) this.releaseActor(actor);
      else target.setExternalEnemyVisual(null);
      return false;
    }
  }

  private createActor(target: EnemyVisualTarget): EnemyActor {
    const runtime = this.runtime;
    const manifest = this.manifest;
    if (!runtime || !manifest) throw new Error('enemy sources are not ready');
    const variantId = enemyVariantFor(target.uid, target.team, manifest.variants);
    const lod = new THREE.LOD();
    lod.name = `aaa:enemy:${target.uid}:${variantId}`;
    lod.position.y = target.enemyVisualFloorOffsetY;
    lod.autoUpdate = false;
    lod.userData.variantId = variantId;
    const levels: ActorLevel[] = [];
    try {
      for (const source of this.loadedLods) {
        const root = cloneVariant(runtime, source.source, variantId, source.level);
        root.name = `aaa:enemy:${variantId}:lod${source.level}`;
        root.traverse((node) => {
          if (!(node instanceof THREE.Mesh)) return;
          node.castShadow = target.shadowCasting && source.level === 0;
          node.receiveShadow = true;
        });
        lod.addLevel(root, source.distance, 0.1);
        levels.push({
          level: source.level,
          root,
          mixer: new THREE.AnimationMixer(root),
          clips: source.clips,
          actions: new Map(),
        });
      }
      for (let index = 0; index < levels.length; index += 1) {
        const level = levels[index];
        if (level) level.root.visible = index === 0;
      }
      const state = emptyState();
      target.getEnemyVisualState(state);
      return {
        target,
        variantId,
        lod,
        levels,
        state,
        lodIndex: 0,
        currentClip: null,
        currentAction: null,
        currentActionLod: -1,
        oneShot: null,
        pendingReload: false,
        lastShotSerial: state.shotSerial,
        lastReloadSerial: state.reloadSerial,
        lastHitSerial: state.hitSerial,
        replayShotSerial: 0,
        handledReplayShotSerial: 0,
        wasAlive: state.alive,
        previousX: target.group.position.x,
        previousZ: target.group.position.z,
        hasPreviousPosition: false,
        lastShadowCasting: target.shadowCasting,
        debugClip: null,
        debugClipRemainingS: 0,
        debugLodIndex: null,
        debugLodRemainingS: 0,
        debugFrameRemainingS: 0,
        debugFrameYawRad: 0,
        debugFrameDistanceM: 5,
        debugFrameThroughReplay: false,
        debugFramed: false,
      };
    } catch (error) {
      for (const level of levels) {
        level.mixer.stopAllAction();
        level.mixer.uncacheRoot(level.root);
        disposeSkeletons(level.root);
      }
      lod.clear();
      throw error;
    }
  }

  notifyReplayShot(uid: number): void {
    const actor = this.actors.get(uid);
    if (actor) actor.replayShotSerial += 1;
  }

  beginReplay(): void {
    this.debugActorUid = null;
    for (const actor of this.actors.values()) {
      // A match can enter final-killcam before the last live render update has
      // consumed shot/hit/reload serials. Baseline them here so only events
      // crossing the recorded replay cursor are emitted in the replay window.
      actor.target.getEnemyVisualState(actor.state);
      actor.lastShotSerial = actor.state.shotSerial;
      actor.lastReloadSerial = actor.state.reloadSerial;
      actor.lastHitSerial = actor.state.hitSerial;
      actor.handledReplayShotSerial = actor.replayShotSerial;
      actor.hasPreviousPosition = false;
      actor.oneShot = null;
      actor.pendingReload = false;
      // Query-gated QA overrides must never leak into the real replay path.
      // Clear both before the first recorded frame is applied so the authored
      // Fire/Death clips are selected exclusively from killcam state.
      actor.debugClip = null;
      actor.debugClipRemainingS = 0;
      if (actor.debugFrameThroughReplay && actor.debugFrameRemainingS > 0) {
        // The explicit `?enemyaudit` killcam framing request keeps only the
        // visual position and close LOD. Clip selection still comes entirely
        // from recorded replay state below.
        actor.debugLodIndex = 0;
        actor.debugLodRemainingS = actor.debugFrameRemainingS;
      } else {
        actor.debugLodIndex = null;
        actor.debugLodRemainingS = 0;
        actor.debugFrameRemainingS = 0;
        actor.debugFrameThroughReplay = false;
        this.restoreDebugFraming(actor);
      }
    }
  }

  private restoreDebugFraming(actor: EnemyActor): void {
    if (!actor.debugFramed) return;
    actor.lod.position.set(0, actor.target.enemyVisualFloorOffsetY, 0);
    actor.lod.quaternion.identity();
    actor.lod.scale.setScalar(1);
    actor.lod.visible =
      actor.target.crowdSlot < 0 && actor.target.group.visible && actor.state.visible;
    actor.lod.updateMatrixWorld(true);
    actor.debugFramed = false;
  }

  private applyDebugFraming(actor: EnemyActor): void {
    this.camera.updateMatrixWorld(true);
    actor.target.group.updateWorldMatrix(true, false);
    const cameraWorld = this.camera.getWorldPosition(new THREE.Vector3());
    const forward = this.camera.getWorldDirection(new THREE.Vector3());
    forward.y = 0;
    if (forward.lengthSq() < 1e-6) forward.set(0, 0, -1);
    else forward.normalize();
    const desiredWorld = cameraWorld.clone().addScaledVector(
      forward,
      THREE.MathUtils.clamp(actor.debugFrameDistanceM, 3.25, 7),
    );
    const floorWorld = actor.target.group.localToWorld(
      new THREE.Vector3(0, actor.target.enemyVisualFloorOffsetY, 0),
    );
    const height = this.manifest?.heightMeters ?? 1.8;
    desiredWorld.y = floorWorld.y;
    // Different-elevation actors still need a readable audit composition.
    if (Math.abs(desiredWorld.y + height * 0.52 - cameraWorld.y) > 1.25) {
      desiredWorld.y = cameraWorld.y - height * 0.52;
    }
    actor.lod.position.copy(actor.target.group.worldToLocal(desiredWorld.clone()));

    const toCamera = cameraWorld.clone().sub(desiredWorld);
    toCamera.y = 0;
    if (toCamera.lengthSq() < 1e-6) toCamera.set(0, 0, 1);
    else toCamera.normalize();
    const worldYaw = Math.atan2(-toCamera.x, -toCamera.z) + actor.debugFrameYawRad;
    const desiredWorldQuaternion = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(0, 1, 0),
      worldYaw,
    );
    const parentWorldQuaternion = actor.target.group
      .getWorldQuaternion(new THREE.Quaternion())
      .invert();
    actor.lod.quaternion.copy(parentWorldQuaternion.multiply(desiredWorldQuaternion));
    actor.lod.visible = true;
    actor.lod.updateMatrixWorld(true);
    actor.debugFramed = true;
  }

  private selectDebugActor(actor: EnemyActor): void {
    if (this.debugActorUid !== null && this.debugActorUid !== actor.target.uid) {
      const previous = this.actors.get(this.debugActorUid);
      if (previous) {
        previous.debugFrameRemainingS = 0;
        previous.debugFrameThroughReplay = false;
        this.restoreDebugFraming(previous);
      }
    }
    this.debugActorUid = actor.target.uid;
  }

  private frameDebugActor(
    actor: EnemyActor,
    holdS: number,
    yawDeg: number,
    distanceM: number,
    throughReplay: boolean,
  ): void {
    this.selectDebugActor(actor);
    actor.debugFrameRemainingS = THREE.MathUtils.clamp(holdS, 0.15, 15);
    actor.debugFrameYawRad = THREE.MathUtils.degToRad(
      THREE.MathUtils.clamp(yawDeg, -65, 65),
    );
    actor.debugFrameDistanceM = THREE.MathUtils.clamp(distanceM, 3.25, 7);
    actor.debugFrameThroughReplay = throughReplay;
    this.applyDebugFraming(actor);
  }

  update(dt: number): void {
    if (!this.ready || this.disposed) return;
    const safeDt = Number.isFinite(dt) ? THREE.MathUtils.clamp(dt, 0, 0.1) : 0;
    for (const actor of [...this.actors.values()]) {
      try {
        this.updateActor(actor, safeDt);
      } catch {
        this.releaseActor(actor);
      }
    }
  }

  private updateActor(actor: EnemyActor, dt: number): void {
    const { target, state } = actor;
    target.getEnemyVisualState(state);
    const x = target.group.position.x;
    const z = target.group.position.z;
    const dx = actor.hasPreviousPosition ? x - actor.previousX : 0;
    const dz = actor.hasPreviousPosition ? z - actor.previousZ : 0;
    actor.previousX = x;
    actor.previousZ = z;
    actor.hasPreviousPosition = true;

    if (target.shadowCasting !== actor.lastShadowCasting) {
      actor.lastShadowCasting = target.shadowCasting;
      for (const level of actor.levels) {
        level.root.traverse((node) => {
          if (node instanceof THREE.Mesh) {
            node.castShadow = target.shadowCasting && level.level === 0;
          }
        });
      }
    }

    if (actor.debugFrameRemainingS > 0) {
      actor.debugFrameRemainingS = Math.max(0, actor.debugFrameRemainingS - dt);
      this.applyDebugFraming(actor);
    } else if (actor.debugFramed) {
      actor.debugFrameThroughReplay = false;
      this.restoreDebugFraming(actor);
    }

    const distance = this.camera.position.distanceTo(target.group.position);
    const threshold0 = actor.levels[0] ? this.loadedLods[0]?.distance ?? 0 : 0;
    const threshold1 = actor.levels[1] ? this.loadedLods[1]?.distance ?? 12 : 12;
    const threshold2 = actor.levels[2] ? this.loadedLods[2]?.distance ?? 36 : 36;
    if (actor.debugLodIndex !== null) {
      actor.debugLodRemainingS = Math.max(0, actor.debugLodRemainingS - dt);
      if (actor.debugLodRemainingS <= 0) actor.debugLodIndex = null;
    }
    const nextLod = actor.debugLodIndex ??
      selectEnemyLod(distance, [threshold0, threshold1, threshold2], actor.lodIndex);
    if (nextLod !== actor.lodIndex) {
      actor.lodIndex = nextLod;
      for (let index = 0; index < actor.levels.length; index += 1) {
        const level = actor.levels[index];
        if (level) level.root.visible = index === nextLod;
      }
    }

    const individualVisible = target.crowdSlot < 0 && target.group.visible && state.visible;
    const shotChanged = state.shotSerial !== actor.lastShotSerial;
    const reloadChanged = state.reloadSerial !== actor.lastReloadSerial;
    const hitChanged = state.hitSerial !== actor.lastHitSerial;
    const replayShotChanged = actor.replayShotSerial !== actor.handledReplayShotSerial;
    actor.lastShotSerial = state.shotSerial;
    actor.lastReloadSerial = state.reloadSerial;
    actor.lastHitSerial = state.hitSerial;
    actor.handledReplayShotSerial = actor.replayShotSerial;

    const replayAlive = state.killcamReplay && state.killcamDeath01 <= 0;
    const effectiveAlive = state.killcamReplay ? replayAlive : state.alive;
    if (actor.debugClip && actor.debugClipRemainingS > 0) {
      const clip = actor.debugClip;
      const restart = actor.currentClip !== clip || actor.currentActionLod !== actor.lodIndex;
      this.setActorClip(actor, clip, restart, restart ? 0 : STATE_CROSSFADE_S);
      actor.levels[actor.lodIndex]?.mixer.update(dt);
      actor.debugClipRemainingS = Math.max(0, actor.debugClipRemainingS - dt);
      if (actor.debugClipRemainingS <= 0) actor.debugClip = null;
      actor.wasAlive = effectiveAlive;
      return;
    }

    if (!individualVisible) {
      actor.oneShot = null;
      actor.pendingReload = false;
      actor.wasAlive = effectiveAlive;
      return;
    }

    if (state.killcamReplay && state.killcamDeath01 > 0) {
      actor.oneShot = null;
      actor.pendingReload = false;
      const deathClip = state.hitFromBack ? 'AN_Soldier_DeathBack' : 'AN_Soldier_DeathFront';
      const action = this.setActorClip(actor, deathClip, !actor.wasAlive, 0);
      const clip = action.getClip();
      action.paused = true;
      action.time = THREE.MathUtils.clamp(state.killcamDeath01, 0, 1) * clip.duration;
      actor.levels[actor.lodIndex]?.mixer.update(0);
      actor.wasAlive = false;
      return;
    }

    if (!effectiveAlive) {
      actor.oneShot = null;
      actor.pendingReload = false;
      const deathClip = state.hitFromBack ? 'AN_Soldier_DeathBack' : 'AN_Soldier_DeathFront';
      const action = this.setActorClip(actor, deathClip, actor.wasAlive, 0.05);
      action.paused = false;
      actor.levels[actor.lodIndex]?.mixer.update(dt);
      actor.wasAlive = false;
      return;
    }

    if (!actor.wasAlive) {
      actor.oneShot = null;
      actor.pendingReload = false;
    }
    actor.wasAlive = true;
    if (reloadChanged) actor.pendingReload = true;
    if (shotChanged || replayShotChanged) actor.oneShot = { clip: 'AN_Soldier_Fire', elapsed: 0 };
    if (hitChanged) {
      actor.oneShot = {
        clip: state.hitFromBack ? 'AN_Soldier_HitBack' : 'AN_Soldier_HitFront',
        elapsed: 0,
      };
    }
    if (!actor.oneShot && actor.pendingReload) {
      actor.oneShot = { clip: 'AN_Soldier_Reload', elapsed: 0 };
      actor.pendingReload = false;
    }

    const measuredSpeed = dt > 1e-5 ? Math.hypot(dx, dz) / dt : 0;
    const speed = state.killcamReplay ? measuredSpeed : state.speedMps;
    const baseClip = selectEnemyBaseAnimation({
      aiState: state.aiState,
      speedMps: speed,
      movementX: dx,
      movementZ: dz,
      heading: target.group.rotation.y,
    });
    let clip = baseClip;
    let restart = false;
    if (actor.oneShot) {
      actor.oneShot.elapsed += dt;
      const activeLevel = actor.levels[actor.lodIndex];
      const duration = activeLevel?.clips.get(actor.oneShot.clip)?.duration ?? 0;
      if (duration > 0 && actor.oneShot.elapsed < duration) {
        clip = actor.oneShot.clip;
        restart = actor.currentClip !== clip || actor.oneShot.elapsed <= dt + 1e-6;
      } else {
        actor.oneShot = null;
        if (actor.pendingReload) {
          actor.oneShot = { clip: 'AN_Soldier_Reload', elapsed: 0 };
          actor.pendingReload = false;
          clip = 'AN_Soldier_Reload';
          restart = true;
        }
      }
    }
    this.setActorClip(actor, clip, restart, STATE_CROSSFADE_S);
    actor.levels[actor.lodIndex]?.mixer.update(dt);
  }

  private setActorClip(
    actor: EnemyActor,
    clipName: EnemyClipName,
    restart: boolean,
    crossfadeS: number,
  ): THREE.AnimationAction {
    const level = actor.levels[actor.lodIndex];
    if (!level) throw new Error(`enemy actor has no LOD${actor.lodIndex}`);
    const clip = level.clips.get(clipName);
    if (!clip) throw new Error(`enemy actor is missing ${clipName}`);
    let action = level.actions.get(clipName);
    if (!action) {
      action = level.mixer.clipAction(clip, level.root);
      level.actions.set(clipName, action);
    }
    const lodChanged = actor.currentActionLod !== actor.lodIndex;
    if (actor.currentAction === action && !restart && !lodChanged) {
      action.paused = false;
      return action;
    }
    const previous = actor.currentAction;
    const previousClip = previous?.getClip();
    const normalized =
      previous && previousClip && previousClip.duration > 0
        ? (previous.time % previousClip.duration) / previousClip.duration
        : 0;
    action.enabled = true;
    action.paused = false;
    action.setEffectiveTimeScale(1);
    action.setEffectiveWeight(1);
    action.reset();
    if (LOOPING_CLIPS.has(clipName)) {
      action.setLoop(THREE.LoopRepeat, Infinity);
      action.clampWhenFinished = false;
      if (lodChanged && actor.currentClip === clipName) action.time = normalized * clip.duration;
    } else {
      action.setLoop(THREE.LoopOnce, 1);
      action.clampWhenFinished = true;
    }
    action.play();
    if (previous && previous !== action) {
      if (!lodChanged && crossfadeS > 0) previous.crossFadeTo(action, crossfadeS, false);
      else previous.stop();
    }
    actor.currentClip = clipName;
    actor.currentAction = action;
    actor.currentActionLod = actor.lodIndex;
    return action;
  }

  /**
   * Query-gated browser QA helper. It drives the actual imported clip on an
   * integrated actor; main.ts never exposes this method without `?enemyaudit`.
   */
  debugPlayClip(
    clip: EnemyClipName,
    variantId?: EnemyVariantId,
    holdS = 0.9,
    startAt01 = 0,
    framingYawDeg = 0,
    framingDistanceM = 5,
    preferredUid?: number,
  ): number | null {
    if (!this.ready || !REQUIRED_CLIP_SET.has(clip)) return null;
    const preferred = preferredUid === undefined ? null : this.actors.get(preferredUid) ?? null;
    const actor = preferred && (!variantId || preferred.variantId === variantId)
      ? preferred
      : this.debugActor(variantId);
    if (!actor) return null;
    const safeHold = THREE.MathUtils.clamp(holdS, 0.15, 4);
    this.frameDebugActor(actor, safeHold, framingYawDeg, framingDistanceM, false);
    actor.debugLodIndex = 0;
    actor.debugLodRemainingS = safeHold;
    if (actor.lodIndex !== 0) {
      actor.lodIndex = 0;
      for (let index = 0; index < actor.levels.length; index += 1) {
        const level = actor.levels[index];
        if (level) level.root.visible = index === 0;
      }
    }
    actor.debugClip = clip;
    actor.debugClipRemainingS = safeHold;
    actor.oneShot = null;
    actor.pendingReload = false;
    const action = this.setActorClip(actor, clip, true, 0);
    action.time = THREE.MathUtils.clamp(startAt01, 0, 0.95) * action.getClip().duration;
    actor.levels[actor.lodIndex]?.mixer.update(0);
    return actor.target.uid;
  }

  /** Frame one exact integrated actor for visual QA; physics/AI remain untouched. */
  debugFrameActor(
    uid: number,
    yawDeg = 0,
    distanceM = 5,
    holdS = 1,
    throughReplay = false,
  ): number | null {
    if (!this.ready) return null;
    const actor = this.actors.get(uid);
    if (!actor) return null;
    const safeHold = THREE.MathUtils.clamp(holdS, 0.15, throughReplay ? 15 : 4);
    this.frameDebugActor(actor, safeHold, yawDeg, distanceM, throughReplay);
    actor.debugLodIndex = 0;
    actor.debugLodRemainingS = safeHold;
    if (actor.lodIndex !== 0) {
      actor.lodIndex = 0;
      for (let index = 0; index < actor.levels.length; index += 1) {
        const level = actor.levels[index];
        if (level) level.root.visible = index === 0;
      }
      if (actor.currentClip) this.setActorClip(actor, actor.currentClip, false, 0);
    }
    return actor.target.uid;
  }

  /** Exercise the real per-actor LOD roots without moving gameplay physics. */
  debugForceLod(
    level: 0 | 1 | 2,
    variantId?: EnemyVariantId,
    holdS = 0.9,
  ): number | null {
    if (!this.ready) return null;
    const previous = this.debugActorUid === null
      ? null
      : this.actors.get(this.debugActorUid) ?? null;
    const actor = previous && (!variantId || previous.variantId === variantId)
      ? previous
      : this.debugActor(variantId);
    if (!actor || !actor.levels[level]) return null;
    this.debugActorUid = actor.target.uid;
    this.frameDebugActor(actor, holdS, actor.debugFrameYawRad * 180 / Math.PI,
      actor.debugFrameDistanceM, false);
    actor.debugLodIndex = level;
    actor.debugLodRemainingS = THREE.MathUtils.clamp(holdS, 0.15, 4);
    if (actor.lodIndex !== level) {
      actor.lodIndex = level;
      for (let index = 0; index < actor.levels.length; index += 1) {
        const actorLevel = actor.levels[index];
        if (actorLevel) actorLevel.root.visible = index === level;
      }
      if (actor.currentClip) this.setActorClip(actor, actor.currentClip, false, 0);
    }
    return actor.target.uid;
  }

  /** Snapshot used by the ignored headless-browser evidence harness. */
  debugSnapshot(): EnemyAssetAuditSnapshot {
    const actors = [...this.actors.values()].map((actor): EnemyActorAuditSnapshot => {
      actor.target.getEnemyVisualState(actor.state);
      const visibility = actor.target.getEnemyVisualVisibilityAudit();
      const world = actor.debugFramed
        ? actor.lod.getWorldPosition(new THREE.Vector3())
        : actor.target.group.getWorldPosition(new THREE.Vector3());
      const projected = world.clone();
      projected.y += 1.2;
      projected.project(this.camera);
      const skinnedMeshesPerLod = actor.levels.map((level) => {
        let count = 0;
        level.root.traverse((node) => {
          if (node instanceof THREE.SkinnedMesh) count += 1;
        });
        return count;
      });
      const action = actor.currentActionLod === actor.lodIndex ? actor.currentAction : null;
      const duration = action?.getClip().duration ?? 0;
      return {
        uid: actor.target.uid,
        team: actor.target.team,
        variantId: actor.variantId,
        alive: actor.state.alive,
        killcamReplay: actor.state.killcamReplay,
        killcamDeath01: actor.state.killcamDeath01,
        distanceM: Number(this.camera.position.distanceTo(world).toFixed(4)),
        lodIndex: actor.lodIndex,
        visibleLods: actor.levels
          .filter((level) => level.root.visible)
          .map((level) => level.level),
        skinnedMeshesPerLod,
        currentClip: actor.currentClip,
        actionTimeS: Number((action?.time ?? 0).toFixed(6)),
        actionDurationS: Number(duration.toFixed(6)),
        actionRunning: Boolean(action?.isRunning()),
        debugFramed: actor.debugFramed,
        externalParented: actor.lod.parent === actor.target.group,
        externalVisible: visibility.externalVisualVisible,
        proceduralRigVisible: visibility.proceduralRigVisible,
        crowdSlot: visibility.crowdSlot,
        inView:
          actor.target.group.visible &&
          visibility.externalVisualVisible &&
          projected.z >= -1 && projected.z <= 1 &&
          Math.abs(projected.x) <= 1 &&
          Math.abs(projected.y) <= 1,
        screenX01: Number(((projected.x + 1) * 0.5).toFixed(6)),
        screenY01: Number(((1 - projected.y) * 0.5).toFixed(6)),
      };
    });
    return {
      ready: this.isReady,
      sourceLods: this.loadedLods.length,
      sourceVariants: this.manifest?.variants.length ?? 0,
      actorCount: actors.length,
      variants: [...new Set(actors.map((actor) => actor.variantId))].sort(),
      activeClips: [...new Set(
        actors.flatMap((actor) => actor.currentClip ? [actor.currentClip] : []),
      )].sort(),
      activeLods: [...new Set(actors.map((actor) => actor.lodIndex))].sort(),
      actors,
    };
  }

  private debugActor(variantId?: EnemyVariantId): EnemyActor | null {
    const candidates = [...this.actors.values()].filter(
      (actor) => !variantId || actor.variantId === variantId,
    );
    const externallyVisible = (actor: EnemyActor): boolean => {
      const visibility = actor.target.getEnemyVisualVisibilityAudit();
      return visibility.externalVisualVisible && actor.target.group.visible;
    };
    // Prefer an actor whose authored rig is actually inside the current camera
    // frustum so the ignored article/QA screenshot contains useful evidence.
    const inView = candidates.find((actor) => {
      if (!externallyVisible(actor)) return false;
      const projected = actor.target.group.getWorldPosition(new THREE.Vector3());
      projected.y += 1.2;
      projected.project(this.camera);
      return projected.z >= -1 && projected.z <= 1 &&
        Math.abs(projected.x) <= 0.92 && Math.abs(projected.y) <= 0.92;
    });
    return inView ?? candidates.find(externallyVisible) ?? candidates[0] ?? null;
  }

  private releaseActor(actor: EnemyActor): void {
    if (this.debugActorUid === actor.target.uid) this.debugActorUid = null;
    this.actors.delete(actor.target.uid);
    try {
      actor.target.setExternalEnemyVisual(null);
    } catch {
      // The visual fallback must not make disposal fail.
    }
    for (const level of actor.levels) {
      level.mixer.stopAllAction();
      for (const action of level.actions.values()) level.mixer.uncacheAction(action.getClip(), level.root);
      level.mixer.uncacheRoot(level.root);
      disposeSkeletons(level.root);
    }
    actor.lod.clear();
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.ready = false;
    this.controller.abort();
    for (const actor of [...this.actors.values()]) this.releaseActor(actor);
    this.targets.clear();
    disposeSources(this.loadedLods);
    this.loadedLods = [];
    this.runtime?.dispose();
    this.runtime = null;
    this.manifest = null;
  }
}
