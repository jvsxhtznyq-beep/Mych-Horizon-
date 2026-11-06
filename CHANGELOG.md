# Changelog

All notable changes to MYCH-HORIZON (formerly MYCH-PLUGIN) are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-11-06

MYCH-HORIZON: the framework becomes model-agnostic and gains eight domain specialists. The core skill keeps its id `mych-plugin` ([decision 0005](docs/decisions/0005-keep-core-skill-id-mych-plugin.md)).

### Added

- Eight specialist skills under `specialists/`: `mych-pixel-art`, `mych-image-generation`, `mych-3d-design`, `mych-chatbot-engineering`, `mych-api-integration`, `mych-emoji-language`, `mych-cloud-infrastructure`, `mych-runpod`, each with twelve required sections, references, standard-library tools and tests.
- Core: `systems/delegation.md`, `systems/model-portability.md`, domain specialist routing and handoffs, `scripts/detect-capabilities.py` (platform, commands, modules, GPU, credential names, skills, MCP server names, specialist readiness).
- `registry/` (specialists, workflows, providers and hosts with evidence levels, neutral tools, integrations with live GitHub evidence) and `adapters/` for Claude, GPT, Gemini, GLM and open-weight models.
- `tools/mych.py`: route, bundle, export, tools-schema, run-tool (workspace confinement, approval gating), harness, validate-all, package-all, registry-check; `tools/collect_ecosystem.py`.
- Game benchmark Glowmoss Caverns with unit, stress, failure, solver and browser tests and a scored report.
- Documentation: architecture, model compatibility matrix, specialist capability matrix, integration registry, roadmap, decisions 0005 to 0008, security review.

### Changed

- Task ledger schema 2: lock file for concurrent writers, failed status, approval gates (`--needs-approval`, `approve`, `unblock --approved-by`), evidence rules (restated, vague and failure-marker evidence refused unless overridden with a recorded reason), completed tasks can be blocked; schema 1 ledgers upgrade on write.
- Project scanner: correct unittest command for test folders, data files listed but never opened, node-tap and the Node.js built-in runner recognized.
- Validator: `mych-specialist` layout for any `mych-*` skill.
- Core wording made provider-neutral; the framework is branded MYCH-HORIZON.

### Fixed

- Live-test weaknesses from 1.0 (see `evaluation/live-test-report.md`): lost ledger writes under concurrency, accepted failing or vague evidence, unenforced approval blocks, wrong inferred test command, missing delegation guidance and missing architecture-only route.

## [1.0.0] - 2026-11-01

First release.

### Added

- `SKILL.md` entry point: activation description, operating loop, nine orientation questions, ten operating principles, authority model, task tiers 0 to 3, specialist selection with combination recipes, nine-phase lifecycle, workflow routing, verification and approval rules, and a file map linking every supporting file directly.
- Intelligence core (`core/`): coordinator procedure, specialist selection with signal catalog and handoff contracts, operating principles with failure signs and conflict resolution, clarification protocol.
- Five discipline manuals (`modes/`): Architect, Researcher, Designer, Engineer, Inventor.
- Ten workflows (`workflows/`): execution lifecycle, lightweight task, new software project, technical research, product design (new and redesign tracks), debugging, performance investigation, invention, sensitive change, continuing project.
- Standards (`standards/`): quality framework with ten evidence-based dimensions, testing strategy, completion criteria, security, transparency and reporting.
- Systems (`systems/`): task management, project memory, decision records, tool availability, autonomy and approval.
- Ten output templates (`templates/`) and six references (`references/`): architecture patterns, source evaluation, design foundations, accessibility checklist (WCAG 2.2 AA oriented), engineering domain checklists, feasibility scale.
- Scripts (`scripts/`), standard-library Python 3.8 or newer: `validate-skill.py`, `package-skill.py`, `scan-project.py`, `task-ledger.py`.
- Unit tests for every script and a staleness check for the committed archive (`tests/`).
- Decision records 0001 to 0004 (`docs/decisions/`).
- Acceptance scenarios and static evaluation results (`evaluation/`).
- Release archive `dist/mych-plugin-1.0.0.zip`.
