// Runtime release slice for solver v2.  DO NOT add a stage here merely because
// the full catalog solver passed: this table and the stage-scoped allow-list
// must advance together only after Blender, collision, mode, and real-browser
// approval.  Keeping the empty slice separate prevents the 31-stage authoring
// table from increasing the production bundle while no stage is released.
import {
  STAGE_PLACEMENT_SOLVER_SHA256,
  STAGE_WORLD_CATALOG_SHA256,
  type SolverStageId,
  type SolverStagePlacement,
} from './stage-placements.generated';

export { STAGE_PLACEMENT_SOLVER_SHA256, STAGE_WORLD_CATALOG_SHA256 };

export const RELEASED_SOLVER_V2_STAGE_PLACEMENTS: Readonly<
  Partial<Record<SolverStageId, SolverStagePlacement>>
> = Object.freeze({});
