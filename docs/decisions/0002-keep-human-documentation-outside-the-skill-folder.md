# 0002. Keep human-facing documentation, tests and evaluation outside the skill folder

- Date: 2026-11-01
- Status: Accepted
- Deciders: implementation session, within the owner's specification

## Context

The specification requires a root README and a CHANGELOG, test scenarios and validation, and a skill package whose files all contain actionable instructions. Anthropic's skill guidance says a skill should contain only what an agent needs to do the work and advises against auxiliary files such as README and CHANGELOG inside the skill folder. Everything inside the skill folder is loaded into the agent's filesystem and shipped to everyone who installs it.

## Problem

Where do README, CHANGELOG, tests, evaluation material, decision records and build output live?

## Options

1. **Repository root for human material; `mych-plugin/` only for agent-facing files.**
2. **Everything inside `mych-plugin/`.**

## Decision

Option 1. The repository root holds `README.md`, `CHANGELOG.md`, `docs/decisions/`, `tests/`, `evaluation/` and `dist/`. The `mych-plugin/` folder holds `SKILL.md` and the eight agent-facing folders only. The packager archives only `mych-plugin/`.

## Reasoning

It keeps the shipped package free of material the agent never needs, satisfies the root README requirement literally, and lets the validator treat a README or CHANGELOG inside a skill folder as a warning for any skill.

## Consequences

- Easier: the package stays small and purposeful; tests and evaluation can grow without affecting installs.
- Harder: version information appears in two places (`metadata.version` in `SKILL.md` and the CHANGELOG); the release checklist in the README keeps them in step.

## Alternatives rejected

- Everything inside the skill: ships non-agent material to every installation and conflicts with Anthropic's guidance.
