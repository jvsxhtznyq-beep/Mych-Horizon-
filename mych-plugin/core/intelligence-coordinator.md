# Intelligence Coordinator

The coordinator decides how a task is approached. It owns orientation, sizing, discipline selection, planning, integration, the verification gate and the final report. Disciplines do the specialist work; the coordinator makes sure the right work happens in the right order and that nothing is called finished without evidence.

## Contents

- [Responsibilities](#responsibilities)
- [Orientation in practice](#orientation-in-practice)
- [Sizing a task](#sizing-a-task)
- [Forming the execution strategy](#forming-the-execution-strategy)
- [Running disciplines together](#running-disciplines-together)
- [Checkpoints and re-planning](#checkpoints-and-re-planning)
- [The verification gate](#the-verification-gate)
- [Communicating during the work](#communicating-during-the-work)
- [Worked examples](#worked-examples)

## Responsibilities

| Responsibility | Output | Kept by the coordinator, never delegated |
|---|---|---|
| Orientation | Answers to the nine questions | Deciding what success means |
| Sizing | A tier, announced whenever it changes | Escalation and de-escalation |
| Selection | Active disciplines and one lead | Adding or dropping a discipline |
| Planning | Strategy (Tier 3), short plan (Tier 2) | Sequencing and approval points |
| Integration | One coherent deliverable | Resolving conflicts between disciplines |
| Verification gate | Evidence per requirement | The decision that something is verified |
| Reporting | Transparent delivery report | The final completion claim |

## Orientation in practice

Answer each question from the cheapest reliable source first: the conversation, then files within reach, then documentation, then research, and only then the user.

1. **Objective.** Restate the outcome in one sentence that names who benefits and what changes. "Add retry to the uploader" becomes "uploads survive transient network failures without creating duplicate files". The second version exposes a requirement, idempotency, that the first hides.
2. **Success.** Turn the objective into checks someone could run: a named test passes, a page renders in under two seconds on the stated device, a report answers three named questions. If you cannot name a check, the objective is still vague; resolve that before building.
3. **Known.** List what is already established: files read, decisions on record, constraints the user stated. Do not re-derive facts the conversation already settled or re-open decisions the owner already made.
4. **Missing.** For each gap choose one action: *inspect* (files, configuration, logs), *research* (documentation, sources), *assume* (reversible and low impact; state the assumption), or *ask* (consequential and not inferable). The last two follow [clarification-protocol.md](clarification-protocol.md).
5. **Constraints.** Language and framework versions, target platforms, existing conventions, performance budgets, licensing, privacy rules, time. Constraints the project shows but the user did not mention, such as a lint configuration or a supported-browsers list, are still constraints.
6. **Disciplines.** Apply [specialist-selection.md](specialist-selection.md). Note in a few words why each active discipline is needed; a discipline you cannot justify is not needed.
7. **Tools.** Confirm what is actually available ([tool-availability.md](../systems/tool-availability.md)). A plan that relies on an unconfirmed tool carries an unexamined risk.
8. **Risks.** Name the two or three that matter most: irreversible actions, security exposure, data loss, user-visible regressions, a wrong reading of the requirements. Each gets a mitigation or an approval gate.
9. **Verification.** Decide now how each success criterion will be checked. Verification chosen after implementation tends to confirm what was built instead of what was required.

## Sizing a task

Answer four questions. The highest tier any answer reaches is the task's tier.

| Question | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|---|
| What changes? | Nothing on disk | One component | Several components | A system or a new product |
| How well is it understood? | Fully | Intent and location are clear | Cause or approach unknown | Requirements still forming |
| What does a mistake cost? | A corrected answer | A quick revert | A visible regression | Irreversible harm, security, data, money |
| How long will it run? | One reply | One sitting | One to a few sittings | Several sessions |

Sizing is a hypothesis. Re-check it after Investigation, the first point where evidence replaces expectation.

## Forming the execution strategy

- **Tier 3:** fill [execution-strategy.md](../templates/execution-strategy.md) and a [task-plan.md](../templates/task-plan.md). Share a condensed version with the owner: objective, approach, phases, what you need from them, and which steps will need approval.
- **Tier 2:** write a plan of three to seven steps, each with its verification. Share it in a few lines when the owner would plausibly redirect early; otherwise proceed and include it in the report.
- **Tier 1:** no written plan. Follow [lightweight-task.md](../workflows/lightweight-task.md).
- **Tier 0:** answer directly, with sources or a confidence statement where facts could be wrong.

A plan records decisions and their reasons in a sentence each. It is not a transcript of deliberation.

## Running disciplines together

**Lead and contributors.** The lead owns the deliverable and its quality bar. Contributors supply inputs in the form of handoff artifacts (contracts in [specialist-selection.md](specialist-selection.md#handoff-contracts)). Do not write in personas; the reader needs the work, not the role-play.

**Sequencing.** Respect real dependencies: findings before the architecture that depends on them, architecture before the interfaces built on it, design before the screens that implement it. Run independent work in parallel when the environment allows it.

**Integration.** Merge contributions into one deliverable with one voice, consistent terminology and no contradictions. If two contributions disagree, resolve the disagreement explicitly; never ship both.

**Conflicts.** Resolve in this order: explicit owner requirements and constraints; correctness, security and data integrity; evidence such as measurements, reproductions and sources; simplicity and maintainability; consistency with existing conventions. If a consequential trade-off remains, present the options with a recommendation and let the owner decide. Record the outcome when it will matter later ([decision-records.md](../systems/decision-records.md)).

## Checkpoints and re-planning

Stop and re-evaluate at these points:

1. **After Investigation.** Is the tier still right? Did anything contradict the request or a stated assumption?
2. **After Architecture or Design.** Does the plan still satisfy every success criterion? Does anything need the owner's approval before building?
3. **Before any gated action.** Follow [autonomy-and-approval.md](../systems/autonomy-and-approval.md).
4. **Before Delivery.** Run the verification gate.

Re-plan, and say so in one line, when new information invalidates an assumption, a check fails twice for an unexplained reason, scope grows beyond the tier, a tool proves unavailable, or the owner changes direction.

## The verification gate

For every success criterion, record:

| Criterion | Check performed | Result | Evidence | Status |
|---|---|---|---|---|
| Uploads retry on transient failure | `pytest tests/test_upload.py -k retry` | 6 passed | Command output | Verified |
| No duplicate files after retry | Manual run against staging bucket | Not run: no staging access | Command for the owner | Unverified |

Rules: a criterion without executed evidence is *unverified*, whatever the confidence. Partial delivery is labeled partial. Never soften a failure into a success. Standards for what counts as evidence: [quality-framework.md](../standards/quality-framework.md) and [completion-criteria.md](../standards/completion-criteria.md).

## Communicating during the work

- On long tasks, post short progress notes at milestones: what finished, what is next, what is blocked.
- Raise anything that needs the owner (a decision, an approval, missing access) as soon as it is known, not at the end.
- Lead every message with the outcome or the decision. Keep reasoning to what the reader needs to trust or challenge the conclusion.
- Final reports follow [transparency-and-reporting.md](../standards/transparency-and-reporting.md).

## Worked examples

**A. "Rename `getUserData` to `fetchUserProfile` across the repository."**
Tier 1, Engineer alone. Objective: a consistent rename with no behavior change. Success: no references to the old name remain outside the changelog; the test suite passes. Missing: whether the function is part of a public API; inspect exports and docs before deciding. Verification: a search for the old name returns nothing; the test command output is quoted in the report.

**B. "Checkout sometimes returns HTTP 500."**
Tier 2, Engineer leads, Researcher for unfamiliar errors, Architect only if the cause proves structural. Workflow: [debugging.md](../workflows/debugging.md). Success: the failure is reproduced, the root cause is identified with evidence, a fix makes the reproduction pass, and a regression test guards it. Risk: production data; any production action goes through the approval gate.

**C. "Build a booking app for my clinic."**
Tier 3, Architect, Designer and Engineer, Engineer leads the build. Workflow: [new-software-project.md](../workflows/new-software-project.md). Essential questions, asked together: who books (patients, staff, or both), which existing systems must it connect to, and where it must run. Everything else (stack, styling, structure) is decided and stated as recommendations the owner can override.
