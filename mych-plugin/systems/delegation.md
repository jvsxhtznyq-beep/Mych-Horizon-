# Delegation

When to hand work to sub-agents or parallel workers, and when not to. The default is that the coordinator does the work: every delegated worker starts without the conversation's context, re-reads what it needs, and returns claims that must still be checked. Delegation earns its cost only when it saves more time or context than it consumes.

## Contents

- [Delegate only when all of these hold](#delegate-only-when-all-of-these-hold)
- [Never delegate](#never-delegate)
- [Writing a delegation brief](#writing-a-delegation-brief)
- [Integrating results](#integrating-results)
- [Hosts without workers](#hosts-without-workers)

## Delegate only when all of these hold

1. **Independent.** The subtask shares no files, state or decisions with work happening at the same time.
2. **Well specified.** Inputs, expected output, acceptance check and forbidden actions can be written in a short brief.
3. **Worth it.** It runs in parallel with other work, or it would flood the coordinator's context (a broad search across a large codebase, a long log analysis) and only its conclusion is needed.
4. **Supported.** The host actually offers workers or sub-agents, and the owner's instructions allow them.

The minimum-sufficient rule applies to workers exactly as it does to disciplines: use as few as the work needs, usually none.

## Never delegate

- The verification gate, the final report, or any completion claim.
- Approval decisions and any gated action ([autonomy-and-approval.md](autonomy-and-approval.md)).
- Work that needs the full conversation context or the owner's preferences to get right.
- Tightly coupled changes, or two workers writing the same file, task ledger or branch.
- Small tasks the coordinator can finish faster than it can write the brief.

## Writing a delegation brief

A worker should be able to succeed without asking questions:

```text
Objective:   Find every caller of format_date() in src/ and report file:line with the argument types used.
Inputs:      Repository at /work/app (read-only for this task).
Constraints: Read-only. No network. Do not modify files.
Output:      A table of file:line, call expression, inferred argument type; plus anything ambiguous.
Acceptance:  Every reported line exists and contains a call to format_date.
Forbidden:   Installing packages, editing files, running the app.
```

## Integrating results

- Treat worker output as a claim, not evidence: spot-check it, re-run its decisive checks, or verify its acceptance condition yourself before relying on it.
- Record task status in the ledger yourself; workers report to the coordinator, which is the single writer of task state.
- When a worker fails or returns something unusable, decide explicitly: retry with a sharper brief, or do the work directly. Never mark the task done on the worker's word.
- Report which parts were delegated if it matters to the owner's trust in the result.

## Hosts without workers

Many hosts offer no sub-agents. Run the subtasks sequentially, in the order of their dependencies, and never describe sequential work as parallel. Context-heavy exploration can still be contained: summarize findings into the task plan or notes as you go and drop the raw material.
