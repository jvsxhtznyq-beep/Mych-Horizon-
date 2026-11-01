# Accessibility Checklist

A review checklist oriented to WCAG 2.2 level AA, organized by the four principles, with the success criterion numbers for lookup in the W3C's "Understanding WCAG" documents. Use it while designing and when reviewing built interfaces. Passing an automated scanner is not the same as passing this checklist; automated tools catch only part of the issues.

## Contents

- [How to use it](#how-to-use-it)
- [Perceivable](#perceivable)
- [Operable](#operable)
- [Understandable](#understandable)
- [Robust](#robust)
- [Testing methods](#testing-methods)
- [Reporting results](#reporting-results)

## How to use it

1. Run it per screen or component, not once per product.
2. Record each item as pass, fail (with location and fix) or not applicable.
3. Compute contrast ratios ([design-foundations.md](design-foundations.md#color-and-contrast)); never eyeball them.
4. For built interfaces, combine an automated scan with the manual methods below.

## Perceivable

- [ ] **Text alternatives (1.1.1):** meaningful images have concise alt text; decorative images are hidden from assistive technology; icon-only buttons have accessible names.
- [ ] **Media (1.2.1, 1.2.2, 1.2.4, 1.2.5):** prerecorded video has captions and audio description where needed; live video has captions; audio-only content has a transcript.
- [ ] **Structure (1.3.1, 1.3.2):** headings, lists, tables, landmarks and form labels are expressed in markup, not only visually; reading order matches visual order.
- [ ] **Sensory characteristics (1.3.3):** instructions do not depend only on shape, position, color or sound ("press the round button on the right").
- [ ] **Orientation (1.3.4):** content works in portrait and landscape unless a specific orientation is essential.
- [ ] **Input purpose (1.3.5):** personal-data fields declare their purpose (for example `autocomplete` attributes).
- [ ] **Use of color (1.4.1):** color is never the only way to convey information, state or required action.
- [ ] **Contrast (1.4.3):** text at least 4.5:1; large text at least 3:1.
- [ ] **Resize and reflow (1.4.4, 1.4.10):** usable at 200% zoom; content reflows at 320 CSS px wide without two-dimensional scrolling, except content that inherently needs it.
- [ ] **Images of text (1.4.5):** real text instead of text in images, except logos.
- [ ] **Non-text contrast (1.4.11):** input borders, icons, focus indicators and meaningful graphics at least 3:1 against adjacent colors.
- [ ] **Text spacing (1.4.12):** no loss of content when users increase line height, paragraph, letter and word spacing.
- [ ] **Hover and focus content (1.4.13):** tooltips and popovers can be dismissed, can be hovered, and stay until dismissed.

## Operable

- [ ] **Keyboard (2.1.1, 2.1.2):** every function works with a keyboard alone; no keyboard traps.
- [ ] **Character key shortcuts (2.1.4):** single-key shortcuts can be turned off or remapped, or are active only on focus.
- [ ] **Timing (2.2.1, 2.2.2):** time limits can be extended or turned off; moving or auto-updating content can be paused, stopped or hidden.
- [ ] **Flashing (2.3.1):** nothing flashes more than three times per second.
- [ ] **Bypass blocks (2.4.1):** a skip link or landmarks let users bypass repeated navigation.
- [ ] **Page titles (2.4.2):** each page or view has a descriptive title.
- [ ] **Focus order (2.4.3):** focus moves in a logical order; dialogs move focus in and return it on close.
- [ ] **Link purpose (2.4.4):** link text, with its context, says where it goes ("Read the pricing guide", not "Click here").
- [ ] **Multiple ways (2.4.5):** pages can be found more than one way (navigation, search, site map), except steps in a process.
- [ ] **Headings and labels (2.4.6):** headings and labels describe topic or purpose.
- [ ] **Focus visible (2.4.7):** keyboard focus is always visible.
- [ ] **Focus not obscured (2.4.11):** the focused element is not entirely hidden by sticky headers, banners or overlays.
- [ ] **Pointer gestures and cancellation (2.5.1, 2.5.2):** multi-point or path gestures have single-pointer alternatives; actions fire on release and can be aborted.
- [ ] **Label in name (2.5.3):** the accessible name contains the visible label text.
- [ ] **Motion actuation (2.5.4):** functions triggered by device motion have an interface alternative and can be disabled.
- [ ] **Dragging (2.5.7):** anything done by dragging can also be done with single clicks or taps.
- [ ] **Target size (2.5.8):** targets at least 24 by 24 CSS px, or with enough spacing. MYCH-HORIZON's design standard recommends 44 by 44 px for touch interfaces.

## Understandable

- [ ] **Language (3.1.1, 3.1.2):** the page language is declared; passages in other languages are marked.
- [ ] **Predictable focus and input (3.2.1, 3.2.2):** receiving focus or changing a value does not trigger unexpected context changes.
- [ ] **Consistency (3.2.3, 3.2.4):** navigation appears in the same place; components with the same function have the same names and icons.
- [ ] **Consistent help (3.2.6):** help mechanisms (contact, chat, help links) appear in the same relative place across pages.
- [ ] **Errors (3.3.1, 3.3.3):** errors are identified in text, next to the field, with a suggestion for fixing them when known.
- [ ] **Labels and instructions (3.3.2):** inputs have visible labels; required formats are stated up front.
- [ ] **Error prevention (3.3.4):** legal, financial and data-changing submissions can be reviewed, corrected or reversed.
- [ ] **Redundant entry (3.3.7):** information already provided in a process is not requested again, or is pre-filled.
- [ ] **Accessible authentication (3.3.8):** login does not require a cognitive function test (memorizing, transcribing, solving puzzles) without an alternative; password managers and paste work.

## Robust

- [ ] **Name, role, value (4.1.2):** custom controls expose name, role and state to assistive technology; native elements are used wherever possible (a real `button`, `a href`, `input` with `label`).
- [ ] **Status messages (4.1.3):** results, errors and progress that appear without a focus change are announced (live regions).

## Testing methods

| Method | What it finds |
|---|---|
| Keyboard walk: Tab, Shift+Tab, Enter, Space, Escape, arrow keys through every top task | Unreachable controls, traps, invisible or obscured focus, illogical order |
| Screen reader smoke test (for example VoiceOver or NVDA) on top tasks | Missing names and roles, unannounced status changes, confusing reading order |
| Zoom to 200% and resize to 320 px wide | Clipped text, overlapping content, horizontal scrolling |
| Contrast computation for every text and component color pair | Insufficient contrast |
| Reduced-motion and high-contrast settings | Motion that ignores preferences, invisible boundaries |
| Automated scanner (for example axe or Lighthouse) | Machine-detectable issues only; never sufficient on its own |

When a method cannot be run in the current environment (no browser, no screen reader), say so and list it as not assessed.

## Reporting results

| Item | Result | Location | Fix |
|---|---|---|---|
| Focus visible (2.4.7) | Fail | Date picker day cells | Add a 2 px focus ring using `color.focus` |
| Contrast (1.4.3) | Pass | All text tokens | Ratios: primary 15.8:1, secondary 6.8:1 |
