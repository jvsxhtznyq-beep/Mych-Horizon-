// End-to-end tests in headless Chromium (Playwright). Writes screenshots and a JSON
// result file to ../../evidence/ (relative to the game folder) and exits non-zero if
// any check fails. Run: node tests/e2e/run.mjs
//
// The single-file build runs from file:// with ?test, so the simulation advances only
// through window.__glowmoss.step(n) while real keyboard events drive the input system.

import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from '../../tools/build.mjs';
import { solveLevel, planToFrames } from '../../tools/solve.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const EVIDENCE = resolve(ROOT, '../evidence');
const SHOTS = join(EVIDENCE, 'screenshots');
mkdirSync(SHOTS, { recursive: true });

const checks = [];
function check(name, ok, detail = '') {
  checks.push({ name, ok: !!ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ` (${detail})` : ''}`);
}

const buildInfo = build();
const fileUrl = pathToFileURL(join(ROOT, 'dist/glowmoss-caverns.html')).href;
const browser = await chromium.launch();
const pageErrors = [];
const watch = (page, label) => {
  page.on('pageerror', (e) => pageErrors.push(`${label}: ${e.message}`));
  page.on('console', (m) => { if (m.type() === 'error') pageErrors.push(`${label} console: ${m.text()}`); });
};
const state = (page) => page.evaluate(() => window.__glowmoss.state());

async function playPlan(page, levelIndex, shotName) {
  const solution = solveLevel(levelIndex);
  if (!solution.solved) throw new Error(`solver could not solve level ${levelIndex + 1}`);
  const frames = planToFrames(solution.plan);
  const keys = { left: 'ArrowLeft', right: 'ArrowRight', jump: 'Space' };
  const held = { left: false, right: false, jump: false };
  let last = null;
  let shot = false;
  for (let i = 0; i < frames.length;) {
    const input = frames[i];
    let j = i;
    while (j < frames.length && frames[j].left === input.left && frames[j].right === input.right && frames[j].jump === input.jump) j++;
    for (const k of Object.keys(keys)) {
      if (input[k] !== held[k]) {
        if (input[k]) await page.keyboard.down(keys[k]); else await page.keyboard.up(keys[k]);
        held[k] = input[k];
      }
    }
    last = await page.evaluate((n) => window.__glowmoss.step(n), j - i);
    if (!shot && last.frame > solution.frames / 2) {
      await page.screenshot({ path: join(SHOTS, shotName) });
      shot = true;
    }
    if (last.status === 'complete') break;
    i = j;
  }
  for (const k of Object.keys(keys)) if (held[k]) await page.keyboard.up(keys[k]);
  return { last, solution };
}

// 1. Desktop: title, full level replay with real key events, save data.
const desktop = await browser.newContext({ viewport: { width: 1280, height: 720 } });
const page = await desktop.newPage();
watch(page, 'desktop');
await page.goto(`${fileUrl}?test=1`);
await page.waitForFunction(() => window.__glowmoss && window.__glowmoss.state().sprites, null, { timeout: 10000 });
check('title screen shows with sprites loaded', await page.isVisible('.screen[data-screen="title"]'));
await page.screenshot({ path: join(SHOTS, '01-title.png') });
await page.click('[data-action="play"]');
let s = await state(page);
check('Play starts cavern 1', s.screen === 'playing' && s.level === 0, `screen ${s.screen}`);
check('Web Audio is available and unlocked by the click', s.audio === true);
const { last, solution } = await playPlan(page, 0, '02-cavern1-mid.png');
s = await state(page);
check('cavern 1 completed through real keyboard input', s.screen === 'complete' && last.status === 'complete',
      `frames ${last.frame} (solver predicted ${solution.frames}), score ${s.score}`);
check('browser replay matches the Node simulation frame for frame', last.frame === solution.frames && s.score === solution.score,
      `browser ${last.frame}/${s.score}, node ${solution.frames}/${solution.score}`);
check('effects ran during play (sound events and particles)', s.events.includes('complete') && s.events.includes('pickup'));
await page.screenshot({ path: join(SHOTS, '03-cavern1-complete.png') });
const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('glowmoss-caverns.save')));
check('progress saved: cavern 2 unlocked and best score stored', stored.unlocked === 2 && stored.best['1'] === s.score,
      JSON.stringify({ unlocked: stored.unlocked, best: stored.best }));

// 2. Pause and resume with the real Escape key, settings persistence.
await page.click('[data-action="next"]');
await page.evaluate(() => window.__glowmoss.step(30));
await page.keyboard.press('Escape');
s = await page.evaluate(() => window.__glowmoss.step(1));
check('Escape pauses the game', s.screen === 'paused');
const frozen = s.frame;
s = await page.evaluate(() => window.__glowmoss.step(20));
check('paused game does not advance', s.frame === frozen);
await page.screenshot({ path: join(SHOTS, '04-paused.png') });
await page.keyboard.press('Escape');
s = await page.evaluate(() => window.__glowmoss.step(5));
check('Escape resumes the game', s.screen === 'playing' && s.frame > frozen);
await page.keyboard.press('Escape');
await page.evaluate(() => window.__glowmoss.step(1));
await page.click('.screen[data-screen="paused"] [data-action="settings"]');
await page.check('#set-showFps');
await page.locator('#set-music').fill('20');
await page.uncheck('#set-shake');
await page.screenshot({ path: join(SHOTS, '05-settings.png') });
await page.click('.screen[data-screen="settings"] [data-action="back"]');
check('Back from settings returns to the pause menu', (await state(page)).screen === 'paused');
await page.reload();
await page.waitForFunction(() => window.__glowmoss && window.__glowmoss.state().sprites);
const settings = await page.evaluate(() => window.__glowmoss.state().save.settings);
check('settings persist across reloads', settings.showFps === true && settings.music === 0.2 && settings.shake === false,
      JSON.stringify(settings));
check('continue label offers the unlocked cavern', (await page.textContent('#continue-label')).includes('cavern 2'));

// 3. Failure handling: corrupted save data and an injected runtime error.
await page.evaluate(() => localStorage.setItem('glowmoss-caverns.save', '{"version": 1, "unlocked": oops'));
await page.reload();
await page.waitForFunction(() => window.__glowmoss);
const toast = await page.textContent('#toast');
s = await state(page);
check('corrupted save is reset with a visible notice', toast.includes('damaged') && s.save.unlocked === 1, toast);
await page.evaluate(() => setTimeout(() => { throw new Error('injected failure for testing'); }, 0));
await page.waitForSelector('.screen[data-screen="error"]:not([hidden])', { timeout: 5000 });
check('uncaught errors show the recovery screen', (await page.textContent('#error-message')).includes('injected failure'));
await page.screenshot({ path: join(SHOTS, '06-error-screen.png') });

// 4. Mobile: responsive scaling and touch controls.
const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
const phone = await mobile.newPage();
watch(phone, 'mobile');
await phone.goto(`${fileUrl}?test=1`);
await phone.waitForFunction(() => window.__glowmoss && window.__glowmoss.state().sprites);
await phone.tap('[data-action="play"]');
const box = await phone.locator('#game').boundingBox();
check('canvas fits the phone width', box.width <= 390 && box.width >= 300, `${box.width}x${box.height}`);
check('touch controls appear on touch devices', await phone.isVisible('#touch'));
const before = (await state(phone)).x;
await phone.locator('[data-touch="right"]').dispatchEvent('pointerdown');
await phone.evaluate(() => window.__glowmoss.step(40));
await phone.locator('[data-touch="right"]').dispatchEvent('pointerup');
const after = (await state(phone)).x;
check('touch right button moves the player', after > before + 20, `x ${before.toFixed(1)} -> ${after.toFixed(1)}`);
await phone.screenshot({ path: join(SHOTS, '07-mobile-touch.png') });

// 5. Missing sprites: the source version over HTTP with the sprite image blocked.
const server = spawn('python3', ['-m', 'http.server', '0', '--bind', '127.0.0.1'], { cwd: ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
const port = await new Promise((resolvePort, reject) => {
  const timer = setTimeout(() => reject(new Error('http.server did not start')), 10000);
  const onData = (chunk) => {
    const match = String(chunk).match(/port (\d+)/);
    if (match) { clearTimeout(timer); resolvePort(Number(match[1])); }
  };
  server.stdout.on('data', onData);
  server.stderr.on('data', onData);
});
const fallbackContext = await browser.newContext({ viewport: { width: 960, height: 540 } });
const fallback = await fallbackContext.newPage();
const fallbackErrors = [];
fallback.on('pageerror', (e) => fallbackErrors.push(e.message));
await fallback.route('**/sprites.png', (route) => route.abort());
await fallback.goto(`http://127.0.0.1:${port}/src/index.html?test=1`);
await fallback.waitForFunction(() => window.__glowmoss);
await fallback.waitForFunction(() => !document.querySelector('#toast').hidden, null, { timeout: 5000 });
await fallback.click('[data-action="play"]');
s = await fallback.evaluate(() => window.__glowmoss.step(60));
check('source build (ES modules over HTTP) runs and falls back to shapes when sprites fail',
      s.sprites === false && s.frame === 60 && fallbackErrors.length === 0, await fallback.textContent('#toast'));
await fallback.screenshot({ path: join(SHOTS, '08-sprite-fallback.png') });
server.kill();

// 6. Performance in real time (no test hook): frame rate and simulation cost.
const perfContext = await browser.newContext({ viewport: { width: 1280, height: 720 } });
const perf = await perfContext.newPage();
watch(perf, 'perf');
await perf.goto(fileUrl);
await perf.waitForFunction(() => window.__glowmoss && window.__glowmoss.state().sprites);
await perf.click('[data-action="play"]');
await perf.keyboard.down('ArrowRight');
const fps = await perf.evaluate(() => new Promise((done) => {
  let frames = 0;
  const start = performance.now();
  const tick = () => { frames += 1; if (performance.now() - start < 2000) requestAnimationFrame(tick); else done(frames / ((performance.now() - start) / 1000)); };
  requestAnimationFrame(tick);
}));
await perf.keyboard.up('ArrowRight');
const realtime = await state(perf);
check('real-time loop advances the simulation without the test hook', realtime.frame > 60, `frame ${realtime.frame}`);
check('rendering keeps a smooth frame rate in headless Chromium', fps >= 50, `${fps.toFixed(1)} fps`);
const stepCost = await page.evaluate(() => {
  window.__glowmoss.startLevel(2);
  const t0 = performance.now();
  window.__glowmoss.step(600);
  return (performance.now() - t0) / 600;
});
check('update plus render costs well under a 16.7 ms frame', stepCost < 4, `${stepCost.toFixed(3)} ms per step (600 steps, cavern 3)`);

const unexpected = pageErrors.filter((e) => !e.includes('injected failure'));
check('no unexpected page errors or console errors', unexpected.length === 0, unexpected.slice(0, 3).join(' | '));
await browser.close();

const summary = { date: new Date().toISOString().slice(0, 10), browser: 'Chromium (Playwright, headless)', build: buildInfo,
                  checks, passed: checks.filter((c) => c.ok).length, total: checks.length,
                  metrics: { fps: Number(fps.toFixed(1)), msPerStep: Number(stepCost.toFixed(3)), level1Frames: solution.frames } };
writeFileSync(join(EVIDENCE, 'e2e-results.json'), JSON.stringify(summary, null, 2) + '\n');
console.log(`\n${summary.passed} of ${summary.total} checks passed`);
process.exitCode = summary.passed === summary.total ? 0 : 1;
