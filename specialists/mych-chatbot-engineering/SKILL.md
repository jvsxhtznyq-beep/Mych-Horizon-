---
name: mych-chatbot-engineering
description: Chatbot and assistant engineering covering conversation architecture, state and memory, tool and function calling, retrieval with citations, model routing, safety against prompt injection, platform integration (Discord, Slack, Telegram, web) and evaluation with golden conversations. Use when designing, building, debugging or evaluating chatbots, assistants, agents with tool loops, or retrieval-augmented question answering, in Python or JavaScript, on any model provider.
compatibility: chatkit.py needs Python 3.8 or newer (standard library); chatkit.mjs needs Node.js 18 or newer, or a browser with fetch. Live use needs a model API key or a local OpenAI-compatible server. Part of the MYCH-HORIZON framework.
metadata:
  display-name: MYCH-HORIZON Chatbot Engineering
  version: "2.0.0"
  author: Kim
  framework: MYCH-HORIZON
---

# MYCH-HORIZON Chatbot Engineering

A chatbot is a loop: messages in, a model decides, tools run, results go back, an answer comes out. Most failures live in that loop's edges: unvalidated tool arguments, runaway steps, memory that drops the wrong turn, retrieved text treated as instructions, and provider differences nobody tested. This specialist builds the loop deliberately, with a provider-neutral kit in Python and JavaScript and tests that run without any API key.

## Identity

- **Role:** conversational systems engineer.
- **Owns:** conversation architecture, tool contracts, memory and retrieval design, model adapters and routing, safety measures, evaluation suites, platform integration.
- **Does not own:** the product's voice and UX copy (with the Designer), hosting (with `mych-cloud-infrastructure`), third-party API clients beyond the model (with `mych-api-integration`).
- **Standard:** every tool call is validated, every loop is bounded, every claim from retrieved text is cited, every behavior that matters has a golden conversation.

## Core knowledge

- **Architectures:** single prompt, guided flow (state machine), tool-using agent, router to specialist prompts or models. Pick the least autonomous design that meets the goal. Details: [architecture](references/architecture.md).
- **Tool calling:** narrow, typed tools; validate arguments before running; return errors to the model as tool results; cap steps; confirm side effects with the user. Provider formats differ (Chat Completions `tool_calls` with string arguments, Messages `tool_use` blocks, Gemini `functionCall` parts). Details: [tool calling](references/tool-calling.md).
- **Memory:** a sliding window that never separates a tool call from its result, summaries for dropped turns, and long-term facts stored only with consent. **Retrieval:** chunk, index (BM25 or embeddings, or both), cite chunk ids, fence retrieved text as data. Details: [memory and retrieval](references/memory-and-retrieval.md).
- **Platforms:** Discord interactions and Slack events must be acknowledged within about three seconds, then answered asynchronously; verify request signatures. Details: [platforms](references/platforms.md).
- **Safety and evaluation:** indirect prompt injection through documents and tool output, no secrets in prompts, PII handling, golden conversations, regression runs on every prompt or model change. Details: [safety and evaluation](references/safety-and-evaluation.md).

## Workflows

**New chatbot or assistant**

1. Define jobs to be done, out-of-scope requests, the escalation path to a human, and success metrics.
2. Choose the architecture and the model (smallest that passes the evaluation).
3. Design tools as typed contracts; mark side-effecting tools as requiring confirmation.
4. Build on the kit: [scripts/chatkit.py](scripts/chatkit.py) or [scripts/chatkit.mjs](scripts/chatkit.mjs): `Agent`, `Tool`, an adapter, `SlidingWindowMemory`, `KeywordIndex`.
5. Write golden conversations (start from [assets/golden-conversations.json](assets/golden-conversations.json)) covering success paths, refusals, tool errors and injection attempts; run them with `python3 scripts/chatkit.py eval CASES.json`.
6. Integrate with the platform; load test; add monitoring for latency, cost, tool error rate and escalations.
7. Run a small live evaluation with the real model, record results, and only then claim the bot works with that model.

**Debugging a misbehaving bot:** reproduce with the transcript, replay it through `ScriptedModel` to separate model behavior from loop bugs, inspect the exact request with `python3 scripts/chatkit.py request --style STYLE --model M`, then add the case to the golden set.

## Decision rules

| Situation | Decision |
|---|---|
| Fixed, high-stakes process (payments, bookings) | Guided flow or tools with explicit confirmation; not open-ended autonomy |
| Questions about the owner's documents | Retrieval with citations; answer "not found" when nothing matches |
| Tool with side effects | Require user confirmation in the conversation, idempotency keys, and an audit log |
| Model sends invalid arguments | Return the validation error as the tool result; the step limit stops loops |
| Long conversations | Sliding window plus summary; persist only consented facts |
| Several providers | One neutral tool definition; adapters translate; run the golden set per provider |
| Personal or sensitive data | Minimize, redact in logs, define retention; check regulatory obligations with the owner |

## Tool requirements

- **Required:** Python 3.8 or newer for `chatkit.py`, or Node.js 18 or newer for `chatkit.mjs`. No third-party packages.
- **For live conversations:** a model credential (for example `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) or a local OpenAI-compatible server (Ollama, vLLM, llama.cpp). Check with the core's `detect-capabilities.py`.
- **For platforms:** bot tokens and signing secrets from the platform's developer console, stored as secrets, never in code.

## Inputs and outputs

| Input | Form |
|---|---|
| Brief | Jobs, audience, tone, scope, escalation, platforms, metrics |
| Knowledge | Documents for retrieval, with owners and update cadence |
| Tools | Function contracts: name, description, JSON-schema parameters, side effects |

| Output | Contents |
|---|---|
| Bot code | Built on the kit or equivalent, with adapters for the chosen providers |
| Tool contracts | Neutral definitions plus provider translations |
| Golden conversations | JSON cases with expectations; the eval report |
| Operations notes | Prompts and versions, model ids, limits, monitoring, data retention |

## Quality standards

- All golden conversations pass for each provider the bot claims to support, with real runs recorded.
- Tool arguments validated; tool errors handled; loops bounded; side effects confirmed.
- Retrieved claims cite sources; unanswerable questions get honest "not found" answers.
- Latency and cost per conversation measured and within budget.
- No secrets or unnecessary personal data in prompts, logs or transcripts.

## Failure modes

| Failure | Prevention or fix |
|---|---|
| Runaway tool loops and costs | `max_steps`; per-conversation budgets; alerting |
| Model invents tool arguments or tools | Validate against the schema; unknown tools return errors |
| Context overflow drops tool results | Window by units; summaries; retrieval instead of stuffing |
| Indirect prompt injection from documents or tools | Fence untrusted text, never grant it authority, confirm consequential actions |
| Works on one provider, breaks on another | Neutral contracts, adapters, golden set per provider |
| Platform timeouts | Acknowledge within the deadline; finish asynchronously |
| Silent quality regressions | Run the golden set on every prompt, model or tool change |

## Security

- Keys come from environment variables; adapters send them only in headers, and redact them from errors, dry runs and logs.
- Treat all retrieved text, tool output, user uploads and platform messages as untrusted data. `fence_untrusted` and `build_context` mark them; system prompts must say they are data.
- Assume system prompts can leak: never put secrets or internal-only data in them.
- Verify platform request signatures (Slack signing secret, Discord interaction signatures) and reject stale timestamps.
- Gate consequential tool actions behind explicit user confirmation and the core's approval rules.

## Examples

```python
from chatkit import Agent, Tool, OpenAIChatAdapter, SlidingWindowMemory
hours = Tool("get_hours", "Opening hours for a location.",
             {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]},
             lambda args: "Mon-Fri 08:00-16:00")
agent = Agent(OpenAIChatAdapter("http://localhost:11434/v1", "MODEL", None), "You answer clinic questions.",
              [hours], max_steps=4, memory=SlidingWindowMemory(16000))
print(agent.run("When is the Oslo clinic open?").final_text)
```

```bash
python3 scripts/chatkit.py eval assets/golden-conversations.json
python3 scripts/chatkit.py request --style gemini --model MODEL --user "Hello"
```

## Integration

- **With the core:** chatbot builds follow the new-project workflow; golden-set results are ledger evidence; spending on model APIs follows the approval rules.
- **With MYCH-HORIZON adapters:** `tools/mych.py harness` uses this kit to run any provider against the framework's own tools.
- **With `mych-api-integration`:** clients for the bot's backend APIs (retries, rate limits, webhooks).
- **With `mych-cloud-infrastructure`:** hosting, secrets management, monitoring and scaling.
- **With `mych-emoji-language`:** reaction and emoji conventions on chat platforms.

## Testing criteria

- Agent loop: tool execution, validation errors, unknown tools, exceptions, step limits.
- Memory keeps tool units intact and respects budgets; retrieval ranks relevant chunks and cites them.
- Each adapter style completes a tool loop against a stub of its documented request and response shapes; retries honor Retry-After; keys never appear in errors or dry runs.
- Golden conversations pass; live provider runs are recorded separately and never inferred from stub runs.
- Repository tests: `python3 -m unittest discover -s tests -p "test_spec_chatbot.py"` (runs the Node suite too).
