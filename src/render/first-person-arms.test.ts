import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { buildFirstPersonArms, disposeFirstPersonArmSkeletons } from './first-person-arms';

function materials(): {
  sleeve: THREE.MeshStandardMaterial;
  glove: THREE.MeshStandardMaterial;
  glovePalm: THREE.MeshStandardMaterial;
  gloveArmor: THREE.MeshStandardMaterial;
  gloveStitch: THREE.MeshStandardMaterial;
  skin: THREE.MeshStandardMaterial;
} {
  return {
    sleeve: new THREE.MeshStandardMaterial({ color: 0x30343a }),
    glove: new THREE.MeshStandardMaterial({ color: 0x111318 }),
    glovePalm: new THREE.MeshStandardMaterial({ color: 0x756957 }),
    gloveArmor: new THREE.MeshStandardMaterial({ color: 0x25292e }),
    gloveStitch: new THREE.MeshStandardMaterial({ color: 0xb88950 }),
    skin: new THREE.MeshStandardMaterial({ color: 0xb87958 }),
  };
}

function disposeRig(root: THREE.Object3D, mats: ReturnType<typeof materials>): void {
  disposeFirstPersonArmSkeletons(root);
  root.traverse((node) => {
    if (node instanceof THREE.Mesh) node.geometry.dispose();
  });
  for (const material of Object.values(mats)) material.dispose();
}

const options = {
  right: {
    arm: [0.03, -0.22, 0.3, 0.62, -0.1, 0] as const,
    hand: [0, -0.11, 0.11, 0.3, 0, 0] as const,
  },
  left: {
    arm: [-0.03, -0.13, -0.04, 0.5, 0.2, 0.12] as const,
    hand: [0, -0.05, -0.16, 0.2, 0, 0] as const,
  },
};

interface FingerDiagnostic {
  readonly name: 'pinky' | 'ring' | 'middle' | 'index';
  readonly triggerFinger: boolean;
  readonly joints: readonly (readonly [number, number, number])[];
  readonly idleJoints?: readonly (readonly [number, number, number])[];
  readonly exchangeJoints?: readonly (readonly [number, number, number])[];
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

function fingerDiagnostics(rig: THREE.Object3D, side: 'left' | 'right'): FingerDiagnostic[] {
  const glove = rig.getObjectByName(`vm:${side}GloveSkin`) as THREE.Mesh;
  return glove.geometry.userData.fingerDiagnostics as FingerDiagnostic[];
}

describe('first-person arms', () => {
  it('左右の手・手首・前腕を同じhand階層へ接続し、独立SkinnedMeshを生成しない', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    const skins: THREE.SkinnedMesh[] = [];
    rig.traverse((node) => {
      if (node instanceof THREE.SkinnedMesh) skins.push(node);
    });
    expect(skins).toHaveLength(0);
    expect(rig.getObjectByName('vm:leftHand')).toBeDefined();
    expect(rig.getObjectByName('vm:rightHand')).toBeDefined();
    expect(rig.getObjectByName('vm:leftGloveSkin')).toBeInstanceOf(THREE.Mesh);
    expect(rig.getObjectByName('vm:rightGloveSkin')).toBeInstanceOf(THREE.Mesh);
    expect(rig.getObjectByName('vm:rightHand:palm')).toBeInstanceOf(THREE.Mesh);
    expect(rig.getObjectByName('vm:rightHand:armor')).toBeInstanceOf(THREE.Mesh);
    expect(rig.getObjectByName('vm:rightHand:stitch')).toBeInstanceOf(THREE.Mesh);
    const leftHand = rig.getObjectByName('vm:leftHand');
    const rightHand = rig.getObjectByName('vm:rightHand');
    expect(leftHand?.getObjectByName('vm:leftSleeveConnected')).toBeInstanceOf(THREE.Mesh);
    expect(rightHand?.getObjectByName('vm:rightSleeveConnected')).toBeInstanceOf(THREE.Mesh);
    expect(rig.getObjectByName('vm:leftArm')?.children).toHaveLength(0);
    expect(rig.getObjectByName('vm:rightArm')?.children).toHaveLength(0);
    expect(rig.getObjectByName('vm:leftHand')?.userData.palmFacesWeapon).toBe(true);
    expect(rig.getObjectByName('vm:rightHand')?.userData.palmFacesWeapon).toBe(false);
    disposeRig(rig, mats);
  });

  it('左支持手の掌面を銃側へ返し、右射撃手の掌面は従来向きを保つ', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    const leftPalm = rig.getObjectByName('vm:leftHand:palm') as THREE.Mesh;
    const rightPalm = rig.getObjectByName('vm:rightHand:palm') as THREE.Mesh;
    leftPalm.geometry.computeBoundingBox();
    rightPalm.geometry.computeBoundingBox();
    expect(leftPalm.geometry.boundingBox!.getCenter(new THREE.Vector3()).y).toBeGreaterThan(0);
    expect(rightPalm.geometry.boundingBox!.getCenter(new THREE.Vector3()).y).toBeLessThan(0);
    expect(leftPalm.geometry.userData.palmFacesWeapon).toBe(true);
    expect(rightPalm.geometry.userData.palmFacesWeapon).toBeUndefined();
    disposeRig(rig, mats);
  });

  it('支持手の指は掌から連続するコンパクトな握りに収まり、棒状に飛び出さない', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    for (const side of ['left', 'right'] as const) {
      const glove = rig.getObjectByName(`vm:${side}GloveSkin`) as THREE.Mesh;
      const palm = rig.getObjectByName(`vm:${side}Hand:palm`) as THREE.Mesh;
      glove.geometry.computeBoundingBox();
      palm.geometry.computeBoundingBox();
      const gloveSize = glove.geometry.boundingBox!.getSize(new THREE.Vector3());
      const palmSize = palm.geometry.boundingBox!.getSize(new THREE.Vector3());
      // 5指+掌+手首の手形だけの範囲。袖は別メッシュなのでこの大きさに混ざらない。
      expect(gloveSize.x, side).toBeLessThan(0.12);
      expect(gloveSize.y, side).toBeLessThan(0.13);
      expect(gloveSize.z, side).toBeLessThan(0.22);
      expect(palmSize.x, side).toBeLessThan(0.12);
      expect(palmSize.y, side).toBeLessThan(0.13);
      expect(palmSize.z, side).toBeLessThan(0.16);
    }
    disposeRig(rig, mats);
  });

  it('4指は小指→薬指→中指→人差し指の人体比率で、共有関節の3節チェーンになる', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    for (const side of ['left', 'right'] as const) {
      const fingers = fingerDiagnostics(rig, side);
      expect(fingers.map((finger) => finger.name)).toEqual(['pinky', 'ring', 'middle', 'index']);
      expect(fingers).toHaveLength(4);
      for (const finger of fingers) {
        expect(finger.joints, `${side}:${finger.name}`).toHaveLength(4);
        expect(finger.radii[0], `${side}:${finger.name}`).toBeGreaterThan(finger.radii[1]);
        expect(finger.radii[1], `${side}:${finger.name}`).toBeGreaterThan(finger.radii[2]);
        expect(finger.tipRadius, `${side}:${finger.name}`).toBeLessThan(finger.radii[2] * 0.8);
        expect(finger.tipRadius, [side, finger.name].join(':')).toBeGreaterThan(
          side === 'left' ? 0.0028 : 0.0035,
        );
        for (let segment = 0; segment < 3; segment += 1) {
          const start = new THREE.Vector3(...finger.joints[segment]!);
          const end = new THREE.Vector3(...finger.joints[segment + 1]!);
          const length = start.distanceTo(end);
          // 支持手の短い小指末節だけは約7mm。旧11.5mm下限は熊手状の
          // 過長な指を強制していたため、人体比率を保つ実寸へ下げる。
          expect(length, `${side}:${finger.name}:${segment}`).toBeGreaterThan(
            side === 'left' ? 0.0065 : 0.009,
          );
          expect(length, `${side}:${finger.name}:${segment}`).toBeLessThan(0.04);
          expect([...finger.joints[segment]!, ...finger.joints[segment + 1]!]
            .every(Number.isFinite), `${side}:${finger.name}:${segment}:finite`).toBe(true);
        }
      }
      const totalLength = (name: FingerDiagnostic['name']) => {
        const finger = fingers.find((candidate) => candidate.name === name)!;
        return finger.joints.slice(0, 3).reduce((sum, joint, index) =>
          sum + new THREE.Vector3(...joint).distanceTo(
            new THREE.Vector3(...finger.joints[index + 1]!),
          ), 0);
      };
      expect(totalLength('pinky'), side).toBeLessThan(totalLength('index'));
      // 人差し指と薬指は個人差で逆転するため、4mm以内の近似比率を許容する。
      expect(Math.abs(totalLength('index') - totalLength('ring')), side).toBeLessThan(0.004);
      expect(totalLength('index'), side).toBeLessThan(totalLength('middle'));
      expect(totalLength('ring'), side).toBeLessThan(totalLength('middle'));
    }
    disposeRig(rig, mats);
  });

  it('指根は掌に食い込み、隣同士は融合せず、指先は外へ開かない', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    for (const side of ['left', 'right'] as const) {
      const fingers = fingerDiagnostics(rig, side);
      const glove = rig.getObjectByName(`vm:${side}GloveSkin`) as THREE.Mesh;
      const support = side === 'left'
        ? glove.geometry.userData.supportGrip as SupportGripDiagnostic
        : undefined;
      for (const finger of fingers) {
        const root = new THREE.Vector3(...finger.joints[0]!);
        const tip = new THREE.Vector3(...finger.joints[3]!);
        if (side === 'left') {
          // マガジン基準の支持手はlocal X/Zの絶対値ではなく、
          // 実掌中心からの接続距離で根元の食い込みを検査する。
          const palmCenter = new THREE.Vector3(...support!.palmCenter);
          expect(root.distanceTo(palmCenter), [side, finger.name, 'palm-root'].join(':'))
            .toBeLessThan(0.075);
          const lengths = finger.joints.slice(0, 3).map((joint, index) =>
            new THREE.Vector3(...joint).distanceTo(new THREE.Vector3(...finger.joints[index + 1]!)),
          );
          expect(lengths[0], `${side}:${finger.name}:proximal`).toBeGreaterThan(lengths[1]!);
          expect(lengths[1], `${side}:${finger.name}:middle`).toBeGreaterThan(lengths[2]!);
        } else {
          expect(Math.abs(root.x), [side, finger.name].join(':')).toBeLessThan(0.024);
          expect(root.z, `${side}:${finger.name}`).toBeGreaterThan(-0.05);
          expect(root.z, `${side}:${finger.name}`).toBeLessThan(-0.025);
          if (finger.name === 'pinky' || finger.name === 'index') {
            expect(Math.abs(tip.x), `${side}:${finger.name}`).toBeLessThan(Math.abs(root.x));
          }
        }
        if (!finger.triggerFinger) {
          // 近位節で前へ出た後、中節/末節は掌へ戻る=角にならない。
          expect(tip.z, `${side}:${finger.name}`).toBeGreaterThan(finger.joints[1]![2]);
          if (side === 'left') {
            // 支持指は先端でマガジン前縁へ戻る。3節の逓減は
            // 上の実長検査で保証し、座標軸に依存しない。
            expect(root.distanceTo(tip), `${side}:${finger.name}:closed-span`).toBeLessThan(0.065);
          } else {
            expect(Math.abs(tip.y), `${side}:${finger.name}:closed-y`)
              .toBeLessThan(Math.abs(finger.joints[2]![1]) + 0.005);
          }
        }
      }
      const orderedRoots = fingers.map((finger) => new THREE.Vector3(...finger.joints[0]!))
        .sort((a, b) => a.x - b.x);
      for (let index = 1; index < orderedRoots.length; index += 1) {
        const distance = orderedRoots[index]!.distanceTo(orderedRoots[index - 1]!);
        expect(distance, [side, 'root-gap', index].join(':')).toBeGreaterThan(
          // 支持手の近位節は掌の中で12mmピッチ。画面に出るDIP側の
          // 2–4mm実表面間隙は下のsupportGrip検査で別に保証する。
          side === 'left' ? 0.0115 : 0.0145,
        );
        expect(distance, [side, 'root-gap', index].join(':')).toBeLessThan(
          side === 'left' ? 0.0155 : 0.0155,
        );
      }
      expect(glove.geometry.userData.connectedFingerRoots).toBe(true);
    }
    disposeRig(rig, mats);
  });

  it('親指は支持手で銃側へ続き、射撃手では柄へ折り返す', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    for (const side of ['left', 'right'] as const) {
      const glove = rig.getObjectByName(`vm:${side}GloveSkin`) as THREE.Mesh;
      const joints = glove.geometry.userData.thumbJoints as Array<readonly [number, number, number]>;
      expect(joints).toHaveLength(3);
      const root = new THREE.Vector3(...joints[0]!);
      const middle = new THREE.Vector3(...joints[1]!);
      const tip = new THREE.Vector3(...joints[2]!);
      const grip = glove.geometry.userData.handGrip as string;
      expect(root.distanceTo(middle), side).toBeGreaterThan(grip === 'support' ? 0.0195 : 0.021);
      expect(middle.distanceTo(tip), side).toBeGreaterThan(grip === 'support' ? 0.009 : 0.019);
      if (grip === 'support') {
        // マガジン上縁へ沿わせる支持親指は、旧ホース状の24mm末節を
        // 9–15mmの短い末節へ変更したことを回帰検査する。
        expect(middle.distanceTo(tip), side).toBeLessThan(0.015);
      }
      if (grip === 'support') {
        // 親指はマガジン上縁で、4指の反対側へ対置する。
        const support = glove.geometry.userData.supportGrip as SupportGripDiagnostic;
        const fingerTipCenter = new THREE.Vector3(...support.fingerTipCenter);
        const anchor = new THREE.Vector3(...support.anchor);
        const palmInterior = new THREE.Vector3(...support.palmInteriorNormal);
        const back = new THREE.Vector3(...support.backNormal);
        expect(fingerTipCenter.clone().sub(anchor).dot(palmInterior), [side, 'four-finger-side'].join(':'))
          .toBeGreaterThan(0.025);
        expect(tip.clone().sub(anchor).dot(back), [side, 'opposed-thumb-side'].join(':'))
          .toBeGreaterThan(0.025);
      } else {
        expect(Math.abs(middle.x), side).toBeGreaterThan(Math.abs(root.x));
        expect(Math.abs(tip.x), side).toBeLessThan(Math.abs(middle.x));
      }
      if (grip !== 'support') {
        expect(Math.max(Math.abs(root.x), Math.abs(middle.x), Math.abs(tip.x)), side).toBeLessThan(0.05);
      }
      const fingers = fingerDiagnostics(rig, side);
      const nearestFingerJoint = Math.min(...fingers.flatMap((finger) =>
        finger.joints.slice(1).map((joint) => tip.distanceTo(new THREE.Vector3(...joint))),
      ));
      // 親指は人差し指に触れてもメッシ同士が食い込むほど近づけない。
      expect(nearestFingerJoint, side).toBeGreaterThan(0.0145);
    }
    disposeRig(rig, mats);
  });

  it('V7支持手は掌を小型化し、4指の表面間隔と親指対置を実形状で保証する', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    const glove = rig.getObjectByName('vm:leftGloveSkin') as THREE.Mesh;
    const palm = rig.getObjectByName('vm:leftHand:palm') as THREE.Mesh;
    const support = glove.geometry.userData.supportGrip as SupportGripDiagnostic;
    expect(glove.geometry.userData.anatomyVersion).toBe(7);
    expect(glove.geometry.userData.idleMorph).toBe(true);
    expect(glove.geometry.morphAttributes.position).toHaveLength(1);
    expect(support).toBeDefined();
    expect(support.adjacentSurfaceClearances).toHaveLength(3);
    for (const [index, clearance] of support.adjacentSurfaceClearances.entries()) {
      // 中心間距離ではなく、両指半径を差し引いた実表面の空隙。
      expect(clearance, ['web-gap', index].join(':')).toBeGreaterThan(0.002);
      expect(clearance, ['web-gap', index].join(':')).toBeLessThan(0.0041);
    }
    const fingerTipCenter = new THREE.Vector3(...support.fingerTipCenter);
    const thumbTip = new THREE.Vector3(...support.thumbTip);
    const anchor = new THREE.Vector3(...support.anchor);
    expect(anchor.distanceTo(fingerTipCenter)).toBeGreaterThan(0.03);
    expect(anchor.distanceTo(thumbTip)).toBeGreaterThan(0.03);
    expect(anchor.distanceTo(fingerTipCenter)).toBeLessThan(0.06);
    expect(anchor.distanceTo(thumbTip)).toBeLessThan(0.06);
    const palmInterior = new THREE.Vector3(...support.palmInteriorNormal).normalize();
    const back = new THREE.Vector3(...support.backNormal).normalize();
    const curl = new THREE.Vector3(...support.curlNormal).normalize();
    expect(palmInterior.dot(back)).toBeLessThan(-0.999);
    expect(Math.abs(curl.dot(palmInterior))).toBeLessThan(0.001);
    const palmCenter = new THREE.Vector3(...support.palmCenter);
    // Q14 corrects the inside-out Q13 basis: -RIGHT is the real weapon-facing
    // surface, 19mm from the grasp anchor into the compact palm.
    expect(palmCenter.clone().sub(anchor).dot(palmInterior)).toBeGreaterThan(0.017);
    glove.geometry.computeBoundingBox();
    palm.geometry.computeBoundingBox();
    const gloveSize = glove.geometry.boundingBox!.getSize(new THREE.Vector3());
    const palmSize = palm.geometry.boundingBox!.getSize(new THREE.Vector3());
    // V6の掌幅86mm／手厚64mmより15〜25%小さく、袖を含めず人体比率へ収まる。
    expect(palmSize.x).toBeLessThan(0.075);
    expect(gloveSize.y).toBeLessThan(0.105);
    disposeRig(rig, mats);
  });

  it('Kaede Q17は小型非対称掌と全材質同期モーフでr05の扇形残留を禁止する', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, {
      ...options,
      supportContactInset: 0.003,
      supportGripVariant: 'kaede-q17',
    });
    const leftHand = rig.getObjectByName('vm:leftHand')!;
    const glove = rig.getObjectByName('vm:leftGloveSkin') as THREE.Mesh;
    expect(glove.geometry.userData.anatomyVersion).toBe(10);
    const handMeshes = leftHand.children.filter((node): node is THREE.Mesh =>
      node instanceof THREE.Mesh && node.name.startsWith('vm:leftHand:'),
    );
    expect(handMeshes).toHaveLength(3);
    for (const mesh of [glove, ...handMeshes]) {
      expect(mesh.geometry.morphAttributes.position, mesh.name).toHaveLength(2);
      expect(mesh.geometry.morphAttributes.normal, mesh.name).toHaveLength(2);
      const base = mesh.geometry.getAttribute('position');
      const idle = mesh.geometry.morphAttributes.position![0]!;
      const exchange = mesh.geometry.morphAttributes.position![1]!;
      expect(base.count, mesh.name).toBe(idle.count);
      expect(base.count, mesh.name).toBe(exchange.count);
      for (const attribute of [
        base,
        idle,
        exchange,
        ...mesh.geometry.morphAttributes.normal!,
      ]) {
        for (let vertex = 0; vertex < attribute.count; vertex += 1) {
          expect(
            Number.isFinite(attribute.getX(vertex)) &&
            Number.isFinite(attribute.getY(vertex)) &&
            Number.isFinite(attribute.getZ(vertex)),
            `${mesh.name}:${attribute.name}:${vertex}`,
          ).toBe(true);
        }
      }
      if (mesh.geometry.userData.handMaterialFamily === 'armor') {
        let stationaryVertices = 0;
        let correctedVertices = 0;
        for (let vertex = 0; vertex < base.count; vertex += 1) {
          const stationary = [0, 1, 2].every(
            (axis) => exchange.getComponent(vertex, axis) === base.getComponent(vertex, axis),
          );
          if (stationary) stationaryVertices += 1;
          else correctedVertices += 1;
        }
        // The cuff stays byte-identical while the exchange-only dorsal pad is
        // buried into the trapezoid instead of remaining a raised paw island.
        expect(stationaryVertices).toBe(89);
        expect(correctedVertices).toBe(117);
      }
    }

    const fingers = fingerDiagnostics(rig, 'left');
    const support = glove.geometry.userData.supportGrip as SupportGripDiagnostic;
    const anchor = new THREE.Vector3(...support.anchor);
    const curl = new THREE.Vector3(...support.curlNormal).normalize();
    const tipDepth = Object.fromEntries(fingers.map((finger) => [
      finger.name,
      new THREE.Vector3(...finger.joints[3]!).sub(anchor).dot(curl),
    ])) as Record<FingerDiagnostic['name'], number>;
    // r03で近側に出るのは人差し指/中指だけ。薬指/小指は弾倉と
    // 掌のシルエットの奥へ11mm以上退避させ、4本の外付け棒を出さない。
    expect(tipDepth.middle - tipDepth.ring).toBeGreaterThanOrEqual(0.011);
    expect(tipDepth.index - tipDepth.pinky).toBeGreaterThanOrEqual(0.016);

    glove.geometry.computeBoundingBox();
    const size = glove.geometry.boundingBox!.getSize(new THREE.Vector3());
    // 指と手首を含む外形も過大にならない。掌ロフト自体は
    // 57x38x25.6mmで、Q15より各可視軸15–20%縮小されている。
    expect(size.x).toBeLessThan(0.115);
    expect(size.y).toBeLessThan(0.095);
    expect(size.z).toBeLessThan(0.125);
    disposeRig(rig, mats);
  });

  it('Kaede Q17qはidle/reloadを固定し、exchange掌を手首狭・knuckle広の直線台形へ変える', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, {
      ...options,
      supportContactInset: 0.003,
      supportGripVariant: 'kaede-q17',
    });
    const glove = rig.getObjectByName('vm:leftGloveSkin') as THREE.Mesh;
    const reload = glove.geometry.getAttribute('position');
    const idle = glove.geometry.morphAttributes.position![0]!;
    const exchange = glove.geometry.morphAttributes.position![1]!;
    expect(reload.count).toBe(1403);
    expect(glove.geometry.index?.count).toBe(6672);
    let reloadCoordinateSum = 0;
    let reloadCoordinateSquareSum = 0;
    let idleCoordinateSum = 0;
    let idleCoordinateSquareSum = 0;
    let exchangeCoordinateSum = 0;
    let exchangeCoordinateSquareSum = 0;
    for (let vertex = 0; vertex < reload.count; vertex += 1) {
      for (let axis = 0; axis < 3; axis += 1) {
        const coordinate = reload.getComponent(vertex, axis);
        reloadCoordinateSum += coordinate;
        reloadCoordinateSquareSum += coordinate * coordinate;
        const idleCoordinate = idle.getComponent(vertex, axis);
        idleCoordinateSum += idleCoordinate;
        idleCoordinateSquareSum += idleCoordinate * idleCoordinate;
        const exchangeCoordinate = exchange.getComponent(vertex, axis);
        exchangeCoordinateSum += exchangeCoordinate;
        exchangeCoordinateSquareSum += exchangeCoordinate * exchangeCoordinate;
      }
    }
    // Q17k/Q17l base/reload and Q17o idle target 0 are frozen. Q17q may alter
    // only exchange target 1, so all three fingerprints are explicit gates.
    expect(reloadCoordinateSum).toBeCloseTo(71.97898724766674, 8);
    expect(reloadCoordinateSquareSum).toBeCloseTo(7.757024541320733, 8);
    expect(idleCoordinateSum).toBeCloseTo(62.66659989682057, 8);
    expect(idleCoordinateSquareSum).toBeCloseTo(5.936065431811895, 8);
    expect(exchangeCoordinateSum).toBeCloseTo(72.29315680324021, 8);
    expect(exchangeCoordinateSquareSum).toBeCloseTo(7.987749670841053, 8);
    const ringSize = 12;
    const ringVector = (
      attribute: THREE.BufferAttribute | THREE.InterleavedBufferAttribute,
      ring: number,
      firstEdge: number,
      oppositeEdge: number,
    ) => new THREE.Vector3().fromBufferAttribute(attribute, ring * ringSize + firstEdge)
      .sub(new THREE.Vector3().fromBufferAttribute(
        attribute,
        ring * ringSize + oppositeEdge,
      ));
    const rightAxis = ringVector(reload, 0, 0, 6).normalize();
    const frontAxis = ringVector(reload, 0, 3, 9).normalize();
    const ringSpan = (
      attribute: THREE.BufferAttribute | THREE.InterleavedBufferAttribute,
      ring: number,
      firstEdge: number,
      oppositeEdge: number,
      axis: THREE.Vector3,
    ) => Math.abs(ringVector(attribute, ring, firstEdge, oppositeEdge).dot(axis));
    const ringCenter = (
      attribute: THREE.BufferAttribute | THREE.InterleavedBufferAttribute,
      ring: number,
    ) => new THREE.Vector3().fromBufferAttribute(attribute, ring * ringSize)
      .add(new THREE.Vector3().fromBufferAttribute(attribute, ring * ringSize + 6))
      .multiplyScalar(0.5);
    const rightShiftFromWrist = (
      attribute: THREE.BufferAttribute | THREE.InterleavedBufferAttribute,
      ring: number,
    ) => ringCenter(attribute, ring).sub(ringCenter(attribute, 0)).dot(rightAxis);

    expect(idle.count).toBe(reload.count);
    expect(exchange.count).toBe(reload.count);
    // The first five rings only receive the existing absolute idle translation.
    // Opposite-vertex distances remove translation and isolate hull radii.
    for (let ring = 0; ring < 5; ring += 1) {
      expect(ringSpan(idle, ring, 0, 6, rightAxis), `ring-${ring}:right`)
        .toBeCloseTo(ringSpan(reload, ring, 0, 6, rightAxis), 6);
      expect(ringSpan(idle, ring, 3, 9, frontAxis), `ring-${ring}:front`)
        .toBeCloseTo(ringSpan(reload, ring, 3, 9, frontAxis), 6);
    }
    // Base positions remain Q17h's authored reload hull.
    expect(ringSpan(reload, 6, 0, 6, rightAxis)).toBeCloseTo(0.0366, 6);
    expect(ringSpan(reload, 6, 3, 9, frontAxis)).toBeCloseTo(0.0190, 6);
    expect(ringSpan(reload, 7, 0, 6, rightAxis)).toBeCloseTo(0.0330, 6);
    expect(ringSpan(reload, 7, 3, 9, frontAxis)).toBeCloseTo(0.0144, 6);
    // Only the absolute idle morph receives Q17o's broad, shallow terminal.
    // Rings 5–7 close over 4.2mm and retain a broad shoulder.
    expect(ringSpan(idle, 5, 0, 6, rightAxis)).toBeCloseTo(0.0380, 6);
    expect(ringSpan(idle, 5, 3, 9, frontAxis)).toBeCloseTo(0.0210, 6);
    expect(ringSpan(idle, 6, 0, 6, rightAxis)).toBeCloseTo(0.0386, 6);
    expect(ringSpan(idle, 6, 3, 9, frontAxis)).toBeCloseTo(0.0188, 6);
    expect(ringSpan(idle, 7, 0, 6, rightAxis)).toBeCloseTo(0.0344, 6);
    expect(ringSpan(idle, 7, 3, 9, frontAxis)).toBeCloseTo(0.0156, 6);
    // Reload retains Q17h's exact ring centres. Idle draws the terminal away
    // from the weapon and below the thumb so a V valley can remain above web.
    expect(rightShiftFromWrist(reload, 6)).toBeCloseTo(0.0058, 6);
    expect(rightShiftFromWrist(reload, 7)).toBeCloseTo(0.0064, 6);
    expect(rightShiftFromWrist(idle, 6)).toBeCloseTo(-0.0055, 6);
    expect(rightShiftFromWrist(idle, 7)).toBeCloseTo(-0.0060, 6);
    expect(rightShiftFromWrist(reload, 6) - rightShiftFromWrist(idle, 6))
      .toBeCloseTo(0.0113, 6);
    expect(rightShiftFromWrist(reload, 7) - rightShiftFromWrist(idle, 7))
      .toBeCloseTo(0.0124, 6);
    // Vertex 97 is the unchanged-topology cap centre. It must sit on the
    // terminal ring axis; an 11mm side offset caused Q17n's visible apex.
    const terminalRingCenter = ringCenter(idle, 7);
    const terminalCapCenter = new THREE.Vector3().fromBufferAttribute(idle, 97);
    expect(terminalCapCenter.distanceTo(terminalRingCenter)).toBeLessThan(1e-7);
    // Morph 1 is exchange-only. Ring 0 stays byte-position compatible. The
    // following widths move from an 11mm wrist toward a 34.5mm knuckle while
    // ring 7 supplies only the rounded terminal closure.
    for (let ring = 0; ring < 1; ring += 1) {
      expect(ringSpan(exchange, ring, 0, 6, rightAxis), `exchange-${ring}:right`)
        .toBeCloseTo(ringSpan(reload, ring, 0, 6, rightAxis), 6);
      expect(ringSpan(exchange, ring, 3, 9, frontAxis), `exchange-${ring}:front`)
        .toBeCloseTo(ringSpan(reload, ring, 3, 9, frontAxis), 6);
      expect(rightShiftFromWrist(exchange, ring), `exchange-${ring}:center`)
        .toBeCloseTo(rightShiftFromWrist(reload, ring), 6);
    }
    const exchangeRightSpans = [
      0.0110,
      0.0160,
      0.0210,
      0.0205,
      0.0225,
      0.0280,
      0.0345,
      0.0320,
    ] as const;
    const exchangeFrontSpans = [
      0.0100,
      0.0136,
      0.0168,
      0.0188,
      0.0196,
      0.0184,
      0.0152,
      0.0088,
    ] as const;
    for (let ring = 0; ring < 8; ring += 1) {
      expect(ringSpan(exchange, ring, 0, 6, rightAxis), `q17q-ring-${ring}:right`)
        .toBeCloseTo(exchangeRightSpans[ring]!, 6);
      expect(ringSpan(exchange, ring, 3, 9, frontAxis), `q17q-ring-${ring}:front`)
        .toBeCloseTo(exchangeFrontSpans[ring]!, 6);
    }
    expect(exchangeRightSpans[6]).toBeGreaterThan(exchangeRightSpans[0] * 3);
    expect(exchangeRightSpans[6]).toBeGreaterThan(exchangeRightSpans[4] + 0.011);

    // Rings 1–6 follow one converging camera-side plane. Measure against the
    // actual authored UP spacing rather than assuming evenly spaced rings.
    const upAxis = new THREE.Vector3().crossVectors(frontAxis, rightAxis).normalize();
    const cameraSidePoints = [1, 2, 3, 4, 5, 6].map((ring) =>
      new THREE.Vector3().fromBufferAttribute(exchange, ring * ringSize + 6));
    const sideStart = cameraSidePoints[0]!;
    const sideEnd = cameraSidePoints.at(-1)!;
    const upStart = sideStart.dot(upAxis);
    const upEnd = sideEnd.dot(upAxis);
    const rightStart = sideStart.dot(rightAxis);
    const rightEnd = sideEnd.dot(rightAxis);
    for (const [index, point] of cameraSidePoints.entries()) {
      const alpha = (point.dot(upAxis) - upStart) / (upEnd - upStart);
      const lineRight = THREE.MathUtils.lerp(rightStart, rightEnd, alpha);
      expect(Math.abs(point.dot(rightAxis) - lineRight), `straight-side-${index}`)
        .toBeLessThan(0.0017);
    }

    // Ring 4 retreats 18mm from the short opposed thumb root. The low web
    // connects only the V apex, leaving the negative opening visibly unclosed.
    const exchangeThumbRoot = new THREE.Vector3(
      ...(glove.geometry.userData.exchangeThumbJoints[0] as readonly [number, number, number]),
    );
    const ringFourContactEdge = new THREE.Vector3().fromBufferAttribute(
      exchange,
      4 * ringSize,
    );
    expect(exchangeThumbRoot.sub(ringFourContactEdge).dot(rightAxis))
      .toBeCloseTo(0.0180, 6);
    expect(rightShiftFromWrist(exchange, 3)).toBeCloseTo(-0.00325, 6);
    expect(rightShiftFromWrist(exchange, 4)).toBeCloseTo(-0.00625, 6);
    expect(rightShiftFromWrist(exchange, 5)).toBeCloseTo(-0.0070, 6);
    expect(rightShiftFromWrist(exchange, 6)).toBeCloseTo(-0.00625, 6);
    expect(rightShiftFromWrist(exchange, 7)).toBeCloseTo(-0.0030, 6);
    disposeRig(rig, mats);
  });

  it('Kaede Q17oはindex/middleのroot/PIPを固定し、idle DIP neckとrounded capを各2.5mm離す', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, {
      ...options,
      supportContactInset: 0.003,
      supportGripVariant: 'kaede-q17',
    });
    const glove = rig.getObjectByName('vm:leftGloveSkin') as THREE.Mesh;
    const support = glove.geometry.userData.supportGrip as SupportGripDiagnostic;
    const anchor = new THREE.Vector3(...support.anchor);
    const front = new THREE.Vector3(...support.curlNormal).normalize();
    const right = new THREE.Vector3(...support.palmInteriorNormal).normalize();
    const up = new THREE.Vector3().crossVectors(front, right).normalize();
    const authored = (point: readonly [number, number, number]) => {
      const offset = new THREE.Vector3(...point).sub(anchor);
      return new THREE.Vector3(offset.dot(right), offset.dot(up), offset.dot(front));
    };
    const fingers = fingerDiagnostics(rig, 'left');
    const reloadJoints = Object.fromEntries(fingers.map((finger) => [
      finger.name,
      finger.joints.map(authored),
    ])) as Record<FingerDiagnostic['name'], THREE.Vector3[]>;
    const idle = Object.fromEntries(fingers.map((finger) => [
      finger.name,
      finger.idleJoints!.map(authored),
    ])) as Record<FingerDiagnostic['name'], THREE.Vector3[]>;

    const fixedReloadProfiles = {
      pinky: [[-0.039, -0.024, -0.026], [-0.043, -0.030, -0.025], [-0.038, -0.027, -0.024], [-0.02383, -0.024, -0.026]],
      ring: [[-0.037, -0.011, -0.025], [-0.041, -0.016, -0.022], [-0.036, -0.013, -0.020], [-0.02402, -0.011, -0.021]],
      middle: [[-0.034, 0.005, -0.022], [-0.024, 0.009, 0.012], [-0.020, 0.007, 0.036], [-0.02835, 0.005, 0.031]],
      index: [[-0.032, 0.018, -0.021], [-0.022, 0.021, 0.013], [-0.019, 0.018, 0.037], [-0.02781, 0.017, 0.031]],
    } as const;
    const fixedReloadRadii = {
      pinky: [[0.0057, 0.0049, 0.00445], 0.00305],
      ring: [[0.00585, 0.00505, 0.00455], 0.0032],
      middle: [[0.00595, 0.00515, 0.00465], 0.0033],
      index: [[0.0058, 0.005, 0.0045], 0.00315],
    } as const;
    for (const finger of fingers) {
      const profile = fixedReloadProfiles[finger.name];
      for (const [jointIndex, expected] of profile.entries()) {
        const actual = reloadJoints[finger.name][jointIndex]!;
        expect(actual.x, `reload-${finger.name}:${jointIndex}:right`).toBeCloseTo(expected[0], 4);
        expect(actual.y, `reload-${finger.name}:${jointIndex}:up`).toBeCloseTo(expected[1], 4);
        expect(actual.z, `reload-${finger.name}:${jointIndex}:front`).toBeCloseTo(expected[2], 4);
      }
      expect(finger.radii, `reload-${finger.name}:radii`)
        .toEqual(fixedReloadRadii[finger.name][0]);
      expect(finger.tipRadius, `reload-${finger.name}:tip-radius`)
        .toBe(fixedReloadRadii[finger.name][1]);
    }

    // Pinky/ring and the index/middle roots/PIPs are the exact Q17j profiles.
    const fixedProfiles = {
      pinky: [[-0.030, -0.021, -0.023], [-0.031, -0.022, -0.017], [-0.029, -0.022, -0.013], [-0.027, -0.021, -0.011]],
      ring: [[-0.029, -0.009, -0.022], [-0.031, -0.010, -0.016], [-0.028, -0.009, -0.012], [-0.026, -0.009, -0.009]],
      middle: [[-0.028, 0.005, -0.022], [-0.030, 0.006, -0.015], [-0.027, 0.0075, -0.011], [-0.025, 0.0075, -0.007]],
      index: [[-0.027, 0.018, -0.021], [-0.029, 0.019, -0.014], [-0.026, 0.0255, -0.006], [-0.024, 0.0245, -0.002]],
    } as const;
    for (const [name, profile] of Object.entries(fixedProfiles)) {
      for (const [jointIndex, expected] of profile.entries()) {
        const actual = idle[name as FingerDiagnostic['name']][jointIndex]!;
        expect(actual.x, `${name}:${jointIndex}:right`).toBeCloseTo(expected[0], 4);
        expect(actual.y, `${name}:${jointIndex}:up`).toBeCloseTo(expected[1], 4);
        expect(actual.z, `${name}:${jointIndex}:front`).toBeCloseTo(expected[2], 4);
      }
    }

    // Relative to Q17n, only the two DIP necks and terminal centres separate;
    // roots/PIPs above remain exact. This is the authored-space 1440p gap fix.
    expect(idle.index[2]!.y - idle.middle[2]!.y).toBeCloseTo(0.0180, 6);
    expect(idle.index[3]!.y - idle.middle[3]!.y).toBeCloseTo(0.0170, 6);
    expect((0.0100 - idle.middle[2]!.y) * 1000).toBeCloseTo(2.5, 6);
    expect((idle.index[2]!.y - 0.0230) * 1000).toBeCloseTo(2.5, 6);
    expect((0.0100 - idle.middle[3]!.y) * 1000).toBeCloseTo(2.5, 6);
    expect((idle.index[3]!.y - 0.0220) * 1000).toBeCloseTo(2.5, 6);
    expect(idle.index[2]!.z - idle.middle[2]!.z).toBeCloseTo(0.005, 5);
    expect(idle.index[3]!.z - idle.middle[3]!.z).toBeCloseTo(0.005, 5);
    const middle = fingers.find((finger) => finger.name === 'middle')!;
    const index = fingers.find((finger) => finger.name === 'index')!;
    expect(middle.tipRadius).toBe(0.0033);
    expect(index.tipRadius).toBe(0.00315);
    expect(middle.idleRadii).toEqual([0.00595, 0.00515, 0.00255]);
    expect(index.idleRadii).toEqual([0.0058, 0.005, 0.00245]);
    expect(middle.idleRadii![0]).toBe(middle.radii[0]);
    expect(middle.idleRadii![1]).toBe(middle.radii[1]);
    expect(index.idleRadii![0]).toBe(index.radii[0]);
    expect(index.idleRadii![1]).toBe(index.radii[1]);
    expect(middle.idleRadii![2]).toBeLessThan(middle.radii[2] - 0.0020);
    expect(index.idleRadii![2]).toBeLessThan(index.radii[2] - 0.0020);
    expect(middle.idleTerminalNeckRadius).toBe(0.00235);
    expect(index.idleTerminalNeckRadius).toBe(0.00225);
    expect(middle.idleTipRadius).toBe(0.00405);
    expect(index.idleTipRadius).toBe(0.00395);
    expect(middle.idleTipRadius!).toBeGreaterThan(middle.idleTerminalNeckRadius! + 0.0016);
    expect(index.idleTipRadius!).toBeGreaterThan(index.idleTerminalNeckRadius! + 0.0016);
    expect(middle.idleTipHorizontalScale).toBe(0.72);
    expect(index.idleTipHorizontalScale).toBe(0.72);
    expect(middle.idleTipDepthScale).toBe(1.20);
    expect(index.idleTipDepthScale).toBe(1.20);
    expect(middle.idleTipLongitudinalScale).toBe(0.86);
    expect(index.idleTipLongitudinalScale).toBe(0.86);
    expect(middle.idleTerminalFacetCount).toBe(12);
    expect(index.idleTerminalFacetCount).toBe(12);
    const idleTipSurfaceGap = idle.middle[3]!.distanceTo(idle.index[3]!)
      - middle.idleTipRadius! * middle.idleTipHorizontalScale!
      - index.idleTipRadius! * index.idleTipHorizontalScale!;
    expect(idleTipSurfaceGap).toBeGreaterThan(0.0119);
    expect(idleTipSurfaceGap).toBeLessThan(0.0123);

    // Idle remains a same-count absolute morph; reload geometry is untouched.
    const reload = glove.geometry.getAttribute('position');
    const idleMorph = glove.geometry.morphAttributes.position![0]!;
    expect(idleMorph.count).toBe(reload.count);
    disposeRig(rig, mats);
  });

  it('Kaede exchange morphはindex/middleだけを人体的に曲げ、接触tipsとpinky/ringを固定する', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, {
      ...options,
      supportContactInset: 0.003,
      supportGripVariant: 'kaede-q17',
    });
    const glove = rig.getObjectByName('vm:leftGloveSkin') as THREE.Mesh;
    const support = glove.geometry.userData.supportGrip as SupportGripDiagnostic;
    const anchor = new THREE.Vector3(...support.anchor);
    const front = new THREE.Vector3(...support.curlNormal).normalize();
    const right = new THREE.Vector3(...support.palmInteriorNormal).normalize();
    const up = new THREE.Vector3().crossVectors(front, right).normalize();
    const authored = (point: readonly [number, number, number]) => {
      const offset = new THREE.Vector3(...point).sub(anchor);
      return new THREE.Vector3(offset.dot(right), offset.dot(up), offset.dot(front));
    };
    const fingers = fingerDiagnostics(rig, 'left');
    const expected = {
      middle: [[-0.036, 0.005, -0.022], [-0.034, 0.008, 0.006], [-0.030, 0.007, 0.025]],
      index: [[-0.034, 0.018, -0.021], [-0.033, 0.021, 0.006], [-0.029, 0.019, 0.025]],
    } as const;
    for (const finger of fingers) {
      const reload = finger.joints.map(authored);
      const exchange = finger.exchangeJoints!.map(authored);
      if (finger.name === 'pinky' || finger.name === 'ring') {
        for (let joint = 0; joint < 4; joint += 1) {
          expect(exchange[joint]!.distanceTo(reload[joint]!), `${finger.name}:${joint}`)
            .toBeLessThan(1e-7);
        }
        continue;
      }
      for (let joint = 0; joint < 3; joint += 1) {
        for (let axis = 0; axis < 3; axis += 1) {
          expect(exchange[joint]!.getComponent(axis), `${finger.name}:${joint}:${axis}`)
            .toBeCloseTo(expected[finger.name][joint]![axis]!, 4);
        }
      }
      // Contact is authored by the frozen reload fingertip, not the correction.
      expect(exchange[3]!.distanceTo(reload[3]!)).toBeLessThan(1e-7);
    }
    disposeRig(rig, mats);
  });

  it('Kaede Q17qはreload/idle親指を固定し、exchangeだけ短い2節と開いたVを作る', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, {
      ...options,
      supportContactInset: 0.003,
      supportGripVariant: 'kaede-q17',
    });
    const glove = rig.getObjectByName('vm:leftGloveSkin') as THREE.Mesh;
    const support = glove.geometry.userData.supportGrip as SupportGripDiagnostic;
    const anchor = new THREE.Vector3(...support.anchor);
    const front = new THREE.Vector3(...support.curlNormal).normalize();
    const right = new THREE.Vector3(...support.palmInteriorNormal).normalize();
    const up = new THREE.Vector3().crossVectors(front, right).normalize();
    const authored = (point: readonly [number, number, number]) => {
      const offset = new THREE.Vector3(...point).sub(anchor);
      return new THREE.Vector3(offset.dot(right), offset.dot(up), offset.dot(front));
    };
    const reload = (glove.geometry.userData.thumbJoints as Array<readonly [number, number, number]>)
      .map(authored);
    const idle = (glove.geometry.userData.idleThumbJoints as Array<readonly [number, number, number]>)
      .map(authored);
    const exchange = (glove.geometry.userData.exchangeThumbJoints as Array<readonly [number, number, number]>)
      .map(authored);
    const webStart = authored(glove.geometry.userData.idleThumbWebStart as readonly [number, number, number]);
    const exchangeWebStart = authored(
      glove.geometry.userData.exchangeThumbWebStart as readonly [number, number, number],
    );
    const expectedReload = [
      [-0.017, 0.027, -0.006],
      [0.006, 0.034, 0.014],
      [0.029, 0.026, 0.030],
    ] as const;
    const expectedIdle = [
      [-0.002, 0.010, -0.006],
      [0.004, 0.020, -0.001],
      [-0.024, 0.0285, 0.0005],
    ] as const;
    const expectedExchange = [
      [-0.018, 0.025, 0.012],
      [-0.023, 0.036, 0.022],
      [-0.012, 0.032, 0.021],
    ] as const;
    for (const [jointIndex, expected] of expectedReload.entries()) {
      for (const [axis, value] of expected.entries()) {
        expect(reload[jointIndex]!.getComponent(axis), `reload-thumb-${jointIndex}:${axis}`)
          .toBeCloseTo(value, 4);
      }
    }
    for (const [jointIndex, expected] of expectedIdle.entries()) {
      for (const [axis, value] of expected.entries()) {
        expect(idle[jointIndex]!.getComponent(axis), `idle-thumb-${jointIndex}:${axis}`)
          .toBeCloseTo(value, 4);
      }
    }
    for (const [jointIndex, expected] of expectedExchange.entries()) {
      for (const [axis, value] of expected.entries()) {
        expect(exchange[jointIndex]!.getComponent(axis), `exchange-thumb-${jointIndex}:${axis}`)
          .toBeCloseTo(value, 4);
      }
    }
    expect(webStart.x).toBeCloseTo(-0.0285, 5);
    expect(webStart.y).toBeCloseTo(0.0095, 5);
    expect(webStart.z).toBeCloseTo(-0.0105, 5);
    expect(exchangeWebStart.x).toBeCloseTo(-0.034, 5);
    expect(exchangeWebStart.y).toBeCloseTo(0.014, 5);
    expect(exchangeWebStart.z).toBeCloseTo(0.008, 5);
    const proximalLength = exchange[0]!.distanceTo(exchange[1]!);
    const distalLength = exchange[1]!.distanceTo(exchange[2]!);
    expect(proximalLength).toBeGreaterThan(0.014);
    expect(proximalLength).toBeLessThan(0.017);
    expect(distalLength).toBeGreaterThan(0.010);
    expect(distalLength).toBeLessThan(0.013);
    expect(proximalLength + distalLength).toBeLessThan(0.030);
    expect(proximalLength + distalLength)
      .toBeLessThan(reload[0]!.distanceTo(reload[1]!) + reload[1]!.distanceTo(reload[2]!) - 0.025);
    // The index DIP and short opposed thumb leave a real surface gap. The
    // low 3mm web touches only the root/apex, so the V cannot become a loop.
    const index = fingerDiagnostics(rig, 'left').find((finger) => finger.name === 'index')!;
    const indexExchange = index.exchangeJoints!.map(authored);
    const exchangeThumbRadii = glove.geometry.userData.exchangeThumbRadii as readonly number[];
    const thumbIndexSurfaceGap = exchange[1]!.distanceTo(indexExchange[2]!)
      - exchangeThumbRadii[1]!
      - index.radii[2];
    expect(thumbIndexSurfaceGap).toBeGreaterThan(0.008);
    expect(glove.geometry.userData.exchangeThumbRadii).toEqual([0.0055, 0.0047, 0.0038]);
    expect(glove.geometry.userData.exchangeThumbWebRadius).toBe(0.0030);
    expect(glove.geometry.userData.exchangeThumbWebRadius)
      .toBeLessThan(exchangeThumbRadii[0]! - 0.002);
    expect(webStart.distanceTo(idle[0]!)).toBeLessThan(0.03);
    expect(glove.geometry.userData.idleThumbRadii).toEqual([0.0048, 0.0044, 0.0040]);
    expect(glove.geometry.userData.idleThumbWebRadius).toBe(0.0030);
    expect(glove.geometry.userData.idleThumbWebRadius)
      .toBeLessThan(glove.geometry.userData.idleThumbRadii[0] - 0.0015);
    disposeRig(rig, mats);
  });

  it('クナイ右手は全4指を柄へ握るpowerグリップ、左手はガード握りになる', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, { ...options, fists: true });
    const rightHand = rig.getObjectByName('vm:fistRHand');
    const leftHand = rig.getObjectByName('vm:fistLHand');
    expect(rightHand?.userData.handGrip).toBe('power');
    expect(leftHand?.userData.handGrip).toBe('guard');
    expect(fingerDiagnostics(rig, 'right').every((finger) => !finger.triggerFinger)).toBe(true);
    expect(fingerDiagnostics(rig, 'left').every((finger) => !finger.triggerFinger)).toBe(true);
    for (const side of ['left', 'right'] as const) {
      const fingers = fingerDiagnostics(rig, side);
      for (const finger of fingers) {
        const pip = new THREE.Vector3(...finger.joints[2]!);
        const tip = new THREE.Vector3(...finger.joints[3]!);
        expect(Math.abs(tip.y), `${side}:${finger.name}:fist-closed-y`)
          .toBeLessThan(Math.abs(pip.y) + 0.005);
        expect(tip.z, `${side}:${finger.name}:dip-fold`).toBeGreaterThan(pip.z);
      }
      const glove = rig.getObjectByName(`vm:${side}GloveSkin`) as THREE.Mesh;
      const thumb = (glove.geometry.userData.thumbJoints as Array<readonly [number, number, number]>)
        .map((joint) => new THREE.Vector3(...joint));
      const nearestFingerJoint = Math.min(...fingers.flatMap((finger) =>
        finger.joints.slice(1).map((joint) => thumb[2]!.distanceTo(new THREE.Vector3(...joint))),
      ));
      expect(nearestFingerJoint, `${side}:fist-thumb-clearance`).toBeGreaterThan(0.0145);
    }
    disposeRig(rig, mats);
  });

  it('旧来の直方体腕を生成せず、軽量な連続袖と立体指を使う', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    let boxes = 0;
    let vertices = 0;
    rig.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return;
      if (node.geometry instanceof THREE.BoxGeometry) boxes += 1;
      vertices += node.geometry.getAttribute('position').count;
    });
    expect(boxes).toBe(0);
    expect(vertices).toBeGreaterThan(1_500);
    expect(vertices).toBeLessThan(8_000);
    disposeRig(rig, mats);
  });

  it('片腕は袖1DC+手袋4DCに固定し、袖は必ずhandの子にある', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    for (const side of ['left', 'right'] as const) {
      const hand = rig.getObjectByName(`vm:${side}Hand`);
      expect(hand).toBeDefined();
      const meshes: THREE.Mesh[] = [];
      hand!.traverse((node) => {
        if (node instanceof THREE.Mesh) meshes.push(node);
      });
      expect(meshes).toHaveLength(5);
      expect(meshes.filter((mesh) => mesh.userData.connectedToHand === true)).toHaveLength(1);
    }
    disposeRig(rig, mats);
  });

  it('武器別armアンカーへ袖の肘端を戻し、手首回転だけで腕方向を決めない', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, options);
    rig.updateWorldMatrix(true, true);
    for (const side of ['left', 'right'] as const) {
      const sleeve = rig.getObjectByName(`vm:${side}SleeveConnected`) as THREE.Mesh;
      const arm = options[side].arm;
      const anchor = new THREE.Vector3(arm[0], arm[1], arm[2]);
      const position = sleeve.geometry.getAttribute('position') as THREE.BufferAttribute;
      let nearest = Number.POSITIVE_INFINITY;
      for (let i = 0; i < position.count; i += 1) {
        const point = new THREE.Vector3(position.getX(i), position.getY(i), position.getZ(i))
          .applyMatrix4(sleeve.matrixWorld);
        nearest = Math.min(nearest, point.distanceTo(anchor));
      }
      expect(nearest, side).toBeLessThan(0.065);
    }
    disposeRig(rig, mats);
  });

  it('クナイ用の既存FIST_POSESノード名を維持する', () => {
    const mats = materials();
    const rig = buildFirstPersonArms(mats, { ...options, fists: true });
    for (const name of ['vm:fistRArm', 'vm:fistRHand', 'vm:fistLArm', 'vm:fistLHand']) {
      expect(rig.getObjectByName(name), name).toBeDefined();
    }
    disposeRig(rig, mats);
  });
});
