# Quality Framework

Deliverables are judged on evidence, never on arbitrary scores. This framework defines ten quality dimensions, what evidence counts for each, how to run a review, and how to grade findings.

## Contents

- [Assessment statuses](#assessment-statuses)
- [The ten dimensions](#the-ten-dimensions)
- [Which dimensions apply](#which-dimensions-apply)
- [Review procedure](#review-procedure)
- [Finding severity](#finding-severity)

## Assessment statuses

Each applicable dimension gets one status:

| Status | Meaning |
|---|---|
| Met | Evidence shows the standard is met; the evidence is cited |
| Not met | Evidence shows a gap; a finding is recorded |
| Not assessed | It applies, but evidence could not be gathered; the reason is stated |
| Not applicable | It does not apply to this deliverable; one-line reason |

Never convert *not assessed* into *met* because the work "looks fine". Numeric quality scores are not used: they hide what was checked.

## The ten dimensions

| # | Dimension | Evidence that counts | Not evidence |
|---|---|---|---|
| 1 | Functional correctness | Tests and acceptance checks executed with their output; a demonstrated user task | "It should work"; code that compiles |
| 2 | Reliability | Error paths, retries, timeouts and edge cases exercised; behavior under partial failure observed | The happy path passing |
| 3 | Security | Threat review notes; tests for denied access and rejected input; diff checked for secrets; dependency advisories checked | Absence of known incidents |
| 4 | Performance | Measurements before and after under the same conditions, against a target | Intuition about speed |
| 5 | Maintainability | A focused diff that follows conventions; clear names; no dead code; linter and type checker clean | Personal style preferences |
| 6 | Usability | A walkthrough of each top task counting steps, decisions and error opportunities; feedback on every action | "Intuitive" without a walkthrough |
| 7 | Accessibility | Checklist results with computed contrast ratios; keyboard path walked; semantics inspected | Visual appearance alone |
| 8 | Documentation | Docs, comments and examples match the shipped behavior; run instructions tried | Documentation that exists but was not read against the code |
| 9 | Compatibility | Target versions, platforms or browsers checked, by test or by documented support | Testing only on the author's environment |
| 10 | Requirement compliance | Each requirement traced to evidence in the verification table | A general statement that requirements are met |

## Which dimensions apply

| Deliverable | Always | Usually | When relevant |
|---|---|---|---|
| Code change | 1, 5, 10 | 2, 3, 8 | 4, 9 |
| User interface | 1, 6, 7, 10 | 5, 8, 9 | 3, 4 |
| Architecture proposal | 2, 3, 10 | 4, 5 | 9 |
| Design specification | 6, 7, 10 | 8 | 9 |
| Research report | 10 (the question is answered) | 8 (sources cited and accurate) | 9 (versions match) |
| Invention concept or prototype | 1 (for prototypes), 10 | 2, 3 | 4 |

For research, "correctness" means claims match their sources; record it under dimension 1 when the research itself is the deliverable.

## Review procedure

1. **Select** the applicable dimensions using the table above.
2. **Gather evidence** for each: run the checks, read the diff, walk the tasks, compute the ratios, trace the requirements.
3. **Record** a status per dimension with the evidence or the reason.
4. **Log findings** for every *not met*, with severity, location and a proposed fix.
5. **Fix** blockers and majors within the task's authority; re-run the checks.
6. **Report** the remaining findings and *not assessed* items in the delivery report.

Review format:

| Dimension | Status | Evidence or reason |
|---|---|---|
| Functional correctness | Met | `npm test` 148 passed; booking flow walked end to end on the dev server |
| Accessibility | Not met | Finding A-1: date picker not keyboard operable |
| Compatibility | Not assessed | No Safari available in this environment; command for the owner listed |

## Finding severity

| Severity | Definition | Action |
|---|---|---|
| Blocker | A requirement fails, data or security is at risk, or the deliverable cannot be used | Fix before delivery, or deliver explicitly marked as not ready |
| Major | Significant degradation of a dimension; a likely user-facing problem | Fix, or obtain the owner's explicit acceptance |
| Minor | Small deviation with limited impact | Fix when cheap; otherwise list it |
| Note | An observation or improvement idea | List it briefly |
