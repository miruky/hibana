import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

/**
 * 一人称専用の両腕リグ。
 *
 * 手・手首・袖口・前腕を同じ hand Group の子として組む。手と袖を別ノードで動かすと、
 * 武器別ポーズやリロード中に必ず隙間が生じるため、接続はアニメーション調整ではなく
 * 階層構造で保証する。旧来の arm Group は viewmodel のポーズ名互換用の空制御ノードとして
 * 残すが、表示ジオメトリは一切持たない。
 */

export interface FirstPersonArmMaterials {
  readonly sleeve: THREE.MeshStandardMaterial;
  readonly glove: THREE.MeshStandardMaterial;
  readonly glovePalm: THREE.MeshStandardMaterial;
  readonly gloveArmor: THREE.MeshStandardMaterial;
  readonly gloveStitch: THREE.MeshStandardMaterial;
  readonly skin: THREE.MeshStandardMaterial;
}

export interface FirstPersonArmPose {
  readonly arm: readonly [x: number, y: number, z: number, rx: number, ry: number, rz: number];
  readonly hand: readonly [x: number, y: number, z: number, rx: number, ry: number, rz: number];
}

export interface FirstPersonArmsOptions {
  readonly right: FirstPersonArmPose;
  readonly left: FirstPersonArmPose;
  /** クナイ用。既存の FIST_POSES が参照する名前を付ける。 */
  readonly fists?: boolean;
  /** 杖・弓・クナイなど、トリガーを持たない右手は4指を握り込む。 */
  readonly rightGrip?: 'trigger' | 'power';
  /** クナイの空いた左手だけは銃支持手ではなく、指を畳んだ近接ガードにする。 */
  readonly leftGrip?: 'support' | 'guard';
  /** Narrow only the opposed terminal pads for a measured magazine width. */
  readonly supportContactInset?: number;
  /** Kaede-only grasp topology gate. Other weapons retain the shared hand. */
  readonly supportGripVariant?: SupportGripVariant;
}

type HandGrip = 'trigger' | 'power' | 'support' | 'guard';
type SupportGripVariant = 'shared' | 'kaede-q17';

interface FingerDiagnostic {
  readonly name: 'pinky' | 'ring' | 'middle' | 'index';
  readonly triggerFinger: boolean;
  readonly joints: readonly [number, number, number][];
  readonly idleJoints?: readonly [number, number, number][];
  readonly exchangeJoints?: readonly [number, number, number][];
  readonly radii: readonly [number, number, number];
  readonly tipRadius: number;
  readonly idleTipRadius?: number;
  readonly idleTerminalNeckRadius?: number;
  readonly idleTipHorizontalScale?: number;
  readonly idleTipDepthScale?: number;
  readonly idleTipLongitudinalScale?: number;
  readonly idleRadii?: readonly [number, number, number];
  readonly idleTerminalFacetCount?: number;
}

interface SupportGripDiagnostic {
  readonly anchor: readonly [number, number, number];
  readonly fingerTipCenter: readonly [number, number, number];
  readonly thumbTip: readonly [number, number, number];
  readonly thumbTipRadius: number;
  readonly adjacentSurfaceClearances: readonly number[];
  readonly palmCenter: readonly [number, number, number];
  readonly palmInteriorNormal: readonly [number, number, number];
  readonly backNormal: readonly [number, number, number];
  readonly curlNormal: readonly [number, number, number];
}

// Kaede reload04 establishes the authored support-hand basis. Keeping it at
// module scope lets the palm, glove cuff and connected sleeve share the exact
// same wrist point instead of visually meeting at unrelated guessed offsets.
const SUPPORT_MAGAZINE_FRONT = new THREE.Vector3(-0.108, 0.543, 0.833).normalize();
const SUPPORT_MAGAZINE_UP = new THREE.Vector3(0.897, 0.415, -0.154).normalize();
const SUPPORT_MAGAZINE_RIGHT = new THREE.Vector3()
  .crossVectors(SUPPORT_MAGAZINE_UP, SUPPORT_MAGAZINE_FRONT)
  .normalize();
const SUPPORT_GRIP_ANCHOR = new THREE.Vector3(
  0.002719417445602287,
  0.04506849065668107,
  0.012879854039843857,
);

function supportGripPoint(right: number, up: number, front: number): THREE.Vector3 {
  return SUPPORT_GRIP_ANCHOR.clone()
    .addScaledVector(SUPPORT_MAGAZINE_RIGHT, right)
    .addScaledVector(SUPPORT_MAGAZINE_UP, up)
    .addScaledVector(SUPPORT_MAGAZINE_FRONT, front);
}

function applyPose(group: THREE.Group, pose: FirstPersonArmPose['arm'] | FirstPersonArmPose['hand']): void {
  group.position.set(pose[0], pose[1], pose[2]);
  group.rotation.set(pose[3], pose[4], pose[5]);
}

function markFirstPersonMesh(mesh: THREE.Mesh): void {
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  // カメラ直付けモデルはワールドのfrustum判定と一致しない場合がある。
  mesh.frustumCulled = false;
  mesh.renderOrder = 3;
  mesh.userData.firstPersonArm = true;
}

function transformGeometry(
  geometry: THREE.BufferGeometry,
  position: THREE.Vector3,
  rotation: THREE.Euler,
  scale = new THREE.Vector3(1, 1, 1),
): THREE.BufferGeometry {
  const q = new THREE.Quaternion().setFromEuler(rotation);
  geometry.applyMatrix4(new THREE.Matrix4().compose(position, q, scale));
  return geometry;
}

function orientGeometry(
  geometry: THREE.BufferGeometry,
  position: THREE.Vector3,
  xAxis: THREE.Vector3,
  yAxis: THREE.Vector3,
  zAxis: THREE.Vector3,
  scale: THREE.Vector3,
): THREE.BufferGeometry {
  const rotation = new THREE.Matrix4().makeBasis(xAxis, yAxis, zAxis);
  const quaternion = new THREE.Quaternion().setFromRotationMatrix(rotation);
  geometry.applyMatrix4(new THREE.Matrix4().compose(position, quaternion, scale));
  return geometry;
}

function cylinderBetween(
  start: THREE.Vector3,
  end: THREE.Vector3,
  startRadius: number,
  endRadius: number,
  radialSegments: number,
  crossSection: readonly [number, number] = [1.08, 0.82],
): THREE.BufferGeometry {
  const delta = new THREE.Vector3().subVectors(end, start);
  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
  const geometry = new THREE.CylinderGeometry(endRadius, startRadius, delta.length(), radialSegments, 2);
  // 人体の前腕断面は真円ではない。画面正対方向を少し潰し、均一な配管形状を避ける。
  geometry.scale(crossSection[0], 1, crossSection[1]);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    delta.normalize(),
  );
  geometry.applyMatrix4(new THREE.Matrix4().compose(midpoint, quaternion, new THREE.Vector3(1, 1, 1)));
  return geometry;
}

function torusAround(
  center: THREE.Vector3,
  direction: THREE.Vector3,
  radius: number,
  tube: number,
  arc = Math.PI * 1.15,
): THREE.BufferGeometry {
  const geometry = new THREE.TorusGeometry(radius, tube, 4, 12, arc);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 0, 1),
    direction.clone().normalize(),
  );
  geometry.applyMatrix4(new THREE.Matrix4().compose(
    center,
    quaternion,
    new THREE.Vector3(1, 0.7, 1),
  ));
  return geometry;
}

/**
 * 2つの関節の間をカプセルで繋ぐ。CapsuleGeometry の length は円筒部分だけなので、
 * 全長が start-end に収まるよう両端半球の直径を引く。指節を独立座標で置くと、
 * 曲げ角を調整した時に指先だけが掌から離れるため、必ず関節チェーンから生成する。
 */
function capsuleBetween(
  start: THREE.Vector3,
  end: THREE.Vector3,
  radius: number,
  capSegments = 4,
  radialSegments = 7,
): THREE.BufferGeometry {
  const delta = new THREE.Vector3().subVectors(end, start);
  const distance = Math.max(delta.length(), radius * 2 + 1e-4);
  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
  const geometry = new THREE.CapsuleGeometry(
    radius,
    Math.max(1e-4, distance - radius * 2),
    capSegments,
    radialSegments,
  );
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    delta.normalize(),
  );
  geometry.applyMatrix4(new THREE.Matrix4().compose(
    midpoint,
    quaternion,
    new THREE.Vector3(1, 1, 1),
  ));
  return geometry;
}

/**
 * 末節だけは指先へ向かって細くする。CapsuleGeometry の両端は同径なので、
 * 4指を並べると指先が同じ大きさの珠に見える。テーパー円柱+小さな終端球にし、
 * PIP側は前節の半球へ重ねて連続、DIP側だけシルエットを絞る。
 */
function taperedFingerSegment(
  start: THREE.Vector3,
  end: THREE.Vector3,
  startRadius: number,
  endRadius: number,
): THREE.BufferGeometry {
  const delta = new THREE.Vector3().subVectors(end, start);
  const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    delta.clone().normalize(),
  );
  const shaft = new THREE.CylinderGeometry(endRadius, startRadius, delta.length(), 7, 2);
  shaft.applyMatrix4(new THREE.Matrix4().compose(
    midpoint,
    quaternion,
    new THREE.Vector3(1, 1, 1),
  ));
  const tip = new THREE.SphereGeometry(1, 8, 5);
  tip.applyMatrix4(new THREE.Matrix4().compose(
    end,
    quaternion,
    new THREE.Vector3(endRadius * 0.94, endRadius * 1.08, endRadius * 0.94),
  ));
  const geometry = mergeGeometries([shaft, tip], false);
  shaft.dispose();
  tip.dispose();
  if (!geometry) throw new Error('failed to build tapered first-person finger segment');
  geometry.computeVertexNormals();
  return geometry;
}

/** Attach an absolute idle-pose morph to an otherwise reload-authored part. */
function attachIdleMorph(
  reloadGeometry: THREE.BufferGeometry,
  idleGeometry: THREE.BufferGeometry,
): THREE.BufferGeometry {
  const reloadPosition = reloadGeometry.getAttribute('position');
  const idlePosition = idleGeometry.getAttribute('position');
  if (reloadPosition.count !== idlePosition.count) {
    reloadGeometry.dispose();
    idleGeometry.dispose();
    throw new Error('support hand idle morph topology mismatch');
  }
  reloadGeometry.morphTargetsRelative = false;
  reloadGeometry.morphAttributes.position = [idlePosition.clone()];
  const idleNormal = idleGeometry.getAttribute('normal');
  if (idleNormal?.count === reloadGeometry.getAttribute('normal')?.count) {
    reloadGeometry.morphAttributes.normal = [idleNormal.clone()];
  }
  idleGeometry.dispose();
  return reloadGeometry;
}

/** Keep a rest-only idle plus one absolute exchange-correction target. */
function attachIdleMorphPair(
  reloadGeometry: THREE.BufferGeometry,
  idleGeometry: THREE.BufferGeometry,
  exchangeGeometry: THREE.BufferGeometry,
): THREE.BufferGeometry {
  const reloadPosition = reloadGeometry.getAttribute('position');
  const idlePosition = idleGeometry.getAttribute('position');
  const exchangePosition = exchangeGeometry.getAttribute('position');
  if (
    reloadPosition.count !== idlePosition.count ||
    reloadPosition.count !== exchangePosition.count
  ) {
    reloadGeometry.dispose();
    idleGeometry.dispose();
    exchangeGeometry.dispose();
    throw new Error('support hand dual idle morph topology mismatch');
  }
  reloadGeometry.morphTargetsRelative = false;
  reloadGeometry.morphAttributes.position = [
    idlePosition.clone(),
    exchangePosition.clone(),
  ];
  const reloadNormal = reloadGeometry.getAttribute('normal');
  const idleNormal = idleGeometry.getAttribute('normal');
  const exchangeNormal = exchangeGeometry.getAttribute('normal');
  if (
    idleNormal?.count === reloadNormal?.count &&
    exchangeNormal?.count === reloadNormal?.count
  ) {
    reloadGeometry.morphAttributes.normal = [
      idleNormal.clone(),
      exchangeNormal.clone(),
    ];
  }
  idleGeometry.dispose();
  exchangeGeometry.dispose();
  return reloadGeometry;
}

/** Every merged glove part must expose the same morph attribute set. */
function attachStationaryIdleMorph(geometry: THREE.BufferGeometry): void {
  if (!geometry.morphAttributes.position?.length) {
    geometry.morphTargetsRelative = false;
    geometry.morphAttributes.position = [geometry.getAttribute('position').clone()];
  }
  if (!geometry.morphAttributes.normal?.length) {
    geometry.morphAttributes.normal = [geometry.getAttribute('normal').clone()];
  }
}

function ensureExchangeCorrectionMorph(geometry: THREE.BufferGeometry): void {
  attachStationaryIdleMorph(geometry);
  const position = geometry.morphAttributes.position!;
  // Target 1 is a short exchange-only corrective. Unauthored parts must stay
  // at their base/reload coordinates, not inherit target 0's idle silhouette.
  if (position.length === 1) position.push(geometry.getAttribute('position').clone());
  const normal = geometry.morphAttributes.normal!;
  if (normal.length === 1) normal.push(geometry.getAttribute('normal').clone());
}

/**
 * 手の甲を単純な回転楕円にすると、一人称の斜視で平たいミトンに見える。
 * ナックル側が広く、手首側が細い準解剖形を球メッシュから変形し、
 * 側面と甲面に連続したハイライトを作る。
 */
function taperedPalmWedge(supportGrip: boolean): THREE.BufferGeometry {
  const geometry = new THREE.SphereGeometry(1, 18, 12);
  const position = geometry.getAttribute('position') as THREE.BufferAttribute;
  for (let i = 0; i < position.count; i += 1) {
    const nx = position.getX(i);
    const ny = position.getY(i);
    const nz = position.getZ(i);
    // nz=-1=ナックル、+1=手首。指根側を広く、手首側を細くする。
    const wrist01 = THREE.MathUtils.clamp((nz + 1) * 0.5, 0, 1);
    const halfWidth = supportGrip
      ? THREE.MathUtils.lerp(0.034, 0.0255, wrist01)
      : THREE.MathUtils.lerp(0.041, 0.03, wrist01);
    const halfDepth = supportGrip
      ? THREE.MathUtils.lerp(0.019, 0.022, wrist01)
      : THREE.MathUtils.lerp(0.028, 0.03, wrist01);
    // 小指側を僅かに薄くし、左右対称の工業部品感を消す。
    const ulnarTaper = 1 - Math.max(0, -nx) * 0.08;
    position.setXYZ(
      i,
      nx * halfWidth * ulnarTaper,
      ny * halfDepth * (1 - Math.abs(nx) * 0.08),
      (supportGrip ? 0.008 : 0.005) + nz * (supportGrip ? 0.047 : 0.056),
    );
  }
  position.needsUpdate = true;
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}

/**
 * A single tapered tube through every joint. Separate capsules overlap into a
 * row of spherical beads at PIP/DIP, which is especially obvious while the
 * reload hand is beside a straight magazine. One continuous surface keeps the
 * silhouette anatomical while retaining a very small vertex budget.
 */
function continuousFingerTube(
  joints: readonly THREE.Vector3[],
  radii: readonly number[],
  radialSegments = 8,
  flatten = 0.84,
): THREE.BufferGeometry {
  if (joints.length < 2 || radii.length !== joints.length) {
    throw new Error('continuous finger tube requires one radius per joint');
  }
  const curve = new THREE.CatmullRomCurve3(
    joints.map((joint) => joint.clone()),
    false,
    'centripetal',
    0.45,
  );
  const tubularSegments = (joints.length - 1) * 4;
  const frames = curve.computeFrenetFrames(tubularSegments, false);
  const positions: number[] = [];
  const indices: number[] = [];
  for (let ring = 0; ring <= tubularSegments; ring += 1) {
    const u = ring / tubularSegments;
    const center = curve.getPointAt(u);
    const radiusPosition = u * (radii.length - 1);
    const radiusIndex = Math.min(radii.length - 2, Math.floor(radiusPosition));
    const radiusAlpha = radiusPosition - radiusIndex;
    const radius = THREE.MathUtils.lerp(
      radii[radiusIndex]!,
      radii[radiusIndex + 1]!,
      radiusAlpha,
    );
    const normal = frames.normals[ring]!;
    const binormal = frames.binormals[ring]!;
    for (let sideIndex = 0; sideIndex < radialSegments; sideIndex += 1) {
      const angle = sideIndex / radialSegments * Math.PI * 2;
      const point = center.clone()
        .addScaledVector(normal, Math.cos(angle) * radius)
        // Fingers are subtly flatter on the pad/back axis than cylinders.
        .addScaledVector(binormal, Math.sin(angle) * radius * flatten);
      positions.push(point.x, point.y, point.z);
    }
  }
  for (let ring = 0; ring < tubularSegments; ring += 1) {
    for (let sideIndex = 0; sideIndex < radialSegments; sideIndex += 1) {
      const nextSide = (sideIndex + 1) % radialSegments;
      const a = ring * radialSegments + sideIndex;
      const b = ring * radialSegments + nextSide;
      const c = (ring + 1) * radialSegments + sideIndex;
      const d = (ring + 1) * radialSegments + nextSide;
      indices.push(a, c, b, b, c, d);
    }
  }
  const rootCenter = positions.length / 3;
  positions.push(joints[0]!.x, joints[0]!.y, joints[0]!.z);
  const tipCenter = positions.length / 3;
  positions.push(joints.at(-1)!.x, joints.at(-1)!.y, joints.at(-1)!.z);
  const lastRing = tubularSegments * radialSegments;
  for (let sideIndex = 0; sideIndex < radialSegments; sideIndex += 1) {
    const nextSide = (sideIndex + 1) % radialSegments;
    indices.push(rootCenter, nextSide, sideIndex);
    indices.push(tipCenter, lastRing + sideIndex, lastRing + nextSide);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(
    new Float32Array(positions.length / 3 * 2),
    2,
  ));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}

/** Q17 terminal pad: retain the low-poly continuous tube but close it with a
 * shallow ellipsoid instead of a flat polygon cap. The latter projected as a
 * pointed claw whenever the idle fingers were almost edge-on to the camera. */
function roundedContinuousFingerTube(
  joints: readonly THREE.Vector3[],
  radii: readonly number[],
  radialSegments = 8,
  flatten = 0.84,
  tipHorizontalScale = 0.9,
  tipDepthScale = 0.72,
  tipFacetRotation = 0,
  tipLongitudinalScale = 1.12,
  tipCapRadius = radii.at(-1)!,
): THREE.BufferGeometry {
  const tube = continuousFingerTube(joints, radii, radialSegments, flatten);
  const penultimate = joints.at(-2)!;
  const terminal = joints.at(-1)!;
  const direction = terminal.clone().sub(penultimate).normalize();
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    direction,
  ).multiply(new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(0, 1, 0),
    tipFacetRotation,
  ));
  const pad = new THREE.SphereGeometry(1, 8, 5);
  pad.applyMatrix4(new THREE.Matrix4().compose(
    terminal,
    quaternion,
    new THREE.Vector3(
      tipCapRadius * tipHorizontalScale,
      tipCapRadius * tipLongitudinalScale,
      tipCapRadius * tipDepthScale,
    ),
  ));
  const geometry = mergeGeometries([tube, pad], false);
  tube.dispose();
  pad.dispose();
  if (!geometry) throw new Error('failed to build rounded continuous first-person finger');
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}

/**
 * Rounded-rectangular metacarpal volume. A scaled sphere reads as a circular
 * mitten in first person; this five-ring mesh has a broad dorsal plane, a
 * flatter palm plane, knuckle taper and a narrow wrist in one continuous hull.
 */
function supportPalmHull(
  center: THREE.Vector3,
  compactAsymmetric = false,
  idleTerminalTaper = false,
  legacyIdleTerminal = false,
  exchangeCorrected = false,
): THREE.BufferGeometry {
  // A compact 68mm metacarpal loft. Q9's 90mm version filled the reload frame
  // like a green paddle; reducing only the palm length/width (not the grasp
  // span) restores a human palm-to-finger ratio while retaining padded depth.
  // The centre is shifted toward +RIGHT below, so the smaller inner face keeps
  // the exact same weapon contact instead of shrinking away from the gun.
  const rings = compactAsymmetric
    ? [
        // Q17: 62mm wrist-to-knuckle loft, 39mm max width and 25mm max
        // thickness. The Q15 mitten tapered both ends into an oval. A real
        // palm is narrow at the wrist but stays broad at the metacarpal heads,
        // so the last two rings retain width for four buried finger roots.
        { up: -0.030, rightRadius: 0.0055, frontRadius: 0.005, rightShift: -0.004 },
        {
          up: -0.024,
          rightRadius: exchangeCorrected ? 0.0080 : 0.010,
          frontRadius: exchangeCorrected ? 0.0068 : 0.0075,
          rightShift: exchangeCorrected ? -0.0040 : -0.0035,
        },
        {
          up: -0.016,
          rightRadius: exchangeCorrected ? 0.0105 : 0.0145,
          frontRadius: exchangeCorrected ? 0.0084 : 0.010,
          rightShift: exchangeCorrected ? -0.0040 : -0.0025,
        },
        {
          up: -0.006,
          rightRadius: exchangeCorrected ? 0.01025 : 0.0178,
          frontRadius: exchangeCorrected ? 0.0094 : 0.0122,
          rightShift: exchangeCorrected ? -0.00725 : -0.0015,
        },
        {
          up: 0.006,
          rightRadius: exchangeCorrected ? 0.01125 : 0.0195,
          frontRadius: exchangeCorrected ? 0.0098 : 0.0125,
          rightShift: exchangeCorrected ? -0.01025 : -0.0005,
        },
        {
          up: idleTerminalTaper && !legacyIdleTerminal ? 0.0155 : 0.018,
          rightRadius: exchangeCorrected
            ? 0.0140
            : idleTerminalTaper && !legacyIdleTerminal ? 0.0190 : 0.0192,
          frontRadius: exchangeCorrected
            ? 0.0092
            : idleTerminalTaper && !legacyIdleTerminal ? 0.0105 : 0.0115,
          rightShift: exchangeCorrected
            ? -0.0110
            : idleTerminalTaper && !legacyIdleTerminal ? -0.0090 : 0.0008,
        },
        // Q17o keeps the reload rings byte-for-byte fixed, but makes the idle
        // terminal a short rounded knuckle cap. Rings 5/6 form a broad shoulder
        // and ring 7 closes it over only 4.2mm; the former 6mm straight taper
        // projected as a pointed mitten even after the thumb was separated.
        {
          up: idleTerminalTaper
            ? legacyIdleTerminal ? 0.027 : 0.0180
            : 0.027,
          rightRadius: exchangeCorrected
            ? 0.01725
            : idleTerminalTaper
            ? legacyIdleTerminal ? 0.0150 : 0.0193
            : 0.0183,
          frontRadius: exchangeCorrected
            ? 0.0076
            : idleTerminalTaper
            ? legacyIdleTerminal ? 0.0080 : 0.0094
            : 0.0095,
          rightShift: exchangeCorrected
            ? -0.01025
            : idleTerminalTaper
            ? legacyIdleTerminal ? -0.0037 : -0.0095
            : 0.0018,
        },
        {
          up: idleTerminalTaper
            ? legacyIdleTerminal ? 0.032 : 0.0192
            : 0.032,
          rightRadius: exchangeCorrected
            ? 0.0160
            : idleTerminalTaper
            ? legacyIdleTerminal ? 0.0105 : 0.0172
            : 0.0165,
          frontRadius: exchangeCorrected
            ? 0.0044
            : idleTerminalTaper
            ? legacyIdleTerminal ? 0.0052 : 0.0078
            : 0.0072,
          rightShift: exchangeCorrected
            ? -0.0070
            : idleTerminalTaper
            ? legacyIdleTerminal ? -0.0041 : -0.0100
            : 0.0024,
        },
      ] as const
    : [
        { up: -0.034, rightRadius: 0.008, frontRadius: 0.0075, rightShift: -0.003 },
        { up: -0.027, rightRadius: 0.0145, frontRadius: 0.011, rightShift: -0.002 },
        { up: -0.018, rightRadius: 0.020, frontRadius: 0.014, rightShift: -0.001 },
        { up: -0.006, rightRadius: 0.023, frontRadius: 0.0155, rightShift: 0 },
        { up: 0.008, rightRadius: 0.023, frontRadius: 0.015, rightShift: 0.001 },
        { up: 0.020, rightRadius: 0.0215, frontRadius: 0.0135, rightShift: 0.0015 },
        { up: 0.029, rightRadius: 0.017, frontRadius: 0.010, rightShift: 0.0015 },
        { up: 0.034, rightRadius: 0.009, frontRadius: 0.0065, rightShift: 0.001 },
      ] as const;
  const radialSegments = 12;
  const positions: number[] = [];
  const indices: number[] = [];
  for (const ring of rings) {
    for (let edge = 0; edge < radialSegments; edge += 1) {
      const angle = edge / radialSegments * Math.PI * 2;
      // A mild superellipse creates broad dorsal/palm planes with rounded
      // contacts. The exchange corrective is deliberately squarer: at its
      // oblique reload angle the round .72 section collapsed back into the
      // long leaf silhouette even after the radii were reduced. Keeping this
      // target-only avoids changing the approved reload and idle fingerprints.
      const roundedPlane = (value: number) =>
        Math.sign(value) * Math.pow(Math.abs(value), exchangeCorrected ? 0.56 : 0.72);
      const knuckleArc = compactAsymmetric && !exchangeCorrected && ring.up > 0.02
        ? Math.cos(angle) * 0.0018 - Math.cos(angle * 2) * 0.0011
        : 0;
      const point = center.clone()
        .addScaledVector(SUPPORT_MAGAZINE_UP, ring.up + knuckleArc)
        .addScaledVector(
          SUPPORT_MAGAZINE_RIGHT,
          ring.rightShift + roundedPlane(Math.cos(angle)) * ring.rightRadius,
        )
        .addScaledVector(
          SUPPORT_MAGAZINE_FRONT,
          roundedPlane(Math.sin(angle)) * ring.frontRadius,
        );
      positions.push(point.x, point.y, point.z);
    }
  }
  const ringSize = radialSegments;
  for (let ring = 0; ring < rings.length - 1; ring += 1) {
    for (let edge = 0; edge < ringSize; edge += 1) {
      const next = (edge + 1) % ringSize;
      const a = ring * ringSize + edge;
      const b = ring * ringSize + next;
      const c = (ring + 1) * ringSize + edge;
      const d = (ring + 1) * ringSize + next;
      indices.push(a, c, b, b, c, d);
    }
  }
  const bottomCenter = positions.length / 3;
  const bottom = center.clone().addScaledVector(SUPPORT_MAGAZINE_UP, rings[0]!.up);
  positions.push(bottom.x, bottom.y, bottom.z);
  const topCenter = positions.length / 3;
  const terminalRing = rings.at(-1)!;
  // The old cap centre stayed on the unshifted palm axis while Q17n's final
  // idle ring moved 11mm toward the little-finger side. That single vertex
  // formed the last 1–2px diagonal apex. Aligning the centre to the terminal
  // ring retains the same topology and reload mesh while the 12-edge rim owns
  // the silhouette as a compact rounded cap.
  const top = center.clone()
    .addScaledVector(SUPPORT_MAGAZINE_UP, terminalRing.up)
    .addScaledVector(
      SUPPORT_MAGAZINE_RIGHT,
      idleTerminalTaper && !legacyIdleTerminal ? terminalRing.rightShift : 0,
    );
  positions.push(top.x, top.y, top.z);
  const lastRing = (rings.length - 1) * ringSize;
  for (let edge = 0; edge < ringSize; edge += 1) {
    const next = (edge + 1) % ringSize;
    indices.push(bottomCenter, edge, next);
    indices.push(topCenter, lastRing + next, lastRing + edge);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(
    new Float32Array(positions.length / 3 * 2),
    2,
  ));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}

/** Exchange-only palm target: a narrow wrist opens along two straight side
 * planes into the metacarpal heads. The terminal cap stays rounded, but the
 * broad section is confined to the knuckle end instead of filling 80px of the
 * projected palm like a leaf. */
function supportExchangePalmHull(center: THREE.Vector3): THREE.BufferGeometry {
  return supportPalmHull(center, true, false, false, true);
}

function tintGeometry(geometry: THREE.BufferGeometry, value: number): void {
  const position = geometry.getAttribute('position');
  const colors = new Float32Array(position.count * 3);
  for (let i = 0; i < position.count; i += 1) {
    colors[i * 3] = value;
    colors[i * 3 + 1] = value;
    colors[i * 3 + 2] = value;
  }
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
}

type HandMaterialFamily = 'glove' | 'palm' | 'armor' | 'stitch';

function mergeHandParts(parts: THREE.BufferGeometry[], family: HandMaterialFamily): THREE.BufferGeometry {
  const merged = mergeGeometries(parts, false);
  for (const part of parts) part.dispose();
  if (!merged) throw new Error(`failed to build first-person hand ${family} geometry`);
  merged.computeVertexNormals();
  merged.userData.handMaterialFamily = family;
  return merged;
}

/**
 * Magazine/fore-end support hand authored directly in its final local basis:
 * +Y=dorsal/camera side, -Y=palm/weapon side, +Z=wrist. Keeping that basis
 * explicit avoids the old rotate-Z-then-guess workflow that inverted the curl
 * and left four claw-like fingers on the camera side of the magazine.
 */
function buildSupportHandGeometries(
  _side: -1 | 1,
  requestedContactInset = 0,
  variant: SupportGripVariant = 'shared',
): Record<HandMaterialFamily, THREE.BufferGeometry> {
  const gripAnchor = SUPPORT_GRIP_ANCHOR;
  const gripPoint = supportGripPoint;
  const contactInset = THREE.MathUtils.clamp(requestedContactInset, 0, 0.004);
  const q16 = variant === 'kaede-q17';
  // Q9 inner surface: -0.027 + 0.031 = +0.004 in the authored RIGHT basis.
  // Q10 keeps that contact exactly: -0.019 + 0.023 = +0.004.
  const sharedIdlePalmCenter = gripPoint(-0.019, -0.004, -0.014);
  const idlePalmCenter = q16
    // Bring the dorsal shell 8mm toward the camera-facing side of the
    // handguard. The former centre left the palm fully occluded, exposing
    // only three terminal caps at the end of the sleeve in idle/fire.
    ? gripPoint(-0.020, -0.002, -0.004)
    : sharedIdlePalmCenter;
  // Q17 retains Q15's physically correct +RIGHT magazine contact, but reduces
  // the palm on all three axes and shortens the palm-to-cuff gap. The broad
  // visible back now ends at roughly -56mm instead of -61mm in RIGHT space.
  const palmCenter = q16 ? gripPoint(-0.037, -0.002, -0.012) : idlePalmCenter;
  const wrist = q16
    ? gripPoint(-0.036, -0.045, -0.016)
    : gripPoint(-0.036, -0.052, -0.018);
  const cuffEnd = q16
    ? gripPoint(-0.034, -0.038, -0.014)
    : gripPoint(-0.031, -0.042, -0.016);
  const lowerPalm = q16
    ? gripPoint(-0.030, -0.027, -0.012)
    : gripPoint(-0.025, -0.030, -0.013);
  const cuffOverlap = cuffEnd.clone().lerp(lowerPalm, 0.38);
  const buckets: Record<HandMaterialFamily, THREE.BufferGeometry[]> = {
    glove: [],
    palm: [],
    armor: [],
    stitch: [],
  };
  const palmHull = q16
    ? attachIdleMorphPair(
        supportPalmHull(palmCenter, true),
        supportPalmHull(idlePalmCenter, true, true),
        supportExchangePalmHull(palmCenter),
      )
    : supportPalmHull(palmCenter);
  const reloadThenarCenter = q16
    ? gripPoint(-0.050, 0.010, -0.004)
    : gripPoint(0.002, 0.014, -0.001);
  const thenar = orientGeometry(
    new THREE.SphereGeometry(1, 12, 8),
    reloadThenarCenter,
    SUPPORT_MAGAZINE_RIGHT,
    SUPPORT_MAGAZINE_UP,
    SUPPORT_MAGAZINE_FRONT,
    q16
      ? new THREE.Vector3(0.0055, 0.0105, 0.008)
      : new THREE.Vector3(0.014, 0.018, 0.012),
  );
  const hypothenar = q16
    ? attachIdleMorphPair(
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.049, -0.014, -0.005),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0045, 0.009, 0.0085),
        ),
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.032, -0.012, -0.004),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0045, 0.009, 0.0085),
        ),
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.0435, -0.012, -0.0045),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0026, 0.0120, 0.0058),
        ),
      )
    : null;
  buckets.glove.push(
    palmHull,
    // The glove bridge begins beneath the dark cuff and ends inside the palm;
    // overlapping contact volumes remove the old slice-like wrist boundary.
    cylinderBetween(
      cuffEnd,
      lowerPalm,
      q16 ? 0.0195 : 0.0195,
      q16 ? 0.0215 : 0.0215,
      12,
    ),
  );
  // Thenar/hypothenar are two low, separated pads rather than one large ball.
  // Their roots overlap the compact hull, so neither can read as an attached
  // sphere. The lighter suede family gives the palm anatomical value breaks.
  if (q16) {
    // These are real soft-tissue volumes under one continuous glove shell,
    // not contrasting appliqués. Keeping them in the glove family preserves
    // the thenar/hypothenar silhouette without painting three circular pads
    // that made the hand read as an animal paw in Q15/Q16 close-ups.
    buckets.glove.push(
      attachIdleMorphPair(
        thenar,
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.033, 0.009, -0.003),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0055, 0.0105, 0.008),
        ),
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.0440, 0.009, -0.004),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0028, 0.0130, 0.0055),
        ),
      ),
      hypothenar!,
    );
  } else {
    buckets.glove.push(thenar);
  }
  if (q16) {
    // Two separated suede islands follow the real thenar/hypothenar masses.
    // The former single 38mm oval was the strongest remaining mitten cue.
    for (const [reloadUp, idleUp, width, length, exchangeWidth, exchangeLength] of [
      [0.011, 0.011, 0.0075, 0.0105, 0.0050, 0.0120],
      [-0.012, -0.012, 0.0065, 0.009, 0.0045, 0.0105],
    ] as const) {
      buckets.palm.push(attachIdleMorphPair(
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.018, reloadUp, -0.007),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0016, length, width),
        ),
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.001, idleUp, -0.007),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0016, length, width),
        ),
        orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.022, reloadUp, -0.0075),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0009, exchangeLength + 0.001, exchangeWidth - 0.001),
        ),
      ));
    }
  } else {
    buckets.palm.push(
      orientGeometry(
          new THREE.SphereGeometry(1, 12, 8),
          gripPoint(-0.041, -0.002, -0.008),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0022, 0.024, 0.011),
        ),
    );
  }
  // The cuff overlaps both the sleeve attachment and glove bridge. Matching
  // the adjacent radii makes it read as a textile cuff, not a severed arm cap.
  buckets.armor.push(
    cylinderBetween(
      wrist,
      cuffOverlap,
      q16 ? 0.0205 : 0.0195,
      q16 ? 0.0215 : 0.0205,
      12,
    ),
  );
  if (q16) {
    // A single thin dorsal pad breaks the smooth mitten highlight without
    // adding four hardware-like knuckle buttons. It follows the palm morph and
    // remains only 2.2mm proud of the glove shell.
    buckets.armor.push(attachIdleMorphPair(
      orientGeometry(
        new THREE.SphereGeometry(1, 12, 8),
        gripPoint(-0.0555, 0.002, -0.010),
        SUPPORT_MAGAZINE_RIGHT,
        SUPPORT_MAGAZINE_UP,
        SUPPORT_MAGAZINE_FRONT,
        new THREE.Vector3(0.0022, 0.0145, 0.0085),
      ),
      orientGeometry(
        new THREE.SphereGeometry(1, 12, 8),
        gripPoint(-0.0385, 0.002, -0.010),
        SUPPORT_MAGAZINE_RIGHT,
        SUPPORT_MAGAZINE_UP,
        SUPPORT_MAGAZINE_FRONT,
        new THREE.Vector3(0.0022, 0.0145, 0.0085),
      ),
      orientGeometry(
        new THREE.SphereGeometry(1, 12, 8),
        gripPoint(-0.0470, 0.002, -0.008),
        SUPPORT_MAGAZINE_RIGHT,
        SUPPORT_MAGAZINE_UP,
        SUPPORT_MAGAZINE_FRONT,
        new THREE.Vector3(0.0012, 0.0155, 0.0055),
      ),
    ));
  }

  const fingerNames = ['pinky', 'ring', 'middle', 'index'] as const;
  const fingerHeights = [-0.018, -0.006, 0.006, 0.018] as const;
  // Keep the four terminal pads on one magazine face, but vary each PIP/DIP
  // path. A shared path only translated by 12mm made the fingers read as four
  // parallel rubber hoses in the reload close-up. The small fan below remains
  // inside the measured 2–4mm surface-clearance gate at the distal joints.
  // PIP knuckles fan more strongly than the contact-side DIP pads. Splitting
  // those offsets makes the silhouette widen like a real grasp while all four
  // fingertips still land on one flat magazine face with measured gaps.
  const reloadPipFan = [-0.005, -0.0017, 0.0017, 0.005] as const;
  const reloadDipFan = [-0.0005, -0.0002, 0.00025, 0.0007] as const;
  // Bury the PIP arc 4–8mm farther inside the palm while leaving DIP/tip
  // contact untouched. This hides the long camera-facing half of each curl;
  // exposing it made the four fingers read as a ladder beside the magazine.
  const reloadPipRights = [-0.039, -0.041, -0.043, -0.040] as const;
  const reloadDipRights = [-0.0382, -0.039, -0.0405, -0.0385] as const;
  const reloadPipFronts = [-0.002, -0.004, -0.006, -0.003] as const;
  const reloadDipFronts = [0.0168, 0.016, 0.0145, 0.016] as const;
  const idleFingerHeights = [-0.02, -0.0068, 0.0068, 0.02] as const;
  const idlePipFronts = [-0.012, -0.01, -0.009, -0.011] as const;
  const idleDipFronts = [-0.001, 0.004, 0.006, 0.003] as const;
  const idleTipFronts = [0.008, 0.017, 0.02, 0.015] as const;
  // Pinky < index/ring < middle, with enough separation to stay visible in a
  // 1440x900 first-person crop instead of merely satisfying local-space math.
  const lengthBiases = [0.78, 0.98, 1.06, 0.95] as const;
  // Metacarpal roots retain their compact 12mm pitch even though the visible
  // phalanges have different lengths. Scaling the buried roots with the new
  // length biases pulled the pinky web almost 17mm away from the ring finger.
  const rootBiases = [0.84, 0.98, 1.04, 0.96] as const;
  const rootRadii = [0.0057, 0.00585, 0.00595, 0.0058] as const;
  const middleRadii = [0.0049, 0.00505, 0.00515, 0.005] as const;
  const distalRadii = [0.00445, 0.00455, 0.00465, 0.0045] as const;
  const tipRadii = [0.00305, 0.0032, 0.0033, 0.00315] as const;
  // Q17 roots begin 3–5mm inside the compact palm boundary. Index/middle
  // alone reach the near visible edge; ring/pinky finish 22/27mm deeper and
  // lower, letting the magazine occlude them instead of showing four add-on
  // tubes. Each PIP starts from a different fan angle.
  const q16ReloadProfiles = [
    // Pinky/ring still terminate on the measured magazine plane, but their
    // curl lies behind the near silhouette so the camera never sees four
    // parallel hoses. Middle/index expose two distinct phalanx turns.
    [[-0.039, -0.024, -0.026], [-0.043, -0.030, -0.025], [-0.038, -0.027, -0.024], [-0.026, -0.024, -0.026]],
    [[-0.037, -0.011, -0.025], [-0.041, -0.016, -0.022], [-0.036, -0.013, -0.020], [-0.026, -0.011, -0.021]],
    [[-0.034, 0.005, -0.022], [-0.024, 0.009, 0.012], [-0.020, 0.007, 0.036], [-0.026, 0.005, 0.031]],
    [[-0.032, 0.018, -0.021], [-0.022, 0.021, 0.013], [-0.019, 0.018, 0.037], [-0.026, 0.017, 0.031]],
  ] as const;
  // In idle/fire the palm supplies the readable hand silhouette. Fingers stay
  // under the handguard and only their terminal pads emerge beyond its edge.
  const q16IdleProfiles = [
    [[-0.030, -0.021, -0.023], [-0.031, -0.022, -0.017], [-0.029, -0.022, -0.013], [-0.027, -0.021, -0.011]],
    [[-0.029, -0.009, -0.022], [-0.031, -0.010, -0.016], [-0.028, -0.009, -0.012], [-0.026, -0.009, -0.009]],
    // Q17o fixes Q17n's buried roots/PIPs exactly. Only the two camera-side
    // DIP necks and terminal centres each move 2.5mm away from Q17n in
    // authored UP (5mm more mutual separation). The 5mm FRONT stagger is untouched. This keeps
    // a continuous three-pixel background valley at native 1440p without
    // changing reload contact, pose, target 1 or the thumb web.
    [[-0.028, 0.005, -0.022], [-0.030, 0.006, -0.015], [-0.027, 0.0075, -0.011], [-0.025, 0.0075, -0.007]],
    [[-0.027, 0.018, -0.021], [-0.029, 0.019, -0.014], [-0.026, 0.0255, -0.006], [-0.024, 0.0245, -0.002]],
  ] as const;
  // The reload rotation is oblique to the magazine X plane, so a depth-staggered
  // fingertip row cannot share one authored RIGHT coordinate. These tiny
  // per-finger offsets preserve the same physical side-surface contact after
  // ring/pinky move behind and index/middle arc toward the camera.
  const q16TipRightOffsets = [0.00217, 0.00198, -0.00235, -0.00181] as const;
  const fingerDiagnostics: FingerDiagnostic[] = [];
  // One buried, continuous ridge supplies the knuckle silhouette. Individual
  // spheres produced four hardware-like buttons in reload close-up.
  const knuckleRidge = orientGeometry(
    new THREE.SphereGeometry(1, 10, 7),
    gripPoint(q16 ? -0.048 : -0.022, q16 ? 0.002 : 0, q16 ? -0.004 : 0),
    SUPPORT_MAGAZINE_RIGHT,
    SUPPORT_MAGAZINE_UP,
    SUPPORT_MAGAZINE_FRONT,
    new THREE.Vector3(q16 ? 0.0035 : 0.0048, q16 ? 0.021 : 0.0265, q16 ? 0.006 : 0.0075),
  );
  buckets.glove.push(q16
    ? attachIdleMorphPair(
        knuckleRidge,
        orientGeometry(
          new THREE.SphereGeometry(1, 10, 7),
          gripPoint(-0.036, 0, -0.002),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0090, 0.014, 0.0090),
        ),
        orientGeometry(
          new THREE.SphereGeometry(1, 10, 7),
          gripPoint(-0.0435, 0.002, -0.003),
          SUPPORT_MAGAZINE_RIGHT,
          SUPPORT_MAGAZINE_UP,
          SUPPORT_MAGAZINE_FRONT,
          new THREE.Vector3(0.0028, 0.018, 0.0058),
        ),
      )
    : knuckleRidge);
  for (let index = 0; index < fingerNames.length; index += 1) {
    const bias = lengthBiases[index]!;
    const up = fingerHeights[index]!;
    // Reload geometry is authored against the magazine. A matching-topology
    // idle morph wraps the same three phalanges beneath the handguard, which a
    // single rigid hand transform cannot achieve without floating in one pose.
    const pointFromTip = (right: number, front: number, height: number = up) => gripPoint(
      -0.029 + (right + 0.029) * bias,
      height,
      0.030 + (front - 0.030) * bias,
    );
    // Each wedge starts inside the compact loft and ends on the magazine face.
    // The 12mm height steps remain anatomical and give all four contacts a
    // readable stagger without fanning the fingertips toward the camera.
    const rootBias = rootBiases[index]!;
    const root = gripPoint(
      -0.029 + (-0.032 + 0.029) * rootBias,
      up,
      0.030 + (-0.030 - 0.030) * rootBias,
    );
    // Keep the root/PIP beneath the palm shell, then let only the middle and
    // distal pad emerge at its magazine-side edge. Rendering the earlier PIP
    // at +6mm exposed the full proximal span as four stripes across the back
    // of the hand; omitting it altogether made the wedges look detached.
    // The PIP rises to the dorsal silhouette before the DIP rolls back toward
    // the contact plane. This shallow C profile reads as four wrapped fingers
    // in the reload close-up; keeping every joint near right=-29mm produced
    // four painted-looking stripes across an otherwise oval palm.
    const pipFan = reloadPipFan[index]!;
    const dipFan = reloadDipFan[index]!;
    const pip = pointFromTip(
      reloadPipRights[index]!,
      reloadPipFronts[index]!,
      up + pipFan,
    );
    const dip = pointFromTip(
      reloadDipRights[index]!,
      reloadDipFronts[index]!,
      up + dipFan,
    );
    const tip = gripPoint(-0.029 + contactInset, up, 0.030);
    const q16Joints = q16ReloadProfiles[index]!.map(([right, height, front]) =>
      gripPoint(right, height, front),
    ) as [THREE.Vector3, THREE.Vector3, THREE.Vector3, THREE.Vector3];
    // Keep the contact inset parameter authoritative even inside the Q17
    // profile; only height/depth differ between fingers at the terminal pad.
    q16Joints[3] = gripPoint(
      -0.029 + contactInset + q16TipRightOffsets[index]!,
      q16ReloadProfiles[index]![3][1],
      q16ReloadProfiles[index]![3][2],
    );
    const joints = q16 ? q16Joints : [root, pip, dip, tip] as const;
    const radii = [rootRadii[index]!, middleRadii[index]!, distalRadii[index]!] as const;
    const idleUp = idleFingerHeights[index]!;
    const sharedIdleJoints = [
      gripPoint(-0.028, up * 0.94, -0.028),
      gripPoint(-0.048, idleUp + 0.004, idlePipFronts[index]!),
      gripPoint(-0.04, idleUp * 0.96 + 0.012, idleDipFronts[index]!),
      gripPoint(-0.034, up * 0.94 + 0.022, idleTipFronts[index]!),
    ] as const;
    const q16IdleJoints = q16IdleProfiles[index]!.map(([right, height, front]) =>
      gripPoint(right, height, front),
    ) as [THREE.Vector3, THREE.Vector3, THREE.Vector3, THREE.Vector3];
    const idleJoints = q16 ? q16IdleJoints : sharedIdleJoints;
    const segmentRadii = [radii[0], radii[1], radii[2], tipRadii[index]!] as const;
    // Q17n holds the root/PIP radii with Q17j, then contracts only the idle
    // DIP into a neck before a shallow rounded pad. The base/reload tube keeps
    // its exact Q17m radii and vertex order; this is an absolute morph only.
    const idleSegmentRadii = q16 && index >= 2
      ? [
          radii[0],
          radii[1],
          index === 2 ? 0.00255 : 0.00245,
          index === 2 ? 0.00235 : 0.00225,
        ] as const
      : segmentRadii;
    const exchangeProfiles = [
      null,
      null,
      [[-0.036, 0.005, -0.022], [-0.034, 0.008, 0.006], [-0.030, 0.007, 0.025]],
      [[-0.034, 0.018, -0.021], [-0.033, 0.021, 0.006], [-0.029, 0.019, 0.025]],
    ] as const;
    const exchangeProfile = exchangeProfiles[index];
    const exchangeJoints = q16 && exchangeProfile
      ? [
          ...exchangeProfile.map(([right, height, front]) => gripPoint(right, height, front)),
          joints[3]!.clone(),
        ] as [THREE.Vector3, THREE.Vector3, THREE.Vector3, THREE.Vector3]
      : joints;
    // One centripetal tube follows all four anatomical joints. The earlier
    // three sphere-ended segments repeated the same rounded cap three times
    // per finger; in reload projection that became four ladder-like ribs.
    // Diagnostics still retain the exact MCP/PIP/DIP/tip chain and contact.
    const reloadFinger = q16
      ? roundedContinuousFingerTube(joints, segmentRadii, 8, 0.58)
      : continuousFingerTube(joints, segmentRadii, 8, 0.58);
    const idleTipCapRadius = q16 && index >= 2
      ? index === 2 ? 0.00405 : 0.00395
      : idleSegmentRadii[3];
    // In the authored support basis local pad X is almost exactly hand UP,
    // i.e. the index/middle gap axis. Keep that axis compact while broadening
    // the orthogonal shoulder: the pad reads wide without closing the valley.
    const idleTipHorizontalScale = q16 && index >= 2 ? 0.72 : 0.98;
    const idleTipDepthScale = q16 && index >= 2 ? 1.20 : 0.90;
    // 0.86 is shorter than Q17n's 1.06 capsule, but still overlaps the 2.25–
    // 2.35mm tube neck. A smaller value exposed the tube's octagonal end face
    // and brought the rectangular-tip artefact back at native resolution.
    const idleTipLongitudinalScale = q16 && index >= 2 ? 0.86 : 1.06;
    const idleFinger = q16
      ? roundedContinuousFingerTube(
          idleJoints,
          idleSegmentRadii,
          8,
          0.58,
          idleTipHorizontalScale,
          idleTipDepthScale,
          Math.PI / 8,
          idleTipLongitudinalScale,
          idleTipCapRadius,
        )
      : continuousFingerTube(idleJoints, segmentRadii, 8, 0.58);
    buckets.glove.push(q16
      ? attachIdleMorphPair(
          reloadFinger,
          idleFinger,
          roundedContinuousFingerTube(exchangeJoints, segmentRadii, 8, 0.58),
        )
      : attachIdleMorph(reloadFinger, idleFinger));
    if (q16 && index >= 2) {
      // Shallow articulated creases make the two camera-side fingers read as
      // proximal + distal phalanges. They are partial cloth seams, not raised
      // armour rings, and their idle counterparts disappear under the rail
      // with the same morph as the finger surface.
      for (const jointIndex of [1, 2] as const) {
        const reloadDirection = joints[jointIndex + 1]!
          .clone()
          .sub(joints[jointIndex - 1]!);
        const idleDirection = idleJoints[jointIndex + 1]!
          .clone()
          .sub(idleJoints[jointIndex - 1]!);
        const exchangeDirection = exchangeJoints[jointIndex + 1]!
          .clone()
          .sub(exchangeJoints[jointIndex - 1]!);
        buckets.stitch.push(attachIdleMorphPair(
          torusAround(
            joints[jointIndex]!,
            reloadDirection,
            segmentRadii[jointIndex]! * 1.01,
            0.00032,
            Math.PI * 0.86,
          ),
          torusAround(
            idleJoints[jointIndex]!,
            idleDirection,
            segmentRadii[jointIndex]! * 1.01,
            0.00032,
            Math.PI * 0.86,
          ),
          torusAround(
            exchangeJoints[jointIndex]!,
            exchangeDirection,
            segmentRadii[jointIndex]! * 0.72,
            0.00018,
            Math.PI * 0.86,
          ),
        ));
      }
    }
    fingerDiagnostics.push({
      name: fingerNames[index]!,
      triggerFinger: false,
      joints: joints.map((joint) => joint.toArray() as [number, number, number]),
      idleJoints: idleJoints.map((joint) => joint.toArray() as [number, number, number]),
      exchangeJoints: q16
        ? exchangeJoints.map((joint) => joint.toArray() as [number, number, number])
        : undefined,
      radii,
      tipRadius: tipRadii[index]!,
      idleTipRadius: idleTipCapRadius,
      idleTerminalNeckRadius: idleSegmentRadii[3],
      idleTipHorizontalScale: q16 ? idleTipHorizontalScale : 0.9,
      idleTipDepthScale: q16 ? idleTipDepthScale : 0.72,
      idleTipLongitudinalScale: q16 ? idleTipLongitudinalScale : 1.12,
      idleRadii: [idleSegmentRadii[0], idleSegmentRadii[1], idleSegmentRadii[2]],
      // The terminal outline combines the eight-sided tube end and the
      // staggered rounded pad silhouette. Twelve visible facets are retained
      // without changing the frozen reload vertex/index buffers.
      idleTerminalFacetCount: q16 ? 12 : 8,
    });

  }

  // Two visible thumb sections cross only the upper edge. The hidden web
  // joins the thenar volume; total visible length is ~34mm (Q: 58% of P).
  const thumbRoot = q16
    ? gripPoint(-0.017, 0.027, -0.006)
    : gripPoint(0.012, 0.021, 0.006);
  // Keep the IP joint on the magazine's opposed side instead of sending it
  // back through the box. Only the short terminal pad crosses the upper edge,
  // so the root/thenar/contact line remains visible beside the magazine.
  const thumbJoint = q16
    ? gripPoint(0.006, 0.034, 0.014)
    : gripPoint(0.036, 0.023, 0.020);
  const thumbTip = gripPoint(0.032 - contactInset, q16 ? 0.026 : 0.019, 0.030);
  const idleThumbRoot = gripPoint(q16 ? -0.002 : 0, q16 ? 0.010 : 0.016, q16 ? -0.006 : -0.006);
  const idleThumbJoint = gripPoint(q16 ? 0.004 : -0.02, q16 ? 0.020 : 0.033, q16 ? -0.001 : 0.002);
  // Q17 keeps the thumb on the upper/opposed side, but within the palm's
  // 34mm knuckle extent. The former 52mm tip emerged alone above an occluding
  // receiver during return and looked like a detached triangular fragment.
  const idleThumbTip = gripPoint(q16 ? -0.024 : -0.036, q16 ? 0.0285 : 0.05, q16 ? 0.0005 : -0.004);
  // During the exchange the thumb leaves the camera-side metacarpal edge,
  // bends through one high IP joint, then returns to the frozen magazine-side
  // contact coordinate. The root lobe is therefore visible at r03 while the
  // thinner terminal remains physically seated instead of showing through
  // the gold magazine face.
  const exchangeThumbRoot = q16 ? gripPoint(-0.018, 0.0250, 0.0120) : thumbRoot;
  const exchangeThumbJoint = q16 ? gripPoint(-0.023, 0.0360, 0.0220) : thumbJoint;
  const exchangeThumbTip = q16
    // The four frozen finger pads own weapon contact during the exchange.
    // End this target-only thumb after two compact, opposed phalanges so its
    // open V cannot close against the magazine into a handle silhouette.
    ? gripPoint(-0.012, 0.0320, 0.0210)
    : thumbTip;
  // The web leaves the palm below the thumb/root tangency, keeping both
  // volumes physically connected while opening a small V-shaped negative
  // valley above it in the 1440p first-person projection.
  const idleThumbWebStart = q16 ? gripPoint(-0.0285, 0.0095, -0.0105) : null;
  const exchangeThumbWebStart = q16 ? gripPoint(-0.034, 0.0140, 0.0080) : null;
  const reloadThumb = (q16 ? roundedContinuousFingerTube : continuousFingerTube)(
    [thumbRoot, thumbJoint, thumbTip],
    [0.0074, 0.006, 0.0041],
    8,
    0.62,
  );
  const idleThumb = (q16 ? roundedContinuousFingerTube : continuousFingerTube)(
    [idleThumbRoot, idleThumbJoint, idleThumbTip],
    q16 ? [0.0048, 0.0044, 0.0040] : [0.0074, 0.006, 0.0041],
    8,
    0.62,
  );
  buckets.glove.push(q16
    ? attachIdleMorphPair(
        reloadThumb,
        idleThumb,
        roundedContinuousFingerTube(
          [exchangeThumbRoot, exchangeThumbJoint, exchangeThumbTip],
          [0.0055, 0.0047, 0.0038],
          8,
          0.62,
        ),
      )
    : attachIdleMorph(reloadThumb, idleThumb));
  if (q16) {
    // Thumb-index webbing is a low continuous bridge from the thenar mass to
    // the proximal thumb. It removes the detached far-side oval in the reload
    // close-up while preserving a real negative space beneath the IP joint.
    buckets.glove.push(attachIdleMorphPair(
      capsuleBetween(gripPoint(-0.027, 0.021, -0.010), thumbRoot, 0.0052, 3, 8),
      capsuleBetween(idleThumbWebStart!, idleThumbRoot, 0.0030, 3, 8),
      capsuleBetween(exchangeThumbWebStart!, exchangeThumbRoot, 0.0030, 3, 8),
    ));
  }
  // Two muted dorsal seam dashes provide cloth scale without a bright outline.
  buckets.stitch.push(
    capsuleBetween(
      gripPoint(q16 ? -0.041 : 0.003, -0.010, -0.010),
      gripPoint(q16 ? -0.041 : 0.003, 0.002, -0.010),
      0.00055,
      2,
      5,
    ),
    capsuleBetween(
      gripPoint(q16 ? -0.041 : 0.003, 0.008, -0.010),
      gripPoint(q16 ? -0.041 : 0.003, 0.018, -0.010),
      0.00055,
      2,
      5,
    ),
  );

  // Q17 moves the whole hand, not only its fingers. Every material family must
  // therefore expose the same absolute idle morph; otherwise the suede palm
  // pads and dorsal armour remain beside the magazine while the glove shell
  // returns to the fore-end, recreating the detached fan seen in Q15 r05.
  if (q16) {
    for (const parts of Object.values(buckets)) {
      for (const part of parts) ensureExchangeCorrectionMorph(part);
    }
  } else {
    for (const part of buckets.glove) attachStationaryIdleMorph(part);
  }
  const merged = {
    glove: mergeHandParts(buckets.glove, 'glove'),
    palm: mergeHandParts(buckets.palm, 'palm'),
    armor: mergeHandParts(buckets.armor, 'armor'),
    stitch: mergeHandParts(buckets.stitch, 'stitch'),
  };
  const fingerTipCenter = fingerDiagnostics.reduce(
    (sum, finger) => sum.add(new THREE.Vector3(...finger.joints[3]!)),
    new THREE.Vector3(),
  ).multiplyScalar(1 / fingerDiagnostics.length);
  // The authored grasp centre is independent from surface pads. Using their
  // midpoint as the hand anchor pulled one side behind the magazine whenever
  // the pads used different depth values.
  const anchor = gripAnchor.clone();
  const adjacentSurfaceClearances = fingerDiagnostics.slice(1).map((finger, index) => {
    const previous = fingerDiagnostics[index]!;
    // The proximal roots are deliberately buried inside the palm loft. Q17's
    // staggered depth intentionally yields unequal distal gaps instead of a
    // uniform comb, while the shared grasp retains its compact spacing.
    return new THREE.Vector3(...finger.joints[2]!).distanceTo(
      new THREE.Vector3(...previous.joints[2]!),
    ) - finger.radii[2] - previous.radii[2];
  });
  const diagnostic: SupportGripDiagnostic = {
    anchor: anchor.toArray(),
    fingerTipCenter: fingerTipCenter.toArray(),
    thumbTip: thumbTip.toArray(),
    thumbTipRadius: 0.0041,
    adjacentSurfaceClearances,
    palmCenter: palmCenter.toArray(),
    palmInteriorNormal: (q16
      ? SUPPORT_MAGAZINE_RIGHT
      : SUPPORT_MAGAZINE_RIGHT.clone().negate()).toArray(),
    backNormal: (q16
      ? SUPPORT_MAGAZINE_RIGHT.clone().negate()
      : SUPPORT_MAGAZINE_RIGHT).toArray(),
    curlNormal: SUPPORT_MAGAZINE_FRONT.toArray(),
  };
  merged.glove.userData.handGrip = 'support';
  merged.glove.userData.fingerDiagnostics = fingerDiagnostics;
  merged.glove.userData.thumbJoints = [thumbRoot, thumbJoint, thumbTip].map((joint) =>
    joint.toArray(),
  );
  merged.glove.userData.idleThumbJoints = [idleThumbRoot, idleThumbJoint, idleThumbTip].map(
    (joint) => joint.toArray(),
  );
  if (q16) {
    merged.glove.userData.exchangeThumbJoints = [
      exchangeThumbRoot,
      exchangeThumbJoint,
      exchangeThumbTip,
    ].map((joint) => joint.toArray());
  }
  if (idleThumbWebStart) merged.glove.userData.idleThumbWebStart = idleThumbWebStart.toArray();
  if (q16) {
    merged.glove.userData.exchangeThumbWebStart = exchangeThumbWebStart!.toArray();
    merged.glove.userData.exchangeThumbRadii = [0.0055, 0.0047, 0.0038];
    merged.glove.userData.exchangeThumbWebRadius = 0.0030;
    merged.glove.userData.idleThumbRadii = [0.0048, 0.0044, 0.0040];
    merged.glove.userData.idleThumbWebRadius = 0.0030;
  }
  merged.glove.userData.supportGrip = diagnostic;
  merged.glove.userData.anatomyVersion = q16 ? 10 : 7;
  merged.glove.userData.idleMorph = true;
  merged.glove.userData.connectedFingerRoots = true;
  for (const geometry of Object.values(merged)) {
    geometry.computeBoundingBox();
    geometry.userData.palmFacesWeapon = true;
  }
  return merged;
}

/**
 * 手を「暗い一塊」ではなく、手首・掌・5本指・関節・掌パッド・縫い目へ分ける。
 * フルフィンガーのタクティカルグローブにすることで、どの武器色／迷彩でも銃の一部に見えない。
 * familyごとに結合するため、形状密度を増やしても片手4DCに固定される。
 */
function buildHandGeometries(
  side: -1 | 1,
  grip: HandGrip,
  supportContactInset = 0,
  supportGripVariant: SupportGripVariant = 'shared',
): Record<HandMaterialFamily, THREE.BufferGeometry> {
  if (grip === 'support') {
    return buildSupportHandGeometries(side, supportContactInset, supportGripVariant);
  }
  const legacyGrip = grip as HandGrip;
  // 支持手は掌を銃側(+local Y)へ向ける。単純に左手を右手と同じ向きで置くと、
  // 手の甲がハンドガードへ貼り付き「銃の部品」に見える。いったん反対側の手型を作って
  // Z軸で180°返すことで、親指の左右は正しいまま掌・4指だけを銃へ巻き付ける。
  const supportHand = legacyGrip === 'support' || legacyGrip === 'guard';
  const supportGrip = legacyGrip === 'support';
  const guardHand = legacyGrip === 'guard';
  const powerHand = legacyGrip === 'power';
  const shootingHand = legacyGrip === 'trigger';
  const geometrySide: -1 | 1 = supportHand ? (side === -1 ? 1 : -1) : side;
  const buckets: Record<HandMaterialFamily, THREE.BufferGeometry[]> = {
    glove: [],
    palm: [],
    armor: [],
    stitch: [],
  };

  // 支持手はカメラに近く投影が大きい。V6の86mm幅の掌は画面上で
  // ボクシンググローブに見えたため、支持手だけ掌幅/厚みを約20%絞る。
  // 指の長さは縮めず、掌と指の比率を人体に近づける。
  const wristRadius = supportGrip ? 0.025 : 0.03;
  const wristFlare = supportGrip ? 0.028 : 0.034;
  const wristLength = supportGrip ? 0.054 : 0.062;
  const bridgeScale = supportGrip
    ? new THREE.Vector3(0.0305, 0.016, 0.015)
    : new THREE.Vector3(0.038, 0.028, 0.025);

  // 手首から掌までを連続させる。旧実装では掌だけが銃の下に浮き、黒い銃床に見えていた。
  buckets.glove.push(
    transformGeometry(
      new THREE.CylinderGeometry(wristRadius, wristFlare, wristLength, 12, 2),
      new THREE.Vector3(0, 0, supportGrip ? 0.062 : 0.067),
      new THREE.Euler(Math.PI / 2, 0, 0),
    ),
    taperedPalmWedge(supportGrip),
    // 掌から指根までの中手骨ブリッジ。指節の根元を掌の奥に必ず重ね、
    // 斜めから見た時に4本の黒い棒が浮くシルエットを消す。
    transformGeometry(
      new THREE.SphereGeometry(1, 14, 9),
      new THREE.Vector3(0, -0.001, supportGrip ? -0.032 : -0.037),
      new THREE.Euler(0.05, 0, 0),
      bridgeScale,
    ),
  );

  // 母指球は掌本体と親指根を連続させる。独立した平面パッドを掌中央へ置くと、
  // 斜視で巨大な円盤に見えるため、親指寄りの非対称な量塊として組む。
  buckets.glove.push(
    transformGeometry(
      new THREE.SphereGeometry(1, 12, 8),
      new THREE.Vector3(0.021 * geometrySide, supportGrip ? 0.009 : -0.009, 0.005),
      new THREE.Euler(0.16, 0.08 * geometrySide, -0.12 * geometrySide),
      supportGrip
        ? new THREE.Vector3(0.015, 0.012, 0.024)
        : new THREE.Vector3(0.018, 0.015, 0.026),
    ),
  );

  // 掌スエードは武器側だけに薄く密着する。甲側からはウェッジ本体とナックルが見える。
  buckets.palm.push(
    transformGeometry(
      new THREE.SphereGeometry(1, 12, 8),
      new THREE.Vector3(
        0.004 * geometrySide,
        supportGrip ? 0.0185 : -0.027,
        guardHand ? 0.004 : 0.001,
      ),
      new THREE.Euler(0.08, 0, 0),
      supportGrip
        ? new THREE.Vector3(0.024, 0.0024, 0.028)
        : new THREE.Vector3(0.032, 0.005, guardHand ? 0.036 : 0.043),
    ),
  );

  // 実測したタクティカルグローブの拳幅へ寄せる。旧 52.5mm の指根幅は、斜めから
  // 見た支持手で4本が扇状に分離して「熊手」に見えた。掌の外形は維持しつつ指根だけを
  // 45mmへ狭め、隣接指の柔らかい接触をシルエットで読ませる。
  // V6は15mmピッチに対し指根直径16.8mmで、数学的に隣接指が融合していた。
  // V7は支持手のみ16mmピッチと約11.8mm径にし、4mm以上の表面間隙を作る。
  const xOffsets = supportGrip
    ? [-0.024, -0.008, 0.008, 0.024]
    : [-0.0225, -0.0075, 0.0075, 0.0225];
  // -Xから小指→薬指→中指→人差し指。旧実装は i===0 を人差し指としており、
  // 右手の小指だけをトリガー方向へ伸ばす左右逆の輪郭になっていた。
  const fingerNames = ['pinky', 'ring', 'middle', 'index'] as const;
  const lengthBiases = [0.78, 1.01, 1.05, 0.94];
  const supportKnuckleArc = [-0.027, -0.033, -0.036, -0.032] as const;
  const fingerDiagnostics: FingerDiagnostic[] = [];
  for (let i = 0; i < xOffsets.length; i += 1) {
    const x = (xOffsets[i] ?? 0) * geometrySide;
    const lengthBias = lengthBiases[i] ?? 1;
    const fingerName = fingerNames[i]!;
    // 射撃手の人差し指だけを半握りにする。杖・弓・クナイは power 握りなので
    // 人差し指も柄へ巻き、存在しないトリガーを指す「角」を作らない。
    const triggerFinger = grip === 'trigger' && fingerName === 'index';
    const base = new THREE.Vector3(
      x,
      guardHand ? -0.001 : supportGrip ? -0.003 : supportHand ? -0.004 : -0.008,
      guardHand
        ? -0.033
        : supportGrip
          ? supportKnuckleArc[i]!
          : supportHand
            ? -0.037
            : -0.04,
    );
    const segmentLengths = (
      triggerFinger
        ? [0.027, 0.0185, 0.0125]
        : guardHand
          ? [0.026, 0.019, 0.0128]
          : supportGrip
            ? [0.029, 0.021, 0.0145]
            : supportHand
              ? [0.024, 0.017, 0.0116]
            : shootingHand
              ? [0.027, 0.0185, 0.0125]
              : [0.027, 0.0195, 0.013]
    ).map((length) => length * lengthBias);
    // 直進(-Z)ではなく第1関節から掌側(-Y)へ深く曲げる。角度は各節の絶対方向。
    // PIP/DIPを2.5rad以上まで戻すことで、末節が掌面の近くへ帰り、横から見ても
    // 4本の指先が珠の列／熊手のように突き出さない閉じた握り輪郭になる。
    const jointAngles = triggerFinger
        ? [1.02, 1.56, 2.08]
      : guardHand
        ? [1.48, 2.74, 3.1]
        : supportGrip
          // 近位節を長く見せ、PIP/DIPで渐次折り返す。各指先が掌下の
          // 同じ点へ集まる旧曲げを廃し、隣接指の隙間が斜視でも残る。
          ? [0.42, 1.2, 2.2]
          : supportHand
            ? [1.32, 2.25, 2.72]
          : powerHand
            ? [1.46, 2.72, 3.08]
            : [1.5, 2.84, 3.14];
    const joints = [base];
    for (let jointIndex = 0; jointIndex < segmentLengths.length; jointIndex += 1) {
      const angle = jointAngles[jointIndex] ?? 0;
      const length = segmentLengths[jointIndex] ?? 0;
      const previous = joints[joints.length - 1]!;
      // 外側に開かず、指先ほど掌中心へ僅かに収束させる。
      const fanScale = supportGrip ? 0.018 : supportHand ? 0.012 : 0.018;
      const fan = -geometrySide * (i - 1.5) * fanScale * (jointIndex + 1);
      joints.push(previous.clone().add(new THREE.Vector3(
        Math.sin(fan) * length,
        -Math.sin(angle) * length,
        -Math.cos(angle) * length,
      )));
    }
    const radii = supportGrip
      ? [0.0059, 0.0051, 0.0043] as const
      : shootingHand
      ? [0.0077, 0.0069, 0.0061] as const
      : [0.0084, 0.0076, 0.0066] as const;
    // 遠近法で針のように見えないよう、支持手と柄握りは末節を丸める。半径は増やすが
    // 節長を短くしたためポリゴン数／描画回数は増えない。
    const tipRadius = supportGrip
      ? 0.003
      : triggerFinger
        ? 0.0042
        : shootingHand
          ? 0.00425
          : 0.0048;
    buckets.glove.push(capsuleBetween(joints[0]!, joints[1]!, radii[0]));
    // 3節すべてを同じ本体布で連続させる。V6/V7初期はPIPだけを明色にしていたため、
    // 暗い近位・末節が消え、ベージュのソーセージが4本浮いて見えていた。
    buckets.glove.push(capsuleBetween(joints[1]!, joints[2]!, radii[1]));
    buckets.glove.push(taperedFingerSegment(joints[2]!, joints[3]!, radii[2], tipRadius));
    fingerDiagnostics.push({
      name: fingerName,
      triggerFinger,
      joints: joints.map((joint) => [joint.x, joint.y, joint.z] as [number, number, number]),
      radii,
      tipRadius,
    });

    // 独立した4つのナックル。大きな一枚板を廃止し、指の始点を目で追えるようにする。
    const knuckle = new THREE.SphereGeometry(1, 9, 6);
    const knuckleSpread = geometrySide * (i - 1.5) * (supportGrip ? 0.015 : 0.018);
    transformGeometry(
      knuckle,
      // 外周へ飛び出す黒い球ではなく、手袋本体へ半分埋めた薄い保護パッド。
      new THREE.Vector3(x, supportGrip ? -0.017 : 0.0215, base.z + 0.006),
      new THREE.Euler(-0.12, 0, knuckleSpread),
      supportGrip
        ? new THREE.Vector3(0.0056, 0.0021, 0.0064)
        : new THREE.Vector3(0.0074, 0.0032, 0.0082),
    );
    buckets.armor.push(knuckle);
  }

  // 親指は掌の横から斜めに生える2節構造。フルフィンガー手袋として材質を統一する。
  // 支持親指は4指と同じ掌面へ畓むのではなく、反対面から人差し指側へ対置する。
  // 支持手は後段でZ軸180°回すため、ここの+Yが最終的な親指側(-Y)になる。
  const thumbRoot = supportGrip
    ? new THREE.Vector3(0.025 * geometrySide, 0.005, 0.012)
    : new THREE.Vector3(0.03 * geometrySide, -0.004, 0.01);
  const thumbJoint = supportGrip
    ? thumbRoot.clone().add(new THREE.Vector3(0.011 * geometrySide, 0.013, -0.016))
    : thumbRoot.clone().add(new THREE.Vector3(
        0.012 * geometrySide,
        guardHand ? -0.011 : -0.01,
        -0.016,
      ));
  const thumbTip = supportGrip
    ? thumbJoint.clone().add(new THREE.Vector3(-0.004 * geometrySide, 0.023, -0.024))
    : thumbJoint.clone().add(new THREE.Vector3(
        -0.003 * geometrySide,
        -0.016,
        -0.014,
      ));
  buckets.glove.push(capsuleBetween(thumbRoot, thumbJoint, supportGrip ? 0.0067 : 0.0095, 4, 8));
  if (supportGrip) {
    buckets.glove.push(taperedFingerSegment(thumbJoint, thumbTip, 0.0053, 0.0034));
  } else {
    buckets.palm.push(capsuleBetween(thumbJoint, thumbTip, 0.0079, 4, 8));
  }

  // 分割型ナックルプレート、手首ストラップ、掌の縫製線。小さな陰影が距離感を作る。
  const backPlate = new THREE.SphereGeometry(1, 12, 7);
  transformGeometry(
    backPlate,
    new THREE.Vector3(0, supportGrip ? -0.018 : 0.024, supportGrip ? 0.011 : 0.008),
    new THREE.Euler(-0.08, 0, 0),
    supportGrip
      ? new THREE.Vector3(0.016, 0.0032, 0.013)
      : new THREE.Vector3(0.021, 0.0045, 0.017),
  );
  buckets.armor.push(backPlate);
  const wristStrap = new THREE.TorusGeometry(
    supportGrip ? 0.027 : 0.031,
    supportGrip ? 0.0025 : 0.0032,
    5,
    18,
  );
  wristStrap.translate(0, 0, supportGrip ? 0.074 : 0.079);
  buckets.armor.push(wristStrap);
  // 縫い目は手袋表面へ埋め込む短い飾り線。長いCapsuleは斜視時に4本の指／爪のように
  // レシーバ外へ突き出して見えるため、拳幅内に収まる短いダッシュだけを残す。
  const seam = new THREE.CapsuleGeometry(0.0008, 0.03, 2, 5);
  transformGeometry(
    seam,
    new THREE.Vector3(0, supportGrip ? -0.021 : 0.0275, 0.014),
    new THREE.Euler(0, 0, Math.PI / 2),
  );
  buckets.stitch.push(seam);
  for (const sx of [-0.014, 0.014]) {
    const stitch = new THREE.CapsuleGeometry(0.0007, 0.008, 2, 5);
    transformGeometry(
      stitch,
      new THREE.Vector3(sx * geometrySide, supportGrip ? -0.021 : 0.027, 0.006),
      new THREE.Euler(Math.PI / 2, 0, 0),
    );
    buckets.stitch.push(stitch);
  }

  const merged = {
    glove: mergeHandParts(buckets.glove, 'glove'),
    palm: mergeHandParts(buckets.palm, 'palm'),
    armor: mergeHandParts(buckets.armor, 'armor'),
    stitch: mergeHandParts(buckets.stitch, 'stitch'),
  };
  if (supportHand) {
    for (const geometry of Object.values(merged)) {
      geometry.rotateZ(Math.PI);
      geometry.computeBoundingBox();
      geometry.userData.palmFacesWeapon = true;
    }
  }
  const diagnosticRotation = supportHand
    ? (joint: readonly [number, number, number]) => [-joint[0], -joint[1], joint[2]] as const
    : (joint: readonly [number, number, number]) => joint;
  merged.glove.userData.handGrip = grip;
  merged.glove.userData.fingerDiagnostics = fingerDiagnostics.map((finger) => ({
    ...finger,
    joints: finger.joints.map(diagnosticRotation),
  }));
  merged.glove.userData.thumbJoints = [thumbRoot, thumbJoint, thumbTip].map((joint) =>
    diagnosticRotation([joint.x, joint.y, joint.z]),
  );
  if (supportGrip) {
    const transformedFingers = fingerDiagnostics.map((finger) => ({
      ...finger,
      joints: finger.joints.map(diagnosticRotation),
    }));
    const fingerTipCenter = transformedFingers.reduce(
      (sum, finger) => sum.add(new THREE.Vector3(...finger.joints[3]!)),
      new THREE.Vector3(),
    ).multiplyScalar(1 / transformedFingers.length);
    const transformedThumbTip = new THREE.Vector3(
      ...diagnosticRotation([thumbTip.x, thumbTip.y, thumbTip.z]),
    );
    // 4指先の中心と対置した親指先の中点が、マガジン/グリップを挟む実把持中心。
    const anchor = fingerTipCenter.clone().add(transformedThumbTip).multiplyScalar(0.5);
    const adjacentSurfaceClearances = transformedFingers.slice(1).map((finger, index) => {
      const previous = transformedFingers[index]!;
      const rootDistance = new THREE.Vector3(...finger.joints[0]!).distanceTo(
        new THREE.Vector3(...previous.joints[0]!),
      );
      return rootDistance - finger.radii[0] - previous.radii[0];
    });
    const diagnostic: SupportGripDiagnostic = {
      anchor: anchor.toArray(),
      fingerTipCenter: fingerTipCenter.toArray(),
      thumbTip: transformedThumbTip.toArray(),
      thumbTipRadius: 0.0034,
      adjacentSurfaceClearances,
      palmCenter: [0, 0, 0.006],
      palmInteriorNormal: [0, -1, 0],
      backNormal: [0, 1, 0],
      curlNormal: [0, -1, 0],
    };
    merged.glove.userData.supportGrip = diagnostic;
    merged.glove.userData.anatomyVersion = 7;
  }
  merged.glove.userData.connectedFingerRoots = true;
  return merged;
}

function buildConnectedSleeve(
  side: -1 | 1,
  material: THREE.MeshStandardMaterial,
  pose: FirstPersonArmPose,
  grip: HandGrip,
  supportGripVariant: SupportGripVariant,
): THREE.Mesh {
  // 手首を始点、武器別 arm.position を画面下側の肘／肩アンカーとして使う。
  // 以前は全武器で hand local +Z へ固定生成していたため、手を内側へ回すほど袖まで
  // 画面右へ捻れ、両腕が一本化して見えていた。アンカーを hand local へ逆変換すれば、
  // 掌の回転と「腕が身体へ帰る方向」を独立させつつ、接続自体は hand 階層で保証できる。
  // The support palm is offset toward its dorsal side so its inner face can
  // actually wrap a magazine. Move the sleeve attachment by the exact same
  // local amount; leaving it at y=0 exposed the capped forearm as a floating
  // circular disk during reload.
  const supportGrip = grip === 'support';
  // The V7 support palm moved left/rear and toward the knuckles. The sleeve
  // must meet that authored wrist exactly; otherwise its wide circular cap
  // reads as a detached second hand during the magazine exchange.
  const q16 = supportGrip && supportGripVariant === 'kaede-q17';
  // Q17 starts the sleeve 11.8mm inside the glove cuff, not at its exposed
  // rear edge. The first tapered sleeve segment therefore runs underneath the
  // whole cuff before heading toward the elbow: no circular cap or wrist seam
  // can open while the complete hand moves during reload.
  const wrist = supportGrip
    ? q16
      ? supportGripPoint(-0.0325, -0.0338, -0.0132)
      : supportGripPoint(-0.036, -0.052, -0.018)
    : new THREE.Vector3(0, 0, 0.073);
  const handPosition = new THREE.Vector3(pose.hand[0], pose.hand[1], pose.hand[2]);
  const handRotation = new THREE.Euler(pose.hand[3], pose.hand[4], pose.hand[5]);
  const inverseHandRotation = new THREE.Quaternion().setFromEuler(handRotation).invert();
  const elbow = new THREE.Vector3(pose.arm[0], pose.arm[1], pose.arm[2])
    .sub(handPosition)
    .applyQuaternion(inverseHandRotation);
  // 肘までの直線を二度だけ穏やかに曲げる。曲げ量はアンカー距離に比例し、拳銃から
  // 重火器まで同じ解像度／同じ5DCのまま、配管ではなく自然な前腕シルエットにする。
  const reach = wrist.distanceTo(elbow);
  const bend = supportGrip
    ? q16
      ? new THREE.Vector3(0.018 * side, -0.016, Math.min(0.026, reach * 0.08))
      : new THREE.Vector3(0.011 * side, -0.009, Math.min(0.017, reach * 0.055))
    : new THREE.Vector3(0.018 * side, -0.014, Math.min(0.026, reach * 0.08));
  const fore = wrist.clone().lerp(elbow, 0.3).addScaledVector(bend, 0.75);
  const mid = wrist.clone().lerp(elbow, 0.64).add(bend);
  const radii = supportGrip
    ? q16
      ? [0.0208, 0.0275, 0.036, 0.048] as const
      : [0.0185, 0.0205, 0.0245, 0.0325] as const
    : [0.031, 0.036, 0.044, 0.056] as const;
  const parts: THREE.BufferGeometry[] = [
    cylinderBetween(wrist, fore, radii[0], radii[1], 16, q16 ? [1.28, 0.68] : undefined),
    cylinderBetween(fore, mid, radii[1], radii[2], 16, q16 ? [1.24, 0.72] : undefined),
    cylinderBetween(mid, elbow, radii[2], radii[3], 16, q16 ? [1.18, 0.76] : undefined),
  ];
  tintGeometry(parts[0]!, 0.96);
  tintGeometry(parts[1]!, 0.9);
  tintGeometry(parts[2]!, 0.8);

  // 袖口と皺は同一ジオメトリへ結合。追加ドローコール無しで布らしい輪郭を残す。
  if (supportGrip) {
    // The dark glove cuff is authored in the hand mesh. Three partial rings
    // follow the actual tapered forearm spline and read as cloth compression,
    // never as a second skin-coloured cylinder.
    for (const [start, end, alpha, radius] of [
      [wrist, fore, 0.36, q16 ? 0.024 : 0.0195],
      [fore, mid, 0.46, q16 ? 0.034 : 0.024],
      [mid, elbow, 0.34, q16 ? 0.045 : 0.030],
    ] as const) {
      const fold = torusAround(
        start.clone().lerp(end, alpha),
        end.clone().sub(start),
        radius,
        0.0009,
      );
      tintGeometry(fold, 0.94);
      parts.push(fold);
    }
  } else {
    const cuff = new THREE.CylinderGeometry(0.037, 0.034, 0.026, 10, 1);
    transformGeometry(cuff, new THREE.Vector3(0, 0, 0.08), new THREE.Euler(Math.PI / 2, 0, 0));
    tintGeometry(cuff, 0.7);
    parts.push(cuff);
    for (const [x, y, z, radius] of [
      [0.006 * side, -0.005, 0.13, 0.028],
      [0.022 * side, -0.021, 0.205, 0.034],
      [0.043 * side, -0.054, 0.292, 0.041],
    ] as const) {
      const fold = new THREE.TorusGeometry(radius, 0.0012, 4, 10, Math.PI * 1.1);
      transformGeometry(
        fold,
        new THREE.Vector3(x, y, z),
        new THREE.Euler(Math.PI / 2 + 0.12, side * 0.04, 0),
        new THREE.Vector3(1, 0.62, 1),
      );
      tintGeometry(fold, 0.96);
      parts.push(fold);
    }
  }
  const geometry = mergeGeometries(parts, false);
  for (const part of parts) part.dispose();
  if (!geometry) throw new Error('failed to build connected first-person sleeve geometry');
  geometry.computeVertexNormals();
  const sleeve = new THREE.Mesh(geometry, material);
  sleeve.name = side < 0 ? 'vm:leftSleeveConnected' : 'vm:rightSleeveConnected';
  sleeve.userData.connectedToHand = true;
  markFirstPersonMesh(sleeve);
  return sleeve;
}

function buildArmSide(
  side: -1 | 1,
  pose: FirstPersonArmPose,
  materials: FirstPersonArmMaterials,
  fists: boolean,
  grip: HandGrip,
  supportContactInset: number,
  supportGripVariant: SupportGripVariant,
): { arm: THREE.Group; hand: THREE.Group } {
  // viewmodel の既存名/FIST_POSES互換を守る空制御ノード。表示物を持たせないことで
  // hand と別々に動かされても腕だけが浮く状態を構造的に排除する。
  const arm = new THREE.Group();
  arm.name = fists
    ? side < 0 ? 'vm:fistLArm' : 'vm:fistRArm'
    : side < 0 ? 'vm:leftArm' : 'vm:rightArm';
  arm.userData.poseControlOnly = true;
  applyPose(arm, pose.arm);

  const hand = new THREE.Group();
  hand.name = fists
    ? side < 0 ? 'vm:fistLHand' : 'vm:fistRHand'
    : side < 0 ? 'vm:leftHand' : 'vm:rightHand';
  applyPose(hand, pose.hand);
  hand.userData.connectedLimb = true;
  hand.userData.palmFacesWeapon = side < 0;
  hand.userData.handGrip = grip;
  hand.add(buildConnectedSleeve(side, materials.sleeve, pose, grip, supportGripVariant));
  const geometries = buildHandGeometries(
    side,
    grip,
    supportContactInset,
    supportGripVariant,
  );
  const handMeshes: Array<[HandMaterialFamily, THREE.MeshStandardMaterial]> = [
    ['glove', materials.glove],
    ['palm', materials.glovePalm],
    ['armor', materials.gloveArmor],
    ['stitch', materials.gloveStitch],
  ];
  for (const [family, material] of handMeshes) {
    const handMesh = new THREE.Mesh(geometries[family], material);
    handMesh.name = family === 'glove'
      ? side < 0 ? 'vm:leftGloveSkin' : 'vm:rightGloveSkin'
      : `vm:${side < 0 ? 'left' : 'right'}Hand:${family}`;
    markFirstPersonMesh(handMesh);
    hand.add(handMesh);
  }
  return { arm, hand };
}

/** 両腕を同時生成する。右手=グリップ、左手=ハンドガード支持が既定。 */
export function buildFirstPersonArms(
  materials: FirstPersonArmMaterials,
  options: FirstPersonArmsOptions,
): THREE.Group {
  const rig = new THREE.Group();
  rig.name = 'vm:firstPersonArms';
  rig.userData.firstPersonArmsRig = true;
  const right = buildArmSide(
    1,
    options.right,
    materials,
    options.fists === true,
    options.rightGrip ?? (options.fists === true ? 'power' : 'trigger'),
    0,
    'shared',
  );
  const left = buildArmSide(
    -1,
    options.left,
    materials,
    options.fists === true,
    options.leftGrip ?? (options.fists === true ? 'guard' : 'support'),
    options.supportContactInset ?? 0,
    options.supportGripVariant ?? 'shared',
  );
  rig.add(right.arm, right.hand, left.arm, left.hand);
  return rig;
}

/** ViewModel.dispose から呼ぶ。旧キャッシュにSkinnedMeshが残る場合も安全に解放する。 */
export function disposeFirstPersonArmSkeletons(root: THREE.Object3D): void {
  root.traverse((node) => {
    if (node instanceof THREE.SkinnedMesh) node.skeleton.dispose();
  });
}
