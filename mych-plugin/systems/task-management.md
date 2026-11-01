# Task Management

How MYCH-PLUGIN tracks work on complex tasks: the task schema, the statuses and the transitions between them, where the task list lives, and how to use the bundled ledger script.

## Contents

- [When to keep a task list](#when-to-keep-a-task-list)
- [Task schema](#task-schema)
- [Statuses and transitions](#statuses-and-transitions)
- [Choosing where the list lives](#choosing-where-the-list-lives)
- [Using the ledger script](#using-the-ledger-script)
- [Keeping the list honest](#keeping-the-list-honest)

## When to keep a task list

Keep a structured task list when any of these hold: the work has three or more distinct tasks with dependencies; it will span sessions; several deliverables or disciplines are involved; the owner wants visible progress. Tier 1 work never needs one.

## Task schema

| Field | Content | Example |
|---|---|---|
| ID | Short and stable; never reused | `T4` |
| Description | What will exist when done, in a sentence | Booking API creates and cancels bookings |
| Priority | P0 blocks everything else; P1 high; P2 normal; P3 nice to have | P1 |
| Dependencies | IDs that must be completed first | T1, T2 |
| Status | One of the five below | In progress |
| Expected result | Observable outcome | `POST /bookings` returns 201 with the booking |
| Verification method | The check that proves it | `pytest tests/api/test_bookings.py` passes |
| Evidence | Filled on verification: what ran and what it showed | 9 passed in 1.2 s |

A task without a verification method is not ready to start: decide how it will be proven first.

## Statuses and transitions

| From | Allowed to | Condition |
|---|---|---|
| Not started | In progress | Dependencies completed or verified |
| Not started, In progress | Blocked | Blocker and unblock condition recorded |
| Blocked | In progress | Blocker resolved |
| In progress | Completed | Expected result exists |
| Completed | Verified | Verification method executed; evidence recorded |
| Completed, Verified | In progress | Reopened with a reason (for example a regression) |

Completed and verified are different statuses. Nothing moves to Verified without evidence, and evidence means the output of a check that actually ran, not a restatement of intent.

## Choosing where the list lives

Use exactly one tracker per project, so there is one source of truth:

1. **The environment's native task tool,** when one exists, for work within a session.
2. **The ledger file** (`.mych/tasks.json` by default) when the list should persist in the repository across sessions, or when the verification rule should be enforced mechanically.
3. **A Markdown table** from [task-plan.md](../templates/task-plan.md) inside the plan or report, for short lists.

If the project already tracks tasks somewhere (an issue tracker, a `TASKS.md`), use that and do not start a parallel list.

## Using the ledger script

`scripts/task-ledger.py` stores tasks as JSON and enforces the transition table above. It writes only the ledger file, atomically.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json init --project "Clinic booking"
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json add T1 --title "Data model and migrations" --priority P1 --expect "Tables for patients, slots and bookings" --verify "pytest tests/test_models.py passes"
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json add T2 --title "Booking API" --depends T1 --expect "POST /bookings creates a booking" --verify "API integration tests pass"
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json start T1
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json complete T1 --note "migrations 0001 to 0003"
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json verify T1 --evidence "pytest tests/test_models.py: 12 passed"
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json block T2 --reason "SMS provider not chosen" --unblock "Owner picks a provider"
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json list
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json render
python3 ${CLAUDE_SKILL_DIR}/scripts/task-ledger.py --file .mych/tasks.json check
```

Behavior worth knowing:

- `start` refuses while dependencies are unfinished; `--force` overrides and records that it did.
- `verify` refuses unless the task is completed and the evidence is substantive (placeholders such as "done" or "TBD" are rejected).
- `reopen ID --reason TEXT` moves a completed or verified task back to in progress and clears its evidence; the history keeps the earlier record.
- `render` prints a Markdown table for reports; `list` and `show` accept `--json`.
- `check` validates the whole ledger (unknown dependencies, cycles, verified tasks without evidence, blocked tasks without reasons) and exits with status 1 when it finds problems.

Ask before adding a `.mych/` folder to a repository the owner did not expect to change; for a repository you are already modifying as part of the task, mention it in the report.

## Keeping the list honest

- Update statuses when they change, not in batches at the end.
- Reflect plan changes in the list: add, split or drop tasks rather than letting the list drift from reality.
- Report from the list: the delivery report's verification table and the list must agree.
