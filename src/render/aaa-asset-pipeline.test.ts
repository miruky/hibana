import { afterEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import {
  AaaStageAssetPipeline,
  isProceduralDistantWorldFallback,
  parseAaaAssetManifest,
  tuneImportedStageMaterial,
} from './aaa-asset-pipeline';

const gltfRuntimeMocks = vi.hoisted(() => ({
  loadScene: vi.fn(),
  clone: vi.fn(),
  dispose: vi.fn(),
}));

vi.mock('./gltf-runtime.js', () => ({
  createGltfRuntime: vi.fn(() => gltfRuntimeMocks),
}));

const TEST_GENERATOR = {
  generatorVersion: 'test-dense-world-v1',
  generatorSha: 'a'.repeat(64),
} as const;
const TEST_CANONICAL_PROVENANCE = {
  placementSource: 'canonical-solver-v2-authoring',
  placementSolverSha256: 'b'.repeat(64),
  stageWorldCatalogSha256: 'c'.repeat(64),
  stageLayoutSha256: 'd'.repeat(64),
} as const;
const TEST_LEGACY_PROVENANCE = {
  ...TEST_CANONICAL_PROVENANCE,
  placementSource: 'runtime-release',
} as const;
const TEST_STAGE_ENTRY_PROVENANCE = {
  stages: ['test'],
  stageProvenance: TEST_CANONICAL_PROVENANCE,
} as const;
const TEST_NODE_PROVENANCE = {
  hibanaStage: 'test',
  hibanaPlacementSource: TEST_CANONICAL_PROVENANCE.placementSource,
  hibanaPlacementSolverSha256: TEST_CANONICAL_PROVENANCE.placementSolverSha256,
  hibanaStageWorldCatalogSha256: TEST_CANONICAL_PROVENANCE.stageWorldCatalogSha256,
  hibanaStageLayoutSha256: TEST_CANONICAL_PROVENANCE.stageLayoutSha256,
  hibanaGeneratorVersion: TEST_GENERATOR.generatorVersion,
  hibanaGeneratorSha: TEST_GENERATOR.generatorSha,
} as const;

function markStageSourceProvenance(
  source: THREE.Object3D,
  overrides: Readonly<Record<string, unknown>> = {},
): void {
  for (const child of source.children) {
    child.traverse((node) => Object.assign(node.userData, TEST_NODE_PROVENANCE, overrides));
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

interface StageSourceFixture {
  readonly root: THREE.Group;
  readonly geometry: THREE.BufferGeometry;
  readonly material: THREE.MeshStandardMaterial;
  readonly texture: THREE.Texture;
  readonly skeleton: THREE.Skeleton;
}

function createStageSource(texture?: THREE.Texture): StageSourceFixture {
  const resolvedTexture = texture ?? new THREE.DataTexture(new Uint8Array([255, 128, 64, 255]), 1, 1);
  // 同じtextureを2スロットに紐付け、material内の重複もdispose 1回をピンする。
  const material = new THREE.MeshStandardMaterial({ map: resolvedTexture, normalMap: resolvedTexture });
  const geometry = new THREE.BoxGeometry(1, 2, 1);
  const skeleton = new THREE.Skeleton([]);
  const mesh = new THREE.SkinnedMesh(geometry, material);
  mesh.bind(skeleton);
  const root = new THREE.Group();
  root.add(mesh);
  markStageSourceProvenance(root);
  return { root, geometry, material, texture: resolvedTexture, skeleton };
}

function cloneStageSource(source: StageSourceFixture): THREE.Object3D {
  // SkeletonUtilsと同じくgeometry/material/textureを共有するclone。このfixtureでは
  // skeletonも意図的に共有し、unique解放ledgerの二重dispose防止を検証する。
  const mesh = new THREE.SkinnedMesh(source.geometry, source.material);
  mesh.bind(source.skeleton);
  const root = new THREE.Group();
  root.add(mesh);
  return root;
}

function successfulRenderer(): THREE.WebGLRenderer {
  return {
    compileAsync: vi.fn(async () => undefined),
    compile: vi.fn(),
  } as unknown as THREE.WebGLRenderer;
}

describe('AAA asset manifest', () => {
  it('安全な相対URL・LOD・instanceを正規化する', () => {
    const manifest = parseAaaAssetManifest({
      version: 1,
      ...TEST_GENERATOR,
      ktx2TranscoderPath: 'transcoders/basis',
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'hero-crate',
        url: 'props/hero-crate.glb',
        minTier: 'high',
        replacesDistantMatte: true,
        replacesProceduralProps: true,
        replacesProceduralStageShell: true,
        instances: [{ position: [1, 0, 2], rotation: [0, 1, 0], scale: 1.2 }],
        lods: [{ url: 'props/hero-crate-lod1.glb', distance: 28 }],
      }],
    });
    expect(manifest.ktx2TranscoderPath).toBe('transcoders/basis/');
    expect(manifest.assets[0]?.lods?.[0]?.distance).toBe(28);
    expect(manifest.assets[0]?.replacesDistantMatte).toBe(true);
    expect(manifest.assets[0]?.replacesProceduralProps).toBe(true);
    expect(manifest.assets[0]?.replacesProceduralStageShell).toBe(true);
    expect(manifest.assets[0]?.stageProvenance).toEqual(TEST_CANONICAL_PROVENANCE);
    expect(manifest.generatorSha).toBe(TEST_GENERATOR.generatorSha);
  });

  it('stage provenanceの欠損SHA形式をmanifest parseで拒否する', () => {
    expect(() => parseAaaAssetManifest({
      version: 1,
      assets: [{
        id: 'invalid-provenance',
        url: 'stages/test.glb',
        stageProvenance: {
          ...TEST_CANONICAL_PROVENANCE,
          placementSolverSha256: 'not-a-sha',
        },
      }],
    })).toThrow(/placementSolverSha256/);
  });

  it('replacement provenanceはstage固有layoutまたはasset SHAを必須とする', () => {
    const { stageLayoutSha256: _ignored, ...globalOnly } = TEST_CANONICAL_PROVENANCE;
    expect(() => parseAaaAssetManifest({
      version: 1,
      assets: [{
        id: 'missing-stage-identity',
        url: 'stages/test.glb',
        stageProvenance: globalOnly,
      }],
    })).toThrow(/requires stageLayoutSha256 or assetSha256/);
  });

  it('遠景置換フラグはboolean以外を拒否する', () => {
    expect(() => parseAaaAssetManifest({
      version: 1,
      assets: [{ id: 'bad-flag', url: 'stage.glb', replacesDistantMatte: 'yes' }],
    })).toThrow(/replacesDistantMatte/);
  });

  it('プロシージャルプロップ置換フラグはboolean以外を拒否する', () => {
    expect(() => parseAaaAssetManifest({
      version: 1,
      assets: [{ id: 'bad-prop-flag', url: 'stage.glb', replacesProceduralProps: 1 }],
    })).toThrow(/replacesProceduralProps/);
  });

  it('プロシージャルステージ外殻置換フラグはboolean以外を拒否する', () => {
    expect(() => parseAaaAssetManifest({
      version: 1,
      assets: [{
        id: 'bad-stage-shell-flag',
        url: 'stage.glb',
        replacesProceduralStageShell: 'yes',
      }],
    })).toThrow(/replacesProceduralStageShell/);
  });

  it.each([
    'https://example.com/model.glb',
    '../private/model.glb',
    '/absolute/model.glb',
    'data:model/gltf-binary;base64,AAAA',
    'stages/model.glb?stale-version',
  ])('外部・親参照・absolute URLを拒否する: %s', (url) => {
    expect(() => parseAaaAssetManifest({
      version: 1,
      assets: [{ id: 'bad', url }],
    })).toThrow();
  });

  it('LOD距離の重複・逆順を拒否する', () => {
    expect(() => parseAaaAssetManifest({
      version: 1,
      assets: [{
        id: 'bad-lod-order',
        url: 'stage-lod0.glb',
        lods: [
          { url: 'stage-lod1.glb', distance: 100 },
          { url: 'stage-lod2.glb', distance: 100 },
        ],
      }],
    })).toThrow(/strictly increasing/);
  });

  it('asset 0件ならThree loader chunkを要求せずfail-openする', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ version: 1, assets: [] }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    })));
    const scene = new THREE.Scene();
    const pipeline = new AaaStageAssetPipeline(
      scene,
      {} as THREE.WebGLRenderer,
      new THREE.PerspectiveCamera(),
    );
    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      manifestUrl: '/manifest.json',
    });
    expect(report).toEqual({ requested: 0, loaded: 0, failed: 0, errors: [] });
    expect(scene.getObjectByName('aaa:external-stage-assets')).toBe(pipeline.root);
    expect(pipeline.hasProceduralPropReplacement).toBe(false);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    pipeline.dispose();
    expect(scene.getObjectByName('aaa:external-stage-assets')).toBeUndefined();
  });

  it('low tierはmanifestもGLBも要求せずプロシージャル表示へ固定する', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const pipeline = new AaaStageAssetPipeline(
      scene,
      {} as THREE.WebGLRenderer,
      new THREE.PerspectiveCamera(),
    );

    const loading = pipeline.load({
      stageId: 'test',
      tier: 'low',
      propPlacements: [],
      manifestUrl: '/manifest.json',
    });
    const repeatedAtHighTier = pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      manifestUrl: '/manifest.json',
    });
    expect(repeatedAtHighTier).toBe(loading);
    const report = await loading;

    expect(report).toEqual({ requested: 0, loaded: 0, failed: 0, errors: [] });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(gltfRuntimeMocks.loadScene).not.toHaveBeenCalled();
    expect(pipeline.root.visible).toBe(false);
    expect(pipeline.hasDistantWorldReplacement).toBe(false);
    expect(pipeline.hasProceduralPropReplacement).toBe(false);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    expect(fallback.visible).toBe(true);
    pipeline.dispose();
    expect(fallback.visible).toBe(true);
  });

  it('canonical candidateをlegacy runtime layoutへは接続せずGLB通信前にfail-openする', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'canonical-stage',
        url: 'stages/test-lod0.glb',
        replacesProceduralStageShell: true,
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const pipeline = new AaaStageAssetPipeline(
      scene,
      successfulRenderer(),
      new THREE.PerspectiveCamera(),
    );

    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_LEGACY_PROVENANCE,
      manifestUrl: '/manifest.json',
    });

    expect(report).toEqual({
      requested: 1,
      loaded: 0,
      failed: 1,
      errors: [
        'canonical-stage: manifest stageProvenance.placementSource does not match the active layout',
      ],
    });
    expect(gltfRuntimeMocks.loadScene).not.toHaveBeenCalled();
    expect(pipeline.root.visible).toBe(false);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    expect(fallback.visible).toBe(true);
    pipeline.dispose();
  });

  it('全体placement SHAしか無い旧manifestはstage replacement候補を許可しない', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      ...TEST_CANONICAL_PROVENANCE,
      assets: [{
        id: 'global-only-stage',
        url: 'stages/test-lod0.glb',
        stages: ['test'],
        replacesDistantMatte: true,
        replacesProceduralStageShell: true,
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const pipeline = new AaaStageAssetPipeline(
      scene,
      successfulRenderer(),
      new THREE.PerspectiveCamera(),
    );

    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    });

    expect(report.errors).toEqual(['global-only-stage: manifest stageProvenance is missing']);
    expect(report).toMatchObject({ requested: 1, loaded: 0, failed: 1 });
    expect(gltfRuntimeMocks.loadScene).not.toHaveBeenCalled();
    expect(pipeline.root.visible).toBe(false);
    expect(fallback.visible).toBe(true);
    pipeline.dispose();
  });

  it('同一stageの置換entryが複数あれば一部成功させず全体をfail-openする', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: ['shell-a', 'shell-b'].map((id) => ({
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id,
        url: `stages/${id}.glb`,
        replacesProceduralStageShell: true,
        instances: [{ position: [0, 0, 0] }],
      })),
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const pipeline = new AaaStageAssetPipeline(
      scene,
      successfulRenderer(),
      new THREE.PerspectiveCamera(),
    );

    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    });

    expect(report).toEqual({
      requested: 2,
      loaded: 0,
      failed: 2,
      errors: ['active stage replacement entry count must be exactly 1 (got 2)'],
    });
    expect(gltfRuntimeMocks.loadScene).not.toHaveBeenCalled();
    expect(pipeline.root.visible).toBe(false);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    expect(fallback.visible).toBe(true);
    pipeline.dispose();
  });

  it('manifestとlayoutが合ってもGLB node extrasのSHA不一致は置換をrollbackする', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'stale-cached-stage',
        url: 'stages/test-lod0.glb',
        replacesDistantMatte: true,
        replacesProceduralStageShell: true,
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const imported = createStageSource();
    markStageSourceProvenance(imported.root, {
      hibanaPlacementSolverSha256: 'd'.repeat(64),
    });
    gltfRuntimeMocks.loadScene.mockResolvedValue(imported.root);
    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const renderer = successfulRenderer();
    const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());

    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    });

    expect(report.errors[0]).toContain('hibanaPlacementSolverSha256 provenance mismatch');
    expect(report).toMatchObject({ requested: 1, loaded: 0, failed: 1 });
    expect(gltfRuntimeMocks.clone).not.toHaveBeenCalled();
    expect(renderer.compileAsync).not.toHaveBeenCalled();
    expect(pipeline.root.visible).toBe(false);
    expect(pipeline.hasDistantWorldReplacement).toBe(false);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    expect(fallback.visible).toBe(true);
    pipeline.dispose();
  });

  it.each([
    { tier: 'high', expectedUrl: 'stages/test-lod0.glb', selectedIndex: 0 },
    { tier: 'medium', expectedUrl: 'stages/test-lod1.glb', selectedIndex: 1 },
  ] as const)(
    '巨大stageは$tier tierで必要な1 LODだけを通信・表示・解放する',
    async ({ tier, expectedUrl, selectedIndex }) => {
      const fetchMock = vi.fn(async () => new Response(JSON.stringify({
        version: 1,
        ...TEST_GENERATOR,
        assets: [{
          ...TEST_STAGE_ENTRY_PROVENANCE,
          id: 'tiered-stage-world',
          url: 'stages/test-lod0.glb',
          minTier: 'medium',
          replacesDistantMatte: true,
          replacesProceduralProps: true,
          replacesProceduralStageShell: true,
          instances: [{ position: [0, 0, 0] }],
          lods: [
            { url: 'stages/test-lod1.glb', distance: 260 },
            { url: 'stages/test-lod2.glb', distance: 460 },
          ],
        }],
      }), { status: 200, headers: { 'content-type': 'application/json' } }));
      vi.stubGlobal('fetch', fetchMock);
      const sourceUrls = [
        'stages/test-lod0.glb',
        'stages/test-lod1.glb',
        'stages/test-lod2.glb',
      ];
      const sources = sourceUrls.map((url) => {
        const source = createStageSource();
        source.root.name = `fixture:${url}`;
        return source;
      });
      const disposeSpies = sources.map((source) => ({
        geometry: vi.spyOn(source.geometry, 'dispose'),
        material: vi.spyOn(source.material, 'dispose'),
        texture: vi.spyOn(source.texture, 'dispose'),
        skeleton: vi.spyOn(source.skeleton, 'dispose'),
      }));
      gltfRuntimeMocks.loadScene.mockImplementation((url: string) => {
        const sourceIndex = sourceUrls.findIndex((sourceUrl) => url.includes(sourceUrl));
        if (sourceIndex < 0) return Promise.reject(new Error(`unexpected URL: ${url}`));
        return Promise.resolve(sources[sourceIndex]!.root);
      });
      gltfRuntimeMocks.clone.mockImplementation((source: THREE.Object3D) => source.clone(true));

      const scene = new THREE.Scene();
      const fallback = new THREE.Group();
      fallback.userData.proceduralDistantWorldFallback = true;
      scene.add(fallback);
      const renderer = successfulRenderer();
      const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());

      const report = await pipeline.load({
        stageId: 'test',
        tier,
        propPlacements: [],
        placementProvenance: TEST_CANONICAL_PROVENANCE,
        manifestUrl: '/manifest.json',
      });

      expect(report).toEqual({ requested: 1, loaded: 1, failed: 0, errors: [] });
      expect(fetchMock).toHaveBeenCalledOnce();
      expect(fetchMock).toHaveBeenCalledWith(
        '/manifest.json',
        expect.objectContaining({ cache: 'no-cache' }),
      );
      expect(gltfRuntimeMocks.loadScene).toHaveBeenCalledOnce();
      expect(gltfRuntimeMocks.loadScene.mock.calls[0]?.[0]).toBe(
        `${import.meta.env.BASE_URL}assets/aaa/${expectedUrl}?v=${TEST_CANONICAL_PROVENANCE.stageLayoutSha256}-${TEST_GENERATOR.generatorSha}`,
      );
      expect(renderer.compileAsync).toHaveBeenCalledOnce();
      expect(pipeline.root.visible).toBe(true);
      expect(pipeline.root.children).toHaveLength(1);
      const holder = pipeline.root.children[0];
      expect(holder).toBeInstanceOf(THREE.Group);
      expect(holder).not.toBeInstanceOf(THREE.LOD);
      expect(holder?.children[0]?.name).toBe(`fixture:${expectedUrl}`);
      expect(fallback.visible).toBe(false);
      expect(pipeline.hasDistantWorldReplacement).toBe(true);
      expect(pipeline.hasProceduralPropReplacement).toBe(true);
      expect(pipeline.hasProceduralStageShellReplacement).toBe(true);

      pipeline.dispose();

      expect(scene.getObjectByName('aaa:external-stage-assets')).toBeUndefined();
      expect(pipeline.root.children).toHaveLength(0);
      expect(fallback.visible).toBe(true);
      expect(sources[selectedIndex]?.root.children).toHaveLength(0);
      for (const [index, spies] of disposeSpies.entries()) {
        const expectedCalls = index === selectedIndex ? 1 : 0;
        expect(spies.geometry).toHaveBeenCalledTimes(expectedCalls);
        expect(spies.material).toHaveBeenCalledTimes(expectedCalls);
        expect(spies.texture).toHaveBeenCalledTimes(expectedCalls);
        expect(spies.skeleton).toHaveBeenCalledTimes(expectedCalls);
      }
      expect(gltfRuntimeMocks.dispose).toHaveBeenCalledOnce();
    },
  );

  it('medium stageにLOD1が無ければLOD0へ品質契約を崩さずfail-openする', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'missing-medium-stage-world',
        url: 'stages/lod0-only.glb',
        replacesDistantMatte: true,
        replacesProceduralStageShell: true,
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);
    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const renderer = successfulRenderer();
    const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());

    const report = await pipeline.load({
      stageId: 'test',
      tier: 'medium',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    });

    expect(report).toEqual({
      requested: 1,
      loaded: 0,
      failed: 1,
      errors: ['missing-medium-stage-world: monolithic stage requires LOD1 for medium tier'],
    });
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(gltfRuntimeMocks.loadScene).not.toHaveBeenCalled();
    expect(renderer.compileAsync).not.toHaveBeenCalled();
    expect(pipeline.root.visible).toBe(false);
    expect(pipeline.root.children).toHaveLength(0);
    expect(fallback.visible).toBe(true);
    expect(pipeline.hasDistantWorldReplacement).toBe(false);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    pipeline.dispose();
  });

  it('実3D遠景のcompile成功後だけ旧3D fallbackとlegacy matteを隠し、disposeで復元する', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'stage-world',
        url: 'stages/test-lod0.glb',
        replacesDistantMatte: true,
        replacesProceduralStageShell: true,
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));

    const imported = new THREE.Group();
    // GLB内部の名前が旧fallbackと一致しても、pipeline root配下は置換対象外。
    imported.name = 'aaa:distant-world';
    imported.add(new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), new THREE.MeshStandardMaterial()));
    markStageSourceProvenance(imported);
    gltfRuntimeMocks.loadScene.mockResolvedValue(imported);
    gltfRuntimeMocks.clone.mockImplementation((source: THREE.Object3D) => source.clone(true));

    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.name = 'aaa:distant-world';
    fallback.userData.proceduralDistantWorldFallback = true;
    const legacyMatte = new THREE.Group();
    legacyMatte.name = 'aaa:distant-stage-matte-root';
    const unrelated = new THREE.Group();
    unrelated.name = 'aaa:perimeter-street-infrastructure';
    scene.add(fallback, legacyMatte, unrelated);

    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());
    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    });

    expect(report).toEqual({ requested: 1, loaded: 1, failed: 0, errors: [] });
    expect(renderer.compileAsync).toHaveBeenCalledOnce();
    expect(pipeline.hasDistantWorldReplacement).toBe(true);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(true);
    expect(pipeline.root.visible).toBe(true);
    expect(fallback.visible).toBe(false);
    expect(legacyMatte.visible).toBe(false);
    expect(unrelated.visible).toBe(true);
    expect(pipeline.root.getObjectByName('aaa:distant-world')?.visible).toBe(true);

    pipeline.dispose();
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    expect(fallback.visible).toBe(true);
    expect(legacyMatte.visible).toBe(true);
  });

  it('汎用asset LODはhysteresis付きで近・中・遠の1 levelだけを表示する', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      assets: [{
        id: 'lod-stage-world',
        url: 'stages/lod0.glb',
        instances: [{ position: [0, 0, 0] }],
        lods: [
          { url: 'stages/lod1.glb', distance: 10 },
          { url: 'stages/lod2.glb', distance: 20 },
        ],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const sources = [new THREE.Group(), new THREE.Group(), new THREE.Group()];
    gltfRuntimeMocks.loadScene
      .mockResolvedValueOnce(sources[0])
      .mockResolvedValueOnce(sources[1])
      .mockResolvedValueOnce(sources[2]);
    gltfRuntimeMocks.clone.mockImplementation((source: THREE.Object3D) => source.clone(true));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera();
    scene.add(camera);
    const pipeline = new AaaStageAssetPipeline(scene, successfulRenderer(), camera);

    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      manifestUrl: '/manifest.json',
    });
    const holder = pipeline.root.children[0];
    if (!(holder instanceof THREE.LOD)) throw new Error('expected a THREE.LOD holder');

    expect(report).toEqual({ requested: 1, loaded: 1, failed: 0, errors: [] });
    expect(holder.levels.map((level) => level.hysteresis)).toEqual([0.1, 0.1, 0.1]);
    for (const [distance, expectedLevel] of [[0, 0], [15, 1], [30, 2]] as const) {
      camera.position.set(distance, 0, 0);
      camera.updateMatrixWorld(true);
      holder.updateMatrixWorld(true);
      holder.update(camera);
      expect(holder.levels.map((level) => level.object.visible)).toEqual(
        [0, 1, 2].map((level) => level === expectedLevel),
      );
    }
    pipeline.dispose();
  });

  it('cache共有のsource・cloneをrootと共に消去し、各resourceを一度だけdisposeする', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      assets: [
        {
          id: 'shared-stage-a',
          url: 'stages/shared.glb',
          instances: [{ position: [0, 0, 0] }],
        },
        {
          id: 'shared-stage-b',
          url: 'stages/shared.glb',
          instances: [{ position: [4, 0, 0] }],
        },
      ],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    class FakeImageBitmap {
      readonly close = vi.fn();
    }
    vi.stubGlobal('ImageBitmap', FakeImageBitmap);
    const source = createStageSource();
    const imageBitmap = new FakeImageBitmap();
    (source.texture.source as unknown as { data: unknown }).data = imageBitmap;
    const geometryDispose = vi.spyOn(source.geometry, 'dispose');
    const materialDispose = vi.spyOn(source.material, 'dispose');
    const textureDispose = vi.spyOn(source.texture, 'dispose');
    const skeletonDispose = vi.spyOn(source.skeleton, 'dispose');
    gltfRuntimeMocks.loadScene.mockResolvedValue(source.root);
    gltfRuntimeMocks.clone.mockImplementation(() => cloneStageSource(source));

    const scene = new THREE.Scene();
    const pipeline = new AaaStageAssetPipeline(scene, successfulRenderer(), new THREE.PerspectiveCamera());
    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      manifestUrl: '/manifest.json',
    });

    expect(report).toEqual({ requested: 2, loaded: 2, failed: 0, errors: [] });
    expect(gltfRuntimeMocks.loadScene).toHaveBeenCalledOnce();
    expect(pipeline.root.children).toHaveLength(2);
    expect(source.root.children).toHaveLength(1);
    expect(gltfRuntimeMocks.dispose).toHaveBeenCalledOnce();

    pipeline.dispose();
    pipeline.dispose();

    expect(pipeline.root.children).toHaveLength(0);
    expect(source.root.children).toHaveLength(0);
    expect(geometryDispose).toHaveBeenCalledOnce();
    expect(materialDispose).toHaveBeenCalledOnce();
    expect(textureDispose).toHaveBeenCalledOnce();
    expect(imageBitmap.close).toHaveBeenCalledOnce();
    expect(skeletonDispose).toHaveBeenCalledOnce();
  });

  it('LODのpartial load失敗をfail-openし、先行・遅延sourceと共有textureを回収する', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'partial-stage-world',
        url: 'stages/partial-lod0.glb',
        replacesDistantMatte: true,
        instances: [{ position: [0, 0, 0] }],
        lods: [
          { url: 'stages/missing-lod1.glb', distance: 100 },
          { url: 'stages/late-lod2.glb', distance: 200 },
        ],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const sharedTexture = new THREE.DataTexture(new Uint8Array([64, 128, 255, 255]), 1, 1);
    const primary = createStageSource(sharedTexture);
    const late = createStageSource(sharedTexture);
    const primaryGeometryDispose = vi.spyOn(primary.geometry, 'dispose');
    const primaryMaterialDispose = vi.spyOn(primary.material, 'dispose');
    const primarySkeletonDispose = vi.spyOn(primary.skeleton, 'dispose');
    const lateGeometryDispose = vi.spyOn(late.geometry, 'dispose');
    const lateMaterialDispose = vi.spyOn(late.material, 'dispose');
    const lateSkeletonDispose = vi.spyOn(late.skeleton, 'dispose');
    const textureDispose = vi.spyOn(sharedTexture, 'dispose');
    let resolveLate: ((source: THREE.Object3D) => void) | undefined;
    const latePromise = new Promise<THREE.Object3D>((resolve) => { resolveLate = resolve; });
    gltfRuntimeMocks.loadScene.mockImplementation((url: string) => {
      if (url.includes('partial-lod0.glb')) return Promise.resolve(primary.root);
      if (url.includes('missing-lod1.glb')) return Promise.reject(new Error('missing LOD1'));
      return latePromise;
    });

    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const renderer = successfulRenderer();
    const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());
    const loading = pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    });
    await vi.waitFor(() => expect(gltfRuntimeMocks.loadScene).toHaveBeenCalledTimes(3));
    resolveLate?.(late.root);
    const report = await loading;

    expect(report.loaded).toBe(0);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('missing LOD1');
    expect(pipeline.root.children).toHaveLength(0);
    expect(primary.root.children).toHaveLength(0);
    expect(late.root.children).toHaveLength(0);
    expect(fallback.visible).toBe(true);
    expect(renderer.compileAsync).not.toHaveBeenCalled();
    expect(primaryGeometryDispose).toHaveBeenCalledOnce();
    expect(primaryMaterialDispose).toHaveBeenCalledOnce();
    expect(primarySkeletonDispose).toHaveBeenCalledOnce();
    expect(lateGeometryDispose).toHaveBeenCalledOnce();
    expect(lateMaterialDispose).toHaveBeenCalledOnce();
    expect(lateSkeletonDispose).toHaveBeenCalledOnce();
    expect(textureDispose).toHaveBeenCalledOnce();
    expect(gltfRuntimeMocks.dispose).toHaveBeenCalledOnce();

    pipeline.dispose();
    expect(textureDispose).toHaveBeenCalledOnce();
  });

  it('複数instanceの途中clone失敗をentry単位でrollbackし、並行loadもsingle-flight化する', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'atomic-stage-world',
        url: 'stages/atomic.glb',
        replacesDistantMatte: true,
        replacesProceduralProps: true,
        replacesProceduralStageShell: true,
        instances: [
          { position: [0, 0, 0] },
          { position: [10, 0, 0] },
        ],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);
    const source = createStageSource();
    const geometryDispose = vi.spyOn(source.geometry, 'dispose');
    const materialDispose = vi.spyOn(source.material, 'dispose');
    const textureDispose = vi.spyOn(source.texture, 'dispose');
    const skeletonDispose = vi.spyOn(source.skeleton, 'dispose');
    gltfRuntimeMocks.loadScene.mockResolvedValue(source.root);
    gltfRuntimeMocks.clone
      .mockImplementationOnce(() => cloneStageSource(source))
      .mockImplementationOnce(() => { throw new Error('second clone failed'); });

    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const renderer = successfulRenderer();
    const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());
    const options = {
      stageId: 'test',
      tier: 'high' as const,
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    };

    const first = pipeline.load(options);
    const second = pipeline.load(options);
    expect(second).toBe(first);
    const report = await first;

    expect(report).toEqual({
      requested: 2,
      loaded: 0,
      failed: 2,
      errors: ['atomic-stage-world: second clone failed'],
    });
    expect(report.requested).toBe(report.loaded + report.failed);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(gltfRuntimeMocks.loadScene).toHaveBeenCalledOnce();
    expect(renderer.compileAsync).not.toHaveBeenCalled();
    expect(pipeline.root.children).toHaveLength(0);
    expect(pipeline.root.visible).toBe(false);
    expect(fallback.visible).toBe(true);
    expect(pipeline.hasDistantWorldReplacement).toBe(false);
    expect(pipeline.hasProceduralPropReplacement).toBe(false);
    expect(pipeline.hasProceduralStageShellReplacement).toBe(false);
    expect(geometryDispose).toHaveBeenCalledOnce();
    expect(materialDispose).toHaveBeenCalledOnce();
    expect(textureDispose).toHaveBeenCalledOnce();
    expect(skeletonDispose).toHaveBeenCalledOnce();
    expect(gltfRuntimeMocks.dispose).toHaveBeenCalledOnce();
    pipeline.dispose();
  });

  it('dispose後に遅れてresolveしたGLB sourceをrootへ戻さず一度だけ回収する', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      assets: [{
        id: 'late-stage-world',
        url: 'stages/late.glb',
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const source = createStageSource();
    const geometryDispose = vi.spyOn(source.geometry, 'dispose');
    const materialDispose = vi.spyOn(source.material, 'dispose');
    const textureDispose = vi.spyOn(source.texture, 'dispose');
    const skeletonDispose = vi.spyOn(source.skeleton, 'dispose');
    let resolveSource: ((source: THREE.Object3D) => void) | undefined;
    gltfRuntimeMocks.loadScene.mockImplementation(() => new Promise<THREE.Object3D>((resolve) => {
      resolveSource = resolve;
    }));

    const scene = new THREE.Scene();
    const pipeline = new AaaStageAssetPipeline(scene, successfulRenderer(), new THREE.PerspectiveCamera());
    const loading = pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      manifestUrl: '/manifest.json',
    });
    await vi.waitFor(() => expect(gltfRuntimeMocks.loadScene).toHaveBeenCalledOnce());
    pipeline.dispose();
    resolveSource?.(source.root);
    const report = await loading;

    expect(report.loaded).toBe(0);
    expect(report.errors).toEqual([]);
    expect(scene.getObjectByName('aaa:external-stage-assets')).toBeUndefined();
    expect(pipeline.root.children).toHaveLength(0);
    expect(source.root.children).toHaveLength(0);
    expect(geometryDispose).toHaveBeenCalledOnce();
    expect(materialDispose).toHaveBeenCalledOnce();
    expect(textureDispose).toHaveBeenCalledOnce();
    expect(skeletonDispose).toHaveBeenCalledOnce();
    expect(gltfRuntimeMocks.dispose).toHaveBeenCalledOnce();
  });

  it('GLB読込失敗時は軽量3D fallbackを表示したままfail-openする', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'broken-stage-world',
        url: 'stages/missing.glb',
        replacesDistantMatte: true,
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    gltfRuntimeMocks.loadScene.mockRejectedValue(new Error('missing GLB'));

    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.name = 'aaa:distant-world';
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const renderer = {
      compileAsync: vi.fn(async () => undefined),
      compile: vi.fn(),
    } as unknown as THREE.WebGLRenderer;
    const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());
    const report = await pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    });

    expect(report.loaded).toBe(0);
    expect(report.failed).toBe(1);
    expect(report.errors[0]).toContain('missing GLB');
    expect(pipeline.hasDistantWorldReplacement).toBe(false);
    expect(pipeline.root.visible).toBe(false);
    expect(fallback.visible).toBe(true);
    expect(renderer.compileAsync).not.toHaveBeenCalled();
    pipeline.dispose();
  });

  it('GLBをcloneできてもshader compile失敗なら置換をcommitしない', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      version: 1,
      ...TEST_GENERATOR,
      assets: [{
        ...TEST_STAGE_ENTRY_PROVENANCE,
        id: 'uncompilable-stage-world',
        url: 'stages/uncompilable.glb',
        replacesDistantMatte: true,
        instances: [{ position: [0, 0, 0] }],
      }],
    }), { status: 200, headers: { 'content-type': 'application/json' } })));
    const imported = createStageSource();
    const geometryDispose = vi.spyOn(imported.geometry, 'dispose');
    const materialDispose = vi.spyOn(imported.material, 'dispose');
    const textureDispose = vi.spyOn(imported.texture, 'dispose');
    const skeletonDispose = vi.spyOn(imported.skeleton, 'dispose');
    gltfRuntimeMocks.loadScene.mockResolvedValue(imported.root);
    gltfRuntimeMocks.clone.mockImplementation(() => cloneStageSource(imported));

    const scene = new THREE.Scene();
    const fallback = new THREE.Group();
    fallback.name = 'aaa:distant-world';
    fallback.userData.proceduralDistantWorldFallback = true;
    scene.add(fallback);
    const compileError = new Error('shader compile failed');
    const renderer = {
      compileAsync: vi.fn(async () => { throw compileError; }),
      compile: vi.fn(() => { throw compileError; }),
    } as unknown as THREE.WebGLRenderer;
    const pipeline = new AaaStageAssetPipeline(scene, renderer, new THREE.PerspectiveCamera());

    await expect(pipeline.load({
      stageId: 'test',
      tier: 'high',
      propPlacements: [],
      placementProvenance: TEST_CANONICAL_PROVENANCE,
      manifestUrl: '/manifest.json',
    })).rejects.toThrow('shader compile failed');
    expect(pipeline.hasDistantWorldReplacement).toBe(false);
    expect(pipeline.root.visible).toBe(false);
    expect(pipeline.root.children).toHaveLength(0);
    expect(imported.root.children).toHaveLength(0);
    expect(fallback.visible).toBe(true);
    expect(gltfRuntimeMocks.dispose).toHaveBeenCalledOnce();
    expect(geometryDispose).toHaveBeenCalledOnce();
    expect(materialDispose).toHaveBeenCalledOnce();
    expect(textureDispose).toHaveBeenCalledOnce();
    expect(skeletonDispose).toHaveBeenCalledOnce();
    pipeline.dispose();
    expect(textureDispose).toHaveBeenCalledOnce();
  });

  it('旧名とuserData契約のどちらでも遠景fallbackを識別する', () => {
    const tagged = new THREE.Group();
    tagged.userData.proceduralDistantWorldFallback = true;
    const legacy = new THREE.Group();
    legacy.name = 'aaa:distant-stage-matte-root';
    const streetLights = new THREE.Group();
    streetLights.name = 'aaa:perimeter-street-infrastructure';

    expect(isProceduralDistantWorldFallback(tagged)).toBe(true);
    expect(isProceduralDistantWorldFallback(legacy)).toBe(true);
    expect(isProceduralDistantWorldFallback(streetLights)).toBe(false);
  });
});

describe('Blender stage PBR material tuning', () => {
  it('水面を追加反射パス無しの透明PBRに正規化する', () => {
    const normal = new THREE.DataTexture(new Uint8Array([128, 128, 255, 255]), 1, 1);
    const roughness = new THREE.DataTexture(new Uint8Array([32, 32, 32, 255]), 1, 1);
    const material = new THREE.MeshStandardMaterial({ normalMap: normal, roughnessMap: roughness });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), material);
    mesh.userData.hibanaMaterial = 'water';

    tuneImportedStageMaterial(mesh);

    expect(material.transparent).toBe(true);
    expect(material.opacity).toBeCloseTo(0.72);
    expect(material.depthWrite).toBe(false);
    expect(material.roughness).toBeCloseTo(0.072);
    expect(material.envMapIntensity).toBeCloseTo(1.9);
    expect(material.normalScale.x).toBeCloseTo(0.52);
    expect(normal.wrapS).toBe(THREE.RepeatWrapping);
    expect(roughness.wrapT).toBe(THREE.RepeatWrapping);
    expect(mesh.castShadow).toBe(false);
    expect(mesh.renderOrder).toBe(1);
  });

  it('Blender発光面のHDR上限をBloom閾値未満へ抑え色相を保つ', () => {
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(1, 0.62, 0.12),
      emissive: new THREE.Color(1, 0.62, 0.12),
      emissiveIntensity: 1.9,
      roughness: 0.2,
      metalness: 0.5,
      envMapIntensity: 1.8,
    });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(16, 3), material);
    mesh.userData.hibanaMaterial = 'emissive';
    mesh.castShadow = true;

    tuneImportedStageMaterial(mesh);

    expect(Math.max(material.color.r, material.color.g, material.color.b)).toBeCloseTo(0.28);
    expect(
      Math.max(material.emissive.r, material.emissive.g, material.emissive.b) *
      material.emissiveIntensity,
    ).toBeCloseTo(0.42);
    expect(material.color.g / material.color.r).toBeCloseTo(0.62);
    expect(material.emissive.g / material.emissive.r).toBeCloseTo(0.62);
    expect(material.roughness).toBeCloseTo(0.44);
    expect(material.metalness).toBeCloseTo(0.12);
    expect(material.envMapIntensity).toBeCloseTo(0.45);
    expect(mesh.castShadow).toBe(false);
    expect(mesh.receiveShadow).toBe(true);

    // 共有materialを持つ複数meshでも、2回目がさらに暗くしない。
    tuneImportedStageMaterial(mesh);
    expect(Math.max(material.color.r, material.color.g, material.color.b)).toBeCloseTo(0.28);
  });

  it('反射窓面は受光を残し不要なマクロ投影を停止する', () => {
    const material = new THREE.MeshStandardMaterial({
      roughness: 0.42,
      metalness: 0.08,
      envMapIntensity: 0.4,
    });
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(8, 4), material);
    mesh.userData.hibanaMaterial = 'glass';
    mesh.castShadow = true;
    mesh.receiveShadow = false;

    tuneImportedStageMaterial(mesh);

    expect(material.roughness).toBeCloseTo(0.18);
    expect(material.metalness).toBeCloseTo(0.24);
    expect(material.envMapIntensity).toBeCloseTo(0.92);
    expect(mesh.castShadow).toBe(false);
    expect(mesh.receiveShadow).toBe(true);
  });
});
