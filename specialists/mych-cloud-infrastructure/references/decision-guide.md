# Hosting Decision Guide

Comparing hosting models by what they demand from the team and what they give back.

| Model | Good for | Team effort | Scaling | Cost shape | Watch out for |
|---|---|---|---|---|---|
| Static hosting plus CDN | Front ends, docs, marketing sites | Very low | Automatic | Mostly bandwidth | Server-side logic must live elsewhere |
| PaaS (managed app platform) | Standard web apps and APIs | Low | Built in, within platform limits | Per instance or usage | Platform limits, less control, lock-in |
| Managed containers | Portable services with custom runtimes | Low to medium | Autoscaling by requests or CPU | Per vCPU and memory time | Cold starts on scale-to-zero |
| Virtual machines | Full control, special software, steady load | Medium to high (patching, scaling) | Manual or scaling groups | Per hour while running | Patching, idle cost |
| Serverless functions | Spiky, event-driven, short tasks | Low | Automatic to high concurrency | Per request and duration | Time limits, cold starts, local testing |
| Kubernetes | Many services, platform teams | High | Very flexible | Cluster plus workloads | Operational complexity, security surface |

## Questions that decide

1. What availability does the business need, and what does an hour of downtime cost?
2. Where must data live (residency), and how sensitive is it?
3. What does the team already operate well?
4. Is load steady, spiky or seasonal?
5. What is the monthly budget, and who approves changes to it?

## Data stores

- Prefer managed databases with automated backups and multi-zone options for production.
- Object storage for files and backups; keep buckets private and serve public content through a CDN.
- Caches (Redis, Memcached) are not durable stores; plan for loss.

## Regions

Choose regions near users and inside residency constraints; check that every needed service is offered there. Multi-region adds cost and complexity: justify it with an availability or latency requirement.
