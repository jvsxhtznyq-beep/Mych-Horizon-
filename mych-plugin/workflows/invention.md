# Invention Workflow

For original ideas, completely new technology, experimental systems and prototypes. The combination is Researcher, Inventor, Architect and Engineer, with the Inventor leading. The output is a set of distinct concepts, honestly rated, and evidence from the smallest experiment that could prove the leading concept wrong. Method details: [inventor.md](../modes/inventor.md).

## Stages and owner checkpoints

| Stage | Lead | Output | Checkpoint |
|---|---|---|---|
| 1. Frame | Inventor | Job, hard part, shared assumptions, why now | |
| 2. Map prior art | Researcher | Existing approaches with limitations and evidence | |
| 3. Diverge | Inventor | Three to five concepts that differ in mechanism | |
| 4. Converge | Inventor with Architect | Evaluation of each concept: value, feasibility, novelty, resources, risk, time to signal | **Owner chooses a direction** |
| 5. Shape | Architect | System sketch of the chosen concept and its riskiest assumption | |
| 6. Plan the prototype | Inventor with Engineer | Experiment design with success and kill criteria | **Owner authorizes the build** |
| 7. Prototype | Engineer | Throwaway prototype aimed at the riskiest assumption | |
| 8. Evaluate | Inventor | Results against the pre-set criteria | |
| 9. Recommend | Inventor | Proceed, pivot or stop, with the next stage's cost and goal | |

When the owner cannot be asked, continue past checkpoint 4 with the concept that has the best ratio of value to time-to-signal, and stop at checkpoint 6 with the prototype plan unless prototyping was already authorized.

## Stage notes

- **Frame:** the shared assumptions are the most productive place to invent. List them explicitly.
- **Map prior art:** search products, open-source projects, papers and, where relevant, patents. Record what exists so novelty claims can be checked.
- **Diverge:** use at least three generation techniques from [inventor.md](../modes/inventor.md#generating-distinct-concepts). Apply the distinctness check; merge reskinned duplicates.
- **Converge:** rate feasibility with [feasibility-scale.md](../references/feasibility-scale.md). Keep speculative concepts in the set, clearly labeled, when they could inform the direction.
- **Shape:** the Architect identifies what the concept needs from the system: data, compute, interfaces, integration points, failure modes.
- **Plan the prototype:** one riskiest assumption, one experiment, criteria with numbers written down before any code.
- **Prototype:** label it as a prototype; keep it out of production code paths; record environment and conditions.
- **Evaluate:** compare results against the pre-set criteria without moving them. Report negative results as plainly as positive ones.

## Deliverables

- [invention-concept.md](../templates/invention-concept.md) covering the frame, prior art, concept set, evaluation and the chosen direction.
- The prototype (when authorized) with instructions to run it.
- An evaluation of results and a next-stage recommendation with cost and duration ranges.

## Verification

- [ ] Every novelty claim names what is new relative to the mapped prior art.
- [ ] Every concept carries a feasibility level with a reason.
- [ ] Prototype criteria predate the prototype.
- [ ] Reported results include conditions and match what was actually run.

## Pitfalls

- Building the first idea before generating alternatives.
- Prototypes that demonstrate the easy part.
- Calling an idea a breakthrough without a prior-art comparison.
- Moving the success criteria after seeing results.
