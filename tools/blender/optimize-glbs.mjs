#!/usr/bin/env node

/**
 * Deterministically generate MikkTSpace tangents and apply
 * EXT_meshopt_compression to Blender stage exports.
 *
 * Blender remains the artistic source.  This final delivery pass preserves
 * geometry/material semantics and extras while making normal-mapped meshes
 * portable across glTF runtimes and quantizing attributes at a game-safe
 * precision. Hibana's GLTFLoader already installs Three.js' MeshoptDecoder
 * before loading any stage GLB.
 */
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  renameSync,
  rmSync,
  statSync,
  unlinkSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const files = process.argv.slice(2).map((file) => resolve(file));
if (files.length === 0) throw new Error('usage: optimize-glbs.mjs <stage.glb> [...]');

// Intermediate GLBs never belong in a cloud-synchronised project directory.
// A unique invocation directory also prevents simultaneous workers from
// unlinking or replacing each other's files. The override names the parent
// directory, not the disposable invocation directory itself.
const commandTimeoutMs = Number.parseInt(process.env.HIBANA_MESHOPT_TIMEOUT_MS ?? '120000', 10);
if (!Number.isSafeInteger(commandTimeoutMs) || commandTimeoutMs <= 0) {
  throw new Error(`invalid HIBANA_MESHOPT_TIMEOUT_MS: ${process.env.HIBANA_MESHOPT_TIMEOUT_MS}`);
}
const workRoot = resolve(process.env.HIBANA_MESHOPT_WORK_DIR ?? tmpdir());
mkdirSync(workRoot, { recursive: true });
const workDir = mkdtempSync(join(workRoot, 'hibana-meshopt-'));
const cli = resolve('node_modules/@gltf-transform/cli/bin/cli.js');
const reports = [];

function hasMeshoptCompression(input) {
  const bytes = readFileSync(input);
  if (bytes.length < 20 || bytes.toString('ascii', 0, 4) !== 'glTF') {
    throw new Error(`invalid GLB header: ${input}`);
  }
  const declaredLength = bytes.readUInt32LE(8);
  if (declaredLength !== bytes.length) {
    throw new Error(`incomplete GLB: declared ${declaredLength} bytes, read ${bytes.length}: ${input}`);
  }
  const jsonLength = bytes.readUInt32LE(12);
  if (bytes.toString('ascii', 16, 20) !== 'JSON' || 20 + jsonLength > bytes.length) {
    throw new Error(`invalid GLB JSON chunk: ${input}`);
  }
  const json = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength).replace(/\0+$/u, ''));
  return json.extensionsUsed?.includes('EXT_meshopt_compression') ?? false;
}

function runCliPhase(phase, input, args) {
  console.error(`[optimize-glbs] ${phase}: ${basename(input)}`);
  const result = spawnSync(process.execPath, [cli, ...args], {
    stdio: 'inherit',
    timeout: commandTimeoutMs,
  });
  if (result.error) {
    const timeout = result.error.code === 'ETIMEDOUT' ? ` after ${commandTimeoutMs} ms` : '';
    throw new Error(`${phase} failed${timeout}: ${input}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(`${phase} failed (${result.status ?? result.signal ?? 'unknown'}): ${input}`);
  }
}

function replaceInput(output, input) {
  try {
    renameSync(output, input);
    return;
  } catch (error) {
    if (error?.code !== 'EXDEV') throw error;
  }

  // tmpdir may live on another filesystem. Copy to an input-adjacent file,
  // then atomically rename only after the complete optimized file exists.
  const sibling = `${input}.${process.pid}.meshopt.tmp`;
  try {
    try { unlinkSync(sibling); } catch { /* first run */ }
    copyFileSync(output, sibling);
    renameSync(sibling, input);
    try { unlinkSync(output); } catch { /* disposable workdir cleanup follows */ }
  } catch (error) {
    try { unlinkSync(sibling); } catch { /* cleanup after failed promotion */ }
    throw error;
  }
}

try {
  for (const [fileIndex, input] of files.entries()) {
    if (!input.endsWith('.glb')) throw new Error(`not a GLB: ${input}`);
    if (hasMeshoptCompression(input)) {
      throw new Error(`refusing lossy re-compression; regenerate the raw Blender GLB first: ${input}`);
    }
    const before = statSync(input).size;
    const temporaryStem = `${basename(input, '.glb')}.${fileIndex}`;
    const tangentOutput = resolve(workDir, `${temporaryStem}.tangent.glb`);
    const output = resolve(workDir, `${temporaryStem}.meshopt.glb`);

    // Blender omits tangents on a few procedural terrain/foliage primitives.
    // Generate them explicitly before quantization so production GLBs do not
    // depend on runtime tangent generation (which can differ between drivers).
    runCliPhase('tangents', input, [
      'tangents',
      input,
      tangentOutput,
    ]);

    runCliPhase('meshopt', input, [
      'meshopt',
      tangentOutput,
      output,
      '--level', 'high',
      '--quantization-volume', 'mesh',
      '--quantize-position', '16',
      '--quantize-normal', '12',
      '--quantize-texcoord', '14',
    ]);
    const after = statSync(output).size;
    if (after >= before) throw new Error(`Meshopt did not reduce ${input}: ${before} -> ${after}`);
    replaceInput(output, input);
    reports.push({
      file: basename(input),
      before,
      after,
      reductionPercent: Number(((1 - after / before) * 100).toFixed(2)),
    });
  }
} finally {
  rmSync(workDir, { recursive: true, force: true });
}

console.log(JSON.stringify({ optimized: reports.length, reports }, null, 2));
