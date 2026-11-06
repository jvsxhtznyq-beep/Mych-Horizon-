import test from 'node:test';
import assert from 'node:assert/strict';
import { createStore, memoryStorage, sanitizeSave, defaultSave, SAVE_KEY, DEFAULT_SETTINGS } from '../../src/engine/storage.js';

function backendWith(value) {
  const backend = { available: true, data: new Map(value === undefined ? [] : [[SAVE_KEY, value]]) };
  backend.getItem = (k) => (backend.data.has(k) ? backend.data.get(k) : null);
  backend.setItem = (k, v) => backend.data.set(k, v);
  return backend;
}

test('fresh storage gives defaults and saves round-trip', () => {
  const backend = backendWith(undefined);
  const store = createStore(3, backend);
  const { save, notice } = store.load();
  assert.deepEqual(save, defaultSave());
  assert.equal(notice, null);
  save.unlocked = 2;
  save.best[1] = 1234;
  assert.ok(store.write(save).ok);
  assert.deepEqual(createStore(3, backend).load().save.best, { 1: 1234 });
});

test('damaged JSON is reset with a notice', () => {
  const { save, notice } = createStore(3, backendWith('{not json')).load();
  assert.deepEqual(save, defaultSave());
  assert.match(notice, /damaged/);
});

test('tampered values are repaired, not trusted', () => {
  const raw = { version: 1, unlocked: 99, best: { 1: 500, 7: 10, 2: -5, x: 3 }, plays: 'many',
                settings: { master: 7, music: -1, sfx: 'loud', shake: 'yes', touch: 'sideways', showFps: true } };
  const { save, problems } = sanitizeSave(raw, 3);
  assert.equal(save.unlocked, 3);
  assert.deepEqual(save.best, { 1: 500 });
  assert.equal(save.settings.master, 1);
  assert.equal(save.settings.music, 0);
  assert.equal(save.settings.sfx, DEFAULT_SETTINGS.sfx);
  assert.equal(save.settings.shake, DEFAULT_SETTINGS.shake);
  assert.equal(save.settings.touch, 'auto');
  assert.equal(save.settings.showFps, true);
  assert.equal(save.plays, 0);
  assert.ok(problems.length >= 3);
});

test('unavailable or failing storage is reported, never thrown', () => {
  const { notice } = createStore(3, memoryStorage()).load();
  assert.match(notice, /unavailable/);
  const full = backendWith(undefined);
  full.setItem = () => { throw new Error('QuotaExceededError'); };
  const result = createStore(3, full).write(defaultSave());
  assert.equal(result.ok, false);
  assert.match(result.notice, /could not be saved/);
  const broken = { available: true, getItem: () => { throw new Error('SecurityError'); }, setItem: () => {} };
  assert.match(createStore(3, broken).load().notice, /could not be read/);
});
