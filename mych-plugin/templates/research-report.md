# Template: Research Report

The Researcher's deliverable: conclusion first, then the evidence that supports it, with uncertainty made explicit. Method: [researcher.md](../modes/researcher.md); source standards: [source-evaluation.md](../references/source-evaluation.md).

## How to fill it

- Write the conclusion last, place it first.
- Label each claim: Fact (sourced or observed), Inference (reasoning shown), Hypothesis (untested) or Unknown.
- List only sources you opened in this session, with version and date. Training knowledge goes under "Background", flagged as possibly outdated.
- If web access was unavailable, say so in "Method".

## Template

```markdown
# Research: [question in plain words]

Date: [YYYY-MM-DD] | Depth: [quick check, standard, deep] | Confidence: [high, medium, low]

## Conclusion
[Two to four sentences answering the question directly. For comparisons: "For these requirements, [option] fits better because [reasons]."]

## Recommendation
[What to do, and the conditions that would change the recommendation.]

## Question and decision
- Question: [precise research question]
- Decision it informs: [decision]
- Context: [system, scale, versions in use]
- Criteria and weights: [criterion (weight), ...]
- Constraints: [...]

## Method
[Sources consulted, experiments run, tools available or unavailable.]

## Findings
| Claim | Label | Source, version, date |
|---|---|---|
| [claim] | [Fact, Inference, Hypothesis, Unknown] | [source] |

## Comparison (when comparing options)
| Criterion (weight) | [Option A] | [Option B] | [Option C] |
|---|---|---|---|
| [criterion] | [assessment with evidence] | [...] | [...] |
[Explain the matrix in words; note where the options are close.]

## Contradictions and how they were resolved
- [Conflicting claims, the explanation (version, configuration, method), or why it remains open]

## Open questions
- [Question]: [what would resolve it]

## Background (not verified in this session)
- [Training knowledge relevant to the topic, flagged as possibly outdated, with the official source to check]

## Sources
1. [Title], [publisher or author], [version if applicable], [date published or updated], [link], accessed [date]
```
