import test from 'node:test';
import assert from 'node:assert/strict';
import { solveLevel } from '../../tools/solve.mjs';
import { LEVELS } from '../../src/game/levels.js';

for (let i = 0; i < LEVELS.length; i++) {
  test(`level ${i + 1} (${LEVELS[i].name}) can be completed without taking damage`, { timeout: 120000 }, () => {
    const result = solveLevel(i);
    assert.ok(result.solved, `solver failed: ${JSON.stringify(result)}`);
    assert.ok(result.frames < 60 * 120, 'completes in under two minutes of game time');
  });
}
