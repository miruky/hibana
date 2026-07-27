import { readFileSync, writeFileSync } from 'node:fs';
import { basename, sep, resolve } from 'node:path';
import validator from '../../../../../node_modules/gltf-validator/index.js';


const paths = process.argv.slice(2);
if (paths.length === 0) throw new Error('usage: validate_khronos_r10.mjs <file.glb> [...]');

const assets = [];
let failed = false;
for (const path of paths) {
  const report = await validator.validateBytes(new Uint8Array(readFileSync(path)), {
    uri: basename(path),
    format: 'glb',
    maxIssues: 0,
    writeTimestamp: false,
  });
  const counts = {
    errors: report.issues?.numErrors ?? 0,
    warnings: report.issues?.numWarnings ?? 0,
    infos: report.issues?.numInfos ?? 0,
    hints: report.issues?.numHints ?? 0,
  };
  if (counts.errors > 0 || counts.warnings > 0) failed = true;
  assets.push({ path, counts, report });
}

const output = { status: failed ? 'FAIL' : 'PASS', assets };
const artifactRoot = resolve(
  process.env.HIBANA_KOUWAN_R10_ROOT ?? 'tools/blender/work/kouwan-r10',
);
const publicRoot = resolve('public');
const workRoot = resolve('tools/blender/work');
if (artifactRoot === publicRoot || artifactRoot.startsWith(`${publicRoot}${sep}`)) {
  throw new Error(`private candidate must never write below public/: ${artifactRoot}`);
}
if (
  artifactRoot.startsWith(`${resolve('.')}${sep}`)
  && artifactRoot !== workRoot
  && !artifactRoot.startsWith(`${workRoot}${sep}`)
) {
  throw new Error(`repository-local output must stay below ignored ${workRoot}: ${artifactRoot}`);
}
const outputPath = resolve(artifactRoot, 'optimized-r10/khronos-validation-r10.json');
writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`);
console.log(JSON.stringify({ status: output.status, assets: assets.map(({ path, counts }) => ({ path, counts })) }, null, 2));
if (failed) process.exitCode = 1;
