# Template: Delivery Report

The final report for Tier 2 and Tier 3 work. It follows [transparency-and-reporting.md](../standards/transparency-and-reporting.md): the owner should be able to see at a glance what was done, what is verified, what failed, and what needs them.

## How to fill it

- Lead with the outcome and the overall state: complete, partially complete or blocked.
- Put anything the owner must act on (approvals, decisions, credentials to rotate) near the top.
- Every row in the verification table cites evidence from a check that ran in this session, or is marked unverified with a reason.
- Remove sections that do not apply rather than filling them with "none", except "Failures" and "Unverified", which must always be stated.

## Template

```markdown
# Delivery report: [task]

Date: [YYYY-MM-DD] | State: [complete, partially complete, blocked]

## Outcome
[One or two sentences: what now exists or works, and whether everything is verified.]

## Needs your attention
- Approval: [action, why, risk]
- Decision: [question, options, recommendation]

## Deliverables
| Deliverable | Location | Status: implemented, tested, verified |
|---|---|---|
| [item] | [path or link] | [status] |

## Changes
- [path]: [what changed and why]

## Verification
| Requirement | Check performed | Result | Evidence |
|---|---|---|---|
| [requirement] | [command, measurement, walkthrough] | [pass, fail] | [output summary or reference] |

## Failures
- [What failed, what is known about why, whether the change caused it] (or "No failures observed in the checks above.")

## Unverified
- [Item]: [why it was not verified; how to verify it, with the exact command] (or "Everything listed above was verified.")

## Limitations and assumptions
- [Known limitation or assumption still open]

## Decisions recorded
- [Decision record link and one-line summary]

## Next steps
1. [Recommended next action]
```
