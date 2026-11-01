# Adapter: GPT

**Evidence:** Codex skill paths **documented** in OpenAI's Codex documentation (retrieved 2026-11-01). The Chat Completions adapter in `chatkit.py` is **stub-tested** only. **No GPT model has run MYCH-HORIZON in this repository**: behavior with the framework is untested.

## Loading MYCH-HORIZON

- **Codex:** repository skills live in `.agents/skills/`; Codex scans that folder in each directory from the working directory up to the repository root (source: <https://developers.openai.com/codex/skills>). Install with `python3 tools/mych.py export --host codex --project .`, which rewrites `${CLAUDE_SKILL_DIR}` to `.agents/skills/<skill>`. User-level locations are listed in the Codex documentation; check it before installing outside a repository.
- **API or ChatGPT without skills:** use a bundle: `python3 tools/mych.py bundle --provider openai --task "..."`.

## How each capability is reached

| Capability | How |
|---|---|
| System instructions | A `system` (or `developer`) message at the start of `messages` |
| Tool definitions | `tools: [{"type": "function", "function": {name, description, parameters}}]` |
| Tool calls | `message.tool_calls[]` with `id` and `function.name`; `function.arguments` is a JSON **string** to parse and validate |
| Tool results | `{"role": "tool", "tool_call_id", "content"}` messages |
| Structured output | JSON schema response formats on models that support them; tool calls as the portable fallback |
| Multimodal input | Text and images (per model) |
| File access | Only through the host's tools (Codex provides workspace access; the bare API does not) |
| Orchestration | Depends on the host; follow [delegation.md](../mych-plugin/systems/delegation.md) |
| Context window | Varies by model; read the current model documentation |

## Notes

- Arguments arrive as a string: parse it, validate it against the tool schema, and return a tool error message (not a crash) when it is malformed. `chatkit.py` does this.
- Several tool calls can arrive in one assistant message; answer each `tool_call_id`.
- Source: <https://platform.openai.com/docs/guides/function-calling> (format as documented; not re-checked against a live API here).
