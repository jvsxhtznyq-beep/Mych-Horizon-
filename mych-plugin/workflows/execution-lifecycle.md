# Execution Lifecycle

The universal nine-phase lifecycle for substantial work. Every other workflow specializes it. Not every task needs every phase: the tier decides, and small tasks stay small.

## Contents

- [Phases by tier](#phases-by-tier)
- [Phase details](#phase-details)
- [Loops and returns](#loops-and-returns)
- [Tier 3 progress checklist](#tier-3-progress-checklist)

## Phases by tier

| Phase | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|---|
| 1 Discovery | Runs (implicit) | Runs | Runs | Runs |
| 2 Investigation | If a lookup is needed | Runs, scoped to the code touched | Runs | Runs |
| 3 Architecture | Skipped | Skipped | If structure or interfaces change | Runs |
| 4 Design | Skipped | Skipped | If a user-facing interface changes | Runs |
| 5 Planning | Skipped | Skipped | Runs (short plan) | Runs (task plan) |
| 6 Implementation | Skipped | Runs | Runs | Runs |
| 7 Verification | Runs (check claims) | Runs | Runs | Runs |
| 8 Optimization | Skipped | Skipped | If a target is unmet | Runs |
| 9 Delivery | Runs | Runs | Runs | Runs |

Discovery, Verification and Delivery never disappear; they only shrink.

## Phase details

### 1. Discovery

- **Purpose:** understand the request, environment, requirements and constraints.
- **Activities:** answer the nine orientation questions ([intelligence-coordinator.md](../core/intelligence-coordinator.md)); size the task; select disciplines; resolve essential ambiguity ([clarification-protocol.md](../core/clarification-protocol.md)); confirm available tools.
- **Exit criterion:** objective, success criteria, constraints and open unknowns are stated.
- **Artifacts:** Tier 3: [execution-strategy.md](../templates/execution-strategy.md). Otherwise none.
- **Lead:** coordinator.

### 2. Investigation

- **Purpose:** replace expectations with evidence.
- **Activities:** inspect the existing files, configuration and history (`scripts/scan-project.py`); read the code that will change; read documentation for the versions in use; research unknown technologies; reproduce reported problems.
- **Exit criterion:** relevant sources are read; each unknown is resolved, converted into a stated assumption, or logged as a risk.
- **Artifacts:** findings notes; [research-report.md](../templates/research-report.md) when research is a deliverable.
- **Lead:** Researcher or Engineer.

### 3. Architecture

- **Purpose:** decide components, dependencies, interfaces and technical approach.
- **Activities:** candidate architectures, evaluation against requirements, failure analysis, interface specification ([architect.md](../modes/architect.md)).
- **Exit criterion:** components, interfaces, data flow and trade-offs are decided; significant decisions are recorded.
- **Artifacts:** [architecture-proposal.md](../templates/architecture-proposal.md), [decision-record.md](../templates/decision-record.md).
- **Lead:** Architect.

### 4. Design

- **Purpose:** define product behavior, interface structure and design requirements.
- **Activities:** users and tasks, information architecture, direction, tokens, components, key screens, responsive and accessibility review ([designer.md](../modes/designer.md)).
- **Exit criterion:** behavior, structure and interface requirements are specified well enough to build without guessing.
- **Artifacts:** [design-specification.md](../templates/design-specification.md), design canvas artboards or prototypes.
- **Lead:** Designer.

### 5. Planning

- **Purpose:** break the work into stages and measurable tasks.
- **Activities:** order tasks by dependency and risk (risky first, a thin end-to-end slice early); give each task an expected result and a verification method; mark approval points ([task-management.md](../systems/task-management.md)).
- **Exit criterion:** every task has priority, dependencies, expected result and verification method.
- **Artifacts:** Tier 2: a short plan. Tier 3: [task-plan.md](../templates/task-plan.md), optionally kept with `scripts/task-ledger.py`.
- **Lead:** coordinator.

### 6. Implementation

- **Purpose:** create the actual deliverables.
- **Activities:** build according to the plan and the relevant mode manual; test alongside; keep the plan's statuses current; stop at approval points.
- **Exit criterion:** the deliverables exist in a location the owner can reach.
- **Artifacts:** code, documents, designs, prototypes.
- **Lead:** Engineer (Designer for design artifacts, Inventor for concept prototypes).

### 7. Verification

- **Purpose:** prove the requirements are met.
- **Activities:** run the checks chosen in Discovery and Planning ([testing-strategy.md](../standards/testing-strategy.md)); review against the [quality framework](../standards/quality-framework.md); trace each requirement to evidence.
- **Exit criterion:** every requirement is traced to an executed check and its evidence, or is listed as unverified with a reason.
- **Artifacts:** the verification table in [delivery-report.md](../templates/delivery-report.md).
- **Lead:** coordinator with the Engineer.

### 8. Optimization

- **Purpose:** improve reliability, performance, maintainability and usability where it matters.
- **Activities:** measure, change one thing, measure again ([performance-investigation.md](performance-investigation.md)); simplify code and structure; remove what the final design no longer needs.
- **Exit criterion:** each improvement is measured against a baseline; nothing is "optimized" by assumption.
- **Artifacts:** before-and-after measurements.
- **Lead:** Engineer, with the Architect for structural changes.

### 9. Delivery

- **Purpose:** hand over finished output and documentation.
- **Activities:** make outputs reachable (paths, links, artifacts); update documentation; write the report ([transparency-and-reporting.md](../standards/transparency-and-reporting.md)); record decisions and open problems for continuity ([project-memory.md](../systems/project-memory.md)).
- **Exit criterion:** the owner can find and use every deliverable; the report states what is verified, what is not, and what awaits approval.
- **Artifacts:** [delivery-report.md](../templates/delivery-report.md) for Tier 2 and Tier 3.
- **Lead:** coordinator.

## Loops and returns

- A failed check returns to **Implementation** when the cause is in the code, to **Design** or **Architecture** when the failure reveals a flaw in the plan, and to **Discovery** when it reveals a misunderstood requirement.
- New information during any phase can send the work back to **Investigation**. Say so in one line rather than silently changing course.
- Return at most twice to the same phase for the same problem before stopping to reassess the approach with the owner.

## Tier 3 progress checklist

Copy into the working notes and keep it current:

```text
Lifecycle progress:
- [ ] 1 Discovery: objective, success criteria, constraints, unknowns stated
- [ ] 2 Investigation: sources read, unknowns resolved or logged
- [ ] 3 Architecture: proposal accepted, decisions recorded
- [ ] 4 Design: specification complete with states and breakpoints
- [ ] 5 Planning: tasks with verification methods and approval points
- [ ] 6 Implementation: deliverables exist and are reachable
- [ ] 7 Verification: every requirement traced to evidence
- [ ] 8 Optimization: improvements measured against baseline
- [ ] 9 Delivery: report written, docs updated, open items recorded
```
