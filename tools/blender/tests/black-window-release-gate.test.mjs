import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { Document, NodeIO } from '@gltf-transform/core';

import {
  FACADE_AUDIT_VERSION,
  auditAsset,
  auditDocument,
} from '../validate-black-window-release-gate.mjs';

const STAGE_ID = 'kunren';
const GENERATOR_SHA = 'a'.repeat(64);

function stageExtras(lod, additions = {}) {
  return {
    hibanaStage: STAGE_ID,
    hibanaLod: lod,
    hibanaGeneratorSha: GENERATOR_SHA,
    ...additions,
  };
}

function auditExtras(overrides = {}) {
  return {
    hibanaFacadeAuditVersion: FACADE_AUDIT_VERSION,
    hibanaFacadeGlassPaneCount: 1,
    hibanaFacadeGlassMaxEqualSizeRepeat: 1,
    hibanaFacadeGlassMinWallClearanceM: 0.013,
    hibanaFacadeGlassMaxWallClearanceM: 0.013,
    hibanaFacadeGlassMinFrameRecessM: 0.147,
    hibanaFacadeGlassNearCoplanarCount: 0,
    hibanaFacadeGlassFloatingCount: 0,
    hibanaFacadeGlassEmbeddedCount: 0,
    hibanaFacadeDarkCardCount: 0,
    ...overrides,
  };
}

function createFixture(lod = 0) {
  const document = new Document();
  const buffer = document.createBuffer('fixture-buffer');
  const scene = document.createScene('fixture-scene');
  return { document, buffer, scene, lod };
}

function createMaterial(document, name, baseColor, additions = {}) {
  return document
    .createMaterial(name)
    .setBaseColorFactor(baseColor)
    .setRoughnessFactor(0.35)
    .setMetallicFactor(0.1)
    .setExtras(additions);
}

function boxArrays(center, size) {
  const [cx, cy, cz] = center;
  const [width, height, depth] = size;
  const x = width / 2;
  const y = height / 2;
  const z = depth / 2;
  const positions = new Float32Array([
    cx - x,
    cy - y,
    cz - z,
    cx + x,
    cy - y,
    cz - z,
    cx + x,
    cy + y,
    cz - z,
    cx - x,
    cy + y,
    cz - z,
    cx - x,
    cy - y,
    cz + z,
    cx + x,
    cy - y,
    cz + z,
    cx + x,
    cy + y,
    cz + z,
    cx - x,
    cy + y,
    cz + z,
  ]);
  const indices = new Uint16Array([
    0, 3, 2, 0, 2, 1, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2, 3, 7, 2, 7, 6, 3, 0,
    4, 3, 4, 7,
  ]);
  return { positions, indices };
}

function addBox(fixture, { name, center, size, material, extras }) {
  const { positions, indices } = boxArrays(center, size);
  const position = fixture.document
    .createAccessor(`${name}-position`, fixture.buffer)
    .setType('VEC3')
    .setArray(positions);
  const index = fixture.document
    .createAccessor(`${name}-indices`, fixture.buffer)
    .setType('SCALAR')
    .setArray(indices);
  const primitive = fixture.document
    .createPrimitive(`${name}-primitive`)
    .setAttribute('POSITION', position)
    .setIndices(index)
    .setMaterial(material);
  const mesh = fixture.document.createMesh(`${name}-mesh`).addPrimitive(primitive);
  const node = fixture.document.createNode(name).setMesh(mesh).setExtras(extras);
  fixture.scene.addChild(node);
  return node;
}

function addDome(fixture, { name, material, extras }) {
  const segments = 12;
  const positions = [];
  const indices = [];
  positions.push(0, 4.2, 0);
  for (let ring = 0; ring < 3; ring += 1) {
    const phi = ((ring + 1) / 4) * (Math.PI / 2);
    for (let segment = 0; segment < segments; segment += 1) {
      const theta = (segment / segments) * Math.PI * 2;
      positions.push(
        Math.cos(theta) * Math.sin(phi) * 3.5,
        4.2 - (1 - Math.cos(phi)) * 3.5,
        Math.sin(theta) * Math.sin(phi) * 3.5,
      );
    }
  }
  for (let segment = 0; segment < segments; segment += 1) {
    const next = (segment + 1) % segments;
    indices.push(0, 1 + segment, 1 + next);
  }
  for (let ring = 0; ring < 2; ring += 1) {
    const lower = 1 + ring * segments;
    const upper = lower + segments;
    for (let segment = 0; segment < segments; segment += 1) {
      const next = (segment + 1) % segments;
      indices.push(lower + segment, upper + segment, upper + next);
      indices.push(lower + segment, upper + next, lower + next);
    }
  }
  const position = fixture.document
    .createAccessor(`${name}-position`, fixture.buffer)
    .setType('VEC3')
    .setArray(new Float32Array(positions));
  const index = fixture.document
    .createAccessor(`${name}-indices`, fixture.buffer)
    .setType('SCALAR')
    .setArray(new Uint16Array(indices));
  const primitive = fixture.document
    .createPrimitive(`${name}-primitive`)
    .setAttribute('POSITION', position)
    .setIndices(index)
    .setMaterial(material);
  const mesh = fixture.document.createMesh(`${name}-mesh`).addPrimitive(primitive);
  const node = fixture.document.createNode(name).setMesh(mesh).setExtras(extras);
  fixture.scene.addChild(node);
  return node;
}

function buildFacade({
  lod = 0,
  paneCenterZ = 0.226,
  glassColor = [0.18, 0.21, 0.24, 1],
  metrics = {},
  paneCount = 1,
} = {}) {
  const fixture = createFixture(lod);
  const wall = createMaterial(fixture.document, `HBMAT_${STAGE_ID}_wall`, [0.55, 0.48, 0.4, 1]);
  const glass = createMaterial(fixture.document, `HBMAT_${STAGE_ID}_glass`, glassColor);
  addBox(fixture, {
    name: `HB_${STAGE_ID}_LOD${lod}_wall`,
    center: [0, 3, 0],
    size: [60, 6, 0.4],
    material: wall,
    extras: stageExtras(lod, {
      hibanaMaterial: 'wall',
      hibanaFacadeAuditRole: 'facade-support',
    }),
  });
  for (let index = 0; index < paneCount; index += 1) {
    addBox(fixture, {
      name: `HB_${STAGE_ID}_LOD${lod}_glass_${index}`,
      center: [index * 2 - (paneCount - 1), 2.8, paneCenterZ],
      size: [1.4, 1.2, 0.026],
      material: glass,
      extras: stageExtras(lod, {
        hibanaMaterial: 'glass',
        hibanaFacadeAuditRole: 'facade-pane',
        ...(index === 0 ? auditExtras(metrics) : {}),
      }),
    });
  }
  return fixture;
}

function issueCodes(report) {
  return new Set(report.issues.map((issue) => issue.code));
}

test('good recessed neutral facade and controlled semantic exceptions pass', () => {
  const fixture = buildFacade();
  const glass = createMaterial(
    fixture.document,
    `HBMAT_${STAGE_ID}_glass_detail`,
    [0.2, 0.24, 0.28, 1],
  );
  addDome(fixture, {
    name: `HB_${STAGE_ID}_LOD0_OBSERVATORY_DOME_glass`,
    material: glass,
    extras: stageExtras(0, {
      hibanaMaterial: 'glass',
      hibanaFacadeAuditRole: 'observatory-dome',
    }),
  });
  addBox(fixture, {
    name: `HB_${STAGE_ID}_LOD0_DEEP_ENTRANCE_glass`,
    center: [12, 1.6, 2],
    size: [1.8, 2.8, 0.08],
    material: glass,
    extras: stageExtras(0, {
      hibanaMaterial: 'glass',
      hibanaFacadeAuditRole: 'deep-entrance',
    }),
  });
  const interiorWall = createMaterial(
    fixture.document,
    `HBMAT_${STAGE_ID}_wall_alt`,
    [0.04, 0.05, 0.06, 1],
  );
  addBox(fixture, {
    name: `HB_${STAGE_ID}_LOD0_INTERIOR_SERVICE_PANEL`,
    center: [-12, 1.7, -2],
    size: [1.2, 1.4, 0.08],
    material: interiorWall,
    extras: stageExtras(0, {
      hibanaMaterial: 'wall_alt',
      hibanaFacadeAuditRole: 'interior-wall',
      hibanaInteriorZone: true,
    }),
  });
  const report = auditDocument(fixture.document, { stageId: STAGE_ID, lod: 0 });
  assert.equal(report.ok, true, JSON.stringify(report.issues, null, 2));
  assert.equal(report.metrics.geometry.placementChecked, 1);
});

test('thin opaque near-black glass card is a blocker', () => {
  const fixture = buildFacade({
    glassColor: [0.01, 0.026, 0.046, 1],
    metrics: { hibanaFacadeDarkCardCount: 1 },
  });
  const report = auditDocument(fixture.document, { stageId: STAGE_ID, lod: 0 });
  const codes = issueCodes(report);
  assert(codes.has('extremely-dark-glass-material'));
  assert(codes.has('thin-dark-facade-card'));
});

test('near-coplanar, floating, and embedded pane placement are distinguished', async (suite) => {
  const cases = [
    {
      name: 'near-coplanar',
      center: 0.215,
      metrics: {
        hibanaFacadeGlassMinWallClearanceM: 0.002,
        hibanaFacadeGlassMaxWallClearanceM: 0.002,
        hibanaFacadeGlassNearCoplanarCount: 1,
      },
      code: 'near-coplanar-facade-pane',
    },
    {
      name: 'floating',
      center: 0.413,
      metrics: {
        hibanaFacadeGlassMinWallClearanceM: 0.2,
        hibanaFacadeGlassMaxWallClearanceM: 0.2,
        hibanaFacadeGlassFloatingCount: 1,
      },
      code: 'floating-facade-pane',
    },
    {
      name: 'embedded',
      center: 0.19,
      metrics: {
        hibanaFacadeGlassMinWallClearanceM: -0.023,
        hibanaFacadeGlassMaxWallClearanceM: -0.023,
        hibanaFacadeGlassEmbeddedCount: 1,
      },
      code: 'embedded-facade-pane',
    },
  ];
  for (const fixtureCase of cases) {
    await suite.test(fixtureCase.name, () => {
      const fixture = buildFacade({
        paneCenterZ: fixtureCase.center,
        metrics: fixtureCase.metrics,
      });
      const report = auditDocument(fixture.document, { stageId: STAGE_ID, lod: 0 });
      assert(issueCodes(report).has(fixtureCase.code), JSON.stringify(report.issues, null, 2));
    });
  }
});

test('more than sixteen same-size facade panes is rejected', () => {
  const fixture = buildFacade({
    paneCount: 17,
    metrics: {
      hibanaFacadeGlassPaneCount: 17,
      hibanaFacadeGlassMaxEqualSizeRepeat: 17,
    },
  });
  const report = auditDocument(fixture.document, { stageId: STAGE_ID, lod: 0 });
  assert(issueCodes(report).has('equal-size-facade-repeat'));
});

test('LOD2 carries no facade window cards', () => {
  const fixture = buildFacade({ lod: 2 });
  const report = auditDocument(fixture.document, { stageId: STAGE_ID, lod: 2 });
  const codes = issueCodes(report);
  assert(codes.has('lod2-window-card'));
  assert(codes.has('facade-pane-count-limit'));
});

test('legacy merged glass without placement metadata is not silently accepted', () => {
  const fixture = createFixture(0);
  const glass = createMaterial(fixture.document, `HBMAT_${STAGE_ID}_glass`, [0.18, 0.21, 0.24, 1]);
  addBox(fixture, {
    name: `HB_${STAGE_ID}_LOD0_glass`,
    center: [0, 2.8, 0.226],
    size: [1.4, 1.2, 0.026],
    material: glass,
    extras: stageExtras(0, { hibanaMaterial: 'glass' }),
  });
  const report = auditDocument(fixture.document, { stageId: STAGE_ID, lod: 0 });
  const codes = issueCodes(report);
  assert(codes.has('missing-facade-audit-metadata'));
  assert(codes.has('unverifiable-pane-placement'));
});

test('generator SHA mismatch is reported separately from a passing visual gate', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'hibana-black-window-test-'));
  try {
    const fixture = buildFacade();
    const path = join(directory, 'kunren-lod0.glb');
    await new NodeIO().write(path, fixture.document);
    const audit = await auditAsset(path, STAGE_ID, 0, 'b'.repeat(64));
    assert.equal(audit.visual.ok, true, JSON.stringify(audit.visual.issues, null, 2));
    assert.equal(audit.provenance.ok, false);
    assert(audit.provenance.issues.some((issue) => issue.code === 'node-generator-sha-mismatch'));
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
