# 0001. Ship MYCH-PLUGIN as one integrated skill with one-hop references

- Date: 2026-11-01
- Status: Accepted
- Deciders: Kim (owner, via the master build specification); implementation session

## Context

The specification asks for one coordinated system with five disciplines under a shared intelligence core, packaged as a single skill named `mych-plugin`. Anthropic's skill documentation recommends focused skills ("several focused skills combine better than one large skill"), a `SKILL.md` body under 500 lines, and references kept one level deep from `SKILL.md`, because Claude may only partially read files that are reached through other referenced files. In Claude's ecosystem, "plugin" also names a different package type that bundles skills, connectors and other extensions.

## Problem

Should MYCH-PLUGIN be one skill, several focused skills, or a plugin, and how should its 50 files be organized so Claude loads only what a task needs?

## Options

1. **One integrated skill with progressive disclosure.** Pros: matches the owner's specification; one coordinator decides across disciplines; shared standards apply uniformly. Cons: a broad description may load the skill for many tasks; `SKILL.md` costs context each time it loads.
2. **Several focused skills (core plus one per discipline).** Pros: follows the focused-skill guidance; smaller loads. Cons: no single coordinator; shared standards duplicated or cross-referenced across skills; contradicts the specification.
3. **A Claude Code plugin bundling several skills.** Pros: installable as a unit in Claude Code. Cons: a different packaging target from the requested skill upload ZIP; adds speculative integration work.

## Decision

Option 1. `SKILL.md` stays lean (principles, orientation, tiers, selection, lifecycle, gates) and links every supporting file directly in a file map, so every reference is one hop from `SKILL.md`. Detailed guidance lives in eight folders and loads only when a task triggers it. Tier 1 work is pointed at a single workflow file.

## Reasoning

The owner's requirement for one coordinating core outweighs the general focused-skill guidance, and progressive disclosure addresses most of its cost: only `SKILL.md` loads on activation, and each supporting file states when to load it. The validator enforces the one-hop rule for this layout, so new files cannot silently become unreachable.

## Consequences

- Easier: one place to change coordination rules; uniform standards; simple installation.
- Harder: the description must stay accurate as scope grows; the `SKILL.md` file map must be updated for every new file (the validator fails until it is).
- Risk accepted: the skill may load for tasks where it adds little. Revisit if live evaluation shows over-triggering, under-triggering or a noticeable context cost on small tasks; the fallback is splitting discipline manuals into separate skills that share the core.
- Naming: despite its name, the package is an Agent Skill, not a Claude plugin. Wrapping it in a plugin later is possible without restructuring the skill folder.

## Alternatives rejected

- Several focused skills: contradicts the single-coordinator requirement.
- Plugin packaging now: speculative for version 1; the specification asks for a skill upload ZIP.
