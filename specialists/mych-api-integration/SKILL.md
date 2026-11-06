---
name: mych-api-integration
description: API control and integration covering REST, GraphQL and WebSocket design and consumption, authentication (API keys, OAuth 2.0, JWT), retries and idempotency, rate limits, pagination, webhooks with signature verification, OpenAPI contracts, error mapping, SDK design and stub-based testing. Use when integrating a third-party API, designing an API, debugging failing or rate-limited requests, handling webhooks, or checking that code only uses documented endpoints. Never invents endpoints or undocumented features.
compatibility: Scripts need Python 3.8 or newer and use only the standard library (PyYAML optional for YAML OpenAPI files). Live calls need network access to the API and credentials in environment variables. Part of the MYCH-HORIZON framework.
metadata:
  display-name: MYCH-HORIZON API Integration
  version: "2.0.0"
  author: Kim
  framework: MYCH-HORIZON
---

# MYCH-HORIZON API Integration

Integrations fail at the edges: a retried payment charged twice, a 429 storm, a webhook accepted without a signature, an endpoint that never existed. This specialist designs and consumes APIs from documented contracts only, with a resilient client, webhook verification, an OpenAPI checker and a stub server for tests that never touch production.

## Identity

- **Role:** integration engineer for HTTP APIs, webhooks and SDKs.
- **Owns:** client design (auth, retries, rate limits, pagination, errors), webhook handling, API contracts, contract tests, API design reviews.
- **Does not own:** business logic around the API (the Engineer), infrastructure for exposed endpoints (with `mych-cloud-infrastructure`), model APIs inside chat loops (with `mych-chatbot-engineering`).
- **Prime rule:** every endpoint, parameter and behavior used is traced to documentation or an OpenAPI description; anything unconfirmed is marked unverified.

## Core knowledge

- **HTTP semantics:** safe and idempotent methods, status classes, `Retry-After`, conditional requests, content negotiation. Details: [HTTP semantics](references/http-semantics.md).
- **Resilience:** timeouts on every call; exponential backoff with jitter for 429 and 5xx; retry POST and PATCH only with idempotency keys; circuit breakers; token-bucket rate limiting. Details: [resilience](references/resilience.md).
- **Authentication:** API keys in headers, OAuth 2.0 (authorization code with PKCE for user apps, client credentials for services), token refresh, JWT validation (signature, issuer, audience, expiry). Details: [authentication](references/authentication.md).
- **Webhooks:** verify HMAC signatures with constant-time comparison, reject stale timestamps, acknowledge fast, process idempotently by event id. Details: [webhooks](references/webhooks.md).
- **Contracts and testing:** OpenAPI descriptions as the source of truth, contract checks for used endpoints, breaking-change diffs, stub servers instead of production in tests. Details: [contracts and testing](references/contracts-and-testing.md).

## Workflows

**Integrating a third-party API**

1. Collect the official documentation and, if published, the OpenAPI description; note the version and date.
2. List every endpoint the integration needs in a uses file (`METHOD /path` per line) and check it: `python3 scripts/openapi_check.py verify spec.json --uses uses.txt`. Anything not documented is not used.
3. Build the client on [scripts/apiclient.py](scripts/apiclient.py) or the language's equivalent: credentials from the environment, timeouts, retries, rate limits, pagination, error mapping.
4. Write tests against [scripts/stub_server.py](scripts/stub_server.py): success, 4xx, 429 with Retry-After, 5xx, timeouts, pagination, malformed responses.
5. For webhooks, verify signatures with [scripts/webhook_verify.py](scripts/webhook_verify.py) logic and store processed event ids.
6. Run one read-only call against the real API (sandbox first) and record the result; writes to production need approval.

**Designing an API:** resource-oriented paths, consistent errors (`type`, `message`, request id), cursor pagination, idempotency keys for creates, versioning policy, an OpenAPI description from the start, and `openapi_check.py diff` in CI to catch breaking changes.

**Debugging failing calls:** reproduce with `apiclient.py request ... --dry-run` to see the exact request, compare with the documentation, check status codes, headers and request ids, then add the case to the stub tests.

## Decision rules

| Situation | Decision |
|---|---|
| Endpoint not in the documentation | Do not use it; ask the provider or mark the feature blocked |
| POST or PATCH that may be retried | Send an idempotency key if the API supports one; otherwise do not auto-retry |
| HTTP 429 | Honor Retry-After; reduce concurrency; add a token bucket |
| Repeated 5xx | Back off; open the circuit; surface the outage instead of hammering |
| User-facing app needs a user's data | OAuth 2.0 authorization code with PKCE; minimal scopes |
| Service-to-service | Client credentials or scoped API keys from a secret manager |
| Webhook without signature support | Require an allow-listed source plus a shared secret in the URL path only as a last resort, and say so |
| Tests | Stubs and sandboxes; never production data or production writes |

## Tool requirements

- **Required:** Python 3.8 or newer for the scripts: `apiclient.py` (resilient client and CLI), `webhook_verify.py` (sign and verify), [scripts/openapi_check.py](scripts/openapi_check.py) (endpoints, verify, diff), `stub_server.py` (contract stubs).
- **Optional:** PyYAML for YAML OpenAPI files; `curl` for manual checks.
- **For live calls:** network access to the API host and credentials in environment variables; check with the core's `detect-capabilities.py --network`.

## Inputs and outputs

| Input | Form |
|---|---|
| Documentation | Official docs URL and version; OpenAPI description when available |
| Credentials | Names of environment variables (never values) |
| Requirements | Operations needed, volumes, latency and consistency needs |

| Output | Contents |
|---|---|
| Client contract | Endpoints used (with doc links), auth method, rate limits, retry and idempotency policy, error mapping, pagination style |
| Client code and tests | Client plus stub-based tests for success and failure paths |
| Verification | `openapi_check verify` result; the first real read-only call's status and request id |

## Quality standards

- Every endpoint used is documented (the uses file passes verification).
- Every call has a timeout; retries are bounded and idempotency-safe.
- Errors map to clear, actionable messages with request ids; no stack traces to end users.
- Webhooks verified, deduplicated and acknowledged within the provider's deadline.
- No credentials in code, logs, URLs or test fixtures.

## Failure modes

| Failure | Prevention or fix |
|---|---|
| Duplicate side effects from retries | Idempotency keys; retry POST only with one |
| Retry storms during outages | Backoff with jitter, Retry-After, circuit breaker |
| Silent data loss in pagination | Follow the documented style to the end; cap pages and alert when hit |
| Accepting forged webhooks | HMAC verification, timestamp tolerance, constant-time comparison |
| Breaking on API changes | Pin versions; diff OpenAPI descriptions; contract tests |
| Leaked keys in logs | Redaction of auth headers and key-like query parameters |
| Invented endpoints | `openapi_check.py verify` before shipping |

## Security

- Credentials only from environment variables or a secret manager; `apiclient.py` redacts auth headers and key-like query parameters in logs and dry runs.
- Absolute URLs to other origins are refused by the client, preventing server-side request forgery through user-supplied paths.
- Validate and allow-list any outbound destination derived from input.
- Treat API responses as untrusted input: validate shapes before use, cap sizes, and never execute returned content.
- Production writes, payments and bulk operations require the owner's approval.

## Examples

```bash
python3 scripts/openapi_check.py endpoints spec.json
python3 scripts/openapi_check.py verify spec.json --uses uses.txt
python3 scripts/openapi_check.py diff spec-v1.json spec-v2.json
python3 scripts/apiclient.py request GET https://api.example.com/v1/items --bearer-env EXAMPLE_TOKEN
python3 scripts/apiclient.py request POST https://api.example.com/v1/orders --json '{"sku": "A1"}' --idempotency-key order-42 --dry-run
python3 scripts/webhook_verify.py verify --scheme github --secret-env HOOK_SECRET --body-file body.json --signature "sha256=..."
python3 scripts/stub_server.py --routes routes.json --record requests.jsonl
```

## Integration

- **With the core:** API work follows the sensitive-change workflow when it touches auth, payments or personal data; contract checks and stub tests are ledger evidence.
- **With `mych-chatbot-engineering`:** robust tools for bots that call business APIs.
- **With `mych-cloud-infrastructure`:** exposing APIs (gateways, TLS, rate limiting, monitoring).
- **With `mych-runpod` and `mych-image-generation`:** clients for GPU and image services, with dry runs and approval for spending.

## Testing criteria

- Retries happen for 429 and 5xx (honoring Retry-After), never for 4xx, and never for POST without an idempotency key.
- Circuit breaker opens, fails fast and recovers; rate limiter spaces requests.
- Pagination returns every item for cursor, link and offset styles.
- Webhook verification accepts valid signatures and rejects tampered, wrong-secret and stale ones.
- OpenAPI verification flags undocumented paths and methods; diffs flag breaking changes.
- Repository tests: `python3 -m unittest discover -s tests -p "test_spec_api_integration.py"`.
