import test from 'node:test';
import assert from 'node:assert/strict';
import { LEVELS, parseLevel } from '../../src/game/levels.js';

test('every shipped level parses without errors', () => {
  assert.ok(LEVELS.length >= 3);
  for (const def of LEVELS) {
    const level = parseLevel(def);
    assert.deepEqual(level.errors, [], def.name);
    assert.ok(level.objects.some((o) => o.kind === 'o'), `${def.name} has orbs`);
    assert.ok(def.hint.length > 20, `${def.name} has a hint`);
  }
});

test('validation rejects malformed maps with clear messages', () => {
  const cases = [
    [{ map: ['#####', '#P.E', '#####'] }, 'row 2 has 4 columns, expected 5'],
    [{ map: ['#####', '#..E#', '#####'] }, "exactly one player start 'P' (found 0)"],
    [{ map: ['#####', '#P..#', '#####'] }, "needs an exit 'E'"],
    [{ map: ['#####', '#PxE#', '#####'] }, "unknown character 'x' at row 2, column 3"],
    [{ map: [] }, 'level has no map rows'],
  ];
  for (const [def, expected] of cases) {
    const errors = parseLevel(def).errors.join(' | ');
    assert.ok(errors.includes(expected), `${expected} not in ${errors}`);
  }
});
