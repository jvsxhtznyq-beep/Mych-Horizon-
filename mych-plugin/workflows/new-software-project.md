# New Software Project Workflow

For building a new application or a major feature: Architect, Designer and Engineer working in sequence and in parallel, usually Tier 3 (Tier 2 for a contained feature). The Engineer leads the build; the Architect leads the Architecture phase; the Designer owns every user-facing surface. Add the Researcher when the stack or domain is unfamiliar.

## Contents

- [Discovery](#discovery)
- [Investigation](#investigation)
- [Architecture](#architecture)
- [Design](#design)
- [Planning](#planning)
- [Implementation](#implementation)
- [Verification, optimization and delivery](#verification-optimization-and-delivery)
- [Pitfalls](#pitfalls)

## Discovery

1. Restate the product in two sentences: who it serves and what it lets them do.
2. Ask only the essential questions, together, up to three ([clarification-protocol.md](../core/clarification-protocol.md)). Typical candidates: who the users are; what existing systems it must integrate with; where it must run. Everything else becomes a stated recommendation.
3. Define success criteria per core user task ("a patient can book an available slot in under a minute on a phone").
4. Define scope: the first release and an explicit *not in this release* list. Scope creep is cheapest to stop here.
5. Fill [execution-strategy.md](../templates/execution-strategy.md).

## Investigation

- Inventory what exists: repositories, APIs to integrate, data to migrate, hosting already paid for.
- Research unfamiliar technology with the Researcher ([technical-research.md](technical-research.md)), limited to the decisions at hand.
- Confirm tools and access: can you create files, run code, install dependencies, reach package registries? ([tool-availability.md](../systems/tool-availability.md)).

## Architecture

The Architect produces an [architecture-proposal.md](../templates/architecture-proposal.md) in proportion to the project ([architect.md](../modes/architect.md#proportionality)).

- **Stack:** prefer what the owner or team already knows, then mainstream, well-documented options with long support windows. Unfamiliar or trendy technology needs a reason tied to a requirement. Record the choice as a decision record.
- **Structure:** a single deployable with clear modules unless a requirement demands more.
- **Domain model:** entities, relationships, ownership and lifecycle; this stabilizes the work of the Designer and Engineer.
- **Interfaces:** API contracts with inputs, outputs and errors before both sides are built.
- **Cross-cutting concerns:** authentication and authorization, configuration and secrets, logging, error handling, data backup.

## Design

The Designer starts once the domain model is stable and works in parallel with the remaining architecture ([designer.md](../modes/designer.md)).

- Rank user tasks; design the top tasks' screens first, with every state.
- Establish tokens before screens so the Engineer can implement them once.
- Use Claude Design when the environment offers it; otherwise produce HTML prototypes or a written specification.
- Hand off with [design-specification.md](../templates/design-specification.md).

Sync point: the Architect and Designer confirm that every screen's data is available through the planned interfaces at acceptable latency.

## Planning

- Plan in **vertical slices**: each slice delivers one user-visible capability end to end (interface, logic, storage, tests).
- First slice: a **walking skeleton**, the thinnest version that runs end to end, including the build and, when deployment is in scope, the deployment path.
- Put the riskiest slices early: unfamiliar integrations, performance-critical paths, anything that could invalidate the architecture.
- Write the plan with [task-plan.md](../templates/task-plan.md); each task has an expected result and a verification method. Mark approval points such as provisioning paid services or deploying.

## Implementation

- Build slice by slice. A slice is complete when its tests pass and its user task works; it is verified when that evidence is recorded.
- Set up the project skeleton with the standard tooling for the stack: formatter, linter, type checking where idiomatic, test runner, a README with run instructions.
- Implement design tokens as variables or theme configuration, not as values copied into components.
- Keep the task plan's statuses current. When reality diverges from the plan, update the plan instead of quietly drifting.
- Stop at approval points ([autonomy-and-approval.md](../systems/autonomy-and-approval.md)).

## Verification, optimization and delivery

- **Verification:** unit tests for domain logic; integration tests for persistence and external interfaces; an end-to-end test for each core user task; the accessibility checklist for every screen; a requirement-by-requirement trace in the delivery report.
- **Optimization:** only against measured shortfalls or stated targets ([performance-investigation.md](performance-investigation.md)).
- **Delivery:** run and deploy instructions; configuration documentation without secrets; known limitations; the not-in-this-release list; recommended next steps. Use [delivery-report.md](../templates/delivery-report.md) and record decisions for future sessions ([project-memory.md](../systems/project-memory.md)).

## Pitfalls

- Choosing the stack before understanding the users and constraints.
- Designing every screen before building anything; or building screens before any design.
- Horizontal layers ("all the database code first") instead of vertical slices, which delays the first working feature.
- Leaving authentication, error handling or deployment to the end.
- Delivering code without run instructions, or claiming a feature works without exercising it.
