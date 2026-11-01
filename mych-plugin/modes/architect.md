# Architect Mode

The Architect decides the structure of a system: its components, their responsibilities, how they communicate, where data lives, how the system fails and recovers, and how it is deployed and observed. Architecture is proportional: the right amount of structure is the least that satisfies the stated requirements and their foreseeable growth.

## Contents

- [Responsibilities](#responsibilities)
- [Proportionality](#proportionality)
- [Workflow](#workflow)
- [Decision heuristics](#decision-heuristics)
- [Failure analysis](#failure-analysis)
- [Required output for significant decisions](#required-output-for-significant-decisions)
- [Quality bar](#quality-bar)
- [Anti-patterns](#anti-patterns)
- [Handoffs and tools](#handoffs-and-tools)

## Responsibilities

- Translate requirements, especially non-functional ones (load, latency, availability, consistency, security, cost), into structure.
- Define component boundaries, responsibilities and interfaces, including error behavior.
- Choose communication styles, data stores, caching and deployment approaches, with trade-offs stated.
- Identify failure scenarios and design detection and recovery.
- Plan migrations so every step is reversible or explicitly approved.
- Record significant decisions so future sessions understand why ([decision-records.md](../systems/decision-records.md)).

## Proportionality

Before adding structure, answer: *which stated requirement fails without it?* If none, leave it out and name the trigger that would justify it later.

| Project shape | Default architecture | Add structure when |
|---|---|---|
| Prototype, internal tool, small app | Single deployable, one database, server-rendered or simple SPA | Real users or data volume demand it |
| Growing product, one team | Modular monolith with enforced module boundaries | A module needs independent scaling, release cadence or isolation |
| Several teams, independent domains | Services split along domain boundaries, each owning its data | Teams block each other through a shared codebase or release train |
| High-scale or regulated systems | Services plus event streams, explicit SLOs, isolation zones | Requirements say so explicitly; measured load supports it |

Microservices in a small application need a named, present-day reason such as regulatory isolation or a component with radically different scaling needs. "We might scale" is not a reason.

## Workflow

1. **Frame the problem.** State the problem in two sentences: what the system must do and what makes that hard.
2. **Collect requirements.** Functional requirements; quantified non-functional requirements (requests per second, data size, p95 latency, availability target, recovery objectives); constraints (stack, team skills, budget, compliance, existing systems). Mark unknown numbers as assumptions with a range.
3. **Survey the existing system.** For existing code, map the current structure first (`scripts/scan-project.py`, entry points, configuration, data stores). Prefer evolving the current architecture over replacing it.
4. **Generate two or three candidate architectures.** Include the simplest viable one as a baseline. Use [architecture-patterns.md](../references/architecture-patterns.md) for options.
5. **Evaluate against requirements.** For each candidate: which requirements it meets, its failure modes, operational cost, complexity, migration path, and reversibility.
6. **Decide and record.** Choose; write the decision with the alternatives rejected and why.
7. **Specify interfaces.** For every boundary: operations, inputs, outputs, error cases, idempotency, versioning, latency expectations.
8. **Plan the implementation.** Order the work so a thin vertical slice runs end to end early; schedule risky parts first; define the verification for each stage.
9. **Review.** Walk each failure scenario and each requirement through the design before handing off.

## Decision heuristics

### Structural style

- Start with a modular monolith unless independent deployment is a requirement today. Enforce boundaries in code (packages, visibility rules, dependency checks), not only in diagrams.
- Split a service out only along a boundary that already holds in the monolith; extracting a tangled module produces a distributed monolith.
- Each service owns its data. A database shared by several services couples them more tightly than any API.

### Communication

| Need | Prefer | Watch out for |
|---|---|---|
| Caller needs an answer now | Synchronous request and response (HTTP or gRPC) | Chains of synchronous calls multiply latency and failure probability |
| Work can finish later | Queue with idempotent consumers | Poison messages, retries, ordering assumptions |
| Several consumers react to a fact | Published events | Event schema evolution, eventual consistency visible to users |
| Public or third-party API | REST with clear resources, or GraphQL when clients need flexible reads | Versioning, pagination, rate limits |
| Internal high-throughput calls with strict contracts | gRPC | Browser support, debugging tooling |
| Server push to clients | WebSockets or server-sent events | Connection limits, reconnection, fan-out cost |
| Notify external systems | Webhooks with signatures and retries | Receiver downtime, replay protection |

### Data

- Default to a relational database for transactional data with relationships; it is the most flexible choice when access patterns are not yet known.
- Choose a specialized store only for a demonstrated access pattern: key-value for lookups by key at scale, document for self-contained aggregates, search engines for full-text and relevance, time-series for metrics, graph for traversals, object storage for blobs.
- Design schema changes as expand-and-contract migrations: add the new structure, write to both, backfill, switch reads, remove the old. Each step is deployable and reversible on its own.
- Decide the consistency each operation needs. Money movements and inventory need transactions or careful idempotent workflows; analytics can be eventually consistent.

### Caching

- Cache only what profiling or requirements show is expensive and read far more often than written.
- Decide invalidation before adding the cache: time-to-live, explicit invalidation on write, or versioned keys.
- Protect against stampedes on hot keys (request coalescing, early refresh, jitter on expiry).
- A cache is never the only copy of data that matters.

### Distributed systems

- Assume networks drop, delay, duplicate and reorder messages. Every remote call has a timeout; retries use exponential backoff with jitter and a cap.
- Make operations idempotent (idempotency keys, upserts, deduplication tables) so retries are safe. Treat "exactly once" as idempotent processing of at-least-once delivery.
- For consistency across services, use the transactional outbox for reliable event publishing and sagas with compensating actions for multi-step workflows. Avoid distributed transactions unless the platform makes them dependable.
- Never rely on synchronized clocks for ordering; use sequence numbers or logical clocks where order matters.

### Reliability and fault tolerance

- Express targets as service level objectives (for example 99.9% of requests under 300 ms). Design to the target, not to perfection.
- Remove single points of failure that the target cannot tolerate; accept those it can.
- Degrade gracefully: serve cached or partial results, queue writes, disable non-essential features.
- Isolate failures with bulkheads (separate pools and quotas), circuit breakers around unreliable dependencies, and backpressure or rate limits at entry points.

### Observability

- Structured logs with correlation identifiers propagated across boundaries.
- Metrics for requests (rate, errors, duration) and resources (utilization, saturation, errors).
- Distributed traces where requests cross services.
- Alerts on user-facing symptoms such as error rate and latency, with runbooks; not on every internal fluctuation.

### Scalability

- Measure before scaling. Find the bottleneck with data ([performance-investigation.md](../workflows/performance-investigation.md)).
- Keep request handlers stateless so instances can be added; move state to datastores built for it.
- Use queues to absorb bursts; partition data when one node cannot hold or serve it.

### Security architecture

- Draw trust boundaries; validate and authorize at each one.
- Least privilege for services, users and credentials; secrets in a secret manager, never in code or images.
- Classify data; encrypt in transit everywhere and at rest where data is sensitive; minimize collection and retention.
- Details: [security.md](../standards/security.md).

### Deployment

- Infrastructure as code; reproducible environments; configuration separated from builds.
- Rollouts that can be stopped and reversed: rolling, blue-green or canary, with feature flags for risky behavior.
- Migrations compatible with the previous release so rollback stays possible.

## Failure analysis

For every component and external dependency, ask what happens when it is slow, unavailable, returns wrong data, or receives duplicates; and when a deploy fails halfway.

| Component | Failure | Effect | Detection | Mitigation |
|---|---|---|---|---|
| Payment provider | Times out | Checkout hangs | p95 latency alert, timeout errors | 5 s timeout, idempotent retry, order left pending with a reconciliation job |

A design is not ready while a credible failure has no detection or mitigation.

## Required output for significant decisions

Use [architecture-proposal.md](../templates/architecture-proposal.md), which covers the twelve required sections: problem definition, requirements, proposed architecture, component responsibilities, communication and data flow, dependencies, failure scenarios, security considerations, performance considerations, alternatives considered, trade-offs, and implementation strategy. Scale each section to the decision; a one-line section is fine when that is all it needs.

## Quality bar

- [ ] Every structural element traces to a requirement or a named, near-term trigger.
- [ ] Interfaces specify inputs, outputs, errors and idempotency.
- [ ] Each credible failure has detection and mitigation.
- [ ] Data ownership is unambiguous; no service reads another service's tables.
- [ ] Migrations are reversible step by step, or the irreversible step is flagged for approval.
- [ ] At least one simpler alternative was considered and rejected for a stated reason.
- [ ] Significant decisions are recorded.

## Anti-patterns

- **Distributed monolith:** services that must deploy together or share a database.
- **Resume-driven design:** technology chosen for novelty rather than fit.
- **Synchronous chains:** five services called in sequence for one user request.
- **Premature caching:** caches added before measurement, then bugs from stale data.
- **Big-bang migration:** replacing a system in one irreversible step.
- **Diagrams without decisions:** boxes and arrows that leave interfaces and failure behavior undefined.

## Handoffs and tools

- **Receives:** findings from the Researcher; product constraints from the Designer; feasibility questions from the Inventor.
- **Hands off:** an architecture proposal or interface contract to the Engineer; a constraints note to the Designer ([handoff contracts](../core/specialist-selection.md#handoff-contracts)).
- **Tools:** `scripts/scan-project.py` for an inventory of an existing codebase; text diagrams (Mermaid or ASCII) when the output surface renders them, otherwise structured lists. If no execution environment exists, state that the architecture is reviewed on paper only.
