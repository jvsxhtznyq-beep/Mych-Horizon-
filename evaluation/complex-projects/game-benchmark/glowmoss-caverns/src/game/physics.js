// Tile physics: axis-separated movement with AABB collision against a tile grid.
// Speeds stay below one tile per frame, so checking the destination row or column
// is enough to prevent tunneling.

export const TILE = 16;
export const T_EMPTY = 0;
export const T_SOLID = 1;
export const T_ONEWAY = 2;
export const T_SPIKE = 3;

export const PHYS = Object.freeze({
  gravity: 0.25,
  maxFall: 5,
  runAccel: 0.2,
  runDecel: 0.3,
  airAccel: 0.15,
  maxRun: 1.6,
  jumpVel: -4.7,
  jumpCut: 0.45,
  stompBounce: -3.6,
  coyoteFrames: 6,
  bufferFrames: 6,
});

export function tileAt(level, tx, ty) {
  if (tx < 0 || tx >= level.width) return T_SOLID;
  if (ty < 0 || ty >= level.height) return T_EMPTY;
  return level.tiles[ty * level.width + tx];
}

export function isSolidTile(t) {
  return t === T_SOLID;
}

export function standingOn(body, level) {
  const feet = body.y + body.h;
  const ty = Math.round(feet / TILE);
  if (Math.abs(feet - ty * TILE) > 0.01) return false;
  const left = Math.floor(body.x / TILE);
  const right = Math.floor((body.x + body.w - 0.001) / TILE);
  for (let tx = left; tx <= right; tx++) {
    const t = tileAt(level, tx, ty);
    if (t === T_SOLID || t === T_ONEWAY) return true;
  }
  return false;
}

export function moveAndCollide(body, level) {
  const hit = { onGround: false, hitWall: false, hitCeiling: false };
  if (body.vx !== 0) {
    body.x += body.vx;
    const top = Math.floor(body.y / TILE);
    const bottom = Math.floor((body.y + body.h - 0.001) / TILE);
    const tx = body.vx > 0 ? Math.floor((body.x + body.w - 0.001) / TILE) : Math.floor(body.x / TILE);
    for (let ty = top; ty <= bottom; ty++) {
      if (isSolidTile(tileAt(level, tx, ty))) {
        body.x = body.vx > 0 ? tx * TILE - body.w : (tx + 1) * TILE;
        body.vx = 0;
        hit.hitWall = true;
        break;
      }
    }
  }
  const prevBottom = body.y + body.h;
  body.y += body.vy;
  const left = Math.floor(body.x / TILE);
  const right = Math.floor((body.x + body.w - 0.001) / TILE);
  if (body.vy > 0) {
    const ty = Math.floor((body.y + body.h - 0.001) / TILE);
    for (let tx = left; tx <= right; tx++) {
      const t = tileAt(level, tx, ty);
      if (isSolidTile(t) || (t === T_ONEWAY && prevBottom <= ty * TILE + 0.001)) {
        body.y = ty * TILE - body.h;
        body.vy = 0;
        hit.onGround = true;
        break;
      }
    }
  } else if (body.vy < 0) {
    const ty = Math.floor(body.y / TILE);
    for (let tx = left; tx <= right; tx++) {
      if (isSolidTile(tileAt(level, tx, ty))) {
        body.y = (ty + 1) * TILE;
        body.vy = 0;
        hit.hitCeiling = true;
        break;
      }
    }
  }
  if (!hit.onGround && body.vy === 0) hit.onGround = standingOn(body, level);
  return hit;
}

export function overlaps(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

export function touchesTile(body, level, kind, inset = 3) {
  const left = Math.floor((body.x + inset) / TILE);
  const right = Math.floor((body.x + body.w - inset - 0.001) / TILE);
  const top = Math.floor((body.y + inset) / TILE);
  const bottom = Math.floor((body.y + body.h - 0.001) / TILE);
  for (let ty = top; ty <= bottom; ty++) {
    for (let tx = left; tx <= right; tx++) if (tileAt(level, tx, ty) === kind) return true;
  }
  return false;
}
