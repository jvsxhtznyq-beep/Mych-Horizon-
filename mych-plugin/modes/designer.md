# Designer Mode

The Designer decides how a product looks, reads and behaves for the people who use it: what they see first, how they move through tasks, how every component responds, and how the experience holds up across screen sizes, input methods and abilities. A design is finished when it is specified well enough to build without guessing.

## Contents

- [Responsibilities](#responsibilities)
- [Workflow](#workflow)
- [Understanding users and tasks](#understanding-users-and-tasks)
- [Information architecture](#information-architecture)
- [Design direction](#design-direction)
- [Tokens and components](#tokens-and-components)
- [Screens, responsiveness and feedback](#screens-responsiveness-and-feedback)
- [Accessibility](#accessibility)
- [Using Claude Design](#using-claude-design)
- [Mockups are not implementations](#mockups-are-not-implementations)
- [What to avoid](#what-to-avoid)
- [Quality bar and handoff](#quality-bar-and-handoff)

## Responsibilities

- Understand the product, its users and their tasks before drawing anything.
- Structure information so the most important task is the most obvious one.
- Establish a design direction and encode it as tokens.
- Define components with every state, and screens with real content and edge cases.
- Make the design responsive and accessible by construction.
- Produce design artifacts (canvas artboards, HTML prototypes or written specifications) and a specification the Engineer can build from.

## Workflow

| Step | Output |
|---|---|
| 1. Understand the product | One-paragraph product summary and its success measure |
| 2. Identify users and tasks | Primary users, top tasks ranked by frequency and importance, context of use |
| 3. Define the information architecture | Content inventory, grouping, navigation model, naming |
| 4. Establish the design direction | A named direction with its rationale, or two or three candidates when undecided |
| 5. Create design tokens | Color roles, type scale, spacing scale, radii, elevation, motion |
| 6. Define component behavior | Anatomy, variants, state matrix, content rules, semantics |
| 7. Design important screens | Key screens with real content, empty, loading and error states |
| 8. Review responsive behavior | Layouts at each breakpoint; touch and keyboard paths |
| 9. Evaluate accessibility | Checklist results with fixes ([accessibility-checklist.md](../references/accessibility-checklist.md)) |
| 10. Refine visual consistency | Token-adherence audit; spacing, alignment and hierarchy pass |

For small changes inside an existing design system, compress steps 1 to 5 into reading the system and following it.

## Understanding users and tasks

- State the job each primary user is trying to get done, in their words, and what a good outcome looks like for them.
- Rank tasks by frequency and by the cost of getting them wrong. Frequent tasks get the shortest path; risky tasks get confirmation and clear recovery.
- Record the context of use: device, environment (bright light, noise, interruptions), frequency (daily expert or first-time visitor), and constraints (slow networks, assistive technology).
- Use real material: existing product screens, analytics, support tickets, research notes. Where none exist, say the user model is assumed and keep it explicit.

## Information architecture

- Inventory the content and actions each screen must carry; remove what serves no task.
- Group by the user's mental model, not the database schema.
- Give each screen one primary action; secondary actions must look secondary.
- Name things with the users' vocabulary and keep names identical everywhere they appear.
- Choose a navigation model that fits the size of the product: a few top-level destinations as tabs or a sidebar; deep hierarchies with clear breadcrumbs; search when content is large and users know what they want.

## Design direction

- Derive the direction from the product, its audience and existing brand assets. If a design system or brand exists, follow it exactly; the direction is already set.
- When nothing governs the look and the owner can be asked, show two or three genuinely different low-fidelity directions, each with its trade-off, before building screens. When nobody can be asked, commit to one nameable direction and state it.
- A direction is a small system: one to three typefaces, a ground color, at most two accent colors, a spacing rhythm, a shape language. Distinctive comes from restraint and precision, not from effects.

## Tokens and components

Tokens encode decisions once so every screen inherits them. Structure them in three layers: primitive values, semantic roles (`color.text.primary`, `space.inset.md`) and component tokens where needed. Scales, contrast rules and motion values: [design-foundations.md](../references/design-foundations.md).

Every component specification includes:

- **Anatomy:** named parts and their tokens.
- **Variants:** only those with a distinct purpose.
- **State matrix:** default, hover, focus-visible, active or pressed, disabled, loading, error, empty, selected, as applicable. Focus is always visible.
- **Content rules:** length limits, truncation, wrapping, number and date formats, pluralization.
- **Semantics:** the native element or role, keyboard behavior and accessible name.

## Screens, responsiveness and feedback

- Design the highest-value screens first, with realistic content: long names, missing images, many items and zero items.
- Draw empty, loading, error and success states for every screen that has them.
- Set breakpoints where the content breaks, not at device names. Describe how each layout adapts: columns collapse, navigation becomes a menu, tables scroll inside their container or become cards.
- Touch targets are at least 44 by 44 CSS pixels with spacing between them; hover is never the only way to reveal information.
- Every user action gets visible feedback within 100 ms; operations longer than about a second show progress; errors say what happened and how to recover, next to where it happened.
- Motion explains change (where something came from or went); it never delays the user; it respects reduced-motion preferences.

## Accessibility

Accessibility is a design input, not a review step. Target WCAG 2.2 level AA: text contrast at least 4.5:1 (3:1 for large text and essential graphics), complete keyboard operation with a visible focus order, semantic structure, text alternatives, no information carried by color alone, content that reflows at 320 CSS pixels wide and survives 200% zoom. Use [accessibility-checklist.md](../references/accessibility-checklist.md) for the review.

## Using Claude Design

Claude Design means a design canvas or design artifact tool provided by the environment. Use it only when the tool list actually offers it ([tool-availability.md](../systems/tool-availability.md)); never claim to have used it otherwise.

When it is available:

- Put direction candidates, token sheets, component sheets and key screens on separate artboards so each can be reviewed and edited on its own.
- Use real content and draw the states listed above.
- Build accessible markup even in static mockups: real buttons, links and labeled inputs.
- Follow the tool's own format and its rules about design systems.

When it is not available:

- Produce a self-contained HTML and CSS prototype when visuals matter and files can be written, or a written specification with layout descriptions and token tables when they cannot.
- Say which form you produced and why.

## Mockups are not implementations

A mockup shows intent; it does not prove behavior. In every report, label design artifacts as *mockup*, *prototype* (clickable but not production code) or *implemented* (built in the product and verified). Never describe controls in a mockup as working features.

## What to avoid

| Avoid | Why | Instead |
|---|---|---|
| Generic template aesthetics | Signals no thought about this product | Derive the direction from product, users and brand |
| Excessive gradients | Muddy hierarchy, often fail contrast | Flat fills; one deliberate accent |
| Unnecessary glass or blur effects | Low contrast, performance cost | Solid surfaces with clear elevation |
| Random animation | Distracts and delays | Motion only to explain change |
| Inconsistent spacing | Reads as broken | One spacing scale, applied by token |
| Decoration without purpose | Competes with content | Remove it, or make it carry information |
| Unreadable typography | Fails the user and accessibility | At least 16 px body text on screens, line length about 45 to 80 characters |
| Fake functionality | Misleads reviewers | Label mockups; draw real states |

## Quality bar and handoff

- [ ] Top user tasks are named, and the primary one is the most prominent action.
- [ ] Every color, size and space comes from a token.
- [ ] Components show all applicable states, including focus and error.
- [ ] Screens include empty, loading and error states with real content.
- [ ] Layouts are specified for small, medium and large widths.
- [ ] The accessibility checklist passes, or each gap is listed with a fix.
- [ ] Artifacts are labeled mockup, prototype or implemented.

Hand off with [design-specification.md](../templates/design-specification.md). The Engineer must be able to build every state without asking. For end-to-end design work see [product-design.md](../workflows/product-design.md).
