# Model Compatibility Matrix

What is known about running MYCH-HORIZON on each model family and agent host, and how it is known. Retrieved and checked on 2026-11-01 to 2026-11-06. Evidence levels follow [registry/providers.json](../registry/providers.json):

- **executed**: ran in this repository's environment with recorded output;
- **stub-tested**: our adapter code ran against a local imitation of the documented format, never against the real service;
- **documented**: stated in the vendor's documentation;
- **secondary**: stated only by third parties;
- **unknown**: no evidence.

**Bottom line:** MYCH-HORIZON has been executed only with Claude inside Claude Code. Every other family is untested with the framework: the adapters exist and pass stub tests, but no GPT, Gemini, GLM or open-weight model has run the framework or its benchmarks here, because the test environment has no API keys or local model runtime (ledger task X1, blocked).

## Model families

| Capability | Claude | GPT | Gemini | GLM | Open-weight (Ollama, vLLM, llama.cpp) |
|---|---|---|---|---|---|
| System instructions | Top-level `system` (documented) | System or developer message (documented) | `systemInstruction` (documented) | System message (secondary) | System message (documented for Ollama) |
| Tool definition format | `input_schema` (documented) | `function.parameters` (documented) | `functionDeclarations` (documented) | OpenAI-compatible (secondary) | OpenAI-compatible (documented for Ollama) |
| Tool call and result encoding in `chatkit.py` | stub-tested | stub-tested | stub-tested | stub-tested (OpenAI style) | stub-tested (OpenAI style) |
| Structured output | Tool schemas (documented) | JSON schema formats on supported models (documented) | Response schema on supported models (documented) | Unverified | JSON mode, model-dependent (documented for Ollama) |
| Multimodal input | Text, images, PDFs per model (documented) | Text, images per model (documented) | Text, images, audio, video, PDFs per model (documented) | Vision models (secondary) | Vision models only (documented for Ollama) |
| Context window | Varies by model; check current docs | Varies; check current docs | Varies; check current docs | Varies; check vendor docs | Set by model and server configuration |
| Loads MYCH-HORIZON skills natively | Yes, in Claude Code (**executed**) | In Codex (documented) | In Gemini CLI (documented) | No native loader found | No (use the harness or a host) |
| Framework behavior with this model | **executed** (this repository was built and evaluated with it) | unknown | unknown | unknown | unknown |
| Bundle produced for this provider | Yes (tested offline) | Yes (tested offline) | Yes (tested offline) | Yes (tested offline) | Yes (tested offline) |

## Agent hosts

| Host | Project skill paths | User skill paths | Expands `${CLAUDE_SKILL_DIR}` | Evidence | Source |
|---|---|---|---|---|---|
| Claude Code | `.claude/skills` | `~/.claude/skills` | Yes | **executed** (skill installed and invoked; substitution observed) | docs.anthropic.com |
| OpenAI Codex | `.agents/skills` (scanned from the working directory up to the repository root) | See vendor docs | No (export rewrites it) | documented | developers.openai.com/codex/skills |
| Gemini CLI | `.gemini/skills`, `.agents/skills` | See vendor docs | No (export rewrites it) | documented | geminicli.com/docs/cli/skills |
| GitHub Copilot (cloud agent, CLI, VS Code agent mode) | `.github/skills`, `.claude/skills`, `.agents/skills` | `~/.copilot/skills`, `~/.claude/skills`, `~/.agents/skills` | No (export rewrites it) | documented | docs.github.com (create skills) |
| Cursor | `.agents/skills` (unconfirmed) | Unconfirmed | No | secondary | third-party articles |

`.agents/skills` is the most portable project location found: Codex, Gemini CLI and Copilot all document it.

## How to move a cell from unknown to executed

1. Provide a key for the provider (or start a local server) in an environment you control.
2. Run the harness with a real task and record the transcript:

   ```bash
   python3 tools/mych.py harness --provider openai --model MODEL --task "Plan and verify a small change in this repository" --workspace .
   ```

3. Run the chatbot kit's golden conversations through a live adapter, and repeat a benchmark task (for example rebuilding a cavern for Glowmoss Caverns) with that model.
4. Record the date, model id, results and transcripts under `evaluation/`, then update this matrix and `registry/providers.json`. A model passes only the cases it actually passed.
