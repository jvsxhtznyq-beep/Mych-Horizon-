# Testing Strategy

Which tests to write and run, chosen by risk; how to run them; and what to do when they fail. Not every project needs every level of testing. Every claimed result must come from a test that actually ran.

## Contents

- [Test levels](#test-levels)
- [Choosing tests by risk](#choosing-tests-by-risk)
- [Writing good tests](#writing-good-tests)
- [Running tests](#running-tests)
- [When tests fail](#when-tests-fail)
- [Special situations](#special-situations)

## Test levels

| Level | Proves | Use when | Cost |
|---|---|---|---|
| Unit | A function or class behaves correctly in isolation | Logic with branches, calculations, parsing, validation | Low |
| Integration | Components work together: code with the database, queue, file system or another service | Persistence, external interfaces, configuration wiring | Medium |
| End-to-end | A user task works through the real interface | Core user journeys, release confidence | High |
| Regression | A fixed bug stays fixed | Every bug fix | Low |
| Performance | Speed and resource use meet a target | Stated targets, hot paths, suspected regressions | Medium to high |
| Compatibility | Behavior holds across versions, platforms or browsers | Libraries, public APIs, supported-platform promises | Medium |
| Security | Unauthorized access is denied, malicious input is rejected | Authentication, authorization, input handling, sensitive data | Medium |
| Manual acceptance | A person confirms the result fits the need | Visual design, usability, anything automation cannot judge | Varies |

## Choosing tests by risk

Risk is the likelihood of a defect times the impact of that defect. Spend testing effort where risk is highest.

| Change | Minimum tests |
|---|---|
| Pure logic change | Unit tests for the changed behavior, including edge cases |
| Bug fix | A regression test that fails before the fix and passes after |
| Database query, schema or migration | Integration test against a real or faithful database; migration tested forward, and backward when supported |
| New or changed API | Contract or integration tests for success and error responses |
| User-facing flow | End-to-end test for the core path, plus manual acceptance for look and feel |
| Authentication, permissions or input handling | Security tests for denial and rejection cases |
| Performance-sensitive change | Before-and-after measurement under fixed conditions |
| Refactoring | The existing suite, or characterization tests written first |
| Dependency upgrade | The full suite; changelog review for breaking changes |

## Writing good tests

- Test behavior through public interfaces, not implementation details, so refactoring does not break tests needlessly.
- Make tests deterministic: control time, randomness, ordering and external calls.
- Keep tests independent: no reliance on execution order or shared mutable state.
- Name tests after the behavior they prove (`rejects_expired_token`, not `test3`).
- Cover error paths and boundaries: empty, maximum, invalid, duplicate, concurrent.
- Mock only what is slow, non-deterministic or external, never the unit under test.
- One reason to fail per test where practical, so a failure points at its cause.

## Running tests

1. Use the project's own commands (from the manifest, Makefile, task runner or CI configuration).
2. Run the narrowest relevant set first for fast feedback, then the broader suite before delivery.
3. Record the exact command and the result summary (counts of passed, failed, skipped) for the report.
4. Treat new warnings as findings.

## When tests fail

1. **Record the failure:** test name, command, error output, environment.
2. **Decide whether the change caused it.** Run the same test on the unchanged baseline (for example after `git stash`, restoring your work afterwards). A failure that exists without your change is pre-existing; report it separately and do not attribute it to your work.
3. **Investigate the cause** with [debugging.md](../workflows/debugging.md); do not guess.
4. **Correct the issue** when it is within the task's authority. A pre-existing failure outside the task's scope is reported, not silently fixed in the same change.
5. **Re-run** the failing test and then the relevant suite.
6. **Record remaining limitations:** tests still failing, tests not run and why.

## Special situations

- **Flaky tests:** treat them as defects. Measure the failure rate by repeated runs; find the source of nondeterminism; never mark the suite green by re-running until it passes.
- **No test infrastructure:** for small tasks, verify with reproducible manual checks and give the commands. For larger work, propose a minimal test setup in the project's ecosystem; adding it is a change the owner should see.
- **Cannot execute tests:** say so plainly, provide the commands, and mark the work unverified.

Never skip, disable, delete or weaken a failing test to make a run pass, unless the owner explicitly decides the test is wrong. Record that decision.
