# Decision Records

How important technical decisions are recorded so future sessions understand why the system was built a certain way, and how decisions are replaced without rewriting history.

## When to record a decision

Record a decision when at least one holds:

- It is expensive to reverse (a database, a framework, a data model, a public API, a hosting platform).
- It shapes structure, interfaces, dependencies or security.
- Reasonable people would choose differently, and someone will later ask why.
- It deliberately departs from a convention, a best practice or an earlier decision.
- The owner made a call against a recommendation; record both the call and the recommendation.

Small, easily reversed choices go in the plan or the report as one line instead.

## Fields

| Field | Content |
|---|---|
| Identifier | Sequential number with a short title: `0007-use-postgres-for-bookings` |
| Date | Date of the decision (ISO 8601) |
| Status | Proposed, Accepted, Superseded by NNNN, or Deprecated |
| Context | The situation and forces at play: requirements, constraints, facts |
| Problem | The question being decided, in one or two sentences |
| Options | The realistic options considered, each with honest pros and cons |
| Selected approach | What was chosen |
| Reasoning summary | Why, in a few sentences, tied to the context; not a transcript |
| Consequences | What becomes easier and harder; follow-up work; risks accepted |
| Alternatives rejected | Each rejected option with the reason it lost |

Use [decision-record.md](../templates/decision-record.md).

## Location and numbering

1. Follow the project's existing convention if one exists (`docs/adr/`, `docs/decisions/`, `doc/architecture/decisions/`, a wiki).
2. Otherwise use `docs/decisions/NNNN-short-title.md`, numbered from `0001`, in lowercase kebab-case.
3. Never renumber or reuse numbers.

## Lifecycle

- **Proposed:** written for review; implementation may wait for acceptance when the decision is consequential.
- **Accepted:** in force. Do not edit the decision or its reasoning afterwards; fix typos and add links only.
- **Superseded:** a newer record replaces it. Set the old record's status to "Superseded by NNNN" and link both ways.
- **Deprecated:** no longer relevant (the feature was removed) and nothing replaces it.

## Writing well

- Lead with the decision; a reader skimming the title and status should know what was decided.
- State facts with sources and label assumptions.
- Give rejected options a fair description; a record that strawmans the alternatives teaches nothing.
- Keep it to one page. Link to longer analyses such as research reports or architecture proposals.
- Write consequences honestly, including the costs accepted.

## Using records when continuing work

Read accepted records before changing anything they cover. If a record now looks wrong, present the evidence to the owner and, if they agree, write a superseding record before changing the code. Silent divergence from a recorded decision creates two sources of truth.
