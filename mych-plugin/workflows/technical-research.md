# Technical Research Workflow

For research, comparison and feasibility questions where the deliverable is a conclusion. The Researcher leads; the Architect joins when the answer depends on fit with a system's architecture. Method details: [researcher.md](../modes/researcher.md).

## Choose the depth

| Depth | Use when | Evidence required |
|---|---|---|
| Quick check | One factual question, low stakes, reversible | One authoritative source for the relevant version |
| Standard | A decision with moderate cost of being wrong; a comparison | Official documentation plus independent confirmation for key claims |
| Deep | Irreversible, expensive or contested decisions; performance-critical choices | Triangulated sources plus a reproducible experiment where possible |

State the chosen depth at the start so the owner can ask for more or less.

## Steps

1. **Frame.** Write the research question with context, options, criteria, constraints and the decision it informs. Agree criteria weights before gathering evidence.
2. **Check tools.** Confirm whether web search and fetching are available ([tool-availability.md](../systems/tool-availability.md)). If not, say so and use local evidence and training knowledge with caveats.
3. **Plan sources.** List the authoritative sources per option: official docs, specifications, changelogs, source code, maintainers' statements ([source-evaluation.md](../references/source-evaluation.md)).
4. **Gather.** Read the sources; record claim, source, version, date and label (fact, inference, hypothesis, unknown) as you go.
5. **Evaluate.** Resolve contradictions by version, configuration or method; scrutinize benchmarks; run an experiment for deep research when tools allow.
6. **Synthesize.** Answer the question directly. For comparisons, build the decision matrix and explain it in words.
7. **Recommend.** For the stated requirements, with the conditions that would change the recommendation. Never declare an unconditional winner.
8. **Report.** Use [research-report.md](../templates/research-report.md): conclusion first, then evidence, confidence, open questions, sources.

## Verification

Before delivering, check:

- [ ] Every important claim has a source opened in this session, with version and date, or carries a label other than fact.
- [ ] No citation, quote, number or version was invented or recalled from memory as if verified.
- [ ] Contradictions are explained or reported.
- [ ] Confidence levels match the evidence.
- [ ] The recommendation follows from the stated criteria.
- [ ] Open questions say how they could be resolved.

## Pitfalls

- Answering from memory when the version in use may differ.
- Letting the first source frame the whole answer.
- Reporting a vendor benchmark as neutral evidence.
- Burying the conclusion under the evidence.
- Researching beyond the decision: stop when the decision is supported at the needed confidence.
