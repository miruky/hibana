import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { STAGES } from './stages';
import type { BoxSpec } from './stage';
import { buildStagePropDecor } from './stage-prop-decor';

describe('procedural stage-shell decoration fallback', () => {
  it('全装飾を一つの切替rootへ収め、Blender外殻との二重描画を止められる', () => {
    const scene = new THREE.Scene();
    const boxes: BoxSpec[] = [
      { x: 0, y: 2, z: 0, w: 8, h: 4, d: 4, color: '#777777', emissive: false },
      { x: 12, y: 0.6, z: 4, w: 5, h: 1.2, d: 1.2, color: '#555555', emissive: false },
    ];
    const root = buildStagePropDecor(scene, boxes, STAGES[0]!.palette);

    expect(root.name).toBe('stage:procedural-shell-decor');
    expect(scene.children).toEqual([root]);
    expect(root.children.length).toBeGreaterThan(0);
    root.visible = false;
    expect(root.children.every((child) => child.visible)).toBe(true);

    root.traverse((node) => {
      if (!(node instanceof THREE.Mesh)) return;
      node.geometry.dispose();
      const materials = Array.isArray(node.material) ? node.material : [node.material];
      for (const material of materials) material.dispose();
      if (node instanceof THREE.InstancedMesh) node.dispose();
    });
  });
});
