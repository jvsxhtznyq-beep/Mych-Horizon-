// Canvas renderer at a fixed internal resolution (320x180), scaled up by CSS
// with pixelated sampling. The level's tiles are drawn once to an offscreen
// canvas; sprites come from the sheet built with mych-pixel-art, with simple
// shapes as a fallback when the sheet is missing.

import { TILE, T_SOLID, T_ONEWAY, T_SPIKE, tileAt } from '../game/physics.js';
import { MAX_HEARTS } from '../game/world.js';
import { seededRandom } from './particles.js';

export const VIEW_W = 320;
export const VIEW_H = 180;
const COLORS = {
  bgTop: '#0d0b14', bgBottom: '#1e1a2e', rock: '#3b3456', rockLight: '#5d5a7a', rockDark: '#2a2140',
  moss: '#2bd67b', mossLight: '#a8ff9e', ledge: '#4a3a8c', spike: '#c9a3ff', hud: '#f2f0ff', heart: '#ff4f7a',
  cyan: '#5ee6e6', gold: '#ffd166',
};

export function indexSheet(image, meta) {
  const frames = meta.frames.map((f) => ({ name: f.filename, ...f.frame, duration: f.duration || 100 }));
  const tags = new Map(meta.meta.frameTags.map((t) => [t.name, { from: t.from, to: t.to, direction: t.direction }]));
  return { image, frames, tags };
}

function tagFrame(sheet, tag, time) {
  const info = sheet.tags.get(tag);
  if (!info) return null;
  const frames = sheet.frames.slice(info.from, info.to + 1);
  const total = frames.reduce((n, f) => n + f.duration, 0);
  let t = ((time * 1000) / 60) % total;
  for (const f of frames) {
    if (t < f.duration) return f;
    t -= f.duration;
  }
  return frames[frames.length - 1];
}

function makeCanvas(doc, w, h) {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  const c = doc.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

export function createRenderer(canvas, doc = globalThis.document) {
  const ctx = canvas.getContext('2d');
  canvas.width = VIEW_W;
  canvas.height = VIEW_H;
  ctx.imageSmoothingEnabled = false;
  let sheet = null;
  let tileCache = null;
  let tileLevel = null;
  const cam = { x: 0, y: 0, ready: false };

  function buildTiles(level) {
    const c = makeCanvas(doc, level.width * TILE, level.height * TILE);
    const g = c.getContext('2d');
    const random = seededRandom(level.width * 131 + level.height);
    for (let ty = 0; ty < level.height; ty++) {
      for (let tx = 0; tx < level.width; tx++) {
        const t = tileAt(level, tx, ty);
        const x = tx * TILE;
        const y = ty * TILE;
        if (t === T_SOLID) {
          g.fillStyle = COLORS.rock;
          g.fillRect(x, y, TILE, TILE);
          g.fillStyle = COLORS.rockDark;
          g.fillRect(x, y + TILE - 2, TILE, 2);
          for (let i = 0; i < 3; i++) {
            g.fillStyle = random() < 0.5 ? COLORS.rockLight : COLORS.rockDark;
            g.fillRect(x + Math.floor(random() * 14) + 1, y + Math.floor(random() * 12) + 2, 2, 1);
          }
          if (tileAt(level, tx, ty - 1) !== T_SOLID && ty > 0) {
            g.fillStyle = COLORS.moss;
            g.fillRect(x, y, TILE, 3);
            g.fillStyle = COLORS.mossLight;
            for (let i = 0; i < 4; i++) g.fillRect(x + Math.floor(random() * 15), y, 1, 1);
            if (random() < 0.4) {
              g.fillStyle = COLORS.moss;
              g.fillRect(x + Math.floor(random() * 14), y + 3, 1, 2 + Math.floor(random() * 3));
            }
          }
        } else if (t === T_ONEWAY) {
          g.fillStyle = COLORS.ledge;
          g.fillRect(x, y, TILE, 4);
          g.fillStyle = COLORS.moss;
          g.fillRect(x, y, TILE, 1);
          g.fillStyle = COLORS.rockDark;
          g.fillRect(x + 2, y + 4, 2, 3);
          g.fillRect(x + 12, y + 4, 2, 3);
        } else if (t === T_SPIKE) {
          g.fillStyle = COLORS.spike;
          for (let i = 0; i < 4; i++) {
            const sx = x + i * 4;
            for (let row = 0; row < 7; row++) g.fillRect(sx + Math.floor(row / 3), y + TILE - row - 1, Math.max(1, 4 - Math.floor(row / 2) * 1), 1);
          }
          g.fillStyle = COLORS.cyan;
          g.fillRect(x + 1, y + TILE - 7, 1, 1);
          g.fillRect(x + 9, y + TILE - 7, 1, 1);
        }
      }
    }
    return c;
  }

  function background(camX, camY, frame) {
    const grad = ctx.createLinearGradient(0, 0, 0, VIEW_H);
    grad.addColorStop(0, COLORS.bgTop);
    grad.addColorStop(1, COLORS.bgBottom);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, VIEW_W, VIEW_H);
    for (const [depth, color, spacing, length] of [[0.2, '#16122a', 23, 50], [0.45, '#211a3a', 37, 70]]) {
      ctx.fillStyle = color;
      const offset = Math.floor(camX * depth);
      for (let i = -1; i < VIEW_W / spacing + 2; i++) {
        const worldIndex = Math.floor(offset / spacing) + i;
        const h = 10 + ((worldIndex * 7919) % length);
        const x = worldIndex * spacing - offset;
        ctx.fillRect(x, 0, 6, h);
        ctx.fillRect(x + 2, h, 2, 6);
        ctx.fillRect(x + 1, VIEW_H - Math.floor(h * 0.6) - Math.floor(camY * depth * 0.2), 8, VIEW_H);
      }
    }
    for (let i = 0; i < 24; i++) {
      const x = (i * 53 - Math.floor(camX * 0.3)) % VIEW_W;
      const y = (i * 37 + Math.sin((frame + i * 20) * 0.03) * 6) % VIEW_H;
      ctx.fillStyle = i % 3 === 0 ? COLORS.cyan : COLORS.moss;
      ctx.globalAlpha = 0.25 + 0.2 * Math.sin((frame + i * 13) * 0.05);
      ctx.fillRect((x + VIEW_W) % VIEW_W, (y + VIEW_H) % VIEW_H, 1, 1);
    }
    ctx.globalAlpha = 1;
  }

  function glow(x, y, radius, color, strength) {
    const grad = ctx.createRadialGradient(x, y, 0, x, y, radius);
    grad.addColorStop(0, color);
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.globalAlpha = strength;
    ctx.fillStyle = grad;
    ctx.fillRect(x - radius, y - radius, radius * 2, radius * 2);
    ctx.globalAlpha = 1;
  }

  function sprite(tag, time, body, camX, camY, flip = false, fallback = '#ff00ff') {
    const x = Math.round(body.x + body.w / 2 - 8 - camX);
    const y = Math.round(body.y + body.h - 16 - camY);
    const frame = sheet ? tagFrame(sheet, tag, time) : null;
    if (!frame) {
      ctx.fillStyle = fallback;
      ctx.fillRect(Math.round(body.x - camX), Math.round(body.y - camY), body.w, body.h);
      return;
    }
    if (flip) {
      ctx.save();
      ctx.translate(x + 16, y);
      ctx.scale(-1, 1);
      ctx.drawImage(sheet.image, frame.x, frame.y, frame.w, frame.h, 0, 0, 16, 16);
      ctx.restore();
    } else {
      ctx.drawImage(sheet.image, frame.x, frame.y, frame.w, frame.h, x, y, 16, 16);
    }
  }

  function updateCamera(world) {
    const p = world.player;
    const maxX = Math.max(0, world.level.width * TILE - VIEW_W);
    const maxY = Math.max(0, world.level.height * TILE - VIEW_H);
    const targetX = Math.min(maxX, Math.max(0, p.x + p.w / 2 - VIEW_W / 2 + p.facing * 24));
    const targetY = Math.min(maxY, Math.max(0, p.y + p.h / 2 - VIEW_H / 2 - 8));
    if (!cam.ready) {
      cam.x = targetX;
      cam.y = targetY;
      cam.ready = true;
    }
    cam.x += (targetX - cam.x) * 0.12;
    cam.y += (targetY - cam.y) * 0.12;
    return { x: Math.round(cam.x), y: Math.round(cam.y) };
  }

  function hud(world, fps) {
    ctx.fillStyle = 'rgba(13,11,20,0.65)';
    ctx.fillRect(0, 0, VIEW_W, 14);
    for (let i = 0; i < MAX_HEARTS; i++) {
      ctx.fillStyle = i < world.hearts ? COLORS.heart : '#3b3456';
      const x = 4 + i * 10;
      ctx.fillRect(x, 4, 3, 3);
      ctx.fillRect(x + 4, 4, 3, 3);
      ctx.fillRect(x, 6, 7, 3);
      ctx.fillRect(x + 1, 9, 5, 1);
      ctx.fillRect(x + 2, 10, 3, 1);
    }
    ctx.font = '8px monospace';
    ctx.textBaseline = 'top';
    ctx.fillStyle = COLORS.mossLight;
    ctx.fillText(`ORBS ${world.orbs}/${world.orbsTotal}`, 40, 3);
    ctx.fillStyle = COLORS.gold;
    ctx.fillText(`SCORE ${world.score}`, 116, 3);
    ctx.fillStyle = COLORS.hud;
    ctx.fillText(`${(world.frame / 60).toFixed(1)}s`, 200, 3);
    ctx.fillText(world.level.name.toUpperCase().slice(0, 16), 236, 3);
    if (fps) {
      ctx.fillStyle = COLORS.cyan;
      ctx.fillText(`${fps} FPS`, 4, VIEW_H - 10);
    }
  }

  return {
    get hasSheet() { return !!sheet; },
    setSheet(next) { sheet = next; },
    resetCamera() { cam.ready = false; },
    render(world, { particles = null, shake = 0, flash = 0, fps = 0 } = {}) {
      if (tileLevel !== world.level) {
        tileCache = buildTiles(world.level);
        tileLevel = world.level;
        cam.ready = false;
      }
      const view = updateCamera(world);
      const sx = shake ? Math.round((Math.sin(world.frame * 12.9898) * 43758.5453 % 1) * shake) : 0;
      const sy = shake ? Math.round((Math.sin(world.frame * 78.233) * 12543.123 % 1) * shake) : 0;
      const camX = view.x + sx;
      const camY = view.y + sy;
      background(camX, camY, world.frame);
      ctx.drawImage(tileCache, camX, camY, VIEW_W, VIEW_H, 0, 0, VIEW_W, VIEW_H);
      const t = world.frame;
      for (const item of world.pickups) {
        if (item.taken) continue;
        const bob = Math.round(Math.sin((t + item.id * 9) * 0.08) * 2);
        glow(item.x + 4 - camX, item.y + 4 - camY, item.kind === 'orb' ? 12 : 16, item.kind === 'orb' ? COLORS.moss : COLORS.heart, 0.35);
        sprite(item.kind === 'orb' ? 'orb_glow' : 'crystal_shine', t, { ...item, y: item.y + 4 + bob }, camX, camY, false,
               item.kind === 'orb' ? COLORS.moss : COLORS.heart);
      }
      for (const cp of world.checkpoints) {
        if (cp.active) glow(cp.x + 6 - camX, cp.y + 4 - camY, 18, COLORS.cyan, 0.3);
        sprite(cp.active ? 'checkpoint_on' : 'checkpoint_off', t, cp, camX, camY, false, COLORS.cyan);
      }
      if (world.exit) {
        const e = world.exit;
        glow(e.x + e.w / 2 - camX, e.y + e.h / 2 - camY, 34, COLORS.mossLight, 0.35 + 0.1 * Math.sin(t * 0.05));
        ctx.fillStyle = COLORS.rockDark;
        ctx.fillRect(Math.round(e.x - camX) - 2, Math.round(e.y - camY), e.w + 4, e.h);
        ctx.fillStyle = COLORS.moss;
        ctx.fillRect(Math.round(e.x - camX), Math.round(e.y - camY) + 2, e.w, e.h - 2);
        ctx.fillStyle = COLORS.mossLight;
        ctx.fillRect(Math.round(e.x - camX) + 3, Math.round(e.y - camY) + 5 + Math.round(Math.sin(t * 0.1) * 2), e.w - 6, 2);
      }
      for (const enemy of world.enemies) {
        if (enemy.dead) continue;
        const tag = enemy.kind === 'slime' ? 'slime_walk' : enemy.kind === 'bat' ? 'bat_fly' : 'turret_idle';
        sprite(tag, enemy.animTime, enemy, camX, camY, enemy.kind === 'turret' ? enemy.facing > 0 : (enemy.vx || 0) > 0, '#ff8c42');
      }
      for (const shot of world.projectiles) {
        glow(shot.x + 3 - camX, shot.y + 3 - camY, 8, COLORS.gold, 0.4);
        sprite('spore_float', t, shot, camX, camY, false, COLORS.gold);
      }
      const p = world.player;
      if (!(p.invuln > 0 && Math.floor(p.invuln / 4) % 2 === 0)) {
        let tag = 'player_idle';
        if (p.invuln > 70) tag = 'player_hurt';
        else if (!p.onGround) tag = p.vy < 0 ? 'player_jump' : 'player_fall';
        else if (Math.abs(p.vx) > 0.2) tag = 'player_run';
        glow(p.x + p.w / 2 - camX, p.y - camY, 22, COLORS.gold, 0.18);
        sprite(tag, p.animTime, p, camX, camY, p.facing < 0, COLORS.ledge);
      }
      if (particles) particles.draw(ctx, camX, camY);
      hud(world, fps);
      if (flash > 0) {
        ctx.globalAlpha = Math.min(0.5, flash / 20);
        ctx.fillStyle = COLORS.heart;
        ctx.fillRect(0, 0, VIEW_W, VIEW_H);
        ctx.globalAlpha = 1;
      }
    },
  };
}
