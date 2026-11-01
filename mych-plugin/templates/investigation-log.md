# Template: Investigation Log

A working record for debugging and performance investigations with more than one hypothesis. It keeps experiments disciplined (one change at a time) and turns into the evidence section of the final report. Workflows: [debugging.md](../workflows/debugging.md), [performance-investigation.md](../workflows/performance-investigation.md).

## How to fill it

- Record the symptom or metric exactly before forming any hypothesis.
- Give each hypothesis evidence for and against; test the cheapest discriminating one first.
- Log every experiment, including the ones that disproved a favorite theory.
- Keep it factual and short; it is a lab notebook, not a narrative.

## Template

```markdown
# Investigation: [symptom or metric]

Started: [YYYY-MM-DD] | Status: [open, root cause found, fixed, verified]

## Symptom or metric
- Expected: [...]
- Actual: [exact error text, measurement or behavior]
- Frequency: [always, intermittent (rate), once]
- Started: [when; related changes around that time]

## Environment and conditions
[Versions, configuration, data size, hardware or instance, workload, warm or cold state.]

## Reproduction or baseline
- Command or steps: [...]
- Result: [...]
- For performance: [median and spread over N runs]

## Hypotheses
| ID | Hypothesis | Evidence for | Evidence against | Test | Result | Status |
|---|---|---|---|---|---|---|
| H1 | [hypothesis] | [...] | [...] | [experiment] | [observation] | [open, refuted, supported, confirmed] |

## Experiments
| # | Change (one only) | Result | Kept or reverted |
|---|---|---|---|
| 1 | [change] | [observation or measurement] | [kept, reverted] |

## Root cause or finding
[Cause distinguished from trigger, with the evidence that demonstrates it.]

## Fix or improvement
[What changed and where.]

## Verification
- [Regression test or re-measurement, command, result]

## Residual risks and follow-ups
- [Same pattern elsewhere, untested environments, remaining gap to target]
```
