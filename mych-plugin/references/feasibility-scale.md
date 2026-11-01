# Feasibility Scale

A five-level scale for rating how feasible an idea, concept or claim is. The Inventor uses it for every concept ([inventor.md](../modes/inventor.md)); the Researcher and Architect use it for feasibility questions. A rating always comes with its reason.

## Contents

- [The five levels](#the-five-levels)
- [Rating procedure](#rating-procedure)
- [Common rating mistakes](#common-rating-mistakes)
- [Presenting ratings](#presenting-ratings)

## The five levels

### 1. Currently feasible

- **Definition:** buildable now with established technology, known techniques and ordinary effort for the team at hand.
- **Evidence required:** existing products or open-source projects do comparable things; the needed components are documented and available.
- **Typical signals:** standard frameworks cover it; estimates are in days to weeks; risks are mostly execution risks.
- **Example:** an online booking system for a small clinic.
- **Next step:** plan and build.

### 2. Feasible with substantial engineering

- **Definition:** the techniques are known and proven elsewhere, but applying them here takes significant effort, expertise or integration work.
- **Evidence required:** documented techniques and at least one comparable system exist; the gap is effort, scale or integration, not unknown science.
- **Typical signals:** needs specialists, careful architecture or months of work; known hard problems (real-time collaboration, large-scale search, offline synchronization).
- **Example:** real-time collaborative editing for a new document type using established synchronization techniques.
- **Next step:** architecture work and a prototype of the hardest integration.

### 3. Experimental

- **Definition:** plausible and partly demonstrated (research results, early prototypes, narrow demos) but without proof that it works reliably in conditions like ours.
- **Evidence required:** published results or credible demonstrations exist; reproduction in our conditions has not been shown.
- **Typical signals:** results depend on conditions that may not hold; few or no production deployments; outcomes vary between attempts.
- **Example:** applying a recently published technique, so far shown only on benchmark datasets, to messy production data.
- **Next step:** a time-boxed experiment with pre-set success and kill criteria.

### 4. Speculative

- **Definition:** depends on capabilities that have not been demonstrated, though nothing known rules them out.
- **Evidence required:** a coherent argument for why it might work; acknowledgement that the key capability is unproven.
- **Typical signals:** "if we could..." statements at the core; no prototype path that tests the core quickly; heavy reliance on future advances.
- **Example:** a system that must reliably migrate arbitrary legacy codebases to a new language with no human review.
- **Next step:** research to find whether any part can be demonstrated; keep separate from delivery plans.

### 5. Currently impractical

- **Definition:** conflicts with known physical, mathematical, informational or economic limits, or needs resources far beyond reach.
- **Evidence required:** the specific limit or cost that blocks it.
- **Typical signals:** violates known bounds (for example compressing arbitrary data far below its information content); costs orders of magnitude beyond the value; requires legal or regulatory changes outside the project's control.
- **Example:** a lossless compressor that shrinks every possible input file.
- **Next step:** reframe the problem; often a relaxed version of the goal lands at a feasible level.

## Rating procedure

1. Break the concept into its components and identify the one that is hardest to achieve.
2. Rate each component; the concept's rating is the rating of its least feasible essential component.
3. Name the evidence behind each rating: products, papers, prototypes, documented limits.
4. Note what would move the rating up (a successful experiment, a new capability) or down (a failed reproduction, a cost discovery).
5. Rate the operational reality, not only the demo: reliability, maintenance, cost at scale, security and compliance.

## Common rating mistakes

- **Demo optimism:** treating a controlled demonstration as proof of production feasibility.
- **Ignoring operations:** rating the build but not the cost of running, securing and maintaining it.
- **Scale blindness:** assuming what works on samples works on full data volumes.
- **Novelty bias:** rating an idea higher because it is exciting, or lower because it is ordinary.
- **Hidden dependencies:** forgetting regulatory approval, data access, partnerships or hardware supply.

## Presenting ratings

State the level, the reason and the evidence in one line, for example: "Experimental: the technique is published with benchmark results, but no production use on comparable data has been reported, and our data is noisier than the benchmarks." Keep speculative and impractical concepts visibly separate from feasible ones, and never present a speculative concept with delivery-plan confidence.
