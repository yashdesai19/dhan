// Publishes the newest production APK on the website, so every installed app offers it.
//
//   npm run release:apk -- "What's new, in one sentence"
//
// Takes the latest finished Android production build for the app.json version, checks it was built
// from this repository's history, downloads it into the backend's downloads, raises version.json,
// then commits and pushes. Render redeploys and the in-app popup offers the APK to everyone.
import { execFileSync, execSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const APK = 'backend/fastapi_app/static/downloads/dhan.apk';
const VERSION_FILE = 'backend/fastapi_app/static/downloads/version.json';

const fail = (msg) => {
  console.error(`\n✗ ${msg}`);
  process.exit(1);
};
const sh = (cmd) => execSync(cmd, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();

const notes = process.argv.slice(2).join(' ').trim();
if (!notes) fail('Add release notes: npm run release:apk -- "What\'s new"');

if (sh('git status --porcelain -- app.json backend/fastapi_app/static/downloads')) {
  fail('app.json or the downloads folder has uncommitted changes. Commit or discard them first.');
}

const version = JSON.parse(readFileSync('app.json', 'utf8')).expo.version;
const current = JSON.parse(readFileSync(VERSION_FILE, 'utf8'));
if (current.latest_version === version) fail(`APK ${version} is already published.`);

console.log(`Looking for a finished production APK ${version} on EAS...`);
const builds = JSON.parse(
  sh('npx eas build:list --platform android --status finished --limit 20 --json --non-interactive'),
);
const build = builds.find(
  (b) => b.appVersion === version && b.buildProfile === 'production' && b.artifacts?.buildUrl?.endsWith('.apk'),
);
if (!build) fail(`No finished production APK for version ${version} yet. Wait for the workflow's build.`);

try {
  execFileSync('git', ['merge-base', '--is-ancestor', build.gitCommitHash, 'HEAD'], { stdio: 'ignore' });
} catch {
  fail(`Build ${build.id} came from commit ${build.gitCommitHash}, which isn't in this branch. Pull first.`);
}

console.log(`Downloading build ${build.id} (commit ${build.gitCommitHash.slice(0, 7)})...`);
const res = await fetch(build.artifacts.buildUrl);
if (!res.ok) fail(`Download failed: HTTP ${res.status}`);
const bytes = Buffer.from(await res.arrayBuffer());
// An APK is a zip file: it starts with "PK"
if (bytes.length < 10_000_000 || bytes[0] !== 0x50 || bytes[1] !== 0x4b) {
  fail(`The download doesn't look like an APK (${bytes.length} bytes).`);
}
writeFileSync(APK, bytes);
writeFileSync(
  VERSION_FILE,
  `${JSON.stringify({ ...current, latest_version: version, release_notes: notes }, null, 2)}\n`,
);
console.log(`Saved ${(bytes.length / 1e6).toFixed(1)} MB and set version.json to ${version}.`);

execFileSync('git', ['add', APK, VERSION_FILE], { stdio: 'inherit' });
execFileSync('git', ['commit', '-m', `Release ${version} APK\n\n${notes}`], { stdio: 'inherit' });
execFileSync('git', ['push'], { stdio: 'inherit' });
console.log(`\n✓ APK ${version} published. Installed apps will offer it once Render finishes deploying.`);
