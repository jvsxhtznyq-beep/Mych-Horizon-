# Template: Task Plan

A structured task list for multi-task work, following the schema and statuses in [task-management.md](../systems/task-management.md). Use it inside a plan or report, or keep the same fields in the ledger script when the list should persist.

## How to fill it

- Order tasks by dependency, then by risk: risky and foundational tasks first, a thin end-to-end slice early.
- Every task needs an expected result and a verification method before it starts.
- Statuses: Not started, In progress, Blocked, Completed, Verified. Evidence is filled only when a task becomes Verified.
- Keep milestones few; each should deliver something the owner can see or use.

## Template

```markdown
# Task plan: [project or feature]

Updated: [YYYY-MM-DD]

## Milestones
| Milestone | Tasks | Outcome the owner can see |
|---|---|---|
| M1 [name] | T1, T2 | [outcome] |

## Tasks
| ID | Description | Priority | Depends on | Status | Expected result | Verification method | Evidence |
|---|---|---|---|---|---|---|---|
| T1 | [what will exist] | P1 | none | Not started | [observable outcome] | [check] | |
| T2 | [what will exist] | P2 | T1 | Not started | [observable outcome] | [check] | |

## Blocked tasks
| ID | Blocker | Unblocks when |
|---|---|---|
| | | |

## Approval points
- [Task ID]: [action that needs approval]

## Changes to the plan
- [YYYY-MM-DD]: [what changed and why]
```

## Priority definitions

| Priority | Meaning |
|---|---|
| P0 | Blocks all other work or fixes active harm |
| P1 | Required for the next milestone |
| P2 | Required for the release, not urgent |
| P3 | Valuable but optional |
