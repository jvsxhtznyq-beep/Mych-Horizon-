import test from 'node:test';
import assert from 'node:assert/strict';
import { createWorld, stepWorld, POINTS, MAX_HEARTS, INVULN_FRAMES } from '../../src/game/world.js';

const IDLE = { left: false, right: false, jump: false };
const RIGHT = { left: false, right: true, jump: false };
const custom = (rows) => [{ name: 'Test', hint: 'test level', map: rows }];

function run(world, input, frames) {
  const events = [];
  for (let i = 0; i < frames; i++) {
    stepWorld(world, input);
    events.push(...world.events.map((e) => e.type));
  }
  return events;
}

test('orbs add score and the exit completes the level with bonuses', () => {
  const levels = custom(['##########', '#........#', '#P.o.o..E#', '##########']);
  const world = createWorld(0, { levels });
  const events = run(world, RIGHT, 240);
  assert.equal(world.orbs, 2);
  assert.equal(world.status, 'complete');
  assert.ok(events.includes('pickup') && events.includes('complete'));
  const r = world.result;
  assert.equal(r.base, 2 * POINTS.orb);
  assert.equal(r.orbBonus, POINTS.allOrbs);
  assert.equal(r.heartBonus, MAX_HEARTS * POINTS.heart);
  assert.equal(r.total, r.base + r.timeBonus + r.heartBonus + r.orbBonus);
});

test('landing on an enemy defeats it and bounces; touching it from the side hurts', () => {
  const stompLevel = custom(['#########', '#.......#', '#.......#', '#.......#', '#P..s..E#', '#########']);
  const world = createWorld(0, { levels: stompLevel });
  const slime = world.enemies[0];
  world.player.x = slime.x;
  world.player.y = slime.y - 40;
  run(world, IDLE, 30);
  assert.ok(slime.dead);
  assert.equal(world.score, POINTS.slime);
  const side = createWorld(0, { levels: stompLevel });
  const events = run(side, RIGHT, 60);
  assert.ok(events.includes('hurt'));
  assert.equal(side.hearts, MAX_HEARTS - 1);
  assert.ok(side.player.invuln > 0 && side.player.invuln <= INVULN_FRAMES);
});

test('falling into a pit costs a heart and respawns at the last checkpoint', () => {
  const levels = custom(['##########', '#........#', '#P.c....E#', '####..####', '#........#']);
  const world = createWorld(0, { levels });
  run(world, RIGHT, 30);
  assert.ok(world.checkpoints[0].active);
  const events = [];
  for (let i = 0; i < 200 && !events.includes('respawn'); i++) {
    stepWorld(world, RIGHT);
    events.push(...world.events.map((e) => e.type));
  }
  assert.ok(events.includes('fall') && events.includes('respawn'));
  assert.equal(world.hearts, MAX_HEARTS - 1);
  assert.equal(world.player.x, world.respawn.x);
});

test('losing the last heart ends the game', () => {
  const levels = custom(['##########', '#........#', '#P......E#', '##^^^^^^##', '##########']);
  const world = createWorld(0, { levels, hearts: 1 });
  world.player.x = 3 * 16;
  const events = run(world, IDLE, 120);
  assert.equal(world.status, 'gameover');
  assert.ok(events.includes('gameover'));
});

test('turrets fire on a rhythm and spores hurt', () => {
  const levels = custom(['############', '#....E.....#', '#..........#', '#P........t#', '############']);
  const world = createWorld(0, { levels });
  const events = run(world, IDLE, 400);
  assert.ok(events.filter((e) => e === 'shoot').length >= 2);
  assert.ok(events.includes('hurt'));
});

test('simulation is deterministic and the world can be cloned', () => {
  const inputs = Array.from({ length: 3000 }, (_, i) => ({ left: i % 400 > 330, right: i % 400 < 300, jump: i % 50 < 12 }));
  const a = createWorld(1);
  const b = createWorld(1);
  for (const input of inputs) {
    stepWorld(a, input);
    stepWorld(b, input);
  }
  const snapshot = (w) => JSON.stringify({ p: w.player, s: w.score, h: w.hearts, e: w.enemies, f: w.frame, st: w.status });
  assert.equal(snapshot(a), snapshot(b));
  const copy = structuredClone(a);
  assert.equal(snapshot(copy), snapshot(a));
});
