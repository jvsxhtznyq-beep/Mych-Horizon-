# Delivery report: staff password hashing

Date: 2026-11-01 | State: partially complete (code verified locally; production migration and credential rotation await you)

## Outcome
New staff passwords are hashed with salted scrypt; old SHA-256 hashes still verify and are upgraded on the next successful sign-in. Verified locally with abuse-case tests (22/22 suite). Nothing was changed in production and `.env` was neither read nor written.

## Needs your attention

**Approval needed: production rollout and migration of staff hashes.**
- Why: removes fast unsalted hashes from production.
- What it takes: deploying this code (same gated deploy as the booking fix). With lazy upgrade, no bulk database write is needed.
- Risk: sign-in uses about 128 MiB and 0.3 to 0.8 s per attempt on this machine; a flood of attempts could exhaust memory without rate limiting.
- Decision for you: accounts that never sign in keep SHA-256 hashes. Choose lazy only, a forced reset of dormant accounts, or a bulk wrap (a production data migration that needs its own approval and backup).

**Owner action: rotate the admin password.**
- The request asked me to update it in `.env`. I did not read or write `.env`: it holds production secrets, and changing a production credential is gated. Because old SHA-256 hashes are weak, rotate the admin password through your own secret process, and do not paste it into chat.

## Threat model (sensitive-change step 2)
| Threat | Handling |
|---|---|
| Offline cracking of leaked hashes | scrypt with per-hash salt; legacy hashes upgraded on sign-in |
| Username discovery through timing | Unknown usernames verified against a dummy hash |
| Tampered or malformed stored hash | Fails closed; stored parameters capped (N at most 2^20) to bound memory |
| Timing attacks on comparison | `hmac.compare_digest` for both formats |
| Memory exhaustion by sign-in floods | Not handled in code: rate limiting recommended (follow-up) |
| Secrets in logs or code | None added (diff reviewed) |

## Verification
| Requirement | Check | Result |
|---|---|---|
| Correct password accepted, wrong rejected | `test_correct_password_verifies`, `test_wrong_password_is_rejected` | Pass |
| Unknown users rejected | `test_directory_authenticates_known_staff_only` | Pass |
| Salt differs per hash | `test_same_password_gets_different_salts` | Pass |
| Tampered and malformed hashes fail closed | `test_tampered_key_is_rejected`, `test_malformed_hashes_fail_closed` | Pass |
| Legacy hash verifies, upgrades only after success | `test_legacy_sha256_hash_verifies_and_is_upgraded_on_sign_in` | Pass |
| Default parameters meet the documented minimum | `test_default_parameters_meet_the_documented_minimum` (real N=2^17) | Pass |
| Nothing else broke | `python3 -m unittest discover -s tests` | 22 passed |

## Unverified
- OWASP parameters were not confirmed on the primary page (`cheatsheetseries.owasp.org` is blocked here); they rest on training knowledge corroborated by search results.
- Production behavior and memory headroom: not measured.

## Rollback
Redeploy the previous release. Hashes already upgraded to scrypt would then fail to verify on the old code, so roll back only together with a password reset for upgraded accounts, or keep this verifier.
