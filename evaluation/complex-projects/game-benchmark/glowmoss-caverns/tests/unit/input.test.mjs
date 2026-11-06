import test from 'node:test';
import assert from 'node:assert/strict';
import { createInput, actionForCode } from '../../src/engine/input.js';

function fakeTarget() {
  const handlers = {};
  return {
    addEventListener: (type, fn) => { (handlers[type] ||= []).push(fn); },
    removeEventListener: (type, fn) => { handlers[type] = (handlers[type] || []).filter((h) => h !== fn); },
    fire: (type, event) => (handlers[type] || []).forEach((fn) => fn({ preventDefault() {}, repeat: false, ...event })),
  };
}

test('keys map to actions with alternatives', () => {
  assert.equal(actionForCode('ArrowLeft'), 'left');
  assert.equal(actionForCode('KeyD'), 'right');
  assert.equal(actionForCode('Space'), 'jump');
  assert.equal(actionForCode('KeyW'), 'jump');
  assert.equal(actionForCode('Escape'), 'pause');
  assert.equal(actionForCode('KeyQ'), null);
});

test('held keys, single-use presses and blur', () => {
  const target = fakeTarget();
  const win = fakeTarget();
  const input = createInput(target, win);
  target.fire('keydown', { code: 'ArrowRight' });
  target.fire('keydown', { code: 'Space' });
  assert.deepEqual(input.sample(), { left: false, right: true, jump: true });
  target.fire('keyup', { code: 'Space' });
  assert.equal(input.sample().jump, false);
  target.fire('keydown', { code: 'Escape' });
  assert.equal(input.consume('pause'), true);
  assert.equal(input.consume('pause'), false);
  target.fire('keydown', { code: 'Escape', repeat: true });
  assert.equal(input.consume('pause'), false, 'auto-repeat does not pause again');
  win.fire('blur', {});
  assert.equal(input.sample().right, false, 'blur releases held keys');
  input.dispose();
  target.fire('keydown', { code: 'ArrowLeft' });
  assert.equal(input.sample().left, false);
});
