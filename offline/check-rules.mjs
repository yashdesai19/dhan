// Offline stand-in for the project rules that `expo lint` + review enforce (spec §20).
// Runs without node_modules:  node offline/check-rules.mjs
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const walk = (dir) =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : /\.(ts|tsx)$/.test(f) ? [p] : [];
  });

const ui = ['app', 'features', 'components'].flatMap((d) => walk(join(root, d)));
const all = [
  ...ui,
  ...['data', 'store', 'utils', 'hooks', 'theme', 'types', 'mock'].flatMap((d) => walk(join(root, d))),
];

const rules = [
  { name: 'no explicit any', files: all, re: /(:\s*any\b|as any\b|<any>)/ },
  {
    name: 'screens must not import the mock DB (Screen → hook → repository → mock)',
    files: ui,
    re: /from '@\/mock\/(db|seed)'/,
  },
  {
    name: 'no raw hex/rgb colors outside theme',
    files: ui.filter((f) => !/[/\\]icons[/\\]/.test(f)),
    re: /['"]#[0-9A-Fa-f]{3,8}['"]|rgba?\(/,
  },
  { name: 'no raw numeric fontSize outside theme', files: ui, re: /fontSize:\s*\d/ },
  { name: 'no font family string literals', files: ui, re: /fontFamily:\s*['"]/ },
  {
    name: 'no ScrollView-mapped long lists of transactions (use FlatList/SectionList)',
    files: ui,
    re: /ScrollView[\s\S]{0,400}transactions\.map\(/,
  },
];

let failures = 0;
for (const r of rules) {
  const hits = [];
  for (const f of r.files) {
    const lines = readFileSync(f, 'utf8').split('\n');
    lines.forEach((l, i) => {
      if (!l.trim().startsWith('//') && r.re.test(l))
        hits.push(`${relative(root, f)}:${i + 1}  ${l.trim().slice(0, 110)}`);
    });
  }
  console.log(`${hits.length ? '✗' : '✓'} ${r.name}`);
  hits.forEach((h) => console.log('    ' + h));
  failures += hits.length;
}
console.log(failures ? `\n${failures} rule violation(s)` : '\nAll project rules pass');
process.exit(failures ? 1 : 0);
