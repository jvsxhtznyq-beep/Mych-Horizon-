# Research: how should staff passwords be hashed under the standard-library-only rule?

Date: 2026-11-01 | Depth: standard | Confidence: medium (local facts high; parameter guidance not verified against the primary source in this session)

## Conclusion
For this project's constraints, use `hashlib.scrypt` with N=2^17, r=8, p=1, a 16-byte random salt and an explicit `maxmem`, storing the parameters in each hash so they can be raised later. Unsalted SHA-256, the current scheme, is not a password hash: it is fast and unsalted, so leaked hashes are cheap to crack.

## Recommendation
Adopt scrypt as above and upgrade legacy SHA-256 hashes when each user next signs in successfully. Switch to PBKDF2-HMAC-SHA256 with at least 600,000 iterations if the server cannot afford about 128 MiB per concurrent sign-in, or if a FIPS-140 requirement appears. If third-party packages ever become allowed, prefer Argon2id.

## Question and decision
- Question: which password-hashing scheme and parameters for staff accounts?
- Decision it informs: the implementation in Task B and decision record 0002.
- Context: one small server, a handful of staff accounts, infrequent sign-ins; Python 3.13 in this environment (project supports 3.9 and later).
- Criteria and weights, set before gathering evidence: resistance to offline cracking per current guidance (40%), available in the standard library (25%, a hard constraint), cost on a small single server (20%), ease of migrating from SHA-256 (15%).
- Constraint: standard library only (CLAUDE.md).

## Method
- Web fetching was **unavailable**: `cheatsheetseries.owasp.org` and `docs.python.org` are blocked by this session's network policy. Web search worked; its snippets are used only as leads.
- Local experiment on this machine (Python 3.13.18, OpenSSL 3.5.9), median of 5 runs.

## Findings
| Claim | Label | Source |
|---|---|---|
| `hashlib.scrypt` and `hashlib.pbkdf2_hmac` are available here | Fact | Local run |
| scrypt with N=2^17, r=8, p=1 raises "memory limit exceeded" unless `maxmem` is raised (it needs about 128 MiB) | Fact | Local run |
| scrypt N=2^17, r=8, p=1 takes a median of 358 ms here (spread 298 to 778 ms) | Fact | Local run |
| PBKDF2-HMAC-SHA256 with 600,000 iterations takes a median of 100 ms here | Fact | Local run |
| `argon2` and `bcrypt` are not installed (and are excluded by the stdlib rule) | Fact | Local run |
| OWASP's minimums: Argon2id 19 MiB, t=2, p=1; scrypt N=2^17, r=8, p=1; PBKDF2-HMAC-SHA256 600,000 iterations; order Argon2id, then scrypt, with PBKDF2 for FIPS settings | Background, corroborated by search snippets; primary page not opened | Training knowledge; web search results pointing to the OWASP cheat sheet |
| scrypt is memory-hard, so GPU cracking costs more than for PBKDF2 at similar time cost | Background | Training knowledge |
| A 128 MiB-per-sign-in cost lets a flood of sign-ins exhaust memory on a small server | Inference | From the measured memory need |

## Comparison
| Criterion (weight) | scrypt N=2^17 | PBKDF2-SHA256 600k | Argon2id | bcrypt |
|---|---|---|---|---|
| Cracking resistance (40%) | Strong, memory-hard | Adequate, not memory-hard | Strongest per guidance | Good |
| Standard library (25%) | Yes | Yes | No | No |
| Small-server cost (20%) | 358 ms and 128 MiB per sign-in | 100 ms, negligible memory | n/a | n/a |
| Migration from SHA-256 (15%) | Rehash on sign-in | Rehash on sign-in | n/a | n/a |

Argon2id and bcrypt fail the hard constraint. scrypt wins on cracking resistance; PBKDF2 wins on server cost. With a handful of staff and infrequent sign-ins, scrypt's cost is affordable, provided sign-in attempts are rate-limited.

## Contradictions and how they were resolved
Search results included secondary pages with older figures (scrypt 2^16, Argon2id 15 MiB). They match an older version of the OWASP sheet; the newer figures above are used. This could not be confirmed on the primary page in this session.

## Open questions
- Exact current OWASP parameters: confirm on the cheat sheet once `cheatsheetseries.owasp.org` is reachable.
- Server memory and peak concurrent sign-ins: needed to confirm scrypt's 128 MiB per sign-in is safe.

## Sources
1. Local experiment, this session: Python 3.13.18, OpenSSL 3.5.9, five runs per configuration.
2. Web search results for "OWASP Password Storage Cheat Sheet ..." (leads only; the primary page was not opened): https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
