import test from 'node:test';
import assert from 'node:assert/strict';
import { createWorld, stepWorld } from '../../src/game/world.js';
import { createParticles, seededRandom } from '../../src/engine/particles.js';

test('crowded world stays fast and finite', () => {
  const world = createWorld(2);
  const template = world.enemies.find((e) => e.kind === 'slime');
  for (let i = 0; i < 500; i++) world.enemies.push({ ...structuredClone(template), id: 1000 + i, x: 40 + (i % 60) * 18 });
  for (let i = 0; i < 300; i++) world.projectiles.push({ id: 5000 + i, x: 100 + i * 3, y: 120, w: 6, h: 6, vx: (i % 2 ? 1 : -1) * 1.2, life: 240 });
  world.player.invuln = 1e9;
  const random = seededRandom(42);
  const started = performance.now();
  const frames = 600;
  for (let f = 0; f < frames; f++) stepWorld(world, { left: random() < 0.3, right: random() < 0.6, jump: random() < 0.2 });
  const msPerFrame = (performance.now() - started) / frames;
  assert.ok(msPerFrame < 8, `simulation took ${msPerFrame.toFixed(3)} ms per frame with 500+ enemies`);
  for (const e of world.enemies) assert.ok(Number.isFinite(e.x) && Number.isFinite(e.y));
  assert.ok(Number.isFinite(world.player.x) && Number.isFinite(world.player.y));
  console.log(`stress: ${world.enemies.length} enemies, ${msPerFrame.toFixed(3)} ms per simulated frame`);
});

test('10,000 frames of random input never produce invalid state', () => {
  for (let level = 0; level < 3; level++) {
    const world = createWorld(level);
    const random = seededRandom(1000 + level);
    for (let f = 0; f < 10000 && world.status === 'playing'; f++) {
      stepWorld(world, { left: random() < 0.35, right: random() < 0.55, jump: random() < 0.25 });
      const p = world.player;
      assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.vx) && Number.isFinite(p.vy));
      assert.ok(world.hearts >= 0 && world.hearts <= 3);
    }
  }
});

test('particle pool caps memory under a flood of effects', () => {
  const particles = createParticles(400);
  for (let i = 0; i < 1000; i++) particles.spawn(10, 10, { count: 20 });
  assert.equal(particles.count(), 400);
  for (let i = 0; i < 100; i++) particles.update();
  assert.equal(particles.count(), 0);
});
