# Webhooks

Receiving events from other systems safely and exactly once in effect.

## Verification

1. Read the **raw request body** before any parsing; signatures cover exact bytes.
2. Compute the HMAC-SHA256 the provider documents and compare with **constant-time** comparison (`hmac.compare_digest`).
3. Reject timestamps outside a tolerance window (commonly five minutes) to stop replays.
4. Reject requests without signatures when the provider supports them.

`webhook_verify.py` implements three common schemes:

| Scheme | Header and signed content |
|---|---|
| `timestamped` | `t=TIMESTAMP,v1=HEX` over `{timestamp}.{body}` (used by several payment providers) |
| `slack` | `X-Slack-Signature: v0=HEX` over `v0:{timestamp}:{body}`, with `X-Slack-Request-Timestamp` |
| `github` | `X-Hub-Signature-256: sha256=HEX` over the body |

Always confirm the exact scheme in the provider's documentation; header names and signed strings differ.

## Processing

- **Acknowledge fast** (HTTP 2xx within the provider's deadline), then process asynchronously from a queue.
- **Deduplicate** by the provider's event id; deliveries are at least once and can arrive out of order.
- **Re-fetch** the resource from the API when ordering or completeness matters, instead of trusting the event payload alone.
- Return non-2xx only when you want a retry.

## Operations

- Log event ids and outcomes (not secrets or full personal data).
- Monitor delivery failures and backlog.
- Rotate signing secrets with an overlap period: accept both old and new signatures during rotation.
