# Sensitive Change Workflow

For changes where a mistake can expose data, grant access, lose information, cost money or break production. Follow this in addition to the task's main workflow. The Engineer leads, with the Architect for trust boundaries and the Researcher for standards and advisories.

## What counts as sensitive

- Authentication, authorization, sessions, roles and permissions.
- Cryptography, secrets, keys, tokens and credential storage.
- Personal or confidential data: collection, storage, logging, export, retention.
- Data deletion, destructive migrations, bulk updates, backups and restores.
- Payments, billing, pricing and anything that moves money.
- Production configuration, infrastructure, DNS, network exposure (ports, CORS, firewall rules).
- CI/CD pipelines, deployment credentials, release processes.
- Dependency changes with security implications.

## Steps

1. **Classify.** Name the assets at risk (data, accounts, money, availability), who could be harmed, and any legal or regulatory obligations the change touches, such as data retention, privacy or financial records. State them in the plan; raise obligations with the owner rather than assuming compliance.
2. **Threat model, briefly.** For the changed surface, ask: who can reach it; what if the input is malicious; can someone act as another user; can someone see data they should not; what if the operation runs twice, partially or concurrently; what is logged; what fails open. Write down the threats that apply and how the change handles each.
3. **Mark approval points.** Every production action, deletion, permission widening, external publication, paid resource or credential change is gated ([autonomy-and-approval.md](../systems/autonomy-and-approval.md)).
4. **Plan a reversible path.** Backups or snapshots verified before destructive steps; feature flags; staged rollout; expand-and-contract migrations; a written rollback procedure, rehearsed where possible.
5. **Implement with secure defaults.** Least privilege, deny by default, parameterized queries, output encoding, validated input, secrets from the secret store, no sensitive data in logs or error messages ([security.md](../standards/security.md)).
6. **Verify, including the abuse cases.** Tests that unauthorized access is denied, invalid input is rejected and limits hold, not only that the happy path works. Review the diff for secrets and debug leftovers. Check new or changed dependencies against known advisories when tools allow.
7. **Request approval** for each gated step with the request format below.
8. **Execute gated steps only after approval,** one at a time, watching for errors; stop at the first unexpected result.
9. **Report** what changed, the security implications, residual risks, how to roll back, and anything the owner must do (for example rotate a credential).

## Approval request format

```text
Approval needed: run the migration that drops the legacy_sessions table in production.
Why: the table is unused since release 4.2 (no reads in 30 days of query logs).
Risk: irreversible deletion of about 1.2M rows; nothing in the application reads them.
Safeguard: snapshot taken at 14:05 UTC and test-restored to staging; rollback is restore from that snapshot.
Alternative: rename the table now and drop it in two weeks.
```

## Never

- Disable or weaken a security control to make something work.
- Widen permissions "temporarily" without approval and a removal plan.
- Commit, print, log or paste secrets, including in test fixtures and examples.
- Test against production data or systems without approval.
- Work around the environment's permission system or a denied action.
- Exploit a vulnerability you discover. Stop, report it to the owner, and recommend remediation (for a leaked credential: revoke and rotate).
