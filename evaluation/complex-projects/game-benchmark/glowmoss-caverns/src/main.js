// Glowmoss Caverns: application shell. Screens and menus are DOM overlays;
// the game runs a fixed 60 Hz simulation and renders on animation frames.
// With ?test in the URL, the simulation only advances through
// window.__glowmoss.step(n), so browser tests are deterministic.

import { LEVELS } from './game/levels.js';
import { createWorld, stepWorld } from './game/world.js';
import { createRenderer, indexSheet } from './engine/renderer.js';
import { createInput } from './engine/input.js';
import { createAudio } from './engine/audio.js';
import { createParticles } from './engine/particles.js';
import { createStore } from './engine/storage.js';

const STEP_MS = 1000 / 60;
const MAX_STEPS_PER_FRAME = 5;
const PARTICLE_STYLES = {
  pickup: { count: 10, color: '#a8ff9e', speed: 1.4, life: 26, gravity: 0.02 },
  heal: { count: 14, color: '#ff4f7a', speed: 1.2, life: 34, gravity: -0.02 },
  stomp: { count: 16, color: '#ff8c42', speed: 1.8, life: 24, gravity: 0.08 },
  hurt: { count: 12, color: '#ff4f7a', speed: 1.6, life: 22, gravity: 0.06 },
  land: { count: 5, color: '#5d5a7a', speed: 0.8, life: 14, gravity: 0.02, spread: Math.PI, angle: -Math.PI / 2 },
  jump: { count: 4, color: '#5d5a7a', speed: 0.6, life: 12, gravity: 0.02, spread: Math.PI, angle: Math.PI / 2 },
  puff: { count: 6, color: '#ffd166', speed: 0.8, life: 16, gravity: 0 },
  checkpoint: { count: 18, color: '#5ee6e6', speed: 1.2, life: 40, gravity: -0.02 },
  complete: { count: 40, color: '#a8ff9e', speed: 2.2, life: 50, gravity: 0.03 },
};

function startApp() {
  const doc = document;
  const $ = (selector) => doc.querySelector(selector);
  const canvas = $('#game');
  const testMode = new URLSearchParams(location.search).has('test');
  const store = createStore(LEVELS.length);
  const loaded = store.load();
  let save = loaded.save;
  const renderer = createRenderer(canvas, doc);
  const input = createInput(window, window);
  const audio = createAudio(window);
  const particles = createParticles(400);
  let screen = 'title';
  let world = createWorld(0);
  let settingsReturn = 'title';
  let shake = 0;
  let flash = 0;
  let accumulator = 0;
  let lastTime = 0;
  let fps = 0;
  let fpsFrames = 0;
  let fpsTime = 0;
  let crashed = false;
  const eventLog = [];

  function toast(message) {
    if (!message) return;
    const el = $('#toast');
    el.textContent = message;
    el.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => { el.hidden = true; }, 4500);
  }

  function showScreen(name) {
    screen = name;
    for (const el of doc.querySelectorAll('.screen')) el.hidden = el.dataset.screen !== name;
    $('#hud-pause').hidden = name !== 'playing';
    if (name !== 'playing') $('#level-hint').hidden = true;
    updateTouchControls();
    const active = doc.querySelector(`.screen[data-screen="${name}"]`);
    const first = active && active.querySelector('button:not([disabled]), input, select');
    if (first) first.focus({ preventScroll: true });
    else canvas.focus({ preventScroll: true }); // keep Space from activating a hidden button during play
    if (name !== 'playing' && name !== 'paused') audio.stopMusic();
  }

  function persist() {
    const result = store.write(save);
    if (!result.ok) toast(result.notice);
  }

  function applySettings() {
    const s = save.settings;
    audio.setVolumes({ master: s.master, music: s.music, sfx: s.sfx });
    for (const key of ['master', 'music', 'sfx']) $(`#set-${key}`).value = String(Math.round(s[key] * 100));
    for (const key of ['shake', 'reducedFlashing', 'showFps']) $(`#set-${key}`).checked = s[key];
    $('#set-touch').value = s.touch;
    updateTouchControls();
  }

  function updateTouchControls() {
    const mode = save.settings.touch;
    const coarse = window.matchMedia ? window.matchMedia('(pointer: coarse)').matches : false;
    $('#touch').hidden = !(screen === 'playing' && (mode === 'on' || (mode === 'auto' && coarse)));
  }

  function renderLevelSelect() {
    const list = $('#level-list');
    list.textContent = '';
    LEVELS.forEach((level, index) => {
      const button = doc.createElement('button');
      const locked = index + 1 > save.unlocked;
      button.disabled = locked;
      button.dataset.level = String(index);
      const best = save.best[index + 1];
      button.textContent = `${index + 1}. ${level.name}${locked ? ' (locked)' : best ? ` - best ${best}` : ''}`;
      list.appendChild(button);
    });
  }

  function startLevel(index) {
    world = createWorld(index);
    particles.clear();
    renderer.resetCamera();
    shake = 0;
    flash = 0;
    input.clearPressed();
    $('#level-hint').textContent = LEVELS[index].hint;
    $('#level-hint').hidden = false;
    setTimeout(() => { $('#level-hint').hidden = true; }, 6000);
    save.plays += 1;
    persist();
    showScreen('playing');
    audio.unlock();
    audio.startMusic();
  }

  function handleEvents(events) {
    for (const event of events) {
      eventLog.push(event.type);
      if (eventLog.length > 200) eventLog.shift();
      audio.play(event.type === 'respawn' ? 'checkpoint' : event.type);
      const style = PARTICLE_STYLES[event.type];
      if (style && event.x !== undefined) particles.spawn(event.x + 4, event.y, style);
      if (event.type === 'stomp' && save.settings.shake) shake = 3;
      if ((event.type === 'hurt' || event.type === 'fall') && save.settings.shake) shake = 4;
      if ((event.type === 'hurt' || event.type === 'fall') && !save.settings.reducedFlashing) flash = 10;
      if (event.type === 'complete') onComplete();
      if (event.type === 'gameover') {
        $('#gameover-score').textContent = `Score: ${world.score}`;
        showScreen('gameover');
      }
    }
  }

  function onComplete() {
    const number = world.levelIndex + 1;
    const r = world.result;
    const previous = save.best[number] || 0;
    if (r.total > previous) save.best[number] = r.total;
    save.unlocked = Math.min(LEVELS.length, Math.max(save.unlocked, number + 1));
    persist();
    const lines = [`Orbs ${r.orbs}/${r.orbsTotal}: ${r.base} points`, `Time ${r.seconds}s: +${r.timeBonus}`,
                   `Hearts: +${r.heartBonus}`, r.orbBonus ? `All orbs: +${r.orbBonus}` : null,
                   `Total: ${r.total}${r.total > previous ? ' (new best!)' : ` (best ${previous})`}`].filter(Boolean);
    if (number === LEVELS.length) {
      const total = Object.values(save.best).reduce((a, b) => a + b, 0);
      $('#victory-summary').textContent = `${lines.join(' • ')} • Best total across caverns: ${total}`;
      if (testMode) showScreen('victory'); else setTimeout(() => showScreen('victory'), 600);
    } else {
      $('#complete-summary').textContent = lines.join(' • ');
      if (testMode) showScreen('complete'); else setTimeout(() => showScreen('complete'), 600);
    }
  }

  function update() {
    if (screen === 'playing') {
      if (input.consume('pause')) {
        showScreen('paused');
        return;
      }
      stepWorld(world, input.sample());
      handleEvents(world.events);
      particles.update();
      if (shake > 0) shake = Math.max(0, shake - 0.25);
      if (flash > 0) flash -= 1;
    } else if (screen === 'paused') {
      if (input.consume('pause')) {
        showScreen('playing');
        audio.startMusic();
      }
    } else {
      input.consume('pause');
    }
  }

  function draw() {
    renderer.render(world, { particles, shake: save.settings.shake ? shake : 0, flash, fps: save.settings.showFps ? fps : 0 });
  }

  function crash(message) {
    if (crashed) return;
    crashed = true;
    $('#error-message').textContent = String(message || 'Unknown error').slice(0, 300);
    showScreen('error');
  }

  function frame(time) {
    if (crashed) return;
    try {
      const delta = lastTime ? Math.min(250, time - lastTime) : STEP_MS;
      lastTime = time;
      if (!testMode) {
        accumulator += delta;
        let steps = 0;
        while (accumulator >= STEP_MS && steps < MAX_STEPS_PER_FRAME) {
          update();
          accumulator -= STEP_MS;
          steps += 1;
        }
        if (steps === MAX_STEPS_PER_FRAME) accumulator = 0;
      }
      fpsFrames += 1;
      fpsTime += delta;
      if (fpsTime >= 1000) {
        fps = Math.round((fpsFrames * 1000) / fpsTime);
        fpsFrames = 0;
        fpsTime = 0;
      }
      draw();
    } catch (error) {
      console.error(error);
      crash(error && error.message);
      return;
    }
    requestAnimationFrame(frame);
  }

  function resize() {
    const scale = Math.min(window.innerWidth / 320, window.innerHeight / 180);
    // Whole-number scaling keeps pixels crisp; below 2x it would waste most of a
    // phone's width, so small screens use the exact fit instead.
    const integer = scale >= 2 ? Math.floor(scale) : scale;
    canvas.style.width = `${Math.floor(320 * integer)}px`;
    canvas.style.height = `${Math.floor(180 * integer)}px`;
    doc.documentElement.style.setProperty('--scale', String(integer));
  }

  doc.addEventListener('click', (event) => {
    const target = event.target.closest('button');
    if (!target) return;
    audio.unlock();
    audio.play('menu');
    if (target.dataset.level) {
      startLevel(Number(target.dataset.level));
      return;
    }
    const action = target.dataset.action;
    const actions = {
      play: () => startLevel(Math.min(save.unlocked, LEVELS.length) - 1),
      levels: () => { renderLevelSelect(); showScreen('levels'); },
      settings: () => { settingsReturn = screen; applySettings(); showScreen('settings'); },
      howto: () => showScreen('howto'),
      back: () => showScreen(settingsReturn === 'paused' && screen === 'settings' ? 'paused' : 'title'),
      resume: () => { showScreen('playing'); audio.startMusic(); },
      pause: () => showScreen('paused'),
      restart: () => startLevel(world.levelIndex),
      quit: () => { world = createWorld(0); showScreen('title'); },
      next: () => startLevel(world.levelIndex + 1),
      replay: () => startLevel(world.levelIndex),
      retry: () => startLevel(world.levelIndex),
      title: () => { world = createWorld(0); showScreen('title'); },
      reload: () => location.reload(),
      reset: () => { save = { ...save, unlocked: 1, best: {} }; persist(); renderLevelSelect(); toast('Progress reset.'); },
    };
    if (actions[action]) actions[action]();
  });

  for (const key of ['master', 'music', 'sfx']) {
    $(`#set-${key}`).addEventListener('input', (event) => {
      save.settings[key] = Number(event.target.value) / 100;
      applySettings();
      persist();
    });
  }
  for (const key of ['shake', 'reducedFlashing', 'showFps']) {
    $(`#set-${key}`).addEventListener('change', (event) => {
      save.settings[key] = event.target.checked;
      persist();
    });
  }
  $('#set-touch').addEventListener('change', (event) => {
    save.settings.touch = event.target.value;
    applySettings();
    persist();
  });
  for (const button of doc.querySelectorAll('#touch [data-touch]')) input.bindTouch(button, button.dataset.touch);
  window.addEventListener('keydown', (event) => {
    if (event.code === 'Escape' && ['settings', 'levels', 'howto'].includes(screen)) {
      showScreen(settingsReturn === 'paused' && screen === 'settings' ? 'paused' : 'title');
    }
  });
  doc.addEventListener('visibilitychange', () => {
    if (doc.hidden) {
      if (screen === 'playing') showScreen('paused');
      audio.suspend();
    } else {
      audio.resume();
    }
  });
  window.addEventListener('resize', resize);
  window.addEventListener('error', (event) => crash(event.message));
  window.addEventListener('unhandledrejection', (event) => crash(event.reason && event.reason.message));

  function loadSprites() {
    const embedded = window.GLOWMOSS_ASSETS;
    const image = new Image();
    const metaPromise = embedded ? Promise.resolve(embedded.sheet)
      : fetch('../build/assets/sprites.json').then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
    return metaPromise.then((meta) => new Promise((resolve, reject) => {
      image.onload = () => resolve(indexSheet(image, meta));
      image.onerror = () => reject(new Error('sprite image failed to load'));
      image.src = embedded ? embedded.sheetImage : '../build/assets/sprites.png';
    }));
  }

  loadSprites().then((sheet) => renderer.setSheet(sheet)).catch(() => toast('Sprites could not be loaded; using simple shapes.'));
  applySettings();
  resize();
  showScreen('title');
  $('#continue-label').textContent = save.unlocked > 1 ? `Continue (cavern ${save.unlocked})` : 'Play';
  toast(loaded.notice);
  requestAnimationFrame(frame);

  window.__glowmoss = {
    testMode,
    step(n = 1) {
      for (let i = 0; i < n; i++) update();
      draw();
      return this.state();
    },
    state() {
      const p = world.player;
      return { screen, level: world.levelIndex, frame: world.frame, status: world.status, score: world.score,
               hearts: world.hearts, orbs: world.orbs, x: p.x, y: p.y, events: eventLog.slice(-20),
               particles: particles.count(), sprites: renderer.hasSheet, audio: audio.available, save };
    },
    startLevel,
    crash,
  };
}

startApp();
