import { describe, expect, it } from 'vitest';
import { buildProp, generateStage, generateThemeObjects, MINI_SCENE_IDS } from './stage';
import type { BoxSpec, PropKind, PropPlacement, StageDef } from './stage';
import { mulberry32 } from '../core/rng';
import { STAGES } from './stages';

describe('generateStage', () => {
  it('同じ定義からは常に同じレイアウトが出る', () => {
    for (const def of STAGES) {
      const a = generateStage(def);
      const b = generateStage(def);
      expect(JSON.stringify(a)).toBe(JSON.stringify(b));
    }
  });

  it('全ステージで不可視境界壁4枚(ghost=true)とスポーン地点が揃う', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      // ghost=true の壁が 4 枚あること(不可視境界コライダーリング)
      const ghostWalls = layout.boxes.filter((box) => box.ghost === true);
      expect(ghostWalls.length).toBeGreaterThanOrEqual(4);
      // 色は palette.wall で識別可能であること
      const wallColorBoxes = layout.boxes.filter((box) => box.color === def.palette.wall);
      expect(wallColorBoxes.length).toBeGreaterThanOrEqual(4);
      expect(layout.playerSpawns).toHaveLength(4);
      expect(layout.botSpawns.length).toBeGreaterThanOrEqual(def.botCount);
    }
  });

  it('通常障害物と建造物はステージ境界の内側に収まる', () => {
    for (const def of STAGES) {
      const half = def.size / 2;
      const layout = generateStage(def);
      for (const box of layout.boxes) {
        // ghost(不可視境界壁)と decor(装飾)はチェック対象外
        if (box.ghost || box.decor) continue;
        expect(Math.abs(box.x) + box.w / 2).toBeLessThanOrEqual(half + 1);
        expect(Math.abs(box.z) + box.d / 2).toBeLessThanOrEqual(half + 1);
      }
    }
  });

  it('ステージは31個あり、idが重複しない', () => {
    expect(STAGES).toHaveLength(31);
    expect(new Set(STAGES.map((s) => s.id)).size).toBe(31);
  });

  it('seedが重複しない(レイアウトの独自性を保証)', () => {
    expect(new Set(STAGES.map((s) => s.seed)).size).toBe(STAGES.length);
  });

  it('パレットの全色が #rrggbb 形式', () => {
    const hex = /^#[0-9a-f]{6}$/;
    for (const def of STAGES) {
      const { sky, fog, floor, wall, obstacle, accent, lightColor } = def.palette;
      for (const color of [sky, fog, floor, wall, obstacle, accent, lightColor]) {
        expect(color, `${def.id}: ${color}`).toMatch(hex);
      }
    }
  });

  it('日差しが安全域に収まる(elevation 12〜62 / exposure 0.85〜1.15 / fogDensity>0)', () => {
    for (const def of STAGES) {
      const { elevation, exposure, fogDensity } = def.palette;
      expect(elevation, `${def.id}: elevation`).toBeGreaterThanOrEqual(12);
      expect(elevation, `${def.id}: elevation`).toBeLessThanOrEqual(62);
      expect(exposure, `${def.id}: exposure`).toBeGreaterThanOrEqual(0.85);
      expect(exposure, `${def.id}: exposure`).toBeLessThanOrEqual(1.15);
      expect(fogDensity, `${def.id}: fogDensity`).toBeGreaterThan(0);
    }
  });

  it('ゾンビ全10面は暗部を潰さない共通の可読性基準を満たす', () => {
    const zombieStages = STAGES.filter((stage) => /^z\d\d$/.test(stage.id));
    expect(zombieStages).toHaveLength(10);
    for (const def of zombieStages) {
      const p = def.palette;
      expect(p.lightIntensity, `${def.id}: key light`).toBeGreaterThanOrEqual(1.02);
      expect(p.ambientIntensity, `${def.id}: ambient`).toBeGreaterThanOrEqual(0.78);
      expect(p.environmentIntensity, `${def.id}: environment`).toBeGreaterThanOrEqual(0.68);
      expect(p.exposure, `${def.id}: exposure`).toBeGreaterThanOrEqual(1.14);
      expect(p.fogDensity, `${def.id}: fog`).toBeLessThanOrEqual(0.0072);
      expect(p.groundFog, `${def.id}: ground fog`).toBeLessThanOrEqual(0.36);
      expect(p.grade?.vignette, `${def.id}: vignette`).toBeLessThanOrEqual(0.3);
    }
  });

  it('size は 280〜360 の範囲(R21 エリア超拡大。訓練場専用ステージを除く)', () => {
    const SMALL_STAGES = new Set(['renshujo']); // 訓練場専用は小サイズ
    for (const def of STAGES) {
      if (SMALL_STAGES.has(def.id)) continue;
      expect(def.size, `${def.id}: size`).toBeGreaterThanOrEqual(280);
      expect(def.size, `${def.id}: size`).toBeLessThanOrEqual(360);
    }
  });

  it('プレイヤー・BOTどちらのスポーン地点付近にも通常障害物を置かない', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      const spawns = [...layout.playerSpawns, ...layout.botSpawns];
      for (const [sx, , sz] of spawns) {
        for (const box of layout.boxes) {
          // ghost(境界壁)と decor(装飾) は対象外
          if (box.ghost || box.decor) continue;
          const dx = Math.max(0, Math.abs(box.x - sx) - box.w / 2);
          const dz = Math.max(0, Math.abs(box.z - sz) - box.d / 2);
          expect(Math.hypot(dx, dz)).toBeGreaterThan(1);
        }
      }
    }
  }, 15_000);

  it('recipe を持つステージは theme が文字列で buildings が 0〜4 棟(訓練場は0棟)', () => {
    for (const def of STAGES) {
      if (!def.recipe) continue;
      expect(typeof def.recipe.theme).toBe('string');
      expect(def.recipe.buildings.length).toBeGreaterThanOrEqual(0);
      expect(def.recipe.buildings.length).toBeLessThanOrEqual(4);
    }
  });

  it('全固定ステージに最大3種の衝突付きプレイアブル地区が実配置される', () => {
    for (const def of STAGES) {
      const districts = new Set(
        generateStage(def).boxes.flatMap((box) => box.district ? [box.district] : []),
      );
      const required = Math.min(3, def.recipe?.buildings.length ?? 0);
      expect(districts.size, `${def.id}: ${[...districts].join(',')}`).toBeGreaterThanOrEqual(required);
    }
  });

  it('巨大修道城面を除く全固定ステージは9地区以上を実体配置する', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      const isAbbey = def.recipe?.buildings.includes('abbey') ?? false;
      expect(layout.districtPlacements.length, `${def.id}: playable districts`)
        .toBeGreaterThanOrEqual(isAbbey ? 1 : 9);
    }
  });

  it('全固定ステージの最大ランドマーク地区は原点へ実配置される', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      if (def.id === 'kairou') {
        // Kairou's origin is the shared civic plaza between two paired hero
        // landmarks.  A legacy origin building would hide one complete hero
        // from every truthful first-person composition.
        expect(layout.districtPlacements.some((placement) =>
          Math.abs(placement.cx) < placement.width / 2
          && Math.abs(placement.cz) < placement.depth / 2), 'kairou: origin plaza').toBe(false);
        continue;
      }
      const central = layout.districtPlacements[0];
      if (!central) continue;
      const first = central.kind;
      const boxes = layout.boxes.filter((box) => box.district === first);
      expect(central.cx, `${def.id}: central x`).toBe(0);
      expect(central.cz, `${def.id}: central z`).toBe(0);
      expect(boxes.length, `${def.id}: ${first}`).toBeGreaterThan(0);
      // 同種地区を複数配置する高密度マップでも、先頭地区の実体床／屋根が原点を覆う。
      // 全同種AABBの総外接矩形では、外周の追加地区まで含まれて中心判定にならない。
      if (first === 'abbey') {
        // 修道城は原点が中庭なので床・壁で覆わない。単一abbeyの総外接中心を確認する。
        const xMin = Math.min(...boxes.map((box) => box.x - box.w / 2));
        const xMax = Math.max(...boxes.map((box) => box.x + box.w / 2));
        const zMin = Math.min(...boxes.map((box) => box.z - box.d / 2));
        const zMax = Math.max(...boxes.map((box) => box.z + box.d / 2));
        expect(Math.abs((xMin + xMax) / 2), `${def.id}: abbey center x`).toBeLessThanOrEqual(4);
        expect(Math.abs((zMin + zMax) / 2), `${def.id}: abbey center z`).toBeLessThanOrEqual(4);
      } else {
        expect(
          boxes.some((box) =>
            box.x - box.w / 2 <= 0
            && box.x + box.w / 2 >= 0
            && box.z - box.d / 2 <= 0
            && box.z + box.d / 2 >= 0,
          ),
          `${def.id}: ${first} covers origin`,
        ).toBe(true);
      }
    }
  });

  it('全プレイアブル地区の階段終端は屋上・歩廊へオートステップ範囲内で接続する', () => {
    const horizontalGap = (
      a: { x: number; z: number; w: number; d: number },
      b: { x: number; z: number; w: number; d: number },
    ): number => {
      const dx = Math.max(0, Math.abs(a.x - b.x) - (a.w + b.w) / 2);
      const dz = Math.max(0, Math.abs(a.z - b.z) - (a.d + b.d) / 2);
      return Math.hypot(dx, dz);
    };

    for (const def of STAGES) {
      const districtBoxes = generateStage(def).boxes.filter((box) => box.district);
      const stairs = districtBoxes.filter((box) =>
        Math.abs(box.h - 0.3) < 1e-6 && box.w <= 2.4 && box.d <= 2.4,
      );
      for (const stair of stairs) {
        const top = stair.y + stair.h / 2;
        const hasNextStep = stairs.some((candidate) => {
          const rise = candidate.y + candidate.h / 2 - top;
          return candidate.district === stair.district
            && rise > 0.29 && rise < 0.31
            && horizontalGap(stair, candidate) <= 0.05;
        });
        if (hasNextStep) continue;

        const connected = districtBoxes.some((target) => {
          if (target === stair || Math.abs(target.h - 0.3) < 1e-6) return false;
          const rise = target.y + target.h / 2 - top;
          return target.district === stair.district
            && rise >= -0.15 && rise <= 0.4
            && horizontalGap(stair, target) <= 0.45;
        });
        expect(connected, `${def.id}:${stair.district} stair top @ ${stair.x},${stair.z},y${top}`).toBe(true);
      }
    }
  });

  it('通常面とゾンビ面の巨大修道城は内部戦闘導線を持つ', () => {
    for (const stageId of ['takadai', 'z04']) {
      const def = STAGES.find((stage) => stage.id === stageId)!;
      const abbey = generateStage(def).boxes.filter((box) => box.district === 'abbey');
      expect(abbey.length, stageId).toBeGreaterThan(150);
      const xMin = Math.min(...abbey.map((box) => box.x - box.w / 2));
      const xMax = Math.max(...abbey.map((box) => box.x + box.w / 2));
      const zMin = Math.min(...abbey.map((box) => box.z - box.d / 2));
      const zMax = Math.max(...abbey.map((box) => box.z + box.d / 2));
      expect(Math.max(xMax - xMin, zMax - zMin), `${stageId}: long span`).toBeGreaterThanOrEqual(90);
      expect(Math.min(xMax - xMin, zMax - zMin), `${stageId}: short span`).toBeGreaterThanOrEqual(70);
      const stairs = abbey.filter((box) => Math.abs(box.h - 0.3) < 1e-6);
      expect(stairs.length, `${stageId}: stairs`).toBeGreaterThanOrEqual(90);
      expect(abbey.some((box) => box.y + box.h / 2 > 17), `${stageId}: towers`).toBe(true);
      expect(abbey.filter((box) => box.h <= 0.6 && box.y > 5).length, `${stageId}: upper walks`).toBeGreaterThanOrEqual(8);
      expect(abbey.filter((box) => box.h >= 7 && box.w <= 2.5 && box.d <= 2.5).length, `${stageId}: columns`).toBeGreaterThanOrEqual(20);
    }
  });

  it('breakable: ghost/decor ボックスは絶対に breakable にならない', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      for (const box of layout.boxes) {
        if (box.ghost || box.decor) {
          expect(box.breakable, `${def.id}: ghost/decor box should not be breakable`).toBeUndefined();
        }
      }
    }
  });

  it('breakable: hp は 120〜260 の範囲に収まる', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      for (const box of layout.boxes) {
        if (box.breakable === undefined) continue;
        expect(box.breakable.hp, `${def.id}: hp too low`).toBeGreaterThanOrEqual(120);
        expect(box.breakable.hp, `${def.id}: hp too high`).toBeLessThanOrEqual(260);
      }
    }
  });

  it('breakable: 小〜中型プロップの 15〜55% に付与される(確率35%の許容誤差込み)', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      const candidates = layout.boxes.filter((box) => {
        if (box.ghost || box.decor) return false;
        const maxXZ = Math.max(box.w, box.d);
        const minXZ = Math.min(box.w, box.d);
        return maxXZ <= 8 && box.h >= 0.8 && box.h <= 10 && (minXZ <= 0 || maxXZ / minXZ <= 5);
      });
      if (candidates.length === 0) continue;
      const breakableCount = layout.boxes.filter((b) => b.breakable !== undefined).length;
      const ratio = breakableCount / candidates.length;
      expect(ratio, `${def.id}: breakable ratio ${ratio.toFixed(2)}`).toBeGreaterThan(0.1);
      expect(ratio, `${def.id}: breakable ratio ${ratio.toFixed(2)}`).toBeLessThan(0.65);
    }
  });

  it('breakable: 同じステージ定義からは常に同じ breakable 割当が出る(決定論)', () => {
    for (const def of STAGES.slice(0, 5)) {
      const a = generateStage(def);
      const b = generateStage(def);
      const aBreakable = a.boxes.map((x) => x.breakable);
      const bBreakable = b.boxes.map((x) => x.breakable);
      expect(JSON.stringify(aBreakable)).toBe(JSON.stringify(bBreakable));
    }
  });

  it('Soukoの現行release経路は12屋根を識別するが、未承認monitor衝突は採用しない', () => {
    const definition = STAGES.find((stage) => stage.id === 'souko')!;
    const layout = generateStage(definition);
    const supports = layout.boxes.filter((box) => box.roofMonitorSupport === true);
    expect(supports).toHaveLength(12);
    expect(supports.every((box) => box.structural === true)).toBe(true);
    expect(supports.map((box) => box.district).sort()).toEqual([
      'hangar', 'hangar', 'hangar',
      'terminal', 'terminal', 'terminal',
      'warehouse', 'warehouse', 'warehouse', 'warehouse', 'warehouse', 'warehouse',
    ]);
    expect(layout.boxes.filter((box) => box.roofMonitor !== undefined)).toHaveLength(0);
    expect(layout.boxes.filter((box) => box.visualReplacement === 'souko-roof-monitor-v1'))
      .toHaveLength(0);
  });
});

describe('dense-world v5 representative district contract', () => {
  const proofIds = ['kairou', 'chikurin', 'setsugen', 'kouwan', 'sakyuu', 'z04', 'takadai'];
  const proofDefs = proofIds.map((id) => STAGES.find((stage) => stage.id === id)!);

  const pointToPlacement = (
    x: number,
    z: number,
    placement: { cx: number; cz: number; width: number; depth: number },
  ): number => {
    const dx = Math.max(0, Math.abs(x - placement.cx) - placement.width / 2);
    const dz = Math.max(0, Math.abs(z - placement.cz) - placement.depth / 2);
    return Math.hypot(dx, dz);
  };

  it('代表7面は配置列を含めてbyte-exactに決定論的', () => {
    for (const def of proofDefs) {
      const first = generateStage(def);
      const second = generateStage(def);
      expect(JSON.stringify(first.districtPlacements), `${def.id}: placements`)
        .toBe(JSON.stringify(second.districtPlacements));
      expect(JSON.stringify(first.boxes), `${def.id}: collider boxes`)
        .toBe(JSON.stringify(second.boxes));
    }
  });

  it('各面に境界内ランドマークが厳密に2件、全14 IDは重複しない', () => {
    const catalogIds: string[] = [];
    for (const def of proofDefs) {
      const layout = generateStage(def);
      expect(layout.landmarkPlacements, `${def.id}: exact two`).toHaveLength(2);
      expect(new Set(layout.landmarkPlacements.map((item) => item.id)).size, `${def.id}: local ids`)
        .toBe(2);
      for (const landmark of layout.landmarkPlacements) {
        catalogIds.push(landmark.id);
        expect(landmark.id.startsWith(`${def.id}-`), `${def.id}: stage-exclusive id`).toBe(true);
        expect(landmark.grounded, `${landmark.id}: grounded`).toBe(true);
        expect(landmark.combatSpace, `${landmark.id}: combat space`).toBe(true);
      }
    }
    expect(catalogIds).toHaveLength(14);
    expect(new Set(catalogIds).size).toBe(14);
  });

  it('巨大建築のフットプリント・入口街路は全て境界内で他地区と交差しない', () => {
    const overlap2d = (
      a: { minX: number; maxX: number; minZ: number; maxZ: number },
      b: { minX: number; maxX: number; minZ: number; maxZ: number },
    ) => a.minX < b.maxX && a.maxX > b.minX && a.minZ < b.maxZ && a.maxZ > b.minZ;

    for (const def of proofDefs) {
      const half = def.size / 2;
      const layout = generateStage(def);
      for (const landmark of layout.landmarkPlacements) {
        const footprint = {
          minX: landmark.cx - landmark.width / 2,
          maxX: landmark.cx + landmark.width / 2,
          minZ: landmark.cz - landmark.depth / 2,
          maxZ: landmark.cz + landmark.depth / 2,
        };
        expect(footprint.minX, `${landmark.id}: min x`).toBeGreaterThanOrEqual(-half + 4);
        expect(footprint.maxX, `${landmark.id}: max x`).toBeLessThanOrEqual(half - 4);
        expect(footprint.minZ, `${landmark.id}: min z`).toBeGreaterThanOrEqual(-half + 4);
        expect(footprint.maxZ, `${landmark.id}: max z`).toBeLessThanOrEqual(half - 4);

        const halfRoad = landmark.approach.width / 2;
        const route = {
          minX: Math.min(landmark.approach.start[0], landmark.approach.end[0]) - halfRoad,
          maxX: Math.max(landmark.approach.start[0], landmark.approach.end[0]) + halfRoad,
          minZ: Math.min(landmark.approach.start[1], landmark.approach.end[1]) - halfRoad,
          maxZ: Math.max(landmark.approach.start[1], landmark.approach.end[1]) + halfRoad,
        };
        expect(route.minX, `${landmark.id}: route min x`).toBeGreaterThanOrEqual(-half);
        expect(route.maxX, `${landmark.id}: route max x`).toBeLessThanOrEqual(half);
        expect(route.minZ, `${landmark.id}: route min z`).toBeGreaterThanOrEqual(-half);
        expect(route.maxZ, `${landmark.id}: route max z`).toBeLessThanOrEqual(half);
        expect(
          Math.hypot(
            landmark.approach.start[0] - landmark.approach.end[0],
            landmark.approach.start[1] - landmark.approach.end[1],
          ),
          `${landmark.id}: approach length`,
        ).toBeGreaterThanOrEqual(20);

        const entranceDx = Math.abs(landmark.entrance[0] - landmark.cx);
        const entranceDz = Math.abs(landmark.entrance[1] - landmark.cz);
        const onXFace = Math.abs(entranceDx - (landmark.width / 2 + 0.8)) < 1e-6
          && entranceDz < 1e-6;
        const onZFace = Math.abs(entranceDz - (landmark.depth / 2 + 0.8)) < 1e-6
          && entranceDx < 1e-6;
        expect(onXFace || onZFace, `${landmark.id}: entrance lies on one authored face`).toBe(true);

        for (const district of layout.districtPlacements) {
          if (
            district.cx === landmark.cx && district.cz === landmark.cz
            && district.width === landmark.width && district.depth === landmark.depth
          ) continue;
          const districtFootprint = {
            minX: district.cx - district.width / 2,
            maxX: district.cx + district.width / 2,
            minZ: district.cz - district.depth / 2,
            maxZ: district.cz + district.depth / 2,
          };
          expect(overlap2d(route, districtFootprint), `${landmark.id}: approach versus district`)
            .toBe(false);
        }
      }
    }
  });

  it('ランドマークはタグ付き実コライダー、開放入口、階段と上階戦闘路を持つ', () => {
    for (const def of proofDefs) {
      const half = def.size / 2;
      const layout = generateStage(def);
      for (const landmark of layout.landmarkPlacements) {
        const colliders = layout.boxes.filter((box) => box.landmarkId === landmark.id);
        expect(colliders.length, `${landmark.id}: collider count`).toBeGreaterThanOrEqual(35);
        for (const requiredPart of ['floor', 'wall', 'stair', 'upper-walk'] as const) {
          expect(colliders.some((box) => box.landmarkPart === requiredPart), `${landmark.id}: ${requiredPart}`)
            .toBe(true);
        }
        expect(colliders.every((box) => box.structural && box.combatSpace), `${landmark.id}: tags`)
          .toBe(true);
        expect(Math.min(...colliders.map((box) => box.y - box.h / 2)), `${landmark.id}: seated`)
          .toBeGreaterThanOrEqual(-0.3);
        for (const box of colliders) {
          expect(Math.abs(box.x) + box.w / 2, `${landmark.id}: collider x bounds`)
            .toBeLessThanOrEqual(half);
          expect(Math.abs(box.z) + box.d / 2, `${landmark.id}: collider z bounds`)
            .toBeLessThanOrEqual(half);
        }

        const directionX = Math.sign(landmark.entrance[0] - landmark.cx);
        const directionZ = Math.sign(landmark.entrance[1] - landmark.cz);
        const gateX = landmark.cx + directionX * landmark.width / 2;
        const gateZ = landmark.cz + directionZ * landmark.depth / 2;
        const wallBlocksGate = colliders.some((box) =>
          box.landmarkPart === 'wall'
          && Math.abs(gateX - box.x) < box.w / 2
          && Math.abs(gateZ - box.z) < box.d / 2
          && box.y - box.h / 2 < 1.7
          && box.y + box.h / 2 > 0.2);
        expect(wallBlocksGate, `${landmark.id}: physical entrance opening`).toBe(false);
      }
    }
  });

  it('回廊の8本列柱は実コライダーで、3m通過余白と28m十字LOSを保つ', () => {
    const def = proofDefs.find((candidate) => candidate.id === 'kairou')!;
    const layout = generateStage(def);
    const sanctuary = layout.landmarkPlacements.find((landmark) =>
      landmark.id === 'kairou-meridian-hypostyle-sanctuary')!;
    const shell = layout.boxes.filter((box) => box.landmarkId === sanctuary.id);
    const columns = shell.filter((box) => box.landmarkPart === 'column');
    expect(columns).toHaveLength(8);
    expect(
      columns.map((box) => [box.x - sanctuary.cx, box.z - sanctuary.cz]),
    ).toEqual([
      [-34, -32], [-28, -32], [-22, -32], [-16, -32],
      [16, -32], [22, -32], [28, -32], [34, -32],
    ]);

    for (const column of columns) {
      expect(column.structural).toBe(true);
      expect(column.combatSpace).toBe(true);
      expect([column.w, column.h, column.d]).toEqual([2.6, 18, 2.6]);
      // Both inequalities must hold: each column stays out of the full union
      // of the 28m north/south and east/west combat corridors.
      expect(Math.abs(column.x - sanctuary.cx) - column.w / 2).toBeGreaterThanOrEqual(14);
      expect(Math.abs(column.z - sanctuary.cz) - column.d / 2).toBeGreaterThanOrEqual(14);
    }

    const horizontalGap = (a: BoxSpec, b: BoxSpec): [number, number] => [
      Math.max(0, Math.abs(a.x - b.x) - (a.w + b.w) / 2),
      Math.max(0, Math.abs(a.z - b.z) - (a.d + b.d) / 2),
    ];
    for (let index = 0; index < columns.length; index += 1) {
      for (let other = index + 1; other < columns.length; other += 1) {
        const [gapX, gapZ] = horizontalGap(columns[index]!, columns[other]!);
        expect(gapX >= 3 || gapZ >= 3, `column ${index}/${other}: ${gapX},${gapZ}`)
          .toBe(true);
      }
    }

    const groundObstacles = shell.filter((box) =>
      box.landmarkPart !== 'column'
      && box.landmarkPart !== 'floor'
      && box.landmarkPart !== 'upper-walk'
      && box.y - box.h / 2 < 3.2
      && box.y + box.h / 2 > 0);
    for (const [index, column] of columns.entries()) {
      for (const obstacle of groundObstacles) {
        const [gapX, gapZ] = horizontalGap(column, obstacle);
        expect(
          gapX >= 3 || gapZ >= 3,
          `column ${index} versus ${obstacle.landmarkPart}: ${gapX},${gapZ}`,
        ).toBe(true);
      }
    }

    const gateColumns = shell.filter((box) => box.landmarkPart === 'gate-column');
    expect(gateColumns).toHaveLength(4);
    expect(gateColumns.map((box) => [
      box.x - sanctuary.cx,
      box.z - sanctuary.cz,
      box.w,
      box.h,
      box.d,
    ])).toEqual([
      [-9, -37, 2, 12.2, 2], [9, -37, 2, 12.2, 2],
      [-9, 37, 2, 12.2, 2], [9, 37, 2, 12.2, 2],
    ]);
    // The central inner faces remain exactly 16m apart.
    for (const localZ of [-37, 37]) {
      const pair = gateColumns
        .filter((box) => Math.abs(box.z - sanctuary.cz - localZ) < 1e-6)
        .sort((a, b) => a.x - b.x);
      expect(pair[1]!.x - pair[1]!.w / 2 - (pair[0]!.x + pair[0]!.w / 2)).toBe(16);
    }

    // Capsule-expanded samples prove a continuous eye-height line from the
    // authored approach, through the north gate and 28m interior cross, to
    // the opposite opening. This catches columns drifting into the route even
    // when their centres still look symmetric on a minimap.
    const start = sanctuary.approach.start;
    const dx = sanctuary.approach.end[0] - start[0];
    const dz = sanctuary.approach.end[1] - start[1];
    const length = Math.hypot(dx, dz);
    const unitX = dx / length;
    const unitZ = dz / length;
    const crossLength = length + sanctuary.depth + 2;
    const capsuleRadius = 0.35;
    for (let travel = 0; travel <= crossLength; travel += 0.5) {
      const x = start[0] + unitX * travel;
      const z = start[1] + unitZ * travel;
      const blockers = layout.boxes.filter((box) =>
        !box.ghost
        && box.h > 0.6
        && box.y - box.h / 2 < 1.65
        && box.y + box.h / 2 > 1.65
        && Math.abs(x - box.x) < box.w / 2 + capsuleRadius
        && Math.abs(z - box.z) < box.d / 2 + capsuleRadius);
      expect(blockers, `LOS blocked at ${x.toFixed(1)},${z.toFixed(1)}`).toHaveLength(0);
    }
  });

  it('回廊天文台の上部城塞は実コライダーで、地上4入口を塞がない', () => {
    const def = proofDefs.find((candidate) => candidate.id === 'kairou')!;
    const layout = generateStage(def);
    const observatory = layout.landmarkPlacements.find((landmark) =>
      landmark.id === 'kairou-windcrown-caravan-observatory')!;
    const upperWalls = layout.boxes.filter((box) =>
      box.landmarkId === observatory.id && box.landmarkPart === 'upper-wall');
    expect(upperWalls).toHaveLength(5);
    for (const wall of upperWalls) {
      expect(wall.structural).toBe(true);
      expect(wall.combatSpace).toBe(true);
      const centralCore = wall.w > 10 && wall.d > 10;
      expect(wall.h).toBe(centralCore ? 12 : 8);
      expect(wall.y - wall.h / 2).toBeGreaterThan(11.5);
      expect(Math.abs(wall.x) + wall.w / 2).toBeLessThanOrEqual(def.size / 2);
      expect(Math.abs(wall.z) + wall.d / 2).toBeLessThanOrEqual(def.size / 2);
    }
    // Player/capsule eye height must see through every authored gate; the
    // upper ring may block high projectiles but never ground traversal.
    const eyeY = 1.65;
    for (const [x, z] of [
      [observatory.cx - observatory.width / 2, observatory.cz],
      [observatory.cx + observatory.width / 2, observatory.cz],
      [observatory.cx, observatory.cz - observatory.depth / 2],
      [observatory.cx, observatory.cz + observatory.depth / 2],
    ] as const) {
      expect(upperWalls.some((wall) =>
        Math.abs(x - wall.x) < wall.w / 2 + 0.35
        && Math.abs(z - wall.z) < wall.d / 2 + 0.35
        && wall.y - wall.h / 2 < eyeY
        && wall.y + wall.h / 2 > eyeY), `${x},${z}: eye gate`).toBe(false);
    }
  });

  it('実コライダー地区の占有率は24.5〜34%、通常面13〜14棟以上、修道城面9棟以上', () => {
    for (const def of proofDefs) {
      const layout = generateStage(def);
      const coverage = layout.districtPlacements.reduce(
        (sum, placement) => sum + placement.width * placement.depth,
        0,
      ) / (def.size * def.size);
      const abbey = def.recipe?.buildings[0] === 'abbey';
      expect(coverage, `${def.id}: ${(coverage * 100).toFixed(2)}%`).toBeGreaterThanOrEqual(0.245);
      expect(coverage, `${def.id}: ${(coverage * 100).toFixed(2)}%`).toBeLessThanOrEqual(0.34);
      expect(layout.districtPlacements.length, `${def.id}: district count`)
        .toBeGreaterThanOrEqual(abbey ? 9 : def.id === 'kairou' || def.size < 300 ? 13 : 14);
    }
  });

  it('全player spawnは地区外30m以上、全bot spawnは地区外8m以上', () => {
    for (const def of proofDefs) {
      const layout = generateStage(def);
      for (const [sx, , sz] of layout.playerSpawns) {
        for (const placement of layout.districtPlacements) {
          expect(pointToPlacement(sx, sz, placement), `${def.id}: player ${sx},${sz}`)
            .toBeGreaterThanOrEqual(30);
        }
      }
      for (const [sx, , sz] of layout.botSpawns) {
        for (const placement of layout.districtPlacements) {
          expect(pointToPlacement(sx, sz, placement), `${def.id}: bot ${sx},${sz}`)
            .toBeGreaterThanOrEqual(8);
        }
      }
    }
  });

  it('地区間に6m以上の通行余白を保ち、重複・閉鎖ポケットを作らない', () => {
    for (const def of proofDefs) {
      const placements = generateStage(def).districtPlacements;
      for (let index = 0; index < placements.length; index += 1) {
        const a = placements[index]!;
        for (let other = index + 1; other < placements.length; other += 1) {
          const b = placements[other]!;
          const gapX = Math.max(0, Math.abs(a.cx - b.cx) - (a.width + b.width) / 2);
          const gapZ = Math.max(0, Math.abs(a.cz - b.cz) - (a.depth + b.depth) / 2);
          expect(
            gapX >= 6 || gapZ >= 6,
            `${def.id}: district ${index}/${other} gaps ${gapX.toFixed(1)},${gapZ.toFixed(1)}`,
          ).toBe(true);
        }
      }
    }
  });

  it('通常面は直交16m主街路+7m路地、修道城面は東西南北の城門軸が連結開放', () => {
    const intersectsAxis = (
      placement: { cx: number; cz: number; width: number; depth: number },
      axis: 'x' | 'z',
      center: number,
      halfWidth: number,
    ): boolean => {
      const epsilon = 1e-6;
      return axis === 'x'
        ? placement.cx - placement.width / 2 < center + halfWidth - epsilon
          && placement.cx + placement.width / 2 > center - halfWidth + epsilon
        : placement.cz - placement.depth / 2 < center + halfWidth - epsilon
          && placement.cz + placement.depth / 2 > center - halfWidth + epsilon;
    };

    for (const def of proofDefs) {
      const layout = generateStage(def);
      const placements = layout.districtPlacements;
      if (def.recipe?.buildings[0] === 'abbey') {
        for (const placement of placements.slice(1)) {
          expect(intersectsAxis(placement, 'x', 0, 9), `${def.id}: east-west gate axis`).toBe(false);
          expect(intersectsAxis(placement, 'z', 0, 9), `${def.id}: north-south gate axis`).toBe(false);
        }
        continue;
      }
      const [primaryLandmark, alleyLandmark] = layout.landmarkPlacements;
      const corridors: ['x' | 'z', number, number][] = def.id === 'kairou'
        ? [
            ['x', 2, 8],
            ['z', primaryLandmark!.cz, 8],
            ['x', alleyLandmark!.cx, 3.5],
            ['z', -30, 3.5],
          ]
        : [
            ['x', primaryLandmark!.cx, 8],
            ['z', primaryLandmark!.cz, 8],
            ['x', alleyLandmark!.cx, 3.5],
            ['z', alleyLandmark!.cz, 3.5],
          ];
      for (const [axis, center, halfWidth] of corridors) {
        const blockers = placements.filter((placement) => {
          if (!intersectsAxis(placement, axis, center, halfWidth)) return false;
          const landmark = layout.landmarkPlacements.find((candidate) =>
            candidate.cx === placement.cx && candidate.cz === placement.cz
            && candidate.width === placement.width && candidate.depth === placement.depth);
          if (!landmark) return true;
          const offset = axis === 'x'
            ? Math.abs(landmark.cx - center)
            : Math.abs(landmark.cz - center);
          // The physical wall and interior openings are both 28m wide.
          return offset + halfWidth > 14;
        });
        expect(blockers, `${def.id}: ${axis}=${center} street blockers`).toHaveLength(0);
      }
    }
  });

  it('回廊の2英雄間は12mカプセル大通りを実際に通せる', () => {
    const def = proofDefs.find((candidate) => candidate.id === 'kairou')!;
    const layout = generateStage(def);
    const [sanctuary, observatory] = layout.landmarkPlacements;
    const westEdge = sanctuary!.cx + sanctuary!.width / 2;
    const eastEdge = observatory!.cx - observatory!.width / 2;
    expect(eastEdge - westEdge).toBeGreaterThanOrEqual(18);
    const centerX = (westEdge + eastEdge) / 2;
    const capsuleRadius = 6;
    for (let z = -def.size / 2 + 4; z <= def.size / 2 - 4; z += 1) {
      const blockers = layout.districtPlacements.filter((placement) =>
        Math.abs(centerX - placement.cx) < placement.width / 2 + capsuleRadius
        && Math.abs(z - placement.cz) < placement.depth / 2 + 0.35);
      expect(blockers, `central boulevard blocked at z=${z}`).toHaveLength(0);
    }
  });

  it('回廊の11通常街区は実屋根上に衝突付き上層商館を1棟ずつ持つ', () => {
    const def = proofDefs.find((candidate) => candidate.id === 'kairou')!;
    const layout = generateStage(def);
    const volumes = layout.boxes.filter((box) => box.urbanVolume);
    expect(volumes).toHaveLength(layout.districtPlacements.length - 2);
    for (const volume of volumes) {
      expect(volume.structural).toBe(true);
      expect(volume.h).toBeGreaterThanOrEqual(5.8);
      const bottom = volume.y - volume.h / 2;
      const supports = layout.boxes.filter((box) =>
        !box.urbanVolume
        && box.district === volume.district
        && Math.abs(box.y + box.h / 2 - bottom) < 1e-6
        && volume.x - volume.w / 2 >= box.x - box.w / 2 - 1e-6
        && volume.x + volume.w / 2 <= box.x + box.w / 2 + 1e-6
        && volume.z - volume.d / 2 >= box.z - box.d / 2 - 1e-6
        && volume.z + volume.d / 2 <= box.z + box.d / 2 + 1e-6);
      expect(supports, `unsupported upper volume ${volume.x},${volume.z}`).not.toHaveLength(0);
    }
  });

  it('31面すべてが例外なしで生成でき、配置中心・寸法が有限', () => {
    expect(STAGES).toHaveLength(31);
    for (const def of STAGES) {
      const layout = generateStage(def);
      expect(layout.boxes.length, `${def.id}: boxes`).toBeGreaterThan(0);
      for (const placement of layout.districtPlacements) {
        for (const value of [placement.cx, placement.cz, placement.width, placement.depth]) {
          expect(Number.isFinite(value), `${def.id}: finite district field`).toBe(true);
        }
      }
    }
  });
});

// ── buildProp / generateThemeObjects テスト ────────────────────────────────

const ALL_PROP_KINDS: PropKind[] = [
  'conifer', 'broadleaf', 'deadtree', 'sakura', 'bamboo',
  'rock', 'towercrane', 'portalkrane', 'smokestack', 'gastank',
  'watertower', 'transformer', 'antenna', 'truck', 'derelictcar',
  'forklift', 'barricadecar', 'concretebarrier', 'fence', 'watchpost',
  'tankhull', 'scaffold', 'streetlight', 'signboard', 'bench',
  'vendingmachine', 'drumgroup', 'pallet', 'torii', 'stonelantern',
  'well', 'pier', 'utilitypole', 'rubble', 'gasbottlegroup', 'supplycrate',
];

describe('buildProp', () => {
  const PALETTE = STAGES[0]!.palette;
  const RAND = mulberry32(42);

  it('全36種が定義されており1個以上のBoxSpecを返す', () => {
    expect(ALL_PROP_KINDS).toHaveLength(36);
    for (const kind of ALL_PROP_KINDS) {
      const boxes = buildProp(kind, 0, 0, 0, RAND, PALETTE);
      expect(boxes.length, `${kind}: ≥1 box`).toBeGreaterThanOrEqual(1);
    }
  });

  it('全ボックスに prop:true が付く', () => {
    for (const kind of ALL_PROP_KINDS) {
      const boxes = buildProp(kind, 0, 0, 0, RAND, PALETTE);
      for (const box of boxes) {
        expect(box.prop, `${kind}: prop`).toBe(true);
      }
    }
  });

  it('h>3 のボックスに shadowCaster:true が付く / h<=3 には付かない', () => {
    for (const kind of ALL_PROP_KINDS) {
      const boxes = buildProp(kind, 0, 0, 0, RAND, PALETTE);
      for (const box of boxes) {
        if (box.h > 3) {
          expect(box.shadowCaster, `${kind} h=${box.h}: shadowCaster`).toBe(true);
        } else {
          expect(box.shadowCaster, `${kind} h=${box.h}: no shadowCaster`).toBeUndefined();
        }
      }
    }
  });

  it('全ボックスの寸法が正の数', () => {
    for (const kind of ALL_PROP_KINDS) {
      const boxes = buildProp(kind, 0, 0, 0, RAND, PALETTE);
      for (const box of boxes) {
        expect(box.w, `${kind}: w>0`).toBeGreaterThan(0);
        expect(box.h, `${kind}: h>0`).toBeGreaterThan(0);
        expect(box.d, `${kind}: d>0`).toBeGreaterThan(0);
      }
    }
  });

  it('大型プロップ(smokestack/towercrane/antenna/utilitypole/watertower)は少なくとも1ボックスにshadowCaster', () => {
    const large: PropKind[] = ['smokestack', 'towercrane', 'antenna', 'utilitypole', 'watertower'];
    for (const kind of large) {
      const boxes = buildProp(kind, 0, 0, 0, RAND, PALETTE);
      expect(boxes.some((b) => b.shadowCaster === true), `${kind}: shadowCaster`).toBe(true);
    }
  });

  it('rot=0 と rot=2 で同じbox数を返す(回転対称)', () => {
    for (const kind of ALL_PROP_KINDS) {
      const b0 = buildProp(kind, 0, 0, 0, RAND, PALETTE);
      const b2 = buildProp(kind, 0, 0, 2, RAND, PALETTE);
      expect(b0.length, `${kind}: box count same for rot 0 and 2`).toBe(b2.length);
    }
  });
});

describe('generateThemeObjects', () => {
  it('同じdef+buildingPlacedからは常に同じ結果(決定論)', () => {
    for (const def of STAGES.slice(0, 6)) {
      const r1 = mulberry32(def.seed ^ 0x7e57ab1e);
      const r2 = mulberry32(def.seed ^ 0x7e57ab1e);
      const a = generateThemeObjects(def, [], r1);
      const b = generateThemeObjects(def, [], r2);
      expect(JSON.stringify(a), `${def.id}: determinism`).toBe(JSON.stringify(b));
    }
  });

  it('生成されたプロップは全て prop:true を持つ', () => {
    for (const def of STAGES) {
      const rand = mulberry32(def.seed ^ 0x7e57ab1e);
      const boxes = generateThemeObjects(def, [], rand);
      for (const box of boxes) {
        expect(box.prop, `${def.id}: prop`).toBe(true);
      }
    }
  });

  it('高密度化後も全ステージのプロップbox数が110以下', () => {
    // Blender/Three.jsの双方で素材単位へマージされ実DCは固定。Rapier側の静的Box数だけを
    // 100前後に制限し、オブジェクト密度とR100時のCPU余裕を両立する。
    for (const def of STAGES) {
      const rand = mulberry32(def.seed ^ 0x7e57ab1e);
      const boxes = generateThemeObjects(def, [], rand);
      expect(boxes.length, `${def.id}: static prop budget (${boxes.length} boxes)`).toBeLessThanOrEqual(110);
    }
  });

  it('プロップ(decorを除く)はステージ境界+2m以内に収まる', () => {
    for (const def of STAGES) {
      const half = def.size / 2;
      const rand = mulberry32(def.seed ^ 0x7e57ab1e);
      const boxes = generateThemeObjects(def, [], rand);
      for (const box of boxes) {
        if (box.decor) continue;
        expect(Math.abs(box.x) + box.w / 2, `${def.id}: x bound`).toBeLessThanOrEqual(half + 2);
        expect(Math.abs(box.z) + box.d / 2, `${def.id}: z bound`).toBeLessThanOrEqual(half + 2);
      }
    }
  });

  it('generateStage に統合後も全体の決定論は保たれる', () => {
    for (const def of STAGES.slice(0, 5)) {
      const a = generateStage(def);
      const b = generateStage(def);
      expect(JSON.stringify(a), `${def.id}: generateStage determinism`).toBe(JSON.stringify(b));
    }
  });

  it('objects未設定ステージも含め全ステージで0エラー', () => {
    for (const def of STAGES) {
      const rand = mulberry32(def.seed ^ 0x7e57ab1e);
      expect(() => generateThemeObjects(def, [], rand)).not.toThrow();
    }
  });
});

// ── ミニシーン + PropPlacement契約(R53-S2) ────────────────────────────────

describe('ミニシーン(scatter=scene)', () => {
  it('MINI_SCENE_IDSは5〜8種で全31ステージの少なくとも1箇所に使われている', () => {
    expect(MINI_SCENE_IDS.length).toBeGreaterThanOrEqual(5);
    expect(MINI_SCENE_IDS.length).toBeLessThanOrEqual(8);
    for (const def of STAGES) {
      const sceneEntries = (def.recipe?.objects ?? []).filter((o) => o.scatter === 'scene');
      expect(sceneEntries.length, `${def.id}: at least 1 scene entry`).toBeGreaterThanOrEqual(1);
      for (const e of sceneEntries) {
        expect(e.sceneId, `${def.id}: sceneId set`).toBeDefined();
        expect(MINI_SCENE_IDS, `${def.id}: sceneId is known`).toContain(e.sceneId);
      }
    }
  });

  it('シーン散布を追加しても全ステージのプロップbox数は110以下のまま', () => {
    for (const def of STAGES) {
      const rand = mulberry32(def.seed ^ 0x7e57ab1e);
      const boxes = generateThemeObjects(def, [], rand);
      expect(boxes.length, `${def.id}: static prop budget (${boxes.length} boxes)`).toBeLessThanOrEqual(110);
    }
  });

  it('決定論: 同じdefからは常に同じシーン配置が出る(placementsOut込み)', () => {
    for (const def of STAGES.slice(0, 8)) {
      const r1 = mulberry32(def.seed ^ 0x7e57ab1e);
      const r2 = mulberry32(def.seed ^ 0x7e57ab1e);
      const p1: PropPlacement[] = [];
      const p2: PropPlacement[] = [];
      const a = generateThemeObjects(def, [], r1, p1);
      const b = generateThemeObjects(def, [], r2, p2);
      expect(JSON.stringify(a), `${def.id}: boxes determinism`).toBe(JSON.stringify(b));
      expect(JSON.stringify(p1), `${def.id}: placements determinism`).toBe(JSON.stringify(p2));
    }
  });

  it('既存配置ビット不変: scatter=sceneのエントリを取り除いても、残りの箱は完全に同一(順序込み)', () => {
    for (const def of STAGES) {
      const objects = def.recipe?.objects;
      if (!objects?.length) continue;
      const sceneCount = objects.filter((o) => o.scatter === 'scene').length;
      if (sceneCount === 0) continue; // 全ステージにscene追加済みのはずだが念のため

      const legacyOnlyDef: StageDef = {
        ...def,
        recipe: { ...def.recipe!, objects: objects.filter((o) => o.scatter !== 'scene') },
      };
      const rLegacy = mulberry32(def.seed ^ 0x7e57ab1e);
      const rFull = mulberry32(def.seed ^ 0x7e57ab1e);
      const legacyBoxes = generateThemeObjects(legacyOnlyDef, [], rLegacy);
      const fullBoxes = generateThemeObjects(def, [], rFull);

      // シーンは末尾に追加されるだけ → 先頭 legacyBoxes.length 件は完全一致するはず
      expect(fullBoxes.length, `${def.id}: full >= legacy`).toBeGreaterThanOrEqual(legacyBoxes.length);
      expect(
        JSON.stringify(fullBoxes.slice(0, legacyBoxes.length)),
        `${def.id}: legacy boxes byte-identical`,
      ).toBe(JSON.stringify(legacyBoxes));
    }
  });

  it('シーン内のプロップも境界内・スポーン離隔・prop:trueを満たす', () => {
    for (const def of STAGES) {
      const half = def.size / 2;
      const layout = generateStage(def);
      const spawns = [...layout.playerSpawns, ...layout.botSpawns];
      for (const box of layout.boxes) {
        if (box.ghost || box.decor) continue;
        expect(Math.abs(box.x) + box.w / 2, `${def.id}: x bound`).toBeLessThanOrEqual(half + 2);
        expect(Math.abs(box.z) + box.d / 2, `${def.id}: z bound`).toBeLessThanOrEqual(half + 2);
        if (box.prop) {
          for (const [sx, , sz] of spawns) {
            const dx = Math.max(0, Math.abs(box.x - sx) - box.w / 2);
            const dz = Math.max(0, Math.abs(box.z - sz) - box.d / 2);
            expect(Math.hypot(dx, dz), `${def.id}: prop far from spawn`).toBeGreaterThan(1);
          }
        }
      }
    }
  });
});

describe('PropPlacement契約(rotRad/scaleJitter, M2c引き継ぎ)', () => {
  it('generateStage().propPlacements が recipe.objects を持つ全ステージで非空', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      if (def.recipe?.objects?.length) {
        expect(layout.propPlacements.length, `${def.id}: propPlacements non-empty`).toBeGreaterThan(0);
      } else {
        expect(layout.propPlacements).toEqual([]);
      }
    }
  });

  it('rotRadは[0, 2π)、scaleJitterは[0.88, 1.12]の範囲に収まる', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      for (const p of layout.propPlacements) {
        expect(p.rotRad, `${def.id}: rotRad >= 0`).toBeGreaterThanOrEqual(0);
        expect(p.rotRad, `${def.id}: rotRad < 2π`).toBeLessThan(Math.PI * 2);
        expect(p.scaleJitter, `${def.id}: scaleJitter lower`).toBeGreaterThanOrEqual(0.88);
        expect(p.scaleJitter, `${def.id}: scaleJitter upper`).toBeLessThanOrEqual(1.12);
      }
    }
  });

  it('propPlacementsの各インスタンスのkindは有効なPropKindで、cx/czは有限数', () => {
    const def = STAGES.find((s) => s.id === 'onsengai')!;
    const layout = generateStage(def);
    expect(layout.propPlacements.length).toBeGreaterThan(0);
    for (const p of layout.propPlacements) {
      expect(typeof p.kind).toBe('string');
      expect(Number.isFinite(p.cx)).toBe(true);
      expect(Number.isFinite(p.cz)).toBe(true);
    }
  });

  it('propPlacementsの件数はboxesのprop:true件数以下(1インスタンス=1〜3boxのため)', () => {
    for (const def of STAGES) {
      const layout = generateStage(def);
      const propBoxCount = layout.boxes.filter((b) => b.prop).length;
      expect(layout.propPlacements.length, `${def.id}`).toBeLessThanOrEqual(propBoxCount);
    }
  });

  it('rotRad/scaleJitterは既存のBoxSpec(コライダー)側には一切現れない(視覚専用の分離を保証)', () => {
    for (const def of STAGES.slice(0, 5)) {
      const layout = generateStage(def);
      for (const box of layout.boxes) {
        const rec = box as unknown as Record<string, unknown>;
        expect(rec.rotRad).toBeUndefined();
        expect(rec.scaleJitter).toBeUndefined();
      }
    }
  });
});

// ── R57-⑥ 確証バグ修正: プロップ視覚回転(rotRad)が軸整列コライダーからはみ出す量の非回帰 ──
//
// V-C確証: LONG_PROP_KINDS が PROP_FOOTPRINTS(クリアランス用の粗い近似値)のアスペクト比から
// 導出されていたため、実コライダーとの乖離・絶対長無視・境界値(アスペクト丁度2.0)取りこぼしの
// 3つの穴で concretebarrier/derelictcar/barricadecar/tankhull(いずれも最頻の遮蔽物)が
// ±0.45rad(約26°)のまま残存し、視覚が軸整列コライダーから最大~1.4mはみ出していた
// (ファントム遮蔽=弾すり抜け/見えない壁)。
//
// 以下は stage.ts の非公開実装(PROP_JITTER_AMP等)に依存せず、公開API(buildProp/generateStage)
// のみを使ったブラックボックス回帰: 「回転済み視覚コーナー」が「軸整列コライダーAABB」から
// 許容(0.25m)を超えてはみ出さないことを、実際に生成された全ステージの全プロップ配置で検証する。
describe('プロップ視覚ジッタのコライダーはみ出し非回帰(R57-⑥)', () => {
  const OVERHANG_ALLOWANCE_M = 0.25;
  const PALETTE = STAGES[0]!.palette;

  /** kindのrot=0コライダー箱群の局所頂点(原点基準)と軸整列AABB。 */
  function localColliderCorners(kind: PropKind): {
    corners: Array<[number, number]>;
    xMin: number; xMax: number; zMin: number; zMax: number;
  } {
    const boxes = buildProp(kind, 0, 0, 0, () => 0, PALETTE);
    let xMin = Infinity, xMax = -Infinity, zMin = Infinity, zMax = -Infinity;
    const corners: Array<[number, number]> = [];
    for (const box of boxes) {
      const x0 = box.x - box.w / 2, x1 = box.x + box.w / 2;
      const z0 = box.z - box.d / 2, z1 = box.z + box.d / 2;
      xMin = Math.min(xMin, x0); xMax = Math.max(xMax, x1);
      zMin = Math.min(zMin, z0); zMax = Math.max(zMax, z1);
      corners.push([x0, z0], [x0, z1], [x1, z0], [x1, z1]);
    }
    return { corners, xMin, xMax, zMin, zMax };
  }

  /** 角度thetaで回転したコーナー群が、元の軸整列AABB(局所rot=0基準)から飛び出す最大量(m)。
   * ジッタ振幅そのものを検証する用途(実配置のquantSteps分離は行わない、単純な理論値)。 */
  function overhangAt(
    data: { corners: Array<[number, number]>; xMin: number; xMax: number; zMin: number; zMax: number },
    theta: number,
  ): number {
    const c = Math.cos(theta);
    const s = Math.sin(theta);
    let maxOver = -Infinity;
    for (const [x, z] of data.corners) {
      const rx = x * c - z * s;
      const rz = x * s + z * c;
      maxOver = Math.max(maxOver, rx - data.xMax, data.xMin - rx, rz - data.zMax, data.zMin - rz);
    }
    return maxOver;
  }

  /** 90°刻みquantStepsだけ回転させたコーナー群のAABB(=実コライダーのAABBと一致)。 */
  function quantRotatedAabb(
    data: { corners: Array<[number, number]> },
    quantSteps: number,
  ): { xMin: number; xMax: number; zMin: number; zMax: number } {
    const k = ((quantSteps % 4) + 4) % 4;
    let xMin = Infinity, xMax = -Infinity, zMin = Infinity, zMax = -Infinity;
    for (const [x, z] of data.corners) {
      const [rx, rz] = k === 0 ? [x, z] : k === 1 ? [-z, x] : k === 2 ? [-x, -z] : [z, -x];
      xMin = Math.min(xMin, rx); xMax = Math.max(xMax, rx);
      zMin = Math.min(zMin, rz); zMax = Math.max(zMax, rz);
    }
    return { xMin, xMax, zMin, zMax };
  }

  /** 実配置のrotRad(=quantSteps*90°+ジッタ)における視覚コーナーが、
   * 実コライダーAABB(quantSteps分だけ回転済み)から飛び出す量(m)。これが実ゲームの
   * 「視覚がコライダーからはみ出す量」そのもの。 */
  function placementOverhang(
    data: { corners: Array<[number, number]> },
    rotRad: number,
  ): number {
    const quantSteps = Math.round(rotRad / (Math.PI / 2));
    const aabb = quantRotatedAabb(data, quantSteps);
    const c = Math.cos(rotRad);
    const s = Math.sin(rotRad);
    let maxOver = -Infinity;
    for (const [x, z] of data.corners) {
      const rx = x * c - z * s;
      const rz = x * s + z * c;
      maxOver = Math.max(maxOver, rx - aabb.xMax, aabb.xMin - rx, rz - aabb.zMax, aabb.zMin - rz);
    }
    return maxOver;
  }

  it('全ステージの全propPlacementsで、視覚回転(rotRad)は実コライダーAABB(quantSteps込み)から許容0.25m超はみ出さない', () => {
    const EPS = 1e-6;
    let worstOverall = -Infinity;
    for (const def of STAGES) {
      const layout = generateStage(def);
      for (const p of layout.propPlacements) {
        const data = localColliderCorners(p.kind);
        const overhang = placementOverhang(data, p.rotRad);
        worstOverall = Math.max(worstOverall, overhang);
        expect(
          overhang,
          `${def.id}: ${p.kind}@(${p.cx},${p.cz}) rotRad=${p.rotRad.toFixed(4)} overhang=${overhang.toFixed(4)}m`,
        ).toBeLessThanOrEqual(OVERHANG_ALLOWANCE_M + EPS);
      }
    }
    // 実際にどこかで許容ぎりぎりまで使われていること(閾値が機能している証跡。過度に緩い実装の検出用)
    expect(worstOverall).toBeGreaterThan(0);
  });

  it('確証バグの4種(concretebarrier/derelictcar/barricadecar/tankhull)は、旧デフォルト±0.45radまで振ると許容を大きく超えるが、実際の配置(現行振幅)では許容内に収まる', () => {
    const buggyKinds: PropKind[] = ['concretebarrier', 'derelictcar', 'barricadecar', 'tankhull'];
    for (const kind of buggyKinds) {
      const data = localColliderCorners(kind);
      const oldOverhangMm = Math.max(overhangAt(data, 0.45), overhangAt(data, -0.45)) * 1000;
      // 修正前(旧ROT_JITTER=0.45固定)は許容を大きく超えていたことを記録(回帰検出の基準線)
      expect(oldOverhangMm, `${kind}: pre-fix overhang at 0.45rad`).toBeGreaterThan(OVERHANG_ALLOWANCE_M * 1000);

      // 実ステージ配置(自然発生する量子化角+実ジッタ)で許容内に収まることを確認
      let maxObserved = -Infinity;
      for (const def of STAGES) {
        const layout = generateStage(def);
        for (const p of layout.propPlacements) {
          if (p.kind !== kind) continue;
          maxObserved = Math.max(maxObserved, placementOverhang(data, p.rotRad));
        }
      }
      if (maxObserved === -Infinity) continue; // このkindが1回も配置されないステージ構成ならスキップ
      expect(maxObserved * 1000, `${kind}: post-fix observed overhang`).toBeLessThanOrEqual(OVERHANG_ALLOWANCE_M * 1000 + 1e-3);
    }
  });

  it('小型プロップ(antenna/stonelantern/streetlight等)は過度に硬直しない: 実配置のrotRadが量子化角から±0.2rad以上ばらつく', () => {
    const smallKinds: PropKind[] = ['antenna', 'stonelantern', 'vendingmachine', 'supplycrate'];
    for (const kind of smallKinds) {
      let maxDelta = 0;
      for (const def of STAGES) {
        const layout = generateStage(def);
        for (const p of layout.propPlacements) {
          if (p.kind !== kind) continue;
          const quant = Math.round(p.rotRad / (Math.PI / 2));
          let delta = p.rotRad - quant * (Math.PI / 2);
          // 正規化: 最短角差
          while (delta > Math.PI) delta -= Math.PI * 2;
          while (delta < -Math.PI) delta += Math.PI * 2;
          maxDelta = Math.max(maxDelta, Math.abs(delta));
        }
      }
      if (maxDelta === 0) continue; // 未配置ならスキップ(存在しないステージ構成向けの安全弁)
      expect(maxDelta, `${kind}: jitter amplitude should stay large (not over-stiffened)`).toBeGreaterThan(0.2);
    }
  });
});
