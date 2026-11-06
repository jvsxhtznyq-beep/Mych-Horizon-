// Build Glowmoss Caverns into one self-contained HTML file and a release ZIP.
//
// 1. Render assets/sprites.sprite with the mych-pixel-art toolchain and validate
//    the sheet against assets/palette.txt (the build fails on palette violations).
// 2. Bundle the ES modules into one script: modules are ordered by their imports,
//    import lines and `export` keywords are removed, and duplicate top-level names
//    fail the build (they would collide in the shared scope).
// 3. Inline the CSS, the bundle and the sprite sheet into dist/glowmoss-caverns.html.
// 4. Write dist/glowmoss-caverns-1.0.0.zip with fixed timestamps (byte-identical rebuilds).

import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { deflateRawSync } from 'node:zlib';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = resolve(ROOT, '../../../..');
const PIXEL_TOOL = join(REPO, 'specialists/mych-pixel-art/scripts/pixel_tool.py');
export const VERSION = '1.0.0';

export function renderSprites() {
  const out = join(ROOT, 'build/assets');
  mkdirSync(out, { recursive: true });
  execFileSync('python3', ['-B', PIXEL_TOOL, 'render', join(ROOT, 'assets/sprites.sprite'), '--out', out, '--sheet'], { stdio: 'pipe' });
  const report = JSON.parse(execFileSync('python3', ['-B', PIXEL_TOOL, 'validate', join(out, 'sprites.png'), '--palette',
    join(ROOT, 'assets/palette.txt'), '--cell', '16x16', '--max-colors', '16', '--json'], { stdio: 'pipe' }).toString());
  if (!report.ok) throw new Error(`sprite sheet fails validation: ${report.errors.join('; ')}`);
  return { png: readFileSync(join(out, 'sprites.png')), meta: JSON.parse(readFileSync(join(out, 'sprites.json'), 'utf8')), report };
}

export function bundle(entry = join(ROOT, 'src/main.js')) {
  const order = [];
  const seen = new Set();
  const visit = (file) => {
    if (seen.has(file)) return;
    seen.add(file);
    const text = readFileSync(file, 'utf8');
    for (const match of text.matchAll(/^import\s+[^;]*?from\s+'(\.[^']+)';$/gm)) visit(resolve(dirname(file), match[1]));
    order.push({ file, text });
  };
  visit(entry);
  const names = new Map();
  const parts = [];
  for (const { file, text } of order) {
    const body = text.replace(/^import\s+[^;]*?from\s+'[^']+';\n/gm, '').replace(/^export\s+(?=(async\s+)?(function|const|let|class)\b)/gm, '');
    if (/^\s*(import|export)\b/m.test(body)) throw new Error(`${relative(ROOT, file)} uses an import or export form the bundler does not support`);
    for (const match of body.matchAll(/^(?:async\s+)?(?:function\*?|const|let|class)\s+([A-Za-z_$][\w$]*)/gm)) {
      if (names.has(match[1])) throw new Error(`top-level name ${match[1]} is declared in both ${names.get(match[1])} and ${relative(ROOT, file)}`);
      names.set(match[1], relative(ROOT, file));
    }
    parts.push(`// ---- ${relative(ROOT, file)} ----\n${body}`);
  }
  return { code: `(function () {\n'use strict';\n${parts.join('\n')}\n})();\n`, modules: order.map((o) => relative(ROOT, o.file)) };
}

const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
function crc32(buffer) {
  let c = 0xffffffff;
  for (const byte of buffer) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

export function zip(entries) {
  // DOS date 1980-01-01 00:00 keeps rebuilds byte-identical.
  const time = 0;
  const date = (0 << 9) | (1 << 5) | 1;
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const { name, data } of entries) {
    const nameBytes = Buffer.from(name, 'utf8');
    const compressed = deflateRawSync(data, { level: 9 });
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0); local.writeUInt16LE(20, 4); local.writeUInt16LE(0x0800, 6); local.writeUInt16LE(8, 8);
    local.writeUInt16LE(time, 10); local.writeUInt16LE(date, 12); local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(compressed.length, 18); local.writeUInt32LE(data.length, 22); local.writeUInt16LE(nameBytes.length, 26);
    locals.push(local, nameBytes, compressed);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0); central.writeUInt16LE(0x0314, 4); central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0x0800, 8); central.writeUInt16LE(8, 10); central.writeUInt16LE(time, 12); central.writeUInt16LE(date, 14);
    central.writeUInt32LE(crc, 16); central.writeUInt32LE(compressed.length, 20); central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(nameBytes.length, 28); central.writeUInt32LE((0o100644 << 16) >>> 0, 38); central.writeUInt32LE(offset, 42);
    centrals.push(central, nameBytes);
    offset += local.length + nameBytes.length + compressed.length;
  }
  const centralSize = centrals.reduce((n, b) => n + b.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(entries.length, 8); end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(centralSize, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, ...centrals, end]);
}

export function build() {
  const sprites = renderSprites();
  const { code, modules } = bundle();
  const css = readFileSync(join(ROOT, 'src/styles.css'), 'utf8');
  const assets = { sheetImage: `data:image/png;base64,${sprites.png.toString('base64')}`, sheet: sprites.meta };
  let html = readFileSync(join(ROOT, 'src/index.html'), 'utf8');
  const script = `window.GLOWMOSS_ASSETS = ${JSON.stringify(assets)};\n${code}`.replace(/<\/script/gi, '<\\/script');
  html = html.replace('<link rel="stylesheet" href="styles.css">', `<style>\n${css}</style>`);
  html = html.replace('<script type="module" src="main.js"></script>', `<script>\n${script}</script>`);
  if (html.includes('src="main.js"') || html.includes('href="styles.css"')) throw new Error('index.html placeholders were not replaced');
  mkdirSync(join(ROOT, 'dist'), { recursive: true });
  const htmlPath = join(ROOT, 'dist/glowmoss-caverns.html');
  writeFileSync(htmlPath, html);
  const readme = readFileSync(join(ROOT, 'README.md'));
  const archive = zip([{ name: 'glowmoss-caverns/index.html', data: Buffer.from(html) }, { name: 'glowmoss-caverns/README.md', data: readme }]);
  const zipPath = join(ROOT, `dist/glowmoss-caverns-${VERSION}.zip`);
  writeFileSync(zipPath, archive);
  const sha = (b) => createHash('sha256').update(b).digest('hex');
  return { modules, htmlBytes: Buffer.byteLength(html), htmlSha256: sha(Buffer.from(html)), zipBytes: archive.length,
           zipSha256: sha(archive), spriteColors: sprites.report.colors, spriteFrames: sprites.meta.frames.length };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const result = build();
  console.log(JSON.stringify(result, null, 2));
}
