import test from 'node:test';
import assert from 'node:assert/strict';
import { moveAndCollide, standingOn, touchesTile, overlaps, PHYS, TILE, T_SPIKE } from '../../src/game/physics.js';
import { parseLevel } from '../../src/game/levels.js';

const map = (rows) => parseLevel({ map: rows.concat(['#P..E#']).length ? rows : rows });
const level = parseLevel({ map: [
  '##########',
  '#........#',
  '#...==...#',
  '#........#',
  '#P....E^.#',
  '##########',
] });

test('falling body lands on solid ground and reports it', () => {
  const body = { x: 20, y: 40, w: 10, h: 14, vx: 0, vy: 0 };
  let grounded = false;
  for (let i = 0; i < 120 && !grounded; i++) {
    body.vy = Math.min(PHYS.maxFall, body.vy + PHYS.gravity);
    grounded = moveAndCollide(body, level).onGround;
  }
  assert.ok(grounded);
  assert.equal(body.y + body.h, 5 * TILE);
  assert.ok(standingOn(body, level));
});

test('walls stop horizontal movement without tunneling at full speed', () => {
  const body = { x: 140, y: 5 * TILE - 14, w: 10, h: 14, vx: 0, vy: 0 };
  for (let i = 0; i < 60; i++) {
    body.vx = PHYS.maxRun * 3;
    moveAndCollide(body, level);
  }
  assert.equal(body.x + body.w, 9 * TILE);
});

test('one-way ledges let bodies pass from below and land from above', () => {
  const rising = { x: 70, y: 3 * TILE + 2, w: 10, h: 14, vx: 0, vy: -4 };
  moveAndCollide(rising, level);
  moveAndCollide(rising, level);
  assert.ok(rising.y < 3 * TILE, 'passed upward through the ledge');
  const falling = { x: 70, y: TILE, w: 10, h: 14, vx: 0, vy: 0 };
  let landed = false;
  for (let i = 0; i < 60 && !landed; i++) {
    falling.vy = Math.min(PHYS.maxFall, falling.vy + PHYS.gravity);
    landed = moveAndCollide(falling, level).onGround;
  }
  assert.equal(falling.y + falling.h, 2 * TILE);
});

test('ceilings stop upward movement', () => {
  const body = { x: 20, y: TILE + 4, w: 10, h: 14, vx: 0, vy: -4.7 };
  const hit = moveAndCollide(body, level);
  assert.ok(hit.hitCeiling);
  assert.equal(body.y, TILE);
});

test('spike and overlap detection', () => {
  assert.ok(touchesTile({ x: 7 * TILE + 2, y: 4 * TILE + 2, w: 10, h: 14 }, level, T_SPIKE));
  assert.ok(!touchesTile({ x: 2 * TILE, y: 4 * TILE + 2, w: 10, h: 14 }, level, T_SPIKE));
  assert.ok(overlaps({ x: 0, y: 0, w: 10, h: 10 }, { x: 9, y: 9, w: 5, h: 5 }));
  assert.ok(!overlaps({ x: 0, y: 0, w: 10, h: 10 }, { x: 10, y: 0, w: 5, h: 5 }));
  assert.ok(map);
});
