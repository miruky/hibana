/*
 * 全武器の一人称腕／射撃／ADS／リロードと、クナイ4形態を実ブラウザで直列監査する。
 * GPU競合を避けるため試合は必ず1つずつ起動し、visual-audit の無音・headless契約を継承する。
 *
 * 例:
 *   node e2e/weapon-arm-audit.mjs --output=/tmp/hibana-weapon-arms
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';

const args = process.argv.slice(2);
const val = (key, fallback) =>
  (args.find((arg) => arg.startsWith(`${key}=`)) ?? '').split('=').slice(1).join('=') || fallback;

const output = path.resolve(val('--output', '/tmp/hibana-weapon-arm-audit'));
const port = Number(val('--port', '5231'));
const quality = val('--quality', 'high');
const viewport = val('--viewport', '1440x900');
const reloadFrames = Number(val('--reload-frames', '6'));
const reloadFrameMs = Number(val('--reload-frame-ms', '180'));
const reloadKind = val('--reload-kind', 'tactical');
const camoId = val('--camo', 'gold');
const settleMs = Number(val('--settle-ms', '900'));
const sampleFrames = Number(val('--frames', '10'));
const maxAttempts = Number(val('--max-attempts', '3'));
if (!Number.isInteger(maxAttempts) || maxAttempts < 1 || maxAttempts > 5) {
  throw new Error('bad max attempts');
}
if (!['tactical', 'empty'].includes(reloadKind)) throw new Error('bad reload kind');

const weaponSource = readFileSync(path.resolve('src/game/weapons.ts'), 'utf8');
const weaponIds = Array.from(
  weaponSource.matchAll(/^\s+id:\s*'([^']+)',/gm),
  (match) => match[1],
);
const weaponFilter = val('--weapons', '');
const selectedWeaponIds = weaponFilter
  ? weaponFilter.split(',').map((weaponId) => weaponId.trim()).filter(Boolean)
  : weaponIds;
for (const weaponId of selectedWeaponIds) {
  if (!weaponIds.includes(weaponId)) throw new Error(`unknown filtered weapon: ${weaponId}`);
}
if (new Set(selectedWeaponIds).size !== selectedWeaponIds.length) {
  throw new Error('duplicate filtered weapon');
}
const kunaiStates = ['normal', 'dark', 'raitei', 'kokuraitei'];
const reloadTargetRatios = Array.from(
  { length: reloadFrames },
  (_, index) => (index + 1) / (reloadFrames + 1),
);
mkdirSync(output, { recursive: true });

function run(command, commandArgs, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, commandArgs, {
      cwd: process.cwd(),
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
      ...options,
    });
    let stdout = '';
    let stderr = '';
    child.stdout?.on('data', (chunk) => { stdout += String(chunk); });
    child.stderr?.on('data', (chunk) => { stderr += String(chunk); });
    child.on('error', reject);
    child.on('exit', (code) => {
      if (code === 0) resolve({ stdout, stderr });
      else reject(new Error(`${command} exited ${code}\n${stderr}\n${stdout}`));
    });
  });
}

async function waitForServer(url, proc) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) throw new Error(`vite exited before ready: ${proc.exitCode}`);
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // 起動待ち
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error('vite dev did not start');
}

const vite = spawn('npx', ['vite', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
  cwd: process.cwd(),
  stdio: ['ignore', 'pipe', 'pipe'],
});
const base = `http://127.0.0.1:${port}`;
const reports = [];
const failures = [];
let screenshotsValidated = 0;
const caseAttempts = {};

const requiredFamilyRepresentatives = {
  rifle: 'kaede-ar',
  pistol: 'suzume',
  kunai: 'fists',
  staff: 'tenrai-staff',
  bow: 'gekkou-bow',
  fan: 'fujin-fan',
  launcher: 'gouka-rl',
  heavy: 'shura-lmg',
};
for (const [family, weaponId] of Object.entries(requiredFamilyRepresentatives)) {
  if (!weaponIds.includes(weaponId)) failures.push(`${family}: representative ${weaponId} is missing`);
}

function validateCapture(weaponId, kunaiState, name, caseFailures) {
  const file = path.join(
    output,
    `kunren-training-${weaponId}-${kunaiState}-${quality}-${viewport}-${name}.png`,
  );
  if (!existsSync(file)) {
    caseFailures.push(`missing ${name} screenshot`);
    return 0;
  }
  const bytes = statSync(file).size;
  if (bytes < 10_000) {
    caseFailures.push(`${name} screenshot is suspiciously small (${bytes} B)`);
    return 0;
  }
  return 1;
}

try {
  await waitForServer(base, vite);
  const cases = selectedWeaponIds.flatMap((weaponId) =>
    weaponId === 'fists'
      ? kunaiStates.map((kunaiState) => ({ weaponId, kunaiState }))
      : [{ weaponId, kunaiState: 'normal' }],
  );
  for (const [index, auditCase] of cases.entries()) {
    const { weaponId, kunaiState } = auditCase;
    const key = `${weaponId}:${kunaiState}`;
    let completed = false;
    let lastCaseFailures = [];
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      caseAttempts[key] = attempt;
      process.stdout.write(
        `[${index + 1}/${cases.length}] ${key}${attempt > 1 ? ` retry ${attempt}/${maxAttempts}` : ''}\n`,
      );
      const caseFailures = [];
      let validated = 0;
      try {
        await run('node', [
          'e2e/visual-audit.mjs',
          `--base=${base}`,
          `--port=${port}`,
          `--weapon=${weaponId}`,
          `--kunai-state=${kunaiState}`,
          `--camo=${camoId}`,
          '--stage=kunren',
          '--mode=training',
          `--quality=${quality}`,
          `--viewport=${viewport}`,
          `--settle-ms=${settleMs}`,
          `--frames=${sampleFrames}`,
          `--reload-frames=${reloadFrames}`,
          `--reload-frame-ms=${reloadFrameMs}`,
          `--reload-kind=${reloadKind}`,
        ], { env: { ...process.env, AUDIT_SHOT_DIR: output } });
        const reportName = `kunren-training-${weaponId}-${kunaiState}-${quality}-${viewport}-report.json`;
        const report = JSON.parse(readFileSync(path.join(output, reportName), 'utf8'));
        for (const name of ['idle', 'fire-055ms', 'fire-150ms', 'ads', 'sprint']) {
          validated += validateCapture(weaponId, kunaiState, name, caseFailures);
        }
        if (weaponId !== 'fists') {
          for (const [index, targetRatio] of reloadTargetRatios.entries()) {
            const ratioTag = String(Math.round(targetRatio * 1000)).padStart(4, '0');
            validated += validateCapture(
              weaponId,
              kunaiState,
              `reload-ratio-${String(index + 1).padStart(2, '0')}-${ratioTag}`,
              caseFailures,
            );
          }
        }
        if (weaponId !== 'fists' && report.reloadObserved !== true) {
          caseFailures.push('reload input was not observed');
        }
        if (weaponId !== 'fists' && report.reloadKind !== reloadKind) {
          caseFailures.push(`reload kind mismatch (${String(report.reloadKind)})`);
        }
        if (weaponId !== 'fists') {
          const captured = Array.isArray(report.reloadCapturedRatios)
            ? report.reloadCapturedRatios
            : [];
          if (captured.length !== reloadTargetRatios.length) {
            caseFailures.push(
              `reload ratio capture count mismatch (${captured.length}/${reloadTargetRatios.length})`,
            );
          } else {
            for (let ratioIndex = 0; ratioIndex < captured.length; ratioIndex += 1) {
              const actual = Number(captured[ratioIndex]);
              const target = reloadTargetRatios[ratioIndex];
              if (!Number.isFinite(actual) || target === undefined || actual < target || actual > target + 0.12) {
                caseFailures.push(
                  `reload ratio ${ratioIndex + 1} out of window (${String(actual)} target=${String(target)})`,
                );
              }
              if (ratioIndex > 0 && actual <= Number(captured[ratioIndex - 1])) {
                caseFailures.push(`reload ratios are not strictly increasing at ${ratioIndex + 1}`);
              }
            }
          }
        }
        if (weaponId !== 'fists' && reloadKind === 'empty' && report.reloadStartAmmo !== 0) {
          caseFailures.push(`empty reload did not start at zero (${String(report.reloadStartAmmo)})`);
        }
        if (report.errors?.length) caseFailures.push(report.errors.join('; '));
        if (caseFailures.length === 0) {
          reports.push(report);
          screenshotsValidated += validated;
          completed = true;
          break;
        }
      } catch (error) {
        caseFailures.push(String(error));
      }
      lastCaseFailures = caseFailures;
      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
    }
    if (!completed) {
      failures.push(...lastCaseFailures.map((failure) => `${key}: ${failure}`));
    }
  }
} finally {
  vite.kill('SIGTERM');
}

const summary = {
  generatedAt: new Date().toISOString(),
  catalogWeaponCount: weaponIds.length,
  weaponCount: selectedWeaponIds.length,
  selectedWeaponIds,
  caseCount: reports.length,
  expectedCaseCount:
    selectedWeaponIds.length + (selectedWeaponIds.includes('fists') ? kunaiStates.length - 1 : 0),
  reloadChecked: reports.filter((report) => report.weaponId !== 'fists').length,
  kunaiStatesChecked: reports
    .filter((report) => report.weaponId === 'fists')
    .map((report) => report.kunaiState),
  quality,
  viewport,
  reloadFrames,
  reloadFrameMs,
  reloadTargetRatios,
  reloadKind,
  camoId,
  maxAttempts,
  caseAttempts,
  retriedCases: Object.values(caseAttempts).filter((attempts) => attempts > 1).length,
  screenshotsValidated,
  expectedScreenshotCount:
    selectedWeaponIds.filter((weaponId) => weaponId !== 'fists').length * (5 + reloadFrames) +
    (selectedWeaponIds.includes('fists') ? kunaiStates.length * 5 : 0),
  requiredFamilyRepresentatives,
  headless: true,
  muted: true,
  failures,
};
writeFileSync(path.join(output, 'summary.json'), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary, null, 2));
if (failures.length > 0 || summary.caseCount !== summary.expectedCaseCount) process.exitCode = 1;
