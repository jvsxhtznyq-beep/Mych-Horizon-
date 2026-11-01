# Adapter: open-weight and local models

**Evidence:** Ollama's OpenAI-compatible endpoint with tool support is **documented** by Ollama (retrieved 2026-11-01). The adapter in `chatkit.py` is **stub-tested** only. No local runtime is installed in this repository's test environment, so **no open-weight model has run MYCH-HORIZON**.

## Loading MYCH-HORIZON

- Local models have no native skill loading. Use the harness (`python3 tools/mych.py harness --provider ollama --model MODEL --task "..."`) or a bundle with a host that can talk to the local server.
- Choose a model that supports tool calling; support depends on the model, not only on the server.

## Servers

| Server | Endpoint | Notes |
|---|---|---|
| Ollama | `http://localhost:11434/v1/chat/completions` | Tools supported on the OpenAI-compatible endpoint for models that support them; the API key value is ignored |
| vLLM | `{base_url}/v1/chat/completions` | OpenAI-compatible server; tool parsing depends on server flags and the model's template |
| llama.cpp server | `{base_url}/v1/chat/completions` | OpenAI-compatible; tool support depends on the build and template |
| LM Studio and gateways | `{base_url}/v1/chat/completions` | Use `--provider openai-compatible --base-url URL` |

## How each capability is reached

| Capability | How |
|---|---|
| System instructions | `system` message |
| Tool definitions, calls and results | OpenAI-compatible; keep schemas flat (the portable subset avoids `anyOf` and `$ref`, which some servers are reported to ignore) |
| Structured output | JSON mode where offered; always validate |
| Context window | Set by the model and the server configuration (for example a context-length option); bundles for small windows should inline only the routed workflow |
| Multimodal input | Vision models only |
| File access and orchestration | Through the harness or host |

## Fitting small context windows

Use the [context budget guidance](../mych-plugin/systems/model-portability.md#context-budgets): bundle with `--max-tokens` set below the model's window, include only the routed workflow, and prefer a single specialist. The core `SKILL.md` plus the core tool definitions come to about 6,000 tokens by the bundle's estimate (characters divided by four).

## Sources

- <https://docs.ollama.com/api/openai-compatibility>
- <https://registry.ollama.ai/blog/tool-support>
