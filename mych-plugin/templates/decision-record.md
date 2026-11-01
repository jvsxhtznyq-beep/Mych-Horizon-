# Template: Decision Record

One significant decision per file, following [decision-records.md](../systems/decision-records.md). Store it where the project keeps decisions; otherwise in `docs/decisions/NNNN-short-title.md`.

## How to fill it

- Title the file and the record with the decision itself, not the topic: "Use PostgreSQL for bookings", not "Database".
- Keep it to about one page; link to longer analyses.
- Describe rejected options fairly.
- After acceptance, never rewrite the decision; supersede it with a new record.

## Template

```markdown
# [NNNN]. [Decision stated as a short imperative sentence]

- Date: [YYYY-MM-DD]
- Status: [Proposed | Accepted | Superseded by NNNN | Deprecated]
- Deciders: [owner and contributors]

## Context
[The situation and the forces at play: requirements, constraints, relevant facts with sources.]

## Problem
[The question being decided, in one or two sentences.]

## Options
1. **[Option A]**: [description]. Pros: [...]. Cons: [...].
2. **[Option B]**: [description]. Pros: [...]. Cons: [...].
3. **[Option C]**: [description]. Pros: [...]. Cons: [...].

## Decision
[The selected approach.]

## Reasoning
[Why, in a few sentences tied to the context.]

## Consequences
- Easier: [...]
- Harder: [...]
- Follow-up work: [...]
- Risks accepted: [...]

## Alternatives rejected
- [Option]: [reason it lost]

## Links
- [Related records, proposals, research reports, issues]
```
