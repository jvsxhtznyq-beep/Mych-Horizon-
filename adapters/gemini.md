# Adapter: Gemini

**Evidence:** Gemini CLI skill paths **documented** (retrieved 2026-11-01). The `generateContent` adapter in `chatkit.py` is **stub-tested** only. **No Gemini model has run MYCH-HORIZON in this repository**: behavior with the framework is untested.

## Loading MYCH-HORIZON

- **Gemini CLI:** workspace skills live in `.gemini/skills/`, with `.agents/skills/` accepted as an alternative; user and extension skills also exist (sources: <https://geminicli.com/docs/cli/skills/>, <https://geminicli.com/docs/cli/creating-skills/>). Install with `python3 tools/mych.py export --host gemini-cli --project .`. Project instructions belong in `GEMINI.md`, which the core's project-memory system already reads.
- **API without skills:** `python3 tools/mych.py bundle --provider gemini --task "..."`.

## How each capability is reached

| Capability | How |
|---|---|
| System instructions | `systemInstruction: {parts: [{text}]}`, separate from `contents` |
| Tool definitions | `tools: [{functionDeclarations: [{name, description, parameters}]}]` |
| Tool calls | A candidate content part `{"functionCall": {"name", "args"}}`; Gemini 3 models also return an `id` |
| Tool results | A content with role `user` holding `{"functionResponse": {"name", "response", "id"}}`; echo the call's `id` when one was given |
| Structured output | Response schema with a JSON MIME type on supported models; tool calls as the portable fallback |
| Multimodal input | Text, images, audio, video and PDFs (per model) |
| File access | Only through the host's tools (Gemini CLI provides them) |
| Orchestration | Depends on the host |
| Context window | Varies by model; read the current model documentation |

## Notes

- Parameter schemas use an OpenAPI-style subset. The bundle keeps only portable keywords and drops the rest (for example `additionalProperties` and `default`).
- Append the model's full returned content (including any thought signatures on newer models) to the history before the function response, as Google's examples do.
- Request header: `x-goog-api-key`. Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.
- Source: <https://ai.google.dev/gemini-api/docs/function-calling> (reached through search results and mirrors; not re-checked against a live API here).
