export const CANONICAL_STAGE_COUNT = 31;
export const CANONICAL_LANDMARK_COUNT = 62;
export const CANONICAL_ORDINARY_DISTRICT_COUNT = 315;

export const CONSTRUCTION_SEQUENCE = [
  'landmarks',
  'roads-and-approaches',
  'ordinary-districts',
  'spawns',
  'props-and-cover',
] as const;

export const BUILDING_KINDS = [
  'arena', 'hangar', 'tower', 'warehouse', 'cathedral',
  'bunker', 'terminal', 'refinery', 'villa', 'pagoda',
  'fortress', 'station', 'checkpoint', 'metro', 'abbey',
] as const;

export const COLLISION_TEMPLATES = [
  'abbey', 'courtyard', 'hall', 'bridge', 'vertical',
] as const;

export type RuntimeBuildingKind = typeof BUILDING_KINDS[number];
export type RuntimeCollisionTemplate = typeof COLLISION_TEMPLATES[number];
export type RuntimeSpawnPoint = [number, number, number];

export interface RuntimeAabb {
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

export interface RuntimeRoad {
  id: string;
  axis: 'x' | 'z';
  centre: number;
  width: number;
  bounds: RuntimeAabb;
}

export interface RuntimeApproach {
  start: [number, number];
  end: [number, number];
  width: number;
}

export interface RuntimeLandmarkPlacement {
  id: string;
  districtKind: RuntimeBuildingKind;
  collisionTemplate: RuntimeCollisionTemplate;
  cx: number;
  cz: number;
  rot: number;
  width: number;
  depth: number;
  height: number;
  entrance: [number, number];
  approach: RuntimeApproach;
  grounded: true;
  combatSpace: true;
}

export interface RuntimeOrdinaryDistrict {
  kind: RuntimeBuildingKind;
  cx: number;
  cz: number;
  rot: number;
  width: number;
  depth: number;
}

export interface RuntimeStagePlacement {
  status: 'PASS';
  mapSize: number;
  playerSpawns: RuntimeSpawnPoint[];
  botSpawns: RuntimeSpawnPoint[];
  roads: RuntimeRoad[];
  landmarks: RuntimeLandmarkPlacement[];
  ordinaryDistricts: RuntimeOrdinaryDistrict[];
}

export interface StageDefinitionContract {
  id: string;
  size: number;
  botCount: number;
}

export interface ValidationIssue {
  code: string;
  path: string;
  message: string;
}

export interface StagePlacementValidation {
  ok: boolean;
  issues: ValidationIssue[];
  value?: RuntimeStagePlacement;
}

export interface CatalogValidation {
  ok: boolean;
  issues: ValidationIssue[];
  stageCount: number;
  landmarkCount: number;
  ordinaryDistrictCount: number;
  uniqueLandmarkCount: number;
}

export type PlacementTable = Readonly<Record<string, unknown>>;

export interface GeneratedPlacementReleaseGate {
  /** Explicit per-stage allow-list. An empty set keeps every stage on legacy. */
  approvedStageIds: ReadonlySet<string>;
}

export type PlacementResolution =
  | {
      source: 'legacy';
      reason: 'not-approved' | 'missing' | 'invalid';
      issues: ValidationIssue[];
    }
  | {
      source: 'generated';
      reason: 'approved';
      issues: [];
      placement: RuntimeStagePlacement;
    };

const BUILDING_KIND_SET = new Set<string>(BUILDING_KINDS);
const COLLISION_TEMPLATE_SET = new Set<string>(COLLISION_TEMPLATES);

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function issue(
  issues: ValidationIssue[],
  code: string,
  path: string,
  message: string,
): void {
  issues.push({ code, path, message });
}

function tuple2(value: unknown, path: string, issues: ValidationIssue[]): [number, number] | null {
  if (!Array.isArray(value) || value.length !== 2 || !value.every(isFiniteNumber)) {
    issue(issues, 'invalid-tuple2', path, 'expected exactly two finite numbers');
    return null;
  }
  return [value[0]!, value[1]!];
}

function tuple3(value: unknown, path: string, issues: ValidationIssue[]): RuntimeSpawnPoint | null {
  if (!Array.isArray(value) || value.length !== 3 || !value.every(isFiniteNumber)) {
    issue(issues, 'invalid-spawn', path, 'expected exactly three finite numbers');
    return null;
  }
  return [value[0]!, value[1]!, value[2]!];
}

function positiveNumber(
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ValidationIssue[],
): number | null {
  const value = record[key];
  if (!isFiniteNumber(value) || value <= 0) {
    issue(issues, 'invalid-positive-number', `${path}.${key}`, 'expected a finite number > 0');
    return null;
  }
  return value;
}

function finiteNumber(
  record: Record<string, unknown>,
  key: string,
  path: string,
  issues: ValidationIssue[],
): number | null {
  const value = record[key];
  if (!isFiniteNumber(value)) {
    issue(issues, 'invalid-number', `${path}.${key}`, 'expected a finite number');
    return null;
  }
  return value;
}

function rotation(
  record: Record<string, unknown>,
  path: string,
  issues: ValidationIssue[],
): number | null {
  const value = record.rot;
  if (!Number.isInteger(value) || (value as number) < 0 || (value as number) > 3) {
    issue(issues, 'invalid-rotation', `${path}.rot`, 'expected an integer rotation step in [0, 3]');
    return null;
  }
  return value as number;
}

function parseAabb(value: unknown, path: string, issues: ValidationIssue[]): RuntimeAabb | null {
  if (!isRecord(value)) {
    issue(issues, 'invalid-aabb', path, 'expected an AABB object');
    return null;
  }
  const minX = finiteNumber(value, 'minX', path, issues);
  const maxX = finiteNumber(value, 'maxX', path, issues);
  const minZ = finiteNumber(value, 'minZ', path, issues);
  const maxZ = finiteNumber(value, 'maxZ', path, issues);
  if ([minX, maxX, minZ, maxZ].some((item) => item === null)) return null;
  if (minX! >= maxX! || minZ! >= maxZ!) {
    issue(issues, 'inverted-aabb', path, 'AABB minima must be lower than maxima');
    return null;
  }
  return { minX: minX!, maxX: maxX!, minZ: minZ!, maxZ: maxZ! };
}

function parseRoad(value: unknown, path: string, issues: ValidationIssue[]): RuntimeRoad | null {
  if (!isRecord(value)) {
    issue(issues, 'invalid-road', path, 'expected a road object');
    return null;
  }
  const id = typeof value.id === 'string' && value.id.length > 0 ? value.id : null;
  const axis = value.axis === 'x' || value.axis === 'z' ? value.axis : null;
  const centre = finiteNumber(value, 'centre', path, issues);
  const width = positiveNumber(value, 'width', path, issues);
  const bounds = parseAabb(value.bounds, `${path}.bounds`, issues);
  if (!id) issue(issues, 'invalid-road-id', `${path}.id`, 'expected a non-empty road id');
  if (!axis) issue(issues, 'invalid-road-axis', `${path}.axis`, "expected 'x' or 'z'");
  if (!id || !axis || centre === null || width === null || !bounds) return null;
  return { id, axis, centre, width, bounds };
}

function parseApproach(
  value: unknown,
  path: string,
  issues: ValidationIssue[],
): RuntimeApproach | null {
  if (!isRecord(value)) {
    issue(issues, 'invalid-approach', path, 'expected an approach object');
    return null;
  }
  const start = tuple2(value.start, `${path}.start`, issues);
  const end = tuple2(value.end, `${path}.end`, issues);
  const width = positiveNumber(value, 'width', path, issues);
  if (!start || !end || width === null) return null;
  if (width < 12 - 1e-6) {
    issue(issues, 'narrow-approach', `${path}.width`, 'approach must retain at least 12m clear width');
    return null;
  }
  if (Math.hypot(start[0] - end[0], start[1] - end[1]) < 20 - 1e-6) {
    issue(issues, 'short-approach', path, 'approach must be at least 20m long');
    return null;
  }
  return { start, end, width };
}

function parseLandmark(
  value: unknown,
  stageId: string,
  path: string,
  issues: ValidationIssue[],
): RuntimeLandmarkPlacement | null {
  if (!isRecord(value)) {
    issue(issues, 'invalid-landmark', path, 'expected a landmark object');
    return null;
  }
  const id = typeof value.id === 'string' && value.id.startsWith(`${stageId}-`) ? value.id : null;
  const districtKind = typeof value.districtKind === 'string' && BUILDING_KIND_SET.has(value.districtKind)
    ? value.districtKind as RuntimeBuildingKind
    : null;
  const collisionTemplate = typeof value.collisionTemplate === 'string'
    && COLLISION_TEMPLATE_SET.has(value.collisionTemplate)
    ? value.collisionTemplate as RuntimeCollisionTemplate
    : null;
  const cx = finiteNumber(value, 'cx', path, issues);
  const cz = finiteNumber(value, 'cz', path, issues);
  const rot = rotation(value, path, issues);
  const width = positiveNumber(value, 'width', path, issues);
  const depth = positiveNumber(value, 'depth', path, issues);
  const height = positiveNumber(value, 'height', path, issues);
  const entrance = tuple2(value.entrance, `${path}.entrance`, issues);
  const approach = parseApproach(value.approach, `${path}.approach`, issues);
  if (!id) issue(issues, 'invalid-landmark-id', `${path}.id`, `expected a ${stageId}-prefixed id`);
  if (!districtKind) issue(issues, 'invalid-building-kind', `${path}.districtKind`, 'unknown building kind');
  if (!collisionTemplate) issue(issues, 'invalid-collision-template', `${path}.collisionTemplate`, 'unknown collision template');
  if (value.grounded !== true) issue(issues, 'not-grounded', `${path}.grounded`, 'landmark must be grounded');
  if (value.combatSpace !== true) issue(issues, 'not-combat-space', `${path}.combatSpace`, 'landmark must be playable');
  if (
    !id || !districtKind || !collisionTemplate || cx === null || cz === null || rot === null
    || width === null || depth === null || height === null || !entrance || !approach
    || value.grounded !== true || value.combatSpace !== true
  ) return null;
  return {
    id,
    districtKind,
    collisionTemplate,
    cx,
    cz,
    rot,
    width,
    depth,
    height,
    entrance,
    approach,
    grounded: true,
    combatSpace: true,
  };
}

function parseDistrict(
  value: unknown,
  path: string,
  issues: ValidationIssue[],
): RuntimeOrdinaryDistrict | null {
  if (!isRecord(value)) {
    issue(issues, 'invalid-district', path, 'expected a district object');
    return null;
  }
  const kind = typeof value.kind === 'string' && BUILDING_KIND_SET.has(value.kind)
    ? value.kind as RuntimeBuildingKind
    : null;
  const cx = finiteNumber(value, 'cx', path, issues);
  const cz = finiteNumber(value, 'cz', path, issues);
  const rot = rotation(value, path, issues);
  const width = positiveNumber(value, 'width', path, issues);
  const depth = positiveNumber(value, 'depth', path, issues);
  if (!kind) issue(issues, 'invalid-building-kind', `${path}.kind`, 'unknown building kind');
  if (!kind || cx === null || cz === null || rot === null || width === null || depth === null) return null;
  return { kind, cx, cz, rot, width, depth };
}

function footprintInBounds(
  cx: number,
  cz: number,
  width: number,
  depth: number,
  half: number,
  inset: number,
): boolean {
  return Math.abs(cx) + width / 2 <= half - inset + 1e-6
    && Math.abs(cz) + depth / 2 <= half - inset + 1e-6;
}

function pointInBounds(point: RuntimeSpawnPoint, half: number): boolean {
  return Math.abs(point[0]) <= half - 2 + 1e-6 && Math.abs(point[2]) <= half - 2 + 1e-6;
}

function footprintOf(item: { cx: number; cz: number; width: number; depth: number }): RuntimeAabb {
  return {
    minX: item.cx - item.width / 2,
    maxX: item.cx + item.width / 2,
    minZ: item.cz - item.depth / 2,
    maxZ: item.cz + item.depth / 2,
  };
}

function approachBounds(approach: RuntimeApproach): RuntimeAabb {
  const radius = approach.width / 2;
  return {
    minX: Math.min(approach.start[0], approach.end[0]) - radius,
    maxX: Math.max(approach.start[0], approach.end[0]) + radius,
    minZ: Math.min(approach.start[1], approach.end[1]) - radius,
    maxZ: Math.max(approach.start[1], approach.end[1]) + radius,
  };
}

function overlaps(a: RuntimeAabb, b: RuntimeAabb, margin = 0): boolean {
  return a.minX - margin < b.maxX
    && a.maxX + margin > b.minX
    && a.minZ - margin < b.maxZ
    && a.maxZ + margin > b.minZ;
}

function pointAabbDistance(point: RuntimeSpawnPoint, box: RuntimeAabb): number {
  const dx = Math.max(0, box.minX - point[0], point[0] - box.maxX);
  const dz = Math.max(0, box.minZ - point[2], point[2] - box.maxZ);
  return Math.hypot(dx, dz);
}

export function validateStagePlacement(
  stageId: string,
  raw: unknown,
  definition?: StageDefinitionContract,
): StagePlacementValidation {
  const issues: ValidationIssue[] = [];
  const path = `stages.${stageId}`;
  if (!isRecord(raw)) {
    issue(issues, 'missing-stage', path, 'generated stage placement is missing');
    return { ok: false, issues };
  }
  if (raw.status !== 'PASS') {
    issue(issues, 'no-ship-stage', `${path}.status`, 'only PASS placements may reach runtime');
  }
  const mapSize = positiveNumber(raw, 'mapSize', path, issues);
  if (mapSize !== null && (!Number.isInteger(mapSize) || mapSize < 200 || mapSize > 400)) {
    issue(issues, 'invalid-map-size', `${path}.mapSize`, 'expected an integer map size in [200, 400]');
  }
  if (definition && mapSize !== null && definition.size !== mapSize) {
    issue(
      issues,
      'stage-definition-size-mismatch',
      `${path}.mapSize`,
      `StageDef.size=${definition.size} must be migrated to generated mapSize=${mapSize} before release`,
    );
  }

  const playerSpawns = Array.isArray(raw.playerSpawns)
    ? raw.playerSpawns.map((item, index) => tuple3(item, `${path}.playerSpawns[${index}]`, issues))
    : [];
  const botSpawns = Array.isArray(raw.botSpawns)
    ? raw.botSpawns.map((item, index) => tuple3(item, `${path}.botSpawns[${index}]`, issues))
    : [];
  if (!Array.isArray(raw.playerSpawns)) issue(issues, 'invalid-player-spawns', `${path}.playerSpawns`, 'expected an array');
  if (!Array.isArray(raw.botSpawns)) issue(issues, 'invalid-bot-spawns', `${path}.botSpawns`, 'expected an array');
  if (playerSpawns.length !== 4) issue(issues, 'player-spawn-count', `${path}.playerSpawns`, 'expected exactly four player anchors');
  if (definition && botSpawns.length < definition.botCount) {
    issue(issues, 'bot-spawn-count', `${path}.botSpawns`, `expected at least ${definition.botCount} bot anchors`);
  }

  const roads = Array.isArray(raw.roads)
    ? raw.roads.map((item, index) => parseRoad(item, `${path}.roads[${index}]`, issues))
    : [];
  if (!Array.isArray(raw.roads)) issue(issues, 'invalid-roads', `${path}.roads`, 'expected an array');
  if (roads.length < 2) issue(issues, 'road-count', `${path}.roads`, 'expected at least two primary roads');

  const landmarks = Array.isArray(raw.landmarks)
    ? raw.landmarks.map((item, index) => parseLandmark(item, stageId, `${path}.landmarks[${index}]`, issues))
    : [];
  if (!Array.isArray(raw.landmarks)) issue(issues, 'invalid-landmarks', `${path}.landmarks`, 'expected an array');
  if (landmarks.length !== 2) issue(issues, 'landmark-count', `${path}.landmarks`, 'expected exactly two landmarks');

  const ordinaryDistricts = Array.isArray(raw.ordinaryDistricts)
    ? raw.ordinaryDistricts.map((item, index) => parseDistrict(item, `${path}.ordinaryDistricts[${index}]`, issues))
    : [];
  if (!Array.isArray(raw.ordinaryDistricts)) issue(issues, 'invalid-districts', `${path}.ordinaryDistricts`, 'expected an array');

  const parsedPlayers = playerSpawns.filter((item): item is RuntimeSpawnPoint => item !== null);
  const parsedBots = botSpawns.filter((item): item is RuntimeSpawnPoint => item !== null);
  const parsedRoads = roads.filter((item): item is RuntimeRoad => item !== null);
  const parsedLandmarks = landmarks.filter((item): item is RuntimeLandmarkPlacement => item !== null);
  const parsedDistricts = ordinaryDistricts.filter((item): item is RuntimeOrdinaryDistrict => item !== null);

  if (new Set(parsedLandmarks.map((item) => item.id)).size !== parsedLandmarks.length) {
    issue(issues, 'duplicate-stage-landmark-id', `${path}.landmarks`, 'landmark ids must be unique within a stage');
  }
  if (new Set(parsedRoads.map((item) => item.id)).size !== parsedRoads.length) {
    issue(issues, 'duplicate-road-id', `${path}.roads`, 'road ids must be unique within a stage');
  }
  const requiredRoads = new Map([
    ['primary-north-south', 'z'],
    ['primary-east-west', 'x'],
  ] as const);
  for (const [roadId, expectedAxis] of requiredRoads) {
    const road = parsedRoads.find((item) => item.id === roadId);
    if (!road) {
      issue(issues, 'missing-primary-road', `${path}.roads`, `missing ${roadId}`);
    } else if (road.axis !== expectedAxis) {
      issue(
        issues,
        'primary-road-axis-mismatch',
        `${path}.roads.${roadId}.axis`,
        `${roadId} must run on the ${expectedAxis} axis`,
      );
    }
  }
  if (mapSize !== null) {
    const half = mapSize / 2;
    for (const [index, road] of parsedRoads.entries()) {
      if (road.width < 16 - 1e-6) {
        issue(issues, 'primary-road-width-under-16m', `${path}.roads[${index}].width`, 'primary road must retain at least 16m clear width');
      }
      const transverseMin = road.axis === 'z' ? road.bounds.minX : road.bounds.minZ;
      const transverseMax = road.axis === 'z' ? road.bounds.maxX : road.bounds.maxZ;
      const longitudinalMin = road.axis === 'z' ? road.bounds.minZ : road.bounds.minX;
      const longitudinalMax = road.axis === 'z' ? road.bounds.maxZ : road.bounds.maxX;
      const transverseMidpoint = (transverseMin + transverseMax) / 2;
      if (Math.abs(transverseMax - transverseMin - road.width) > 1e-6) {
        issue(issues, 'road-width-bounds-mismatch', `${path}.roads[${index}].bounds`, 'road bounds must encode the declared width');
      }
      if (Math.abs(transverseMidpoint - road.centre) > 1e-6) {
        issue(issues, 'road-centre-bounds-mismatch', `${path}.roads[${index}].bounds`, 'road bounds must be centred on road.centre');
      }
      if (longitudinalMin > -half + 4 + 1e-6 || longitudinalMax < half - 4 - 1e-6) {
        issue(issues, 'primary-road-does-not-cross-map', `${path}.roads[${index}].bounds`, 'primary road must cross the complete 4m-inset playable map');
      }
      if (
        road.bounds.minX < -half - 1e-6 || road.bounds.maxX > half + 1e-6
        || road.bounds.minZ < -half - 1e-6 || road.bounds.maxZ > half + 1e-6
      ) {
        issue(issues, 'road-out-of-bounds', `${path}.roads[${index}].bounds`, 'road bounds leave the playable boundary');
      }
    }
    for (const [index, spawn] of parsedPlayers.entries()) {
      if (!pointInBounds(spawn, half)) issue(issues, 'player-spawn-out-of-bounds', `${path}.playerSpawns[${index}]`, 'spawn is outside the playable inset');
    }
    for (const [index, spawn] of parsedBots.entries()) {
      if (!pointInBounds(spawn, half)) issue(issues, 'bot-spawn-out-of-bounds', `${path}.botSpawns[${index}]`, 'spawn is outside the playable inset');
    }
    for (const [index, landmark] of parsedLandmarks.entries()) {
      if (!footprintInBounds(landmark.cx, landmark.cz, landmark.width, landmark.depth, half, 4)) {
        issue(issues, 'landmark-out-of-bounds', `${path}.landmarks[${index}]`, 'landmark footprint violates the 4m inset');
      }
    }
    for (const [index, district] of parsedDistricts.entries()) {
      if (!footprintInBounds(district.cx, district.cz, district.width, district.depth, half, 4)) {
        issue(issues, 'district-out-of-bounds', `${path}.ordinaryDistricts[${index}]`, 'ordinary footprint violates the 4m inset');
      }
    }

    const structures = [
      ...parsedLandmarks.map((item, index) => ({
        path: `${path}.landmarks[${index}]`,
        ownerLandmarkIndex: index,
        box: footprintOf(item),
      })),
      ...parsedDistricts.map((item, index) => ({
        path: `${path}.ordinaryDistricts[${index}]`,
        ownerLandmarkIndex: -1,
        box: footprintOf(item),
      })),
    ];

    for (let index = 0; index < structures.length; index += 1) {
      for (let other = index + 1; other < structures.length; other += 1) {
        if (overlaps(structures[index]!.box, structures[other]!.box, 6)) {
          issue(
            issues,
            'structure-gap-under-6m',
            structures[other]!.path,
            `requires a 6m firebreak from ${structures[index]!.path}`,
          );
        }
      }
    }

    for (const [index, road] of parsedRoads.entries()) {
      for (const structure of structures) {
        if (overlaps(structure.box, road.bounds, 6)) {
          issue(
            issues,
            'primary-road-capsule-blocked',
            `${path}.roads[${index}]`,
            `${structure.path} enters the road plus 6m capsule clearance`,
          );
        }
      }
    }

    for (const [index, landmark] of parsedLandmarks.entries()) {
      if (Math.hypot(
        landmark.entrance[0] - landmark.approach.end[0],
        landmark.entrance[1] - landmark.approach.end[1],
      ) > 1e-6) {
        issue(
          issues,
          'approach-end-entrance-mismatch',
          `${path}.landmarks[${index}].approach.end`,
          'approach must terminate exactly at the authored entrance',
        );
      }
      const route = approachBounds(landmark.approach);
      if (
        route.minX < -half - 1e-6 || route.maxX > half + 1e-6
        || route.minZ < -half - 1e-6 || route.maxZ > half + 1e-6
      ) {
        issue(issues, 'approach-out-of-bounds', `${path}.landmarks[${index}].approach`, 'approach leaves the playable boundary');
      }
      for (const structure of structures) {
        if (structure.ownerLandmarkIndex === index) continue;
        if (overlaps(route, structure.box)) {
          issue(
            issues,
            'approach-blocked',
            `${path}.landmarks[${index}].approach`,
            `${structure.path} intersects the authored entrance route`,
          );
        }
      }
    }

    for (const [index, spawn] of parsedPlayers.entries()) {
      for (const structure of structures) {
        const clearance = pointAabbDistance(spawn, structure.box);
        if (clearance < 30 - 1e-6) {
          issue(
            issues,
            'player-spawn-clearance-under-30m',
            `${path}.playerSpawns[${index}]`,
            `${structure.path} is only ${clearance.toFixed(3)}m away`,
          );
        }
      }
    }
    for (const [index, spawn] of parsedBots.entries()) {
      for (const structure of structures) {
        const clearance = pointAabbDistance(spawn, structure.box);
        if (clearance < 8 - 1e-6) {
          issue(
            issues,
            'bot-spawn-clearance-under-8m',
            `${path}.botSpawns[${index}]`,
            `${structure.path} is only ${clearance.toFixed(3)}m away`,
          );
        }
      }
    }
  }

  if (issues.length > 0 || mapSize === null) return { ok: false, issues };
  return {
    ok: true,
    issues,
    value: {
      status: 'PASS',
      mapSize,
      playerSpawns: parsedPlayers,
      botSpawns: parsedBots,
      roads: parsedRoads,
      landmarks: parsedLandmarks,
      ordinaryDistricts: parsedDistricts,
    },
  };
}

export function validatePlacementCatalog(
  table: PlacementTable,
  definitions: readonly StageDefinitionContract[],
): CatalogValidation {
  const issues: ValidationIssue[] = [];
  const definitionIds = new Set(definitions.map((item) => item.id));
  const tableIds = Object.keys(table);
  for (const id of tableIds) {
    if (!definitionIds.has(id)) issue(issues, 'unknown-generated-stage', `stages.${id}`, 'generated stage has no StageDef');
  }
  for (const definition of definitions) {
    const validation = validateStagePlacement(definition.id, table[definition.id], definition);
    issues.push(...validation.issues);
  }
  const landmarkIds = tableIds.flatMap((stageId) => {
    const raw = table[stageId];
    if (!isRecord(raw) || !Array.isArray(raw.landmarks)) return [];
    return raw.landmarks.flatMap((item) =>
      isRecord(item) && typeof item.id === 'string' ? [item.id] : []);
  });
  const landmarkCount = landmarkIds.length;
  const ordinaryDistrictCount = tableIds.reduce((sum, stageId) => {
    const raw = table[stageId];
    return sum + (isRecord(raw) && Array.isArray(raw.ordinaryDistricts) ? raw.ordinaryDistricts.length : 0);
  }, 0);
  const uniqueLandmarkCount = new Set(landmarkIds).size;
  if (definitions.length !== CANONICAL_STAGE_COUNT) {
    issue(issues, 'stage-count', 'catalog', `expected ${CANONICAL_STAGE_COUNT} StageDefs, got ${definitions.length}`);
  }
  if (tableIds.length !== CANONICAL_STAGE_COUNT) {
    issue(issues, 'generated-stage-count', 'catalog', `expected ${CANONICAL_STAGE_COUNT} generated stages, got ${tableIds.length}`);
  }
  if (landmarkCount !== CANONICAL_LANDMARK_COUNT) {
    issue(issues, 'catalog-landmark-count', 'catalog', `expected ${CANONICAL_LANDMARK_COUNT} landmarks, got ${landmarkCount}`);
  }
  if (uniqueLandmarkCount !== CANONICAL_LANDMARK_COUNT) {
    issue(issues, 'catalog-landmark-uniqueness', 'catalog', `expected ${CANONICAL_LANDMARK_COUNT} globally unique landmark ids, got ${uniqueLandmarkCount}`);
  }
  if (ordinaryDistrictCount !== CANONICAL_ORDINARY_DISTRICT_COUNT) {
    issue(issues, 'catalog-district-count', 'catalog', `expected ${CANONICAL_ORDINARY_DISTRICT_COUNT} ordinary districts, got ${ordinaryDistrictCount}`);
  }
  const training = table.renshujo;
  if (!isRecord(training) || training.mapSize !== 236) {
    issue(issues, 'renshujo-map-size', 'stages.renshujo.mapSize', 'renshujo must be migrated to 236m');
  }
  return {
    ok: issues.length === 0,
    issues,
    stageCount: tableIds.length,
    landmarkCount,
    ordinaryDistrictCount,
    uniqueLandmarkCount,
  };
}

/**
 * Fail closed for the generated feature, fail open to the proven procedural path.
 * A stage must be explicitly approved and independently valid. One invalid stage
 * cannot opt in another stage and cannot abort match creation.
 */
export function resolveReleasedStagePlacement(
  table: PlacementTable,
  definition: StageDefinitionContract,
  gate: GeneratedPlacementReleaseGate,
): PlacementResolution {
  if (!gate.approvedStageIds.has(definition.id)) {
    return { source: 'legacy', reason: 'not-approved', issues: [] };
  }
  const raw = table[definition.id];
  if (raw === undefined) {
    return {
      source: 'legacy',
      reason: 'missing',
      issues: [{ code: 'missing-stage', path: `stages.${definition.id}`, message: 'generated stage placement is missing' }],
    };
  }
  const validation = validateStagePlacement(definition.id, raw, definition);
  if (!validation.ok || !validation.value) {
    return { source: 'legacy', reason: 'invalid', issues: validation.issues };
  }
  return { source: 'generated', reason: 'approved', issues: [], placement: validation.value };
}
