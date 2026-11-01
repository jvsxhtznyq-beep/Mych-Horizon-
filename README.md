# MYCH-PLUGIN

**Universal Engineering Intelligence Framework**, an Agent Skill for Claude.

| | |
|---|---|
| Skill name | `mych-plugin` |
| Version | 1.0.0 (2026-11-01) |
| Owner | Kim |
| Package | [`dist/mych-plugin-1.0.0.zip`](dist/mych-plugin-1.0.0.zip) |
| Target | Claude surfaces that support Agent Skills: Claude web and desktop apps, Claude Code, the Claude API |

## What it is

MYCH-PLUGIN is a modular operating framework that changes how Claude approaches complex technical, creative, research, design and software work. One intelligence coordinator orients on the objective, selects the minimum set of five specialist disciplines a task needs, runs a lifecycle proportional to the task's size and risk, and verifies before it claims anything is complete.

It is not a collection of personas. The disciplines are operating manuals with workflows, quality bars and handoff contracts, bound together by shared standards for quality, testing, security and transparent reporting.

## Purpose

- Approach large or ambiguous technical work methodically: orient, investigate, decide, build, verify.
- Keep small work small: a one-line fix gets a five-step lightweight path, not a project plan.
- Make quality claims evidence-based: *completed* and *verified* are different statuses.
- Respect the owner's authority and approval boundaries while still contributing independent judgment.
- Preserve continuity across sessions through the project's own documentation and decision records.

## Architecture

```text
              Request  ·  Environment  ·  Project context
                                 │
                                 ▼
          ┌──────────────────────────────────────────────┐
          │           Intelligence Coordinator           │   core/
          │  orient → size → select → plan → verify →    │
          │  report                                      │
          └──────────────────────────────────────────────┘
                                 │  minimum sufficient set
      ┌───────────┬───────────┬──┴────────┬───────────┐
      ▼           ▼           ▼           ▼           ▼
  Architect   Researcher   Designer    Engineer    Inventor        modes/
      └───────────┴───────────┴─────┬─────┴───────────┘
                                    ▼
                    Verification gate (evidence per requirement)
                                    ▼
                    Delivery with a transparent report

  Shared foundations, loaded on demand:
  workflows/ · standards/ · systems/ · templates/ · references/ · scripts/
```

- **Operating loop:** orient (nine questions), size (Tier 0 to 3), select disciplines, load only the needed files, execute, verify, report.
- **Task tiers:** Tier 0 direct answer; Tier 1 light (one component); Tier 2 standard (several parts or an unknown cause); Tier 3 full (new system, high risk, multi-session).
- **Lifecycle:** Discovery, Investigation, Architecture, Design, Planning, Implementation, Verification, Optimization, Delivery. Each tier runs only the phases its risk requires; Discovery, Verification and Delivery always run.
- **Progressive disclosure:** `SKILL.md` stays concise and links every supporting file directly, one hop away, so Claude loads detail only when a task needs it.

## The five disciplines

| Discipline | Owns | Manual |
|---|---|---|
| Architect | System structure, data, APIs, reliability, scalability, migrations; proportional architecture with failure analysis | [`modes/architect.md`](mych-plugin/modes/architect.md) |
| Researcher | Evidence-based answers: source tiers, version and date checks, labeled claims, conditional recommendations | [`modes/researcher.md`](mych-plugin/modes/researcher.md) |
| Designer | Users and tasks, information architecture, tokens, component states, responsive behavior, accessibility; Claude Design when available | [`modes/designer.md`](mych-plugin/modes/designer.md) |
| Engineer | Inspect-before-change protocol, focused implementation, tests, honest verification, version-control hygiene | [`modes/engineer.md`](mych-plugin/modes/engineer.md) |
| Inventor | Distinct concepts, prior-art mapping, feasibility ratings, prototypes aimed at the riskiest assumption | [`modes/inventor.md`](mych-plugin/modes/inventor.md) |

Common combinations: a new application uses Architect, Designer and Engineer; a completely new technology uses Researcher, Inventor, Architect and Engineer; a product redesign uses Researcher, Designer, Architect and Engineer; a performance investigation uses Researcher, Architect and Engineer.

## Repository layout

```text
Mych-Horizon-/
├── mych-plugin/                 the skill package (50 files; the only folder that ships)
│   ├── SKILL.md                 entry point: principles, tiers, selection, lifecycle, gates, file map
│   ├── core/            (4)     coordinator, specialist selection, operating principles, clarification
│   ├── modes/           (5)     architect, researcher, designer, engineer, inventor
│   ├── workflows/       (10)    lifecycle, lightweight task, new project, research, design, debugging,
│   │                            performance, invention, sensitive change, continuing project
│   ├── standards/       (5)     quality framework, testing, completion criteria, security, reporting
│   ├── systems/         (5)     task management, project memory, decision records, tool availability,
│   │                            autonomy and approval
│   ├── templates/       (10)    strategy, task plan, architecture proposal, decision record, research
│   │                            report, design spec, invention concept, investigation log, delivery
│   │                            report, project context
│   ├── references/      (6)     architecture patterns, source evaluation, design foundations,
│   │                            accessibility checklist, engineering domains, feasibility scale
│   └── scripts/         (4)     validate-skill.py, package-skill.py, scan-project.py, task-ledger.py
├── docs/decisions/              decision records for MYCH-PLUGIN itself
├── evaluation/                  acceptance scenarios and evaluation results
├── tests/                       unit tests for the scripts and the committed archive
├── dist/                        the release ZIP
├── CHANGELOG.md
└── README.md
```

Human-facing documentation, tests and evaluation stay outside the skill folder so the package carries only what Claude needs ([decision 0002](docs/decisions/0002-keep-human-documentation-outside-the-skill-folder.md)).

## Installation

### Claude web and desktop apps

1. Download [`dist/mych-plugin-1.0.0.zip`](dist/mych-plugin-1.0.0.zip).
2. In Claude, open **Customize > Skills**, upload the ZIP, and turn the skill on. (Menu names follow Anthropic's current "Create custom skills" guide and may change.)
3. The bundled scripts run only where code execution is available. The guidance works without them.

The archive contains the `mych-plugin/` folder as its single top-level entry, which is the layout the upload expects.

### Claude Code

Copy the skill folder into your personal or project skills directory:

```bash
cp -R mych-plugin ~/.claude/skills/
```

```bash
mkdir -p .claude/skills && cp -R mych-plugin .claude/skills/
```

Start `claude`, then describe a task the skill covers, or type `/mych-plugin` to invoke it directly.

### Claude API

Upload the skill through the Skills API as described in Anthropic's [skills guide](https://platform.claude.com/docs/en/build-with-claude/skills-guide). API code execution has no network access and no runtime package installation; the scripts use only the Python standard library, so they work there.

## Usage examples

The skill activates from its description when a request matches, or explicitly ("Use MYCH-PLUGIN to ..." or `/mych-plugin` in Claude Code).

| Request | What MYCH-PLUGIN does |
|---|---|
| "Fix the off-by-one error in `api/orders.py` pagination." | Tier 1, Engineer only: read, minimal fix, regression test, run it, five-line report |
| "Build a booking app for my clinic." | Tier 3: at most three essential questions, proportional architecture with decision records, design before screens, vertical slices, per-slice verification |
| "Redis Streams or RabbitMQ for our order events?" | Researcher: criteria first, sourced and dated evidence, labeled claims, conditional recommendation |
| "Design the onboarding flow for our budgeting app." | Designer: users and tasks, tokens, full component states, responsive and accessibility review; Claude Design artifacts when available |
| "The nightly export sometimes writes an empty file." | Debugging workflow: reproduce, isolate, test hypotheses one at a time, fix the root cause, regression test |
| "Invent a new way for remote teams to sense availability." | Inventor: problem frame, prior art, three or more distinct concepts with feasibility ratings, owner checkpoint before prototyping |
| "Delete inactive accounts in production tonight." | Sensitive-change workflow: threat model, denied-access tests, explicit approval request with safeguards before any production action |
| "Let's continue with the booking app." | Continuity protocol: read instructions, decision records and task ledger first; verify state; continue under existing decisions |

## Bundled scripts

All scripts are standard-library Python 3.8 or newer, support `--help`, and use exit status 0 for success, 1 for problems found and 2 for usage errors.

| Script | Purpose |
|---|---|
| `scripts/validate-skill.py` | Validates a skill folder: structure, YAML frontmatter (strict built-in parser, cross-checked with PyYAML when installed), metadata limits, naming, file references, links and heading anchors, placeholder and empty files, development artifacts and secrets |
| `scripts/package-skill.py` | Builds a deterministic, upload-ready ZIP with the skill folder as its top level, excludes development artifacts, then reopens and verifies the archive against the source; `--verify-only` checks an existing ZIP |
| `scripts/scan-project.py` | Read-only project summary for Discovery: languages, stack signals, likely commands, CI, documentation, decision records, task ledgers; lists secret-bearing files without opening them |
| `scripts/task-ledger.py` | JSON task ledger that enforces the status rules: dependencies before start, completion before verification, substantive evidence for verification |

## Development

```bash
python3 mych-plugin/scripts/validate-skill.py --strict
```

```bash
python3 -m unittest discover -s tests
```

```bash
python3 mych-plugin/scripts/package-skill.py
```

Release checklist:

1. Update the content and bump `metadata.version` in `mych-plugin/SKILL.md`.
2. Add a `CHANGELOG.md` entry.
3. Run the validator in strict mode and the unit tests.
4. Rebuild the package; the archive lands in `dist/` as `mych-plugin-<version>.zip`.
5. Commit the archive with the change. `tests/test_dist_archive.py` fails if the committed archive no longer matches the skill folder.

Extending: add one kebab-case file to the matching folder, register it in the `SKILL.md` tables (and, for a new discipline, in `core/specialist-selection.md`), then validate. The validator fails until every file is referenced from `SKILL.md`.

## Verification status

| Check | Status |
|---|---|
| Strict validation of the package | Passed (0 errors, 0 warnings) |
| Unit tests | Passed; details in [evaluation/results.md](evaluation/results.md#automated-checks) |
| Package build and archive verification | Passed |
| Static trace of the ten acceptance scenarios | All covered after four fixes ([results](evaluation/results.md)) |
| Live behavioral evaluation with Claude | **Not yet run.** Protocol ready in [evaluation/scenarios.md](evaluation/scenarios.md#running-a-live-evaluation) |

## Limitations

- **Skills guide behavior; they do not guarantee it.** The scenarios were traced against the instructions, not run live. Behavioral effectiveness is unmeasured until the live protocol is run.
- **Broad activation.** The description covers most technical work by design. The skill may load where it adds little, and `SKILL.md` costs context each time it loads ([decision 0001](docs/decisions/0001-ship-one-integrated-skill-with-one-hop-references.md)).
- **Environment-dependent capabilities.** Claude Design, web access and code execution vary by surface. The skill detects and reports their absence but cannot provide them.
- **Script compatibility.** The scripts were executed on Python 3.13 and checked against the Python 3.8 grammar; they were not run on a 3.8 interpreter.
- **Frontmatter parsing.** The validator's built-in parser supports the conservative YAML subset skill frontmatter needs and reports anything else ([decision 0003](docs/decisions/0003-standard-library-scripts-and-a-strict-frontmatter-parser.md)).
- **Specification access.** The Agent Skills specification site was unreachable from the build environment. Field limits were confirmed from Anthropic's documentation; the list of optional fields (`license`, `compatibility`, `metadata`, `allowed-tools`) follows the specification as known at build time. Running the reference `skills-ref validate` tool is a worthwhile independent check.
- **Name versus package type.** Despite its name, MYCH-PLUGIN is an Agent Skill, not a Claude plugin. It can be wrapped in a plugin later without restructuring the skill folder.
- **Archive bytes.** Builds are deterministic for a given Python and zlib build. Content verification is exact regardless of zlib version.

## Version information

Version 1.0.0, released 2026-11-01. See [CHANGELOG.md](CHANGELOG.md). The version is recorded in `metadata.version` in `mych-plugin/SKILL.md` and in the archive name.

## License

Not yet specified by the project owner.
