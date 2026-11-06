# HTTP Semantics for Integrations

The parts of HTTP that decide whether an integration is correct under retries, caching and failure.

## Methods

| Method | Safe | Idempotent | Typical use |
|---|---|---|---|
| GET, HEAD, OPTIONS | Yes | Yes | Read |
| PUT | No | Yes | Replace a resource at a known URL |
| DELETE | No | Yes | Remove (repeating it leaves the same state) |
| POST | No | No | Create, or trigger an action |
| PATCH | No | Not guaranteed | Partial update |

Idempotent methods can be retried safely. POST and PATCH need an idempotency key (a client-generated unique value the server uses to deduplicate) before automatic retries.

## Status codes that drive behavior

| Code | Meaning | Client action |
|---|---|---|
| 200, 201, 202, 204 | Success (202: accepted for later processing) | For 202, poll or wait for a webhook |
| 301, 302, 307, 308 | Redirect | Follow only to trusted origins; 307 and 308 keep the method |
| 400, 422 | Invalid request | Fix the request; do not retry |
| 401 | Missing or invalid credentials | Refresh the token once, then fail |
| 403 | Authenticated but not allowed | Do not retry; check scopes |
| 404, 410 | Not found or gone | Do not retry |
| 409 | Conflict (version or state) | Re-read and reconcile |
| 429 | Rate limited | Wait (Retry-After), then retry |
| 500, 502, 503, 504 | Server or gateway trouble | Retry with backoff when the method is safe to repeat |

## Headers worth handling

- `Retry-After`: seconds (or an HTTP date) to wait before retrying.
- `X-Request-Id` or similar: log it; providers need it to debug your requests.
- `ETag` with `If-None-Match` (caching) and `If-Match` (optimistic concurrency).
- Rate-limit headers (names vary by provider): read the provider's documentation rather than guessing names.
- `Link` with `rel="next"` for link-based pagination (RFC 8288).

## Pagination styles

| Style | Mechanism | Notes |
|---|---|---|
| Cursor | Response returns an opaque cursor for the next page | Stable under inserts; preferred |
| Link header | `Link: <url>; rel="next"` | Follow URLs as given |
| Offset and limit | `offset=N&limit=M` | Simple; items can shift between pages under concurrent writes |

## GraphQL and WebSockets

- GraphQL often returns HTTP 200 with an `errors` array: check it on every response. Paginate with the schema's connections or cursors.
- WebSockets need heartbeats, reconnects with backoff, resubscription after reconnect, and idempotent message handling.
