# Security and Operations

Running infrastructure safely day to day.

## Identity and access

- Separate accounts or projects for production and non-production.
- Least privilege for people and workloads; avoid long-lived keys (use workload identity or short-lived tokens).
- MFA for console access; break-glass accounts monitored and rarely used.

## Network

- Databases and internal services in private subnets with no public addresses.
- Security groups open only the ports needed, from the sources needed; never SSH, RDP or database ports to `0.0.0.0/0`.
- TLS everywhere, certificates renewed automatically; HSTS for web front ends.

## Secrets and data

- Secret managers or platform secrets, injected at runtime; never in images, repositories, IaC state shared publicly, or logs.
- Encryption at rest for all stores holding personal or confidential data; key management with rotation.
- Classify data and apply retention and access controls per class.

## Change management

- Infrastructure as code reviewed like application code; `plan` before `apply`.
- Staged rollouts with health checks and automatic rollback.
- Production changes, DNS changes and new spending require the owner's approval (the MYCH core's approval rules).

## Containers

- Pin base images by version or digest; rebuild regularly for security patches.
- Run as a non-root user; drop capabilities; read-only file systems where possible.
- No secrets in `ENV` or `ARG`; use runtime secrets or build secrets.
- Add health checks; keep images small (multi-stage builds, clean package caches).

`infra_tool.py check-dockerfile` checks several of these rules offline.

## Incidents

Detect, stabilize, communicate, then fix. Do not take destructive remediation (deleting data or resources) without approval; record a timeline and write a blameless review afterwards.
