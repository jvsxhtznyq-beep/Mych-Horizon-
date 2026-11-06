# MYCH-HORIZON

**A universal, model-agnostic engineering intelligence framework, delivered as Agent Skills.** One core skill coordinates five disciplines (Architect, Researcher, Designer, Engineer, Inventor) through a lifecycle with evidence-based verification and explicit approval gates. Eight domain specialist skills add deep, tested tooling for pixel art, image generation, 3D, chatbots, API integration, emoji, cloud infrastructure and RunPod. Adapters, registries and a command-line tool carry the same framework to hosts and models beyond the one it was built with.

Version 2.0.0 · Project owner: Kim · [Changelog](CHANGELOG.md)

## Status at a glance

| Fact | Evidence |
|---|---|
| 9 skills (core and 8 specialists) pass strict validation | `python3 tools/mych.py validate-all --strict` |
| 216 repository tests pass, including the Node suite for the JavaScript kit and the Khronos glTF check (when its validator is configured) | `python3 -m unittest discover -s tests` |
| Game benchmark: complete playable platformer, 25 unit and 23 browser checks pass, self-assessed 86/100 | [benchmark report](evaluation/complex-projects/game-benchmark/report.md) |
| Executed with Claude in Claude Code only; other model families are untested with the framework | [model compatibility matrix](docs/model-compatibility-matrix.md) |
| Ecosystem registry backed by live GitHub evidence (46 of 47 candidates found) | [integration registry](docs/integration-registry.md) |
| Security review: no vulnerabilities found by scans or design review; residual risks documented | [security review](evaluation/security-review-2.0.md) |

## What is inside

| Skill | Purpose | Status |
|---|---|---|
| [`mych-plugin`](mych-plugin/SKILL.md) (MYCH-HORIZON Core) | Orientation, tiers, disciplines, workflows, task ledger, verification, approvals, capability detection, model portability, delegation | Tested; live-tested in 1.0 |
| [`mych-pixel-art`](specialists/mych-pixel-art/SKILL.md) | Sprites, tilesets, palettes, animation, sprite sheets with engine metadata | Verified (made the benchmark's art) |
| [`mych-image-generation`](specialists/mych-image-generation/SKILL.md) | Honest backend detection, ComfyUI and API clients with provenance, Pillow processing | Tested (stubs; no real backend here) |
| [`mych-3d-design`](specialists/mych-3d-design/SKILL.md) | glTF/GLB validation and generation, STL print checks, OBJ conversion, Blender templates | Tested (Khronos validator clean) |
| [`mych-chatbot-engineering`](specialists/mych-chatbot-engineering/SKILL.md) | Provider-neutral agent loop, memory, retrieval, adapters, evaluation, in Python and JavaScript | Tested (stubs) |
| [`mych-api-integration`](specialists/mych-api-integration/SKILL.md) | Resilient clients, webhooks, OpenAPI checks, stub servers | Tested |
| [`mych-emoji-language`](specialists/mych-emoji-language/SKILL.md) | Emoji sequences, lengths, rendering, custom emoji, visual language | Tested |
| [`mych-cloud-infrastructure`](specialists/mych-cloud-infrastructure/SKILL.md) | Hosting decisions, plan, DNS and Dockerfile reviews, sourced cost estimates | Tested (offline) |
| [`mych-runpod`](specialists/mych-runpod/SKILL.md) | GPU sizing, persistence-aware plans, dry-run serverless client | Tested (offline and stubs) |

Details: [architecture](docs/architecture.md), [specialist capability matrix](docs/specialist-capability-matrix.md).

## Install

Release archives (one skill per ZIP, skill folder at the archive root) are in [`dist/`](dist/).

**Claude Code:** copy the skills you want into `~/.claude/skills/` (personal) or `.claude/skills/` (project), or let the tool do it:

```bash
python3 tools/mych.py export --host claude-code --project .
```

**Claude apps that accept skill uploads:** upload `dist/mych-plugin-2.0.0.zip` and any specialist archives you want.

**Codex, Gemini CLI, GitHub Copilot:** export to the host's documented folder (the tool rewrites `${CLAUDE_SKILL_DIR}`, which only Claude Code expands). These hosts are documented to read skills but were not tested here:

```bash
python3 tools/mych.py export --host codex --project .
```

```bash
python3 tools/mych.py export --host gemini-cli --project .
```

```bash
python3 tools/mych.py export --host github-copilot --project .
```

**Any model through an API:** build a bundle (system prompt plus translated tool definitions within a token budget), or run the agent harness:

```bash
python3 tools/mych.py bundle --provider gemini --task "Add retries to our payment client" --out build/bundle
```

```bash
python3 tools/mych.py harness --provider ollama --model MODEL --task "Plan a small change and verify it" --workspace .
```

## Command-line tool

`tools/mych.py` (standard-library Python 3.8+):

| Command | Does |
|---|---|
| `route "TASK"` | Suggests tier, lead discipline, workflow and specialists (heuristic; the coordinator confirms) |
| `bundle --provider ID` | Single system prompt plus tool definitions for models without skill loading |
| `export --host ID` | Installs skills into a host's skills folder |
| `tools-schema --format openai\|anthropic\|gemini\|openai-compatible` | Prints tool definitions in a provider's format |
| `run-tool NAME --args JSON` | Executes one neutral tool call, confined to a workspace; paid actions need `--approved` |
| `harness --provider ID --model M --task T` | Agent loop against a model API (or `--dry-run`) |
| `validate-all`, `package-all`, `registry-check` | Validation, deterministic release archives, registry consistency |

## Repository layout

```text
mych-plugin/              core skill (MYCH-HORIZON Core)
specialists/mych-*/       eight domain specialist skills
registry/                 specialists, workflows, providers and hosts, tools, integrations (data)
adapters/                 provider notes: Claude, GPT, Gemini, GLM, open-weight and local
tools/                    mych.py command-line tool; collect_ecosystem.py
docs/                     architecture, matrices, integration registry, roadmap, decisions
evaluation/               1.0 scenarios and live test; 2.0 game benchmark with evidence; security review
tests/                    repository tests (Python unittest; Node tests for the JavaScript kit)
dist/                     release archives
.mych/tasks.json          the 2.0 build's own task ledger
```

## Development

```bash
python3 -m unittest discover -s tests
```

```bash
python3 tools/mych.py validate-all --strict && python3 tools/mych.py registry-check
```

```bash
python3 tools/mych.py package-all --out dist
```

## Limitations

- **Cross-model behavior is untested.** Only Claude in Claude Code has executed the framework; adapters for GPT, Gemini, GLM and open-weight models pass stub tests only (no keys or local runtime were available).
- **Live services were not called.** Image generation, Blender, RunPod and cloud actions are implemented with dry runs, stubs or templates and are labeled unverified until run with real credentials or software.
- **Routing is heuristic.** `route` uses keyword signals; the core's orientation questions remain the authority.
- **Self-assessed benchmark.** The game benchmark score was assigned by the agent that built it, with evidence for every line.
- **License.** Not yet specified by the project owner.

## Version information

2.0.0, released 2026-11-06. The version is in each skill's `metadata.version`, in `registry/specialists.json` and in the archive names. The 1.0.0 core archive remains in `dist/` for reference.

## License

Not yet specified by the project owner.
