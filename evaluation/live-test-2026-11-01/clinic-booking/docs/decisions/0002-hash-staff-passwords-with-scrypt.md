# 0002. Hash staff passwords with scrypt and upgrade legacy hashes on sign-in

- Date: 2026-11-01
- Status: Accepted locally; production rollout awaiting the owner's approval
- Deciders: implementation session; owner to confirm the rollout

## Context
Staff passwords were stored as unsalted SHA-256, which is fast to crack if the hashes leak. The project allows only the standard library (CLAUDE.md). Research: [docs/research/2026-11-01-password-hashing.md](../research/2026-11-01-password-hashing.md).

## Problem
Which hashing scheme, and how do existing accounts move off SHA-256 without knowing their passwords?

## Options
1. **scrypt (N=2^17, r=8, p=1) with lazy upgrade on sign-in.** Pros: memory-hard, standard library, no bulk production write. Cons: about 128 MiB and 0.3 to 0.8 s per sign-in here; dormant accounts stay on SHA-256 until they sign in.
2. **PBKDF2-HMAC-SHA256 (600,000 iterations).** Pros: cheap in memory, standard library. Cons: not memory-hard.
3. **Bulk wrap: scrypt(SHA-256 hash) for every account now.** Pros: protects dormant accounts immediately. Cons: needs a production data migration and a second verification format.
4. **Argon2id or bcrypt.** Excluded: third-party packages.

## Decision
Option 1, with each hash carrying its parameters (`scrypt$N$r$p$salt$key`) so they can be raised later. Unknown or malformed formats fail closed. Unknown usernames are checked against a dummy hash so timing does not reveal valid usernames.

## Consequences
- Easier: parameters can be raised without another format change; no bulk write is needed to start.
- Harder: sign-in costs more memory and time, so sign-in attempts should be rate-limited.
- Risk accepted until the owner decides: dormant accounts keep SHA-256 hashes. Options 3, or a forced reset of dormant accounts, close this.

## Alternatives rejected
- PBKDF2: weaker against GPU cracking at similar time cost; kept as the fallback if memory is constrained.
- Argon2id and bcrypt: violate the standard-library rule.
