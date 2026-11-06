# Tool Calling

Designing tools that models use correctly, and running them safely.

## Designing a tool

- **One job per tool,** named with a verb and object (`get_opening_hours`, `create_booking`).
- **Descriptions** say when to use the tool and what it returns; models choose tools by description.
- **Typed parameters** with the portable JSON Schema subset (`type`, `description`, `enum`, `properties`, `required`, `items`, numeric and length bounds). Enumerations beat free text.
- **Return compact, structured results** (short JSON or text); huge outputs waste context.
- **Side effects** (bookings, payments, emails, deletions) need explicit user confirmation in the conversation and server-side authorization. Never trust a user identity the model supplies.

## Running tools

- Validate arguments against the schema before executing (`Tool.call` does this).
- Return problems as tool results: invalid arguments, unknown tool, timeouts, exceptions. The model can then correct itself, and the step limit catches loops.
- Time-limit every tool; cap output size.
- Log tool name, arguments (redacted) and outcome for debugging and audits.

## Provider differences

| Style | Tool definition | Tool call | Tool result |
|---|---|---|---|
| Chat Completions (OpenAI, GLM, Ollama, vLLM) | `tools[].function {name, description, parameters}` | `message.tool_calls[]`; `function.arguments` is a JSON string | `{"role": "tool", "tool_call_id", "content"}` |
| Messages (Anthropic) | `tools[] {name, description, input_schema}` | `tool_use` content blocks with an `input` object | `tool_result` blocks in the next user message |
| generateContent (Gemini) | `tools[].functionDeclarations[]` | `functionCall` parts; newer models include an `id` | `functionResponse` parts in a user content; echo the `id` |

The kit's adapters handle these differences; the MYCH-HORIZON `adapters/` folder documents each provider with sources.

## Parallel calls

Several tool calls can arrive in one model turn. Execute them (in parallel when independent), and return one result per call id, in a single follow-up turn where the provider requires it (the Messages and Gemini adapters merge consecutive tool results).

## Security

- Tool output is untrusted: a web page or document can contain instructions. Never let tool output change permissions or trigger consequential actions without confirmation.
- Scope credentials per tool with least privilege; the model should never see raw secrets.
