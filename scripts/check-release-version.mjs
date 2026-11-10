// Runs in the deploy workflow when the native code has changed (a new APK is about to be built).
// Installed apps only offer an APK whose version is newer than theirs, so a native change must come
// with a higher "version" in app.json than the APK already published; otherwise phones would keep
// the old native code and never receive later updates.
import { readFileSync } from 'node:fs';

const appVersion = JSON.parse(readFileSync('app.json', 'utf8')).expo.version;
const published = JSON.parse(
  readFileSync('backend/fastapi_app/static/downloads/version.json', 'utf8'),
).latest_version;

const parts = (v) => String(v).split('.').map((n) => Number(n) || 0);
const newer = (a, b) => {
  const [x, y] = [parts(a), parts(b)];
  for (let i = 0; i < Math.max(x.length, y.length); i += 1) {
    if ((x[i] ?? 0) !== (y[i] ?? 0)) return (x[i] ?? 0) > (y[i] ?? 0);
  }
  return false;
};

if (!newer(appVersion, published)) {
  console.error(
    `Native code changed, but app.json "version" (${appVersion}) is not newer than the published APK (${published}).\n` +
      'Raise "version" in app.json (for example 1.2.0 -> 1.3.0) and push again.',
  );
  process.exit(1);
}
console.log(`OK: building APK ${appVersion} (published: ${published}).`);
