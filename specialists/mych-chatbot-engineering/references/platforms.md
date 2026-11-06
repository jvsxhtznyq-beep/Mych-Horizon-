# Platform Integration

Connecting a bot to chat platforms and the web. Platform rules change: confirm limits and requirements in each platform's current developer documentation.

## Discord

- **Interactions** (slash commands, buttons): Discord expects an initial response within about three seconds. Respond immediately or defer, then send follow-up messages when the model finishes.
- **Gateway intents:** reading ordinary message content requires the message content intent, which is privileged and must be enabled for the application; prefer slash commands where possible.
- **Verification:** interaction webhooks are signed; verify signatures with the application's public key before processing.
- Respect rate limits returned in response headers; queue outgoing messages.

## Slack

- **Events API and interactivity:** acknowledge requests within about three seconds (HTTP 200), then do the work asynchronously and reply via the Web API or response URLs.
- **Request signing:** verify `X-Slack-Signature` (an HMAC-SHA256 over `v0:{timestamp}:{body}` with the signing secret) and reject old timestamps to prevent replays.
- **Socket Mode** avoids exposing a public endpoint, useful for internal bots.

## Telegram

- Choose webhooks (public HTTPS endpoint) or long polling (simpler, no public endpoint).
- Keep the bot token secret; it grants full control of the bot.

## Web chat

- Stream responses (server-sent events or WebSockets) to show progress.
- Authenticate users; never accept a user identity from the client without verification.
- Configure CORS narrowly; rate-limit per user and per IP.
- Render model output safely: escape HTML, or sanitize Markdown rendering, to prevent script injection.

## Common requirements

- Store tokens and signing secrets in a secret manager or environment variables.
- Make handlers idempotent: platforms retry deliveries.
- Log platform message ids with conversation ids for tracing.
