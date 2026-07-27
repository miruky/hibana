#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '../..');
const DEFAULT_GENERATED_DIR = resolve(HERE, 'generated');
const DEFAULT_TYPESCRIPT_OUT = resolve(REPO_ROOT, 'src/game/generated/stage-placements.generated.ts');
const PROOF7 = new Set(['kairou', 'chikurin', 'setsugen', 'kouwan', 'sakyuu', 'z04', 'takadai']);
const GRID_M = 4;
const BOUNDARY_INSET_M = 4;
const PRIMARY_ROAD_WIDTH_M = 16;
const APPROACH_WIDTH_M = 12;
const CAPSULE_RADIUS_M = 6;
const PLAYER_SPAWN_CLEAR_M = 30;
const BOT_SPAWN_CLEAR_M = 8;
const ORDINARY_GAP_M = 6;
const EYE_HEIGHT_M = 1.65;
const MAX_TOTAL_COVERAGE = 0.48;
const TEAM_ANCHOR_GAP_M = 20;
const FFA_NEAR_MIN_M = 60;
const FFA_NEAR_MAX_M = 120;
const MODE_OBJECTIVE_CLEAR_M = 4;
const SND_SITE_CLEAR_M = 7;
const TRAINING_TARGET_CLEAR_M = 1;
const ZOMBIE_SHOP_CLEAR_M = 2;
const COLLISION_TEMPLATES = new Set(['abbey', 'courtyard', 'hall', 'bridge', 'vertical']);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function round(value, digits = 3) {
  const factor = 10 ** digits;
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
}

function sha256(value) {
  return createHash('sha256').update(value, 'utf8').digest('hex');
}

function normalizedAuditPayload(audit) {
  const { solverSha256: _ignored, ...payload } = audit;
  return stableStringify(payload);
}

// The layout document embeds its own placementSolverSha256 as provenance for
// downstream consumers (build_all_stages.py bakes it into manifest.json).
// That field must be excluded before hashing the layout: otherwise the hash
// of "the layout" depends on a value that is itself derived from the hash of
// "the layout", and no fixed point can exist (sha(layout containing X) == X
// has no general solution). Excluding it makes layoutsSha256 - and therefore
// solverSha256 - independent of whatever is currently stored in that field,
// so writing the computed solverSha256 back into it converges immediately.
function normalizedLayoutsPayload(layouts) {
  const { placementSolverSha256: _ignored, ...payload } = layouts;
  return stableStringify(payload);
}

function aabb(cx, cz, width, depth) {
  return {
    minX: cx - width / 2,
    maxX: cx + width / 2,
    minZ: cz - depth / 2,
    maxZ: cz + depth / 2,
  };
}

function expand(box, margin) {
  return {
    minX: box.minX - margin,
    maxX: box.maxX + margin,
    minZ: box.minZ - margin,
    maxZ: box.maxZ + margin,
  };
}

function overlaps(a, b, margin = 0) {
  return (
    a.minX - margin < b.maxX
    && a.maxX + margin > b.minX
    && a.minZ - margin < b.maxZ
    && a.maxZ + margin > b.minZ
  );
}

function contains(box, x, z) {
  return x >= box.minX && x <= box.maxX && z >= box.minZ && z <= box.maxZ;
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

function boundaryClearance(box, half) {
  return Math.min(box.minX + half, half - box.maxX, box.minZ + half, half - box.maxZ);
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

function approachLength(approach) {
  return Math.hypot(approach.start[0] - approach.end[0], approach.start[1] - approach.end[1]);
}

function signedBearingDeg(spawn, target) {
  const sx = spawn[0];
  const sz = spawn[2];
  const vx = -sx;
  const vz = -sz;
  const tx = target[0] - sx;
  const tz = target[1] - sz;
  const cross = vx * tz - vz * tx;
  const dot = vx * tx + vz * tz;
  return round(Math.atan2(cross, dot) * 180 / Math.PI);
}

function angularHeightDeg(spawn, target, height) {
  const distance = Math.max(0.001, Math.hypot(target[0] - spawn[0], target[1] - spawn[2]));
  return round(Math.atan2(height - EYE_HEIGHT_M, distance) * 180 / Math.PI);
}

function segmentBoxEntryT(start, end, box) {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  let t0 = 0;
  let t1 = 1;
  for (const [p, q] of [
    [-dx, start[0] - box.minX],
    [dx, box.maxX - start[0]],
    [-dz, start[1] - box.minZ],
    [dz, box.maxZ - start[1]],
  ]) {
    if (Math.abs(p) < 1e-9) {
      if (q < 0) return null;
      continue;
    }
    const r = q / p;
    if (p < 0) {
      if (r > t1) return null;
      if (r > t0) t0 = r;
    } else {
      if (r < t0) return null;
      if (r < t1) t1 = r;
    }
  }
  return t0;
}

function roadNetwork(mapSize) {
  const half = mapSize / 2;
  const roadHalf = PRIMARY_ROAD_WIDTH_M / 2;
  return [
    {
      id: 'primary-north-south',
      axis: 'z',
      centre: 0,
      width: PRIMARY_ROAD_WIDTH_M,
      bounds: { minX: -roadHalf, maxX: roadHalf, minZ: -half + BOUNDARY_INSET_M, maxZ: half - BOUNDARY_INSET_M },
    },
    {
      id: 'primary-east-west',
      axis: 'x',
      centre: 0,
      width: PRIMARY_ROAD_WIDTH_M,
      bounds: { minX: -half + BOUNDARY_INSET_M, maxX: half - BOUNDARY_INSET_M, minZ: -roadHalf, maxZ: roadHalf },
    },
  ];
}

function scaledSpawns(spawns, sourceSize, targetSize) {
  if (sourceSize === targetSize) return spawns.map((spawn) => [...spawn]);
  const scale = targetSize / sourceSize;
  return spawns.map(([x, y, z]) => [round(x * scale), y, round(z * scale)]);
}

function canonicalPrototype(landmark) {
  return {
    id: landmark.id,
    districtKind: landmark.collision.districtKind,
    collisionTemplate: landmark.collision.collisionTemplate,
    width: landmark.collision.collisionFootprintM.width,
    depth: landmark.collision.collisionFootprintM.depth,
    height: landmark.collision.heightM,
  };
}

function minimumPointDistance(spawns, footprint) {
  if (spawns.length === 0) return Infinity;
  return Math.min(...spawns.map(([x, , z]) => pointAabbDistance(x, z, footprint)));
}

function mulberry32(seed) {
  let state = seed | 0;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function zombieShopSlotKinds(seed) {
  const rand = mulberry32(seed);
  // generateShopLayout intentionally consumes one legacy perk-count draw,
  // then selects 4..6 optional walls. The remaining shuffles change identity,
  // not the placement-radius class used by this geometry reservation.
  rand();
  const optionalCount = 4 + Math.floor(rand() * 3);
  return [
    ...Array.from({ length: 2 + optionalCount }, () => 'wall-buy'),
    ...Array.from({ length: 6 }, () => 'perk-machine'),
    'mystery-box',
    'pack-a-punch',
    'door',
  ];
}

function fixedModeReservations(mapSize, layout) {
  const points = [];
  const add = (id, x, z, clearanceM, contract) => points.push({
    id, x: round(x), z: round(z), clearanceM, contract,
  });
  const zombieOnly = /^z\d\d$/.test(layout.id);
  const trainingOnly = layout.id === 'renshujo';
  if (!zombieOnly && !trainingOnly) {
    // Exact current runtime formulae from Match.buildZones,
    // Match.buildHardpointZones, and StoryEngine.buildSndSites. Zombie and
    // training maps are excluded by stagesForMode and reserve their own live
    // contracts below instead of fictional unreachable-mode objectives.
    add('dom-a', -mapSize * 0.3, mapSize * 0.12, MODE_OBJECTIVE_CLEAR_M, 'match.buildZones');
    add('dom-b', 0, 0, MODE_OBJECTIVE_CLEAR_M, 'match.buildZones');
    add('dom-c', mapSize * 0.3, -mapSize * 0.12, MODE_OBJECTIVE_CLEAR_M, 'match.buildZones');
    for (const [id, x, z] of [
      ['hardpoint-0', -mapSize * 0.28, mapSize * 0.1],
      ['hardpoint-1', mapSize * 0.18, -mapSize * 0.22],
      ['hardpoint-2', mapSize * 0.3, mapSize * 0.15],
      ['hardpoint-3', -mapSize * 0.15, mapSize * 0.28],
      ['hardpoint-4', 0, 0],
    ]) add(id, x, z, MODE_OBJECTIVE_CLEAR_M, 'match.buildHardpointZones');
    add('snd-site-a', -mapSize * 0.3, mapSize * 0.12, SND_SITE_CLEAR_M, 'story.buildSndSites');
    add('snd-site-b', mapSize * 0.3, -mapSize * 0.12, SND_SITE_CLEAR_M, 'story.buildSndSites');
    // CTF is defined as pure state but is not yet wired into Match/MODE_IDS.
    // Reserve the proven Domination A/C bases as an explicit forward-compatible
    // projection; the audit records that this is not represented as live wiring.
    add('ctf-player-base-projection', -mapSize * 0.3, mapSize * 0.12, MODE_OBJECTIVE_CLEAR_M, 'ctf-unwired/dom-a-c-projection');
    add('ctf-enemy-base-projection', mapSize * 0.3, -mapSize * 0.12, MODE_OBJECTIVE_CLEAR_M, 'ctf-unwired/dom-a-c-projection');
  }
  return points;
}

function flexibleModeReservationGroups(mapSize, layout) {
  if (!/^z\d\d$/.test(layout.id)) return [];
  const groups = [];
  const offsets = [0, 0.22, -0.22, 0.44, -0.44];
  const addGroup = (id, baseAngle, radius, contract) => groups.push({
    id,
    clearanceM: ZOMBIE_SHOP_CLEAR_M,
    contract,
    alternatives: offsets.map((offset, index) => ({
      id: `${id}-offset-${index}`,
      x: round(Math.cos(baseAngle + offset) * radius),
      z: round(Math.sin(baseAngle + offset) * radius),
    })),
  });
  const kinds = zombieShopSlotKinds(layout.seed);
  for (const [index, kind] of kinds.entries()) {
    // The mystery group is immediately moved to boxPositions[0] after build;
    // its transient construction coordinate is not a live objective.
    if (kind === 'mystery-box') continue;
    const angle = index / kinds.length * Math.PI * 2 + layout.seed * 0.01;
    const radius = kind === 'wall-buy' ? mapSize * 0.36
      : kind === 'door' ? mapSize * 0.4
        : kind === 'perk-machine' ? mapSize * 0.26
          : mapSize * 0.16;
    addGroup(`zombie-shop-${index}-${kind}`, angle, radius, 'zombie.findShopGroundPos');
  }
  for (const [index, angle] of [0.1, 1.3, 2.5, 3.8, 5.1].entries()) {
    addGroup(`zombie-mystery-relocation-${index}`, angle + layout.seed * 0.01, mapSize * 0.15, 'zombie.boxPositions/findShopGroundPos');
  }
  return groups;
}

function flexibleGroupsViable(footprints, groups) {
  return groups.every((group) => group.alternatives.some((point) => (
    footprints.every((box) => pointAabbDistance(point.x, point.z, box) >= group.clearanceM - 1e-6)
  )));
}

function modeReservationsClear(footprint, reservations) {
  return reservations.every((point) => pointAabbDistance(point.x, point.z, footprint) >= point.clearanceM - 1e-6);
}

function candidateForSide(prototype, side, parallel, length, half, viewSpawn, roads, reservations, tie) {
  const width = prototype.orientedWidth ?? prototype.width;
  const depth = prototype.orientedDepth ?? prototype.depth;
  const roadHalf = PRIMARY_ROAD_WIDTH_M / 2;
  let cx;
  let cz;
  let entrance;
  let start;
  let direction;
  if (side === 'west') {
    const endX = -roadHalf - length;
    cx = endX - 0.8 - width / 2;
    cz = parallel;
    entrance = [endX, parallel];
    start = [-roadHalf, parallel];
    direction = [1, 0];
  } else if (side === 'east') {
    const endX = roadHalf + length;
    cx = endX + 0.8 + width / 2;
    cz = parallel;
    entrance = [endX, parallel];
    start = [roadHalf, parallel];
    direction = [-1, 0];
  } else if (side === 'south') {
    const endZ = -roadHalf - length;
    cx = parallel;
    cz = endZ - 0.8 - depth / 2;
    entrance = [parallel, endZ];
    start = [parallel, -roadHalf];
    direction = [0, 1];
  } else {
    const endZ = roadHalf + length;
    cx = parallel;
    cz = endZ + 0.8 + depth / 2;
    entrance = [parallel, endZ];
    start = [parallel, roadHalf];
    direction = [0, -1];
  }
  cx = round(cx);
  cz = round(cz);
  entrance = entrance.map((value) => round(value));
  start = start.map((value) => round(value));
  const footprint = aabb(cx, cz, width, depth);
  const approach = { start, end: entrance, width: APPROACH_WIDTH_M };
  const route = routeAabb(approach);
  if (boundaryClearance(footprint, half) < BOUNDARY_INSET_M - 1e-6) return null;
  if (boundaryClearance(route, half) < -1e-6) return null;
  if (roads.some((road) => overlaps(footprint, road.bounds, CAPSULE_RADIUS_M))) return null;
  if (!modeReservationsClear(footprint, reservations)) return null;
  const firstBearing = signedBearingDeg(viewSpawn, [cx, cz]);
  const clear = boundaryClearance(footprint, half);
  const score = Math.abs(firstBearing) * 1.7
    + Math.abs(length - 20) * 0.4
    + Math.hypot(cx, cz) * 0.025
    - clear * 0.015
    + tie * 0.000001;
  return {
    ...prototype,
    cx,
    cz,
    rot: prototype.rot ?? 0,
    entrance,
    entranceDirection: direction,
    approach,
    footprint,
    route,
    side,
    score,
    boundaryClearance: round(clear),
    firstBearing,
  };
}

function landmarkCandidates(prototype, mapSize, viewSpawn, roads, reservations, serial) {
  const half = mapSize / 2;
  const candidates = [];
  const lengths = [20, 24, 28, 32];
  let tie = serial * 1000000;
  // The runtime adapter currently validates width/depth as world AABB extents
  // and does not rotate the footprint. Until that contract changes, emitting a
  // quarter-turn would make solver geometry and runtime geometry disagree.
  for (const rot of [0]) {
    const oriented = {
      ...prototype,
      rot,
      orientedWidth: rot & 1 ? prototype.depth : prototype.width,
      orientedDepth: rot & 1 ? prototype.width : prototype.depth,
    };
    for (const side of ['west', 'east', 'south', 'north']) {
      const parallelHalf = side === 'west' || side === 'east' ? oriented.orientedDepth / 2 : oriented.orientedWidth / 2;
      const exactMin = -half + BOUNDARY_INSET_M + parallelHalf;
      const exactMax = half - BOUNDARY_INSET_M - parallelHalf;
      const min = Math.ceil(exactMin / GRID_M) * GRID_M;
      const max = Math.floor(exactMax / GRID_M) * GRID_M;
      const parallelValues = [round(exactMin), round(exactMax)];
      for (let parallel = min; parallel <= max; parallel += GRID_M) parallelValues.push(parallel);
      const uniqueParallelValues = [...new Set(parallelValues)].sort((a, b) => a - b);
      for (const length of lengths) {
        for (const parallel of uniqueParallelValues) {
          tie += 1;
          const candidate = candidateForSide(
            oriented,
            side,
            parallel,
            length,
            half,
            viewSpawn,
            roads,
            reservations,
            tie,
          );
          if (candidate) candidates.push(candidate);
        }
      }
    }
  }
  candidates.sort((a, b) => a.score - b.score || a.cx - b.cx || a.cz - b.cz || a.side.localeCompare(b.side));
  return candidates.slice(0, 320);
}

function buildPlayerSpawns(mapSize, pair) {
  const half = mapSize / 2;
  const raw = [];
  const append = (x, z) => {
    const point = [round(x), 0, round(z)];
    if (pair.landmarks.some((landmark) => pointAabbDistance(point[0], point[2], landmark.footprint) < PLAYER_SPAWN_CLEAR_M)) return;
    raw.push(point);
  };
  for (const travel of [-half + 12, half - 12]) {
    append(0, travel);
    append(travel, 0);
  }
  for (let travel = -half + 24; travel <= half - 24; travel += 12) {
    append(0, travel);
    append(travel, 0);
  }
  raw.sort((a, b) => {
    const aBearing = Math.max(...pair.landmarks.map((landmark) => Math.abs(signedBearingDeg(a, [landmark.cx, landmark.cz]))));
    const bBearing = Math.max(...pair.landmarks.map((landmark) => Math.abs(signedBearingDeg(b, [landmark.cx, landmark.cz]))));
    return aBearing - bBearing
      || Math.hypot(b[0], b[2]) - Math.hypot(a[0], a[2])
      || a[0] - b[0]
      || a[2] - b[2];
  });
  const result = [];
  for (const spawn of raw) {
    if (result.some((other) => Math.hypot(spawn[0] - other[0], spawn[2] - other[2]) < 40)) continue;
    result.push(spawn);
    if (result.length === 4) break;
  }
  return result.length === 4 ? result : null;
}

function trainingTargetReservations(playerSpawns, stageId) {
  if (stageId !== 'renshujo' || playerSpawns.length === 0) return [];
  const spawn = playerSpawns[0];
  const length = Math.hypot(spawn[0], spawn[2]);
  const forward = length > 0.01 ? [-spawn[0] / length, -spawn[2] / length] : [0, -1];
  const right = [-forward[1], forward[0]];
  const points = [];
  const add = (id, offset, distance, clearanceM = TRAINING_TARGET_CLEAR_M) => points.push({
    id,
    x: round(spawn[0] + forward[0] * distance + right[0] * offset),
    z: round(spawn[2] + forward[1] * distance + right[1] * offset),
    clearanceM,
    contract: 'training-range.create',
  });
  [5, 10, 20, 30, 50].forEach((distance, index) => add(`training-static-${index}`, (index - 2) * 3, distance));
  [1, 2, 3].forEach((_, index) => {
    const offset = (index - 1) * 4;
    // Moving targets traverse +/-3.5m along the local right axis.
    for (let sweep = -3.5; sweep <= 3.5 + 1e-9; sweep += 0.5) {
      add(`training-moving-${index}-${round(sweep, 1)}`, offset + sweep, 15);
    }
  });
  for (let index = 0; index < 4; index += 1) add(`training-popup-${index}`, (index - 1.5) * 2, 8);
  return points;
}

function makeSndSpawnFormation(anchor, count, spacing = 2.4) {
  if (count <= 0) return [];
  const dx = -anchor[0];
  const dz = -anchor[2];
  const length = Math.hypot(dx, dz);
  const forwardX = length > 1e-5 ? dx / length : 0;
  const forwardZ = length > 1e-5 ? dz / length : -1;
  const rightX = -forwardZ;
  const rightZ = forwardX;
  const result = [];
  let cursor = 0;
  let row = 0;
  while (cursor < count) {
    const rowCount = Math.min(3, count - cursor);
    const rowWidth = (rowCount - 1) * spacing;
    const inward = 1.5 + row * spacing;
    for (let column = 0; column < rowCount; column += 1) {
      const lateral = column * spacing - rowWidth / 2;
      result.push([
        anchor[0] + forwardX * inward + rightX * lateral,
        anchor[1],
        anchor[2] + forwardZ * inward + rightZ * lateral,
      ]);
      cursor += 1;
    }
    row += 1;
  }
  return result;
}

function buildBotSpawns(mapSize, count, pair, districts, playerSpawns, botCount) {
  const half = mapSize / 2;
  const candidates = [];
  for (let travel = -half + 12; travel <= half - 12; travel += 10) {
    candidates.push([0, 0, round(travel)], [round(travel), 0, 0]);
  }
  // Dense maps can legitimately consume long sections of the two primary
  // roads. Keep roads first, then draw from measured open cells throughout
  // the connected town plan instead of weakening the 30 m landmark clearance.
  const openGrid = [];
  for (let z = -half + 12; z <= half - 12; z += 4) {
    for (let x = -half + 12; x <= half - 12; x += 4) {
      openGrid.push([round(x), 0, round(z)]);
    }
  }
  openGrid.sort((a, b) => {
    const aFromFirst = Math.hypot(a[0] - playerSpawns[0][0], a[2] - playerSpawns[0][2]);
    const bFromFirst = Math.hypot(b[0] - playerSpawns[0][0], b[2] - playerSpawns[0][2]);
    const aBand = aFromFirst >= FFA_NEAR_MIN_M && aFromFirst <= FFA_NEAR_MAX_M ? 0 : 1;
    const bBand = bFromFirst >= FFA_NEAR_MIN_M && bFromFirst <= FFA_NEAR_MAX_M ? 0 : 1;
    if (aBand !== bBand) return aBand - bBand;
    const aRoadDistance = Math.min(Math.abs(a[0]), Math.abs(a[2]));
    const bRoadDistance = Math.min(Math.abs(b[0]), Math.abs(b[2]));
    return aRoadDistance - bRoadDistance
      || Math.hypot(a[0], a[2]) - Math.hypot(b[0], b[2])
      || a[0] - b[0]
      || a[2] - b[2];
  });
  candidates.push(...openGrid);
  const uniqueCandidates = [...new Map(candidates.map((point) => [`${point[0]}:${point[2]}`, point])).values()];
  uniqueCandidates.sort((a, b) => {
    const aFromFirst = Math.hypot(a[0] - playerSpawns[0][0], a[2] - playerSpawns[0][2]);
    const bFromFirst = Math.hypot(b[0] - playerSpawns[0][0], b[2] - playerSpawns[0][2]);
    const aBand = aFromFirst >= FFA_NEAR_MIN_M && aFromFirst <= FFA_NEAR_MAX_M ? 0 : 1;
    const bBand = bFromFirst >= FFA_NEAR_MIN_M && bFromFirst <= FFA_NEAR_MAX_M ? 0 : 1;
    return aBand - bBand
      || Math.min(Math.abs(a[0]), Math.abs(a[2])) - Math.min(Math.abs(b[0]), Math.abs(b[2]))
      || aFromFirst - bFromFirst
      || a[0] - b[0]
      || a[2] - b[2];
  });
  const result = [];
  const structures = [
    ...pair.landmarks.map((landmark) => landmark.footprint),
    ...districts.map((district) => aabb(district.cx, district.cz, district.width, district.depth)),
  ];
  const allyCount = Math.max(0, Math.floor((botCount - 1) / 2));
  const maximumFormationMembers = Math.max(1 + allyCount, Math.max(1, botCount - allyCount));
  for (const spawn of uniqueCandidates) {
    const [x, , z] = spawn;
    if (playerSpawns.some((player) => Math.hypot(x - player[0], z - player[2]) < 32)) continue;
    if (result.some((other) => Math.hypot(x - other[0], z - other[2]) < 5)) continue;
    if (structures.some((footprint) => pointAabbDistance(x, z, footprint) < BOT_SPAWN_CLEAR_M)) continue;
    const formation = makeSndSpawnFormation(spawn, maximumFormationMembers);
    if (formation.some((point) => Math.abs(point[0]) > half - 0.5 || Math.abs(point[2]) > half - 0.5)) continue;
    if (formation.some((point) => structures.some((footprint) => pointAabbDistance(point[0], point[2], footprint) < 1))) continue;
    result.push(spawn);
    if (result.length === count) break;
  }
  if (result.length !== count) return null;
  const hasFfaNear = result.some((spawn) => {
    const distance = Math.hypot(spawn[0] - playerSpawns[0][0], spawn[2] - playerSpawns[0][2]);
    return distance >= FFA_NEAR_MIN_M && distance <= FFA_NEAR_MAX_M;
  });
  return hasFfaNear ? result : null;
}

function pairCandidates(first, second, flexibleReservations) {
  const pairs = [];
  for (const a of first) {
    for (const b of second) {
      const gap = aabbGap(a.footprint, b.footprint);
      if (gap < ORDINARY_GAP_M - 1e-6) continue;
      if (overlaps(a.route, b.footprint, 2) || overlaps(b.route, a.footprint, 2)) continue;
      if (!flexibleGroupsViable([a.footprint, b.footprint], flexibleReservations)) continue;
      const bearingSeparation = Math.abs(a.firstBearing - b.firstBearing);
      const sameSidePenalty = a.side === b.side ? 20 : 0;
      const crowdingPenalty = Math.max(0, 10 - bearingSeparation) * 2;
      pairs.push({
        landmarks: [a, b],
        gap,
        score: a.score + b.score + sameSidePenalty + crowdingPenalty,
      });
    }
  }
  pairs.sort((a, b) => a.score - b.score || b.gap - a.gap);
  return pairs.slice(0, 120);
}

const DEFAULT_KIND_HEIGHT = {
  arena: 14,
  hangar: 16,
  tower: 32,
  warehouse: 12,
  cathedral: 28,
  bunker: 14,
  terminal: 18,
  refinery: 30,
  villa: 18,
  pagoda: 30,
  fortress: 24,
  station: 18,
  checkpoint: 14,
  metro: 15,
  abbey: 34,
};

function sourceOrdinaryDistricts(layout) {
  const landmarkKeys = new Set((layout.landmarkPlacements ?? []).map((landmark) => (
    `${landmark.cx}:${landmark.cz}:${landmark.width}:${landmark.depth}`
  )));
  const raw = layout.districtPlacements.filter((district) => !landmarkKeys.has(
    `${district.cx}:${district.cz}:${district.width}:${district.depth}`,
  ));
  return raw.map((district, index) => {
    const footprint = aabb(district.cx, district.cz, district.width, district.depth);
    let height = 0;
    for (const box of layout.boxes) {
      if (box.district !== district.kind || box.landmarkId || box.ghost || box.decor) continue;
      if (!contains(expand(footprint, 1), box.x, box.z)) continue;
      height = Math.max(height, box.y + box.h / 2);
    }
    return {
      sourceIndex: index,
      kind: district.kind,
      cx: district.cx,
      cz: district.cz,
      rot: district.rot,
      width: district.width,
      depth: district.depth,
      height: round(height || DEFAULT_KIND_HEIGHT[district.kind] || 16),
    };
  });
}

function localDimensions(district) {
  return district.rot & 1
    ? [district.depth, district.width]
    : [district.width, district.depth];
}

function districtCandidateValid(candidate, occupied, approaches, roads, playerSpawns, botSpawns, half, visibilityTargets, reservations, flexibleReservations) {
  const footprint = aabb(candidate.cx, candidate.cz, candidate.width, candidate.depth);
  if (boundaryClearance(footprint, half) < BOUNDARY_INSET_M - 1e-6) return false;
  if (roads.some((road) => overlaps(footprint, road.bounds, CAPSULE_RADIUS_M))) return false;
  if (occupied.some((other) => overlaps(footprint, other, ORDINARY_GAP_M))) return false;
  if (approaches.some((route) => overlaps(footprint, route, 0))) return false;
  if (minimumPointDistance(playerSpawns, footprint) < PLAYER_SPAWN_CLEAR_M) return false;
  if (minimumPointDistance(botSpawns, footprint) < BOT_SPAWN_CLEAR_M) return false;
  if (!modeReservationsClear(footprint, reservations)) return false;
  if (!flexibleGroupsViable([...occupied, footprint], flexibleReservations)) return false;
  for (const { spawn, target } of visibilityTargets) {
    const entry = segmentBoxEntryT([spawn[0], spawn[2]], [target.cx, target.cz], footprint);
    if (entry === null || entry <= 0.001 || entry >= 0.999) continue;
    const sightHeight = EYE_HEIGHT_M + (target.height * 0.92 - EYE_HEIGHT_M) * entry;
    if (candidate.height >= sightHeight - 0.5) return false;
  }
  candidate.footprint = footprint;
  return true;
}

function packOrdinaryDistricts(sourceDistricts, pair, roads, playerSpawns, botSpawns, mapSize, strategy, reservations, flexibleReservations) {
  const half = mapSize / 2;
  const occupied = pair.landmarks.map((landmark) => landmark.footprint);
  const approaches = pair.landmarks.map((landmark) => landmark.route);
  const visibilityTargets = pair.landmarks.map((target) => ({ spawn: playerSpawns[0], target }));
  const districts = sourceDistricts.map((district) => ({ ...district }));
  if (strategy === 0 || strategy === 1) {
    districts.sort((a, b) => b.width * b.depth - a.width * a.depth || a.sourceIndex - b.sourceIndex);
  } else if (strategy === 2) {
    districts.sort((a, b) => a.sourceIndex - b.sourceIndex);
  } else {
    districts.sort((a, b) => b.height - a.height || b.width * b.depth - a.width * a.depth);
  }
  const placed = [];
  for (const district of districts) {
    const [localW, localD] = localDimensions(district);
    const scale = mapSize / Math.max(1, strategy === 1 ? mapSize : mapSize);
    let best = null;
    const rotations = [district.rot, district.rot + 1, district.rot + 2, district.rot + 3]
      .map((value) => value & 3)
      .filter((value, index, values) => values.indexOf(value) === index);
    for (const rot of rotations) {
      const [width, depth] = rot & 1 ? [localD, localW] : [localW, localD];
      const minX = Math.ceil((-half + BOUNDARY_INSET_M + width / 2) / GRID_M) * GRID_M;
      const maxX = Math.floor((half - BOUNDARY_INSET_M - width / 2) / GRID_M) * GRID_M;
      const minZ = Math.ceil((-half + BOUNDARY_INSET_M + depth / 2) / GRID_M) * GRID_M;
      const maxZ = Math.floor((half - BOUNDARY_INSET_M - depth / 2) / GRID_M) * GRID_M;
      for (let z = minZ; z <= maxZ; z += GRID_M) {
        for (let x = minX; x <= maxX; x += GRID_M) {
          const candidate = {
            sourceIndex: district.sourceIndex,
            kind: district.kind,
            cx: x,
            cz: z,
            rot,
            width,
            depth,
            height: district.height,
          };
          if (!districtCandidateValid(candidate, occupied, approaches, roads, playerSpawns, botSpawns, half, visibilityTargets, reservations, flexibleReservations)) continue;
          const preserveDistance = Math.hypot(x - district.cx * scale, z - district.cz * scale);
          const quadrantBias = strategy === 1
            ? -Math.hypot(x, z) * 0.06
            : strategy === 3
              ? Math.abs(Math.abs(x) - Math.abs(z)) * 0.08
              : 0;
          const rotationPenalty = rot === district.rot ? 0 : 3;
          const deterministicTie = (district.sourceIndex * 17 + (x + half) * 3 + (z + half) * 5 + rot) * 1e-7;
          const score = preserveDistance + quadrantBias + rotationPenalty + deterministicTie;
          if (!best || score < best.score) best = { ...candidate, score };
        }
      }
    }
    if (!best) {
      return { status: 'FAIL', reason: `ordinary-district-${district.sourceIndex}-${district.kind}-unplaceable`, districts: placed };
    }
    occupied.push(best.footprint);
    placed.push(best);
  }
  placed.sort((a, b) => a.sourceIndex - b.sourceIndex);
  return {
    status: 'PASS',
    districts: placed.map(({ score: _score, footprint: _footprint, ...district }) => district),
  };
}

function lineOfSight(spawn, target, obstacles) {
  const start = [spawn[0], spawn[2]];
  const end = [target.cx, target.cz];
  const blockers = [];
  for (const obstacle of obstacles) {
    const entry = segmentBoxEntryT(start, end, obstacle.footprint);
    if (entry === null || entry <= 0.001 || entry >= 0.999) continue;
    const sightHeight = EYE_HEIGHT_M + (target.height * 0.92 - EYE_HEIGHT_M) * entry;
    if (obstacle.height >= sightHeight - 0.5) {
      blockers.push({ id: obstacle.id, entryT: round(entry), obstacleHeightM: obstacle.height, sightHeightM: round(sightHeight) });
    }
  }
  return { visible: blockers.length === 0, blockers };
}

function navigationAudit(mapSize, pair, districts, playerSpawns, botSpawns) {
  const half = mapSize / 2;
  const min = -half + CAPSULE_RADIUS_M;
  const max = half - CAPSULE_RADIUS_M;
  const step = 2;
  const count = Math.floor((max - min) / step) + 1;
  const obstacles = [
    ...pair.landmarks.map((landmark) => landmark.footprint),
    ...districts.map((district) => aabb(district.cx, district.cz, district.width, district.depth)),
  ].map((box) => expand(box, CAPSULE_RADIUS_M));
  const blocked = new Uint8Array(count * count);
  const indexOf = (ix, iz) => iz * count + ix;
  for (let iz = 0; iz < count; iz += 1) {
    const z = min + iz * step;
    for (let ix = 0; ix < count; ix += 1) {
      const x = min + ix * step;
      if (obstacles.some((box) => contains(box, x, z))) blocked[indexOf(ix, iz)] = 1;
    }
  }
  const nearestOpen = ([x, z]) => {
    const rawX = Math.max(0, Math.min(count - 1, Math.round((x - min) / step)));
    const rawZ = Math.max(0, Math.min(count - 1, Math.round((z - min) / step)));
    for (let radius = 0; radius <= 6; radius += 1) {
      for (let dz = -radius; dz <= radius; dz += 1) {
        for (let dx = -radius; dx <= radius; dx += 1) {
          if (Math.max(Math.abs(dx), Math.abs(dz)) !== radius) continue;
          const ix = rawX + dx;
          const iz = rawZ + dz;
          if (ix < 0 || iz < 0 || ix >= count || iz >= count) continue;
          const index = indexOf(ix, iz);
          if (!blocked[index]) return { index, ix, iz, distanceM: round(Math.hypot(dx, dz) * step) };
        }
      }
    }
    return null;
  };
  const start = nearestOpen([playerSpawns[0][0], playerSpawns[0][2]]);
  if (!start) return { reachable: false, reason: 'first-spawn-has-no-capsule-cell' };
  const seen = new Uint8Array(count * count);
  const queue = new Int32Array(count * count);
  let head = 0;
  let tail = 0;
  queue[tail++] = start.index;
  seen[start.index] = 1;
  const moves = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (head < tail) {
    const current = queue[head++];
    const ix = current % count;
    const iz = Math.floor(current / count);
    for (const [dx, dz] of moves) {
      const nx = ix + dx;
      const nz = iz + dz;
      if (nx < 0 || nz < 0 || nx >= count || nz >= count) continue;
      const next = indexOf(nx, nz);
      if (blocked[next] || seen[next]) continue;
      seen[next] = 1;
      queue[tail++] = next;
    }
  }
  const targets = [
    ...playerSpawns.map(([x, , z], index) => ({ id: `player-spawn-${index}`, point: [x, z] })),
    ...botSpawns.map(([x, , z], index) => ({ id: `bot-spawn-${index}`, point: [x, z] })),
    ...pair.landmarks.map((landmark) => ({ id: `${landmark.id}-approach-start`, point: landmark.approach.start })),
  ];
  const targetResults = targets.map((target) => {
    const cell = nearestOpen(target.point);
    return {
      id: target.id,
      snappedDistanceM: cell?.distanceM ?? null,
      reachable: Boolean(cell && seen[cell.index]),
    };
  });
  return {
    reachable: targetResults.every((target) => target.reachable && target.snappedDistanceM <= 6),
    gridStepM: step,
    capsuleDiameterM: CAPSULE_RADIUS_M * 2,
    visitedCells: tail,
    targetResults,
  };
}

function minimumStructureClearance(points, footprints) {
  if (points.length === 0 || footprints.length === 0) return Infinity;
  return Math.min(...points.flatMap((point) => footprints.map((box) => pointAabbDistance(point[0], point[2], box))));
}

function runtimeModeAudit(layout, mapSize, pair, districts, roads, playerSpawns, botSpawns, reservations, flexibleReservations) {
  const half = mapSize / 2;
  const footprints = [
    ...pair.landmarks.map((landmark) => landmark.footprint),
    ...districts.map((district) => aabb(district.cx, district.cz, district.width, district.depth)),
  ];
  const minimumPlayerStructureClearanceM = minimumStructureClearance(playerSpawns, footprints);
  const minimumBotStructureClearanceM = minimumStructureClearance(botSpawns, footprints);
  let structureGapViolations = 0;
  for (let index = 0; index < footprints.length; index += 1) {
    for (let other = index + 1; other < footprints.length; other += 1) {
      if (overlaps(footprints[index], footprints[other], ORDINARY_GAP_M)) structureGapViolations += 1;
    }
  }
  let primaryRoadViolations = 0;
  for (const road of roads) for (const box of footprints) if (overlaps(box, road.bounds, CAPSULE_RADIUS_M)) primaryRoadViolations += 1;
  const ffaNearSpawnCount = botSpawns.filter((spawn) => {
    const distance = Math.hypot(spawn[0] - playerSpawns[0][0], spawn[2] - playerSpawns[0][2]);
    return distance >= FFA_NEAR_MIN_M && distance <= FFA_NEAR_MAX_M;
  }).length;
  const minimumTeamAnchorGapM = playerSpawns.length > 0 && botSpawns.length > 0
    ? Math.min(...playerSpawns.flatMap((player) => botSpawns.map((bot) => Math.hypot(player[0] - bot[0], player[2] - bot[2]))))
    : Infinity;

  let sndMinimumClearanceM = Infinity;
  let sndMinimumOpponentGapM = Infinity;
  let sndOutOfBounds = 0;
  if (layout.id !== 'renshujo') {
    const allyCount = Math.max(0, Math.floor((layout.botCount - 1) / 2));
    const playerMembers = 1 + allyCount;
    const enemyMembers = Math.max(1, layout.botCount - allyCount);
    for (let roundIndex = 0; roundIndex < 8; roundIndex += 1) {
      const attackFromPlayerSide = roundIndex < 4;
      const playerCandidates = attackFromPlayerSide ? playerSpawns : botSpawns;
      const enemyCandidates = attackFromPlayerSide ? botSpawns : playerSpawns;
      const playerAnchor = playerCandidates[roundIndex % Math.max(1, playerCandidates.length)] ?? [0, 0, 0];
      let enemyAnchor = enemyCandidates[0] ?? [0, 0, 0];
      let farthestSq = -1;
      for (const candidate of enemyCandidates) {
        const distanceSq = (candidate[0] - playerAnchor[0]) ** 2 + (candidate[2] - playerAnchor[2]) ** 2;
        if (distanceSq > farthestSq) {
          farthestSq = distanceSq;
          enemyAnchor = candidate;
        }
      }
      const playerFormation = makeSndSpawnFormation(playerAnchor, playerMembers);
      const enemyFormation = makeSndSpawnFormation(enemyAnchor, enemyMembers);
      for (const point of [...playerFormation, ...enemyFormation]) {
        if (Math.abs(point[0]) > half - 0.5 || Math.abs(point[2]) > half - 0.5) sndOutOfBounds += 1;
        sndMinimumClearanceM = Math.min(sndMinimumClearanceM, ...footprints.map((box) => pointAabbDistance(point[0], point[2], box)));
      }
      for (const player of playerFormation) {
        for (const enemy of enemyFormation) {
          sndMinimumOpponentGapM = Math.min(sndMinimumOpponentGapM, Math.hypot(player[0] - enemy[0], player[2] - enemy[2]));
        }
      }
    }
  }
  const sndPass = layout.id === 'renshujo'
    || (sndOutOfBounds === 0 && sndMinimumClearanceM >= 1 - 1e-6 && sndMinimumOpponentGapM >= 20 - 1e-6);

  let zombieMinimumFreeRatio = 1;
  for (const spawn of playerSpawns) {
    let total = 0;
    let free = 0;
    for (const radius of [18, 22, 26, 30, 32]) {
      for (let index = 0; index < 72; index += 1) {
        const angle = index / 72 * Math.PI * 2;
        const x = Math.max(-half + 2, Math.min(half - 2, spawn[0] + Math.cos(angle) * radius));
        const z = Math.max(-half + 2, Math.min(half - 2, spawn[2] + Math.sin(angle) * radius));
        total += 1;
        if (footprints.every((box) => pointAabbDistance(x, z, box) >= 0.6)) free += 1;
      }
    }
    zombieMinimumFreeRatio = Math.min(zombieMinimumFreeRatio, free / total);
  }

  const reservationResults = reservations.map((point) => {
    const clearanceM = Math.min(...footprints.map((box) => pointAabbDistance(point.x, point.z, box)));
    return { ...point, actualClearanceM: round(clearanceM), pass: clearanceM >= point.clearanceM - 1e-6 };
  });
  const flexibleReservationResults = flexibleReservations.map((group) => {
    const candidates = group.alternatives.map((point) => {
      const clearanceM = Math.min(...footprints.map((box) => pointAabbDistance(point.x, point.z, box)));
      return { ...point, actualClearanceM: round(clearanceM), pass: clearanceM >= group.clearanceM - 1e-6 };
    });
    const selectedIndex = candidates.findIndex((candidate) => candidate.pass);
    return {
      id: group.id,
      contract: group.contract,
      requiredClearanceM: group.clearanceM,
      selectedIndex,
      selected: selectedIndex >= 0 ? candidates[selectedIndex] : null,
      pass: selectedIndex >= 0,
      candidates,
    };
  });
  const first = playerSpawns[0] ?? [0, 0, 0];
  let exfil = first;
  let farthest = -1;
  for (const candidate of [...playerSpawns, ...botSpawns]) {
    const distance = Math.hypot(candidate[0] - first[0], candidate[2] - first[2]);
    if (distance > farthest) { farthest = distance; exfil = candidate; }
  }
  const campaignPoints = [
    { id: 'campaign-extract-infiltrate', point: exfil },
    { id: 'campaign-escort-start', point: playerSpawns[1] ?? first },
    { id: 'campaign-escort-mid', point: [0, 0, 0] },
    { id: 'campaign-escort-goal', point: exfil },
    ...botSpawns.map((point, index) => ({ id: `campaign-defend-collect-${index}`, point })),
  ].map((item) => ({
    id: item.id,
    clearanceM: round(Math.min(...footprints.map((box) => pointAabbDistance(item.point[0], item.point[2], box)))),
  }));
  const campaignPass = campaignPoints.every((item) => item.clearanceM >= 1 - 1e-6);
  const failures = [];
  if (minimumPlayerStructureClearanceM < PLAYER_SPAWN_CLEAR_M - 1e-6) failures.push('player-structure-clearance');
  if (minimumBotStructureClearanceM < BOT_SPAWN_CLEAR_M - 1e-6) failures.push('bot-structure-clearance');
  if (structureGapViolations > 0) failures.push('structure-firebreak');
  if (primaryRoadViolations > 0) failures.push('primary-road-capsule');
  if (layout.id !== 'renshujo' && ffaNearSpawnCount === 0) failures.push('ffa-near-anchor');
  if (layout.id !== 'renshujo' && minimumTeamAnchorGapM < TEAM_ANCHOR_GAP_M - 1e-6) failures.push('team-anchor-separation');
  if (!sndPass) failures.push('snd-formation');
  if (zombieMinimumFreeRatio < 0.35 - 1e-6) failures.push('zombie-ring-candidates');
  if (reservationResults.some((item) => !item.pass) || flexibleReservationResults.some((item) => !item.pass)) failures.push('mode-objective-clearance');
  if (!campaignPass) failures.push('campaign-objective-clearance');
  return {
    pass: failures.length === 0,
    failures,
    minimumPlayerStructureClearanceM: round(minimumPlayerStructureClearanceM),
    minimumBotStructureClearanceM: round(minimumBotStructureClearanceM),
    structureGapViolations,
    primaryRoadViolations,
    ffaNearSpawnCount,
    minimumTeamAnchorGapM: round(minimumTeamAnchorGapM),
    snd: {
      pass: sndPass,
      minimumClearanceM: layout.id === 'renshujo' ? null : round(sndMinimumClearanceM),
      minimumOpponentGapM: layout.id === 'renshujo' ? null : round(sndMinimumOpponentGapM),
      outOfBounds: sndOutOfBounds,
    },
    zombie: { pass: zombieMinimumFreeRatio >= 0.35 - 1e-6, minimumFreeRatio: round(zombieMinimumFreeRatio) },
    objectives: {
      pass: reservationResults.every((item) => item.pass) && flexibleReservationResults.every((item) => item.pass) && campaignPass,
      fixedAndSpecial: reservationResults,
      flexibleZombieShop: flexibleReservationResults,
      campaign: campaignPoints,
      ctfRuntimeStatus: 'NOT-WIRED; Domination A/C coordinates reserved as explicit projection',
    },
  };
}

function pairAudit(layout, pair, districts, roads, playerSpawns, botSpawns, mapSize, reservations, flexibleReservations) {
  const half = mapSize / 2;
  const districtObstacles = districts.map((district) => ({
    id: `district-${district.sourceIndex}-${district.kind}`,
    footprint: aabb(district.cx, district.cz, district.width, district.depth),
    height: district.height,
  }));
  const visibility = pair.landmarks.map((landmark, index) => {
    const other = pair.landmarks[1 - index];
    const sight = lineOfSight(playerSpawns[0], landmark, [
      ...districtObstacles,
      { id: other.id, footprint: other.footprint, height: other.height },
    ]);
    return {
      landmarkId: landmark.id,
      cameraHeightM: EYE_HEIGHT_M,
      bearingDeg: signedBearingDeg(playerSpawns[0], [landmark.cx, landmark.cz]),
      angularHeightDeg: angularHeightDeg(playerSpawns[0], [landmark.cx, landmark.cz], landmark.height),
      ...sight,
    };
  });
  const approachChecks = pair.landmarks.map((landmark, index) => {
    const route = landmark.route;
    const otherFootprint = pair.landmarks[1 - index].footprint;
    const blockers = districtObstacles.filter((district) => overlaps(route, district.footprint, 0)).map((item) => item.id);
    if (overlaps(route, otherFootprint, 0)) blockers.push(pair.landmarks[1 - index].id);
    return {
      landmarkId: landmark.id,
      lengthM: round(approachLength(landmark.approach)),
      widthM: landmark.approach.width,
      withinBounds: boundaryClearance(route, half) >= -1e-6,
      blockers,
      capsuleClear: blockers.length === 0,
    };
  });
  const navigation = navigationAudit(mapSize, pair, districts, playerSpawns, botSpawns);
  const runtimeModes = runtimeModeAudit(layout, mapSize, pair, districts, roads, playerSpawns, botSpawns, reservations, flexibleReservations);
  const footprints = pair.landmarks.map((landmark) => landmark.footprint);
  const districtFootprints = districtObstacles.map((item) => item.footprint);
  const checks = {
    exactLandmarkPair: pair.landmarks.length === 2 && new Set(pair.landmarks.map((landmark) => landmark.id)).size === 2,
    footprintsFullyInsideAuthoritativeBounds: footprints.every((box) => boundaryClearance(box, half) >= BOUNDARY_INSET_M - 1e-6),
    landmarkSeparation6m: aabbGap(footprints[0], footprints[1]) >= ORDINARY_GAP_M - 1e-6,
    playerSpawnClearance30mAllStructures: runtimeModes.minimumPlayerStructureClearanceM >= PLAYER_SPAWN_CLEAR_M - 1e-6,
    botSpawnClearance8mAllStructures: runtimeModes.minimumBotStructureClearanceM >= BOT_SPAWN_CLEAR_M - 1e-6,
    majorRoadsClearFor12mCapsule: footprints.every((box) => roads.every((road) => !overlaps(box, road.bounds, CAPSULE_RADIUS_M))),
    ordinaryDistrictsNonOverlapping: districtFootprints.every((box, index) => (
      footprints.every((landmarkBox) => !overlaps(box, landmarkBox, ORDINARY_GAP_M))
      && districtFootprints.every((other, otherIndex) => index === otherIndex || !overlaps(box, other, ORDINARY_GAP_M))
    )),
    approachesAtLeast20m: approachChecks.every((item) => item.lengthM >= 20),
    approachesWidth12m: approachChecks.every((item) => item.widthM >= APPROACH_WIDTH_M),
    approachCapsuleCorridorsClear: approachChecks.every((item) => item.withinBounds && item.capsuleClear),
    initialVisibilityFrom1_65m: visibility.every((item) => item.visible && Math.abs(item.bearingDeg) <= 82 && item.angularHeightDeg >= 6),
    bfsCapsuleReachable: navigation.reachable,
    groundedAtY0: true,
    combatSpace: pair.landmarks.every((landmark) => landmark.width >= 12 && landmark.depth >= 12 && COLLISION_TEMPLATES.has(landmark.collisionTemplate)),
    runtimeAllModeGate: runtimeModes.pass,
  };
  const totalArea = pair.landmarks.reduce((sum, landmark) => sum + landmark.width * landmark.depth, 0)
    + districts.reduce((sum, district) => sum + district.width * district.depth, 0);
  checks.coverageBelow48Percent = totalArea / (mapSize * mapSize) <= MAX_TOTAL_COVERAGE + 1e-9;
  return { checks, approachChecks, visibility, navigation, runtimeModes };
}

function summarizeLandmark(landmark, playerSpawns, botSpawns, visibility, approvalStatus) {
  const spawnMetrics = playerSpawns.map((spawn, index) => ({
    spawnIndex: index,
    bearingDeg: signedBearingDeg(spawn, [landmark.cx, landmark.cz]),
    angularHeightDeg: angularHeightDeg(spawn, [landmark.cx, landmark.cz], landmark.height),
    centreDistanceM: round(Math.hypot(landmark.cx - spawn[0], landmark.cz - spawn[2])),
    footprintClearanceM: round(pointAabbDistance(spawn[0], spawn[2], landmark.footprint)),
  }));
  return {
    id: landmark.id,
    districtKind: landmark.districtKind,
    collisionTemplate: landmark.collisionTemplate,
    approvalSource: approvalStatus === 'PASS'
      ? (PROOF7.has(landmark.id.split('-')[0]) ? 'solver-v2-proof-preserved-and-all-mode-validated' : 'solver-v2-all-mode-validated')
      : 'solver-v2-no-ship-candidate',
    cx: landmark.cx,
    cz: landmark.cz,
    rot: landmark.rot,
    width: landmark.width,
    depth: landmark.depth,
    height: landmark.height,
    footprintBounds: landmark.footprint,
    entrance: landmark.entrance,
    approach: landmark.approach,
    grounded: true,
    groundY: 0,
    combatSpace: true,
    metrics: {
      areaM2: landmark.width * landmark.depth,
      boundaryClearanceM: landmark.boundaryClearance,
      nearestPlayerSpawnClearanceM: round(minimumPointDistance(playerSpawns, landmark.footprint)),
      nearestBotSpawnClearanceM: round(minimumPointDistance(botSpawns, landmark.footprint)),
      firstSpawnVisibility: visibility,
      playerSpawnMetrics: spawnMetrics,
    },
  };
}

function sourceBoxAudit(layout) {
  const finite = layout.boxes.every((box) => ['x', 'y', 'z', 'w', 'h', 'd'].every((key) => Number.isFinite(box[key])));
  const groundContactBoxes = layout.boxes.filter((box) => !box.ghost && !box.decor && Math.abs(box.y - box.h / 2) <= 1e-4).length;
  return {
    boxCount: layout.boxes.length,
    finiteTransforms: finite,
    ghostBoundaryBoxCount: layout.boxes.filter((box) => box.ghost).length,
    districtBoxCount: layout.boxes.filter((box) => box.district && !box.landmarkId).length,
    landmarkBoxCount: layout.boxes.filter((box) => box.landmarkId).length,
    groundContactEvidenceBoxCount: groundContactBoxes,
  };
}

function failedCheckNames(checks) {
  return Object.entries(checks).filter(([, value]) => !value).map(([key]) => key);
}

function solveVariant(layout, catalogStage, mapSize, variantId) {
  const sourcePlayerSpawns = scaledSpawns(layout.playerSpawns, layout.size, mapSize);
  const sourceBotSpawns = scaledSpawns(layout.botSpawns, layout.size, mapSize);
  const roads = roadNetwork(mapSize);
  const fixedReservations = fixedModeReservations(mapSize, layout);
  const flexibleReservations = flexibleModeReservationGroups(mapSize, layout);
  const prototypes = catalogStage.landmarks.map(canonicalPrototype);
  const candidateSets = prototypes.map((prototype, index) => landmarkCandidates(
    prototype,
    mapSize,
    sourcePlayerSpawns[0],
    roads,
    fixedReservations,
    index,
  ));
  const pairs = pairCandidates(candidateSets[0], candidateSets[1], flexibleReservations);
  const sourceDistricts = sourceOrdinaryDistricts(layout);
  const failureHistogram = new Map();
  let bestAttempt = null;
  for (const [pairIndex, pair] of pairs.entries()) {
    if (pairIndex >= 80) break;
    const playerSpawns = buildPlayerSpawns(mapSize, pair);
    if (!playerSpawns) {
      failureHistogram.set('four-player-road-spawns-unplaceable', (failureHistogram.get('four-player-road-spawns-unplaceable') ?? 0) + 1);
      continue;
    }
    const modeReservations = [...fixedReservations, ...trainingTargetReservations(playerSpawns, layout.id)];
    for (let strategy = 0; strategy < 4; strategy += 1) {
      const packed = packOrdinaryDistricts(sourceDistricts, pair, roads, playerSpawns, [], mapSize, strategy, modeReservations, flexibleReservations);
      if (packed.status !== 'PASS') {
        failureHistogram.set(packed.reason, (failureHistogram.get(packed.reason) ?? 0) + 1);
        continue;
      }
      const botSpawns = buildBotSpawns(mapSize, layout.botSpawns.length, pair, packed.districts, playerSpawns, layout.botCount);
      if (!botSpawns) {
        failureHistogram.set('road-bot-spawns-unplaceable', (failureHistogram.get('road-bot-spawns-unplaceable') ?? 0) + 1);
        continue;
      }
      const audit = pairAudit(layout, pair, packed.districts, roads, playerSpawns, botSpawns, mapSize, modeReservations, flexibleReservations);
      const failures = failedCheckNames(audit.checks);
      if (!bestAttempt || failures.length < bestAttempt.failures.length) {
        bestAttempt = { pair, districts: packed.districts, playerSpawns, botSpawns, audit, failures };
      }
      if (failures.length > 0) {
        for (const failure of failures) failureHistogram.set(failure, (failureHistogram.get(failure) ?? 0) + 1);
        continue;
      }
      bestAttempt = { pair, districts: packed.districts, playerSpawns, botSpawns, audit, failures };
      break;
    }
    if (bestAttempt?.failures.length === 0) break;
  }
  if (!bestAttempt && pairs.length > 0) {
    bestAttempt = {
      pair: pairs[0],
      districts: [],
      playerSpawns: sourcePlayerSpawns,
      botSpawns: sourceBotSpawns,
      audit: { checks: {}, approachChecks: [], visibility: [], navigation: { reachable: false, reason: 'ordinary-district-packing-failed' } },
      failures: ['ordinaryDistrictPacking'],
    };
  }
  const status = bestAttempt && bestAttempt.failures.length === 0 ? 'PASS' : 'NO-SHIP';
  const pair = bestAttempt?.pair ?? { landmarks: [], gap: null };
  const playerSpawns = bestAttempt?.playerSpawns ?? sourcePlayerSpawns;
  const botSpawns = bestAttempt?.botSpawns ?? sourceBotSpawns;
  const visibilityById = new Map((bestAttempt?.audit.visibility ?? []).map((item) => [item.landmarkId, item]));
  const landmarks = pair.landmarks.map((landmark) => summarizeLandmark(
    landmark,
    playerSpawns,
    botSpawns,
    visibilityById.get(landmark.id) ?? null,
    status,
  ));
  const ordinaryArea = (bestAttempt?.districts ?? []).reduce((sum, district) => sum + district.width * district.depth, 0);
  const landmarkArea = pair.landmarks.reduce((sum, landmark) => sum + landmark.width * landmark.depth, 0);
  const failures = status === 'PASS'
    ? []
    : [
        ...(bestAttempt?.failures ?? [
          'no-valid-landmark-pair',
          ...candidateSets.flatMap((items, index) => items.length === 0
            ? [`${prototypes[index].id}: no candidate satisfies 4m boundary inset + 16m primary-road/12m-capsule clearance + 12m approach`]
            : []),
        ]),
        ...[...failureHistogram.entries()]
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .slice(0, 8)
          .map(([reason, count]) => `${reason} (${count} attempts)`),
      ];
  return {
    variantId,
    status,
    sourceMapSizeM: layout.size,
    evaluatedMapSizeM: mapSize,
    spawnTransform: 'deterministic-primary-road-replan-from-source-counts',
    playerSpawns,
    botSpawns,
    roads: roads.map(({ bounds, ...road }) => ({ ...road, bounds })),
    sourceAudit: {
      ...sourceBoxAudit(layout),
      recipeBuildings: [...layout.recipe.buildings],
      sourceOrdinaryDistrictCount: sourceDistricts.length,
      sourcePlayerSpawnCount: layout.playerSpawns.length,
      sourceBotSpawnCount: layout.botSpawns.length,
    },
    landmarks,
    ordinaryDistricts: bestAttempt?.districts ?? [],
    checks: bestAttempt?.audit.checks ?? {},
    approachAudit: bestAttempt?.audit.approachChecks ?? [],
    visibilityAudit: bestAttempt?.audit.visibility ?? [],
    navigationAudit: bestAttempt?.audit.navigation ?? { reachable: false, reason: 'no-candidate' },
    runtimeModeAudit: bestAttempt?.audit.runtimeModes ?? { pass: false, failures: ['no-candidate'] },
    metrics: {
      landmarkOccupancyRate: round(landmarkArea / (mapSize * mapSize), 6),
      ordinaryDistrictOccupancyRate: round(ordinaryArea / (mapSize * mapSize), 6),
      totalStructureOccupancyRate: round((landmarkArea + ordinaryArea) / (mapSize * mapSize), 6),
      landmarkCentreDistanceM: pair.landmarks.length === 2
        ? round(Math.hypot(pair.landmarks[0].cx - pair.landmarks[1].cx, pair.landmarks[0].cz - pair.landmarks[1].cz))
        : null,
      landmarkFootprintGapM: pair.landmarks.length === 2 ? round(aabbGap(pair.landmarks[0].footprint, pair.landmarks[1].footprint)) : null,
      minimumPrimaryRoadWidthM: PRIMARY_ROAD_WIDTH_M,
      minimumApproachWidthM: APPROACH_WIDTH_M,
      evaluatedPairCandidates: Math.min(80, pairs.length),
      candidateCounts: candidateSets.map((items) => items.length),
    },
    failures,
  };
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
    result[stageMatch[1]] = pair;
  }
  return result;
}

function proofDiff(stageTsSource, catalog) {
  const current = parseProofBlock(stageTsSource);
  const fields = ['id', 'districtKind', 'collisionTemplate', 'width', 'depth', 'height'];
  const stages = [];
  const differences = [];
  for (const [stageId, currentPair] of Object.entries(current)) {
    const canonical = catalog.stages.find((stage) => stage.id === stageId).landmarks.map(canonicalPrototype);
    const stageDifferences = [];
    for (let index = 0; index < 2; index += 1) {
      for (const field of fields) {
        if (currentPair[index]?.[field] === canonical[index]?.[field]) continue;
        stageDifferences.push({ ordinal: index, field, current: currentPair[index]?.[field], canonical: canonical[index]?.[field] });
      }
    }
    differences.push(...stageDifferences.map((difference) => ({ stageId, ...difference })));
    stages.push({ stageId, semanticEqual: stageDifferences.length === 0, differences: stageDifferences });
  }
  return {
    status: Object.keys(current).length === 7 && differences.length === 0 ? 'PASS' : 'FAIL',
    representativeStageCount: Object.keys(current).length,
    representativeLandmarkCount: Object.keys(current).length * 2,
    semanticFields: fields,
    breakingDifferenceCount: differences.length,
    differences,
    stages,
  };
}

function validateInputJoins(catalog, layouts) {
  assert(catalog.stages.length === 31, 'canonical catalog must contain 31 stages');
  assert(layouts.stages.length === 31, 'stage layouts must contain 31 stages');
  const catalogIds = catalog.stages.map((stage) => stage.id).sort();
  const layoutIds = layouts.stages.map((stage) => stage.id).sort();
  assert(JSON.stringify(catalogIds) === JSON.stringify(layoutIds), 'catalog/layout stage ID drift');
  const landmarkIds = catalog.stages.flatMap((stage) => stage.landmarks.map((landmark) => landmark.id));
  assert(landmarkIds.length === 62 && new Set(landmarkIds).size === 62, 'canonical requires 62 unique landmark IDs');
}

function validateRuntimeSourceContracts(runtimeSources) {
  const { match, storyEngine, snd, zombieDirector, trainingRange, modes, stages } = runtimeSources;
  assert(/\['A',\s*-size \* 0\.3,\s*size \* 0\.12\]/.test(match), 'Domination A coordinate formula drift');
  assert(/\['C',\s*size \* 0\.3,\s*-size \* 0\.12\]/.test(match), 'Domination C coordinate formula drift');
  for (const expression of [
    /-size \* 0\.28,\s*size \* 0\.1/,
    /size \* 0\.18,\s*-size \* 0\.22/,
    /size \* 0\.3,\s*size \* 0\.15/,
    /-size \* 0\.15,\s*size \* 0\.28/,
  ]) assert(expression.test(match), `Hardpoint coordinate formula drift: ${expression}`);
  assert(/x:\s*-size \* 0\.3,\s*z:\s*size \* 0\.12/.test(storyEngine), 'S&D site A formula drift');
  assert(/x:\s*size \* 0\.3,\s*z:\s*-size \* 0\.12/.test(storyEngine), 'S&D site B formula drift');
  assert(/spacing = 2\.4/.test(snd) && /const inward = 1\.5 \+ row \* spacing/.test(snd), 'S&D formation formula drift');
  for (const expression of [
    /radius = size \* 0\.36/,
    /radius = size \* 0\.4/,
    /radius = size \* 0\.26/,
    /radius = size \* 0\.16/,
    /const offsets = \[0, 0\.22, -0\.22, 0\.44, -0\.44\]/,
  ]) assert(expression.test(zombieDirector), `Zombie shop formula drift: ${expression}`);
  assert(/\[5, 10, 20, 30, 50\]/.test(trainingRange), 'training static-target distances drift');
  assert(/moveRange:\s*3\.5/.test(trainingRange), 'training moving-target sweep drift');
  assert(/if \(mode === 'zombie'\) return STAGES\.filter\(isZombieStage\)/.test(stages), 'zombie stage gating drift');
  assert(/if \(mode === 'training'\) return STAGES\.filter\(isTrainingStage\)/.test(stages), 'training stage gating drift');
  const modeIds = modes.match(/export const MODE_IDS:[^=]*= \[([^\]]+)\]/)?.[1] ?? '';
  assert(modeIds.length > 0 && !modeIds.includes("'ctf'"), 'CTF runtime wiring status drift');
}

function generateTypeScript(audit) {
  const stageIds = audit.stages.map((stage) => JSON.stringify(stage.id)).join(' | ');
  const record = Object.fromEntries(audit.stages.map((stage) => [stage.id, {
    status: stage.status,
    mapSize: stage.evaluatedMapSizeM,
    playerSpawns: stage.playerSpawns,
    botSpawns: stage.botSpawns,
    roads: stage.roads,
    landmarks: stage.landmarks.map((landmark) => ({
      id: landmark.id,
      districtKind: landmark.districtKind,
      collisionTemplate: landmark.collisionTemplate,
      cx: landmark.cx,
      cz: landmark.cz,
      rot: landmark.rot,
      width: landmark.width,
      depth: landmark.depth,
      height: landmark.height,
      entrance: landmark.entrance,
      approach: landmark.approach,
      grounded: landmark.grounded,
      combatSpace: landmark.combatSpace,
    })),
    ordinaryDistricts: stage.ordinaryDistricts.map((district) => ({
      kind: district.kind,
      cx: district.cx,
      cz: district.cz,
      rot: district.rot,
      width: district.width,
      depth: district.depth,
    })),
  }]));
  const noShip = audit.stages.filter((stage) => stage.status !== 'PASS').map((stage) => stage.id);
  return `// Generated by tools/blender/stage-placement-solver.mjs (solver v2). DO NOT EDIT.\n`
    + `export const STAGE_PLACEMENT_SOLVER_SHA256 = ${JSON.stringify(audit.solverSha256)} as const;\n`
    + `export const STAGE_WORLD_CATALOG_SHA256 = ${JSON.stringify(audit.catalogSha256)} as const;\n\n`
    + `export type SolverStageId = ${stageIds};\n`
    + `export type SolverPlacementStatus = 'PASS' | 'NO-SHIP';\n\n`
    + `export interface SolverLandmarkPlacement { readonly id: string; readonly districtKind: string; readonly collisionTemplate: string; readonly cx: number; readonly cz: number; readonly rot: number; readonly width: number; readonly depth: number; readonly height: number; readonly entrance: readonly [number, number]; readonly approach: { readonly start: readonly [number, number]; readonly end: readonly [number, number]; readonly width: number }; readonly grounded: true; readonly combatSpace: true }\n`
    + `export interface SolverStagePlacement { readonly status: SolverPlacementStatus; readonly mapSize: number; readonly playerSpawns: readonly (readonly [number, number, number])[]; readonly botSpawns: readonly (readonly [number, number, number])[]; readonly roads: readonly unknown[]; readonly landmarks: readonly SolverLandmarkPlacement[]; readonly ordinaryDistricts: readonly unknown[] }\n\n`
    + `export const SOLVER_V2_STAGE_PLACEMENTS = ${JSON.stringify(record, null, 2)} as const satisfies Readonly<Record<SolverStageId, SolverStagePlacement>>;\n\n`
    + `export const SOLVER_V2_NO_SHIP_STAGE_IDS = ${JSON.stringify(noShip)} as const;\n`
    + `/** Compatibility aliases for the v1 runtime adapter import surface. */\n`
    + `export const SOLVER_V1_STAGE_PLACEMENTS = SOLVER_V2_STAGE_PLACEMENTS;\n`
    + `export const SOLVER_V1_NO_SHIP_STAGE_IDS = SOLVER_V2_NO_SHIP_STAGE_IDS;\n`;
}

function renderArtifacts(audit, proof) {
  const allModeStages = audit.stages.map((stage) => ({
    stageId: stage.id,
    mapSize: stage.evaluatedMapSizeM,
    status: stage.status,
    ...stage.runtimeModeAudit,
  }));
  const allModeFailures = allModeStages.flatMap((stage) => stage.failures.map((failure) => ({ stageId: stage.stageId, failure })));
  return {
    'stage-placement-audit.json': `${JSON.stringify(audit, null, 2)}\n`,
    'proof7-breaking-diff.json': `${JSON.stringify({
      schemaVersion: audit.schemaVersion,
      catalogSha256: audit.catalogSha256,
      solverSha256: audit.solverSha256,
      currentStageTsSha256: audit.sources.stageTsSha256,
      ...proof,
    }, null, 2)}\n`,
    'stage-placements.generated.ts': generateTypeScript(audit),
    'all-mode-objective-audit.json': `${JSON.stringify({
      schemaVersion: audit.schemaVersion,
      solverSha256: audit.solverSha256,
      summary: {
        stageCount: allModeStages.length,
        passStageCount: allModeStages.filter((stage) => stage.pass).length,
        noShipStageIds: allModeStages.filter((stage) => !stage.pass).map((stage) => stage.stageId),
        violationCount: allModeFailures.length,
        failureCounts: Object.fromEntries([...new Set(allModeFailures.map((item) => item.failure))].sort().map((failure) => [
          failure,
          allModeFailures.filter((item) => item.failure === failure).length,
        ])),
        fixedObjectiveReservationCount: allModeStages.reduce((sum, stage) => sum + (stage.objectives?.fixedAndSpecial?.length ?? 0), 0),
        flexibleZombieShopGroupCount: allModeStages.reduce((sum, stage) => sum + (stage.objectives?.flexibleZombieShop?.length ?? 0), 0),
      },
      stages: allModeStages,
    }, null, 2)}\n`,
    'stage-placement.manifest.json': `${JSON.stringify({
      schemaVersion: audit.schemaVersion,
      solverSha256: audit.solverSha256,
      catalogSha256: audit.catalogSha256,
      stageCount: audit.summary.stageCount,
      landmarkRecordCount: audit.summary.landmarkRecordCount,
      validatedLandmarkCount: audit.summary.validatedLandmarkCount,
      noShipStageIds: audit.summary.noShipStageIds,
      heuristicTagCount: audit.summary.heuristicTagCount,
      proof7BreakingDifferenceCount: proof.breakingDifferenceCount,
      allModePassStageCount: allModeStages.filter((stage) => stage.pass).length,
      allModeViolationCount: allModeFailures.length,
    }, null, 2)}\n`,
  };
}

export async function buildAudit({ catalogText, layoutsText, stageTsSource, stagesTsSource, runtimeSources }) {
  const catalog = JSON.parse(catalogText);
  const layouts = JSON.parse(layoutsText);
  validateInputJoins(catalog, layouts);
  validateRuntimeSourceContracts(runtimeSources);
  const layoutById = new Map(layouts.stages.map((stage) => [stage.id, stage]));
  const stages = [];
  let renshujoCompactEvaluation = null;
  for (const catalogStage of catalog.stages) {
    const layout = layoutById.get(catalogStage.id);
    assert(layout, `${catalogStage.id}: layout missing`);
    if (catalogStage.id === 'renshujo') {
      const recommended = solveVariant(layout, catalogStage, 236, 'recommended-236m');
      const compact = solveVariant(layout, catalogStage, 200, 'compact-200m');
      renshujoCompactEvaluation = compact;
      stages.push(recommended.status === 'PASS' ? recommended : compact);
    } else {
      stages.push(solveVariant(layout, catalogStage, layout.size, 'authoritative-current-size'));
    }
    stages[stages.length - 1].id = catalogStage.id;
    stages[stages.length - 1].name = catalogStage.name;
  }
  if (renshujoCompactEvaluation) {
    renshujoCompactEvaluation.id = 'renshujo';
    renshujoCompactEvaluation.name = catalog.stages.find((stage) => stage.id === 'renshujo').name;
  }
  const proof = proofDiff(stageTsSource, catalog);
  const noShipStageIds = stages.filter((stage) => stage.status !== 'PASS').map((stage) => stage.id);
  const audit = {
    schemaVersion: '2.0.0-solver-prototype',
    solverSha256: '',
    catalogSha256: catalog.catalogSha256,
    normalization: 'recursive-key-sort UTF-8 JSON without whitespace; omit top-level solverSha256',
    sources: {
      catalogSha256: sha256(catalogText),
      layoutsSha256: sha256(normalizedLayoutsPayload(layouts)),
      layoutGeneratedAt: layouts.generatedAt,
      stageTsSha256: sha256(stageTsSource),
      stagesTsSha256: sha256(stagesTsSource),
      matchTsSha256: sha256(runtimeSources.match),
      storyEngineTsSha256: sha256(runtimeSources.storyEngine),
      sndTsSha256: sha256(runtimeSources.snd),
      zombieDirectorTsSha256: sha256(runtimeSources.zombieDirector),
      trainingRangeTsSha256: sha256(runtimeSources.trainingRange),
      modesTsSha256: sha256(runtimeSources.modes),
    },
    constants: {
      gridM: GRID_M,
      boundaryInsetM: BOUNDARY_INSET_M,
      primaryRoadWidthM: PRIMARY_ROAD_WIDTH_M,
      approachWidthM: APPROACH_WIDTH_M,
      capsuleDiameterM: CAPSULE_RADIUS_M * 2,
      playerSpawnClearanceM: PLAYER_SPAWN_CLEAR_M,
      botSpawnClearanceM: BOT_SPAWN_CLEAR_M,
      ordinaryDistrictGapM: ORDINARY_GAP_M,
      initialCameraHeightM: EYE_HEIGHT_M,
      maxTotalCoverage: MAX_TOTAL_COVERAGE,
      teamAnchorGapM: TEAM_ANCHOR_GAP_M,
      ffaPreferredBandM: [FFA_NEAR_MIN_M, FFA_NEAR_MAX_M],
      modeObjectiveClearanceM: MODE_OBJECTIVE_CLEAR_M,
      sndSiteClearanceM: SND_SITE_CLEAR_M,
      trainingTargetClearanceM: TRAINING_TARGET_CLEAR_M,
      zombieShopClearanceM: ZOMBIE_SHOP_CLEAR_M,
    },
    migrationModel: {
      order: ['mode-objective-reservations', 'landmarks', 'roads-and-approaches', 'spawn-and-formation-reservations', 'ordinary-district-repack', 'all-mode-audit', 'props-and-boxes-regeneration'],
      existingBoxesPreservedInPlace: false,
      rationale: 'Existing generated boxes are read for bounds, ground contact, district count and height evidence; runtime adoption must regenerate ordinary building/prop/cover boxes from the accepted reservations so stale colliders cannot remain under a landmark.',
    },
    proof7: proof,
    renshujo: {
      preferredVariant: 'recommended-236m',
      adoptedVariant: stages.find((stage) => stage.id === 'renshujo').variantId,
      compact200mEvaluation: renshujoCompactEvaluation,
    },
    stages,
    summary: {
      stageCount: stages.length,
      landmarkRecordCount: stages.reduce((sum, stage) => sum + stage.landmarks.length, 0),
      validatedLandmarkCount: stages.filter((stage) => stage.status === 'PASS').reduce((sum, stage) => sum + stage.landmarks.length, 0),
      passStageCount: stages.filter((stage) => stage.status === 'PASS').length,
      noShipStageCount: noShipStageIds.length,
      noShipStageIds,
      heuristicTagCount: 0,
      proof7BreakingDifferenceCount: proof.breakingDifferenceCount,
      allModePassStageCount: stages.filter((stage) => stage.runtimeModeAudit?.pass).length,
      allModeViolationCount: stages.reduce((sum, stage) => sum + (stage.runtimeModeAudit?.failures?.length ?? 1), 0),
    },
  };
  audit.solverSha256 = sha256(normalizedAuditPayload(audit));
  return { audit, proof, artifacts: renderArtifacts(audit, proof) };
}

function parseArgs(argv) {
  const options = {
    catalog: resolve(HERE, 'stage-world.catalog.json'),
    layouts: resolve(HERE, 'generated/stage-layouts.json'),
    stageTs: resolve(REPO_ROOT, 'src/game/stage.ts'),
    stagesTs: resolve(REPO_ROOT, 'src/game/stages.ts'),
    matchTs: null,
    storyEngineTs: null,
    sndTs: null,
    zombieDirectorTs: null,
    trainingRangeTs: null,
    modesTs: null,
    outDir: DEFAULT_GENERATED_DIR,
    typescriptOut: DEFAULT_TYPESCRIPT_OUT,
    check: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--check') options.check = true;
    else if (arg === '--catalog') options.catalog = resolve(argv[++index]);
    else if (arg === '--layouts') options.layouts = resolve(argv[++index]);
    else if (arg === '--stage-ts') options.stageTs = resolve(argv[++index]);
    else if (arg === '--stages-ts') options.stagesTs = resolve(argv[++index]);
    else if (arg === '--match-ts') options.matchTs = resolve(argv[++index]);
    else if (arg === '--story-engine-ts') options.storyEngineTs = resolve(argv[++index]);
    else if (arg === '--snd-ts') options.sndTs = resolve(argv[++index]);
    else if (arg === '--zombie-director-ts') options.zombieDirectorTs = resolve(argv[++index]);
    else if (arg === '--training-range-ts') options.trainingRangeTs = resolve(argv[++index]);
    else if (arg === '--modes-ts') options.modesTs = resolve(argv[++index]);
    else if (arg === '--out-dir') options.outDir = resolve(argv[++index]);
    else if (arg === '--typescript-out') options.typescriptOut = resolve(argv[++index]);
    else throw new Error(`unknown argument ${arg}`);
  }
  const gameDir = dirname(options.stageTs);
  options.matchTs ??= resolve(gameDir, 'match.ts');
  options.storyEngineTs ??= resolve(gameDir, 'story-engine.ts');
  options.sndTs ??= resolve(gameDir, 'snd.ts');
  options.zombieDirectorTs ??= resolve(gameDir, 'zombie-director.ts');
  options.trainingRangeTs ??= resolve(gameDir, 'training-range.ts');
  options.modesTs ??= resolve(gameDir, 'modes.ts');
  return options;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const [
    catalogText, layoutsText, stageTsSource, stagesTsSource, matchSource,
    storyEngineSource, sndSource, zombieDirectorSource, trainingRangeSource, modesSource,
  ] = await Promise.all([
    readFile(options.catalog, 'utf8'),
    readFile(options.layouts, 'utf8'),
    readFile(options.stageTs, 'utf8'),
    readFile(options.stagesTs, 'utf8'),
    readFile(options.matchTs, 'utf8'),
    readFile(options.storyEngineTs, 'utf8'),
    readFile(options.sndTs, 'utf8'),
    readFile(options.zombieDirectorTs, 'utf8'),
    readFile(options.trainingRangeTs, 'utf8'),
    readFile(options.modesTs, 'utf8'),
  ]);
  const runtimeSources = {
    match: matchSource,
    storyEngine: storyEngineSource,
    snd: sndSource,
    zombieDirector: zombieDirectorSource,
    trainingRange: trainingRangeSource,
    modes: modesSource,
    stages: stagesTsSource,
  };
  const { audit, artifacts } = await buildAudit({ catalogText, layoutsText, stageTsSource, stagesTsSource, runtimeSources });
  await mkdir(options.outDir, { recursive: true });
  await mkdir(dirname(options.typescriptOut), { recursive: true });
  const outputPath = (name) => name === 'stage-placements.generated.ts'
    ? options.typescriptOut
    : resolve(options.outDir, name);
  if (options.check) {
    const drift = [];
    for (const [name, expected] of Object.entries(artifacts)) {
      let actual = null;
      try { actual = await readFile(outputPath(name), 'utf8'); } catch { /* drift below */ }
      if (actual !== expected) drift.push(name);
    }
    if (drift.length) throw new Error(`generated output drift: ${drift.join(', ')}`);
    process.stdout.write(`CHECK PASS ${audit.solverSha256} ${audit.summary.passStageCount}/31 PASS, ${audit.summary.validatedLandmarkCount}/62 validated\n`);
    return;
  }
  for (const [name, content] of Object.entries(artifacts)) {
    await writeFile(outputPath(name), content, 'utf8');
  }
  process.stdout.write(`GENERATED ${audit.solverSha256} ${audit.summary.passStageCount}/31 PASS, ${audit.summary.validatedLandmarkCount}/62 validated\n`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  await main();
}
