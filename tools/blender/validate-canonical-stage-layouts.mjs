#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const EXPECTED_STAGE_COUNT = 31;
const EXPECTED_LANDMARK_COUNT = 62;
const MODULE_PATH = fileURLToPath(import.meta.url);

function finite(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function pointPair(value) {
  return Array.isArray(value) && value.length === 2 && value.every(finite);
}

export function validateCanonicalLayouts(document, expectedProvenance = null) {
  const errors = [];
  const stages = Array.isArray(document?.stages) ? document.stages : [];
  if (document?.placementSource !== 'canonical-solver-v2-authoring') {
    errors.push('root-placement-source');
  }
  if (expectedProvenance) {
    if (document?.placementSolverSha256 !== expectedProvenance.solverSha256) {
      errors.push('placement-solver-sha-mismatch');
    }
    if (document?.stageWorldCatalogSha256 !== expectedProvenance.catalogSha256) {
      errors.push('stage-world-catalog-sha-mismatch');
    }
  }
  if (stages.length !== EXPECTED_STAGE_COUNT) {
    errors.push(`stage-count:${stages.length}:${EXPECTED_STAGE_COUNT}`);
  }
  const stageIds = new Set();
  const landmarkIds = new Set();
  let landmarkCount = 0;
  for (const stage of stages) {
    const stageId = typeof stage?.id === 'string' ? stage.id : '<invalid-stage>';
    if (stageIds.has(stageId)) errors.push(`${stageId}:duplicate-stage-id`);
    stageIds.add(stageId);
    if (stage?.placementSource !== 'canonical-solver-v2-authoring') {
      errors.push(`${stageId}:placement-source`);
    }
    const size = stage?.authoringStageSizeM;
    if (!finite(size) || size <= 0 || stage?.size !== size) {
      errors.push(`${stageId}:authoring-size`);
      continue;
    }
    const landmarks = Array.isArray(stage?.landmarkPlacements)
      ? stage.landmarkPlacements
      : [];
    if (landmarks.length !== 2) errors.push(`${stageId}:landmark-count:${landmarks.length}:2`);
    for (const landmark of landmarks) {
      landmarkCount += 1;
      const id = landmark?.id;
      if (typeof id !== 'string' || !id.startsWith(`${stageId}-`)) {
        errors.push(`${stageId}:invalid-landmark-id`);
      } else if (landmarkIds.has(id)) {
        errors.push(`${stageId}:duplicate-landmark-id:${id}`);
      } else {
        landmarkIds.add(id);
      }
      const values = [landmark?.cx, landmark?.cz, landmark?.width, landmark?.depth, landmark?.height];
      if (!values.every(finite) || landmark.width <= 0 || landmark.depth <= 0 || landmark.height <= 0) {
        errors.push(`${stageId}:${id}:invalid-envelope`);
        continue;
      }
      const half = size / 2;
      if (
        Math.abs(landmark.cx) + landmark.width / 2 > half - 4 + 1e-6
        || Math.abs(landmark.cz) + landmark.depth / 2 > half - 4 + 1e-6
      ) errors.push(`${stageId}:${id}:outside-playable-bounds`);
      if (landmark.grounded !== true || landmark.combatSpace !== true) {
        errors.push(`${stageId}:${id}:not-playable`);
      }
      if (!pointPair(landmark.entrance) || !pointPair(landmark?.approach?.start)
        || !pointPair(landmark?.approach?.end) || !finite(landmark?.approach?.width)) {
        errors.push(`${stageId}:${id}:invalid-entrance-approach`);
      } else if (
        Math.hypot(
          landmark.approach.end[0] - landmark.entrance[0],
          landmark.approach.end[1] - landmark.entrance[1],
        ) > 1e-6
      ) errors.push(`${stageId}:${id}:approach-end-mismatch`);
    }
  }
  if (landmarkCount !== EXPECTED_LANDMARK_COUNT) {
    errors.push(`landmark-count:${landmarkCount}:${EXPECTED_LANDMARK_COUNT}`);
  }
  if (landmarkIds.size !== EXPECTED_LANDMARK_COUNT) {
    errors.push(`unique-landmark-count:${landmarkIds.size}:${EXPECTED_LANDMARK_COUNT}`);
  }
  const renshujo = stages.find((stage) => stage?.id === 'renshujo');
  if (renshujo?.sourceStageSizeM !== 200 || renshujo?.authoringStageSizeM !== 236) {
    errors.push('renshujo:explicit-200-to-236-authoring-envelope');
  }
  return {
    ok: errors.length === 0,
    summary: {
      stageCount: stages.length,
      landmarkCount,
      uniqueLandmarkCount: landmarkIds.size,
      errorCount: errors.length,
    },
    errors,
  };
}

async function main(argv) {
  const input = argv[0];
  if (!input) throw new Error('usage: validate-canonical-stage-layouts.mjs INPUT.json [REPORT.json]');
  const document = JSON.parse(await readFile(resolve(input), 'utf8'));
  const placementManifest = JSON.parse(await readFile(
    fileURLToPath(new URL('./generated/stage-placement.manifest.json', import.meta.url)),
    'utf8',
  ));
  const report = validateCanonicalLayouts(document, {
    solverSha256: placementManifest.solverSha256,
    catalogSha256: placementManifest.catalogSha256,
  });
  const payload = `${JSON.stringify(report, null, 2)}\n`;
  if (argv[1]) {
    const { writeFile } = await import('node:fs/promises');
    await writeFile(resolve(argv[1]), payload);
  }
  console.log(payload.trimEnd());
  return report.ok ? 0 : 1;
}

if (resolve(process.argv[1] ?? '') === resolve(MODULE_PATH)) {
  main(process.argv.slice(2)).then(
    (code) => { process.exitCode = code; },
    (error) => { console.error(error.stack ?? error); process.exitCode = 1; },
  );
}
