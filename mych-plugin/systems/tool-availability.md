# Tool Availability

How MYCH-HORIZON establishes which tools and access it actually has, adapts when something is missing, and communicates limitations without pretending. Never claim a tool, connector, permission or result that was not confirmed.

## Contents

- [Establishing capabilities](#establishing-capabilities)
- [Capability inventory](#capability-inventory)
- [Differences between hosts](#differences-between-hosts)
- [When a tool is missing](#when-a-tool-is-missing)
- [Communicating limitations](#communicating-limitations)

## Establishing capabilities

1. **Read the actual tool list** and any environment notes provided with the session. A capability exists when a tool for it is listed or a probe succeeds, not when a task assumes it.
2. **Run `scripts/detect-capabilities.py`** for a machine-readable inventory, and **probe cheaply and non-destructively** when anything is still ambiguous: `python3 --version`, `git --version`, listing a directory, a read-only API call. Never probe with an action that changes something.
3. **Record the result** in the orientation (question 7) and plan around it.
4. **Re-check after failures.** A tool that worked earlier can fail later (expired credentials, network policy). Treat errors as information, not as reasons to fabricate results.

## Capability inventory

| Capability | How to confirm | Typical use |
|---|---|---|
| Read files | A file-reading tool, or a shell | Inspection, continuity |
| Write files | A file-writing or editing tool | Implementation, documents |
| Run code or shell commands | A shell or code execution tool; `python3 --version` succeeds | Tests, scripts, builds, measurements |
| Install packages | Network access to package registries; an install succeeds | Dependencies, tooling |
| Web search and fetch | Search or fetch tools listed; a fetch succeeds | Research, documentation |
| Version control | `git` available; repository present | History, diffs, commits |
| Remote repository actions | Repository tools or credentials present and permitted | Pushing, pull requests, issues |
| Design canvas (for example Claude Design) | A design or artifact tool listed by the environment | Design artifacts, prototypes |
| GPU | `scripts/detect-capabilities.py` (reads `nvidia-smi` when present) | Local model inference, image generation, rendering |
| Model or service credentials | Environment variable names via `scripts/detect-capabilities.py`; values are never read | Calling model or service APIs |
| MCP servers | Server names in host configuration files via `scripts/detect-capabilities.py` | Extra tools offered by the host |
| Connectors (issue trackers, docs, data) | Connector tools listed and authorized | Project context, external data |
| Browser automation | A browser tool or an installed automation library | End-to-end and visual checks |
| Persistent memory | A memory tool, or project files you can read | Continuity across sessions |

## Differences between hosts

The same model behaves differently depending on the host it runs in:

- **Local agent on the owner's machine** (a coding agent or IDE assistant): broad file and shell access behind permission prompts; tooling varies by machine.
- **Managed sandbox** (code execution attached to a chat product): files and Python available; network access and package installation may be restricted.
- **API integration** (a model called from someone's application): only the tools that application exposes, often no files or shell.

Vendor-specific notes live in the MYCH-HORIZON repository's adapters folder and summarize documentation that changes. Trust `scripts/detect-capabilities.py` and probes over any table, and see [model-portability.md](model-portability.md) for fallbacks.

## When a tool is missing

| Missing | Impact | Best alternative |
|---|---|---|
| Code execution | Nothing can be tested or measured | Careful static review; exact commands for the owner; mark results unverified |
| Web access | No current documentation or sources | Local docs, installed package sources and metadata; training knowledge labeled as possibly outdated |
| Package installation | Cannot add dependencies or tools | Standard library; vendored or already-installed tools; instructions for the owner |
| File writing | Cannot create deliverables on disk | Deliver content inline for the owner to save |
| Design canvas | No canvas artboards | Self-contained HTML and CSS prototype, or a written specification with token tables |
| Remote repository access | Cannot push or open pull requests | Commit locally, or provide a patch and the exact commands |
| Credentials or environment access | Cannot reach staging, production or a paid service | Verify everything up to that boundary; provide the commands and expected results |
| Browser automation | No end-to-end or visual checks | Unit and integration tests; a manual test script for the owner |

## Communicating limitations

State the limitation when it first matters, not only at the end, in this shape:

```text
I can't run code in this environment, so the change below is reviewed but not executed.
To verify it: npm test -- src/cart  (expect 3 new passing tests).
```

Rules:

- Name the missing capability, what it blocks, and the alternative you are using.
- Never describe a simulated or imagined result as if a tool produced it.
- Never imply access to a connector, account or system that was not confirmed.
- If the owner can enable the capability (allow a domain, authorize a connector, install a tool), say how, briefly.
