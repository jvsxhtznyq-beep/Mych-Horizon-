# MYCH-PLUGIN evaluation results

Evaluation of version 1.0.0 against the ten scenarios in [scenarios.md](scenarios.md), plus the automated checks run on the package.

## What was and was not tested

| Kind of check | Performed | Result |
|---|---|---|
| Static scenario trace: does the skill route each scenario correctly and contain an explicit instruction for every pass criterion? | Yes, for all ten scenarios | All ten covered after four fixes (below) |
| Live behavioral runs: does Claude, with the skill installed, actually behave this way? | **No** | Not run. This environment could not install the skill into a separate Claude instance, and no independent sessions were started for it. The protocol in [scenarios.md](scenarios.md#running-a-live-evaluation) is ready for the owner to run. |
| Automated checks of the package and scripts | Yes | See [Automated checks](#automated-checks) |

The static trace was performed by the same session that wrote the skill, so it is not an independent review. It shows that the instructions exist and route correctly. It cannot show that a model follows them.

## Method

For each scenario:

1. Start from `SKILL.md` as a model would: size the task with the tier table, select disciplines with the specialist table, pick the workflow from the workflow table.
2. Follow only the files that the file map and the chosen workflow direct the reader to.
3. For each pass criterion, find the explicit instruction that produces the behavior and record the file and section.
4. Verdict per criterion: **covered** (an explicit instruction), **partial** (implied, ambiguous or reached only indirectly) or **gap** (no instruction).
5. Fix partials and gaps in the skill, then re-trace.

## Findings fixed during evaluation

| ID | Scenario | Finding | Fix |
|---|---|---|---|
| F1 | S1 | Routing ambiguity: the workflow table sent every bug to `workflows/debugging.md`, a ten-step investigation, even when the cause and fix were obvious and local | `SKILL.md` workflow table now routes bugs with an obvious local cause to `workflows/lightweight-task.md` and only bugs with an unknown cause to `workflows/debugging.md`; `debugging.md` states the same boundary |
| F2 | S1 | Tier 1 work could load a full mode manual because the file map said "load when the discipline is active" | The operating loop's Load step and the file map now say Tier 1 usually needs only `workflows/lightweight-task.md` |
| F3 | S1 | `workflows/lightweight-task.md` asked to read callers but not existing tests before editing | The Locate step now includes existing tests |
| F4 | S9 | Regulatory and data-retention obligations were covered in `standards/security.md` but not in the sensitive-change procedure itself | Step 1 of `workflows/sensitive-change.md` now names legal and regulatory obligations and says to raise them rather than assume compliance |

## Scenario traces

### S1. Simple coding task: covered

| Criterion | Where the skill produces it |
|---|---|
| Routes to Tier 1, Engineer only, lightweight workflow | `SKILL.md` Task tiers (Tier 1) and Workflows table (after F1); `core/specialist-selection.md` recipe "Small change in known code" |
| Reads the function and its test first | `workflows/lightweight-task.md` step 2 Locate (after F3) |
| Minimal change, no unrelated refactoring | `workflows/lightweight-task.md` step 3 and "Keep it light" |
| Adds a test | `workflows/lightweight-task.md` step 3 |
| Runs the check and reports the real result | `workflows/lightweight-task.md` steps 4 and 5; `standards/transparency-and-reporting.md` Prohibited reporting |
| No planning documents or role-play | `workflows/lightweight-task.md` "Keep it light"; `core/specialist-selection.md` Anti-patterns (persona theater) |
| Report in a few lines | `workflows/lightweight-task.md` step 5 and report example |

### S2. Complex software project: covered

| Criterion | Where the skill produces it |
|---|---|
| At most three essential questions with defaults | `workflows/new-software-project.md` Discovery step 2; `core/clarification-protocol.md` Asking well |
| Condensed plan with success criteria and approval points | `core/intelligence-coordinator.md` Forming the execution strategy; `templates/execution-strategy.md`; `workflows/new-software-project.md` Planning |
| Proportional architecture, stack rationale, decisions recorded | `modes/architect.md` Proportionality; `workflows/new-software-project.md` Architecture; `systems/decision-records.md` |
| Design before screens, with states, responsiveness and accessibility | `workflows/new-software-project.md` Design; `modes/designer.md` Workflow; `SKILL.md` principle 4 |
| Vertical slices, walking skeleton, verification per task | `workflows/new-software-project.md` Planning; `templates/task-plan.md` |
| Per-slice evidence in reports | `workflows/new-software-project.md` Implementation; `standards/completion-criteria.md` |

### S3. Technical research: covered

| Criterion | Where the skill produces it |
|---|---|
| Question, criteria and weights first | `workflows/technical-research.md` step 1; `modes/researcher.md` Framing the question |
| Checks web access, adjusts confidence | `workflows/technical-research.md` step 2; `modes/researcher.md` Working without web access |
| Sources opened in session, versions and dates | `modes/researcher.md` Sources and versions, Citation rules; `references/source-evaluation.md` |
| Claims labeled; confidence stated | `modes/researcher.md` Weighing evidence |
| Conditional recommendation, no unconditional winner | `modes/researcher.md` Comparisons; `workflows/technical-research.md` step 7 |
| No invented citations or numbers | `modes/researcher.md` Citation rules; `workflows/technical-research.md` Verification |

### S4. Product design: covered

| Criterion | Where the skill produces it |
|---|---|
| Users, tasks and context before visuals | `workflows/product-design.md` Track A step 1; `modes/designer.md` Understanding users and tasks |
| Named direction and tokens with computed contrast | `modes/designer.md` Design direction; `references/design-foundations.md` Color and contrast |
| Full state matrix; screens with real content and states | `modes/designer.md` Tokens and components, Screens; `references/design-foundations.md` Component state matrix |
| Layouts per width, touch targets, keyboard paths | `workflows/product-design.md` step 7; `modes/designer.md` Screens, responsiveness and feedback |
| Accessibility results and consistency pass | `workflows/product-design.md` steps 8 and 9; `references/accessibility-checklist.md` |
| Artifacts labeled; Claude Design only if available | `modes/designer.md` Using Claude Design, Mockups are not implementations; `systems/tool-availability.md` |

### S5. Debugging: covered

| Criterion | Where the skill produces it |
|---|---|
| Symptom captured before changes | `workflows/debugging.md` step 1 and governing rule |
| Reproduction or evidence gathering first | `workflows/debugging.md` step 2 |
| Hypotheses tested one at a time | `workflows/debugging.md` steps 4 and 5, Rules; `templates/investigation-log.md` |
| Root cause distinct from trigger, or labeled hypothesis | `workflows/debugging.md` step 6 and Rules |
| Fix, regression test, suite run | `workflows/debugging.md` steps 7 to 9 |
| Production actions gated | `workflows/debugging.md` Special cases; `workflows/sensitive-change.md` |

### S6. Original invention: covered

| Criterion | Where the skill produces it |
|---|---|
| Problem frame | `modes/inventor.md` Framing the problem |
| Existing approaches mapped | `modes/inventor.md` Mapping existing approaches; `workflows/invention.md` stage 2 |
| Three or more concepts differing in mechanism | `modes/inventor.md` Generating distinct concepts (distinctness check) |
| Feasibility, resources, riskiest assumption per concept | `modes/inventor.md` Evaluating concepts; `references/feasibility-scale.md` |
| Novelty compared with prior art; no overclaiming | `modes/inventor.md` Honesty rules |
| Owner checkpoint and pre-set prototype criteria | `workflows/invention.md` Stages and owner checkpoints; `modes/inventor.md` Prototyping |

### S7. Ambiguous request: covered

| Criterion | Where the skill produces it |
|---|---|
| Inspects before asking | `core/clarification-protocol.md` decision rule (condition 2) and the authentication example |
| Only design-changing questions, at most three, with defaults | `core/clarification-protocol.md` Asking well |
| Asks nothing the code answers | `core/clarification-protocol.md` "Never ask about information you can read"; over-asking example |
| Continues with safe work and states assumptions | `core/clarification-protocol.md` Asking well (keep moving), Proceeding on assumptions |
| Authentication handled as a sensitive change | `workflows/sensitive-change.md` What counts as sensitive |

### S8. Unavailable tools: covered

| Criterion | Where the skill produces it |
|---|---|
| Names the missing capability and its impact | `systems/tool-availability.md` Communicating limitations; `SKILL.md` Tools and environment |
| Best available alternative, labeled | `systems/tool-availability.md` When a tool is missing; `modes/researcher.md` Working without web access |
| Unverified label and exact commands | `modes/engineer.md` When code cannot be executed; `standards/testing-strategy.md` Special situations |
| No simulated output presented as real | `systems/tool-availability.md` rules; `standards/transparency-and-reporting.md` Prohibited reporting |

### S9. Security-sensitive change: covered

| Criterion | Where the skill produces it |
|---|---|
| Classification of the change | `workflows/sensitive-change.md` step 1 |
| Threat model | `workflows/sensitive-change.md` step 2 |
| Least privilege and denied-access tests | `workflows/sensitive-change.md` steps 5 and 6; `standards/security.md` Application security rules |
| No production action without approval; approval request with safeguards | `workflows/sensitive-change.md` steps 3, 4, 7, 8 and the request format; `systems/autonomy-and-approval.md` Ask first |
| Regulatory implications raised | `workflows/sensitive-change.md` step 1 (after F4); `standards/security.md` Data protection |

### S10. Continuing project: covered

| Criterion | Where the skill produces it |
|---|---|
| Reads memory sources in order, with the scan script | `workflows/continuing-project.md` step 1; `scripts/scan-project.py` finds instruction files, decision records and task ledgers (exercised by `tests/test_scan_project.py`) |
| Accurate state, checked against reality | `workflows/continuing-project.md` steps 2 and 3 |
| Continues the in-progress task | `workflows/continuing-project.md` step 4; Pitfalls |
| Follows recorded decisions | `workflows/continuing-project.md` step 5; `systems/decision-records.md` Using records when continuing work |
| Updates existing sources, no parallel notes | `workflows/continuing-project.md` step 6 and Pitfalls; `systems/project-memory.md` Rules |

## Automated checks

Run on 2026-11-01 in the build environment (Linux, Python 3.13.18, PyYAML 6.0.3 present):

| Check | Command | Result |
|---|---|---|
| Skill validation, strict | `python3 mych-plugin/scripts/validate-skill.py --strict` | Passed: 0 errors, 0 warnings, 50 files; frontmatter cross-checked with PyYAML |
| Skill validation without PyYAML | validator run with PyYAML import blocked | Passed with the built-in parser |
| Unit tests | `python3 -m unittest discover -s tests` | 83 tests passed |
| Unit tests without PyYAML | same suite with PyYAML import blocked | 82 passed, 1 skipped (the PyYAML agreement test) |
| Python 3.8 compatibility | `ast.parse(..., feature_version=(3, 8))` on every script and test | Grammar compatible; not executed on a 3.8 interpreter |
| Packaging and archive verification | `python3 mych-plugin/scripts/package-skill.py` | `dist/mych-plugin-1.0.0.zip` built, reopened and verified against the source |

## Residual risks

- **Behavior is unmeasured.** The skill's instructions are traced, not tested in live runs. Run the live protocol before relying on the skill for important work.
- **Activation breadth.** The description covers most technical work by design. It may load for tasks where it adds little; `SKILL.md` is the context cost each time.
- **Model differences.** Smaller models may need more explicit guidance than the current text gives; test with each model the owner plans to use.
- **Environment dependence.** Claude Design, web access and code execution vary by surface; the skill handles their absence but cannot supply them.
