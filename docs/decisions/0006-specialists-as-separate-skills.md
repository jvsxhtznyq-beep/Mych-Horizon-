# 0006. Ship domain specialists as separate skills

- Status: accepted
- Date: 2026-11-01

## Context

The 2.0 brief adds eight domains (3D, image generation, pixel art, chatbots, emoji, cloud, RunPod, API integration), each needing knowledge, tools and tests. Putting them inside the core skill would grow every task's context and couple unrelated release cycles.

## Decision

Each domain is an independent Agent Skill named `mych-*` with twelve required sections, its own references, standard-library scripts and tests in the repository. The core routes to specialists but works without them; specialists work with or without the core. The validator enforces the specialist layout.

## Consequences

- Hosts load a specialist only when its description matches the task, keeping context small.
- Each specialist can be installed, versioned and packaged on its own (`package-all` builds one archive per skill).
- Cross-skill consistency (versions, requirements, tools) is checked by `registry-check` instead of being implicit.
