# Contracts and Testing

Keeping integrations honest: documented endpoints only, tests that do not touch production, and early warning of breaking changes.

## The contract

- The provider's OpenAPI description (or documentation) is the contract. Record its version and retrieval date.
- Keep a **uses file** listing every `METHOD /path` the client calls, and verify it in CI:

```bash
python3 scripts/openapi_check.py verify spec.json --uses uses.txt
```

- When the provider publishes a new description, diff it:

```bash
python3 scripts/openapi_check.py diff spec-old.json spec-new.json
```

Breaking changes (removed operations, new required parameters, request bodies becoming required, removed responses) fail the check.

## Stub-based tests

`stub_server.py` serves scripted responses per route (sequences repeat their last entry) and records requests:

```json
{"routes": [
  {"method": "GET", "path": "/v1/items", "responses": [
    {"status": 429, "headers": {"Retry-After": "1"}, "json": {"error": "slow down"}},
    {"status": 200, "json": {"data": [{"id": 1}], "next_cursor": null}}]}]}
```

Cover: success, validation errors, auth failures, 404, 409, 429 with Retry-After, 5xx then success, timeouts, malformed JSON, empty pages, very large pages.

## Real calls

- Use the provider's sandbox or test mode with test credentials.
- Start with one read-only call; record status, request id and date as evidence.
- Writes to production, payments and bulk operations need the owner's approval.

## Reporting

State which endpoints were verified against the description, which tests ran against stubs, and which real calls were made (environment, date, request ids). Stub tests prove client behavior, not the provider's behavior.
