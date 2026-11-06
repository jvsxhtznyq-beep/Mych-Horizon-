# Conversation Architecture

Choosing how much autonomy a conversational system gets, and structuring the loop so it stays reliable.

## Architectures

| Architecture | How it works | Use when | Risks |
|---|---|---|---|
| Single prompt | One model call per user turn, no tools | FAQ-style answers from model knowledge, drafting | Hallucination; no access to live data |
| Guided flow (state machine) | Code drives the steps; the model fills slots and phrases replies | Bookings, payments, onboarding: fixed, auditable processes | Rigid; needs good fallbacks |
| Tool-using agent | The model chooses tools in a loop until it answers | Open-ended tasks over live data or actions | Runaway loops, wrong actions, cost; needs limits and confirmations |
| Router | A cheap classifier or model routes to specialist prompts, flows or models | Distinct domains, cost control | Misroutes; evaluate the router separately |
| Retrieval-augmented | Retrieve relevant chunks, answer with citations | Questions over the owner's documents | Stale or missing documents; injection through content |

Prefer the least autonomous architecture that meets the goal, and combine them: a router into guided flows, with retrieval for questions.

## The loop

1. Receive the user turn; authenticate the user and load their conversation state.
2. Build the context: system prompt, memory window, retrieved material (fenced as data), tool definitions.
3. Call the model; parse text and tool calls.
4. Validate and execute tool calls; return results (or errors) as tool messages.
5. Repeat until the model answers or the step limit is reached.
6. Post-process: safety checks, formatting for the platform, logging (redacted).

## Design rules

- Make tools idempotent or require idempotency keys for side effects; retries happen.
- Stream long answers to reduce perceived latency; send a typing indicator where the platform supports it.
- Keep conversation state outside the process (database or cache) so servers can scale and restart.
- Version prompts and tools like code; log which versions served each conversation.
- Design the human handoff: when to offer it, how context transfers, and what the user sees.
