import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  generateStage,
  generateStageFromGeneratedPlacement,
  type StageDef,
} from '../../src/game/stage.ts';
import {
  SOLVER_V2_STAGE_PLACEMENTS,
  STAGE_PLACEMENT_SOLVER_SHA256,
  STAGE_WORLD_CATALOG_SHA256,
} from '../../src/game/generated/stage-placements.generated.ts';
import { validateStagePlacement } from '../../src/game/stage-placement-runtime-core.ts';
import { STAGES } from '../../src/game/stages.ts';

const here = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const canonicalPlacements = argv.includes('--canonical-placements');
const outputArgumentIndex = argv.indexOf('--output');
if (outputArgumentIndex >= 0 && !argv[outputArgumentIndex + 1]) {
  throw new Error('--output requires a file path');
}
if (canonicalPlacements && outputArgumentIndex < 0) {
  throw new Error('--canonical-placements requires --output so it cannot overwrite the live export accidentally');
}
const output = outputArgumentIndex >= 0
  ? resolve(argv[outputArgumentIndex + 1]!)
  : resolve(here, 'generated/stage-layouts.json');
mkdirSync(dirname(output), { recursive: true });

const stages = STAGES.map((stage) => {
  let authoringDefinition: StageDef = stage;
  let layout;
  if (canonicalPlacements) {
    const raw = SOLVER_V2_STAGE_PLACEMENTS[
      stage.id as keyof typeof SOLVER_V2_STAGE_PLACEMENTS
    ];
    // Renshujo's two in-bounds landmarks require the separately audited 236m
    // authoring envelope. This does not mutate the live 200m StageDef; runtime
    // adoption remains guarded by the empty per-stage release allow-list.
    authoringDefinition = raw.mapSize === stage.size
      ? stage
      : { ...stage, size: raw.mapSize };
    const validation = validateStagePlacement(stage.id, raw, authoringDefinition);
    if (!validation.ok || !validation.value) {
      const detail = validation.issues
        .map((issue) => `${issue.code}@${issue.path}: ${issue.message}`)
        .join('; ');
      throw new Error(`${stage.id}: canonical authoring placement is invalid: ${detail}`);
    }
    layout = generateStageFromGeneratedPlacement(authoringDefinition, validation.value);
  } else {
    layout = generateStage(stage);
  }
  return {
    ...authoringDefinition,
    sourceStageSizeM: stage.size,
    authoringStageSizeM: authoringDefinition.size,
    placementSource: canonicalPlacements ? 'canonical-solver-v2-authoring' : 'runtime-release',
    boxes: layout.boxes,
    playerSpawns: layout.playerSpawns,
    botSpawns: layout.botSpawns,
    propPlacements: layout.propPlacements,
    districtPlacements: layout.districtPlacements,
    landmarkPlacements: layout.landmarkPlacements,
  };
});

writeFileSync(output, `${JSON.stringify({
  version: 1,
  generatedAt: new Date().toISOString(),
  placementSource: canonicalPlacements ? 'canonical-solver-v2-authoring' : 'runtime-release',
  placementSolverSha256: STAGE_PLACEMENT_SOLVER_SHA256,
  stageWorldCatalogSha256: STAGE_WORLD_CATALOG_SHA256,
  stages,
}, null, 2)}\n`);
console.log(JSON.stringify({
  output,
  placementSource: canonicalPlacements ? 'canonical-solver-v2-authoring' : 'runtime-release',
  stages: stages.length,
  landmarks: stages.reduce((sum, stage) => sum + stage.landmarkPlacements.length, 0),
  boxes: stages.reduce((sum, stage) => sum + stage.boxes.length, 0),
}, null, 2));
