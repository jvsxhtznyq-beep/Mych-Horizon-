// The game world: a deterministic simulation stepped at 60 updates per second.
// The world holds only plain data (structuredClone-able), so the level solver and
// tests can copy and replay it. Side effects (sound, particles, saving) are left
// to the caller through the events list filled during each step.

import { LEVELS, parseLevel } from './levels.js';
import { PHYS, TILE, T_SPIKE, moveAndCollide, overlaps, tileAt, touchesTile, T_SOLID, T_ONEWAY } from './physics.js';

export const MAX_HEARTS = 3;
export const POINTS = Object.freeze({ orb: 10, crystal: 50, slime: 100, bat: 120, turret: 150, allOrbs: 500, heart: 100 });
export const TURRET_PERIOD = 120;
export const INVULN_FRAMES = 90;

export function createWorld(levelIndex, options = {}) {
  const def = (options.levels || LEVELS)[levelIndex];
  if (!def) throw new Error(`no level ${levelIndex + 1}`);
  const level = parseLevel(def);
  if (level.errors.length) throw new Error(`level ${levelIndex + 1} is invalid: ${level.errors.join('; ')}`);
  const world = {
    levelIndex, level, frame: 0, score: 0, orbs: 0, orbsTotal: 0, hearts: options.hearts ?? MAX_HEARTS,
    status: 'playing', events: [], enemies: [], projectiles: [], pickups: [], checkpoints: [], exit: null,
    player: null, respawn: null, result: null, nextId: 1, stats: { stomps: 0, hurts: 0, falls: 0, jumps: 0 },
  };
  for (const obj of level.objects) {
    const id = world.nextId++;
    if (obj.kind === 'P') {
      world.player = { x: obj.x + 3, y: obj.y + 2, w: 10, h: 14, vx: 0, vy: 0, facing: 1, onGround: false, coyote: 0,
                       buffer: 0, jumpHeldPrev: false, invuln: 0, animTime: 0, landedFrame: -100 };
      world.respawn = { x: obj.x + 3, y: obj.y + 2 };
    } else if (obj.kind === 'E') {
      world.exit = { id, x: obj.x + 2, y: obj.y - 12, w: 12, h: 28 };
    } else if (obj.kind === 'o' || obj.kind === '*') {
      world.pickups.push({ id, kind: obj.kind === 'o' ? 'orb' : 'crystal', x: obj.x + 4, y: obj.y + 4, w: 8, h: 8, taken: false });
      if (obj.kind === 'o') world.orbsTotal += 1;
    } else if (obj.kind === 'c') {
      world.checkpoints.push({ id, x: obj.x + 2, y: obj.y, w: 12, h: 16, active: false });
    } else if (obj.kind === 's') {
      world.enemies.push({ id, kind: 'slime', x: obj.x + 2, y: obj.y + 6, w: 12, h: 10, vx: -0.5, vy: 0, dead: false, animTime: 0 });
    } else if (obj.kind === 'b') {
      world.enemies.push({ id, kind: 'bat', x: obj.x + 2, y: obj.y + 4, w: 12, h: 8, vx: 0.7, vy: 0, baseY: obj.y + 4,
                           minX: obj.x - 48, maxX: obj.x + 48, phase: (obj.tx * 7) % 60, dead: false, animTime: 0 });
    } else if (obj.kind === 't' || obj.kind === 'T') {
      world.enemies.push({ id, kind: 'turret', x: obj.x + 2, y: obj.y + 4, w: 12, h: 12, facing: obj.kind === 't' ? -1 : 1,
                           cooldown: 40 + (obj.tx * 13) % 60, dead: false, animTime: 0 });
    }
  }
  return world;
}

function emit(world, type, data = {}) {
  world.events.push({ type, frame: world.frame, ...data });
}

function hurtPlayer(world, fromX, reason) {
  const p = world.player;
  if (p.invuln > 0 || world.status !== 'playing') return;
  world.hearts -= 1;
  world.stats.hurts += 1;
  p.invuln = INVULN_FRAMES;
  p.vy = -3;
  p.vx = (p.x + p.w / 2 < fromX ? -1 : 1) * 1.6;
  emit(world, 'hurt', { reason, x: p.x, y: p.y });
  if (world.hearts <= 0) gameOver(world);
}

function gameOver(world) {
  world.status = 'gameover';
  emit(world, 'gameover');
}

function updatePlayer(world, input) {
  const p = world.player;
  const dir = (input.right ? 1 : 0) - (input.left ? 1 : 0);
  if (dir !== 0) {
    p.vx += dir * (p.onGround ? PHYS.runAccel : PHYS.airAccel);
    p.vx = Math.max(-PHYS.maxRun, Math.min(PHYS.maxRun, p.vx));
    p.facing = dir;
  } else {
    const decel = p.onGround ? PHYS.runDecel : PHYS.airAccel * 0.5;
    p.vx = Math.abs(p.vx) <= decel ? 0 : p.vx - Math.sign(p.vx) * decel;
  }
  const pressed = input.jump && !p.jumpHeldPrev;
  p.buffer = pressed ? PHYS.bufferFrames : Math.max(0, p.buffer - 1);
  p.coyote = p.onGround ? PHYS.coyoteFrames : Math.max(0, p.coyote - 1);
  if (p.buffer > 0 && p.coyote > 0) {
    p.vy = PHYS.jumpVel;
    p.buffer = 0;
    p.coyote = 0;
    world.stats.jumps += 1;
    emit(world, 'jump', { x: p.x, y: p.y + p.h });
  }
  if (p.jumpHeldPrev && !input.jump && p.vy < 0) p.vy *= PHYS.jumpCut;
  p.vy = Math.min(PHYS.maxFall, p.vy + PHYS.gravity);
  const fallSpeed = p.vy;
  const wasGrounded = p.onGround;
  const hit = moveAndCollide(p, world.level);
  p.onGround = hit.onGround;
  if (p.onGround && !wasGrounded && fallSpeed > 2) {
    p.landedFrame = world.frame;
    emit(world, 'land', { x: p.x + p.w / 2, y: p.y + p.h });
  }
  p.jumpHeldPrev = !!input.jump;
  p.animTime += 1;
  if (p.invuln > 0) p.invuln -= 1;
}

function updateEnemy(world, e) {
  const level = world.level;
  e.animTime += 1;
  if (e.kind === 'slime') {
    e.vy = Math.min(PHYS.maxFall, e.vy + PHYS.gravity);
    const hit = moveAndCollide(e, level);
    const aheadX = e.vx > 0 ? e.x + e.w + 1 : e.x - 1;
    const below = tileAt(level, Math.floor(aheadX / TILE), Math.floor((e.y + e.h + 1) / TILE));
    if (hit.hitWall) e.vx = e.vx > 0 ? -0.5 : 0.5;
    else if (hit.onGround && below !== T_SOLID && below !== T_ONEWAY) e.vx = -e.vx;
    if (e.y > level.height * TILE + 64) e.dead = true;
  } else if (e.kind === 'bat') {
    e.x += e.vx;
    if (e.x < e.minX || e.x > e.maxX || touchesTile(e, level, T_SOLID, 0)) {
      e.x -= e.vx;
      e.vx = -e.vx;
    }
    e.y = e.baseY + Math.sin((world.frame + e.phase) * 0.08) * 10;
  } else if (e.kind === 'turret') {
    e.cooldown -= 1;
    if (e.cooldown <= 0) {
      e.cooldown = TURRET_PERIOD;
      world.projectiles.push({ id: world.nextId++, x: e.facing > 0 ? e.x + e.w : e.x - 6, y: e.y + 3, w: 6, h: 6,
                               vx: e.facing * 1.2, life: 240 });
      emit(world, 'shoot', { x: e.x, y: e.y });
    }
  }
}

function playerCollisions(world) {
  const p = world.player;
  for (const e of world.enemies) {
    if (e.dead || !overlaps(p, e)) continue;
    const stomping = p.vy > 0 && p.y + p.h - p.vy <= e.y + 6;
    if (stomping) {
      e.dead = true;
      p.vy = PHYS.stompBounce;
      world.score += POINTS[e.kind];
      world.stats.stomps += 1;
      emit(world, 'stomp', { kind: e.kind, x: e.x + e.w / 2, y: e.y + e.h / 2 });
    } else {
      hurtPlayer(world, e.x + e.w / 2, e.kind);
    }
  }
  for (const shot of world.projectiles) {
    if (shot.life > 0 && overlaps(p, shot)) {
      shot.life = 0;
      hurtPlayer(world, shot.x, 'spore');
    }
  }
  if (touchesTile(p, world.level, T_SPIKE, 3)) hurtPlayer(world, p.x + p.w / 2 - p.vx * 10, 'spikes');
  for (const item of world.pickups) {
    if (item.taken || !overlaps(p, item)) continue;
    item.taken = true;
    if (item.kind === 'orb') {
      world.orbs += 1;
      world.score += POINTS.orb;
      emit(world, 'pickup', { x: item.x, y: item.y });
    } else if (world.hearts < MAX_HEARTS) {
      world.hearts += 1;
      emit(world, 'heal', { x: item.x, y: item.y });
    } else {
      world.score += POINTS.crystal;
      emit(world, 'pickup', { x: item.x, y: item.y, crystal: true });
    }
  }
  for (const cp of world.checkpoints) {
    if (!cp.active && overlaps(p, cp)) {
      for (const other of world.checkpoints) other.active = false;
      cp.active = true;
      world.respawn = { x: cp.x + 1, y: cp.y + 2 };
      emit(world, 'checkpoint', { x: cp.x, y: cp.y });
    }
  }
  if (world.exit && overlaps(p, world.exit)) completeLevel(world);
}

function completeLevel(world) {
  const seconds = world.frame / 60;
  const timeBonus = Math.max(0, Math.round((180 - seconds) * 5));
  const heartBonus = world.hearts * POINTS.heart;
  const orbBonus = world.orbs === world.orbsTotal && world.orbsTotal > 0 ? POINTS.allOrbs : 0;
  world.result = { base: world.score, timeBonus, heartBonus, orbBonus, total: world.score + timeBonus + heartBonus + orbBonus,
                   seconds: Math.round(seconds * 10) / 10, orbs: world.orbs, orbsTotal: world.orbsTotal };
  world.score = world.result.total;
  world.status = 'complete';
  emit(world, 'complete', { total: world.result.total });
}

export function stepWorld(world, input) {
  world.events = [];
  if (world.status !== 'playing') return world;
  world.frame += 1;
  updatePlayer(world, input);
  for (const e of world.enemies) if (!e.dead) updateEnemy(world, e);
  for (const shot of world.projectiles) {
    if (shot.life <= 0) continue;
    shot.x += shot.vx;
    shot.life -= 1;
    if (touchesTile(shot, world.level, T_SOLID, 0)) {
      shot.life = 0;
      emit(world, 'puff', { x: shot.x, y: shot.y });
    }
  }
  world.projectiles = world.projectiles.filter((shot) => shot.life > 0);
  playerCollisions(world);
  const p = world.player;
  if (world.status === 'playing' && p.y > world.level.height * TILE + 32) {
    world.hearts -= 1;
    world.stats.falls += 1;
    emit(world, 'fall', { x: p.x, y: p.y });
    if (world.hearts <= 0) {
      gameOver(world);
    } else {
      Object.assign(p, { x: world.respawn.x, y: world.respawn.y, vx: 0, vy: 0, invuln: 60, onGround: false });
      emit(world, 'respawn', { x: p.x, y: p.y });
    }
  }
  return world;
}

export function levelCount(levels = LEVELS) {
  return levels.length;
}
