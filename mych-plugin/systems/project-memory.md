# Project Memory

The context management protocol for work that continues over time. Memory lives in the project's files, in one place per kind of fact, and is updated when the work changes it.

## Contents

- [Rules](#rules)
- [Where each kind of fact lives](#where-each-kind-of-fact-lives)
- [Starting work in an existing project](#starting-work-in-an-existing-project)
- [Ending a working session](#ending-a-working-session)
- [Creating a project context file](#creating-a-project-context-file)
- [What never goes into memory](#what-never-goes-into-memory)

## Rules

1. **No assumed persistence.** Do not assume anything carried over from an earlier session unless the environment demonstrably provides memory (a memory tool, or files you can read). If it does, treat stored memories as claims to check, like any document.
2. **Inspect before acting.** Read existing documentation, decision records and task lists before starting work ([continuing-project.md](../workflows/continuing-project.md)).
3. **Preserve conventions and decisions.** Follow what the project established. To change a decision, record a new one that supersedes it ([decision-records.md](decision-records.md)).
4. **Avoid repeating completed work.** Check what exists before building.
5. **One source of truth per fact.** Never keep the same fact in two places that can drift apart. Link instead of copying.
6. **Update when changes justify it.** When the work changes behavior, structure, decisions or plans, update the corresponding record in the same session.

## Where each kind of fact lives

Use the project's existing locations first. Only when none exists, use the default.

| Kind of fact | Look for first | Default if none exists |
|---|---|---|
| How to work in this repository | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CONTRIBUTING.md` | Section in `README.md` |
| What the project is and how to run it | `README.md`, `docs/` | `README.md` |
| Why it is built this way | `docs/adr/`, `docs/decisions/`, `adr/` | `docs/decisions/` |
| What is planned and in progress | Issue tracker, `TASKS.md`, existing plan | `.mych/tasks.json` via the ledger script |
| What changed per release | `CHANGELOG.md`, release notes | `CHANGELOG.md` |
| Current state, open problems, gotchas | Existing notes or status docs | A project context file (below) |

## Starting work in an existing project

Run `python3 ${CLAUDE_SKILL_DIR}/scripts/scan-project.py PROJECT_DIR`; it lists the documentation, decision records, task ledgers and instruction files it finds. Read them in the order given in [continuing-project.md](../workflows/continuing-project.md). Then confirm the claims that matter against the code and test results; record discrepancies.

## Ending a working session

Before the final report on multi-session work, record in the project's existing sources:

- What was completed and verified, with evidence pointers.
- What is in progress, and its exact state.
- What should happen next.
- New decisions (as decision records) and assumptions still open.
- Unresolved problems, known limitations and gotchas discovered.

Keep entries short and factual. The next session needs state, not narrative.

## Creating a project context file

Create one only when the work spans sessions and the project has no equivalent place for current state. Use [project-context.md](../templates/project-context.md), keep it under about a hundred lines, link to decision records and the task list instead of copying them, and tell the owner you created it. Suggested location: `docs/project-context.md`, or the location the owner prefers.

## What never goes into memory

- Secrets, credentials, tokens or connection strings.
- Personal data beyond what the project already legitimately stores.
- Raw logs or transcripts; summarize them.
- Copies of facts kept elsewhere; link to the source instead.
- Speculation recorded as fact; label hypotheses.
