// Runtime-only glTF facade. Its sibling .d.ts deliberately exposes a very small type surface:
// @types/three's Meshopt declaration recursively re-exports meshoptimizer and makes TS 5.6 spend
// excessive time expanding the loader module. Vite still bundles the official implementations.
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { clone } from 'three/addons/utils/SkeletonUtils.js';

export function createGltfRuntime(renderer, base, options) {
  const loader = new GLTFLoader();
  loader.setMeshoptDecoder(MeshoptDecoder);
  let ktx2 = null;
  let draco = null;
  if (options.ktx2TranscoderPath) {
    ktx2 = new KTX2Loader();
    ktx2.setTranscoderPath(`${base}${options.ktx2TranscoderPath}`);
    ktx2.detectSupport(renderer);
    loader.setKTX2Loader(ktx2);
  }
  if (options.dracoDecoderPath) {
    draco = new DRACOLoader();
    draco.setDecoderPath(`${base}${options.dracoDecoderPath}`);
    loader.setDRACOLoader(draco);
  }
  return {
    async loadScene(url, signal) {
      // GLTFLoader.loadAsync does not expose AbortSignal. Fetch the GLB body
      // explicitly so a disposed match cannot retain an unbounded body
      // request, then hand the completed bytes to the official parser. The
      // decoder/parser phase itself remains governed by Three's loader APIs.
      const response = await globalThis.fetch(url, { signal, cache: 'force-cache' });
      if (!response.ok) throw new Error(`GLB HTTP ${response.status}: ${url}`);
      const payload = await response.arrayBuffer();
      const slash = url.lastIndexOf('/');
      const resourcePath = slash >= 0 ? url.slice(0, slash + 1) : '';
      const result = await loader.parseAsync(payload, resourcePath);
      // Object3D.animationsはThree標準の保管場所。小さなfacadeを保ったまま、
      // 環境GLBと共通のMeshopt/Draco/KTX2 loaderでスキンアニメも取得できる。
      result.scene.animations = result.animations;
      return result.scene;
    },
    clone(source) {
      return clone(source);
    },
    dispose() {
      ktx2?.dispose();
      draco?.dispose();
    },
  };
}
