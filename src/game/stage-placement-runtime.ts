/**
 * Fail-closed runtime boundary for the canonical solver-v2 placement table.
 *
 * The generated table deliberately exposes roads and ordinary districts as
 * unknown payloads.  They are validated and cloned here before a stage can
 * replace the established procedural layout.  The release allow-list remains
 * empty until visual geometry, collision, modes, motion, and browser audits use
 * the same coordinates for that individual stage.
 */
import {
  RELEASED_SOLVER_V2_STAGE_PLACEMENTS,
  STAGE_PLACEMENT_SOLVER_SHA256,
  STAGE_WORLD_CATALOG_SHA256,
} from './generated/stage-placements.release.generated';
import type { StageDef } from './stage';
import {
  resolveReleasedStagePlacement,
  type RuntimeStagePlacement,
} from './stage-placement-runtime-core';

/**
 * Stage-scoped release switch.  Empty is intentional: catalog completeness or
 * a solver PASS alone is not permission to alter live gameplay.
 */
export const RELEASED_GENERATED_STAGE_PLACEMENT_IDS = [] as const satisfies readonly string[];

const RELEASE_GATE = {
  approvedStageIds: new Set<string>(RELEASED_GENERATED_STAGE_PLACEMENT_IDS),
};

export const GENERATED_STAGE_PLACEMENT_PROVENANCE = Object.freeze({
  solverSha256: STAGE_PLACEMENT_SOLVER_SHA256,
  catalogSha256: STAGE_WORLD_CATALOG_SHA256,
});

export interface GeneratedStagePlacementDiagnostic {
  source: 'generated' | 'legacy';
  reason: 'approved' | 'not-approved' | 'missing' | 'invalid';
  issues: readonly { code: string; path: string; message: string }[];
}

export function resolveGeneratedStagePlacement(
  def: Pick<StageDef, 'id' | 'size' | 'botCount'>,
): { placement: RuntimeStagePlacement | null; diagnostic: GeneratedStagePlacementDiagnostic } {
  const resolution = resolveReleasedStagePlacement(
    RELEASED_SOLVER_V2_STAGE_PLACEMENTS,
    def,
    RELEASE_GATE,
  );
  if (resolution.source === 'generated') {
    return {
      placement: resolution.placement,
      diagnostic: { source: 'generated', reason: 'approved', issues: [] },
    };
  }
  return {
    placement: null,
    diagnostic: {
      source: 'legacy',
      reason: resolution.reason,
      issues: resolution.issues,
    },
  };
}
