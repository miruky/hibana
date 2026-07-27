import { describe, expect, it } from 'vitest';
import {
  SOLVER_V2_STAGE_PLACEMENTS,
  STAGE_PLACEMENT_SOLVER_SHA256,
  STAGE_WORLD_CATALOG_SHA256,
} from './generated/stage-placements.generated';
import {
  GENERATED_STAGE_PLACEMENT_PROVENANCE,
  RELEASED_GENERATED_STAGE_PLACEMENT_IDS,
  resolveGeneratedStagePlacement,
} from './stage-placement-runtime';
import { RELEASED_SOLVER_V2_STAGE_PLACEMENTS } from './generated/stage-placements.release.generated';
import {
  CONSTRUCTION_SEQUENCE,
  resolveReleasedStagePlacement,
  validateStagePlacement,
} from './stage-placement-runtime-core';
import { generateStageFromGeneratedPlacement } from './stage';
import { STAGES, stageById } from './stages';

describe('generated stage placement runtime boundary', () => {
  it('keeps the release allow-list empty until per-stage browser approval', () => {
    expect(RELEASED_GENERATED_STAGE_PLACEMENT_IDS).toEqual([]);
    expect(Object.keys(RELEASED_SOLVER_V2_STAGE_PLACEMENTS)).toEqual(
      RELEASED_GENERATED_STAGE_PLACEMENT_IDS,
    );
    expect(CONSTRUCTION_SEQUENCE).toEqual([
      'landmarks',
      'roads-and-approaches',
      'ordinary-districts',
      'spawns',
      'props-and-cover',
    ]);

    const resolution = resolveGeneratedStagePlacement(stageById('kairou'));
    expect(resolution.placement).toBeNull();
    expect(resolution.diagnostic).toEqual({
      source: 'legacy',
      reason: 'not-approved',
      issues: [],
    });
  });

  it('exposes exact solver and catalog provenance', () => {
    expect(GENERATED_STAGE_PLACEMENT_PROVENANCE).toEqual({
      solverSha256: STAGE_PLACEMENT_SOLVER_SHA256,
      catalogSha256: STAGE_WORLD_CATALOG_SHA256,
    });
  });

  it('validates solver-v2 stages while isolating the explicit renshujo size migration', () => {
    for (const definition of STAGES) {
      const raw = SOLVER_V2_STAGE_PLACEMENTS[
        definition.id as keyof typeof SOLVER_V2_STAGE_PLACEMENTS
      ];
      const validation = validateStagePlacement(definition.id, raw, definition);
      if (definition.id === 'renshujo') {
        expect(validation.ok).toBe(false);
        expect(validation.issues.map((issue) => issue.code)).toEqual([
          'stage-definition-size-mismatch',
        ]);
      } else {
        expect(validation.issues, definition.id).toEqual([]);
        expect(validation.ok, definition.id).toBe(true);
      }
    }
  });

  it('approves one valid stage without enabling any sibling stage', () => {
    const kunren = stageById('kunren');
    const gate = { approvedStageIds: new Set(['kunren']) };
    const approved = resolveReleasedStagePlacement(SOLVER_V2_STAGE_PLACEMENTS, kunren, gate);
    expect(approved.source).toBe('generated');

    const sibling = resolveReleasedStagePlacement(
      SOLVER_V2_STAGE_PLACEMENTS,
      stageById('souko'),
      gate,
    );
    expect(sibling).toEqual({ source: 'legacy', reason: 'not-approved', issues: [] });
  });

  it('rejects narrowed or internally inconsistent route geometry', () => {
    const definition = stageById('kunren');
    const source = SOLVER_V2_STAGE_PLACEMENTS.kunren;
    const narrowApproach = {
      ...source,
      landmarks: source.landmarks.map((landmark, index) => index === 0
        ? { ...landmark, approach: { ...landmark.approach, width: 8 } }
        : landmark),
    };
    expect(validateStagePlacement(definition.id, narrowApproach, definition).issues)
      .toEqual(expect.arrayContaining([
        expect.objectContaining({ code: 'narrow-approach' }),
      ]));

    const inconsistentRoad = {
      ...source,
      roads: source.roads.map((road, index) => index === 0
        ? { ...road, width: 12, centre: road.centre + 2 }
        : road),
    };
    const roadIssues = validateStagePlacement(definition.id, inconsistentRoad, definition).issues;
    expect(roadIssues).toEqual(expect.arrayContaining([
      expect.objectContaining({ code: 'primary-road-width-under-16m' }),
      expect.objectContaining({ code: 'road-width-bounds-mismatch' }),
      expect.objectContaining({ code: 'road-centre-bounds-mismatch' }),
    ]));
  });

  it('rejects an entrance whose approach terminates at a different point', () => {
    const definition = stageById('kunren');
    const source = SOLVER_V2_STAGE_PLACEMENTS.kunren;
    const corrupt = {
      ...source,
      landmarks: source.landmarks.map((landmark, index) => index === 0
        ? { ...landmark, entrance: [landmark.entrance[0] + 1, landmark.entrance[1]] }
        : landmark),
    };
    expect(validateStagePlacement(definition.id, corrupt, definition).issues)
      .toEqual(expect.arrayContaining([
        expect.objectContaining({ code: 'approach-end-entrance-mismatch' }),
      ]));
  });

  it('fails open to the procedural path when an approved payload is invalid', () => {
    const definition = stageById('kunren');
    const corrupt = {
      ...SOLVER_V2_STAGE_PLACEMENTS,
      kunren: { ...SOLVER_V2_STAGE_PLACEMENTS.kunren, roads: [] },
    };
    const resolution = resolveReleasedStagePlacement(
      corrupt,
      definition,
      { approvedStageIds: new Set(['kunren']) },
    );
    expect(resolution.source).toBe('legacy');
    expect(resolution.reason).toBe('invalid');
    expect(resolution.issues.some((issue) => issue.code === 'road-count')).toBe(true);
  });

  it('rebuilds a generated layout deterministically without stale districts or road blockers', () => {
    const definition = stageById('kunren');
    const validation = validateStagePlacement(
      definition.id,
      SOLVER_V2_STAGE_PLACEMENTS.kunren,
      definition,
    );
    expect(validation.issues).toEqual([]);
    expect(validation.value).toBeDefined();
    const placement = validation.value!;

    const first = generateStageFromGeneratedPlacement(definition, placement);
    const second = generateStageFromGeneratedPlacement(definition, placement);
    expect(second).toEqual(first);
    expect(first.playerSpawns).toEqual(placement.playerSpawns);
    expect(first.botSpawns).toEqual(placement.botSpawns);
    expect(first.landmarkPlacements).toEqual(placement.landmarks);
    expect(first.districtPlacements.slice(2)).toEqual(placement.ordinaryDistricts);
    expect(first.districtPlacements).toHaveLength(placement.ordinaryDistricts.length + 2);
    expect(first.boxes.filter((box) => box.ghost)).toHaveLength(4);

    const roadBlockers = first.boxes.filter((box) => {
      if (box.ghost || box.decor) return false;
      const bounds = {
        minX: box.x - box.w / 2,
        maxX: box.x + box.w / 2,
        minZ: box.z - box.d / 2,
        maxZ: box.z + box.d / 2,
      };
      return placement.roads.some((road) => (
        bounds.minX < road.bounds.maxX
        && bounds.maxX > road.bounds.minX
        && bounds.minZ < road.bounds.maxZ
        && bounds.maxZ > road.bounds.minZ
      ));
    });
    expect(roadBlockers).toEqual([]);
  });

  it('exports exactly 44 collision-authoritative Souko roof-monitor proxies from 12 stable supports', () => {
    const definition = stageById('souko');
    const validation = validateStagePlacement(
      definition.id,
      SOLVER_V2_STAGE_PLACEMENTS.souko,
      definition,
    );
    expect(validation.issues).toEqual([]);
    const layout = generateStageFromGeneratedPlacement(definition, validation.value!);
    const supports = layout.boxes
      .map((box, originalIndex) => ({ box, originalIndex }))
      .filter(({ box }) => box.roofMonitorSupport === true)
      .sort((a, b) => (
        b.box.w * b.box.h * b.box.d - a.box.w * a.box.h * a.box.d
        || a.originalIndex - b.originalIndex
      ));
    expect(supports).toHaveLength(12);
    expect(supports.every(({ box }) => box.structural === true)).toBe(true);
    expect(supports.map(({ box }) => [box.district, box.x, box.z, box.w, box.d])).toEqual([
      ['terminal', 28, -44, 24, 58],
      ['terminal', 96, -72, 58, 24],
      ['terminal', -56, -128, 58, 24],
      ['hangar', -100, 112, 22, 40],
      ['hangar', -104, 72, 40, 22],
      ['hangar', -36, 28, 40, 22],
      ['warehouse', -150, 48, 24, 12],
      ['warehouse', -122, 48, 24, 12],
      ['warehouse', -128, -58, 12, 24],
      ['warehouse', -128, -86, 12, 24],
      ['warehouse', -106, -120, 24, 12],
      ['warehouse', -134, -120, 24, 12],
    ]);

    const proxies = layout.boxes.filter((box) => box.roofMonitor !== undefined);
    expect(proxies).toHaveLength(44);
    expect(proxies.filter((box) => box.roofMonitor?.part === 'curb')).toHaveLength(12);
    expect(proxies.filter((box) => box.roofMonitor?.part === 'body')).toHaveLength(16);
    expect(proxies.filter((box) => box.roofMonitor?.part === 'roof-proxy')).toHaveLength(16);
    expect(proxies.every((box) => (
      box.structural === true
      && box.district !== undefined
      && box.visualReplacement === 'souko-roof-monitor-v1'
      && box.breakable === undefined
      && box.w > 0 && box.h > 0 && box.d > 0
    ))).toBe(true);

    for (const [supportIndex, { box: support }] of supports.entries()) {
      const owned = proxies.filter((box) => box.roofMonitor?.supportIndex === supportIndex);
      const variant = (supportIndex % 3) as 0 | 1 | 2;
      expect(new Set(owned.map((box) => box.roofMonitor?.variant))).toEqual(new Set([variant]));
      expect(owned.filter((box) => box.roofMonitor?.part === 'curb')).toHaveLength(1);
      expect(owned.filter((box) => box.roofMonitor?.part === 'body'))
        .toHaveLength(variant === 2 ? 2 : 1);
      expect(owned.filter((box) => box.roofMonitor?.part === 'roof-proxy'))
        .toHaveLength(variant === 2 ? 2 : 1);
      expect(owned.every((box) => box.district === support.district)).toBe(true);

      const supportTop = support.y + support.h / 2;
      const curb = owned.find((box) => box.roofMonitor?.part === 'curb')!;
      expect(curb.y - curb.h / 2).toBeCloseTo(supportTop - 0.04, 8);
      expect(curb.y + curb.h / 2).toBeCloseTo(supportTop + 0.46, 8);
      expect(Math.abs(curb.x - support.x) + curb.w / 2).toBeLessThanOrEqual(support.w / 2);
      expect(Math.abs(curb.z - support.z) + curb.d / 2).toBeLessThanOrEqual(support.d / 2);

      const bodies = owned.filter((box) => box.roofMonitor?.part === 'body');
      const roofs = owned.filter((box) => box.roofMonitor?.part === 'roof-proxy');
      for (const body of bodies) {
        if (body.roofMonitor?.part !== 'body') throw new Error('body discriminator drift');
        const bodySegmentIndex = body.roofMonitor.segmentIndex;
        const roof = roofs.find((candidate) => (
          candidate.roofMonitor?.part === 'roof-proxy'
          && candidate.roofMonitor.segmentIndex === bodySegmentIndex
        ));
        expect(roof).toBeDefined();
        expect(body.y - body.h / 2).toBeCloseTo(supportTop + 0.41, 8);
        expect(curb.y + curb.h / 2 - (body.y - body.h / 2)).toBeCloseTo(0.05, 8);
        expect(roof!.y - roof!.h / 2).toBeCloseTo(body.y + body.h / 2 - 0.06, 8);
        expect(roof!.w).toBeGreaterThan(body.w);
        expect(roof!.d).toBeGreaterThan(body.d);
        expect(Math.abs(roof!.x - support.x) + roof!.w / 2).toBeLessThanOrEqual(support.w / 2);
        expect(Math.abs(roof!.z - support.z) + roof!.d / 2).toBeLessThanOrEqual(support.d / 2);
      }
    }

    const curbVariants = proxies
      .filter((box) => box.roofMonitor?.part === 'curb')
      .map((box) => box.roofMonitor!.variant);
    expect(curbVariants.filter((variant) => variant === 0)).toHaveLength(4);
    expect(curbVariants.filter((variant) => variant === 1)).toHaveLength(4);
    expect(curbVariants.filter((variant) => variant === 2)).toHaveLength(4);
  });
});
