# Resilience Patterns

How the client survives slow, failing or rate-limited APIs without making things worse.

## Timeouts

Every call needs a timeout (connect and read). Without one, a hung connection holds a worker forever. Pick timeouts from the API's documented latency plus margin, not from defaults.

## Retries

- Retry only transient failures: 429, 500, 502, 503, 504 and connection errors.
- Retry only idempotent operations, or POST and PATCH with an idempotency key.
- Use **exponential backoff with jitter**: delay = random between half and all of `base * 2^attempt`, capped. Jitter prevents synchronized retry waves.
- Honor `Retry-After` when present.
- Bound attempts (3 to 5 total is common) and the total time budget.

`apiclient.RetryPolicy` implements these rules; `ApiError` reports when a POST was not retried for lack of a key.

## Rate limiting on the client

A token bucket (`apiclient.TokenBucket`) keeps the average request rate under the provider's limit while allowing short bursts. Size it from the documented limit with a safety margin, per credential.

## Circuit breaker

After a run of consecutive failures, `apiclient.CircuitBreaker` opens and fails fast for a cooling period, then lets one trial request through (half-open). This protects both sides during outages and gives users a fast, clear error.

## Idempotency on the server side

When you design an API, accept an `Idempotency-Key` header on creates: store the key with the result and return the stored result for repeats within a retention window.

## Degradation

Decide in advance what users see when a dependency is down: cached data with a notice, a queued action, or a clear error. Never retry forever in a user-facing request.
