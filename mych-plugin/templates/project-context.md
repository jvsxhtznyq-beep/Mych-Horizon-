# Template: Project Context

A short, current-state file for projects that span sessions and have no existing place for that state. It is a map, not an archive: link to decision records, task lists and docs instead of copying them. Protocol: [project-memory.md](../systems/project-memory.md).

## How to fill it

- Create it only when no equivalent exists; tell the owner you created it.
- Keep it under about a hundred lines. Move detail into the documents it links to.
- Update "Current state", "In progress" and "Next steps" at the end of each working session.
- Never store secrets, credentials or personal data here.

## Template

```markdown
# Project context: [project name]

Last updated: [YYYY-MM-DD] by [who or which session]

## Purpose
[One paragraph: what the project is and who it serves.]

## Current state
[Three to five lines: what works today, what is verified, what is not.]

## How to run and test
- Setup: [command]
- Run: [command]
- Test: [command]

## Architecture in brief
[Five lines at most, then links: architecture proposal, diagrams.]

## Conventions
- [Convention that is not obvious from the code, with a link to where it is defined]

## Decisions
- [NNNN-title](docs/decisions/NNNN-title.md): [one-line summary]

## In progress
- [Task ID or description]: [exact state]

## Next steps
1. [Next action]

## Open problems and gotchas
- [Problem or gotcha, and what is known about it]
```
