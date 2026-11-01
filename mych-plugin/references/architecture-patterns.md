# Architecture Patterns

A catalog of architectural patterns with when to use them, when to avoid them and what they cost. Use it while generating and evaluating candidate architectures ([architect.md](../modes/architect.md)). Every pattern here solves a specific problem; none is a default upgrade.

## Contents

- [Structural styles](#structural-styles)
- [Communication](#communication)
- [Data management](#data-management)
- [Caching](#caching)
- [Reliability](#reliability)
- [Deployment and release](#deployment-and-release)
- [Observability](#observability)
- [Choosing between patterns](#choosing-between-patterns)

## Structural styles

| Pattern | What it is | Use when | Avoid when | Main risks |
|---|---|---|---|---|
| Layered monolith | One deployable organized in layers (interface, domain, data) | Small to medium apps, one team, early products | Layers become pass-through boilerplate | Tangled dependencies across features |
| Modular monolith | One deployable split into modules with enforced boundaries and owned data | Growing products, one or a few teams; the default for most new systems | A module truly needs independent scaling or isolation today | Boundaries eroding without automated checks |
| Microservices | Independently deployable services per business capability, each owning its data | Several teams need independent release; parts have very different scaling or isolation needs | Small teams, unclear domain boundaries, no operational maturity | Distributed monolith, network failures, data consistency, operational load |
| Coarse services (service-oriented) | A few larger services around major domains | Clear major domains, moderate team count | The domains are not yet understood | Services growing into monoliths again |
| Serverless functions | Event-triggered functions on a managed platform | Spiky or low traffic, event processing, glue code | Long-running or latency-critical work, heavy local state | Cold starts, vendor lock-in, hard local testing, cost at sustained load |
| Hexagonal (ports and adapters) | Domain core isolated behind interfaces; infrastructure in adapters | Complex domain logic that must be testable and outlive infrastructure choices | Simple CRUD where indirection adds nothing | Over-abstraction |
| Client-server | Clients call a server that owns data and rules | Most applications | Fully offline or peer-to-peer requirements | Server as a single point of failure if not redundant |
| Backend for frontend | A dedicated backend layer per client type | Clients with very different data needs (mobile, web, partners) | One client type | Duplicated logic across backends |
| Micro-frontends | Independently deployed frontend parts per team | Many teams on one large frontend | Single team or small app | Inconsistent UX, heavier bundles, integration complexity |
| Plugin architecture | A core with extension points loaded at runtime or by convention | Products extended by third parties or by many independent features | Extension needs are speculative | Unstable extension contracts |

## Communication

| Pattern | What it is | Use when | Avoid when | Main risks |
|---|---|---|---|---|
| REST over HTTP | Resource-oriented request and response | Public and general-purpose APIs | Chatty high-frequency internal calls | Over- and under-fetching, versioning drift |
| GraphQL | Client-specified queries over a typed schema | Many clients with varied read needs | Simple APIs, heavy write workloads | Expensive queries, caching complexity, authorization per field |
| gRPC | Typed binary RPC over HTTP/2 | Internal service calls with strict contracts and high throughput | Browser clients without a proxy | Tooling and debugging overhead |
| Message queue | Producers enqueue work; consumers process asynchronously | Background work, load leveling, retries | The caller needs the result immediately | Poison messages, duplicate delivery, ordering |
| Publish and subscribe | Events broadcast to any number of subscribers | Several consumers react to the same fact | One consumer; the producer needs a response | Hidden coupling through event schemas, eventual consistency |
| Event streaming log | Durable ordered log consumers read at their own pace | High-volume events, replay, multiple downstream systems | Small systems | Operational complexity, partitioning and ordering design |
| Event sourcing | State stored as a sequence of events | Audit-critical domains, temporal queries | Most CRUD domains | Schema evolution of events, rebuild costs, steep learning curve |
| CQRS | Separate models for writes and reads | Read and write workloads diverge strongly | Simple domains | Two models to keep consistent |
| Webhooks | HTTP callbacks to external systems | Notifying third parties of events | Receivers cannot accept inbound HTTP | Receiver downtime, replay attacks without signatures |
| WebSockets or server-sent events | Persistent connection for server push | Live updates, collaboration, notifications | Infrequent updates (use polling) | Connection scaling, reconnection logic |
| API gateway | One entry point for routing, authentication and rate limiting | Several services behind one public surface | One service | Gateway as bottleneck or single point of failure |

## Data management

| Pattern | What it is | Use when | Avoid when | Main risks |
|---|---|---|---|---|
| Single relational database | One transactional store | Most systems at most scales | Proven need for specialized access patterns | Becoming a shared integration point for many services |
| Database per service | Each service owns its store | Microservices | A monolith | Cross-service queries and consistency |
| Read replicas | Copies serving reads | Read-heavy workloads | Strong read-after-write needs everywhere | Replication lag visible to users |
| Partitioning (sharding) | Data split across nodes by key | Data or load exceeds one node | Before vertical scaling and indexing are exhausted | Hot partitions, cross-shard queries, resharding |
| Polyglot persistence | Different stores for different access patterns | Demonstrated needs such as search or time series | Speculative needs | Operational load, data synchronization |
| Transactional outbox | Events written in the same transaction as data, then published | Reliable event publishing from a transactional store | No events | Publisher lag, duplicate events (consumers must be idempotent) |
| Saga | A multi-step workflow with compensating actions | Business transactions across services | A single database transaction suffices | Complex failure handling, partial states visible |
| Change data capture | Stream changes from the database log | Feeding search indexes, caches or analytics | Small systems | Schema coupling to consumers |
| Analytics separation | Warehouse or lake fed from operational stores | Heavy analytical queries | Small reporting needs | Freshness lag, pipeline maintenance |

## Caching

| Pattern | What it is | Use when | Main risks |
|---|---|---|---|
| Cache-aside | Application reads cache, falls back to store, populates cache | General-purpose read caching | Stale data, stampedes on expiry |
| Read-through | Cache loads from the store on miss | A caching layer that supports loaders | Hidden latency on misses |
| Write-through | Writes go to cache and store together | Reads must see fresh writes | Write latency |
| Write-behind | Writes go to cache, flushed later | Write bursts tolerating delay | Data loss on cache failure |
| Edge or CDN caching | Responses cached near users | Static assets, public cacheable responses | Serving stale or personalized content wrongly |
| Memoization | Cache pure function results in process | Expensive deterministic computations | Unbounded memory growth |

Decide invalidation (time to live, explicit invalidation, versioned keys) before adding any cache.

## Reliability

| Pattern | Purpose | Notes |
|---|---|---|
| Timeouts | Bound waiting on any remote call | Every remote call; set from latency targets |
| Retries with exponential backoff and jitter | Survive transient failures | Only for idempotent operations; cap attempts |
| Idempotency keys | Make retries and duplicates safe | Required for payments and other side effects |
| Circuit breaker | Stop calling a failing dependency | Pair with a fallback or clear error |
| Bulkhead | Isolate resources per dependency or tenant | Prevents one failure exhausting shared pools |
| Rate limiting and throttling | Protect capacity and prevent abuse | At entry points and expensive operations |
| Backpressure | Slow producers when consumers fall behind | Queues with bounded size |
| Graceful degradation | Keep core functions when parts fail | Cached data, read-only mode, disabled extras |
| Health checks and readiness | Route traffic only to healthy instances | Separate liveness from readiness |
| Redundancy | Remove single points of failure the targets cannot tolerate | Across instances, zones or regions as targets require |

## Deployment and release

| Pattern | Use when | Notes |
|---|---|---|
| Rolling deployment | Stateless services with backward-compatible changes | Old and new versions run together briefly |
| Blue-green | Fast rollback by switching traffic | Requires duplicate capacity during the switch |
| Canary | Risky changes; measurable health signals | Route a small share of traffic first; automate rollback triggers |
| Feature flags | Decouple deploy from release; staged rollouts | Remove stale flags; flags are configuration debt |
| Expand and contract migrations | Schema changes without downtime | Each step deployable and reversible on its own |
| Infrastructure as code | Reproducible environments | Review infrastructure changes like code |
| Immutable artifacts | Same build through every environment | Configuration injected at deploy time |

## Observability

| Practice | What to implement |
|---|---|
| Structured logging | JSON or key-value logs with correlation identifiers; no secrets or personal data |
| Request metrics | Rate, errors and duration per endpoint |
| Resource metrics | Utilization, saturation and errors per resource |
| Distributed tracing | Trace context propagated across service boundaries |
| Service level objectives | Targets with error budgets that guide release pace |
| Symptom-based alerting | Alerts on user-visible symptoms, each with a runbook |

## Choosing between patterns

1. Start from the simplest structure that meets the quantified requirements.
2. For each additional pattern, name the requirement it satisfies and the cost it adds.
3. Prefer patterns the team can operate; operational capability is a constraint, not an afterthought.
4. Prefer reversible choices; record irreversible ones as decision records.
5. Re-evaluate when a named trigger occurs (load threshold, team growth, new compliance need), not on a schedule.
