import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { clone as skeletonClone } from 'three/addons/utils/SkeletonUtils.js';
import type { EnemyVisualState } from '../game/bot';
import {
  ENEMY_CLIP_NAMES,
  ENEMY_VARIANT_IDS,
  EnemyAssetPipeline,
  enemyLodDistances,
  enemyVariantFor,
  parseEnemyAssetManifest,
  selectEnemyBaseAnimation,
  selectEnemyLod,
  type EnemyAssetManifest,
  type EnemyVisualTarget,
} from './enemy-asset-pipeline';

const runtimeMocks = vi.hoisted(() => ({
  loadScene: vi.fn(),
  clone: vi.fn(),
  dispose: vi.fn(),
}));

vi.mock('./gltf-runtime.js', () => ({
  createGltfRuntime: vi.fn(() => runtimeMocks),
}));

const MANIFEST: EnemyAssetManifest = {
  schemaVersion: 1,
  packVersion: 1,
  id: 'hibana-enemy-soldiers',
  sharedSkeleton: 'ARM_Enemy_Shared',
  heightMeters: 1.8,
  forwardAxis: '-Z',
  variants: ENEMY_VARIANT_IDS,
  animations: ENEMY_CLIP_NAMES,
  lods: [
    { level: 0, url: 'soldier-pack-lod0.glb', screenHeightMin: 0.24 },
    { level: 1, url: 'soldier-pack-lod1.glb', screenHeightMin: 0.09 },
    { level: 2, url: 'soldier-pack-lod2.glb', screenHeightMin: 0 },
  ],
};

function makeSource(level: number, missingClip?: string): THREE.Group {
  const root = new THREE.Group();
  root.name = `pack-lod${level}`;
  for (const variant of ENEMY_VARIANT_IDS) {
    const bone = new THREE.Bone();
    bone.name = `root_${variant}_${level}`;
    root.add(bone);
    const mesh = new THREE.SkinnedMesh(
      new THREE.BoxGeometry(0.3, 1.8, 0.25),
      new THREE.MeshStandardMaterial({ color: 0x555555 }),
    );
    mesh.name = `${variant}-lod${level}`;
    mesh.userData.variantId = variant;
    mesh.bind(new THREE.Skeleton([bone]));
    root.add(mesh);
  }
  root.animations = ENEMY_CLIP_NAMES
    .filter((name) => name !== missingClip)
    .map((name) => new THREE.AnimationClip(name, name.includes('Idle') ? 3 : 1, []));
  return root;
}

/** Mirrors GLTFLoader's multi-material shape: extras live on a Group and each primitive is a SkinnedMesh. */
function makeGroupedSource(level: number): THREE.Group {
  const root = new THREE.Group();
  root.name = `grouped-pack-lod${level}`;
  const bone = new THREE.Bone();
  bone.name = `root_${level}`;
  root.add(bone);
  for (const variant of ENEMY_VARIANT_IDS) {
    const variantRoot = new THREE.Group();
    variantRoot.name = `${variant}-lod${level}`;
    variantRoot.userData.variantId = variant;
    for (let primitive = 0; primitive < 2; primitive += 1) {
      const mesh = new THREE.SkinnedMesh(
        new THREE.BoxGeometry(0.3, 1.8, 0.25),
        new THREE.MeshStandardMaterial({ color: 0x555555 }),
      );
      mesh.name = `${variant}-lod${level}-primitive${primitive}`;
      mesh.bind(new THREE.Skeleton([bone]));
      variantRoot.add(mesh);
    }
    root.add(variantRoot);
  }
  root.animations = ENEMY_CLIP_NAMES.map(
    (name) => new THREE.AnimationClip(name, name.includes('Idle') ? 3 : 1, []),
  );
  return root;
}

function state(overrides: Partial<EnemyVisualState> = {}): EnemyVisualState {
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
    ...overrides,
  };
}

class FakeTarget implements EnemyVisualTarget {
  readonly group = new THREE.Group();
  crowdSlot = -1;
  shadowCasting = true;
  enemyVisualFloorOffsetY = -0.8;
  current = state();
  external: THREE.Object3D | null = null;
  proceduralVisible = true;

  constructor(readonly uid: number, readonly team: number) {}

  getEnemyVisualState(out: EnemyVisualState): void {
    Object.assign(out, this.current);
  }

  getEnemyVisualVisibilityAudit() {
    return {
      proceduralRigVisible: this.proceduralVisible,
      externalVisualPresent: this.external !== null,
      externalVisualVisible: Boolean(this.external?.visible && this.group.visible),
      crowdSlot: this.crowdSlot,
    };
  }

  setExternalEnemyVisual(root: THREE.Object3D | null): void {
    if (this.external) this.group.remove(this.external);
    this.external = root;
    this.proceduralVisible = root === null;
    if (root) this.group.add(root);
  }
}

function stubManifest(): void {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(MANIFEST), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })));
}

beforeEach(() => {
  runtimeMocks.clone.mockImplementation((source: THREE.Object3D) => skeletonClone(source));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('enemy asset manifest and deterministic policy', () => {
  it('strictly accepts the authored six variants, three LODs and fourteen clips', () => {
    const parsed = parseEnemyAssetManifest(MANIFEST);
    expect(parsed.variants).toEqual(ENEMY_VARIANT_IDS);
    expect(parsed.animations).toHaveLength(14);
    expect(parsed.lods.map((lod) => lod.level)).toEqual([0, 1, 2]);
  });

  it.each([
    'https://example.com/soldier.glb',
    '../soldier.glb',
    '/absolute/soldier.glb',
    'data:model/gltf-binary;base64,AAAA',
  ])('rejects unsafe GLB paths: %s', (url) => {
    expect(() => parseEnemyAssetManifest({
      ...MANIFEST,
      lods: [{ ...MANIFEST.lods[0], url }, MANIFEST.lods[1], MANIFEST.lods[2]],
    })).toThrow(/safe relative path/);
  });

  it('rejects packs that silently omit an authored combat animation', () => {
    expect(() => parseEnemyAssetManifest({
      ...MANIFEST,
      animations: ENEMY_CLIP_NAMES.filter((clip) => clip !== 'AN_Soldier_Fire'),
    })).toThrow(/missing a required animation/);
  });

  it('distributes six sequential bot ids across all six variantId values deterministically', () => {
    const first = Array.from({ length: 6 }, (_, uid) => enemyVariantFor(uid, 1));
    const second = Array.from({ length: 6 }, (_, uid) => enemyVariantFor(uid, 1));
    expect(new Set(first)).toEqual(new Set(ENEMY_VARIANT_IDS));
    expect(second).toEqual(first);
  });

  it('derives ordered distance LODs and applies hysteresis around transitions', () => {
    const distances = enemyLodDistances(MANIFEST, 78);
    expect(distances[0]).toBe(0);
    expect(distances[1]).toBeGreaterThan(5);
    expect(distances[2]).toBeGreaterThan(distances[1]);
    expect(selectEnemyLod(distances[1] * 1.2, distances, 0)).toBe(1);
    expect(selectEnemyLod(distances[1] * 0.95, distances, 1)).toBe(1);
    expect(selectEnemyLod(distances[1] * 0.8, distances, 1)).toBe(0);
  });
});

describe('AI to Blender animation mapping', () => {
  it('maps idle, ready and aim directly from the existing AI state', () => {
    expect(selectEnemyBaseAnimation({ aiState: 'patrol', speedMps: 0, movementX: 0, movementZ: 0, heading: 0 }))
      .toBe('AN_Soldier_Idle');
    expect(selectEnemyBaseAnimation({ aiState: 'search', speedMps: 0, movementX: 0, movementZ: 0, heading: 0 }))
      .toBe('AN_Soldier_RifleReady');
    expect(selectEnemyBaseAnimation({ aiState: 'combat', speedMps: 0, movementX: 0, movementZ: 0, heading: 0 }))
      .toBe('AN_Soldier_Aim');
  });

  it('maps forward, backward, both strafes and run without changing AI movement', () => {
    expect(selectEnemyBaseAnimation({ aiState: 'combat', speedMps: 2, movementX: 0, movementZ: -1, heading: 0 }))
      .toBe('AN_Soldier_WalkForward');
    expect(selectEnemyBaseAnimation({ aiState: 'combat', speedMps: 2, movementX: 0, movementZ: 1, heading: 0 }))
      .toBe('AN_Soldier_WalkBackward');
    expect(selectEnemyBaseAnimation({ aiState: 'combat', speedMps: 2, movementX: -1, movementZ: 0, heading: 0 }))
      .toBe('AN_Soldier_StrafeLeft');
    expect(selectEnemyBaseAnimation({ aiState: 'combat', speedMps: 2, movementX: 1, movementZ: 0, heading: 0 }))
      .toBe('AN_Soldier_StrafeRight');
    expect(selectEnemyBaseAnimation({ aiState: 'combat', speedMps: 6, movementX: 0, movementZ: -1, heading: 0 }))
      .toBe('AN_Soldier_RunForward');
  });
});

describe('EnemyAssetPipeline fail-open lifecycle', () => {
  it('uses Meshopt runtime clones, commits only after compile, and keeps one variant per LOD', async () => {
    stubManifest();
    runtimeMocks.loadScene
      .mockResolvedValueOnce(makeSource(0))
      .mockResolvedValueOnce(makeSource(1))
      .mockResolvedValueOnce(makeSource(2));
    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(78, 1, 0.05, 800);
    scene.add(camera);
    const target = new FakeTarget(2, 1);
    scene.add(target.group);
    const pipeline = new EnemyAssetPipeline(scene, renderer, camera);
    pipeline.register(target);

    const report = await pipeline.load({ manifestUrl: '/assets/aaa/enemies/manifest.json' });

    expect(report).toMatchObject({ ready: true, sourceLods: 3, variants: 6, actors: 1, failedActors: 0 });
    expect(runtimeMocks.loadScene.mock.calls.map((call) => call[0])).toEqual([
      '/assets/aaa/enemies/soldier-pack-lod0.glb',
      '/assets/aaa/enemies/soldier-pack-lod1.glb',
      '/assets/aaa/enemies/soldier-pack-lod2.glb',
    ]);
    expect(renderer.compileAsync).toHaveBeenCalledOnce();
    expect(target.external).toBeInstanceOf(THREE.LOD);
    expect(target.proceduralVisible).toBe(false);
    const variants: string[] = [];
    target.external?.traverse((node) => {
      if (node instanceof THREE.SkinnedMesh) variants.push(node.userData.variantId as string);
    });
    expect(variants).toHaveLength(3);
    expect(new Set(variants)).toEqual(new Set([enemyVariantFor(2, 1)]));
    expect(target.external?.position.y).toBeCloseTo(-0.8);

    pipeline.dispose();
    expect(target.external).toBeNull();
    expect(target.proceduralVisible).toBe(true);
    expect(runtimeMocks.dispose).toHaveBeenCalledOnce();
  });

  it('keeps the procedural soldier when a GLB omits Fire animation', async () => {
    stubManifest();
    class FakeImageBitmap {
      readonly close = vi.fn();
    }
    vi.stubGlobal('ImageBitmap', FakeImageBitmap);
    const invalidSource = makeSource(0, 'AN_Soldier_Fire');
    const invalidMesh = invalidSource.children.find(
      (child): child is THREE.SkinnedMesh => child instanceof THREE.SkinnedMesh,
    );
    if (!invalidMesh) throw new Error('test fixture is missing a SkinnedMesh');
    const geometryDispose = vi.spyOn(invalidMesh.geometry, 'dispose');
    const materialDispose = vi.spyOn(invalidMesh.material as THREE.Material, 'dispose');
    const skeletonDispose = vi.spyOn(invalidMesh.skeleton, 'dispose');
    const imageBitmap = new FakeImageBitmap();
    const texture = new THREE.Texture();
    (texture.source as unknown as { data: unknown }).data = imageBitmap;
    (invalidMesh.material as THREE.MeshStandardMaterial).map = texture;
    const textureDispose = vi.spyOn(texture, 'dispose');
    runtimeMocks.loadScene.mockResolvedValueOnce(invalidSource);
    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera();
    scene.add(camera);
    const target = new FakeTarget(0, 1);
    const pipeline = new EnemyAssetPipeline(scene, renderer, camera);
    pipeline.register(target);

    const report = await pipeline.load({ manifestUrl: '/assets/aaa/enemies/manifest.json' });

    expect(report.ready).toBe(false);
    expect(report.errors[0]).toContain('AN_Soldier_Fire');
    expect(target.external).toBeNull();
    expect(target.proceduralVisible).toBe(true);
    expect(renderer.compileAsync).not.toHaveBeenCalled();
    expect(runtimeMocks.dispose).toHaveBeenCalledOnce();
    expect(geometryDispose).toHaveBeenCalledOnce();
    expect(materialDispose).toHaveBeenCalledOnce();
    expect(skeletonDispose).toHaveBeenCalledOnce();
    expect(textureDispose).toHaveBeenCalledOnce();
    expect(imageBitmap.close).toHaveBeenCalledOnce();
    pipeline.dispose();
  });

  it('attaches and releases bots added after preload without disposing shared sources early', async () => {
    stubManifest();
    const sources = [makeSource(0), makeSource(1), makeSource(2)];
    runtimeMocks.loadScene
      .mockResolvedValueOnce(sources[0])
      .mockResolvedValueOnce(sources[1])
      .mockResolvedValueOnce(sources[2]);
    const sourceMesh = sources[0]?.children.find(
      (child): child is THREE.SkinnedMesh => child instanceof THREE.SkinnedMesh,
    );
    if (!sourceMesh) throw new Error('test fixture is missing a source SkinnedMesh');
    const sourceGeometryDispose = vi.spyOn(sourceMesh.geometry, 'dispose');
    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(78, 1, 0.05, 800);
    scene.add(camera);
    const pipeline = new EnemyAssetPipeline(scene, renderer, camera);

    const report = await pipeline.load({ manifestUrl: '/assets/aaa/enemies/manifest.json' });
    const first = new FakeTarget(10, 1);
    const second = new FakeTarget(11, 1);
    pipeline.register(first);
    pipeline.register(second);
    const firstMesh = first.external?.getObjectByProperty('type', 'SkinnedMesh') as
      | THREE.SkinnedMesh
      | undefined;
    if (!firstMesh) throw new Error('test actor is missing a SkinnedMesh');
    const actorSkeletonDispose = vi.spyOn(firstMesh.skeleton, 'dispose');

    expect(report).toMatchObject({ ready: true, sourceLods: 3, actors: 0 });
    expect(first.external).toBeInstanceOf(THREE.LOD);
    expect(second.external).toBeInstanceOf(THREE.LOD);
    expect(first.proceduralVisible).toBe(false);
    expect(second.proceduralVisible).toBe(false);

    pipeline.unregister(first);

    expect(first.external).toBeNull();
    expect(first.proceduralVisible).toBe(true);
    expect(second.external).toBeInstanceOf(THREE.LOD);
    expect(second.proceduralVisible).toBe(false);
    expect(actorSkeletonDispose).toHaveBeenCalledOnce();
    expect(sourceGeometryDispose).not.toHaveBeenCalled();

    pipeline.dispose();
    expect(second.external).toBeNull();
    expect(second.proceduralVisible).toBe(true);
    expect(sourceGeometryDispose).toHaveBeenCalledOnce();
  });

  it('baselines unconsumed live serials at replay start and accepts only recorded shot notifications', async () => {
    stubManifest();
    runtimeMocks.loadScene
      .mockResolvedValueOnce(makeSource(0))
      .mockResolvedValueOnce(makeSource(1))
      .mockResolvedValueOnce(makeSource(2));
    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera();
    scene.add(camera);
    const target = new FakeTarget(21, 1);
    const pipeline = new EnemyAssetPipeline(scene, renderer, camera);
    pipeline.register(target);
    await pipeline.load({ manifestUrl: '/assets/aaa/enemies/manifest.json' });
    // A deep browser audit can leave a forced clip/LOD active immediately
    // before the real final-killcam path. beginReplay must clear both.
    expect(pipeline.debugPlayClip('AN_Soldier_WalkForward', undefined, 3)).toBe(target.uid);
    expect(pipeline.debugForceLod(2, undefined, 3)).toBe(target.uid);
    target.current = state({ shotSerial: 1, hitSerial: 1, reloadSerial: 1, killcamReplay: true });

    pipeline.beginReplay();
    pipeline.update(1 / 60);
    const actors = (pipeline as unknown as {
      actors: Map<number, {
        oneShot: { clip: string } | null;
        debugClip: string | null;
        debugLodIndex: number | null;
        debugFramed: boolean;
      }>;
    }).actors;
    expect(actors.get(target.uid)?.oneShot).toBeNull();
    expect(actors.get(target.uid)?.debugClip).toBeNull();
    expect(actors.get(target.uid)?.debugLodIndex).toBeNull();
    expect(actors.get(target.uid)?.debugFramed).toBe(false);

    pipeline.notifyReplayShot(target.uid);
    pipeline.update(1 / 60);
    expect(actors.get(target.uid)?.oneShot?.clip).toBe('AN_Soldier_Fire');
    target.current = state({ killcamReplay: true, killcamDeath01: 0.5 });
    pipeline.update(1 / 60);
    expect(pipeline.debugSnapshot().actors[0]?.currentClip).toBe('AN_Soldier_DeathFront');

    expect(pipeline.debugFrameActor(target.uid, 25, 4.5, 3, true)).toBe(target.uid);
    pipeline.beginReplay();
    pipeline.update(0);
    expect(pipeline.debugSnapshot().actors[0]).toMatchObject({
      debugFramed: true,
      lodIndex: 0,
      visibleLods: [0],
    });
    pipeline.dispose();
  });

  it('exposes query-gated clip and LOD evidence from the actual integrated actor roots', async () => {
    stubManifest();
    const sources = [makeGroupedSource(0), makeGroupedSource(1), makeGroupedSource(2)];
    runtimeMocks.loadScene
      .mockResolvedValueOnce(sources[0])
      .mockResolvedValueOnce(sources[1])
      .mockResolvedValueOnce(sources[2]);
    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(78, 1, 0.05, 800);
    scene.add(camera);
    const target = new FakeTarget(9, 1);
    target.group.position.set(0, 0, -5);
    scene.add(target.group);
    const pipeline = new EnemyAssetPipeline(scene, renderer, camera);
    pipeline.register(target);
    const report = await pipeline.load({ manifestUrl: '/assets/aaa/enemies/manifest.json' });

    const variantId = enemyVariantFor(target.uid, target.team);
    expect(report).toMatchObject({
      ready: true,
      sourceLods: 3,
      variants: 6,
      actors: 1,
      failedActors: 0,
      errors: [],
    });
    // 18 prewarm clones (6 variants x 3 LODs) + one actor's 3 LOD clones.
    expect(runtimeMocks.clone).toHaveBeenCalledTimes(21);
    const actorLod = target.external as THREE.LOD;
    expect(actorLod.children.map((child) => child.name)).toEqual([
      `aaa:enemy:${variantId}:lod0`,
      `aaa:enemy:${variantId}:lod1`,
      `aaa:enemy:${variantId}:lod2`,
    ]);
    for (const levelRoot of actorLod.children) {
      const meshes: THREE.SkinnedMesh[] = [];
      levelRoot.traverse((node) => {
        if (node instanceof THREE.SkinnedMesh) meshes.push(node);
      });
      expect(meshes).toHaveLength(2);
      expect(new Set(meshes.map((mesh) => mesh.userData.variantId))).toEqual(new Set([variantId]));
      expect(meshes.every((mesh) => mesh.name.startsWith(`${variantId}-`))).toBe(true);
      expect(
        ENEMY_VARIANT_IDS
          .filter((other) => other !== variantId)
          .every((other) => levelRoot.getObjectByName(`${other}-lod0`) === undefined),
      ).toBe(true);
    }
    const sourceVariantRoot = sources[0]?.children.find(
      (child) => child.userData.variantId === variantId,
    );
    const sourceMesh = sourceVariantRoot?.children.find(
      (child): child is THREE.SkinnedMesh => child instanceof THREE.SkinnedMesh,
    );
    const actorMesh = actorLod.children[0]?.getObjectByProperty('type', 'SkinnedMesh') as
      | THREE.SkinnedMesh
      | undefined;
    if (!sourceMesh || !actorMesh) throw new Error('grouped source/actor fixture is incomplete');
    expect(actorMesh.geometry).toBe(sourceMesh.geometry);
    expect(actorMesh.material).toBe(sourceMesh.material);
    expect(actorMesh.skeleton).not.toBe(sourceMesh.skeleton);
    expect(actorMesh.skeleton.bones[0]).not.toBe(sourceMesh.skeleton.bones[0]);
    const sourceGeometryDispose = vi.spyOn(sourceMesh.geometry, 'dispose');
    const sourceMaterialDispose = vi.spyOn(sourceMesh.material as THREE.Material, 'dispose');
    const sourceSkeletonDispose = vi.spyOn(sourceMesh.skeleton, 'dispose');
    const actorSkeletonDispose = vi.spyOn(actorMesh.skeleton, 'dispose');

    expect(pipeline.debugPlayClip('AN_Soldier_Reload', variantId, 1)).toBe(target.uid);
    pipeline.update(0.1);
    const playing = pipeline.debugSnapshot();
    expect(playing).toMatchObject({ ready: true, sourceLods: 3, sourceVariants: 6, actorCount: 1 });
    expect(playing.actors[0]).toMatchObject({
      variantId,
      currentClip: 'AN_Soldier_Reload',
      lodIndex: 0,
      visibleLods: [0],
      skinnedMeshesPerLod: [2, 2, 2],
      debugFramed: true,
      externalParented: true,
      externalVisible: true,
      proceduralRigVisible: false,
    });
    expect(playing.actors[0]?.actionTimeS).toBeGreaterThan(0);

    expect(pipeline.debugForceLod(2, variantId, 1)).toBe(target.uid);
    pipeline.update(0.1);
    expect(pipeline.debugSnapshot().actors[0]).toMatchObject({ lodIndex: 2, visibleLods: [2] });

    // Preserve the exact audited actor across an LOD sequence even if another
    // same-variant bot moves into a better screenshot position between calls.
    const sameVariantTarget = new FakeTarget(target.uid + 6, target.team);
    sameVariantTarget.group.position.set(0, 0, -4);
    scene.add(sameVariantTarget.group);
    pipeline.register(sameVariantTarget);
    expect(enemyVariantFor(sameVariantTarget.uid, sameVariantTarget.team)).toBe(variantId);
    target.group.position.set(50, 0, 5);
    expect(pipeline.debugForceLod(1, variantId, 1)).toBe(target.uid);

    pipeline.dispose();
    expect(target.external).toBeNull();
    expect(sameVariantTarget.external).toBeNull();
    expect(sourceGeometryDispose).toHaveBeenCalledOnce();
    expect(sourceMaterialDispose).toHaveBeenCalledOnce();
    expect(sourceSkeletonDispose).toHaveBeenCalledOnce();
    expect(actorSkeletonDispose).toHaveBeenCalledOnce();
    expect(runtimeMocks.dispose).toHaveBeenCalledOnce();
  });

  it('rejects a primitive tagged as a different nested variant instead of mixing uniforms', async () => {
    stubManifest();
    const invalid = makeGroupedSource(0);
    const rifleman = invalid.children.find((child) => child.userData.variantId === 'rifleman');
    const primitive = rifleman?.children.find(
      (child): child is THREE.SkinnedMesh => child instanceof THREE.SkinnedMesh,
    );
    if (!primitive) throw new Error('grouped invalid fixture is incomplete');
    primitive.userData.variantId = 'support';
    runtimeMocks.loadScene.mockResolvedValueOnce(invalid);
    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera();
    scene.add(camera);
    const target = new FakeTarget(5, 1);
    const pipeline = new EnemyAssetPipeline(scene, renderer, camera);
    pipeline.register(target);

    const report = await pipeline.load({ manifestUrl: '/assets/aaa/enemies/manifest.json' });

    expect(report.ready).toBe(false);
    expect(report.errors[0]).toMatch(/support variant root/);
    expect(target.external).toBeNull();
    expect(target.proceduralVisible).toBe(true);
    expect(renderer.compileAsync).not.toHaveBeenCalled();
    pipeline.dispose();
  });

  it('does not commit external rigs when both async and sync shader compile fail', async () => {
    stubManifest();
    runtimeMocks.loadScene
      .mockResolvedValueOnce(makeSource(0))
      .mockResolvedValueOnce(makeSource(1))
      .mockResolvedValueOnce(makeSource(2));
    const renderer = {
      compileAsync: vi.fn(async () => { throw new Error('parallel compile failed'); }),
      compile: vi.fn(() => { throw new Error('sync compile failed'); }),
    } as unknown as THREE.WebGLRenderer;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera();
    scene.add(camera);
    const target = new FakeTarget(0, 1);
    const pipeline = new EnemyAssetPipeline(scene, renderer, camera);
    pipeline.register(target);

    const report = await pipeline.load({ manifestUrl: '/assets/aaa/enemies/manifest.json' });

    expect(report.ready).toBe(false);
    expect(report.errors[0]).toContain('sync compile failed');
    expect(target.external).toBeNull();
    expect(target.proceduralVisible).toBe(true);
    expect(runtimeMocks.dispose).toHaveBeenCalledOnce();
    pipeline.dispose();
  });
});
