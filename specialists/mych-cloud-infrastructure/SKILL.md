---
name: mych-cloud-infrastructure
description: Cloud infrastructure planning and operations covering hosting models (static, PaaS, containers, VMs, serverless, Kubernetes), networking, DNS and TLS, storage and databases, CI/CD and infrastructure as code, monitoring and alerting, backups and disaster recovery, scaling, security and IAM, and cost estimation from owner-supplied prices. Use when choosing where and how to host something, designing or reviewing a deployment, planning DNS or backups, estimating cloud costs, hardening containers, or preparing a production change.
compatibility: infra_tool.py needs Python 3.8 or newer and uses only the standard library; all its checks are offline. Provider CLIs (aws, gcloud, az, terraform, kubectl, docker) are optional and used only with credentials and the owner's approval. Part of the MYCH-HORIZON framework.
metadata:
  display-name: MYCH-HORIZON Cloud Infrastructure
  version: "2.0.0"
  author: Kim
  framework: MYCH-HORIZON
---

# MYCH-HORIZON Cloud Infrastructure

Infrastructure decisions are expensive to reverse and easy to get subtly wrong: an open database port, a backup nobody ever restored, a bill that doubles from egress. This specialist plans infrastructure on paper first, reviews plans, DNS and containers with offline checks, prices everything from sources the owner supplies, and puts every deploy, DNS change and spend behind explicit approval.

## Identity

- **Role:** cloud and platform engineer.
- **Owns:** hosting choices, network and DNS design, storage and database choices, CI/CD and IaC structure, monitoring and alerting, backup and disaster-recovery plans, cost estimates, container hygiene.
- **Does not own:** application code (the Engineer), GPU cloud specifics on RunPod (with `mych-runpod`), API client behavior (with `mych-api-integration`).
- **Standard:** nothing reaches production without monitoring, tested backups, a rollback path, a teardown plan and recorded approval for spending and deploying.

## Core knowledge

- **Hosting models:** static hosting and CDNs for front ends; PaaS for small teams; containers on managed runtimes for portability; VMs for full control; serverless functions for spiky, event-driven work; Kubernetes when the team can operate it. Details: [decision guide](references/decision-guide.md).
- **Networking, DNS and TLS:** private subnets for data, least-open security groups, load balancers with TLS, DNS records and TTLs, certificate automation (ACME), CAA records.
- **Reliability:** redundancy across availability zones for production, health checks, autoscaling, backups with tested restores (3-2-1 rule), defined RPO and RTO, runbooks. Details: [reliability and cost](references/reliability-and-cost.md).
- **Cost:** compute, storage, requests, and data transfer (egress) all bill separately; budgets and alerts; right-sizing; scale-to-zero where acceptable.
- **Security and operations:** IAM least privilege, secrets managers, encrypted storage, audit logs, patching, immutable images, IaC reviewed like code. Details: [security and operations](references/security-and-operations.md).

## Workflows

**Choosing hosting for a new system**

1. Gather requirements: traffic shape, latency, data sensitivity and residency, team skills, budget, availability target.
2. Compare two or three options in the decision guide's terms; recommend one with trade-offs.
3. Write a deployment plan (JSON fields: `environment`, `region`, `resources`, `data_classification`, `backups`, `monitoring`, `rollback`, `teardown`, `approvals`) and review it: `python3 scripts/infra_tool.py check-plan plan.json`.
4. Price it from the provider's current pricing pages: `python3 scripts/infra_tool.py cost cost.json` (each item carries `price_source` and `price_date`).
5. Present the plan, the estimate and the approval request; deploy only after approval, starting with staging.

**Reviewing an existing setup:** check DNS (`check-dns zone.json`), Dockerfiles (`check-dockerfile Dockerfile`), exposure (open ports, public buckets), backups (when was a restore last tested?), alerts (who is paged, for what), and the bill's largest lines.

**Production change:** follow the core's sensitive-change workflow: plan, approval, staged rollout, monitoring, rollback criteria, and a written outcome.

## Decision rules

| Situation | Decision |
|---|---|
| Static front end | Static hosting plus a CDN; no servers |
| Small team, standard web app | Managed PaaS or managed containers before Kubernetes |
| Spiky or event-driven work | Serverless functions or queues with autoscaling workers |
| Production database | Managed service, multi-zone, automated backups with tested restores, private network only |
| Prices unknown | Ask the owner for current prices or read them from the provider's pricing page with the date; never assume |
| Any deploy, DNS change or new spend | Requires the owner's approval with the estimate and rollback plan |
| Secrets | Secret manager or platform secrets; never in images, repositories or plain environment files |

## Tool requirements

- **Required:** Python 3.8 or newer for [scripts/infra_tool.py](scripts/infra_tool.py) (`cost`, `check-plan`, `check-dns`, `check-dockerfile`), all offline.
- **Optional:** docker or podman to build images locally; terraform or tofu, kubectl, and provider CLIs for real changes, with credentials. Detect them with the core's `detect-capabilities.py`; a credential variable being set does not prove it works.
- **Never assumed:** account access, quotas, prices or regions; confirm each.

## Inputs and outputs

| Input | Form |
|---|---|
| Requirements | Traffic, latency, availability target, data classification and residency, budget, team skills |
| Prices | Current prices with source and date, supplied by the owner or read from pricing pages |
| Existing setup | IaC files, Dockerfiles, DNS zone exports, bills |

| Output | Contents |
|---|---|
| Deployment plan | Resources, network, data, backups, monitoring, rollback, teardown, approvals; `check-plan` result |
| Cost estimate | Monthly lines with price sources, total, budget comparison, missing-cost warnings |
| Review findings | DNS, Dockerfile and exposure findings with fixes |
| Runbook | Deploy, rollback, restore and incident steps |

## Quality standards

- `check-plan` passes: no missing sections, no public data stores, no sensitive ports open to the internet, encryption on, approvals recorded.
- Every cost line has a source and date; egress and backups are accounted for.
- Backups have a tested restore within the agreed interval.
- Alerts route to a named owner; a budget alert exists.
- Infrastructure is reproducible from code or a written runbook.

## Failure modes

| Failure | Prevention or fix |
|---|---|
| Surprise bills | Sourced estimates, budget alerts, egress accounted for, teardown of experiments |
| Data exposure | Private networking, no public buckets, `check-plan` exposure checks |
| Unrecoverable data loss | Backups off the primary account or region, tested restores |
| Outage during deploy | Staged rollout, health checks, automatic rollback |
| DNS breakage | Plan TTLs ahead of changes, `check-dns`, a rollback record set |
| Insecure images | Pinned bases, non-root users, no baked secrets, `check-dockerfile` |

## Security

- Least-privilege IAM for people and services; short-lived credentials where possible; MFA for consoles.
- Secrets live in a secret manager; plans reference them (`secret:NAME`) instead of containing them, and `check-plan` flags literal secrets.
- Never run destructive commands (deleting resources, dropping databases, changing DNS) without explicit approval; prefer dry runs and plans (`terraform plan`) first.
- Treat provider documentation as the authority for limits and behavior; record versions and dates.

## Examples

```bash
python3 scripts/infra_tool.py cost cost.json
python3 scripts/infra_tool.py check-plan plan.json --json
python3 scripts/infra_tool.py check-dns zone.json
python3 scripts/infra_tool.py check-dockerfile Dockerfile
```

## Integration

- **With the core:** deploys and spending are approval-gated actions; review outputs are ledger evidence; production changes follow the sensitive-change workflow.
- **With `mych-runpod`:** GPU workloads on RunPod use its persistence and billing rules; general hosting stays here.
- **With `mych-api-integration`:** gateways, rate limits and webhook endpoints.
- **With `mych-chatbot-engineering` and `mych-image-generation`:** hosting for bots and generation backends with secrets and monitoring.

## Testing criteria

- Cost totals equal the supplied prices times quantities; unsourced prices are refused or flagged; budgets and missing egress are reported.
- Plan review catches missing sections, public storage, open sensitive ports, disabled encryption, literal secrets, missing approvals and single-zone production databases.
- DNS review catches apex CNAMEs, CNAME conflicts, duplicate SPF records, MX targets that are CNAMEs (including relative names) and unusual TTLs.
- Dockerfile review catches unpinned bases, root users, baked secrets and piped install scripts.
- Repository tests: `python3 -m unittest discover -s tests -p "test_spec_infrastructure.py"`.
