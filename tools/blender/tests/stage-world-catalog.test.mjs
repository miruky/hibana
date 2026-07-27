import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  computeCatalogSha256,
  normalizedCatalogPayload,
  renderOutputs,
  stableStringify,
  validateCatalog,
} from '../codegen-stage-world.mjs';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const REPO_ROOT = resolve(ROOT, '../..');
const catalog = JSON.parse(await readFile(resolve(ROOT, 'stage-world.catalog.json'), 'utf8'));
const blender = JSON.parse(await readFile(resolve(ROOT, 'generated/stage-world.blender.generated.json'), 'utf8'));
const manifest = JSON.parse(await readFile(resolve(ROOT, 'generated/stage-world.manifest-sha.json'), 'utf8'));
const generatedTs = await readFile(resolve(REPO_ROOT, 'src/game/generated/stage-landmarks.generated.ts'), 'utf8');
const proofDiff = JSON.parse(await readFile(resolve(ROOT, 'generated/representative7-semantic-diff.json'), 'utf8'));
const schema = JSON.parse(await readFile(resolve(ROOT, 'stage-world.catalog.schema.json'), 'utf8'));

test('canonical catalog has exactly 31 stages and 62 unique joined landmark IDs', () => {
  assert.deepEqual(validateCatalog(catalog), { stageCount: 31, landmarkCount: 62 });
  const stageIds = catalog.stages.map((stage) => stage.id);
  const landmarks = catalog.stages.flatMap((stage) => stage.landmarks);
  assert.equal(new Set(stageIds).size, 31);
  assert.equal(new Set(landmarks.map((landmark) => landmark.id)).size, 62);
  assert.ok(landmarks.every((landmark) => landmark.id === landmark.legacyProfileId));
});

test('normalized SHA is deterministic and excludes only the embedded SHA field', () => {
  const first = computeCatalogSha256(catalog);
  const second = computeCatalogSha256(JSON.parse(JSON.stringify(catalog)));
  assert.equal(first, second);
  assert.equal(first, catalog.catalogSha256);
  const changedStamp = { ...catalog, catalogSha256: '0'.repeat(64) };
  assert.equal(computeCatalogSha256(changedStamp), first);
  const changedContent = structuredClone(catalog);
  changedContent.stages[0].identity.brief += 'x';
  assert.notEqual(computeCatalogSha256(changedContent), first);
  assert.equal(normalizedCatalogPayload(catalog), stableStringify(JSON.parse(normalizedCatalogPayload(catalog))));
});

test('canonical, TypeScript, Blender and manifest embed the same SHA', () => {
  const tsSha = generatedTs.match(/STAGE_WORLD_CATALOG_SHA256 = "([a-f0-9]{64})"/)?.[1];
  assert.equal(tsSha, catalog.catalogSha256);
  assert.equal(blender.catalogSha256, catalog.catalogSha256);
  assert.equal(manifest.catalogSha256, catalog.catalogSha256);
  assert.ok(blender.stages.every((stage) => stage.catalogSha256 === catalog.catalogSha256));
});

test('code generation is byte deterministic', () => {
  const first = renderOutputs(catalog);
  const second = renderOutputs(JSON.parse(JSON.stringify(catalog)));
  assert.deepEqual(first, second);
  for (const [name, expected] of Object.entries(first.files)) {
    const actual = name === 'stage-landmarks.generated.ts'
      ? generatedTs
      : name === 'stage-world.blender.generated.json'
        ? `${JSON.stringify(blender, null, 2)}\n`
        : `${JSON.stringify(manifest, null, 2)}\n`;
    assert.equal(actual, expected, `${name} drifted`);
  }
});

test('every stage carries explicit facade, roof, non-glass and LOD grammars', () => {
  for (const stage of catalog.stages) {
    assert.deepEqual(stage.districtGrammar.ordinaryFloors, [3, 6]);
    assert.ok(stage.facade.roofGrammar.length > 0);
    assert.ok(stage.facade.nonGlassAlternatives.length >= 4);
    assert.equal(stage.facade.lod2WindowCards, 0);
    assert.equal(stage.legacyVista.countedTowardLandmarkQuota, false);
    for (const key of ['lod0Preserve', 'lod1Preserve', 'lod2Preserve']) assert.ok(stage.lod[key].length > 0);
    for (const landmark of stage.landmarks) {
      assert.ok(landmark.geometryGrammar.conceptPriority.length > 0);
      assert.ok(landmark.geometryGrammar.primarySilhouette.length > 0);
      assert.ok(landmark.geometryGrammar.nonGlassAlternatives.length >= 4);
    }
  }
});

test('visual envelopes and collision footprints are separate contracts', () => {
  for (const landmark of catalog.stages.flatMap((stage) => stage.landmarks)) {
    assert.notStrictEqual(landmark.visualEnvelopeM, landmark.collision.collisionFootprintM);
    assert.ok(landmark.visualEnvelopeM.width > 0 && landmark.visualEnvelopeM.depth > 0 && landmark.visualEnvelopeM.height > 0);
    assert.ok(landmark.collision.collisionFootprintM.width > 0 && landmark.collision.collisionFootprintM.depth > 0);
  }
  for (const stageId of ['takadai', 'z04']) {
    const first = catalog.stages.find((stage) => stage.id === stageId).landmarks[0];
    assert.deepEqual(first.visualEnvelopeM, { width: 128, depth: 102, height: stageId === 'takadai' ? 70 : 72 });
    assert.deepEqual(first.collision.collisionFootprintM, { width: 124, depth: 100 });
  }
});

test('renshujo exposes the 236m recommendation and blocks silent 200m adoption', () => {
  const stage = catalog.stages.find((item) => item.id === 'renshujo');
  assert.equal(stage.mapSizeM.current, 200);
  assert.equal(stage.mapSizeM.recommended, 236);
  assert.equal(stage.mapSizeM.compactExceptionRequired, true);
  assert.match(stage.mapSizeM.exceptionReason, /31\.1%/);
  assert.match(stage.mapSizeM.adoptionGate, /coverage|spawn-clearance/);
});

test('representative seven are semantically identical to current stage.ts proof contract', () => {
  assert.equal(proofDiff.status, 'PASS');
  assert.equal(proofDiff.representativeStageCount, 7);
  assert.equal(proofDiff.representativeLandmarkCount, 14);
  assert.equal(proofDiff.breakingDifferenceCount, 0);
  assert.ok(proofDiff.stages.every((stage) => stage.semanticEqual));
});

test('JSON Schema carries the release-critical structural gates', () => {
  assert.equal(schema.$schema, 'https://json-schema.org/draft/2020-12/schema');
  assert.equal(schema.properties.stages.minItems, 31);
  assert.equal(schema.properties.stages.maxItems, 31);
  assert.equal(schema.$defs.stage.properties.landmarks.minItems, 2);
  assert.equal(schema.$defs.stage.properties.landmarks.maxItems, 2);
  assert.equal(schema.$defs.facade.properties.lod2WindowCards.const, 0);
});

test('live legacy profile join remains exact', async () => {
  const profiles = JSON.parse(await readFile(resolve(REPO_ROOT, 'tools/blender/stage-profiles.json'), 'utf8'));
  assert.deepEqual(catalog.stages.map((stage) => stage.id).sort(), Object.keys(profiles.profiles).sort());
  for (const stage of catalog.stages) {
    assert.deepEqual(stage.landmarks.map((landmark) => landmark.id), profiles.profiles[stage.id].megaLandmarks.map((landmark) => landmark.id));
  }
});
