# Authentication and Authorization

Choosing and implementing API authentication safely.

## Options

| Method | Use when | Notes |
|---|---|---|
| API key in a header | Server-to-server with simple scopes | Store in a secret manager; rotate; never put keys in URLs |
| OAuth 2.0 authorization code with PKCE | An app acts for a user | Request minimal scopes; store refresh tokens encrypted |
| OAuth 2.0 client credentials | A service acts for itself | Cache tokens until shortly before expiry |
| Basic auth over TLS | Legacy APIs | Treat the password like an API key |
| Mutual TLS | High-assurance service links | Certificate lifecycle management needed |

## Tokens

- Refresh access tokens before expiry; on 401, refresh once and retry once, then fail.
- Validate JWTs you receive: signature with the issuer's published keys, `iss`, `aud`, `exp` and `nbf`, and the expected algorithm only (never accept `none`).
- Do not decode a JWT and trust its claims without verifying the signature.

## Storage and handling

- Read credentials from environment variables or a secret manager (`apiclient.BearerEnv`, `HeaderKeyEnv`, `BasicEnv`).
- Redact credentials in logs, errors and dry runs (the client does this for common header names and key-like query parameters).
- Scope credentials to the minimum permissions and environments needed; separate sandbox and production keys.
- If a key leaks: revoke and rotate it, check access logs, and remove it from history; deleting it from the latest commit is not enough.

## Authorization in your own APIs

Check authorization on the server for every request and every object (deny by default). Never trust user ids or roles sent by the client.
