# Provider adapters

The MYCH-HORIZON core and specialists define **what** to do: orientation, routing, the lifecycle, the ledger, verification and approval rules. An adapter defines **how** that reaches one model family: how instructions are passed, how tools are declared and called, how results come back, and which capabilities to expect. Nothing in the framework is duplicated per model; adapters are data plus short notes.

| Adapter | Families | Loading MYCH-HORIZON | Evidence |
|---|---|---|---|
| [claude.md](claude.md) | Claude | Native skills (Claude Code and other Anthropic surfaces) or bundle | Skill loading **executed**; API adapter stub-tested |
| [gpt.md](gpt.md) | GPT | Native skills in Codex; bundle elsewhere | Skill paths **documented**; API adapter stub-tested; model behavior **not tested** |
| [gemini.md](gemini.md) | Gemini | Native skills in Gemini CLI; bundle elsewhere | Skill paths **documented**; API adapter stub-tested; model behavior **not tested** |
| [glm.md](glm.md) | GLM | Bundle or a host that reads skills | Endpoint from secondary sources; API adapter stub-tested; model behavior **not tested** |
| [open-weight-local.md](open-weight-local.md) | Llama, Qwen, Mistral and other open-weight models via Ollama, vLLM, llama.cpp | Bundle with the harness or a host | API shape **documented** for Ollama; adapter stub-tested; model behavior **not tested** |

Evidence levels are defined in [registry/providers.json](../registry/providers.json). Only Claude, inside Claude Code, has been executed with MYCH-HORIZON so far. The other families are untested: a skill that works in Claude is not assumed to work in GPT, Gemini or GLM.

## Three ways to load the framework

1. **Native skill loading.** Hosts that read `SKILL.md` folders (Claude Code, Codex, Gemini CLI, GitHub Copilot) load the core and specialists on demand. Install with `python3 tools/mych.py export --host HOST --project DIR`. Only Claude Code expands `${CLAUDE_SKILL_DIR}`; for other hosts the export rewrites it to the installed path.
2. **Bundle.** For a model reached through an API or a chat window, `python3 tools/mych.py bundle --provider ID --task "..."` writes `system-prompt.md` (the core plus the routed workflow and specialists, inlined), `tools.json` in that provider's tool format, and `manifest.json` with an approximate token count. The bundle refuses to exceed `--max-tokens`.
3. **Harness.** `python3 tools/mych.py harness --provider ID --model MODEL --task "..."` runs an agent loop: it sends the bundle, executes the model's tool calls with `run-tool` (argument lists, no shell, confined to `--workspace`), and returns the transcript summary. `--dry-run` builds the first request and sends nothing. The harness has run only against local stubs in this repository.

## Tool translation

The neutral definitions in [registry/tools.json](../registry/tools.json) (and each specialist's `tools` in [registry/specialists.json](../registry/specialists.json)) use a portable JSON Schema subset: `type`, `description`, `enum`, `properties`, `required`, `items`, and numeric or length bounds. `tools/mych.py tools-schema --format FORMAT` emits:

| Format | Shape |
|---|---|
| `openai` and `openai-compatible` | `{"type": "function", "function": {"name", "description", "parameters"}}` |
| `anthropic` | `{"name", "description", "input_schema"}` |
| `gemini` | `[{"functionDeclarations": [{"name", "description", "parameters"}]}]`, with non-portable keywords removed |

Tool names are lowercase `snake_case` of at most 64 characters, which every format above accepts.

## Capability differences the core already handles

The core's [model-portability guide](../mych-plugin/systems/model-portability.md) plans in capabilities (read files, run commands, call tools, structured output, vision, workers) and gives a fallback for each missing one. Adapters only record which capabilities a family offers and how to reach them; they never change the rules for evidence, approval or reporting.

## Adding an adapter

1. Add the provider to `registry/providers.json` with endpoint, auth, tool format, evidence levels and sources.
2. If its API style is new, add a model adapter class to the chatbot specialist's `chatkit.py` (Python) and test it against a stub of the documented request and response shapes.
3. Write `adapters/<family>.md` with the sections used by the existing adapters.
4. Run `python3 tools/mych.py registry-check` and the test suite. Mark model behavior as untested until a real run with recorded evidence exists.
