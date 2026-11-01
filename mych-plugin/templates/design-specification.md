# Template: Design Specification

The Designer's handoff: everything the Engineer needs to build every screen and state without guessing. Method: [designer.md](../modes/designer.md); tokens and scales: [design-foundations.md](../references/design-foundations.md); review: [accessibility-checklist.md](../references/accessibility-checklist.md).

## How to fill it

- Fill sections progressively: users, tasks and information architecture before direction; tokens before components; components before screens.
- Use real content in examples, including long, empty and error cases.
- Express every value as a token; a raw value in a component specification is a gap in the token set.
- Label every artifact as mockup, prototype or implemented.

## Template

```markdown
# Design specification: [product or feature]

Date: [YYYY-MM-DD] | Status: [draft, ready for build, implemented]

## Product summary
[One paragraph: what it is, for whom, and how success is measured.]

## Users and top tasks
| User | Task | Frequency | Cost of error | Context of use |
|---|---|---|---|---|
| [user] | [task] | [daily, weekly, rare] | [low, medium, high] | [device, environment] |

## Information architecture
- Navigation model: [tabs, sidebar, hub and spoke, wizard]
- Screens and their primary action:
  - [Screen]: [primary action]
- Vocabulary: [term]: [meaning]; used consistently everywhere

## Design direction
[Named direction, rationale, and what it rules out. Reference brand or design system if one governs.]

## Tokens
Color roles:
| Token | Value (light) | Value (dark) | Use |
|---|---|---|---|
| color.text.primary | [#hex] | [#hex] | Body text |
Type scale:
| Token | Size / line height | Weight | Use |
|---|---|---|---|
| type.body | [16 / 24] | [400] | Body text |
Spacing: [scale, e.g. 4, 8, 12, 16, 24, 32, 48, 64]
Radii, elevation, motion: [values and use]

## Components
### [Component name]
- Anatomy: [parts and tokens]
- Variants: [variant: purpose]
- States:
  | State | Appearance | Behavior |
  |---|---|---|
  | Default | | |
  | Hover | | |
  | Focus-visible | | |
  | Active | | |
  | Disabled | | |
  | Loading | | |
  | Error | | |
- Content rules: [length limits, truncation, formats]
- Semantics: [element or role, keyboard behavior, accessible name]

## Screens
### [Screen name]
- Purpose and primary action: [...]
- Layout: small [...] | medium [...] | large [...]
- States: empty [...] | loading [...] | error [...] | success [...]
- Edge cases: [long names, many items, missing data, slow network]

## Responsive rules
[Breakpoints and what changes at each; touch targets; input modes.]

## Interaction and motion
[Feedback timing, transitions and their purpose, reduced-motion behavior.]

## Accessibility review
| Check | Result | Fix |
|---|---|---|
| Text contrast (computed) | [ratios] | |
| Keyboard path for top tasks | [result] | |
| Focus visible and not obscured | [result] | |

## Artifacts
| Artifact | Type: mockup, prototype or implemented | Location |
|---|---|---|
| [name] | [type] | [link or path] |

## Open questions
- [Question, options, recommendation]
```
