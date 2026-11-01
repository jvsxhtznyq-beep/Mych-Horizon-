# Performance Investigation Workflow

For slowness, excessive resource use and scaling limits. The combination is Researcher, Architect and Engineer, with the Engineer leading. The rule: **measure, change one thing, measure again.** An optimization without before-and-after numbers under the same conditions is an opinion.

## Steps

1. **Define the metric and target.** Name the metric precisely (p95 request latency, throughput at a stated concurrency, peak memory, startup time, bundle size, time to interactive, query duration) and the target, from requirements or from the owner. Without a target, agree on what "fast enough" means.
2. **Fix the conditions.** Environment, hardware or instance type, data size, workload, versions, warm or cold caches. Write them down; every later measurement uses the same conditions.
3. **Measure the baseline.** Repeat runs (at least five for noisy metrics), discard warm-up runs where appropriate, and report the median and the spread. Keep the measurement script.
4. **Profile to find where the time or memory goes.** Use the profiler that fits the layer: CPU profilers and flame graphs, query plans (`EXPLAIN ANALYZE` or the database's equivalent), allocation and heap snapshots, browser performance and network waterfalls, system tools for I/O and contention. Do not guess the bottleneck.
5. **Hypothesize.** For the largest measured cost, state why it is expensive and what change would reduce it.
6. **Change one thing.** The smallest change that tests the hypothesis.
7. **Re-measure under identical conditions.** Compare against the baseline with the spread in mind; a change inside the noise is not an improvement.
8. **Keep or revert.** Keep changes that move the metric meaningfully without harming correctness or readability disproportionately; revert the rest.
9. **Repeat** from step 4 until the target is met or returns diminish. Report when the remaining gap needs a structural change.
10. **Check correctness and regressions.** Run the test suite; check other metrics did not get worse (memory for speed, latency for throughput).
11. **Report** the before-and-after table with conditions.

## Common causes to check

| Layer | Frequent causes |
|---|---|
| Data access | N+1 queries, missing or unused indexes, fetching unused columns or rows, unbounded queries, lock contention |
| Application | Quadratic algorithms on growing inputs, repeated expensive computation, excessive allocation, blocking I/O on hot paths, serialization overhead |
| Network | Chatty calls that could be batched, no connection reuse, missing compression, large payloads, sequential calls that could run in parallel |
| Frontend | Large bundles, render thrashing, unoptimized images, blocking scripts, layout shifts, too many re-renders |
| Infrastructure | Undersized resources, cold starts, noisy neighbors, missing caching at the edge |

## When the cause is structural

Bring in the Architect when profiling shows the limit is the design itself: one database serving every workload, synchronous chains across services, a missing queue for bursty work, data that no longer fits one node. Structural changes need a proposal ([architecture-proposal.md](../templates/architecture-proposal.md)) and usually a decision record.

## Report format

| Metric | Baseline | After | Change | Conditions |
|---|---|---|---|---|
| p95 latency, GET /orders | 840 ms (spread 790 to 910) | 210 ms (spread 195 to 240) | -75% | 50 concurrent users, 1M orders, staging instance, 10 runs |

Below the table: what changed and why it helped, what was tried and reverted, correctness evidence, and the remaining gap to the target, if any. Use [investigation-log.md](../templates/investigation-log.md) to keep the hypotheses and experiments in order.
