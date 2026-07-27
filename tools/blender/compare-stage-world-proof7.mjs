#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '../..');

function parseArgs(argv) {
  const options = {
    'stage-ts': resolve(REPO_ROOT, 'src/game/stage.ts'),
    catalog: resolve(HERE, 'stage-world.catalog.json'),
    out: resolve(HERE, 'generated/representative7-semantic-diff.json'),
  };
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith('--')) continue;
    options[key.slice(2)] = resolve(argv[++index]);
  }
  return options;
}

function parseProofBlock(source) {
  const match = source.match(/const DENSE_WORLD_V5_LANDMARKS:[\s\S]*?= \{([\s\S]*?)\n\};/);
  if (!match) throw new Error('DENSE_WORLD_V5_LANDMARKS block not found');
  const result = {};
  const stagePattern = /^\s{2}([a-z0-9]+): \[\n([\s\S]*?)^\s{2}\],/gm;
  for (const stageMatch of match[1].matchAll(stagePattern)) {
    const pair = [];
    const itemPattern = /\{ id: '([^']+)', districtKind: '([^']+)', collisionTemplate: '([^']+)', width: ([\d.]+), depth: ([\d.]+), height: ([\d.]+) \}/g;
    for (const item of stageMatch[2].matchAll(itemPattern)) {
      pair.push({ id: item[1], districtKind: item[2], collisionTemplate: item[3], width: Number(item[4]), depth: Number(item[5]), height: Number(item[6]) });
    }
    if (pair.length !== 2) throw new Error(`${stageMatch[1]}: expected two parsed proof landmarks, got ${pair.length}`);
    result[stageMatch[1]] = pair;
  }
  return result;
}

function canonicalPair(stage) {
  return stage.landmarks.map((landmark) => ({
    id: landmark.id,
    districtKind: landmark.collision.districtKind,
    collisionTemplate: landmark.collision.collisionTemplate,
    width: landmark.collision.collisionFootprintM.width,
    depth: landmark.collision.collisionFootprintM.depth,
    height: landmark.collision.heightM,
  }));
}

function diffRecord(current, generated) {
  const fields = ['id', 'districtKind', 'collisionTemplate', 'width', 'depth', 'height'];
  return fields.flatMap((field) => current[field] === generated[field] ? [] : [{ field, current: current[field], generated: generated[field] }]);
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const [source, catalogText] = await Promise.all([readFile(options['stage-ts'], 'utf8'), readFile(options.catalog, 'utf8')]);
  const catalog = JSON.parse(catalogText);
  const current = parseProofBlock(source);
  const diffs = [];
  const stages = [];
  for (const [stageId, currentPair] of Object.entries(current)) {
    const canonicalStage = catalog.stages.find((stage) => stage.id === stageId);
    if (!canonicalStage) throw new Error(`${stageId}: missing canonical stage`);
    const generatedPair = canonicalPair(canonicalStage);
    const pairDiffs = currentPair.flatMap((item, index) => diffRecord(item, generatedPair[index]).map((diff) => ({ ordinal: index, id: item.id, ...diff })));
    diffs.push(...pairDiffs.map((diff) => ({ stageId, ...diff })));
    stages.push({ stageId, current: currentPair, generated: generatedPair, semanticEqual: pairDiffs.length === 0, differences: pairDiffs });
  }
  const report = {
    schemaVersion: '1.0.0',
    catalogSha256: catalog.catalogSha256,
    currentStageTsSha256: createHash('sha256').update(source).digest('hex'),
    representativeStageCount: stages.length,
    representativeLandmarkCount: stages.length * 2,
    semanticFields: ['id', 'districtKind', 'collisionTemplate', 'width', 'depth', 'height'],
    status: stages.length === 7 && diffs.length === 0 ? 'PASS' : 'FAIL',
    breakingDifferenceCount: diffs.length,
    nonBreakingCanonicalAdditions: ['visualEnvelopeM', 'conceptLabel', 'visualSignature', 'geometryGrammar', 'facade.nonGlassAlternatives', 'stage-specific LOD rules', 'legacyVista uncounted policy', 'catalog SHA'],
    stages,
  };
  await mkdir(dirname(options.out), { recursive: true });
  await writeFile(options.out, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  process.stdout.write(`${report.status} proof7=${stages.length} diffs=${diffs.length}\n`);
  if (report.status !== 'PASS') process.exitCode = 1;
}

await main();
