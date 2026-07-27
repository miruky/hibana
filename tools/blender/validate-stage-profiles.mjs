import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '../..');
const profilePath = resolve(root, 'tools/blender/stage-profiles.json');
const stagesPath = resolve(root, 'src/game/stages.ts');

const profilesDocument = JSON.parse(readFileSync(profilePath, 'utf8'));
const stageSource = readFileSync(stagesPath, 'utf8');
const stageIds = [...stageSource.matchAll(/\n\s+id: '([^']+)',\n\s+name:/g)].map((match) => match[1]);
const profiles = profilesDocument.profiles ?? {};
const profileIds = Object.keys(profiles);

const failures = [];
const requireCondition = (condition, message) => {
  if (!condition) failures.push(message);
};

requireCondition(profilesDocument.version >= 2, 'profile document version must be >= 2');
requireCondition(stageIds.length === 31, `src/game/stages.ts must expose 31 stages, got ${stageIds.length}`);
requireCondition(profileIds.length === 31, `stage-profiles.json must expose 31 profiles, got ${profileIds.length}`);
requireCondition(
  stageIds.length === profileIds.length && stageIds.every((id) => profileIds.includes(id)),
  'stage IDs and profile IDs must match exactly',
);

const landmarks = [];
for (const stageId of stageIds) {
  const profile = profiles[stageId];
  if (!profile) continue;
  const city = profile.cityProfile;
  requireCondition(Boolean(city), `${stageId}: missing cityProfile`);
  if (city) {
    requireCondition(Array.isArray(city.targetBuildingCount) && city.targetBuildingCount[0] >= 20, `${stageId}: dense building target must start at 20+`);
    requireCondition(city.coverageRatio >= 0.58 && city.coverageRatio <= 0.75, `${stageId}: coverageRatio out of dense-but-playable range`);
    requireCondition(city.highRiseRatio >= 0.68 && city.highRiseRatio <= 0.85, `${stageId}: highRiseRatio must keep tall buildings in the majority`);
    requireCondition(Array.isArray(city.dominantHeightM) && city.dominantHeightM[1] >= 34, `${stageId}: dominant height band is too low`);
    requireCondition(Array.isArray(city.secondaryHeightM), `${stageId}: missing secondary height band`);
    requireCondition(Array.isArray(city.streetWidthM), `${stageId}: missing street width range`);
    requireCondition(city.horizonStrategy?.includes('画像マット') && city.horizonStrategy?.includes('禁止'), `${stageId}: horizon must explicitly ban raster mattes`);
    requireCondition(city.forbiddenMotifs?.includes('遠景画像'), `${stageId}: forbidden motifs must include distant raster images`);
  }

  const stageLandmarks = profile.megaLandmarks;
  requireCondition(Array.isArray(stageLandmarks) && stageLandmarks.length === 2, `${stageId}: must have exactly two megaLandmarks`);
  if (!Array.isArray(stageLandmarks)) continue;
  for (const entry of stageLandmarks) {
    landmarks.push({ ...entry, stageId });
    requireCondition(entry.id?.startsWith(`${stageId}-`), `${stageId}: landmark id must be stage-owned (${entry.id})`);
    requireCondition(Boolean(entry.name && entry.purpose && entry.silhouette && entry.roof && entry.facade), `${stageId}/${entry.id}: incomplete visual brief`);
    requireCondition(Array.isArray(entry.materials) && entry.materials.length >= 4, `${stageId}/${entry.id}: needs four or more material cues`);
    requireCondition(Array.isArray(entry.combatFlow) && entry.combatFlow.length === 3, `${stageId}/${entry.id}: needs exactly three combat-flow layers`);
    const dims = entry.dimensionsM ?? {};
    requireCondition(dims.width >= 78 && dims.depth >= 56 && dims.height >= 36, `${stageId}/${entry.id}: dimensions are below castle-scale gate`);
    requireCondition(Boolean(entry.lodPolicy), `${stageId}/${entry.id}: missing LOD policy`);
  }
}

requireCondition(landmarks.length === 62, `expected 62 landmarks, got ${landmarks.length}`);
for (const field of ['id', 'name', 'silhouette', 'roof', 'facade']) {
  const values = landmarks.map((entry) => entry[field]);
  requireCondition(new Set(values).size === 62, `all 62 landmark ${field} values must be unique`);
}
requireCondition(new Set(stageIds.map((id) => profiles[id]?.cityProfile?.archetype)).size === 31, 'all 31 city archetypes must be unique');
requireCondition(new Set(stageIds.map((id) => profiles[id]?.cityProfile?.blockPattern)).size === 31, 'all 31 block patterns must be unique');
requireCondition(new Set(stageIds.map((id) => profiles[id]?.cityProfile?.roofLanguage)).size === 31, 'all 31 roof languages must be unique');
requireCondition(new Set(stageIds.map((id) => profiles[id]?.cityProfile?.facadeLanguage)).size === 31, 'all 31 facade languages must be unique');

if (failures.length > 0) {
  console.error(`Stage profile validation failed (${failures.length}):`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exitCode = 1;
} else {
  console.log(`Stage profile validation passed: ${profileIds.length} stages, ${landmarks.length} unique mega-landmarks, two per stage.`);
}
