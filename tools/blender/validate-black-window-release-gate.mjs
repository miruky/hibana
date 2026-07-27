#!/usr/bin/env node

/**
 * Independent release gate for Hibana's repeated black facade-card failure.
 *
 * This intentionally does not import build_all_stages.py.  It inspects the
 * shipped GLB after meshopt compression, so a generator-side counter cannot
 * hide geometry that was transformed, duplicated, or exported incorrectly.
 * Generator provenance is reported separately from the visual facade gate.
 */

import { createHash } from 'node:crypto';
import { existsSync } from 'node:fs';
import { readFile, writeFile } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { NodeIO } from '@gltf-transform/core';
import {
  EXTMeshoptCompression,
  KHRMaterialsClearcoat,
  KHRMaterialsEmissiveStrength,
  KHRMeshQuantization,
} from '@gltf-transform/extensions';
import { MeshoptDecoder } from 'meshoptimizer';

export const EXPECTED_STAGE_IDS = Object.freeze([
  'kunren',
  'souko',
  'nakaniwa',
  'kairou',
  'kouwan',
  'takadai',
  'sakyuu',
  'setsugen',
  'koushou',
  'yoichi',
  'okujou',
  'saisekiba',
  'chikurin',
  'tanada',
  'misaki',
  'haieki',
  'kyokoku',
  'kohan',
  'kuko',
  'onsengai',
  'z01',
  'z02',
  'z03',
  'z04',
  'z05',
  'z06',
  'z07',
  'z08',
  'z09',
  'z10',
  'renshujo',
]);

export const FACADE_AUDIT_VERSION = 'black-window-v1';

export const REQUIRED_FACADE_EXTRAS = Object.freeze([
  'hibanaFacadeAuditVersion',
  'hibanaFacadeGlassPaneCount',
  'hibanaFacadeGlassMaxEqualSizeRepeat',
  'hibanaFacadeGlassMinWallClearanceM',
  'hibanaFacadeGlassMaxWallClearanceM',
  'hibanaFacadeGlassMinFrameRecessM',
  'hibanaFacadeGlassNearCoplanarCount',
  'hibanaFacadeGlassFloatingCount',
  'hibanaFacadeGlassEmbeddedCount',
  'hibanaFacadeDarkCardCount',
]);

const COUNT_EXTRA_KEYS = Object.freeze([
  'hibanaFacadeGlassPaneCount',
  'hibanaFacadeGlassMaxEqualSizeRepeat',
  'hibanaFacadeGlassNearCoplanarCount',
  'hibanaFacadeGlassFloatingCount',
  'hibanaFacadeGlassEmbeddedCount',
  'hibanaFacadeDarkCardCount',
]);

const DISTANCE_EXTRA_KEYS = Object.freeze([
  'hibanaFacadeGlassMinWallClearanceM',
  'hibanaFacadeGlassMaxWallClearanceM',
  'hibanaFacadeGlassMinFrameRecessM',
]);

const PANE_LIMITS = Object.freeze([120, 48, 0]);
const DARK_CARD_LIMITS = Object.freeze([96, 32, 0]);
const KAIROU_DARK_CARD_LIMITS = Object.freeze([0, 0, 0]);
const MAX_EQUAL_SIZE_REPEAT = 16;
const MIN_WALL_CLEARANCE_M = 0.008;
const MAX_WALL_CLEARANCE_M = 0.06;
const MIN_FRAME_RECESS_M = 0.08;
const DARK_GLASS_LUMINANCE = 0.055;
const WELD_PRECISION_M = 0.0001;

const CARD_MATERIAL_ROLES = new Set(['glass', 'wall_alt', 'wall_cool', 'accent']);
const WALL_MATERIAL_ROLES = new Set([
  'wall',
  'wall_alt',
  'wall_cool',
  'wall_warm',
  'wall_weathered',
]);
const MATERIAL_ROLES = Object.freeze([
  'wall_weathered',
  'wall_warm',
  'wall_cool',
  'wall_alt',
  'glass',
  'accent',
  'emissive',
  'trim',
  'wall',
  'wood',
  'roof',
  'terrain',
  'road',
  'floor',
  'obstacle',
  'natural',
  'water',
]);
const CONTROLLED_SEMANTIC_ROLES = new Set([
  'facade-pane',
  'facade-support',
  'deep-entrance',
  'interior-wall',
  'observatory-dome',
  'vehicle-glass',
  'decorative-glass',
]);

const MODULE_PATH = fileURLToPath(import.meta.url);
const PROJECT_ROOT = resolve(dirname(MODULE_PATH), '../..');

let ioPromise;

async function getIO() {
  if (!ioPromise) {
    ioPromise = (async () => {
      await MeshoptDecoder.ready;
      return new NodeIO()
        .registerExtensions([
          EXTMeshoptCompression,
          KHRMeshQuantization,
          KHRMaterialsClearcoat,
          KHRMaterialsEmissiveStrength,
        ])
        .registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
    })();
  }
  return ioPromise;
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

function isNonNegativeInteger(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

function luminance(rgb) {
  return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
}

function inferMaterialRole(nodeExtras, material) {
  const explicit = nodeExtras?.hibanaMaterial ?? material?.getExtras()?.hibanaMaterialRole;
  if (typeof explicit === 'string' && explicit.trim()) return explicit.trim();
  const name = material?.getName()?.toLowerCase() ?? '';
  return MATERIAL_ROLES.find((role) => name.endsWith(`_${role}`)) ?? 'unknown';
}

function materialReport(material, role) {
  const base = material?.getBaseColorFactor?.() ?? [1, 1, 1, 1];
  const emissive = material?.getEmissiveFactor?.() ?? [0, 0, 0];
  const alphaMode = material?.getAlphaMode?.() ?? 'OPAQUE';
  const extras = material?.getExtras?.() ?? {};
  const transmission = Number(extras.hibanaTransmissionFactor ?? 0);
  const baseLuminance = luminance(base);
  const emissiveLuminance = luminance(emissive);
  const transparent = alphaMode === 'BLEND' || base[3] < 0.9 || transmission >= 0.25;
  return {
    name: material?.getName?.() ?? '(material missing)',
    role,
    baseColorFactor: base.map((value) => Number(value.toFixed(6))),
    baseLuminance: Number(baseLuminance.toFixed(6)),
    emissiveLuminance: Number(emissiveLuminance.toFixed(6)),
    alphaMode,
    hasBaseColorTexture: Boolean(material?.getBaseColorTexture?.()),
    extremelyDarkGlass:
      role === 'glass' &&
      baseLuminance < DARK_GLASS_LUMINANCE &&
      emissiveLuminance < 0.02 &&
      !transparent,
  };
}

function transformPoint(matrix, point) {
  const [x, y, z] = point;
  return [
    matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
    matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
    matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
  ];
}

function roundedKey(point) {
  return point.map((value) => Math.round(value / WELD_PRECISION_M)).join(',');
}

class DisjointSet {
  constructor(size) {
    this.parent = Int32Array.from({ length: size }, (_, index) => index);
    this.rank = new Uint8Array(size);
  }

  find(value) {
    let root = value;
    while (this.parent[root] !== root) root = this.parent[root];
    while (this.parent[value] !== value) {
      const next = this.parent[value];
      this.parent[value] = root;
      value = next;
    }
    return root;
  }

  union(left, right) {
    left = this.find(left);
    right = this.find(right);
    if (left === right) return;
    if (this.rank[left] < this.rank[right]) [left, right] = [right, left];
    this.parent[right] = left;
    if (this.rank[left] === this.rank[right]) this.rank[left] += 1;
  }
}

function componentGeometry(points, triangleCount) {
  const minimum = [Infinity, Infinity, Infinity];
  const maximum = [-Infinity, -Infinity, -Infinity];
  let centerX = 0;
  let centerZ = 0;
  for (const point of points) {
    centerX += point[0];
    centerZ += point[2];
    for (let axis = 0; axis < 3; axis += 1) {
      minimum[axis] = Math.min(minimum[axis], point[axis]);
      maximum[axis] = Math.max(maximum[axis], point[axis]);
    }
  }
  centerX /= points.length;
  centerZ /= points.length;
  let xx = 0;
  let zz = 0;
  let xz = 0;
  for (const point of points) {
    const x = point[0] - centerX;
    const z = point[2] - centerZ;
    xx += x * x;
    zz += z * z;
    xz += x * z;
  }
  const angle = 0.5 * Math.atan2(2 * xz, xx - zz);
  const primary = [Math.cos(angle), Math.sin(angle)];
  const secondary = [-primary[1], primary[0]];
  let primaryMin = Infinity;
  let primaryMax = -Infinity;
  let secondaryMin = Infinity;
  let secondaryMax = -Infinity;
  for (const point of points) {
    const x = point[0] - centerX;
    const z = point[2] - centerZ;
    const first = x * primary[0] + z * primary[1];
    const second = x * secondary[0] + z * secondary[1];
    primaryMin = Math.min(primaryMin, first);
    primaryMax = Math.max(primaryMax, first);
    secondaryMin = Math.min(secondaryMin, second);
    secondaryMax = Math.max(secondaryMax, second);
  }
  const firstExtent = primaryMax - primaryMin;
  const secondExtent = secondaryMax - secondaryMin;
  const tangent = firstExtent >= secondExtent ? primary : secondary;
  const normal = firstExtent >= secondExtent ? secondary : primary;
  const width = Math.max(firstExtent, secondExtent);
  const thickness = Math.min(firstExtent, secondExtent);
  const height = maximum[1] - minimum[1];
  const boxLike =
    (points.length === 8 && triangleCount === 12) || (points.length === 4 && triangleCount === 2);
  return {
    bounds: [...minimum, ...maximum],
    center: [
      (minimum[0] + maximum[0]) / 2,
      (minimum[1] + maximum[1]) / 2,
      (minimum[2] + maximum[2]) / 2,
    ],
    width,
    height,
    thickness,
    tangent,
    normal,
    uniquePointCount: points.length,
    triangleCount,
    boxLike,
  };
}

/** Extract connected components after welding split normal/UV vertices by position. */
export function extractPrimitiveComponents(node, primitive) {
  const position = primitive.getAttribute('POSITION');
  if (!position || position.getCount() === 0) return [];
  const indices = primitive.getIndices();
  const vertexCount = position.getCount();
  const worldMatrix = node.getWorldMatrix();
  const originalToPoint = new Int32Array(vertexCount);
  const uniquePoints = [];
  const pointByPosition = new Map();
  const element = [0, 0, 0];
  for (let vertex = 0; vertex < vertexCount; vertex += 1) {
    position.getElement(vertex, element);
    const point = transformPoint(worldMatrix, element);
    const key = roundedKey(point);
    let pointIndex = pointByPosition.get(key);
    if (pointIndex === undefined) {
      pointIndex = uniquePoints.length;
      uniquePoints.push(point);
      pointByPosition.set(key, pointIndex);
    }
    originalToPoint[vertex] = pointIndex;
  }
  const sets = new DisjointSet(uniquePoints.length);
  const indexCount = indices ? indices.getCount() : vertexCount;
  const triangleRoots = [];
  for (let offset = 0; offset + 2 < indexCount; offset += 3) {
    const a = originalToPoint[indices ? indices.getScalar(offset) : offset];
    const b = originalToPoint[indices ? indices.getScalar(offset + 1) : offset + 1];
    const c = originalToPoint[indices ? indices.getScalar(offset + 2) : offset + 2];
    sets.union(a, b);
    sets.union(a, c);
    triangleRoots.push(a);
  }
  const pointsByRoot = new Map();
  uniquePoints.forEach((point, index) => {
    const root = sets.find(index);
    if (!pointsByRoot.has(root)) pointsByRoot.set(root, []);
    pointsByRoot.get(root).push(point);
  });
  const trianglesByRoot = new Map();
  for (const pointIndex of triangleRoots) {
    const root = sets.find(pointIndex);
    trianglesByRoot.set(root, (trianglesByRoot.get(root) ?? 0) + 1);
  }
  return [...pointsByRoot.entries()].map(([root, points]) =>
    componentGeometry(points, trianglesByRoot.get(root) ?? 0),
  );
}

function isThinVerticalCard(component) {
  const faceArea = component.width * component.height;
  return (
    component.boxLike &&
    component.thickness <= 0.22 &&
    component.width >= 0.35 &&
    component.width <= 4.8 &&
    component.height >= 0.45 &&
    component.height <= 3.2 &&
    faceArea >= 0.3 &&
    faceArea <= 20.0
  );
}

function semanticRole(nodeExtras) {
  const role = nodeExtras?.hibanaFacadeAuditRole;
  return typeof role === 'string' ? role : null;
}

function semanticExemption(component, role, nodeExtras) {
  if (!role || role === 'facade-pane' || role === 'facade-support') return false;
  if (!CONTROLLED_SEMANTIC_ROLES.has(role)) return false;
  if (role === 'observatory-dome' || role === 'decorative-glass') {
    return !component.boxLike || component.width >= 5 || component.height >= 4;
  }
  if (role === 'deep-entrance') {
    return component.height >= 2.2 && component.width >= 1.2;
  }
  if (role === 'interior-wall') {
    return nodeExtras?.hibanaInteriorZone === true;
  }
  if (role === 'vehicle-glass') {
    return component.width <= 3.5 && component.height <= 2.0;
  }
  return false;
}

function repeatSignature(component) {
  const quantum = 0.05;
  const width = Math.round(component.width / quantum) * quantum;
  const height = Math.round(component.height / quantum) * quantum;
  return `${width.toFixed(2)}x${height.toFixed(2)}`;
}

function projectBounds(bounds, axis) {
  const [minX, minY, minZ, maxX, maxY, maxZ] = bounds;
  const values = [
    minX * axis[0] + minZ * axis[1],
    minX * axis[0] + maxZ * axis[1],
    maxX * axis[0] + minZ * axis[1],
    maxX * axis[0] + maxZ * axis[1],
  ];
  return {
    min: Math.min(...values),
    max: Math.max(...values),
    minY,
    maxY,
  };
}

function intervalOverlap(leftMin, leftMax, rightMin, rightMax) {
  return Math.max(0, Math.min(leftMax, rightMax) - Math.max(leftMin, rightMin));
}

function intervalGap(leftMin, leftMax, rightMin, rightMax) {
  if (leftMin >= rightMax) return leftMin - rightMax;
  if (rightMin >= leftMax) return rightMin - leftMax;
  return -Math.min(leftMax, rightMax) + Math.max(leftMin, rightMin);
}

/** Return signed wall clearance: positive=outside, negative=embedded. */
function findWallClearance(pane, walls) {
  const paneNormal = projectBounds(pane.bounds, pane.normal);
  const paneTangent = projectBounds(pane.bounds, pane.tangent);
  const paneTangentSize = Math.max(1e-6, paneTangent.max - paneTangent.min);
  const paneHeight = Math.max(1e-6, paneTangent.maxY - paneTangent.minY);
  let best = null;
  for (const wall of walls) {
    const wallNormal = projectBounds(wall.bounds, pane.normal);
    const wallTangent = projectBounds(wall.bounds, pane.tangent);
    const tangentRatio =
      intervalOverlap(paneTangent.min, paneTangent.max, wallTangent.min, wallTangent.max) /
      paneTangentSize;
    const verticalRatio =
      intervalOverlap(paneTangent.minY, paneTangent.maxY, wallTangent.minY, wallTangent.maxY) /
      paneHeight;
    if (tangentRatio < 0.55 || verticalRatio < 0.55) continue;
    const clearance = intervalGap(paneNormal.min, paneNormal.max, wallNormal.min, wallNormal.max);
    const score = Math.abs(clearance) + (1 - tangentRatio) + (1 - verticalRatio);
    if (!best || score < best.score) best = { clearance, score };
  }
  return best?.clearance ?? null;
}

function addIssue(issueMap, code, count = 1, sample = undefined, severity = 'blocker') {
  if (count <= 0) return;
  if (!issueMap.has(code)) issueMap.set(code, { code, severity, count: 0, samples: [] });
  const issue = issueMap.get(code);
  issue.count += count;
  if (sample !== undefined && issue.samples.length < 5) issue.samples.push(sample);
}

function serialiseIssues(issueMap) {
  return [...issueMap.values()].sort((left, right) => left.code.localeCompare(right.code));
}

function collectMetricOwners(nodes, issueMap) {
  const owners = [];
  for (const node of nodes) {
    const extras = node.getExtras?.() ?? {};
    const hasMetric = REQUIRED_FACADE_EXTRAS.some((key) => key in extras);
    if (!hasMetric) continue;
    const missing = REQUIRED_FACADE_EXTRAS.filter((key) => !(key in extras));
    if (missing.length > 0) {
      addIssue(issueMap, 'facade-audit-owner-missing-field', missing.length, {
        node: node.getName(),
        missing,
      });
    }
    if (extras.hibanaFacadeAuditVersion !== FACADE_AUDIT_VERSION) {
      addIssue(issueMap, 'facade-audit-version', 1, {
        node: node.getName(),
        actual: extras.hibanaFacadeAuditVersion ?? null,
        expected: FACADE_AUDIT_VERSION,
      });
    }
    for (const key of COUNT_EXTRA_KEYS) {
      if (key in extras && !isNonNegativeInteger(extras[key])) {
        addIssue(issueMap, 'facade-audit-invalid-count', 1, {
          node: node.getName(),
          key,
          value: extras[key],
        });
      }
    }
    for (const key of DISTANCE_EXTRA_KEYS) {
      if (key in extras && !isFiniteNumber(extras[key])) {
        addIssue(issueMap, 'facade-audit-invalid-distance', 1, {
          node: node.getName(),
          key,
          value: extras[key],
        });
      }
    }
    owners.push({ node: node.getName(), extras });
  }
  if (owners.length === 0) addIssue(issueMap, 'missing-facade-audit-metadata');
  return owners;
}

function aggregateMetricOwners(owners) {
  const number = (owner, key, fallback = 0) =>
    isFiniteNumber(owner.extras[key]) ? owner.extras[key] : fallback;
  return {
    owners: owners.length,
    paneCount: owners.reduce((sum, owner) => sum + number(owner, 'hibanaFacadeGlassPaneCount'), 0),
    maxEqualSizeRepeat: owners.reduce(
      (maximum, owner) => Math.max(maximum, number(owner, 'hibanaFacadeGlassMaxEqualSizeRepeat')),
      0,
    ),
    minWallClearanceM: owners.length
      ? Math.min(
          ...owners.map((owner) => number(owner, 'hibanaFacadeGlassMinWallClearanceM', Infinity)),
        )
      : null,
    maxWallClearanceM: owners.length
      ? Math.max(
          ...owners.map((owner) => number(owner, 'hibanaFacadeGlassMaxWallClearanceM', -Infinity)),
        )
      : null,
    minFrameRecessM: owners.length
      ? Math.min(
          ...owners.map((owner) => number(owner, 'hibanaFacadeGlassMinFrameRecessM', Infinity)),
        )
      : null,
    nearCoplanarCount: owners.reduce(
      (sum, owner) => sum + number(owner, 'hibanaFacadeGlassNearCoplanarCount'),
      0,
    ),
    floatingCount: owners.reduce(
      (sum, owner) => sum + number(owner, 'hibanaFacadeGlassFloatingCount'),
      0,
    ),
    embeddedCount: owners.reduce(
      (sum, owner) => sum + number(owner, 'hibanaFacadeGlassEmbeddedCount'),
      0,
    ),
    darkCardCount: owners.reduce(
      (sum, owner) => sum + number(owner, 'hibanaFacadeDarkCardCount'),
      0,
    ),
  };
}

function checkMetricConsistency(metrics, issueMap) {
  if (metrics.owners === 0) return;
  if (metrics.paneCount === 0) return;
  if (
    metrics.minWallClearanceM < MIN_WALL_CLEARANCE_M &&
    metrics.nearCoplanarCount === 0 &&
    metrics.embeddedCount === 0
  ) {
    addIssue(issueMap, 'facade-audit-metadata-inconsistent', 1, 'min-clearance-without-count');
  }
  if (metrics.minFrameRecessM < MIN_FRAME_RECESS_M && metrics.nearCoplanarCount === 0) {
    addIssue(issueMap, 'facade-audit-metadata-inconsistent', 1, 'min-recess-without-count');
  }
  if (metrics.maxWallClearanceM > MAX_WALL_CLEARANCE_M && metrics.floatingCount === 0) {
    addIssue(issueMap, 'facade-audit-metadata-inconsistent', 1, 'max-clearance-without-floating');
  }
}

/** Audit one already-decoded glTF Transform document. */
export function auditDocument(document, { stageId, lod, sourcePath = '(memory)' }) {
  const issueMap = new Map();
  const nodes = document
    .getRoot()
    .listNodes()
    .filter((node) => {
      const extras = node.getExtras?.() ?? {};
      return (
        (extras.hibanaStage === stageId && extras.hibanaLod === lod) ||
        node.getName().startsWith(`HB_${stageId}_LOD${lod}_`)
      );
    });
  const metricOwners = collectMetricOwners(nodes, issueMap);
  const metadata = aggregateMetricOwners(metricOwners);
  checkMetricConsistency(metadata, issueMap);

  const materialByName = new Map();
  const paneComponents = [];
  const wallComponents = [];
  const thinCardComponents = [];
  const invalidExemptions = [];
  let componentsAnalysed = 0;

  for (const node of nodes) {
    const mesh = node.getMesh();
    if (!mesh) continue;
    const nodeExtras = node.getExtras?.() ?? {};
    const semantic = semanticRole(nodeExtras);
    if (semantic && !CONTROLLED_SEMANTIC_ROLES.has(semantic)) {
      addIssue(issueMap, 'unknown-facade-semantic-role', 1, {
        node: node.getName(),
        role: semantic,
      });
    }
    for (const primitive of mesh.listPrimitives()) {
      const material = primitive.getMaterial();
      const role = inferMaterialRole(nodeExtras, material);
      if (
        !CARD_MATERIAL_ROLES.has(role) &&
        !WALL_MATERIAL_ROLES.has(role) &&
        semantic !== 'facade-pane' &&
        semantic !== 'facade-support'
      )
        continue;
      const materialInfo = materialReport(material, role);
      materialByName.set(materialInfo.name, materialInfo);
      const components = extractPrimitiveComponents(node, primitive);
      componentsAnalysed += components.length;
      for (const component of components) {
        const value = {
          ...component,
          node: node.getName(),
          role,
          semantic,
          material: materialInfo.name,
          darkMaterial:
            materialInfo.extremelyDarkGlass ||
            (role !== 'glass' && materialInfo.baseLuminance < 0.11),
        };
        if (WALL_MATERIAL_ROLES.has(role) || semantic === 'facade-support') {
          wallComponents.push(value);
        }
        if (!isThinVerticalCard(component)) continue;
        const exempt = semanticExemption(component, semantic, nodeExtras);
        if (semantic && semantic !== 'facade-pane' && semantic !== 'facade-support' && !exempt)
          invalidExemptions.push(value);
        if (exempt) continue;
        if (role === 'glass' || semantic === 'facade-pane') paneComponents.push(value);
        if (CARD_MATERIAL_ROLES.has(role) || semantic === 'facade-pane') {
          thinCardComponents.push(value);
        }
      }
    }
  }

  if (invalidExemptions.length > 0) {
    addIssue(
      issueMap,
      'invalid-semantic-exemption',
      invalidExemptions.length,
      invalidExemptions.slice(0, 5).map((value) => ({
        node: value.node,
        role: value.semantic,
        dimensions: [value.width, value.height, value.thickness].map((number) =>
          Number(number.toFixed(4)),
        ),
      })),
    );
  }

  const darkGlassMaterials = [...materialByName.values()].filter((item) => item.extremelyDarkGlass);
  for (const material of darkGlassMaterials) {
    addIssue(issueMap, 'extremely-dark-glass-material', 1, material);
  }

  const repeatCounts = new Map();
  for (const pane of paneComponents) {
    const signature = repeatSignature(pane);
    repeatCounts.set(signature, (repeatCounts.get(signature) ?? 0) + 1);
  }
  const geometryMaxRepeat = Math.max(0, ...repeatCounts.values());
  const geometryDarkCards = thinCardComponents.filter((component) => component.darkMaterial);
  if (geometryDarkCards.length > 0) {
    addIssue(
      issueMap,
      'thin-dark-facade-card',
      geometryDarkCards.length,
      geometryDarkCards.slice(0, 5).map((component) => ({
        node: component.node,
        material: component.material,
        dimensions: [component.width, component.height, component.thickness].map((number) =>
          Number(number.toFixed(4)),
        ),
      })),
    );
  }

  let geometryNearCoplanar = 0;
  let geometryFloating = 0;
  let geometryEmbedded = 0;
  let geometryPlacementChecked = 0;
  for (const pane of paneComponents) {
    if (pane.semantic !== 'facade-pane') continue;
    geometryPlacementChecked += 1;
    const clearance = findWallClearance(pane, wallComponents);
    if (clearance === null || clearance > MAX_WALL_CLEARANCE_M) geometryFloating += 1;
    else if (clearance < -0.004) geometryEmbedded += 1;
    else if (clearance < MIN_WALL_CLEARANCE_M) geometryNearCoplanar += 1;
  }

  if (paneComponents.length > 0 && metricOwners.length === 0 && geometryPlacementChecked === 0) {
    addIssue(issueMap, 'unverifiable-pane-placement', paneComponents.length, {
      reason: 'merged facade/prop glass requires aggregate clearance metadata',
    });
  }

  const effective = {
    paneCount: metricOwners.length ? metadata.paneCount : paneComponents.length,
    // Once construction-side facade metadata exists, generic merged glass may
    // also contain vehicle windscreens and hero domes. Their equal dimensions
    // are not a facade grid, so the audited facade counter is authoritative.
    maxEqualSizeRepeat: metricOwners.length ? metadata.maxEqualSizeRepeat : geometryMaxRepeat,
    nearCoplanarCount: Math.max(metadata.nearCoplanarCount, geometryNearCoplanar),
    floatingCount: Math.max(metadata.floatingCount, geometryFloating),
    embeddedCount: Math.max(metadata.embeddedCount, geometryEmbedded),
    darkCardCount: Math.max(metadata.darkCardCount, geometryDarkCards.length),
  };

  const paneLimit = PANE_LIMITS[lod] ?? 0;
  const darkCardLimit =
    (stageId === 'kairou' ? KAIROU_DARK_CARD_LIMITS : DARK_CARD_LIMITS)[lod] ?? 0;
  if (effective.paneCount > paneLimit) {
    addIssue(issueMap, 'facade-pane-count-limit', effective.paneCount - paneLimit, {
      actual: effective.paneCount,
      limit: paneLimit,
    });
  }
  if (effective.darkCardCount > darkCardLimit) {
    addIssue(issueMap, 'facade-card-count-limit', effective.darkCardCount - darkCardLimit, {
      actual: effective.darkCardCount,
      limit: darkCardLimit,
    });
  }
  if (effective.maxEqualSizeRepeat > MAX_EQUAL_SIZE_REPEAT) {
    addIssue(
      issueMap,
      'equal-size-facade-repeat',
      effective.maxEqualSizeRepeat - MAX_EQUAL_SIZE_REPEAT,
      {
        actual: effective.maxEqualSizeRepeat,
        limit: MAX_EQUAL_SIZE_REPEAT,
      },
    );
  }
  if (effective.nearCoplanarCount > 0) {
    addIssue(issueMap, 'near-coplanar-facade-pane', effective.nearCoplanarCount);
  }
  if (effective.floatingCount > 0) {
    addIssue(issueMap, 'floating-facade-pane', effective.floatingCount);
  }
  if (effective.embeddedCount > 0) {
    addIssue(issueMap, 'embedded-facade-pane', effective.embeddedCount);
  }
  if (lod === 2 && effective.paneCount > 0) {
    addIssue(issueMap, 'lod2-window-card', effective.paneCount);
  }

  const issues = serialiseIssues(issueMap);
  return {
    path: sourcePath,
    stageId,
    lod,
    ok: issues.length === 0,
    metrics: {
      effective,
      metadata,
      geometry: {
        componentsAnalysed,
        paneCandidates: paneComponents.length,
        thinCardCandidates: thinCardComponents.length,
        darkCardCandidates: geometryDarkCards.length,
        maxEqualSizeRepeat: geometryMaxRepeat,
        placementChecked: geometryPlacementChecked,
        nearCoplanarCount: geometryNearCoplanar,
        floatingCount: geometryFloating,
        embeddedCount: geometryEmbedded,
      },
      material: {
        inspected: materialByName.size,
        extremelyDarkGlass: darkGlassMaterials.length,
      },
    },
    issues,
  };
}

function provenanceFromDocument(document, expectedSha) {
  const variants = new Set();
  let missing = 0;
  for (const node of document.getRoot().listNodes()) {
    const sha = node.getExtras?.()?.hibanaGeneratorSha;
    if (typeof sha === 'string' && sha) variants.add(sha);
    else missing += 1;
  }
  const values = [...variants].sort();
  const issues = [];
  if (missing > 0) issues.push({ code: 'node-generator-sha-missing', count: missing });
  if (values.length !== 1 || values[0] !== expectedSha) {
    issues.push({
      code: 'node-generator-sha-mismatch',
      count: Math.max(1, values.length),
      actual: values,
      expected: expectedSha,
    });
  }
  return { ok: issues.length === 0, generatorShaVariants: values, missing, issues };
}

export async function auditAsset(path, stageId, lod, expectedGeneratorSha) {
  const io = await getIO();
  const document = await io.read(path);
  return {
    visual: auditDocument(document, { stageId, lod, sourcePath: path }),
    provenance: provenanceFromDocument(document, expectedGeneratorSha),
  };
}

function sumIssueCodes(assets, selector) {
  const counts = {};
  for (const asset of assets) {
    for (const issue of selector(asset))
      counts[issue.code] = (counts[issue.code] ?? 0) + issue.count;
  }
  return Object.fromEntries(
    Object.entries(counts).sort(([left], [right]) => left.localeCompare(right)),
  );
}

function metadataContract() {
  return {
    version: FACADE_AUDIT_VERSION,
    requiredNodeExtras: REQUIRED_FACADE_EXTRAS,
    explanation:
      'Write these aggregate values on one exported owner node per independent MeshBuilder scope. ' +
      'Merged stage/prop glass cannot be classified reliably after export without these values.',
    controlledSemanticRoles: [...CONTROLLED_SEMANTIC_ROLES].sort(),
    thresholds: {
      facadePaneCountsByLod: PANE_LIMITS,
      darkCardCountsByLod: DARK_CARD_LIMITS,
      kairouDarkCardCountsByLod: KAIROU_DARK_CARD_LIMITS,
      maxEqualSizeRepeat: MAX_EQUAL_SIZE_REPEAT,
      minWallClearanceM: MIN_WALL_CLEARANCE_M,
      maxWallClearanceM: MAX_WALL_CLEARANCE_M,
      minFrameRecessM: MIN_FRAME_RECESS_M,
      darkOpaqueGlassLuminance: DARK_GLASS_LUMINANCE,
    },
  };
}

export async function validateRelease({
  assetsDir = resolve(PROJECT_ROOT, 'public/assets/aaa/stages'),
  manifestPath = resolve(PROJECT_ROOT, 'public/assets/aaa/manifest.json'),
  generatorPath = resolve(PROJECT_ROOT, 'tools/blender/build_all_stages.py'),
  stageIds = EXPECTED_STAGE_IDS,
} = {}) {
  const expectedGeneratorSha = createHash('sha256')
    .update(await readFile(generatorPath))
    .digest('hex');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const assets = [];
  const coverageIssues = [];
  for (const stageId of stageIds) {
    for (let lod = 0; lod < 3; lod += 1) {
      const path = resolve(assetsDir, `${stageId}-lod${lod}.glb`);
      if (!existsSync(path)) {
        coverageIssues.push({ code: 'missing-stage-lod', stageId, lod, path });
        continue;
      }
      try {
        const audit = await auditAsset(path, stageId, lod, expectedGeneratorSha);
        assets.push({ path, stageId, lod, ...audit });
      } catch (error) {
        assets.push({
          path,
          stageId,
          lod,
          visual: {
            path,
            stageId,
            lod,
            ok: false,
            metrics: null,
            issues: [
              {
                code: 'invalid-or-unreadable-glb',
                severity: 'blocker',
                count: 1,
                samples: [String(error)],
              },
            ],
          },
          provenance: {
            ok: false,
            generatorShaVariants: [],
            missing: 0,
            issues: [{ code: 'provenance-unreadable-glb', count: 1 }],
          },
        });
      }
    }
  }
  const visualGateOk = coverageIssues.length === 0 && assets.every((asset) => asset.visual.ok);
  const manifestProvenanceIssues = [];
  if (manifest.generatorSha !== expectedGeneratorSha) {
    manifestProvenanceIssues.push({
      code: 'manifest-generator-sha-mismatch',
      count: 1,
      actual: manifest.generatorSha ?? null,
      expected: expectedGeneratorSha,
    });
  }
  const provenanceOk =
    manifestProvenanceIssues.length === 0 && assets.every((asset) => asset.provenance.ok);
  return {
    releaseOk: visualGateOk && provenanceOk,
    visualGateOk,
    provenanceOk,
    coverage: {
      expectedStages: stageIds.length,
      expectedAssets: stageIds.length * 3,
      inspectedAssets: assets.length,
      issues: coverageIssues,
    },
    generatorProvenance: {
      expectedGeneratorSha,
      manifestGeneratorSha: manifest.generatorSha ?? null,
      issues: manifestProvenanceIssues,
      assetIssueCounts: sumIssueCodes(assets, (asset) => asset.provenance.issues),
    },
    blackWindowGate: {
      issueCounts: sumIssueCodes(assets, (asset) => asset.visual.issues),
      failedAssets: assets.filter((asset) => !asset.visual.ok).length,
      passedAssets: assets.filter((asset) => asset.visual.ok).length,
    },
    metadataContract: metadataContract(),
    assets,
  };
}

function parseArguments(argv) {
  const options = { stages: [], report: null };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    const value = argv[index + 1];
    if (argument === '--assets-dir' && value) {
      options.assetsDir = resolve(value);
      index += 1;
    } else if (argument === '--manifest' && value) {
      options.manifestPath = resolve(value);
      index += 1;
    } else if (argument === '--generator' && value) {
      options.generatorPath = resolve(value);
      index += 1;
    } else if (argument === '--stage' && value) {
      options.stages.push(value);
      index += 1;
    } else if (argument === '--report' && value) {
      options.report = resolve(value);
      index += 1;
    } else if (argument === '--help') options.help = true;
    else throw new Error(`unknown or incomplete argument: ${argument}`);
  }
  return options;
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (options.help) {
    console.log(
      'usage: validate-black-window-release-gate.mjs ' +
        '[--assets-dir DIR] [--manifest FILE] [--generator FILE] ' +
        '[--stage ID ...] [--report FILE]',
    );
    return 0;
  }
  const unknown = options.stages.filter((stage) => !EXPECTED_STAGE_IDS.includes(stage));
  if (unknown.length) throw new Error(`unknown stage ID(s): ${unknown.join(', ')}`);
  const report = await validateRelease({
    assetsDir: options.assetsDir,
    manifestPath: options.manifestPath,
    generatorPath: options.generatorPath,
    stageIds: options.stages.length ? options.stages : EXPECTED_STAGE_IDS,
  });
  const json = `${JSON.stringify(report, null, 2)}\n`;
  if (options.report) await writeFile(options.report, json);
  console.log(json.trimEnd());
  return report.releaseOk ? 0 : 1;
}

if (resolve(process.argv[1] ?? '') === resolve(MODULE_PATH)) {
  main().then(
    (code) => {
      process.exitCode = code;
    },
    (error) => {
      console.error(`[${basename(MODULE_PATH)}] ${error.stack ?? error}`);
      process.exitCode = 1;
    },
  );
}
