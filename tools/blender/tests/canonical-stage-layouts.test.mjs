import assert from 'node:assert/strict';
import test from 'node:test';
import { validateCanonicalLayouts } from '../validate-canonical-stage-layouts.mjs';

function stage(id, size = 300) {
  const make = (ordinal, cx) => ({
    id: `${id}-hero-${ordinal}`,
    cx,
    cz: 0,
    width: 50,
    depth: 40,
    height: 45,
    grounded: true,
    combatSpace: true,
    entrance: [cx, 20],
    approach: { start: [cx, 50], end: [cx, 20], width: 12 },
  });
  return {
    id,
    size,
    sourceStageSizeM: id === 'renshujo' ? 200 : size,
    authoringStageSizeM: size,
    placementSource: 'canonical-solver-v2-authoring',
    landmarkPlacements: [make(0, -50), make(1, 50)],
  };
}

function validDocument() {
  const stages = Array.from({ length: 30 }, (_, index) => stage(`s${String(index).padStart(2, '0')}`));
  stages.push(stage('renshujo', 236));
  return { placementSource: 'canonical-solver-v2-authoring', stages };
}

test('accepts exactly 31 stages and 62 unique playable in-bounds landmarks', () => {
  const report = validateCanonicalLayouts(validDocument());
  assert.equal(report.ok, true, JSON.stringify(report.errors));
});

test('rejects an outside, duplicate and disconnected landmark contract', () => {
  const document = validDocument();
  const first = document.stages[0].landmarkPlacements[0];
  first.cx = 149;
  document.stages[0].landmarkPlacements[1].id = first.id;
  document.stages[0].landmarkPlacements[1].approach.end = [0, 0];
  const report = validateCanonicalLayouts(document);
  assert.equal(report.ok, false);
  assert.ok(report.errors.some((item) => item.includes('outside-playable-bounds')));
  assert.ok(report.errors.some((item) => item.includes('duplicate-landmark-id')));
  assert.ok(report.errors.some((item) => item.includes('approach-end-mismatch')));
});
