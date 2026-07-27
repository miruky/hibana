import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '..', '..', '..');
const generator = readFileSync(path.join(repo, 'tools/blender/build_all_stages.py'), 'utf8');
const solverSource = readFileSync(
  path.join(repo, 'src/game/generated/stage-placements.generated.ts'),
  'utf8',
);

function pythonNumber(name) {
  const match = generator.match(new RegExp(`^${name} = ([0-9.]+)$`, 'm'));
  assert.ok(match, `missing ${name}`);
  return Number(match[1]);
}

function solverPlacements() {
  const match = solverSource.match(
    /export const SOLVER_V2_STAGE_PLACEMENTS = (\{[\s\S]*?\}) as const satisfies/,
  );
  assert.ok(match, 'unable to parse solver-v2 placements');
  return JSON.parse(match[1]);
}

function functionBody(name, nextName) {
  const start = generator.indexOf(`def ${name}(`);
  const end = generator.indexOf(`\ndef ${nextName}(`, start + 1);
  assert.ok(start >= 0 && end > start, `unable to isolate ${name}`);
  return generator.slice(start, end);
}

test('Souko canonical connection map remains solver-authored', () => {
  const souko = solverPlacements().souko;
  assert.equal(souko.status, 'PASS');
  assert.equal(souko.mapSize, 336);
  assert.deepEqual(souko.playerSpawns, [
    [-156, 0, 0],
    [0, 0, -156],
    [156, 0, 0],
    [0, 0, 156],
  ]);
  assert.deepEqual(souko.roads, [
    {
      id: 'primary-north-south',
      axis: 'z',
      centre: 0,
      width: 16,
      bounds: { minX: -8, maxX: 8, minZ: -164, maxZ: 164 },
    },
    {
      id: 'primary-east-west',
      axis: 'x',
      centre: 0,
      width: 16,
      bounds: { minX: -164, maxX: 164, minZ: -8, maxZ: 8 },
    },
  ]);
  assert.deepEqual(
    souko.landmarks.map(({ id, cx, cz, width, depth, height, entrance, approach }) => ({
      id,
      cx,
      cz,
      width,
      depth,
      height,
      entrance,
      approach,
    })),
    [
      {
        id: 'souko-shiosai-stackhouse',
        cx: 80.8,
        cz: 96,
        width: 104,
        depth: 66,
        height: 64,
        entrance: [28, 96],
        approach: { start: [8, 96], end: [28, 96], width: 12 },
      },
      {
        id: 'souko-amakado-customs-terminal',
        cx: -68,
        cz: -67.8,
        width: 92,
        depth: 78,
        height: 47,
        entrance: [-68, -28],
        approach: { start: [-68, -8], end: [-68, -28], width: 12 },
      },
    ],
  );
});

test('A18 raised geometry preserves traversal and arrival clearance', () => {
  assert.equal(pythonNumber('SOUKO_STACKHOUSE_RACK_BASE_M'), 12.82);
  assert.ok(pythonNumber('SOUKO_STACKHOUSE_SKYBRIDGE_BOTTOM_M') >= 13);
  assert.ok(pythonNumber('SOUKO_CUSTOMS_ROOF_BASE_M') >= 9.87);
  assert.ok(pythonNumber('SOUKO_CUSTOMS_CANOPY_BOTTOM_M') >= 9.7);
  assert.equal(pythonNumber('SOUKO_ROUTE_VISUAL_MARGIN_M'), 2);
  assert.equal(pythonNumber('SOUKO_SPAWN_CLEARANCE_M'), 30);

  const signature = functionBody('add_catalog_landmark_signature', 'landmark_arrival_frame_specs');
  assert.match(signature, /rack_laterals = \(-32\.0, 0\.0, 32\.0\)/);
  assert.match(signature, /bridge_bottom = SOUKO_STACKHOUSE_SKYBRIDGE_BOTTOM_M/);
  assert.match(signature, /bay_count = 4/);
  assert.match(signature, /roof_base = SOUKO_CUSTOMS_ROOF_BASE_M/);
  assert.match(signature, /canopy_bottom = SOUKO_CUSTOMS_CANOPY_BOTTOM_M/);
  assert.match(signature, /control_deck_bottom = min\(/);
  assert.match(signature, /process_specs = \(/);
  assert.match(signature, /truss_bays = 6 if lod == 0 else 4/);
  assert.match(signature, /stack_specs = \(\(-34\.5, -29\.0, 45\.5\)/);
  assert.match(signature, /cluster_lateral in enumerate\(\(-25\.5, 25\.5\)\)/);

  const routeDressing = functionBody('add_route_set_dressing', 'add_district_public_realm');
  assert.match(routeDressing, /half_span = float\(landmark\["approach"\]\["width"\]\) \/ 2 \+ 1\.4/);
  assert.match(routeDressing, /frame_top = 8\.8 if lod == 0 else 8\.2/);
});

test('A18 coast is closed 3D geometry and replaces the generic east boundary', () => {
  const coast = functionBody('add_souko_coastal_edge', 'boundary_natural_sample_count');
  assert.match(coast, /builder\.add_box\([\s\S]*?"water"/);
  assert.match(coast, /builder\.add_box\(half \+ 2\.15, -1\.25/);
  assert.match(coast, /crane_zs = \(-76\.0, 66\.0\)/);
  assert.match(coast, /add_workboat\(builder, half \+ 66\.0/);
  assert.doesNotMatch(coast, /add_image|image_plane|billboard\s*\(/i);

  const boundary = functionBody('add_boundary', 'add_skyline');
  assert.match(boundary, /souko_coast = stage\["id"\] == "souko"/);
  assert.match(boundary, /if souko_coast and spec\["side"\] == 3:/);
  assert.match(boundary, /add_souko_coastal_edge\(builder, stage, lod, half\)/);
});

test('Souko owns wet logistics surface roles and LOD identity metadata', () => {
  for (const role of [
    'wet-zinc-steel',
    'wet-red-brick',
    'weathered-folded-zinc',
    'translucent-frp-antiglare',
    'orange-safety-paint',
  ]) {
    assert.match(generator, new RegExp(role));
  }
  assert.match(generator, /hibanaSoukoReferenceMatchVersion/);
  assert.match(generator, /hibanaSoukoEastCoast3D/);
  assert.match(generator, /2: \(13\.0, 35\.5, 58\.0\)/);
  assert.match(generator, /water\.diffuse_color = \(\*water\.diffuse_color\[:3\], 0\.97\)/);
  assert.match(generator, /tooth_rises = \(10\.8, 12\.1, 11\.3, 13\.0\)/);
  assert.match(generator, /add_workboat\(builder, half \+ 72\.0, 91\.0/);
});
