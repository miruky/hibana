import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const REPO_ROOT = resolve(ROOT, '../..');
const GENERATED = resolve(ROOT, 'generated');
const auditText = await readFile(resolve(GENERATED, 'stage-placement-audit.json'), 'utf8');
const audit = JSON.parse(auditText);
const catalogText = await readFile(resolve(ROOT, 'stage-world.catalog.json'), 'utf8');
const catalog = JSON.parse(catalogText);
const manifest = JSON.parse(await readFile(resolve(GENERATED, 'stage-placement.manifest.json'), 'utf8'));
const proof = JSON.parse(await readFile(resolve(GENERATED, 'proof7-breaking-diff.json'), 'utf8'));
const generatedTs = await readFile(resolve(REPO_ROOT, 'src/game/generated/stage-placements.generated.ts'), 'utf8');
const layoutsText = await readFile(resolve(GENERATED, 'stage-layouts.json'), 'utf8');
const layouts = JSON.parse(layoutsText);
const allModeAudit = JSON.parse(await readFile(resolve(GENERATED, 'all-mode-objective-audit.json'), 'utf8'));
const adapterModeAudit = JSON.parse(await readFile(resolve(GENERATED, 'mode-spawn-route-audit.json'), 'utf8'));

function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
}

function sha256(value) {
  return createHash('sha256').update(value, 'utf8').digest('hex');
}

// Mirrors stage-placement-solver.mjs's normalizedLayoutsPayload: the layout's
// own embedded placementSolverSha256 must be excluded before hashing, or the
// hash of "the layout" depends on a value derived from the hash of "the
// layout" and no fixed point can exist.
function normalizedLayoutsPayload(layoutsDoc) {
  const { placementSolverSha256: _ignored, ...payload } = layoutsDoc;
  return stableStringify(payload);
}

function overlaps(a, b, margin = 0) {
  return a.minX - margin < b.maxX && a.maxX + margin > b.minX
    && a.minZ - margin < b.maxZ && a.maxZ + margin > b.minZ;
}

function pointAabbDistance(x, z, box) {
  const dx = Math.max(0, box.minX - x, x - box.maxX);
  const dz = Math.max(0, box.minZ - z, z - box.maxZ);
  return Math.hypot(dx, dz);
}

function aabbGap(a, b) {
  const dx = Math.max(0, a.minX - b.maxX, b.minX - a.maxX);
  const dz = Math.max(0, a.minZ - b.maxZ, b.minZ - a.maxZ);
  return Math.hypot(dx, dz);
}

function routeAabb(approach) {
  const radius = approach.width / 2;
  return {
    minX: Math.min(approach.start[0], approach.end[0]) - radius,
    maxX: Math.max(approach.start[0], approach.end[0]) + radius,
    minZ: Math.min(approach.start[1], approach.end[1]) - radius,
    maxZ: Math.max(approach.start[1], approach.end[1]) + radius,
  };
}

function districtAabb(district) {
  return {
    minX: district.cx - district.width / 2,
    maxX: district.cx + district.width / 2,
    minZ: district.cz - district.depth / 2,
    maxZ: district.cz + district.depth / 2,
  };
}

test('normalized solver SHA is deterministic and excludes only its embedded field', () => {
  const { solverSha256: _ignored, ...payload } = audit;
  const computed = sha256(stableStringify(payload));
  assert.equal(computed, audit.solverSha256);
  const alteredStamp = { ...audit, solverSha256: '0'.repeat(64) };
  const { solverSha256: _ignoredAgain, ...alteredPayload } = alteredStamp;
  assert.equal(sha256(stableStringify(alteredPayload)), computed);
  const changed = structuredClone(audit);
  changed.stages[0].evaluatedMapSizeM += 1;
  const { solverSha256: _thirdIgnored, ...changedPayload } = changed;
  assert.notEqual(sha256(stableStringify(changedPayload)), computed);
});

test('catalog contains exactly 31 PASS stages and 62 unique validated landmark records', () => {
  assert.equal(audit.stages.length, 31);
  assert.equal(new Set(audit.stages.map((stage) => stage.id)).size, 31);
  const landmarks = audit.stages.flatMap((stage) => stage.landmarks);
  assert.equal(landmarks.length, 62);
  assert.equal(new Set(landmarks.map((landmark) => landmark.id)).size, 62);
  assert.ok(audit.stages.every((stage) => stage.status === 'PASS' && stage.landmarks.length === 2));
  assert.equal(audit.summary.passStageCount, 31);
  assert.equal(audit.summary.validatedLandmarkCount, 62);
  assert.deepEqual(audit.summary.noShipStageIds, []);
  assert.equal(audit.stages.reduce((sum, stage) => sum + stage.ordinaryDistricts.length, 0), 315);
});

test('all 62 output identities and local collision dimensions join exactly to the canonical catalog', () => {
  assert.equal(sha256(catalogText), audit.sources.catalogSha256);
  for (const stage of audit.stages) {
    const canonicalStage = catalog.stages.find((item) => item.id === stage.id);
    assert.ok(canonicalStage, stage.id);
    for (let index = 0; index < 2; index += 1) {
      const actual = stage.landmarks[index];
      const expected = canonicalStage.landmarks[index];
      assert.deepEqual(
        {
          id: actual.id,
          districtKind: actual.districtKind,
          collisionTemplate: actual.collisionTemplate,
          width: actual.width,
          depth: actual.depth,
          height: actual.height,
        },
        {
          id: expected.id,
          districtKind: expected.collision.districtKind,
          collisionTemplate: expected.collision.collisionTemplate,
          width: expected.collision.collisionFootprintM.width,
          depth: expected.collision.collisionFootprintM.depth,
          height: expected.collision.heightM,
        },
        `${stage.id} landmark ${index}`,
      );
    }
  }
});

test('every runtime AABB is in bounds and all structures clear player 30m / bot 8m', () => {
  for (const stage of audit.stages) {
    const half = stage.evaluatedMapSizeM / 2;
    const [first, second] = stage.landmarks;
    assert.ok(aabbGap(first.footprintBounds, second.footprintBounds) >= 6 - 1e-9, stage.id);
    assert.ok(stage.landmarks.every((landmark) => landmark.rot === 0), `${stage.id}: runtime adapter does not rotate AABB width/depth`);
    const allBoxes = [...stage.landmarks.map((landmark) => landmark.footprintBounds), ...stage.ordinaryDistricts.map(districtAabb)];
    for (const landmark of stage.landmarks) {
      const box = landmark.footprintBounds;
      assert.ok(box.minX >= -half + 4 - 1e-9 && box.maxX <= half - 4 + 1e-9, `${stage.id}/${landmark.id} X bounds`);
      assert.ok(box.minZ >= -half + 4 - 1e-9 && box.maxZ <= half - 4 + 1e-9, `${stage.id}/${landmark.id} Z bounds`);
    }
    for (const [x, , z] of stage.playerSpawns) {
      assert.ok(allBoxes.every((box) => pointAabbDistance(x, z, box) >= 30 - 1e-9), `${stage.id} player spawn clearance`);
    }
    for (const [x, , z] of stage.botSpawns) {
      assert.ok(allBoxes.every((box) => pointAabbDistance(x, z, box) >= 8 - 1e-9), `${stage.id} bot spawn clearance`);
    }
  }
});

test('roads, approaches and ordinary districts preserve the 12m capsule contract', () => {
  for (const stage of audit.stages) {
    const half = stage.evaluatedMapSizeM / 2;
    assert.ok(stage.roads.every((road) => road.width >= 16), stage.id);
    const landmarkBoxes = stage.landmarks.map((landmark) => landmark.footprintBounds);
    const districtBoxes = stage.ordinaryDistricts.map(districtAabb);
    for (const landmark of stage.landmarks) {
      for (const road of stage.roads) assert.equal(overlaps(landmark.footprintBounds, road.bounds, 6), false, `${stage.id}/${landmark.id} road`);
      const length = Math.hypot(
        landmark.approach.start[0] - landmark.approach.end[0],
        landmark.approach.start[1] - landmark.approach.end[1],
      );
      assert.ok(length >= 20 && landmark.approach.width >= 12, `${stage.id}/${landmark.id} approach dimensions`);
      const route = routeAabb(landmark.approach);
      assert.ok(route.minX >= -half && route.maxX <= half && route.minZ >= -half && route.maxZ <= half, `${stage.id}/${landmark.id} approach bounds`);
      assert.ok(districtBoxes.every((box) => !overlaps(route, box, 0)), `${stage.id}/${landmark.id} approach/district`);
      assert.ok(landmarkBoxes.every((box) => box === landmark.footprintBounds || !overlaps(route, box, 0)), `${stage.id}/${landmark.id} approach/landmark`);
    }
    for (let index = 0; index < districtBoxes.length; index += 1) {
      assert.ok(
        districtBoxes[index].minX >= -half + 4 - 1e-9
          && districtBoxes[index].maxX <= half - 4 + 1e-9
          && districtBoxes[index].minZ >= -half + 4 - 1e-9
          && districtBoxes[index].maxZ <= half - 4 + 1e-9,
        `${stage.id} district ${index} bounds`,
      );
      assert.ok(landmarkBoxes.every((box) => !overlaps(districtBoxes[index], box, 6)), `${stage.id} district/landmark`);
      assert.ok(stage.roads.every((road) => !overlaps(districtBoxes[index], road.bounds, 6)), `${stage.id} district/road`);
      for (let other = index + 1; other < districtBoxes.length; other += 1) {
        assert.equal(overlaps(districtBoxes[index], districtBoxes[other], 6), false, `${stage.id} districts ${index}/${other}`);
      }
    }
  }
});

test('ordinary district count and source recipe functionality are retained', () => {
  for (const stage of audit.stages) {
    assert.equal(stage.ordinaryDistricts.length, stage.sourceAudit.sourceOrdinaryDistrictCount, stage.id);
    assert.ok(stage.sourceAudit.recipeBuildings.length >= 1, stage.id);
    assert.equal(stage.sourceAudit.finiteTransforms, true, stage.id);
    assert.ok(stage.sourceAudit.groundContactEvidenceBoxCount > 0, stage.id);
    const sourceLayout = layouts.stages.find((item) => item.id === stage.id);
    assert.ok(sourceLayout, stage.id);
    const landmarkKeys = new Set((sourceLayout.landmarkPlacements ?? []).map((item) => `${item.cx}:${item.cz}:${item.width}:${item.depth}`));
    const sourceOrdinary = sourceLayout.districtPlacements.filter((item) => !landmarkKeys.has(`${item.cx}:${item.cz}:${item.width}:${item.depth}`));
    assert.equal(sourceOrdinary.length, stage.ordinaryDistricts.length, stage.id);
    for (const district of stage.ordinaryDistricts) {
      const source = sourceOrdinary[district.sourceIndex];
      assert.ok(source, `${stage.id}/${district.sourceIndex}`);
      assert.equal(district.kind, source.kind, `${stage.id}/${district.sourceIndex} kind`);
      assert.deepEqual(
        [district.width, district.depth].sort((a, b) => a - b),
        [source.width, source.depth].sort((a, b) => a - b),
        `${stage.id}/${district.sourceIndex} dimensions`,
      );
    }
  }
});

test('repository-local mode spawn and route audit is 31/31 PASS with zero violation codes', () => {
  assert.equal(adapterModeAudit.schemaVersion, '2.0.0');
  assert.equal(adapterModeAudit.summary.stageCount, 31);
  assert.equal(adapterModeAudit.summary.passStageIds.length, 31);
  assert.deepEqual(adapterModeAudit.summary.noShipStageIds, []);
  assert.deepEqual(adapterModeAudit.summary.failureCounts, {});
  assert.ok(adapterModeAudit.stages.every((stage) => stage.releaseGate === 'PASS' && stage.failures.length === 0));
});

test('all objective, formation, shop and training reservations pass with zero violations', () => {
  assert.equal(allModeAudit.summary.stageCount, 31);
  assert.equal(allModeAudit.summary.passStageCount, 31);
  assert.equal(allModeAudit.summary.violationCount, 0);
  assert.deepEqual(allModeAudit.summary.noShipStageIds, []);
  assert.deepEqual(allModeAudit.summary.failureCounts, {});
  assert.equal(allModeAudit.summary.fixedObjectiveReservationCount, 294);
  assert.equal(allModeAudit.summary.flexibleZombieShopGroupCount, 203);
  for (const stage of allModeAudit.stages) {
    assert.equal(stage.pass, true, stage.stageId);
    assert.equal(stage.objectives.pass, true, stage.stageId);
    assert.equal(stage.snd.pass, true, stage.stageId);
    assert.equal(stage.zombie.pass, true, stage.stageId);
    assert.ok(stage.objectives.fixedAndSpecial.every((item) => item.pass), stage.stageId);
    assert.ok(stage.objectives.flexibleZombieShop.every((item) => item.pass && item.selected !== null), stage.stageId);
    assert.ok(stage.objectives.campaign.every((item) => item.clearanceM >= 1), stage.stageId);
  }
});

test('all navigation, visibility, grounding, combat and occupancy gates pass independently recorded audits', () => {
  for (const stage of audit.stages) {
    assert.deepEqual(Object.values(stage.checks).filter((value) => value !== true), [], stage.id);
    assert.equal(stage.navigationAudit.reachable, true, stage.id);
    assert.ok(stage.navigationAudit.targetResults.every((target) => target.reachable && target.snappedDistanceM <= 6), stage.id);
    assert.ok(stage.visibilityAudit.every((item) => item.cameraHeightM === 1.65 && item.visible && Math.abs(item.bearingDeg) <= 82 && item.angularHeightDeg >= 6), stage.id);
    assert.ok(stage.landmarks.every((landmark) => landmark.grounded && landmark.groundY === 0 && landmark.combatSpace), stage.id);
    assert.ok(stage.metrics.totalStructureOccupancyRate <= 0.48, stage.id);
    assert.deepEqual(stage.failures, [], stage.id);
  }
});

test('renshujo adopts 236m and honestly rejects the separately evaluated 200m compact variant', () => {
  const adopted = audit.stages.find((stage) => stage.id === 'renshujo');
  const compact = audit.renshujo.compact200mEvaluation;
  assert.equal(audit.renshujo.preferredVariant, 'recommended-236m');
  assert.equal(audit.renshujo.adoptedVariant, 'recommended-236m');
  assert.equal(adopted.evaluatedMapSizeM, 236);
  assert.equal(adopted.status, 'PASS');
  assert.equal(compact.evaluatedMapSizeM, 200);
  assert.equal(compact.status, 'NO-SHIP');
  assert.ok(compact.failures.some((failure) => failure.includes('no-valid-landmark-pair')));
  assert.equal(compact.landmarks.length, 0, 'must not fabricate compact coordinates');
});

test('proof7 collision prototypes remain a zero-breaking-difference contract', () => {
  assert.equal(proof.status, 'PASS');
  assert.equal(proof.representativeStageCount, 7);
  assert.equal(proof.representativeLandmarkCount, 14);
  assert.deepEqual(proof.semanticFields, [
    'id',
    'districtKind',
    'collisionTemplate',
    'width',
    'depth',
    'height',
  ]);
  assert.equal(proof.breakingDifferenceCount, 0);
  assert.ok(proof.stages.every((stage) => stage.semanticEqual));
});

test('no migration heuristic tags survive into the proposed generated plan', () => {
  assert.equal(audit.summary.heuristicTagCount, 0);
  assert.doesNotMatch(auditText, /migration-heuristic-explicit-review-required/);
  assert.ok(audit.stages.flatMap((stage) => stage.landmarks).every((landmark) => landmark.approvalSource.includes('all-mode-validated')));
});

test('manifest and TypeScript embed the exact solver and catalog SHAs', () => {
  assert.equal(manifest.solverSha256, audit.solverSha256);
  assert.equal(manifest.catalogSha256, audit.catalogSha256);
  assert.equal(manifest.stageCount, 31);
  assert.equal(manifest.landmarkRecordCount, 62);
  assert.equal(manifest.validatedLandmarkCount, 62);
  assert.equal(manifest.allModePassStageCount, 31);
  assert.equal(manifest.allModeViolationCount, 0);
  assert.match(generatedTs, new RegExp(`STAGE_PLACEMENT_SOLVER_SHA256 = "${audit.solverSha256}"`));
  assert.match(generatedTs, new RegExp(`STAGE_WORLD_CATALOG_SHA256 = "${audit.catalogSha256}"`));
  assert.match(generatedTs, /Readonly<Record<SolverStageId, SolverStagePlacement>>/);
  assert.match(generatedTs, /SOLVER_V2_STAGE_PLACEMENTS/);
  assert.match(generatedTs, /SOLVER_V1_STAGE_PLACEMENTS = SOLVER_V2_STAGE_PLACEMENTS/);
});

test('live source hashes still match the exact repository files used by the solver', async () => {
  const repo = REPO_ROOT;
  const [layouts, stageTs, stagesTs, matchTs, storyEngineTs, sndTs, zombieDirectorTs, trainingRangeTs, modesTs] = await Promise.all([
    readFile(resolve(repo, 'tools/blender/generated/stage-layouts.json'), 'utf8'),
    readFile(resolve(repo, 'src/game/stage.ts'), 'utf8'),
    readFile(resolve(repo, 'src/game/stages.ts'), 'utf8'),
    readFile(resolve(repo, 'src/game/match.ts'), 'utf8'),
    readFile(resolve(repo, 'src/game/story-engine.ts'), 'utf8'),
    readFile(resolve(repo, 'src/game/snd.ts'), 'utf8'),
    readFile(resolve(repo, 'src/game/zombie-director.ts'), 'utf8'),
    readFile(resolve(repo, 'src/game/training-range.ts'), 'utf8'),
    readFile(resolve(repo, 'src/game/modes.ts'), 'utf8'),
  ]);
  assert.equal(sha256(normalizedLayoutsPayload(JSON.parse(layouts))), audit.sources.layoutsSha256);
  assert.equal(sha256(stageTs), audit.sources.stageTsSha256);
  assert.equal(sha256(stagesTs), audit.sources.stagesTsSha256);
  assert.equal(sha256(matchTs), audit.sources.matchTsSha256);
  assert.equal(sha256(storyEngineTs), audit.sources.storyEngineTsSha256);
  assert.equal(sha256(sndTs), audit.sources.sndTsSha256);
  assert.equal(sha256(zombieDirectorTs), audit.sources.zombieDirectorTsSha256);
  assert.equal(sha256(trainingRangeTs), audit.sources.trainingRangeTsSha256);
  assert.equal(sha256(modesTs), audit.sources.modesTsSha256);
});
