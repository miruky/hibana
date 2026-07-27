import RAPIER from '@dimforge/rapier3d-compat';
import * as THREE from 'three';
import { beforeAll, describe, expect, it } from 'vitest';
import { Bot, DIFFICULTY, type EnemyVisualState } from './bot';

beforeAll(async () => {
  await RAPIER.init();
});

function makeBot(scale = 1): { world: RAPIER.World; bot: Bot } {
  const world = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
  const floor = world.createRigidBody(RAPIER.RigidBodyDesc.fixed());
  world.createCollider(
    RAPIER.ColliderDesc.cuboid(20, 0.5, 20).setTranslation(0, -0.5, 0),
    floor,
  );
  const bot = new Bot(
    world,
    'visual-test',
    new THREE.Vector3(),
    0x884433,
    { ...DIFFICULTY.normal, scale },
  );
  world.step();
  return { world, bot };
}

function snapshot(bot: Bot): EnemyVisualState {
  const result: EnemyVisualState = {
    alive: true,
    visible: true,
    aiState: 'patrol',
    speedMps: 0,
    shotSerial: 0,
    reloadSerial: 0,
    hitSerial: 0,
    hitFromBack: false,
    dying01: 0,
    killcamReplay: false,
    killcamDeath01: 0,
  };
  bot.getEnemyVisualState(result);
  return result;
}

describe('Bot external Blender soldier display contract', () => {
  it('keeps procedural, external and crowd paths mutually exclusive and fail-open', () => {
    const { bot } = makeBot();
    const internal = bot as unknown as { rig: THREE.Group };
    const external = new THREE.Group();

    expect(internal.rig.visible).toBe(true);
    bot.setExternalEnemyVisual(external);
    expect(external.parent).toBe(bot.group);
    expect(external.visible).toBe(true);
    expect(internal.rig.visible).toBe(false);

    bot.setCrowdSlot(4);
    expect(external.visible).toBe(false);
    expect(internal.rig.visible).toBe(false);

    bot.setCrowdSlot(-1);
    expect(external.visible).toBe(true);
    expect(internal.rig.visible).toBe(false);

    bot.setExternalEnemyVisual(null);
    expect(external.parent).toBeNull();
    expect(internal.rig.visible).toBe(true);
  });

  it('converts the collider-center origin to GLB boot-floor Y even when scaled', () => {
    expect(makeBot().bot.enemyVisualFloorOffsetY).toBeCloseTo(-0.8, 8);
    expect(makeBot(1.15).bot.enemyVisualFloorOffsetY).toBeCloseTo(-0.8 / 1.15, 8);
  });

  it('delegates killcam death to the GLB clip without applying a second group fall', () => {
    const { bot } = makeBot();
    bot.setExternalEnemyVisual(new THREE.Group());
    bot.fkApplyLivePose(2, 0.8, -3, 0.4);
    bot.fkApplyDeathPose(0.65);

    const state = snapshot(bot);
    expect(state.killcamReplay).toBe(true);
    expect(state.killcamDeath01).toBeCloseTo(0.65);
    expect(bot.group.rotation.x).toBe(0);
    expect(bot.group.rotation.z).toBe(0);
  });

  it('emits monotonic hit state and preserves front/back direction for authored reactions', () => {
    const { bot } = makeBot();
    bot.fkApplyLivePose(0, 0.8, 0, 0);
    bot.takeDamage(1, new THREE.Vector3(0, 0, 1));
    const back = snapshot(bot);
    expect(back.hitSerial).toBe(1);
    expect(back.hitFromBack).toBe(true);

    bot.takeDamage(1, new THREE.Vector3(0, 0, -1));
    const front = snapshot(bot);
    expect(front.hitSerial).toBe(2);
    expect(front.hitFromBack).toBe(false);
  });
});
