# Design Foundations

Reference values and rules for design tokens, typography, color and contrast, spacing, motion, layout and component states. Use them when no brand or design system governs; when one does, its values win. Method: [designer.md](../modes/designer.md).

## Contents

- [Token architecture](#token-architecture)
- [Spacing](#spacing)
- [Typography](#typography)
- [Color and contrast](#color-and-contrast)
- [Dark themes](#dark-themes)
- [Shape and elevation](#shape-and-elevation)
- [Motion](#motion)
- [Layout and breakpoints](#layout-and-breakpoints)
- [Iconography](#iconography)
- [Component state matrix](#component-state-matrix)
- [Content and microcopy](#content-and-microcopy)

## Token architecture

Three layers, each referencing the one below:

| Layer | Purpose | Example |
|---|---|---|
| Primitive | The raw palette and scales | `blue.600 = #2D5BC9`, `space.4 = 16px` |
| Semantic | Meaning in the interface | `color.accent = blue.600`, `space.inset.md = space.4` |
| Component | Optional, for component-specific decisions | `button.primary.background = color.accent` |

Components reference semantic tokens, never primitives directly, so a theme change touches one layer. Name tokens by role (`color.text.secondary`), not by appearance (`color.gray-dark`).

## Spacing

- Base unit 4 px. A practical scale: 0, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96.
- Related items sit closer together than unrelated ones; spacing expresses grouping.
- Use larger steps between sections than within them; keep one rhythm per surface.
- Lay out sibling groups with gap-based layouts (flex or grid gap) rather than per-element margins.

## Typography

- One or two families, at most three, each with a system fallback of similar metrics.
- Body text at least 16 px on screens; small text no smaller than 12 px, and only for secondary information.
- A modular scale with a ratio around 1.2 to 1.25 gives enough contrast between levels. Example: 12, 14, 16, 18, 20, 24, 30, 36, 48, 60.
- Line height: about 1.4 to 1.6 for body text; 1.1 to 1.3 for headings.
- Line length: about 45 to 80 characters for running text.
- Limit visible hierarchy to three or four distinct text styles per screen; more reads as noise.
- Use weight and size for hierarchy before color; never rely on color alone.

## Color and contrast

Semantic roles to define: background, surface (and raised surface), text primary, text secondary, border, accent, accent text, focus ring, success, warning, danger, info.

Contrast requirements (WCAG 2.2 AA):

| Element | Minimum ratio |
|---|---|
| Body and small text | 4.5:1 |
| Large text (at least 24 px regular, or 18.66 px bold) | 3:1 |
| Interface components and meaningful graphics (borders of inputs, icons, focus indicators) | 3:1 against adjacent colors |

Compute contrast rather than estimating it:

1. Convert each sRGB channel `c` (0 to 255) to `s = c / 255`, then to linear: `s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ^ 2.4`.
2. Relative luminance `L = 0.2126 R + 0.7152 G + 0.0722 B` of the linear values.
3. Contrast ratio `(L1 + 0.05) / (L2 + 0.05)`, with `L1` the lighter color.

Rules of thumb: grey caption text and white text on colored buttons fail most often, so check them first. Colors that must be told apart should differ in lightness as well as hue; blue and orange separate better than red and green for people with common color vision deficiencies. Use at most two accent colors with similar lightness and chroma.

## Dark themes

- Use a very dark grey for the background rather than pure black, and off-white text rather than pure white, to reduce glare.
- Express elevation with lighter surfaces, not shadows.
- Reduce the saturation of accent colors so they do not vibrate against dark backgrounds; re-check every contrast pair.
- Provide both themes from the same semantic tokens.

## Shape and elevation

- Choose one radius family (for example 2, 4 and 8 px) and apply it consistently by component size.
- Use elevation sparingly: base, raised (cards, menus) and overlay (dialogs). Each level needs a clear purpose.

## Motion

| Use | Duration | Easing |
|---|---|---|
| Small state changes (hover, toggle) | 100 to 150 ms | Ease out |
| Standard transitions (menus, panels) | 200 to 300 ms | Ease out to enter, ease in to exit |
| Large movements (page-level) | 300 to 500 ms | Ease in and out |

- Motion explains change: where something came from, where it went, what is connected.
- Never block input while an animation runs.
- Honor reduced-motion preferences by replacing movement with simple fades or no animation.
- Avoid flashing content (more than three flashes per second).

## Layout and breakpoints

- Design small first, then add layout as space allows.
- Set breakpoints where the content breaks. Common starting points are around 640, 768, 1024 and 1280 px, but adjust to the content.
- Use a column grid with consistent gutters and margins (for example 4 columns on small screens, 8 on medium, 12 on large).
- Content must reflow at 320 CSS px wide without horizontal scrolling, except content that needs two dimensions such as data tables, which scroll inside their own container.
- Constrain reading width with a maximum container width instead of letting text span wide screens.

## Iconography

- One icon style (stroke or fill) and stroke width throughout; sizes such as 16, 20 and 24 px aligned to the type scale.
- Icons that act as buttons need an accessible name; pair icons with visible labels where meaning is not universal.
- Decorative icons are hidden from assistive technology.

## Component state matrix

Specify each state that applies:

| State | Visual change | Behavior |
|---|---|---|
| Default | Base appearance | |
| Hover | Subtle emphasis (pointer devices only) | Never the only way to reveal information |
| Focus-visible | Clear focus ring, at least 3:1 against surroundings | Keyboard focus always visible and not obscured |
| Active or pressed | Pressed appearance | Immediate feedback |
| Disabled | Reduced emphasis, still legible | Explain why when it is not obvious |
| Loading | Progress indicator; layout stays stable | Prevent duplicate submission |
| Error | Error color plus icon or text, never color alone | Message says what happened and how to fix it |
| Empty | Explanation and next action | Never a blank area |
| Selected | Distinct from hover and focus | Announced to assistive technology |

## Content and microcopy

- Use the users' vocabulary; keep each term identical everywhere it appears.
- Sentence case for interface text; buttons start with a verb that names the outcome ("Save changes", not "OK").
- Error messages: what happened, why if useful, and what to do next, in plain words, next to the problem.
- Empty states explain what will appear and offer the first action.
- No filler text in designs; where real content is missing, use clearly marked placeholders such as [Clinic name].
