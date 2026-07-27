/*
 * Blender製敵兵の実ゲーム統合監査。
 *
 * - headless / background / muted のみ。OSの画面やフォーカスは奪わない。
 * - high/medium × TDM/FFA/S&Dでmanifest、3 LOD、6 variants、fail-openを確認。
 * - high TDMで14 clips、3 LOD切替、一人称final killcam継続を実sceneから監査。
 * - PNG/JSONはtools/blender/screenshots以下のignored監査証跡だけに書く。
 *
 *   node e2e/enemy-browser-audit.mjs
 *   node e2e/enemy-browser-audit.mjs --output=/tmp/hibana-enemy-audit
 */
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { installSilentAudio, SILENT_BROWSER_ARGS } from './silence-audio.mjs';

const args = process.argv.slice(2);
const val = (key, fallback) =>
  (args.find((arg) => arg.startsWith(`${key}=`)) ?? '').split('=').slice(1).join('=') || fallback;
const output = path.resolve(val('--output', 'tools/blender/screenshots/054-enemy-browser-audit'));
const port = Number(val('--port', '5254'));
const viewportName = val('--viewport', '1440x900');
const onlyCase = val('--case', '');
const [width, height] = viewportName.split('x').map(Number);
if (!Number.isFinite(width) || !Number.isFinite(height)) throw new Error(`bad viewport: ${viewportName}`);
mkdirSync(output, { recursive: true });

const manifest = JSON.parse(readFileSync('public/assets/aaa/enemies/manifest.json', 'utf8'));
const variants = manifest.variants;
const clips = manifest.animations;
const lods = manifest.lods;
if (!Array.isArray(variants) || variants.length !== 6 || new Set(variants).size !== 6) {
  throw new Error('enemy audit requires exactly six manifest variants');
}
if (!Array.isArray(clips) || clips.length !== 14 || new Set(clips).size !== 14) {
  throw new Error('enemy audit requires exactly fourteen manifest clips');
}
if (!Array.isArray(lods) || lods.length !== 3 || lods.some((lod, index) => lod.level !== index)) {
  throw new Error('enemy audit requires ordered LOD0/1/2 manifest entries');
}

const allCases = [
  { id: 'tdm-high', mode: 'tdm', quality: 'high', deep: true },
  { id: 'tdm-medium', mode: 'tdm', quality: 'medium', deep: false },
  { id: 'ffa-high', mode: 'ffa', quality: 'high', deep: false },
  { id: 'ffa-medium', mode: 'ffa', quality: 'medium', deep: false },
  { id: 'snd-high', mode: 'snd', quality: 'high', deep: false },
  { id: 'snd-medium', mode: 'snd', quality: 'medium', deep: false },
];
const cases = onlyCase
  ? allCases.filter((auditCase) => auditCase.id === onlyCase)
  : allCases;
if (onlyCase && cases.length !== 1) throw new Error(`unknown audit case: ${onlyCase}`);

const viteEntry = path.resolve('node_modules/vite/bin/vite.js');
const vite = spawn(process.execPath, [viteEntry, '--port', String(port), '--strictPort'], {
  cwd: process.cwd(),
  stdio: ['ignore', 'ignore', 'ignore'],
});
let viteExit = null;
vite.once('exit', (code, signal) => {
  viteExit = { code, signal };
});
const base = `http://localhost:${port}`;
const deadline = Date.now() + 60_000;
let viteReady = false;
while (Date.now() < deadline) {
  if (viteExit) throw new Error(`vite dev exited before readiness: ${JSON.stringify(viteExit)}`);
  try {
    const response = await fetch(base);
    if (response.ok) {
      viteReady = true;
      break;
    }
  } catch {
    // Vite起動待ち。
  }
  await new Promise((resolve) => setTimeout(resolve, 250));
}
if (!viteReady) {
  vite.kill('SIGTERM');
  throw new Error('vite dev did not start');
}

const failures = [];
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const actorByUid = (snapshot, uid) => snapshot?.actors?.find((actor) => actor.uid === uid) ?? null;

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

  for (const auditCase of cases) {
    const caseOutput = path.join(output, auditCase.id);
    mkdirSync(caseOutput, { recursive: true });
    const context = await browser.newContext({ viewport: { width, height } });
    await context.addInitScript(installSilentAudio);
    await context.addInitScript(
      ({ mode, quality }) => {
        let fakePointerLockElement = null;
        try {
          Object.defineProperty(document, 'pointerLockElement', {
            configurable: true,
            get: () => fakePointerLockElement,
          });
          Element.prototype.requestPointerLock = function requestPointerLockForEnemyAudit() {
            fakePointerLockElement = document.querySelector('#app canvas') ?? document.documentElement;
            document.dispatchEvent(new Event('pointerlockchange'));
            return Promise.resolve();
          };
          document.exitPointerLock = () => {
            fakePointerLockElement = null;
            document.dispatchEvent(new Event('pointerlockchange'));
          };
        } catch {
          // 上書き不可環境はChromiumの実Pointer Lockへfail-open。
        }
        localStorage.setItem('hibana.profile.v1', JSON.stringify({
          xp: 99_999_999,
          weaponStats: { 'kaede-ar': { kills: 9999, headshots: 9999 } },
          selectedCamos: { 'kaede-ar': 'diamond' },
        }));
        localStorage.setItem('hibana.loadout.v1', JSON.stringify({
          stageId: 'kunren',
          mode,
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
        }));
        localStorage.setItem('hibana.settings.v1', JSON.stringify({
          graphicsQuality: quality,
          volMaster: 0,
          volSfx: 0,
          volUi: 0,
          musicVolume: 0,
          voVolume: 0,
          masterVolume: 0,
          sfxVolume: 0,
          announcerVolume: 0,
          screenShake: 0,
          reduceMotion: false,
          radarEnabled: false,
        }));
        window.__hibanaEnemyAssetEvents = [];
        window.addEventListener('hibana:enemy-assets', (event) => {
          window.__hibanaEnemyAssetEvents.push({ at: performance.now(), detail: event.detail });
        });
      },
      { mode: auditCase.mode, quality: auditCase.quality },
    );

    const page = await context.newPage();
    const errors = [];
    const requests = [];
    const responses = [];
    const isEnemyAsset = (url) => new URL(url).pathname.includes('/assets/aaa/enemies/');
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(`console: ${message.text()}`);
    });
    page.on('pageerror', (error) => errors.push(`pageerror: ${String(error)}`));
    page.on('request', (request) => {
      if (isEnemyAsset(request.url())) requests.push(new URL(request.url()).pathname);
    });
    page.on('response', (response) => {
      if (isEnemyAsset(response.url())) {
        responses.push({ path: new URL(response.url()).pathname, status: response.status() });
      }
    });

    const result = {
      ...auditCase,
      ok: false,
      eventReport: null,
      initial: null,
      variantEvidence: [],
      clipEvidence: [],
      lodEvidence: [],
      killcamEvidence: [],
      requests,
      responses,
      errors,
    };
    try {
      await page.goto(`${base}/?ui2&perfhud=1&enemyaudit=1&fkdemo=1`, {
        waitUntil: 'domcontentloaded',
        timeout: 30_000,
      });
      await page.locator('[data-id="title-start"]').waitFor({ state: 'visible', timeout: 15_000 });
      await page.locator('[data-id="title-start"]').click();
      await page.locator('[data-id="hub-root"]').waitFor({ state: 'visible' });
      await page.locator('[data-id="hub-nav-deploy"]').click();
      await page.locator('[data-id="scr-deploy"]').waitFor({ state: 'visible' });
      // The legacy menu remains mounted and also owns a hidden start control.
      // Always click the launch button inside the visible UI2 deployment
      // screen; an unscoped selector can silently send the audit back through
      // the legacy title flow and leave the HUD wait hanging for a minute.
      await page
        .locator('[data-id="scr-deploy"] [data-id="start"]')
        .evaluate((element) => element.click());
      await page.locator('#hud:not([hidden])').waitFor({ state: 'visible', timeout: 60_000 });
      await page.waitForFunction(() => {
        const report = window.__hibanaEnemyAssetEvents?.at(-1)?.detail;
        // Stop immediately on a fail-open report as well. Waiting only for
        // ready=true hides the structural GLB error behind a generic timeout.
        return Boolean(report) && (
          report.ready === false || window.__hibanaEnemyAudit?.snapshot()?.ready === true
        );
      }, null, { timeout: 30_000 });
      await page.waitForTimeout(350);

      result.eventReport = await page.evaluate(() => window.__hibanaEnemyAssetEvents.at(-1)?.detail ?? null);
      result.initial = await page.evaluate(() => window.__hibanaEnemyAudit.snapshot());
      const snapshot = result.initial;
      assert(result.eventReport?.ready === true, 'enemy asset report not ready');
      assert(result.eventReport?.sourceLods === 3, `sourceLods=${result.eventReport?.sourceLods}`);
      assert(result.eventReport?.variants === 6, `report variants=${result.eventReport?.variants}`);
      assert(result.eventReport?.failedActors === 0, `failedActors=${result.eventReport?.failedActors}`);
      assert(Array.isArray(result.eventReport?.errors) && result.eventReport.errors.length === 0,
        `asset errors=${JSON.stringify(result.eventReport?.errors)}`);
      assert(snapshot?.ready === true, 'scene snapshot not ready');
      assert(snapshot.sourceLods === 3, `scene sourceLods=${snapshot.sourceLods}`);
      assert(snapshot.sourceVariants === 6, `scene sourceVariants=${snapshot.sourceVariants}`);
      assert(snapshot.actorCount > 0 && snapshot.actorCount === result.eventReport.actors,
        `actor count scene=${snapshot.actorCount} report=${result.eventReport.actors}`);
      assert(snapshot.actors.every((actor) => actor.externalParented), 'externalEnemyVisual missing');
      const liveActors = snapshot.actors.filter((actor) => actor.alive);
      const individuallyRendered = liveActors.filter((actor) => actor.crowdSlot < 0);
      const crowdRendered = liveActors.filter((actor) => actor.crowdSlot >= 0);
      assert(individuallyRendered.every((actor) => actor.externalVisible),
        'an individually rendered actor did not show its authored GLB');
      assert(crowdRendered.every((actor) => !actor.externalVisible),
        'an authored GLB remained visible while the crowd renderer owned the actor');
      // S&D can begin with every hostile at the distant team spawn, so all of
      // them legitimately use crowd slots until the two teams close distance.
      // TDM/FFA must exercise at least one individually rendered GLB at start.
      if (auditCase.mode !== 'snd') {
        assert(individuallyRendered.length > 0,
          'no individually rendered authored enemy is active');
      } else {
        assert(individuallyRendered.length > 0 || crowdRendered.length === liveActors.length,
          'S&D actor has neither an individual nor crowd rendering owner');
      }
      assert(snapshot.actors.every((actor) => actor.proceduralRigVisible === false),
        'procedural rig remained visible after external commit');
      assert(snapshot.actors.every((actor) =>
        actor.skinnedMeshesPerLod.length === 3 && actor.skinnedMeshesPerLod.every((count) => count > 0)),
      'actor has an empty authored variant root in at least one LOD');
      assert(snapshot.actors.every((actor) =>
        actor.visibleLods.length === 1 && actor.visibleLods[0] === actor.lodIndex),
      'actor has zero or multiple visible LOD roots');
      if (auditCase.mode === 'tdm') {
        assert(variants.every((variant) => snapshot.variants.includes(variant)),
          `TDM did not integrate all variants: ${snapshot.variants.join(',')}`);
      }
      const expectedFiles = ['manifest.json', ...lods.map((lod) => lod.url)];
      for (const filename of expectedFiles) {
        assert(requests.some((requestPath) => requestPath.endsWith(`/enemies/${filename}`)),
          `request missing ${filename}`);
        assert(responses.some((response) =>
          response.path.endsWith(`/enemies/${filename}`) && response.status === 200),
        `HTTP 200 missing ${filename}`);
      }
      assert(errors.length === 0, `browser errors before capture: ${errors.join('; ')}`);
      await page.screenshot({ path: path.join(caseOutput, 'integrated-match.png') });

      if (auditCase.deep) {
        // Six role silhouettes: use the exact integrated LOD0 root, framed only
        // by the query-gated audit adapter. AI, physics and hitboxes stay put.
        for (const variant of variants) {
          const uid = await page.evaluate(
            ({ variantId }) => window.__hibanaEnemyAudit.playClip(
              'AN_Soldier_Aim', variantId, 1.2, 0.35, 0, 3.25,
            ),
            { variantId: variant },
          );
          assert(Number.isInteger(uid), `could not frame ${variant}`);
          await page.waitForTimeout(80);
          const front = await page.evaluate(() => window.__hibanaEnemyAudit.snapshot());
          const frontActor = actorByUid(front, uid);
          assert(frontActor?.variantId === variant, `${variant} selected wrong actor`);
          assert(frontActor.debugFramed && frontActor.inView && frontActor.lodIndex === 0,
            `${variant} front framing failed`);
          await page.screenshot({ path: path.join(caseOutput, `variant-${variant}-front.png`) });

          const obliqueUid = await page.evaluate(
            ({ actorUid }) => window.__hibanaEnemyAudit.frameActor(actorUid, 32, 3.25, 1.1, false),
            { actorUid: uid },
          );
          assert(obliqueUid === uid, `${variant} oblique selected a different actor`);
          await page.waitForTimeout(80);
          const oblique = await page.evaluate(() => window.__hibanaEnemyAudit.snapshot());
          const obliqueActor = actorByUid(oblique, uid);
          assert(obliqueActor?.debugFramed && obliqueActor.inView,
            `${variant} oblique framing failed`);
          result.variantEvidence.push({ variant, uid, front: frontActor, oblique: obliqueActor });
          await page.screenshot({ path: path.join(caseOutput, `variant-${variant}-oblique.png`) });
        }

        const riflemanEvidence = result.variantEvidence.find(
          (evidence) => evidence.variant === 'rifleman',
        );
        const clipUid = riflemanEvidence?.uid;
        assert(Number.isInteger(clipUid), 'rifleman clip actor missing');
        for (let index = 0; index < clips.length; index += 1) {
          const clip = clips[index];
          const uid = await page.evaluate(
            ({ clipName, actorUid }) => window.__hibanaEnemyAudit.playClip(
              clipName, 'rifleman', 1.25, 0, 0, 3.25, actorUid,
            ),
            { clipName: clip, actorUid: clipUid },
          );
          assert(uid === clipUid, `${clip} selected a different actor ${uid}/${clipUid}`);
          await page.waitForTimeout(55);
          const start = await page.evaluate(() => window.__hibanaEnemyAudit.snapshot());
          const startActor = actorByUid(start, uid);
          assert(startActor?.currentClip === clip, `${clip} did not commit at start`);
          assert(startActor.debugFramed && startActor.inView && startActor.lodIndex === 0,
            `${clip} start is not visibly framed at LOD0`);
          await page.screenshot({
            path: path.join(caseOutput,
              `clip-${String(index + 1).padStart(2, '0')}-${clip}-start.png`),
          });

          const midUid = await page.evaluate(
            ({ clipName, actorUid }) => window.__hibanaEnemyAudit.playClip(
              clipName, 'rifleman', 1.25, 0.45, 0, 3.25, actorUid,
            ),
            { clipName: clip, actorUid: clipUid },
          );
          assert(midUid === clipUid, `${clip} midpoint selected a different actor`);
          await page.waitForTimeout(55);
          const mid = await page.evaluate(() => window.__hibanaEnemyAudit.snapshot());
          const midActor = actorByUid(mid, uid);
          assert(midActor?.currentClip === clip, `${clip} was replaced before midpoint`);
          assert(midActor.actionDurationS > 0, `${clip} duration is zero`);
          assert(midActor.actionTimeS > midActor.actionDurationS * 0.4,
            `${clip} did not reach its middle pose`);
          assert(midActor.externalParented && !midActor.proceduralRigVisible,
            `${clip} lost external/procedural exclusivity`);
          assert(midActor.debugFramed && midActor.inView && midActor.lodIndex === 0,
            `${clip} midpoint is not visibly framed at LOD0`);
          result.clipEvidence.push({ clip, uid, start: startActor, mid: midActor });
          await page.screenshot({
            path: path.join(caseOutput,
              `clip-${String(index + 1).padStart(2, '0')}-${clip}-mid.png`),
          });
        }

        const lodClipUid = await page.evaluate(
          ({ actorUid }) => window.__hibanaEnemyAudit.playClip(
            'AN_Soldier_WalkForward', 'rifleman', 3, 0.15, 0, 3.25, actorUid,
          ),
          { actorUid: clipUid },
        );
        assert(lodClipUid === clipUid, 'LOD continuity actor missing');
        for (const level of [0, 1, 2]) {
          const uid = await page.evaluate(
            ({ lodLevel }) => window.__hibanaEnemyAudit.forceLod(lodLevel, undefined, 0.8),
            { lodLevel: level },
          );
          assert(uid === clipUid, `LOD${level} selected a different actor ${uid}/${clipUid}`);
          await page.waitForTimeout(130);
          const lodSnapshot = await page.evaluate(() => window.__hibanaEnemyAudit.snapshot());
          const actor = actorByUid(lodSnapshot, uid);
          assert(actor?.lodIndex === level, `LOD${level} did not activate`);
          assert(actor.debugFramed && actor.inView, `LOD${level} is not visibly framed`);
          assert(actor.visibleLods.length === 1 && actor.visibleLods[0] === level,
            `LOD${level} visibility=${actor?.visibleLods}`);
          assert(actor.currentClip === 'AN_Soldier_WalkForward',
            `animation continuity broke at LOD${level}: ${actor.currentClip}`);
          assert(actor.actionTimeS > 0, `LOD${level} action time did not advance`);
          result.lodEvidence.push({ level, uid, actor });
          await page.screenshot({ path: path.join(caseOutput, `lod-${level}.png`) });
        }

        await page.waitForTimeout(900);
        const liveBeforeKillcam = await page.evaluate(() => window.__hibanaEnemyAudit.snapshot());
        const preferredVictim = actorByUid(liveBeforeKillcam, clipUid)?.alive
          ? clipUid
          : liveBeforeKillcam.actors.find((actor) => actor.alive)?.uid;
        assert(Number.isInteger(preferredVictim), 'killcam victim missing');
        const framedVictim = await page.evaluate(
          ({ actorUid }) => window.__hibanaEnemyAudit.frameActor(actorUid, 0, 3.25, 15, true),
          { actorUid: preferredVictim },
        );
        assert(framedVictim === preferredVictim, 'killcam victim framing failed');
        const forced = await page.evaluate(
          ({ actorUid }) => window.__fkDemo?.(actorUid) ?? false,
          { actorUid: preferredVictim },
        );
        assert(forced === true, 'first-person final killcam could not be forced');
        await page.waitForFunction(() => document.body.classList.contains('killcam-active'), null, {
          timeout: 5_000,
        });
        const killcamDeadline = Date.now() + 11_000;
        let sawReplay = false;
        let sawReplayDeath = false;
        let sawReadableReplayDeath = false;
        let sampleIndex = 0;
        while (Date.now() < killcamDeadline) {
          const sample = await page.evaluate(() => ({
            active: document.body.classList.contains('killcam-active'),
            snapshot: window.__hibanaEnemyAudit.snapshot(),
          }));
          const replayActors = sample.snapshot?.actors?.filter((actor) => actor.killcamReplay) ?? [];
          if (sample.active) {
            assert(sample.snapshot?.killcamPlaying === true,
              'killcam UI became active without the replay controller');
            assert(sample.snapshot?.killcamFirstPerson === true,
              'forced player final kill did not use the first-person replay path');
          }
          if (replayActors.length > 0) sawReplay = true;
          if (replayActors.some((actor) =>
            actor.killcamDeath01 > 0 &&
            (actor.currentClip === 'AN_Soldier_DeathFront' || actor.currentClip === 'AN_Soldier_DeathBack'))) {
            sawReplayDeath = true;
          }
          if (replayActors.some((actor) =>
            actor.killcamDeath01 >= 0.35 &&
            (actor.currentClip === 'AN_Soldier_DeathFront' || actor.currentClip === 'AN_Soldier_DeathBack'))) {
            sawReadableReplayDeath = true;
          }
          const victim = actorByUid(sample.snapshot, preferredVictim);
          if (victim?.killcamReplay) {
            assert(victim.debugFramed && victim.inView,
              'killcam victim is not readable in the captured first-person frame');
          }
          assert(sample.snapshot?.actors?.every((actor) =>
            actor.externalParented && actor.proceduralRigVisible === false),
          'killcam lost external rig continuity');
          result.killcamEvidence.push({ atMs: sampleIndex * 200, ...sample });
          if (sampleIndex === 0 || sawReadableReplayDeath) {
            await page.screenshot({
              path: path.join(caseOutput,
                sawReadableReplayDeath ? 'killcam-death.png' : 'killcam-entry.png'),
            });
          }
          if (sawReadableReplayDeath) break;
          if (!sample.active && sampleIndex > 2) break;
          sampleIndex += 1;
          await page.waitForTimeout(200);
        }
        assert(sawReplay, 'killcam never replayed an integrated enemy actor');
        assert(sawReplayDeath, 'killcam never reached the authored enemy death clip');
        assert(sawReadableReplayDeath,
          'killcam death clip never reached a visually reviewable pose (>=35%)');
      }

      assert(errors.length === 0, `browser errors: ${errors.join('; ')}`);
      result.ok = true;
    } catch (error) {
      const text = String(error);
      errors.push(`audit: ${text}`);
      failures.push(`${auditCase.id}: ${text}`);
      await page.screenshot({ path: path.join(caseOutput, 'failure.png') }).catch(() => undefined);
    }
    results.push(result);
    writeFileSync(path.join(caseOutput, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
    await context.close();
    process.stdout.write(`${result.ok && errors.length === 0 ? 'OK' : 'NG'} ${auditCase.id}\n`);
    await sleep(100);
  }
} finally {
  await browser?.close();
  vite.kill('SIGTERM');
}

const report = {
  headless: true,
  muted: true,
  viewport: viewportName,
  cases: results.length,
  passed: results.filter((result) => result.ok && result.errors.length === 0).length,
  failed: results.filter((result) => !result.ok || result.errors.length > 0).length,
  variants,
  clips,
  results,
  failures,
};
writeFileSync(path.join(output, 'report.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ cases: report.cases, passed: report.passed, failed: report.failed }, null, 2));
if (report.failed > 0) process.exitCode = 1;
