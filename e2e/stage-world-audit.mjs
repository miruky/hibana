/*
 * 全固定ステージの実ゲーム描画監査。
 * 1つのheadless Chromiumを使い回し、ステージごとに独立contextを開く。
 * OS SpeechSynthesis / WebAudio / HTMLMedia / Chromium出力を全層で無音化し、
 * 画面のフォーカスは奪わない。
 *
 *   node e2e/stage-world-audit.mjs
 *   node e2e/stage-world-audit.mjs --quality=high --output=/tmp/hibana-worlds
 *   node e2e/stage-world-audit.mjs --stage=z01
 */
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { installSilentAudio, SILENT_BROWSER_ARGS } from './silence-audio.mjs';

const args = process.argv.slice(2);
const val = (key, fallback) =>
  (args.find((arg) => arg.startsWith(`${key}=`)) ?? '').split('=').slice(1).join('=') || fallback;
const quality = val('--quality', 'high');
const onlyStage = val('--stage', '');
const stageList = val('--stages', '');
const output = val('--output', '/tmp/hibana-stage-world-audit');
const assetRootArg = val('--asset-root', '');
const assetRoot = assetRootArg ? path.resolve(assetRootArg) : '';
const landmarkPoses = args.includes('--landmark-poses');
const port = Number(val('--port', '5241'));
const settleMs = Number(val('--settle-ms', '650'));
const walkMs = Number(val('--walk-ms', '0'));
const strafeMs = Number(val('--strafe-ms', '0'));
const viewportName = val('--viewport', '1280x720');
const [width, height] = viewportName.split('x').map(Number);
if (!['medium', 'high'].includes(quality)) {
  throw new Error(`stage GLB audit requires --quality=medium or high (got ${quality})`);
}
if (!Number.isFinite(width) || !Number.isFinite(height)) throw new Error(`bad viewport: ${viewportName}`);

const stageSource = readFileSync(path.resolve('src/game/stages.ts'), 'utf8');
const authoritativeStageIds = [...stageSource.matchAll(/\n\s+id: '([^']+)',\n\s+name:/g)]
  .map((match) => match[1])
  .sort((a, b) => a.localeCompare(b));
const thumbnailStageIds = readdirSync(path.resolve('public/assets/stage-thumbs'))
  .filter((name) => name.endsWith('.webp'))
  .map((name) => name.replace(/\.webp$/, ''))
  .sort((a, b) => a.localeCompare(b));
const manifest = JSON.parse(readFileSync(path.resolve('public/assets/aaa/manifest.json'), 'utf8'));
const manifestEntries = Array.isArray(manifest.assets) ? manifest.assets : [];
const manifestStageIds = manifestEntries
  .filter((entry) => entry && typeof entry === 'object' && String(entry.id).startsWith('stage-'))
  .flatMap((entry) => Array.isArray(entry.stages) ? entry.stages : [])
  .filter((stageId) => typeof stageId === 'string')
  .sort((a, b) => a.localeCompare(b));

const assertExactStageSet = (label, actual) => {
  const expected = new Set(authoritativeStageIds);
  const observed = new Set(actual);
  const missing = authoritativeStageIds.filter((stageId) => !observed.has(stageId));
  const extra = actual.filter((stageId) => !expected.has(stageId));
  if (
    authoritativeStageIds.length !== 31 ||
    expected.size !== 31 ||
    actual.length !== 31 ||
    observed.size !== 31 ||
    missing.length > 0 ||
    extra.length > 0
  ) {
    throw new Error(
      `${label} stage set mismatch: expected=${authoritativeStageIds.length}/${expected.size}` +
      ` actual=${actual.length}/${observed.size} missing=${missing.join(',')} extra=${extra.join(',')}`,
    );
  }
};

assertExactStageSet('thumbnail', thumbnailStageIds);
assertExactStageSet('manifest', manifestStageIds);
if (manifestEntries.length !== 31) throw new Error(`manifest must contain exactly 31 assets, got ${manifestEntries.length}`);
for (const stageId of authoritativeStageIds) {
  const matches = manifestEntries.filter(
    (entry) => entry?.id === `stage-${stageId}` &&
      Array.isArray(entry.stages) &&
      entry.stages.length === 1 &&
      entry.stages[0] === stageId,
  );
  if (matches.length !== 1) throw new Error(`manifest entry mismatch for ${stageId}: ${matches.length}`);
  const entry = matches[0];
  for (const field of [
    'replacesDistantMatte',
    'replacesProceduralProps',
    'replacesProceduralStageShell',
  ]) {
    if (entry[field] !== true) throw new Error(`manifest ${stageId}.${field} must be literal true`);
  }
}

if (onlyStage && stageList) throw new Error('use only one of --stage or --stages');
const requestedStageIds = stageList
  ? stageList.split(',').map((id) => id.trim()).filter(Boolean)
  : onlyStage
    ? [onlyStage]
    : authoritativeStageIds;
if (new Set(requestedStageIds).size !== requestedStageIds.length) {
  throw new Error(`duplicate stage selection: ${requestedStageIds.join(',')}`);
}
const unknownStageIds = requestedStageIds.filter((id) => !authoritativeStageIds.includes(id));
if (unknownStageIds.length > 0) throw new Error(`unknown stage: ${unknownStageIds.join(',')}`);
const stageIds = requestedStageIds;
const stageLayoutById = landmarkPoses
  ? new Map(
      JSON.parse(readFileSync(path.resolve('tools/blender/generated/stage-layouts.json'), 'utf8'))
        .stages
        .map((stage) => [stage.id, stage]),
    )
  : new Map();
if (landmarkPoses) {
  for (const stageId of stageIds) {
    const placements = stageLayoutById.get(stageId)?.landmarkPlacements;
    if (!Array.isArray(placements) || placements.length !== 2) {
      throw new Error(`${stageId}: --landmark-poses requires exactly two landmark placements`);
    }
  }
}
const manifestEntryByStage = new Map(manifestEntries.map((entry) => [entry.stages[0], entry]));
const selectedAssetUrlByStage = new Map(stageIds.map((stageId) => {
  const entry = manifestEntryByStage.get(stageId);
  const selectedUrl = quality === 'high' ? entry?.url : entry?.lods?.[0]?.url;
  if (typeof selectedUrl !== 'string' || selectedUrl.length === 0) {
    throw new Error(`missing ${quality} asset URL for ${stageId}`);
  }
  return [stageId, selectedUrl];
}));
mkdirSync(output, { recursive: true });

const vite = spawn('npx', ['vite', '--port', String(port), '--strictPort'], {
  cwd: process.cwd(),
  stdio: ['ignore', 'ignore', 'ignore'],
});
const url = `http://localhost:${port}`;
const deadline = Date.now() + 60_000;
while (Date.now() < deadline) {
  try {
    const response = await fetch(url);
    if (response.ok) break;
  } catch {
    // Vite起動待ち
  }
  await new Promise((resolve) => setTimeout(resolve, 250));
}
if (Date.now() >= deadline) {
  vite.kill('SIGTERM');
  throw new Error('vite dev did not start');
}

const readInMatchGate = (page, expectedStageId) => page.evaluate((stageId) => {
  const visible = (element) => {
    if (!(element instanceof HTMLElement) || element.hidden) return false;
    const style = getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden' && element.getClientRects().length > 0;
  };
  const overlaySelectors = [
    '[data-id="title-root"]',
    '[data-id="hub-root"]',
    '[data-id="scr-deploy"]',
    '[data-id="scr-result"]',
    '.menu-result',
  ];
  const visibleOverlays = overlaySelectors.filter((selector) =>
    [...document.querySelectorAll(selector)].some(visible));
  const hud = document.querySelector('#hud');
  const menu = document.querySelector('#menu');
  const death = hud?.querySelector('[data-id="death"]') ?? null;
  const hpText = hud?.querySelector('[data-id="hp"]')?.textContent ?? '';
  const hp = Number(hpText.replace(/[^0-9.+-]/g, ''));
  const canvas = document.querySelector('#app canvas');
  const canvasRect = canvas?.getBoundingClientRect();
  let selectedStageId = null;
  try {
    selectedStageId = JSON.parse(localStorage.getItem('hibana.loadout.v1') ?? 'null')?.stageId ?? null;
  } catch {
    selectedStageId = null;
  }
  const audit = window.__hibanaAaaAssetAudit ?? null;
  const hudVisible = visible(hud);
  const menuHidden = menu instanceof HTMLElement && menu.hidden && !visible(menu);
  const deathHidden = death instanceof HTMLElement && death.hidden && !visible(death);
  const killcamInactive = !document.body.classList.contains('killcam-active');
  const canvasConnected = canvas instanceof HTMLCanvasElement &&
    canvas.isConnected &&
    document.querySelectorAll('#app canvas').length === 1 &&
    canvas.width > 0 &&
    canvas.height > 0 &&
    (canvasRect?.width ?? 0) > 0 &&
    (canvasRect?.height ?? 0) > 0;
  const phase = hudVisible && menuHidden && deathHidden && killcamInactive &&
    canvasConnected && visibleOverlays.length === 0 && hp > 0
    ? 'playing'
    : 'not-playing';
  return {
    expectedStageId: stageId,
    selectedStageId,
    phase,
    hp,
    hudVisible,
    menuHidden,
    deathHidden,
    killcamInactive,
    canvasConnected,
    visibleOverlays,
    bootId: audit?.bootId ?? null,
    startSerial: audit?.startSerial ?? null,
    startMark: audit?.startMark ?? null,
    serial: audit?.serial ?? null,
    eventAt: audit?.eventAt ?? null,
    report: audit?.report ?? null,
    worldSerial: audit?.worldSerial ?? null,
    worldEventAt: audit?.worldEventAt ?? null,
    worldState: audit?.worldState ?? null,
  };
}, expectedStageId);

const assertInMatchGate = (gate, label, auditStart, baseline = null) => {
  const report = gate.report;
  const reportExact = report &&
    report.requested === 1 &&
    report.loaded === 1 &&
    report.failed === 0 &&
    Array.isArray(report.errors) &&
    report.errors.length === 0;
  const failures = [];
  if (gate.phase !== 'playing') failures.push(`phase=${gate.phase}`);
  if (gate.selectedStageId !== gate.expectedStageId) {
    failures.push(`stage=${gate.selectedStageId} expected=${gate.expectedStageId}`);
  }
  if (!reportExact) failures.push(`AAA=${JSON.stringify(report)}`);
  if (gate.bootId !== auditStart.bootId) failures.push('boot-changed');
  if (gate.startSerial !== auditStart.startSerial || gate.startMark !== auditStart.startMark) {
    failures.push('start-marker-changed');
  }
  if (gate.serial !== auditStart.startSerial + 1) {
    failures.push(`event-serial=${gate.serial} expected=${auditStart.startSerial + 1}`);
  }
  if (!(Number.isFinite(gate.eventAt) && gate.eventAt >= auditStart.startMark)) {
    failures.push(`stale-event-at=${gate.eventAt}`);
  }
  if (gate.worldSerial !== 1) failures.push(`world-event-serial=${gate.worldSerial}`);
  if (!(Number.isFinite(gate.worldEventAt) && gate.worldEventAt >= auditStart.startMark)) {
    failures.push(`stale-world-event-at=${gate.worldEventAt}`);
  }
  const world = gate.worldState;
  if (!world) {
    failures.push('stage-world-state-missing');
  } else {
    if (world.stageId !== gate.expectedStageId) failures.push(`world-stage=${world.stageId}`);
    if (world.tier !== quality) failures.push(`world-tier=${world.tier}`);
    if (world.externalRootCount !== 1) failures.push(`external-roots=${world.externalRootCount}`);
    if (world.externalRootVisibleCount !== 1) {
      failures.push(`visible-external-roots=${world.externalRootVisibleCount}`);
    }
    if (world.externalRootChildCount !== 1) {
      failures.push(`external-root-children=${world.externalRootChildCount}`);
    }
    for (const [field, value] of Object.entries({
      proceduralStageShellVisible: world.proceduralStageShellVisible,
      proceduralPropsVisible: world.proceduralPropsVisible,
      proceduralDecorVisible: world.proceduralDecorVisible,
      stageKitVisible: world.stageKitVisible,
    })) {
      if (value !== false) failures.push(`${field}=${value}`);
    }
    if (world.distantStageMatteVisible === true) failures.push('distantStageMatteVisible=true');
    for (const [field, value] of Object.entries(world.replacementFlags ?? {})) {
      if (value !== true) failures.push(`replacement-${field}=${value}`);
    }
    if (Object.keys(world.replacementFlags ?? {}).length !== 3) {
      failures.push('replacement-flags-incomplete');
    }
  }
  if (baseline && (gate.bootId !== baseline.bootId || gate.serial !== baseline.serial)) {
    failures.push('boot-or-event-serial-changed-before-capture');
  }
  if (baseline && (
    gate.eventAt !== baseline.eventAt ||
    JSON.stringify(gate.report) !== JSON.stringify(baseline.report) ||
    gate.worldEventAt !== baseline.worldEventAt ||
    JSON.stringify(gate.worldState) !== JSON.stringify(baseline.worldState)
  )) {
    failures.push('AAA-or-world-commit-changed-before-capture');
  }
  if (failures.length > 0) {
    throw new Error(`${label} gate failed: ${failures.join('; ')} state=${JSON.stringify(gate)}`);
  }
};

const visualScoreCategories = [
  {
    id: 'macro_composition',
    label: 'Macro composition and first-person readability',
  },
  {
    id: 'landmark_0_silhouette',
    label: 'Landmark 0 identity and castle-scale silhouette',
  },
  {
    id: 'landmark_1_silhouette',
    label: 'Landmark 1 identity and castle-scale silhouette',
  },
  {
    id: 'dense_settlement_horizon',
    label: 'Dense settlement and layered real-3D horizon',
  },
  {
    id: 'stage_exclusive_architecture',
    label: 'Stage-exclusive facade, roof, and skyline language',
  },
  {
    id: 'pbr_material_response',
    label: 'PBR material, relief, roughness, and contact response',
  },
  {
    id: 'entrance_structure',
    label: 'Entrance depth and structural credibility',
  },
  {
    id: 'interior_combat_verticality',
    label: 'Interior combat space, cover, routes, and verticality',
  },
  {
    id: 'set_dressing_story',
    label: 'Set dressing, vegetation, and environmental storytelling',
  },
  {
    id: 'lighting_color_atmosphere',
    label: 'Lighting, color separation, and atmosphere',
  },
];

const parsePerfHud = (text) => {
  if (typeof text !== 'string') {
    return { frameP50Ms: null, frameP95Ms: null, rendererInfoCalls: null };
  }
  const frame = /^p50\s+([0-9.]+)ms\s+p95\s+([0-9.]+)ms/m.exec(text);
  const calls = /^calls\s+([0-9]+)/m.exec(text);
  return {
    frameP50Ms: frame ? Number(frame[1]) : null,
    frameP95Ms: frame ? Number(frame[2]) : null,
    rendererInfoCalls: calls ? Number(calls[1]) : null,
  };
};

const stageWorldReplacementPasses = (world, expectedStageId) => Boolean(
  world &&
  world.stageId === expectedStageId &&
  world.tier === quality &&
  world.externalRootCount === 1 &&
  world.externalRootVisibleCount === 1 &&
  world.externalRootChildCount === 1 &&
  world.proceduralStageShellVisible === false &&
  world.proceduralPropsVisible === false &&
  world.proceduralDecorVisible === false &&
  world.stageKitVisible === false &&
  world.distantStageMatteVisible !== true &&
  world.replacementFlags?.distantWorld === true &&
  world.replacementFlags?.proceduralProps === true &&
  world.replacementFlags?.proceduralStageShell === true &&
  Object.keys(world.replacementFlags ?? {}).length === 3
);

let browser;
const results = [];
try {
  browser = await chromium.launch({
    channel: 'chromium',
    headless: true,
    args: [
      '--enable-unsafe-swiftshader',
      '--autoplay-policy=no-user-gesture-required',
      '--enable-precise-memory-info',
      ...SILENT_BROWSER_ARGS,
    ],
  });

  for (const stageId of stageIds) {
    const mode = /^z\d\d$/.test(stageId) ? 'zombie' : stageId === 'renshujo' ? 'training' : 'tdm';
    const errors = [];
    const context = await browser.newContext({ viewport: { width, height } });
    await context.addInitScript(installSilentAudio);
    // Command-level draw-call probe, matching the measurement method used by
    // hibana-real-benchmark. Unlike renderer.info, this includes every
    // post-processing pass in the browser frame.
    await context.addInitScript(() => {
      const probe = { frames: [], current: 0 };
      window.__hibanaStageDrawProbe = probe;
      const patch = (prototype, method) => {
        if (!prototype || typeof prototype[method] !== 'function') return;
        const original = prototype[method];
        if (original.__hibanaStageAuditPatched) return;
        const wrapped = function stageAuditPatchedDraw(...args) {
          probe.current += 1;
          return original.apply(this, args);
        };
        wrapped.__hibanaStageAuditPatched = true;
        prototype[method] = wrapped;
      };
      for (const prototype of [
        window.WebGLRenderingContext?.prototype,
        window.WebGL2RenderingContext?.prototype,
      ]) {
        for (const method of [
          'drawArrays',
          'drawElements',
          'drawArraysInstanced',
          'drawElementsInstanced',
        ]) patch(prototype, method);
      }
      const nativeRaf = window.requestAnimationFrame.bind(window);
      const sample = () => {
        probe.frames.push(probe.current);
        probe.current = 0;
        nativeRaf(sample);
      };
      nativeRaf(sample);
    });
    await context.addInitScript(() => {
      window.__hibanaAaaAssetReport = null;
      window.__hibanaAaaAssetAudit = {
        bootId: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
        serial: 0,
        startSerial: null,
        startMark: null,
        eventAt: null,
        report: null,
        worldSerial: 0,
        worldEventAt: null,
        worldState: null,
      };
      window.addEventListener('hibana:aaa-assets', (event) => {
        window.__hibanaAaaAssetReport = event.detail;
        const audit = window.__hibanaAaaAssetAudit;
        audit.serial += 1;
        audit.eventAt = performance.now();
        audit.report = event.detail;
      });
      window.addEventListener('hibana:stage-world-state', (event) => {
        const audit = window.__hibanaAaaAssetAudit;
        audit.worldSerial += 1;
        audit.worldEventAt = performance.now();
        audit.worldState = event.detail;
      });
    });
    await context.addInitScript(
      ({ selectedStageId, selectedMode, graphicsQuality }) => {
        let fakePointerLockElement = null;
        try {
          Object.defineProperty(document, 'pointerLockElement', {
            configurable: true,
            get: () => fakePointerLockElement,
          });
          Element.prototype.requestPointerLock = function requestPointerLockForWorldAudit() {
            fakePointerLockElement = document.querySelector('#app canvas') ?? document.documentElement;
            document.dispatchEvent(new Event('pointerlockchange'));
            return Promise.resolve();
          };
          document.exitPointerLock = () => {
            fakePointerLockElement = null;
            document.dispatchEvent(new Event('pointerlockchange'));
          };
        } catch {
          // 上書き不可環境はネイティブPointer Lockへフォールバック。
        }
        localStorage.setItem('hibana.profile.v1', JSON.stringify({
          xp: 99_999_999,
          weaponStats: { 'kaede-ar': { kills: 9999, headshots: 9999 } },
          selectedCamos: { 'kaede-ar': 'diamond' },
          charms: { unlocked: ['perkcarry'], equipped: 'perkcarry' },
        }));
        localStorage.setItem('hibana.loadout.v1', JSON.stringify({
          stageId: selectedStageId,
          mode: selectedMode,
          primaryId: 'kaede-ar',
          secondaryId: 'suzume',
          attachments: [],
          grenade: 'frag',
          difficulty: 'normal',
          missionDifficulty: 'normal',
          hellMode: false,
          allGiantMode: false,
          rogueRun: false,
          zombieStartRound: 1,
          charm: 'perkcarry',
        }));
        localStorage.setItem('hibana.zombie.lastPerk.v1', JSON.stringify('juggernog'));
        localStorage.setItem('hibana.settings.v1', JSON.stringify({
          graphicsQuality,
          masterVolume: 0,
          sfxVolume: 0,
          musicVolume: 0,
          announcerVolume: 0,
          screenShake: 0,
          reduceMotion: false,
          radarEnabled: false,
        }));
      },
      { selectedStageId: stageId, selectedMode: mode, graphicsQuality: quality },
    );

    const page = await context.newPage();
    if (assetRoot) {
      await page.route('**/assets/aaa/stages/*.glb', async (route) => {
        const filename = path.basename(new URL(route.request().url()).pathname);
        const localPath = path.join(assetRoot, filename);
        if (!existsSync(localPath)) {
          await route.abort('failed');
          return;
        }
        await route.fulfill({
          status: 200,
          contentType: 'model/gltf-binary',
          path: localPath,
        });
      });
    }
    const expectedAssetUrl = selectedAssetUrlByStage.get(stageId);
    const stageGlbRequests = [];
    const stageGlbResponses = [];
    const isStageGlbUrl = (requestUrl) => {
      const pathname = new URL(requestUrl).pathname;
      return pathname.includes('/assets/aaa/stages/') && pathname.endsWith('.glb');
    };
    page.on('request', (request) => {
      if (!isStageGlbUrl(request.url())) return;
      stageGlbRequests.push({
        url: request.url(),
        method: request.method(),
        resourceType: request.resourceType(),
      });
    });
    page.on('response', (response) => {
      if (!isStageGlbUrl(response.url())) return;
      stageGlbResponses.push({ url: response.url(), status: response.status() });
    });
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(`console: ${message.text()}`);
    });
    page.on('pageerror', (error) => errors.push(`pageerror: ${String(error)}`));
    const startedAt = performance.now();
    let ok = false;
    let auditStart = null;
    let initialGate = null;
    let finalGate = null;
    let postCaptureGate = null;
    let drawCalls = null;
    const landmarkCaptures = [];
    try {
      await page.goto(`${url}/?ui2&perfhud=1&stageaudit=1`, {
        waitUntil: 'domcontentloaded',
        timeout: 30_000,
      });
      await page.locator('[data-id="title-start"]').waitFor({ state: 'visible', timeout: 15_000 });
      await page.locator('[data-id="title-start"]').click();
      await page.locator('[data-id="hub-root"]').waitFor({ state: 'visible' });
      await page.locator('[data-id="hub-nav-deploy"]').click();
      await page.locator('[data-id="scr-deploy"]').waitFor({ state: 'visible' });
      auditStart = await page.evaluate(() => {
        const audit = window.__hibanaAaaAssetAudit;
        if (!audit) throw new Error('AAA audit state missing before match start');
        audit.startSerial = audit.serial;
        audit.startMark = performance.now();
        return {
          bootId: audit.bootId,
          startSerial: audit.startSerial,
          startMark: audit.startMark,
        };
      });
      if (auditStart.startSerial !== 0) {
        throw new Error(`unexpected AAA event before match start: ${auditStart.startSerial}`);
      }
      // Legacy menu markup also contains a hidden `[data-id="start"]` button.
      // Scope the synthetic keyboard-style click to the visible UI2 deploy
      // screen so a DOM-order change cannot silently launch the wrong control.
      await page
        .locator('[data-id="scr-deploy"] [data-id="start"]')
        .evaluate((element) => element.click());
      await page.locator('#hud:not([hidden])').waitFor({ state: 'visible', timeout: 50_000 });
      await page.waitForFunction(
        (startSerial) =>
          (window.__hibanaAaaAssetAudit?.serial ?? 0) > startSerial &&
          (window.__hibanaAaaAssetAudit?.worldSerial ?? 0) === 1,
        auditStart.startSerial,
        { timeout: 20_000 },
      );
      initialGate = await readInMatchGate(page, stageId);
      assertInMatchGate(initialGate, 'initial in-match', auditStart);
      await page.evaluate(() => {
        window.__hibanaStageDrawProbe.frames = [];
        window.__hibanaStageDrawProbe.current = 0;
      });
      await page.waitForTimeout(settleMs);
      // Optional deterministic first-person traversal for gate/interior QA.
      // Chromium remains headless and the global silent-audio shim stays active.
      if (strafeMs > 0) {
        await page.keyboard.down('d');
        await page.waitForTimeout(strafeMs);
        await page.keyboard.up('d');
      }
      if (walkMs > 0) {
        await page.keyboard.down('Shift');
        await page.keyboard.down('w');
        await page.waitForTimeout(walkMs);
        await page.keyboard.up('w');
        await page.keyboard.up('Shift');
      }
      await page.waitForTimeout(400);
      drawCalls = await page.evaluate(() => {
        const samples = window.__hibanaStageDrawProbe?.frames
          ?.filter((value) => Number.isFinite(value) && value > 0)
          ?.sort((a, b) => a - b) ?? [];
        const percentile = (q) => samples[Math.min(samples.length - 1, Math.floor(q * samples.length))] ?? null;
        return {
          samples: samples.length,
          min: samples[0] ?? null,
          p50: percentile(0.5),
          p95: percentile(0.95),
          max: samples.at(-1) ?? null,
        };
      });
      if (!(drawCalls.samples > 0 && drawCalls.p95 > 0)) {
        throw new Error(`draw-call probe failed: ${JSON.stringify(drawCalls)}`);
      }
      const expectedPath = `/assets/aaa/${expectedAssetUrl}`;
      const requestedPaths = stageGlbRequests.map((entry) => new URL(entry.url).pathname);
      const responsePaths = stageGlbResponses.map((entry) => new URL(entry.url).pathname);
      if (requestedPaths.length !== 1 || requestedPaths[0] !== expectedPath) {
        throw new Error(
          `stage GLB request mismatch: expected=${expectedPath} actual=${requestedPaths.join(',')}`,
        );
      }
      if (
        stageGlbResponses.length !== 1 ||
        responsePaths[0] !== expectedPath ||
        stageGlbResponses[0].status !== 200
      ) {
        throw new Error(
          `stage GLB response mismatch: expected=${expectedPath}/200` +
          ` actual=${JSON.stringify(stageGlbResponses)}`,
        );
      }
      // A source edit/HMR, match teardown, or accidental return to title can
      // otherwise produce a perfectly valid PNG and a false-positive `ok`.
      // Reassert the real in-match gate immediately before evidence capture.
      await page.locator('#hud:not([hidden])').waitFor({ state: 'visible', timeout: 2_000 });
      finalGate = await readInMatchGate(page, stageId);
      assertInMatchGate(finalGate, 'final pre-capture', auditStart, initialGate);
      await page.screenshot({ path: path.join(output, `${stageId}.png`) });
      if (landmarkPoses) {
        const placements = stageLayoutById.get(stageId).landmarkPlacements;
        for (const [landmarkIndex, placement] of placements.entries()) {
          const start = placement.approach.start;
          const end = placement.approach.end;
          const dx = end[0] - start[0];
          const dz = end[1] - start[1];
          const length = Math.hypot(dx, dz);
          if (!(length > 0)) throw new Error(`${placement.id}: degenerate approach`);
          const ux = dx / length;
          const uz = dz / length;
          const poses = [
            {
              name: 'approach',
              position: start,
              target: [end[0] + ux * 8, end[1] + uz * 8],
            },
            {
              name: 'threshold',
              position: [end[0] - ux * 5.5, end[1] - uz * 5.5],
              target: [end[0] + ux * 10, end[1] + uz * 10],
            },
            {
              name: 'interior',
              position: [end[0] + ux * 10, end[1] + uz * 10],
              target: [end[0] + ux * 22, end[1] + uz * 22],
            },
          ];
          for (const pose of poses) {
            const requested = await page.evaluate(
              ({ position, target }) =>
                window.__hibanaStageAudit?.setPose(
                  position[0],
                  position[1],
                  target[0],
                  target[1],
                ) ?? null,
              pose,
            );
            if (!requested) throw new Error(`${placement.id}/${pose.name}: stage audit pose unavailable`);
            await page.waitForTimeout(350);
            const observed = await page.evaluate(() => window.__hibanaStageAudit?.snapshot() ?? null);
            if (!observed) throw new Error(`${placement.id}/${pose.name}: stage audit snapshot unavailable`);
            const driftM = Math.hypot(
              observed.x - pose.position[0],
              observed.z - pose.position[1],
            );
            const filename = `${stageId}-landmark-${landmarkIndex}-${pose.name}.png`;
            await page.screenshot({ path: path.join(output, filename) });
            landmarkCaptures.push({
              landmarkIndex,
              landmarkId: placement.id,
              pose: pose.name,
              requested: { position: pose.position, target: pose.target },
              observed,
              driftM,
              screenshot: filename,
            });
          }
        }
      }
      postCaptureGate = await readInMatchGate(page, stageId);
      assertInMatchGate(postCaptureGate, 'post-capture', auditStart, finalGate);
      ok = true;
    } catch (error) {
      errors.push(`audit: ${String(error)}`);
    }
    const perfhud = await page.locator('#perfhud').textContent().catch(() => null);
    const heap = await page.evaluate(() => {
      const memory = performance.memory;
      return memory ? { used: memory.usedJSHeapSize, total: memory.totalJSHeapSize } : null;
    }).catch(() => null);
    const aaaAssets = await page.evaluate(() => window.__hibanaAaaAssetReport).catch(() => null);
    results.push({
      stageId,
      mode,
      ok,
      elapsedMs: Math.round(performance.now() - startedAt),
      perfhud,
      heap,
      aaaAssets,
      expectedAssetUrl,
      stageGlbRequests,
      stageGlbResponses,
      drawCalls,
      landmarkCaptures,
      auditStart,
      initialGate,
      finalGate,
      postCaptureGate,
      errors,
    });
    await context.close();
    process.stdout.write(`${ok && errors.length === 0 ? 'OK' : 'NG'} ${stageId}\n`);
  }
} finally {
  await browser?.close();
  vite.kill('SIGTERM');
}

const report = {
  generatedAt: new Date().toISOString(),
  quality,
  viewport: viewportName,
  assetRoot: assetRoot || null,
  landmarkPoses,
  traversal: { walkMs, strafeMs },
  stages: results.length,
  passed: results.filter((entry) => entry.ok && entry.errors.length === 0).length,
  failed: results.filter((entry) => !entry.ok || entry.errors.length > 0).length,
  results,
};
writeFileSync(path.join(output, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);

const scorecardInputs = {
  schemaVersion: 1,
  generatedAt: report.generatedAt,
  evidenceRoot: path.resolve(output),
  quality,
  viewport: viewportName,
  assetRoot: assetRoot || null,
  landmarkPoses,
  scoringPolicy: {
    automatedFieldsAreEvidenceOnly: true,
    visualScoresRequireHumanReview: true,
    visualScoreRange: { min: 0, max: 10 },
    shipRule: 'Do not infer visual quality from runtime or performance passes.',
  },
  stages: results.map((entry) => {
    const expectedAssetPath = `/assets/aaa/${entry.expectedAssetUrl}`;
    const effectiveAssetPath = assetRoot
      ? path.join(assetRoot, path.basename(expectedAssetPath))
      : path.resolve('public/assets/aaa', entry.expectedAssetUrl);
    const effectiveAssetExists = existsSync(effectiveAssetPath);
    const effectiveAssetStat = effectiveAssetExists ? statSync(effectiveAssetPath) : null;
    const effectiveAssetSha256 = effectiveAssetExists
      ? createHash('sha256').update(readFileSync(effectiveAssetPath)).digest('hex')
      : null;
    const conceptReference = `tools/blender/concepts/${entry.stageId}-reference-v1.png`;
    const requestPaths = entry.stageGlbRequests.map((request) => new URL(request.url).pathname);
    const responsePaths = entry.stageGlbResponses.map((response) => new URL(response.url).pathname);
    const httpPass = requestPaths.length === 1 &&
      requestPaths[0] === expectedAssetPath &&
      responsePaths.length === 1 &&
      responsePaths[0] === expectedAssetPath &&
      entry.stageGlbResponses[0]?.status === 200;
    const expectedPoseCaptureCount = landmarkPoses ? 6 : 0;
    const landmarkIds = [...new Set(entry.landmarkCaptures.map((capture) => capture.landmarkId))];
    const landmarkIndexes = [...new Set(entry.landmarkCaptures.map((capture) => capture.landmarkIndex))]
      .sort((a, b) => a - b);
    const requiredPoseNames = ['approach', 'threshold', 'interior'];
    const completeLandmarkPoses = landmarkPoses &&
      landmarkIndexes.length === 2 &&
      landmarkIndexes[0] === 0 &&
      landmarkIndexes[1] === 1 &&
      landmarkIds.length === 2 &&
      entry.landmarkCaptures.length === expectedPoseCaptureCount &&
      landmarkIndexes.every((landmarkIndex) => {
        const observed = entry.landmarkCaptures
          .filter((capture) => capture.landmarkIndex === landmarkIndex)
          .map((capture) => capture.pose)
          .sort();
        return JSON.stringify(observed) === JSON.stringify([...requiredPoseNames].sort());
      });
    const allGrounded = entry.landmarkCaptures.length > 0
      ? entry.landmarkCaptures.every((capture) => capture.observed?.grounded === true)
      : null;
    const finiteDrifts = entry.landmarkCaptures
      .map((capture) => capture.driftM)
      .filter(Number.isFinite);
    const maxHorizontalDriftM = finiteDrifts.length > 0 ? Math.max(...finiteDrifts) : null;
    const poseGatePass = landmarkPoses
      ? completeLandmarkPoses && allGrounded === true && maxHorizontalDriftM <= 0.01
      : null;
    const frame = parsePerfHud(entry.perfhud);
    const worldState = entry.finalGate?.worldState ?? null;
    const aaaAssetReportPass = entry.aaaAssets?.requested === 1 &&
      entry.aaaAssets?.loaded === 1 &&
      entry.aaaAssets?.failed === 0 &&
      Array.isArray(entry.aaaAssets?.errors) &&
      entry.aaaAssets.errors.length === 0;
    const spawnScreenshot = `${entry.stageId}.png`;
    return {
      stageId: entry.stageId,
      mode: entry.mode,
      conceptReference,
      conceptReferenceExists: existsSync(path.resolve(conceptReference)),
      automatedVerdict: {
        runtimePass: entry.ok && entry.errors.length === 0,
        httpPass,
        aaaAssetReportPass,
        stageWorldReplacementPass: stageWorldReplacementPasses(worldState, entry.stageId),
        poseGatePass,
        visualReviewStatus: 'pending-human-review',
      },
      evidence: {
        spawn: {
          screenshot: spawnScreenshot,
          exists: existsSync(path.join(output, spawnScreenshot)),
        },
        landmarks: entry.landmarkCaptures.map((capture) => ({
          ...capture,
          screenshotExists: existsSync(path.join(output, capture.screenshot)),
        })),
      },
      poseContract: {
        requested: landmarkPoses,
        expectedLandmarks: landmarkPoses ? 2 : null,
        observedLandmarkIds: landmarkIds,
        observedLandmarkIndexes: landmarkIndexes,
        requiredPosesPerLandmark: landmarkPoses ? requiredPoseNames : [],
        expectedCaptureCount: expectedPoseCaptureCount,
        observedCaptureCount: entry.landmarkCaptures.length,
        complete: landmarkPoses ? completeLandmarkPoses : null,
        allGrounded,
        maxHorizontalDriftM,
        toleranceM: landmarkPoses ? 0.01 : null,
      },
      http: {
        expectedAssetPath,
        requests: entry.stageGlbRequests,
        responses: entry.stageGlbResponses,
      },
      assetProvenance: {
        routedFromOverride: Boolean(assetRoot),
        effectivePath: effectiveAssetPath,
        exists: effectiveAssetExists,
        bytes: effectiveAssetStat?.size ?? null,
        modifiedAt: effectiveAssetStat?.mtime.toISOString() ?? null,
        sha256: effectiveAssetSha256,
      },
      runtime: {
        elapsedMs: entry.elapsedMs,
        errors: entry.errors,
        aaaAssets: entry.aaaAssets,
        initialGate: entry.initialGate,
        finalGate: entry.finalGate,
        postCaptureGate: entry.postCaptureGate,
        worldState,
      },
      performance: {
        ...frame,
        commandDrawCalls: entry.drawCalls,
        javascriptHeapBytes: entry.heap,
        rawPerfHud: entry.perfhud,
      },
      visualScores: visualScoreCategories.map((category) => {
        const landmarkIndex = category.id === 'landmark_0_silhouette'
          ? 0
          : category.id === 'landmark_1_silhouette'
            ? 1
            : null;
        return {
          ...category,
          subjectLandmarkId: landmarkIndex === null ? null : landmarkIds[landmarkIndex] ?? null,
          score: null,
          notes: null,
        };
      }),
    };
  }),
};
writeFileSync(
  path.join(output, 'scorecard-inputs.json'),
  `${JSON.stringify(scorecardInputs, null, 2)}\n`,
);
console.log(JSON.stringify({ stages: report.stages, passed: report.passed, failed: report.failed }, null, 2));
if (report.failed > 0) process.exitCode = 1;
