# 0008. Use explicit evidence levels for every compatibility claim

- Status: accepted
- Date: 2026-11-01

## Context

The brief forbids fabricated cross-model results and requires that missing evidence be marked unverified. Without a shared vocabulary, "supports" and "works with" drift into claims nobody tested.

## Decision

Every provider, host and specialist claim carries an evidence level: executed, stub-tested, documented, secondary or unknown for providers and hosts; planned, implemented, tested or verified for specialists. `registry-check` rejects unknown levels and evidence without sources. Documentation must not state more than the level supports.

## Consequences

- Readers can see at a glance that only Claude in Claude Code is executed.
- Moving a cell to "executed" requires a recorded run, which keeps the matrix honest over time.
- Some documentation reads more cautiously than marketing copy would; that is intended.
