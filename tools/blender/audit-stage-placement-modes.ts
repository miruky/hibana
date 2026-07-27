import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const repo = resolve(HERE, '../..');
const outputDir = resolve(HERE, 'generated');
const check = process.argv.includes('--check');

const generatedModule = await import(pathToFileURL(resolve(repo, 'src/game/generated/stage-placements.generated.ts')).href);
const stagesModule = await import(pathToFileURL(resolve(repo, 'src/game/stages.ts')).href);
const sndModule = await import(pathToFileURL(resolve(repo, 'src/game/snd.ts')).href);
const table = generatedModule.SOLVER_V2_STAGE_PLACEMENTS as Record<string, RawStage>;
const definitions = new Map<string, StageDef>(
  (stagesModule.STAGES as StageDef[]).map((item) => [item.id, item]),
);
const makeSndSpawnFormation = sndModule.makeSndSpawnFormation as (
  anchor: Point3,
  count: number,
) => Point3[];

interface StageDef {
  id: string;
  size: number;
  botCount: number;
}

type Spawn = [number, number, number];
interface Point3 { x: number; y: number; z: number }
interface Aabb { minX: number; maxX: number; minZ: number; maxZ: number }
interface Structure { label: string; cx: number; cz: number; width: number; depth: number }
interface RawStage {
  status: string;
  mapSize: number;
  playerSpawns: Spawn[];
  botSpawns: Spawn[];
  roads: Array<{ id: string; width: number; bounds: Aabb }>;
  landmarks: Array<Structure & { id: string; approach: { start: [number, number]; end: [number, number]; width: number } }>;
  ordinaryDistricts: Array<Structure & { kind: string }>;
}

function boxOf(item: Structure): Aabb {
  return {
    minX: item.cx - item.width / 2,
    maxX: item.cx + item.width / 2,
    minZ: item.cz - item.depth / 2,
    maxZ: item.cz + item.depth / 2,
  };
}

function overlaps(a: Aabb, b: Aabb, margin = 0): boolean {
  return a.minX - margin < b.maxX && a.maxX + margin > b.minX
    && a.minZ - margin < b.maxZ && a.maxZ + margin > b.minZ;
}

function pointDistance(x: number, z: number, box: Aabb): number {
  return Math.hypot(
    Math.max(0, box.minX - x, x - box.maxX),
    Math.max(0, box.minZ - z, z - box.maxZ),
  );
}

function pairDistance(a: Spawn, b: Spawn): number {
  return Math.hypot(a[0] - b[0], a[2] - b[2]);
}

function minStructureClearance(spawn: Spawn, boxes: Aabb[]): number {
  return Math.min(...boxes.map((box) => pointDistance(spawn[0], spawn[2], box)));
}

function nearestFreeGrid(
  spawn: Spawn,
  isWalkable: (gx: number, gz: number) => boolean,
  min: number,
  max: number,
  step: number,
): [number, number] | null {
  const baseX = Math.round((spawn[0] - min) / step);
  const baseZ = Math.round((spawn[2] - min) / step);
  for (let radius = 0; radius <= 4; radius += 1) {
    for (let dx = -radius; dx <= radius; dx += 1) {
      for (let dz = -radius; dz <= radius; dz += 1) {
        if (Math.max(Math.abs(dx), Math.abs(dz)) !== radius) continue;
        const gx = baseX + dx;
        const gz = baseZ + dz;
        const x = min + gx * step;
        const z = min + gz * step;
        if (x < min || x > max || z < min || z > max) continue;
        if (isWalkable(gx, gz)) return [gx, gz];
      }
    }
  }
  return null;
}

function bfsAudit(stage: RawStage, boxes: Aabb[]): { reachable: boolean; visited: number; walkable: number } {
  const step = 4;
  const min = -stage.mapSize / 2 + 4;
  const max = stage.mapSize / 2 - 4;
  const count = Math.floor((max - min) / step) + 1;
  const index = (gx: number, gz: number) => gz * count + gx;
  const walkable = new Uint8Array(count * count);
  let walkableCount = 0;
  for (let gz = 0; gz < count; gz += 1) {
    for (let gx = 0; gx < count; gx += 1) {
      const x = min + gx * step;
      const z = min + gz * step;
      const blocked = boxes.some((box) =>
        x > box.minX - 0.6 && x < box.maxX + 0.6 && z > box.minZ - 0.6 && z < box.maxZ + 0.6);
      if (!blocked) {
        walkable[index(gx, gz)] = 1;
        walkableCount += 1;
      }
    }
  }
  const isWalkable = (gx: number, gz: number): boolean =>
    gx >= 0 && gx < count && gz >= 0 && gz < count && walkable[index(gx, gz)] === 1;
  const anchors = [...stage.playerSpawns, ...stage.botSpawns]
    .map((spawn) => nearestFreeGrid(spawn, isWalkable, min, max, step));
  if (anchors.some((item) => item === null)) return { reachable: false, visited: 0, walkable: walkableCount };
  const start = anchors[0]!;
  const queue: Array<[number, number]> = [start];
  const seen = new Uint8Array(count * count);
  seen[index(start[0], start[1])] = 1;
  let cursor = 0;
  while (cursor < queue.length) {
    const [gx, gz] = queue[cursor++]!;
    for (const [nx, nz] of [[gx + 1, gz], [gx - 1, gz], [gx, gz + 1], [gx, gz - 1]] as const) {
      if (!isWalkable(nx, nz)) continue;
      const key = index(nx, nz);
      if (seen[key]) continue;
      seen[key] = 1;
      queue.push([nx, nz]);
    }
  }
  return {
    reachable: anchors.every(([gx, gz]) => seen[index(gx, gz)] === 1),
    visited: queue.length,
    walkable: walkableCount,
  };
}

function sndFormationAudit(stage: RawStage, botCount: number, boxes: Aabb[]): {
  pass: boolean;
  minimumClearanceM: number;
  minimumOpponentGapM: number;
  outOfBounds: number;
} {
  const allyCount = Math.max(0, Math.floor((botCount - 1) / 2));
  const playerMembers = 1 + allyCount;
  const enemyMembers = Math.max(1, botCount - allyCount);
  const half = stage.mapSize / 2;
  let minimumClearanceM = Infinity;
  let minimumOpponentGapM = Infinity;
  let outOfBounds = 0;
  for (let roundIndex = 0; roundIndex < 8; roundIndex += 1) {
    const attackFromPlayerSide = roundIndex < 4;
    const playerCandidates = attackFromPlayerSide ? stage.playerSpawns : stage.botSpawns;
    const enemyCandidates = attackFromPlayerSide ? stage.botSpawns : stage.playerSpawns;
    const playerAnchorRaw = playerCandidates[roundIndex % Math.max(1, playerCandidates.length)] ?? [0, 0, 0];
    const playerAnchor: Point3 = { x: playerAnchorRaw[0], y: playerAnchorRaw[1], z: playerAnchorRaw[2] };
    let enemyAnchorRaw = enemyCandidates[0] ?? [0, 0, 0];
    let farthestSq = -1;
    for (const candidate of enemyCandidates) {
      const distanceSq = (candidate[0] - playerAnchor.x) ** 2 + (candidate[2] - playerAnchor.z) ** 2;
      if (distanceSq > farthestSq) {
        farthestSq = distanceSq;
        enemyAnchorRaw = candidate;
      }
    }
    const enemyAnchor: Point3 = { x: enemyAnchorRaw[0], y: enemyAnchorRaw[1], z: enemyAnchorRaw[2] };
    const playerFormation = makeSndSpawnFormation(playerAnchor, playerMembers);
    const enemyFormation = makeSndSpawnFormation(enemyAnchor, enemyMembers);
    for (const point of [...playerFormation, ...enemyFormation]) {
      if (Math.abs(point.x) > half - 0.5 || Math.abs(point.z) > half - 0.5) outOfBounds += 1;
      const clearance = Math.min(...boxes.map((box) => pointDistance(point.x, point.z, box)));
      minimumClearanceM = Math.min(minimumClearanceM, clearance);
    }
    for (const player of playerFormation) {
      for (const enemy of enemyFormation) {
        minimumOpponentGapM = Math.min(
          minimumOpponentGapM,
          Math.hypot(player.x - enemy.x, player.z - enemy.z),
        );
      }
    }
  }
  return {
    pass: outOfBounds === 0 && minimumClearanceM >= 1 && minimumOpponentGapM >= 20,
    minimumClearanceM,
    minimumOpponentGapM,
    outOfBounds,
  };
}

function zombieCandidateAudit(stage: RawStage, boxes: Aabb[]): { pass: boolean; minimumFreeRatio: number } {
  const half = stage.mapSize / 2 - 2;
  let minimumFreeRatio = 1;
  for (const spawn of stage.playerSpawns) {
    let total = 0;
    let free = 0;
    for (const radius of [18, 22, 26, 30, 32]) {
      for (let index = 0; index < 72; index += 1) {
        const angle = index / 72 * Math.PI * 2;
        const x = Math.max(-half, Math.min(half, spawn[0] + Math.cos(angle) * radius));
        const z = Math.max(-half, Math.min(half, spawn[2] + Math.sin(angle) * radius));
        total += 1;
        if (boxes.every((box) => pointDistance(x, z, box) >= 0.6)) free += 1;
      }
    }
    minimumFreeRatio = Math.min(minimumFreeRatio, free / total);
  }
  return { pass: minimumFreeRatio >= 0.35, minimumFreeRatio };
}

const reports = [];
for (const [stageId, stage] of Object.entries(table)) {
  const def = definitions.get(stageId);
  assert(def, `${stageId}: missing StageDef`);
  const structures: Structure[] = [
    ...stage.landmarks.map((item) => ({ ...item, label: item.id })),
    ...stage.ordinaryDistricts.map((item, index) => ({ ...item, label: `${item.kind}-${index}` })),
  ];
  const boxes = structures.map(boxOf);
  const minimumPlayerStructureClearanceM = Math.min(
    ...stage.playerSpawns.map((spawn) => minStructureClearance(spawn, boxes)),
  );
  const minimumBotStructureClearanceM = Math.min(
    ...stage.botSpawns.map((spawn) => minStructureClearance(spawn, boxes)),
  );
  let structureGapViolations = 0;
  for (let index = 0; index < boxes.length; index += 1) {
    for (let other = index + 1; other < boxes.length; other += 1) {
      if (overlaps(boxes[index]!, boxes[other]!, 6)) structureGapViolations += 1;
    }
  }
  let primaryRoadViolations = 0;
  for (const road of stage.roads) {
    for (const box of boxes) if (overlaps(box, road.bounds, 6)) primaryRoadViolations += 1;
  }
  const ffaNearSpawnCount = stage.botSpawns.filter((spawn) => {
    const distance = pairDistance(stage.playerSpawns[0]!, spawn);
    return distance >= 60 && distance <= 120;
  }).length;
  const minimumTeamAnchorGapM = Math.min(
    ...stage.playerSpawns.flatMap((player) => stage.botSpawns.map((bot) => pairDistance(player, bot))),
  );
  const snd = stageId === 'renshujo'
    ? { pass: true, minimumClearanceM: null, minimumOpponentGapM: null, outOfBounds: 0 }
    : sndFormationAudit(stage, def.botCount, boxes);
  const zombie = zombieCandidateAudit(stage, boxes);
  const bfs = bfsAudit(stage, boxes);
  const failures: string[] = [];
  if (stage.status !== 'PASS') failures.push('source-no-ship');
  if (stage.landmarks.length !== 2) failures.push('landmark-count');
  if (minimumPlayerStructureClearanceM < 30 - 1e-6) failures.push('player-structure-clearance');
  if (minimumBotStructureClearanceM < 8 - 1e-6) failures.push('bot-structure-clearance');
  if (structureGapViolations > 0) failures.push('structure-firebreak');
  if (primaryRoadViolations > 0) failures.push('primary-road-capsule');
  if (ffaNearSpawnCount === 0 && stageId !== 'renshujo') failures.push('ffa-near-anchor');
  if (minimumTeamAnchorGapM < 20 && stageId !== 'renshujo') failures.push('team-anchor-separation');
  if (!snd.pass) failures.push('snd-formation');
  if (!zombie.pass) failures.push('zombie-ring-candidates');
  if (!bfs.reachable) failures.push('bfs-disconnected');
  reports.push({
    stageId,
    mapSize: stage.mapSize,
    sourceStageDefSize: def.size,
    playerSpawnCount: stage.playerSpawns.length,
    botSpawnCount: stage.botSpawns.length,
    landmarkCount: stage.landmarks.length,
    ordinaryDistrictCount: stage.ordinaryDistricts.length,
    minimumPlayerStructureClearanceM: Number(minimumPlayerStructureClearanceM.toFixed(3)),
    minimumBotStructureClearanceM: Number(minimumBotStructureClearanceM.toFixed(3)),
    structureGapViolations,
    primaryRoadViolations,
    ffaNearSpawnCount,
    minimumTeamAnchorGapM: Number(minimumTeamAnchorGapM.toFixed(3)),
    snd: {
      ...snd,
      minimumClearanceM: snd.minimumClearanceM === null ? null : Number(snd.minimumClearanceM.toFixed(3)),
      minimumOpponentGapM: snd.minimumOpponentGapM === null ? null : Number(snd.minimumOpponentGapM.toFixed(3)),
    },
    zombie: { pass: zombie.pass, minimumFreeRatio: Number(zombie.minimumFreeRatio.toFixed(3)) },
    bfs,
    releaseGate: failures.length === 0 ? 'PASS' : 'NO-SHIP',
    failures,
  });
}

const summary = {
  stageCount: reports.length,
  passStageIds: reports.filter((item) => item.releaseGate === 'PASS').map((item) => item.stageId),
  noShipStageIds: reports.filter((item) => item.releaseGate === 'NO-SHIP').map((item) => item.stageId),
  failureCounts: Object.fromEntries(
    [...new Set(reports.flatMap((item) => item.failures))]
      .sort()
      .map((code) => [code, reports.filter((item) => item.failures.includes(code)).length]),
  ),
};

assert.equal(reports.length, 31);
assert.equal(reports.reduce((sum, item) => sum + item.landmarkCount, 0), 62);
assert.equal(reports.reduce((sum, item) => sum + item.ordinaryDistrictCount, 0), 315);
assert.equal(summary.passStageIds.length, 31);
assert.deepEqual(summary.noShipStageIds, []);
assert.deepEqual(summary.failureCounts, {});

const outputPath = resolve(outputDir, 'mode-spawn-route-audit.json');
const output = `${JSON.stringify({ schemaVersion: '2.0.0', summary, stages: reports }, null, 2)}\n`;
await mkdir(outputDir, { recursive: true });
if (check) {
  let current = null;
  try {
    current = await readFile(outputPath, 'utf8');
  } catch {
    // The assertion below gives the same actionable drift message for a missing file.
  }
  assert.equal(
    current,
    output,
    'mode-spawn-route-audit.json drift; run ./node_modules/.bin/tsx tools/blender/audit-stage-placement-modes.ts',
  );
} else {
  await writeFile(outputPath, output);
}
console.log(JSON.stringify(summary, null, 2));
