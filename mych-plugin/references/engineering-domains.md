# Engineering Domains

Domain-specific checklists for the Engineer ([engineer.md](../modes/engineer.md)). Each list holds the checks that most often separate working software from software that only looks finished. Apply the lists for the domains a change touches.

## Contents

- [Frontend](#frontend)
- [Backend](#backend)
- [Systems programming](#systems-programming)
- [Databases](#databases)
- [APIs](#apis)
- [Networking](#networking)
- [File systems](#file-systems)
- [Concurrency](#concurrency)
- [Command-line tools](#command-line-tools)
- [Deployment and operations](#deployment-and-operations)
- [Maintenance](#maintenance)

## Frontend

- [ ] Every data-driven view handles loading, empty, error and success states.
- [ ] Forms validate on the client for convenience and on the server for safety; errors appear next to fields.
- [ ] Semantic elements and accessible names; keyboard paths work ([accessibility-checklist.md](accessibility-checklist.md)).
- [ ] Design tokens implemented as variables or theme configuration, not repeated literal values.
- [ ] State lives in one place per piece of data; derived values are computed, not duplicated.
- [ ] No unnecessary re-renders or layout thrashing on hot paths; lists of many items are virtualized when needed.
- [ ] Bundle size watched: no heavy dependency for a small need; code split by route where the framework supports it.
- [ ] Images sized and compressed; layout does not shift as content loads.
- [ ] User input rendered through the framework's escaping; no raw HTML injection of untrusted content.
- [ ] Works at small, medium and large widths and in the supported browsers.

## Backend

- [ ] Input validated and parsed at the boundary into typed structures; unknown fields handled deliberately.
- [ ] Authorization checked for every operation and every object, on the server.
- [ ] Errors mapped to consistent responses; internals and stack traces never reach clients.
- [ ] Operations with side effects are idempotent or protected by idempotency keys where retries are possible.
- [ ] Transactions wrap multi-step writes that must succeed together; long transactions avoided.
- [ ] Outbound calls have timeouts, bounded retries with backoff, and clear failure handling.
- [ ] Configuration and secrets come from the environment or a secret manager.
- [ ] Structured logs with request identifiers; no secrets or personal data in logs.
- [ ] Background jobs are retry-safe and observable; failures land somewhere visible.

## Systems programming

- [ ] Memory and resource ownership is explicit; every acquired resource is released on every path, including errors.
- [ ] No undefined behavior: bounds checked, integer overflow considered, no use after free, no data races.
- [ ] Errors propagated with context rather than ignored; panics or aborts reserved for unrecoverable states.
- [ ] Unsafe code isolated, minimized and justified in a comment.
- [ ] Endianness, alignment and platform differences handled where data crosses machines.
- [ ] Performance claims backed by profiling under realistic workloads.

## Databases

- [ ] Schema changes are migrations under version control; expand and contract for anything live.
- [ ] Migrations tested forward, and backward when the tooling supports it; destructive steps flagged for approval.
- [ ] Queries parameterized; no string-built SQL.
- [ ] Indexes support the actual query patterns; query plans checked for slow or frequent queries.
- [ ] No N+1 query patterns in loops; batch or join instead.
- [ ] Constraints (foreign keys, uniqueness, not-null, checks) enforce invariants in the database, not only in code.
- [ ] Backups exist and a restore has been tested before risky operations.
- [ ] Time stored in UTC with explicit types; money stored as exact decimals or integer minor units.

## APIs

- [ ] Contract defined before implementation: operations, inputs, outputs, errors, authentication.
- [ ] Consistent naming, error format, pagination and filtering conventions across endpoints.
- [ ] Versioning strategy decided; breaking changes avoided or versioned with a deprecation path.
- [ ] Idempotency for retryable writes; correct use of HTTP methods and status codes for HTTP APIs.
- [ ] Rate limits and payload size limits on public endpoints.
- [ ] Documentation generated from or tested against the implementation (for example an OpenAPI description).
- [ ] Contract or integration tests for success and error responses.

## Networking

- [ ] Every connection and request has a timeout; retries are bounded with exponential backoff and jitter.
- [ ] Transport security enabled and certificate verification never disabled.
- [ ] Connection pooling and reuse where the client supports them.
- [ ] Partial failures, slow responses and dropped connections handled, not only total outages.
- [ ] Payloads compressed when large; chatty request patterns batched.
- [ ] Outbound destinations derived from input are validated against an allow-list.

## File systems

- [ ] Paths built with the platform's path utilities; untrusted path input resolved and checked against a base directory.
- [ ] Writes that must not leave partial files use write-to-temporary-then-rename in the same directory.
- [ ] Encodings explicit (UTF-8 unless the format says otherwise); line endings handled deliberately.
- [ ] File handles closed on every path; large files streamed rather than loaded whole.
- [ ] Permissions set deliberately for created files; secrets files not world-readable.
- [ ] Symbolic links handled deliberately; directory walks do not follow links into unexpected places.
- [ ] Temporary files created with secure APIs and cleaned up.

## Concurrency

- [ ] Shared mutable state minimized; access synchronized or confined to one owner.
- [ ] Lock ordering consistent to avoid deadlocks; locks never held across slow I/O without need.
- [ ] Cancellation and shutdown paths tested; no orphaned tasks or threads.
- [ ] Concurrency tests or stress runs for code that relies on ordering.

## Command-line tools

- [ ] `--help` explains usage with examples; errors go to standard error with a non-zero exit code.
- [ ] Exit codes documented and meaningful (for example 0 success, 1 failure found, 2 usage error).
- [ ] Destructive operations require explicit flags or confirmation; a dry-run mode where useful.
- [ ] Machine-readable output option (for example JSON) when other tools will consume the output.
- [ ] Works without color or interactive terminals when output is piped.

## Deployment and operations

- [ ] Builds are reproducible; the same artifact moves through every environment.
- [ ] Configuration separated from code and documented without secret values.
- [ ] Health and readiness checks reflect real ability to serve.
- [ ] Rollout can be stopped and rolled back; database migrations compatible with the previous release.
- [ ] Monitoring and alerts cover user-facing symptoms; runbooks exist for alerts.
- [ ] Production changes follow [sensitive-change.md](../workflows/sensitive-change.md).

## Maintenance

- [ ] Dependencies updated deliberately, with changelogs read for breaking changes and the test suite run.
- [ ] Deprecation warnings addressed before they become errors.
- [ ] Dead code and stale feature flags removed.
- [ ] Documentation kept in step with behavior; README run instructions still work.
- [ ] Recurring failures turned into tests, and recurring decisions into decision records.
