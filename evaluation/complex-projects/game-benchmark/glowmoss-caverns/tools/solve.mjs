// Level solver: beam search over short input "macros" using the real game
// simulation. A level counts as completable when the solver reaches the exit
// without taking damage. The found input plan is replayed by the browser tests.
//
// Usage: node tools/solve.mjs [--level N] [--width 400]

import { createWorld, stepWorld } from '../src/game/world.js';
import { TILE, T_SOLID, tileAt } from '../src/game/physics.js';
import { LEVELS } from '../src/game/levels.js';

export const MACRO_FRAMES = 6;
export const ACTIONS = [
  { left: false, right: true, jump: false },
  { left: false, right: true, jump: true },
  { left: false, right: false, jump: false },
  { left: false, right: false, jump: true },
  { left: true, right: false, jump: false },
  { left: true, right: false, jump: true },
];

function distanceMap(level, exit) {
  const { width, height } = level;
  const dist = new Float64Array(width * height).fill(Infinity);
  const queue = [];
  const ex = Math.floor((exit.x + exit.w / 2) / TILE);
  for (let ty = Math.floor(exit.y / TILE); ty <= Math.floor((exit.y + exit.h - 1) / TILE); ty++) {
    if (ty >= 0 && ty < height) {
      dist[ty * width + ex] = 0;
      queue.push(ty * width + ex);
    }
  }
  for (let head = 0; head < queue.length; head++) {
    const cell = queue[head];
    const cx = cell % width;
    const cy = (cell - cx) / width;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = cx + dx;
      const ny = cy + dy;
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
      const next = ny * width + nx;
      if (dist[next] !== Infinity || tileAt(level, nx, ny) === T_SOLID) continue;
      dist[next] = dist[cell] + 1;
      queue.push(next);
    }
  }
  return dist;
}

function clone(world) {
  const level = world.level;
  world.level = null;
  const copy = structuredClone(world);
  world.level = level;
  copy.level = level;
  return copy;
}

function stateKey(world) {
  const p = world.player;
  const dead = world.enemies.reduce((n, e) => n + (e.dead ? 1 : 0), 0);
  return [Math.round(p.x / 2), Math.round(p.y / 2), Math.round(p.vx * 4), Math.round(p.vy * 2), p.onGround ? 1 : 0,
          p.jumpHeldPrev ? 1 : 0, dead].join(',');
}

export function solveLevel(levelIndex, { width = 300, maxLayers = 600, levels = LEVELS } = {}) {
  const started = Date.now();
  const start = createWorld(levelIndex, { levels });
  const dist = distanceMap(start.level, start.exit);
  const hearts = start.hearts;
  const groundBelow = (w) => {
    // Is there something safe to land on below the player? Bottomless pits and spikes are not.
    const p = w.player;
    for (const x of [p.x + 1, p.x + p.w - 1]) {
      const tx = Math.floor(x / TILE);
      for (let ty = Math.floor((p.y + p.h) / TILE); ty < w.level.height; ty++) {
        const t = tileAt(w.level, tx, ty);
        if (t === T_SOLID || t === 2) return true;
        if (t === 3) break;
      }
    }
    return false;
  };
  const score = (w) => {
    const p = w.player;
    const tx = Math.floor((p.x + p.w / 2) / TILE);
    const ty = Math.floor((p.y + p.h / 2) / TILE);
    const d = tx >= 0 && ty >= 0 && tx < w.level.width && ty < w.level.height ? dist[ty * w.level.width + tx] : Infinity;
    const danger = p.onGround || groundBelow(w) ? 0 : 40;
    return (Number.isFinite(d) ? d : 1e6) * 16 + danger - w.orbs * 0.5;
  };
  let beam = [{ world: start, plan: [] }];
  let expanded = 0;
  for (let layer = 0; layer < maxLayers; layer++) {
    const seen = new Set();
    const next = [];
    for (const node of beam) {
      for (let a = 0; a < ACTIONS.length; a++) {
        const w = clone(node.world);
        let alive = true;
        for (let f = 0; f < MACRO_FRAMES; f++) {
          stepWorld(w, ACTIONS[a]);
          expanded += 1;
          if (w.status === 'complete') {
            const plan = node.plan.concat(a);
            return { solved: true, level: levelIndex, plan, frames: w.frame, score: w.result.total, orbs: w.orbs,
                     orbsTotal: w.orbsTotal, expandedFrames: expanded, ms: Date.now() - started };
          }
          if (w.hearts < hearts || w.status !== 'playing') {
            alive = false;
            break;
          }
        }
        if (!alive) continue;
        const key = stateKey(w);
        if (seen.has(key)) continue;
        seen.add(key);
        next.push({ world: w, plan: node.plan.concat(a), h: score(w) });
      }
    }
    if (!next.length) break;
    next.sort((x, y) => x.h - y.h);
    // Keep the beam diverse: at most `perCell` states per tile, so one promising
    // but doomed area cannot crowd out every alternative.
    const perCell = new Map();
    beam = [];
    for (const node of next) {
      const p = node.world.player;
      const cell = Math.floor(p.x / TILE) + ',' + Math.floor(p.y / TILE);
      const count = perCell.get(cell) || 0;
      if (count >= 10) continue;
      perCell.set(cell, count + 1);
      beam.push(node);
      if (beam.length >= width) break;
    }
  }
  return { solved: false, level: levelIndex, expandedFrames: expanded, ms: Date.now() - started,
           best: beam.length ? { x: beam[0].world.player.x, y: beam[0].world.player.y } : null };
}

export function planToFrames(plan) {
  const frames = [];
  for (const a of plan) for (let f = 0; f < MACRO_FRAMES; f++) frames.push(ACTIONS[a]);
  return frames;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const only = args.includes('--level') ? Number(args[args.indexOf('--level') + 1]) - 1 : null;
  const width = args.includes('--width') ? Number(args[args.indexOf('--width') + 1]) : 300;
  let failed = 0;
  for (let i = 0; i < LEVELS.length; i++) {
    if (only !== null && i !== only) continue;
    const result = solveLevel(i, { width });
    if (!result.solved) failed += 1;
    console.log(JSON.stringify({ ...result, plan: result.plan ? `${result.plan.length} macros` : undefined }));
  }
  process.exitCode = failed ? 1 : 0;
}
