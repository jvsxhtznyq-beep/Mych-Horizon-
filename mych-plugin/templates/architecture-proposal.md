# Template: Architecture Proposal

The Architect's output for significant architectural decisions. It covers the twelve required sections. Scale each section to the decision: one line is enough when one line says everything. Method: [architect.md](../modes/architect.md).

## How to fill it

- Quantify requirements where possible; label estimates as assumptions with a range.
- Always include the simplest viable alternative in "Alternatives considered", with the reason it lost.
- Every failure scenario needs detection and mitigation; a blank cell means the design is not ready.
- Record the final choice as a decision record ([decision-record.md](decision-record.md)) and link it.

## Template

```markdown
# Architecture proposal: [system or change]

Date: [YYYY-MM-DD] | Status: [draft, accepted] | Decision record: [link]

## 1. Problem definition
[Two sentences: what the system must do and what makes it hard.]

## 2. Requirements
Functional:
- [requirement]
Non-functional (quantified):
| Quality | Target | Source or assumption |
|---|---|---|
| Load | [e.g. 200 requests/s peak] | [source] |
| Latency | [e.g. p95 under 300 ms] | [source] |
| Availability | [e.g. 99.9% monthly] | [source] |
| Data size and growth | [estimate] | [source] |
Constraints: [stack, budget, team, compliance, existing systems]

## 3. Proposed architecture
[Overview in prose, plus a text diagram where the output surface renders one.]

## 4. Component responsibilities
| Component | Responsibility | Owns data | Interfaces |
|---|---|---|---|
| [name] | [one sentence] | [tables or stores] | [APIs, events] |

## 5. Communication and data flow
[Main flows step by step: who calls whom, synchronously or asynchronously, with what data. Interface contracts: operations, inputs, outputs, errors, idempotency, versioning.]

## 6. Dependencies
| Dependency | Purpose | Failure impact | Alternatives |
|---|---|---|---|
| [service or library] | [purpose] | [impact] | [alternatives] |

## 7. Failure scenarios
| Component | Failure | Effect | Detection | Mitigation |
|---|---|---|---|---|
| [component] | [slow, down, wrong data, duplicates, partial deploy] | [effect] | [signal] | [response] |

## 8. Security considerations
[Trust boundaries, authentication and authorization, secrets, data classification, encryption, abuse cases.]

## 9. Performance considerations
[Expected hot paths, capacity estimate, caching, scaling approach, what will be measured.]

## 10. Alternatives considered
| Alternative | Why it was not chosen |
|---|---|
| [simplest viable option] | [reason] |

## 11. Trade-offs
[What this design makes easier and harder; costs accepted; triggers that would justify revisiting.]

## 12. Implementation strategy
[Order of work, first vertical slice, risky parts first, migration steps with reversibility, verification per stage, approval points.]
```
