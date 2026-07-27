#!/usr/bin/env node
/** Apply Kairou V10's mineral PBR language to a collision-aligned raw GLB.
 *
 * Geometry, transforms, node names, extras, accessors and primitive topology
 * are immutable in this pass.  Only material texture bindings and scalar PBR
 * response are changed.  This makes the output suitable for exact contact-
 * skeleton comparison before any public integration is attempted.
 */
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '../../../..');
const require = createRequire(resolve(REPO_ROOT, 'package.json'));
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS, KHRTextureTransform } = require('@gltf-transform/extensions');
const sharp = require('sharp');

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) throw new Error(`unknown argument ${token}`);
    const key = token.slice(2);
    const value = argv[++index];
    if (!value) throw new Error(`${token} requires a value`);
    result[key] = resolve(value);
  }
  for (const key of ['input', 'output', 'source-dir', 'report']) {
    if (!result[key]) throw new Error(`--${key} is required`);
  }
  return result;
}

const FAMILY_BY_ROLE = {
  wall_weathered: 'dark-stone',
  obstacle: 'dark-stone',
  wall_warm: 'pale-stone',
  wall: 'pale-stone',
  terrain: 'terrain-sand',
  road: 'paved-stone',
  trim: 'mineral-trim',
  accent: 'aged-metal',
  wood: 'aged-wood',
};

const CROPS = {
  'pale-stone': { source: 'Dielectric', left: 16, top: 16, width: 256, height: 384 },
  'dark-stone': { source: 'Dielectric', left: 304, top: 16, width: 256, height: 384 },
  'terrain-sand': { source: 'Dielectric', left: 16, top: 432, width: 256, height: 384 },
  'paved-stone': { source: 'Dielectric', left: 592, top: 624, width: 416, height: 192 },
  'mineral-trim': { source: 'Dielectric', left: 592, top: 432, width: 416, height: 64 },
  'aged-wood': { source: 'Dielectric', left: 880, top: 16, width: 128, height: 384 },
  'aged-metal': { source: 'Metal', left: 0, top: 0, width: 256, height: 256 },
};

const BASE_FACTORS = {
  // V6 deliberately keeps three clearly separated limestone values.  The
  // atlas still supplies mineral variation, but neutral factors prevent the
  // previous orange/brown wash under daylight presentation.
  wall_weathered: [0.68, 0.70, 0.68, 1],
  obstacle: [0.61, 0.64, 0.63, 1],
  wall_warm: [0.94, 0.93, 0.88, 1],
  wall: [0.82, 0.84, 0.81, 1],
  terrain: [0.75, 0.68, 0.56, 1],
  road: [0.69, 0.70, 0.67, 1],
  trim: [0.78, 0.82, 0.80, 1],
  accent: [0.31, 0.63, 0.64, 1],
  wood: [0.43, 0.30, 0.20, 1],
};

// World-space UVs arrive in metres.  Sampling every atlas crop once per metre
// made the stone grid conspicuously repeat and flattened the large-scale
// roughness response.  Separate channel scales preserve fine normal relief
// while moving colour and ORM variation into broad 5--10 m fields.  No new
// material or texture is introduced, and the existing 512 px cap is retained.
const TEXTURE_SCALES = {
  wall_weathered: { baseColor: 0.14, orm: 0.20, normal: 0.48 },
  obstacle: { baseColor: 0.15, orm: 0.21, normal: 0.50 },
  wall_warm: { baseColor: 0.14, orm: 0.20, normal: 0.48 },
  wall: { baseColor: 0.15, orm: 0.21, normal: 0.50 },
  terrain: { baseColor: 0.10, orm: 0.16, normal: 0.34 },
  road: { baseColor: 0.12, orm: 0.18, normal: 0.42 },
  trim: { baseColor: 0.20, orm: 0.26, normal: 0.56 },
  accent: { baseColor: 0.34, orm: 0.42, normal: 0.72 },
  wood: { baseColor: 0.24, orm: 0.31, normal: 0.62 },
};

function textureOffset(role) {
  const digest = createHash('sha256').update(`kairou-v6.3.1:${role}`).digest();
  return [digest[0] / 255, digest[1] / 255];
}

function roleForMaterial(name) {
  return Object.keys(FAMILY_BY_ROLE)
    .sort((left, right) => right.length - left.length)
    .find((role) => name.endsWith(`_${role}`));
}

function sha256(buffer) {
  return createHash('sha256').update(buffer).digest('hex');
}

async function cropTexture(source, crop, channel) {
  const pipeline = sharp(source).extract(crop).resize(512, 512, {
    fit: 'fill',
    kernel: channel === 'NormalGL' ? 'cubic' : 'lanczos3',
  });
  // PNG is kept for the Blender/private QA stage.  The release optimizer
  // performs the single deterministic PNG -> WebP conversion afterwards.
  return pipeline.png({ compressionLevel: 9, adaptiveFiltering: true }).toBuffer();
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const sourceDir = args['source-dir'];
  const sourceFiles = {
    Dielectric: {
      BaseColor: resolve(sourceDir, 'T_Kairou_V4_Dielectric_BaseColor.png'),
      NormalGL: resolve(sourceDir, 'T_Kairou_V4_Dielectric_NormalGL.png'),
      ORM: resolve(sourceDir, 'T_Kairou_V4_Dielectric_ORM.png'),
    },
    Metal: {
      BaseColor: resolve(sourceDir, 'T_Kairou_V4_Metal_BaseColor.png'),
      NormalGL: resolve(sourceDir, 'T_Kairou_V4_Metal_NormalGL.png'),
      ORM: resolve(sourceDir, 'T_Kairou_V4_Metal_ORM.png'),
    },
  };
  const sourceBuffers = {};
  for (const [source, channels] of Object.entries(sourceFiles)) {
    sourceBuffers[source] = {};
    for (const [channel, path] of Object.entries(channels)) {
      sourceBuffers[source][channel] = await readFile(path);
    }
  }

  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
  const document = await io.read(args.input);
  const root = document.getRoot();
  const textureTransform = document.createExtension(KHRTextureTransform);
  const textures = new Map();
  const textureReport = [];
  for (const [family, crop] of Object.entries(CROPS)) {
    const channels = {};
    for (const channel of ['BaseColor', 'NormalGL', 'ORM']) {
      const image = await cropTexture(sourceBuffers[crop.source][channel], crop, channel);
      const texture = document
        .createTexture(`T_Kairou_V10_1_${family}_${channel}`)
        .setImage(image)
        .setMimeType('image/png');
      channels[channel] = texture;
      textureReport.push({ family, channel, bytes: image.length, sha256: sha256(image) });
    }
    textures.set(family, channels);
  }

  const materials = [];
  for (const material of root.listMaterials()) {
    const role = roleForMaterial(material.getName());
    const family = role ? FAMILY_BY_ROLE[role] : null;
    if (!family) {
      materials.push({ name: material.getName(), role: role ?? 'preserved', family: null });
      continue;
    }
    const channels = textures.get(family);
    material
      .setBaseColorTexture(channels.BaseColor)
      .setNormalTexture(channels.NormalGL)
      .setMetallicRoughnessTexture(channels.ORM)
      .setOcclusionTexture(channels.ORM)
      .setBaseColorFactor(BASE_FACTORS[role] ?? [1, 1, 1, 1])
      .setMetallicFactor(role === 'accent' ? 0.72 : 0.02)
      .setRoughnessFactor(role === 'road' ? 0.95 : role === 'wood' ? 0.82 : 0.90)
      .setExtras({
        ...(material.getExtras() ?? {}),
        hibanaKairouArtRevision: 'v10.1-collision-aligned',
        hibanaKairouPbrFamily: family,
        hibanaKairouPbrSource: 'V10.1 atlas crop; geometry and collision skeleton unchanged',
      });
    const scales = TEXTURE_SCALES[role];
    const offset = textureOffset(role);
    const transform = (scale) => textureTransform
      .createTransform()
      .setOffset(offset)
      .setScale([scale, scale]);
    material.getBaseColorTextureInfo().setExtension('KHR_texture_transform', transform(scales.baseColor));
    material.getMetallicRoughnessTextureInfo().setExtension('KHR_texture_transform', transform(scales.orm));
    material.getOcclusionTextureInfo().setExtension('KHR_texture_transform', transform(scales.orm));
    material.getNormalTextureInfo().setExtension('KHR_texture_transform', transform(scales.normal));
    materials.push({ name: material.getName(), role, family, textureScales: scales, textureOffset: offset });
  }
  await mkdir(dirname(args.output), { recursive: true });
  await io.write(args.output, document);
  const inputBytes = await readFile(args.input);
  const outputBytes = await readFile(args.output);
  const report = {
    schemaVersion: 1,
    status: 'PASS',
    geometryPolicy: 'immutable accessors, topology, node transforms and extras',
    input: { path: args.input, bytes: inputBytes.length, sha256: sha256(inputBytes) },
    output: { path: args.output, bytes: outputBytes.length, sha256: sha256(outputBytes) },
    materials,
    textures: textureReport,
  };
  await mkdir(dirname(args.report), { recursive: true });
  await writeFile(args.report, `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

await main();
