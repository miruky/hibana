import { afterEach, describe, expect, it, vi } from 'vitest';
import type * as THREE from 'three';
import { createGltfRuntime } from './gltf-runtime.js';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('gltf runtime request lifecycle', () => {
  it('parses fetched GLB bytes through the official loader facade', async () => {
    const json = new TextEncoder().encode(JSON.stringify({
      asset: { version: '2.0' },
      scene: 0,
      scenes: [{ nodes: [] }],
      nodes: [],
    }));
    const paddedLength = Math.ceil(json.length / 4) * 4;
    const bytes = new Uint8Array(20 + paddedLength);
    const view = new DataView(bytes.buffer);
    view.setUint32(0, 0x46546c67, true);
    view.setUint32(4, 2, true);
    view.setUint32(8, bytes.length, true);
    view.setUint32(12, paddedLength, true);
    view.setUint32(16, 0x4e4f534a, true);
    bytes.fill(0x20, 20);
    bytes.set(json, 20);
    const fetchMock = vi.fn(async () => new Response(bytes, { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const runtime = createGltfRuntime({} as THREE.WebGLRenderer, '/', {});

    const scene = await runtime.loadScene('/assets/aaa/stages/empty.glb');

    expect(scene.type).toBe('Group');
    expect(scene.animations).toEqual([]);
    expect(fetchMock).toHaveBeenCalledOnce();
    runtime.dispose();
  });

  it('forwards AbortSignal to the GLB body request and settles when a match is disposed', async () => {
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      const signal = init?.signal;
      if (!signal) throw new Error('missing AbortSignal');
      signal.addEventListener('abort', () => {
        reject(new DOMException('aborted', 'AbortError'));
      }, { once: true });
    }));
    vi.stubGlobal('fetch', fetchMock);
    const runtime = createGltfRuntime(
      {} as THREE.WebGLRenderer,
      '/',
      {},
    );
    const controller = new AbortController();

    const loading = runtime.loadScene('/assets/aaa/stages/test.glb', controller.signal);
    controller.abort();

    await expect(loading).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetchMock).toHaveBeenCalledWith(
      '/assets/aaa/stages/test.glb',
      expect.objectContaining({ signal: controller.signal, cache: 'force-cache' }),
    );
    runtime.dispose();
  });
});
