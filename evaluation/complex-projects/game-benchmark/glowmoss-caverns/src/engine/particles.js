// Pooled particles for visual effects. A fixed pool caps memory and work;
// a seeded generator keeps effects reproducible in tests.

export function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function createParticles(max = 400, seed = 7) {
  const pool = Array.from({ length: max }, () => ({ alive: false, x: 0, y: 0, vx: 0, vy: 0, life: 0, maxLife: 1, color: '#fff', size: 1, gravity: 0 }));
  const random = seededRandom(seed);
  let cursor = 0;
  return {
    spawn(x, y, { count = 8, color = '#a8ff9e', speed = 1.5, life = 30, gravity = 0.05, size = 2, spread = Math.PI * 2, angle = 0 } = {}) {
      for (let i = 0; i < count; i++) {
        const p = pool[cursor];
        cursor = (cursor + 1) % max;
        const a = angle - spread / 2 + random() * spread;
        const v = speed * (0.4 + random() * 0.6);
        Object.assign(p, { alive: true, x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life, maxLife: life, color, size, gravity });
      }
    },
    update() {
      for (const p of pool) {
        if (!p.alive) continue;
        p.x += p.vx;
        p.y += p.vy;
        p.vy += p.gravity;
        p.life -= 1;
        if (p.life <= 0) p.alive = false;
      }
    },
    draw(ctx, camX, camY) {
      for (const p of pool) {
        if (!p.alive) continue;
        ctx.globalAlpha = Math.max(0, p.life / p.maxLife);
        ctx.fillStyle = p.color;
        ctx.fillRect(Math.round(p.x - camX), Math.round(p.y - camY), p.size, p.size);
      }
      ctx.globalAlpha = 1;
    },
    count() {
      return pool.reduce((n, p) => n + (p.alive ? 1 : 0), 0);
    },
    clear() {
      for (const p of pool) p.alive = false;
    },
  };
}
