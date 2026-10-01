// Runs the pure-TypeScript tests (utils, selectors, repositories) with only Node + TypeScript,
// for environments without node_modules. The real suite runs with `npm test` (jest-expo).
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { existsSync, readdirSync, rmSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, '.offline-build');
rmSync(out, { recursive: true, force: true });

const localTsc = path.join(
  root,
  'node_modules/.bin',
  process.platform === 'win32' ? 'tsc.cmd' : 'tsc',
);
const tsc = process.env.TSC ?? (existsSync(localTsc) ? localTsc : 'tsc');
execFileSync(tsc, ['-p', path.join(root, 'offline/tsconfig.logic.json')], {
  stdio: 'inherit',
  shell: process.platform === 'win32',
});

const require = createRequire(import.meta.url);
const Module = require('node:module');
const origResolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) {
  if (request.startsWith('@/')) request = path.join(out, request.slice(2));
  return origResolve.call(this, request, ...rest);
};

// Minimal jest-compatible globals.
const tests = [];
let prefix = [];
globalThis.describe = (name, fn) => {
  prefix.push(name);
  fn();
  prefix.pop();
};
globalThis.it = globalThis.test = (name, fn) => tests.push({ name: [...prefix, name].join(' › '), fn });
globalThis.beforeEach = (fn) => tests.push({ hook: fn });
const fmt = (v) => JSON.stringify(v);
globalThis.expect = (actual) => {
  const fail = (msg) => {
    throw new Error(msg);
  };
  const deepEq = (a, b) => fmt(a) === fmt(b);
  return {
    toBe: (e) => Object.is(actual, e) || fail(`expected ${fmt(actual)} to be ${fmt(e)}`),
    toEqual: (e) => deepEq(actual, e) || fail(`expected ${fmt(actual)} to equal ${fmt(e)}`),
    toBeCloseTo: (e, d = 2) => Math.abs(actual - e) < 10 ** -d / 2 || fail(`expected ${actual} ≈ ${e}`),
    toBeGreaterThan: (e) => actual > e || fail(`expected ${actual} > ${e}`),
    toBeLessThan: (e) => actual < e || fail(`expected ${actual} < ${e}`),
    toContain: (e) => actual.includes(e) || fail(`expected ${fmt(actual)} to contain ${fmt(e)}`),
    toHaveLength: (e) => actual.length === e || fail(`expected length ${actual.length} to be ${e}`),
    toBeUndefined: () => actual === undefined || fail(`expected undefined, got ${fmt(actual)}`),
    toBeDefined: () => actual !== undefined || fail('expected a value'),
    toBeNull: () => actual === null || fail(`expected null, got ${fmt(actual)}`),
    toBeTruthy: () => !!actual || fail(`expected truthy, got ${fmt(actual)}`),
    toBeFalsy: () => !actual || fail(`expected falsy, got ${fmt(actual)}`),
  };
};

const dir = path.join(out, '__tests__');
const files = existsSync(dir) ? readdirSync(dir).filter((f) => f.endsWith('.logic.test.js') || f === 'invariants.test.js') : [];
let passed = 0;
let failed = 0;
for (const f of files) {
  tests.length = 0;
  require(path.join(dir, f));
  const hooks = tests.filter((t) => t.hook).map((t) => t.hook);
  for (const t of tests.filter((x) => !x.hook)) {
    try {
      for (const h of hooks) await h();
      await t.fn();
      passed += 1;
      console.log(`  ✓ ${t.name}`);
    } catch (e) {
      failed += 1;
      console.log(`  ✗ ${t.name}\n      ${e.message}`);
    }
  }
}
console.log(`\n${passed} passed, ${failed} failed (${files.length} files)`);
rmSync(out, { recursive: true, force: true });
process.exit(failed ? 1 : 0);
