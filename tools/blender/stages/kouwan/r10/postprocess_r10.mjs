import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { sep, resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';


const ARTIFACT_ROOT = resolve(
  process.env.HIBANA_KOUWAN_R10_ROOT ?? 'tools/blender/work/kouwan-r10',
);
const PUBLIC_ROOT = resolve('public');
const WORK_ROOT = resolve('tools/blender/work');
if (ARTIFACT_ROOT === PUBLIC_ROOT || ARTIFACT_ROOT.startsWith(`${PUBLIC_ROOT}${sep}`)) {
  throw new Error(`private candidate must never write below public/: ${ARTIFACT_ROOT}`);
}
if (
  ARTIFACT_ROOT.startsWith(`${resolve('.')}${sep}`)
  && ARTIFACT_ROOT !== WORK_ROOT
  && !ARTIFACT_ROOT.startsWith(`${WORK_ROOT}${sep}`)
) {
  throw new Error(`repository-local output must stay below ignored ${WORK_ROOT}: ${ARTIFACT_ROOT}`);
}
const ROOT = resolve(ARTIFACT_ROOT, 'optimized-r10');
const RAW = resolve(ROOT, 'raw');
const WORK = resolve(ROOT, 'work');
const STAGES = resolve(ROOT, 'stages');
const CLI = resolve('node_modules/.bin/gltf-transform');
mkdirSync(WORK, { recursive: true });
mkdirSync(STAGES, { recursive: true });


function run(args) {
  const result = spawnSync(CLI, args, { cwd: process.cwd(), encoding: 'utf8' });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.status !== 0) {
    throw new Error(`gltf-transform failed (${result.status}): ${args.join(' ')}`);
  }
}


async function stripRedundantTangents(input, output) {
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
  const document = await io.read(input);
  let removed = 0;
  for (const mesh of document.getRoot().listMeshes()) {
    for (const primitive of mesh.listPrimitives()) {
      const material = primitive.getMaterial();
      if (primitive.getAttribute('TANGENT') && !material?.getNormalTexture()) {
        primitive.setAttribute('TANGENT', null);
        removed += 1;
      }
    }
  }
  await io.write(output, document);
  return removed;
}


const textureSizes = [640, 512, 256];
for (let level = 0; level < 3; level += 1) {
  const input = resolve(RAW, `kouwan-r10-lod${level}.glb`);
  const resized = resolve(WORK, `lod${level}-resized.glb`);
  const tangent = resolve(WORK, `lod${level}-tangent.glb`);
  const stripped = resolve(WORK, `lod${level}-stripped.glb`);
  const welded = resolve(WORK, `lod${level}-welded.glb`);
  const output = resolve(STAGES, `kouwan-r10-lod${level}.glb`);
  const size = textureSizes[level];

  run(['resize', input, resized, '--width', String(size), '--height', String(size)]);
  run(['tangents', resized, tangent]);
  const removed = await stripRedundantTangents(tangent, stripped);
  if (removed === 0) throw new Error(`lod${level}: no redundant tangents removed`);
  run(['weld', stripped, welded]);
  run(['meshopt', welded, output, '--level', 'high']);
  console.log(JSON.stringify({ level, textureSize: size, redundantTangentsRemoved: removed, output }));
}
