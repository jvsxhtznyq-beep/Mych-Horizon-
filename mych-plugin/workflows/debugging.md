# Debugging Workflow

For bugs, failures and unexpected behavior whose cause is not yet established. The rule that governs everything here: **investigate before changing code.** A fix without a reproduced failure and an identified cause is a guess. The Engineer leads; the Researcher joins for unfamiliar errors; the Architect joins when the cause is structural.

When the cause and the fix are already clear and confined to one place, use [lightweight-task.md](lightweight-task.md) instead, and still add a regression test.

## Contents

- [Steps](#steps)
- [Rules](#rules)
- [Special cases](#special-cases)
- [Report](#report)

## Steps

Keep an [investigation-log.md](../templates/investigation-log.md) when more than one hypothesis is in play.

1. **Capture the symptom precisely.** Expected versus actual behavior; exact error text and stack trace; frequency (always, sometimes, once); environment (versions, configuration, data); when it started; what changed around that time (deploys, dependency updates, configuration, data volume).
2. **Reproduce.** Find the smallest input and environment that trigger the failure, ideally as an automated test or a one-line command. If it cannot be reproduced, gather more evidence before touching code: logs, metrics, traces, the exact failing inputs; add non-destructive diagnostic logging if needed; narrow the conditions (data shape, timing, concurrency, environment).
3. **Isolate.** Narrow where the fault lives: bisect history (`git bisect` with the reproduction), divide the code path in halves, compare a working and a failing environment, disable components one at a time, minimize the input.
4. **Hypothesize.** List candidate causes with the evidence for and against each. Rank them by likelihood and by the cost of testing them. Prefer hypotheses that explain *all* observations.
5. **Test one hypothesis at a time.** Design an experiment whose outcome would refute the hypothesis: a targeted log line, an assertion, a debugger breakpoint, a controlled input. Change one variable per experiment and record the result.
6. **Identify the root cause.** Distinguish the trigger (what made it visible) from the cause (what is actually wrong). Ask why repeatedly until the answer is something you can fix at its source. Check whether the same mistake exists elsewhere.
7. **Fix the cause.** Make the smallest change that removes the cause, not the symptom. Do not mix the fix with refactoring.
8. **Add a regression test** that fails without the fix and passes with it. If no test framework exists, record a reproducible manual check.
9. **Verify.** The reproduction now passes; the relevant test suite passes; no new warnings or errors appeared; the original symptom is gone in the environment where it was reported, when that environment is reachable.
10. **Report** using the format [below](#report).

## Rules

- Never change several things at once while investigating; you will not know which change mattered.
- Never silence the symptom: no blanket exception handlers, no retries that hide a deterministic failure, no skipped or loosened tests.
- Never claim a root cause you have not demonstrated. If evidence is incomplete, present the most likely cause as a hypothesis with its supporting evidence and the experiment that would confirm it.
- Revert diagnostic code that should not ship.
- When two investigation rounds fail to narrow the problem, step back: re-read the symptom, question an assumption, or add the Researcher or Architect.

## Special cases

- **Flaky failures:** treat flakiness as a bug. Look for order dependence, shared state, time and time-zone assumptions, randomness without seeds, race conditions, network calls in tests, and resource exhaustion. Run the test repeatedly to measure the failure rate before and after the fix.
- **Production-only failures:** start read-only: logs, metrics, traces, configuration differences, data differences. Any change in production, including diagnostic changes, follows [sensitive-change.md](sensitive-change.md) and needs approval.
- **Performance regressions:** use [performance-investigation.md](performance-investigation.md).
- **Failures in dependencies:** confirm with a minimal reproduction outside the project; check the dependency's issue tracker and changelog; prefer a documented workaround or version pin over patching vendored code, and record the decision.
- **Cannot run code:** reason from code and logs, state clearly that nothing was reproduced or executed, mark conclusions as hypotheses, and give the owner the reproduction and verification commands.

## Report

```text
Symptom:    checkout returns HTTP 500 for carts with a discounted item and free shipping
Reproduced: tests/test_checkout.py::test_discount_with_free_shipping (failed before the fix)
Root cause: shipping total was None when free shipping applied; the discount calculation added None
Fix:        shipping total defaults to Decimal("0") in pricing/shipping.py
Evidence:   regression test passes; pytest tests/ -> 212 passed; reproduction script returns 200
Residual:   the same None pattern exists in legacy/export.py (not fixed; reported for follow-up)
```
