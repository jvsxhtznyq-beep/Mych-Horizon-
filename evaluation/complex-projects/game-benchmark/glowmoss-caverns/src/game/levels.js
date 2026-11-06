// Level data as text maps, and a parser that validates them.
// Legend: '#' rock, '=' one-way ledge, '^' spikes, 'P' player start, 'E' exit,
// 'o' glowmoss orb, '*' heart crystal, 'c' checkpoint, 's' slime, 'b' bat,
// 't' spore turret facing left, 'T' spore turret facing right, '.' empty.

import { TILE, T_EMPTY, T_SOLID, T_ONEWAY, T_SPIKE } from './physics.js';

const TILE_CODES = { '.': T_EMPTY, '#': T_SOLID, '=': T_ONEWAY, '^': T_SPIKE };
const OBJECT_CODES = new Set(['P', 'E', 'o', '*', 'c', 's', 'b', 't', 'T']);
export const MAX_LEVEL_SIZE = { width: 400, height: 64 };

export const LEVELS = [
  {
    name: 'Lantern Path',
    hint: 'Run and jump with the arrow keys and Space, a gamepad or the on-screen buttons. Collect glowmoss orbs and reach the glowing door.',
    map: [
      '############################################################',
      '#..........................................................#',
      '#..........................................................#',
      '#..........................................................#',
      '#..........................................................#',
      '#..........................................................#',
      '#..........................................................#',
      '#...............................................o.o........#',
      '#..............o.o.o........ooo.......*........#####.....E.#',
      '#.P...........#######...........oo.s.===......#######...####',
      '#.........###.........######...######.........##########...#',
      '#######..####.........######...######.......################',
      '#######..####^^^^^^^^^######...######^^^^^^^################',
    ],
  },
  {
    name: 'Echo Hollow',
    hint: 'Bats bob up and down. Jump onto ledges from below, and stomp enemies by landing on them.',
    map: [
      '######################################################################',
      '#....................................................................#',
      '#....................................................................#',
      '#...........................oo.......................................#',
      '#..........b...............====..........b...........ooo.............#',
      '#......................................................===.....E.....#',
      '#..................ooo.............===.............===.......#########',
      '#.................=====.......................===....................#',
      '#..........o.o..........................c............................#',
      '#.P.......=====..........s............#######...........s............#',
      '#######..........################....#########....##############.....#',
      '#######^^^^^^^^^^################^^^^#########^^^^##############^^^^^#',
      '######################################################################',
    ],
  },
  {
    name: 'Spore Galleries',
    hint: 'Turrets fire spores on a rhythm. Time your runs, and grab heart crystals when you are hurt.',
    map: [
      '##########################################################################',
      '#........................................................................#',
      '#........................................................................#',
      '#.......................................ooo..............................#',
      '#......................................=====.............*...............#',
      '#...............ooo............................................ooo.......#',
      '#..............=====.........*.............c..............=====......E...#',
      '#...........................====.......................................###',
      '#.P......o.o..................................b..........................#',
      '#.......#####........T................................t..........s.......#',
      '#######.......#############^^^#####...########....#######...##########...#',
      '#######^^^^^^^#############^^^#####^^^########^^^^#######^^^##########^^^#',
      '##########################################################################',
    ],
  },
];

export function parseLevel(def) {
  const errors = [];
  const rows = Array.isArray(def?.map) ? def.map : [];
  if (!rows.length) errors.push('level has no map rows');
  const width = rows[0]?.length || 0;
  const height = rows.length;
  if (width > MAX_LEVEL_SIZE.width || height > MAX_LEVEL_SIZE.height) errors.push(`level is larger than ${MAX_LEVEL_SIZE.width}x${MAX_LEVEL_SIZE.height}`);
  const tiles = new Uint8Array(Math.max(0, width * height));
  const objects = [];
  rows.forEach((row, y) => {
    if (typeof row !== 'string' || row.length !== width) {
      errors.push(`row ${y + 1} has ${row?.length} columns, expected ${width}`);
      return;
    }
    [...row].forEach((ch, x) => {
      if (ch in TILE_CODES) tiles[y * width + x] = TILE_CODES[ch];
      else if (OBJECT_CODES.has(ch)) objects.push({ kind: ch, x: x * TILE, y: y * TILE, tx: x, ty: y });
      else errors.push(`unknown character '${ch}' at row ${y + 1}, column ${x + 1}`);
    });
  });
  const starts = objects.filter((o) => o.kind === 'P');
  if (starts.length !== 1) errors.push(`level needs exactly one player start 'P' (found ${starts.length})`);
  if (!objects.some((o) => o.kind === 'E')) errors.push("level needs an exit 'E'");
  return { name: def?.name || 'Untitled', hint: def?.hint || '', width, height, tiles, objects, errors };
}
