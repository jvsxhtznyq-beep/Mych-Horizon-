# 0005. Keep the core skill id `mych-plugin` under the MYCH-HORIZON name

- Status: accepted
- Date: 2026-11-01

## Context

Version 2.0 renames the framework to MYCH-HORIZON. The core skill's `name` (`mych-plugin`) is its install identity: hosts key installed skills by name, users may already have version 1.0 installed, and the folder name must match the skill name.

## Decision

Keep the skill id and folder `mych-plugin`. Present it as "MYCH-HORIZON Core" through `metadata.display-name`, the title and the documentation. Name new specialists `mych-*`.

## Consequences

- Version 1.0 installations upgrade in place; no duplicate skills appear side by side.
- The id no longer matches the brand; documentation explains the relationship.
- A future rename would need a migration note and a period where both ids are documented.
