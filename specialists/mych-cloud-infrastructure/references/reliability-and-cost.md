# Reliability and Cost

Keeping systems up and bills predictable.

## Availability building blocks

- **Redundancy:** at least two instances across availability zones for production services and databases.
- **Health checks:** load balancers remove unhealthy instances; orchestrators restart hung processes.
- **Autoscaling:** scale on a signal that tracks load (requests, queue depth, CPU), with minimums that survive a zone loss.
- **Graceful degradation:** decide what still works when a dependency fails.

## Backups and disaster recovery

- **3-2-1:** three copies, on two kinds of storage, one off-site (another region or account).
- **RPO** (how much data loss is acceptable) sets backup frequency; **RTO** (how long recovery may take) sets the restore approach.
- **Test restores** on a schedule and record the date and duration; an untested backup is not a plan.
- Protect backups from deletion (separate account or retention locks) so one compromised credential cannot destroy everything.

## Monitoring

- Alert on symptoms users feel (error rate, latency, availability), not only on resource metrics.
- Every alert has an owner and a runbook entry; noisy alerts get fixed or removed.
- Keep logs structured, redacted and retained per policy.

## Cost control

| Driver | Control |
|---|---|
| Idle compute | Right-size; schedule non-production shutdowns; scale to zero where acceptable |
| Data transfer (egress) | Keep traffic within a region; cache at the CDN; compress |
| Storage growth | Lifecycle rules; delete old snapshots and logs per retention |
| Forgotten experiments | Tags with owner and expiry; teardown steps in every plan |
| Surprises | Budgets with alerts at thresholds; review the bill monthly |

`infra_tool.py cost` multiplies owner-supplied prices only and requires a source and date for each; it warns when no egress line exists. Treat its total as an estimate: real bills depend on usage, discounts and taxes.
