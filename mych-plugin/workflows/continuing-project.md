# Continuing Project Workflow

For resuming earlier work. Continuity comes from the project's files, not from memory: unless the environment provides a memory tool, assume nothing carried over from earlier sessions. The goal is to pick up exactly where the work stands, under the decisions already made, without redoing finished work or creating a second source of truth.

## Steps

1. **Find the project's memory sources.** Run `python3 ${CLAUDE_SKILL_DIR}/scripts/scan-project.py PROJECT_DIR` and read, in this order, whatever exists:
   1. Agent and contributor instructions (for example `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`).
   2. `README` and the `docs/` folder.
   3. Decision records (`docs/decisions/`, `docs/adr/`, `adr/` or similar).
   4. The project context file, if the project keeps one ([project-context.md](../templates/project-context.md)).
   5. The task plan or ledger, if one exists (for example `.mych/tasks.json` kept with `scripts/task-ledger.py`).
   6. `CHANGELOG` and recent version-control history (`git log --oneline -n 30`).
   7. Open issues and pull requests, when the environment gives access.
2. **Reconstruct the state.** What is done, in progress, blocked and decided; which conventions apply; what was planned next; which problems are unresolved.
3. **Check the state against reality.** Documentation drifts. Cheaply confirm the claims that matter: the files marked done exist, the tests marked passing pass, the decision records match the code. Note any discrepancy.
4. **Choose the next task.** Continue the recorded next step if one exists. Ask the owner only if the next step is genuinely unclear or the recorded plan conflicts with a newer request ([clarification-protocol.md](../core/clarification-protocol.md)).
5. **Work under existing decisions.** Follow recorded decisions and conventions. If one now looks wrong, raise it with evidence; do not silently diverge. Replacing a decision means a new decision record that supersedes the old one ([decision-records.md](../systems/decision-records.md)).
6. **Update the memory at the end,** in the sources the project already uses: task statuses, new decisions, open problems, next steps ([project-memory.md](../systems/project-memory.md)).

## Resolving conflicting sources

When sources disagree, trust them in this order, and report the discrepancy:

1. The code and the results of running it.
2. Accepted decision records, newest first.
3. Current project documentation.
4. Older notes, plans and comments.

## Pitfalls

- Re-implementing something that already exists because the earlier work was not read.
- Starting a new `NOTES.md` when the project already keeps its context somewhere else.
- "Cleaning up" established conventions as a side effect.
- Trusting a status line in a document without checking it.
- Assuming the owner remembers what the last session did; summarize it briefly when it matters for the next decision.
