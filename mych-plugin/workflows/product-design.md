# Product Design Workflow

For designing a product or interface (Track A) and for redesigning an existing one (Track B). The Designer leads. Track B is the "complete product redesign" combination: Researcher, Designer, Architect and Engineer. Method details: [designer.md](../modes/designer.md).

## Contents

- [Track A: new product or interface](#track-a-new-product-or-interface)
- [Track B: redesign of an existing product](#track-b-redesign-of-an-existing-product)
- [Using a design canvas](#using-a-design-canvas)
- [Verification](#verification)
- [Pitfalls](#pitfalls)

## Track A: new product or interface

1. **Product and users.** Summarize the product, its primary users, their top tasks and context of use. Use the owner's material; label assumed user models as assumptions.
2. **Information architecture.** Inventory content and actions; group them; choose the navigation model; name things in the users' vocabulary.
3. **Direction.** If a brand or design system exists, adopt it. Otherwise show two or three distinct low-fidelity directions with trade-offs when the owner can choose, or commit to one named direction when nobody can be asked.
4. **Tokens.** Define color roles, type scale, spacing scale, radii, elevation and motion ([design-foundations.md](../references/design-foundations.md)).
5. **Components.** Specify anatomy, variants, the full state matrix, content rules and semantics.
6. **Key screens.** Highest-value tasks first, with real content and empty, loading, error and success states.
7. **Responsive review.** Layout at small, medium and large widths; touch targets; keyboard paths.
8. **Accessibility review.** Run [accessibility-checklist.md](../references/accessibility-checklist.md); fix or list every gap.
9. **Consistency pass.** Audit token use, spacing rhythm, alignment and type hierarchy across screens.
10. **Handoff.** Complete [design-specification.md](../templates/design-specification.md). If the Engineer builds it, review the implementation against the specification.

## Track B: redesign of an existing product

1. **Audit (Researcher with Designer).** Walk the current product's top tasks; run a heuristic evaluation; collect evidence such as analytics, support tickets and user feedback when the owner can provide them. Record each problem with its evidence and severity.
2. **Decide what to keep.** Identify what works and what users rely on (learned layouts, shortcuts, terminology). Redesigns that discard working patterns create new problems.
3. **Set redesign goals** tied to the audited problems ("reduce the steps to reorder from five to two"), not to taste.
4. **Redesign** using Track A steps 2 to 9, constrained by the keep list.
5. **Assess impact (Architect).** What the redesign changes underneath: new data needs, API changes, performance implications, migration of user settings or content.
6. **Plan the transition.** Prefer incremental rollout (feature flags, screen by screen, opt-in previews) over a single switch. Plan how users are told about changes.
7. **Build (Engineer)** against the specification, slice by slice.
8. **Measure** against the redesign goals after release, when measurement is available; otherwise define how the owner can measure.

## Using a design canvas

When the host provides a design canvas (for example Claude Design; see [tool-availability.md](../systems/tool-availability.md)) and the owner will review artboards: one artboard per direction candidate, token sheet, component sheet and key screen, so each can be reviewed separately. When it does not: an HTML and CSS prototype or a written specification, with the format stated in the report. Label every artifact as mockup, prototype or implemented.

## Verification

- **Task walkthrough:** for each top task, step through the design and count steps, decisions and possible errors.
- **State coverage:** every component and screen shows all applicable states.
- **Responsive check:** each key screen at small, medium and large widths.
- **Accessibility:** checklist results with contrast ratios computed, not guessed.
- **Consistency:** no values outside the token set.
- **Implementation (when built):** compare the built screens against the specification; run end-to-end tests for top tasks; check keyboard and screen reader paths.

## Pitfalls

- Starting from visuals instead of users and tasks.
- Designing only the happy path.
- A redesign that answers taste instead of evidence.
- Changing everything at once, so users lose what they had learned.
- Presenting a mockup as if it were the product.
