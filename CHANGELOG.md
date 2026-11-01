# Changelog

All notable changes to MYCH-PLUGIN are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

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
