#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '../..');
const DEFAULT_GENERATED_DIR = resolve(HERE, 'generated');
const DEFAULT_TYPESCRIPT_OUT = resolve(REPO_ROOT, 'src/game/generated/stage-landmarks.generated.ts');
export const BUILDING_KINDS = ['arena', 'hangar', 'tower', 'warehouse', 'cathedral', 'bunker', 'terminal', 'refinery', 'villa', 'pagoda', 'fortress', 'station', 'checkpoint', 'metro', 'abbey'];
export const COLLISION_TEMPLATES = ['abbey', 'courtyard', 'hall', 'bridge', 'vertical'];

export function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
}

export function normalizedCatalogPayload(catalog) {
  const { catalogSha256: _ignored, ...payload } = catalog;
  return stableStringify(payload);
}

export function computeCatalogSha256(catalog) {
  return createHash('sha256').update(normalizedCatalogPayload(catalog), 'utf8').digest('hex');
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function nonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

export function validateCatalog(catalog) {
  assert(catalog && typeof catalog === 'object', 'catalog must be an object');
  assert(Array.isArray(catalog.stages) && catalog.stages.length === 31, 'catalog requires exactly 31 stages');
  const stageIds = new Set();
  const landmarkIds = new Set();
  for (const stage of catalog.stages) {
    assert(nonEmptyString(stage.id), 'stage id missing');
    assert(!stageIds.has(stage.id), `duplicate stage id ${stage.id}`);
    stageIds.add(stage.id);
    assert(Array.isArray(stage.landmarks) && stage.landmarks.length === 2, `${stage.id}: exactly two landmarks required`);
    assert(stage.identity && nonEmptyString(stage.identity.dominantSilhouette), `${stage.id}: dominant silhouette missing`);
    assert(stage.districtGrammar?.ordinaryFloors?.[0] === 3 && stage.districtGrammar?.ordinaryFloors?.[1] === 6, `${stage.id}: ordinary floor contract must be 3-6`);
    assert(Array.isArray(stage.facade?.nonGlassAlternatives) && stage.facade.nonGlassAlternatives.length >= 4, `${stage.id}: non-glass alternatives missing`);
    assert(nonEmptyString(stage.facade?.roofGrammar), `${stage.id}: roof grammar missing`);
    assert(stage.facade?.lod2WindowCards === 0, `${stage.id}: LOD2 window cards must be zero`);
    assert(stage.legacyVista?.countedTowardLandmarkQuota === false, `${stage.id}: legacy vista must be uncounted`);
    for (const [index, landmark] of stage.landmarks.entries()) {
      assert(landmark.ordinal === index, `${stage.id}: landmark ordinal mismatch`);
      assert(nonEmptyString(landmark.id), `${stage.id}: landmark ID missing`);
      assert(!landmarkIds.has(landmark.id), `duplicate landmark id ${landmark.id}`);
      landmarkIds.add(landmark.id);
      assert(landmark.id === landmark.legacyProfileId, `${landmark.id}: ID join drift`);
      assert(nonEmptyString(landmark.conceptLabel) && nonEmptyString(landmark.visualSignature), `${landmark.id}: concept identity missing`);
      assert(BUILDING_KINDS.includes(landmark.collision?.districtKind), `${landmark.id}: invalid district kind`);
      assert(COLLISION_TEMPLATES.includes(landmark.collision?.collisionTemplate), `${landmark.id}: invalid collision template`);
      assert(landmark.collision.collisionFootprintM.width > 0 && landmark.collision.collisionFootprintM.depth > 0 && landmark.collision.heightM > 0, `${landmark.id}: invalid collision dimensions`);
      assert(landmark.visualEnvelopeM.width > 0 && landmark.visualEnvelopeM.depth > 0 && landmark.visualEnvelopeM.height > 0, `${landmark.id}: invalid visual envelope`);
      assert(landmark.collision.collisionFootprintM !== landmark.visualEnvelopeM, `${landmark.id}: collision and visual envelope must be separate objects`);
      const grammar = landmark.geometryGrammar;
      assert(grammar && nonEmptyString(grammar.conceptPriority) && nonEmptyString(grammar.primarySilhouette), `${landmark.id}: explicit geometry grammar missing`);
      assert(nonEmptyString(grammar.roof) && nonEmptyString(grammar.facade) && nonEmptyString(grammar.entrance), `${landmark.id}: geometry roof/facade/entrance missing`);
      assert(Array.isArray(grammar.nonGlassAlternatives) && grammar.nonGlassAlternatives.length >= 4, `${landmark.id}: landmark non-glass grammar missing`);
    }
    for (const key of ['lod0Preserve', 'lod1Preserve', 'lod2Preserve']) {
      assert(Array.isArray(stage.lod?.[key]) && stage.lod[key].length > 0, `${stage.id}: ${key} missing`);
    }
  }
  assert(stageIds.size === 31, '31 unique stage IDs required');
  assert(landmarkIds.size === 62, '62 unique landmark IDs required');
  const renshujo = catalog.stages.find((stage) => stage.id === 'renshujo');
  assert(renshujo.mapSizeM.current === 200 && renshujo.mapSizeM.recommended >= 230, 'renshujo map-size recommendation missing');
  assert(renshujo.mapSizeM.compactExceptionRequired === true && nonEmptyString(renshujo.mapSizeM.adoptionGate), 'renshujo exception gate missing');
  return { stageCount: stageIds.size, landmarkCount: landmarkIds.size };
}

function q(value) {
  return JSON.stringify(value);
}

export function generateTypeScript(catalog, sha) {
  const stageIds = catalog.stages.map((stage) => q(stage.id)).join(' | ');
  const rows = catalog.stages.map((stage) => {
    const pair = stage.landmarks.map((landmark) => {
      const footprint = landmark.collision.collisionFootprintM;
      const visual = landmark.visualEnvelopeM;
      return `    { id: ${q(landmark.id)}, districtKind: ${q(landmark.collision.districtKind)}, collisionTemplate: ${q(landmark.collision.collisionTemplate)}, width: ${footprint.width}, depth: ${footprint.depth}, height: ${landmark.collision.heightM}, visualWidth: ${visual.width}, visualDepth: ${visual.depth}, visualHeight: ${visual.height} }`;
    }).join(',\n');
    return `  ${q(stage.id)}: [\n${pair},\n  ],`;
  }).join('\n');
  const recommendations = catalog.stages.map((stage) => `  ${q(stage.id)}: { current: ${stage.mapSizeM.current}, recommended: ${stage.mapSizeM.recommended}, compactExceptionRequired: ${stage.mapSizeM.compactExceptionRequired} },`).join('\n');
  return `// Generated by tools/blender/codegen-stage-world.mjs. DO NOT EDIT.\n` +
    `export const STAGE_WORLD_CATALOG_SHA256 = ${q(sha)} as const;\n\n` +
    `export type StageWorldStageId = ${stageIds};\n` +
    `export type GeneratedLandmarkCollisionTemplate = ${COLLISION_TEMPLATES.map(q).join(' | ')};\n` +
    `export type GeneratedLandmarkDistrictKind = ${BUILDING_KINDS.map(q).join(' | ')};\n\n` +
    `export interface GeneratedLandmarkPrototype {\n` +
    `  readonly id: string;\n  readonly districtKind: GeneratedLandmarkDistrictKind;\n  readonly collisionTemplate: GeneratedLandmarkCollisionTemplate;\n` +
    `  readonly width: number;\n  readonly depth: number;\n  readonly height: number;\n` +
    `  readonly visualWidth: number;\n  readonly visualDepth: number;\n  readonly visualHeight: number;\n}\n\n` +
    `export const GENERATED_STAGE_LANDMARKS: Readonly<Record<StageWorldStageId, readonly [GeneratedLandmarkPrototype, GeneratedLandmarkPrototype]>> = {\n${rows}\n};\n\n` +
    `export const GENERATED_STAGE_MAP_SIZES: Readonly<Record<StageWorldStageId, { readonly current: number; readonly recommended: number; readonly compactExceptionRequired: boolean }>> = {\n${recommendations}\n};\n`;
}

export function generateBlenderCatalog(catalog, sha) {
  const stages = catalog.stages.map((stage) => ({
    id: stage.id,
    name: stage.name,
    catalogSha256: sha,
    mapSizeM: stage.mapSizeM,
    referenceImage: stage.referenceImage,
    identity: stage.identity,
    districtGrammar: stage.districtGrammar,
    routes: stage.routes,
    facade: stage.facade,
    lod: stage.lod,
    legacyVista: stage.legacyVista,
    landmarks: stage.landmarks.map((landmark) => ({
      id: landmark.id,
      ordinal: landmark.ordinal,
      conceptLabel: landmark.conceptLabel,
      visualSignature: landmark.visualSignature,
      placementIntent: landmark.placementIntent,
      playableContract: landmark.playableContract,
      collision: landmark.collision,
      visualEnvelopeM: landmark.visualEnvelopeM,
      geometryGrammar: landmark.geometryGrammar,
    })),
  }));
  return `${JSON.stringify({ schemaVersion: catalog.schemaVersion, catalogSha256: sha, coordinateSystem: catalog.coordinateSystem, stages }, null, 2)}\n`;
}

export function generateManifest(catalog, sha) {
  return `${JSON.stringify({
    schemaVersion: '1.0.0',
    catalogSha256: sha,
    normalization: catalog.normalization,
    stageCount: catalog.stages.length,
    landmarkCount: catalog.stages.reduce((sum, stage) => sum + stage.landmarks.length, 0),
    generatedFiles: [
      'src/game/generated/stage-landmarks.generated.ts',
      'tools/blender/generated/stage-world.blender.generated.json',
    ],
  }, null, 2)}\n`;
}

export function renderOutputs(catalog) {
  validateCatalog(catalog);
  const sha = computeCatalogSha256(catalog);
  return {
    sha,
    files: {
      'stage-landmarks.generated.ts': generateTypeScript(catalog, sha),
      'stage-world.blender.generated.json': generateBlenderCatalog(catalog, sha),
      'stage-world.manifest-sha.json': generateManifest(catalog, sha),
    },
  };
}

function parseArgs(argv) {
  const options = {
    catalog: resolve(HERE, 'stage-world.catalog.json'),
    outDir: DEFAULT_GENERATED_DIR,
    typescriptOut: DEFAULT_TYPESCRIPT_OUT,
    check: false,
    stamp: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--check') options.check = true;
    else if (arg === '--stamp') options.stamp = true;
    else if (arg === '--catalog') options.catalog = resolve(argv[++index]);
    else if (arg === '--out-dir') options.outDir = resolve(argv[++index]);
    else if (arg === '--typescript-out') options.typescriptOut = resolve(argv[++index]);
    else throw new Error(`Unknown argument ${arg}`);
  }
  return options;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const catalog = JSON.parse(await readFile(options.catalog, 'utf8'));
  validateCatalog(catalog);
  const computedSha = computeCatalogSha256(catalog);
  if (options.stamp) {
    catalog.catalogSha256 = computedSha;
    await writeFile(options.catalog, `${JSON.stringify(catalog, null, 2)}\n`, 'utf8');
  } else if (catalog.catalogSha256 !== computedSha) {
    throw new Error(`catalog SHA mismatch: embedded=${catalog.catalogSha256} computed=${computedSha}; run --stamp`);
  }
  const rendered = renderOutputs(catalog);
  await mkdir(options.outDir, { recursive: true });
  await mkdir(dirname(options.typescriptOut), { recursive: true });
  const outputPath = (name) => name === 'stage-landmarks.generated.ts'
    ? options.typescriptOut
    : resolve(options.outDir, name);
  if (options.check) {
    const failures = [];
    for (const [name, expected] of Object.entries(rendered.files)) {
      let actual = null;
      try { actual = await readFile(outputPath(name), 'utf8'); } catch { /* reported below */ }
      if (actual !== expected) failures.push(name);
    }
    if (failures.length) throw new Error(`generated output drift: ${failures.join(', ')}`);
    process.stdout.write(`CHECK PASS ${rendered.sha} 31 stages 62 landmarks\n`);
    return;
  }
  for (const [name, content] of Object.entries(rendered.files)) {
    await writeFile(outputPath(name), content, 'utf8');
  }
  process.stdout.write(`GENERATED ${rendered.sha} 31 stages 62 landmarks\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  await main();
}
