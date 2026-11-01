# Design specification: staff day view

Date: 2026-11-01 | Status: prototype for review (static HTML; not implemented in the app)

## Users and top tasks
| User | Task | Frequency | Cost of error | Context |
|---|---|---|---|---|
| Front-desk staff | See who is next | Constantly | Medium | Phone, standing, interrupted |
| Front-desk staff | Book a free slot for a caller or walk-in | Many times a day | Medium | Phone |
| Office staff | Cancel or review the day | Daily | High (cancelling the wrong patient) | Desktop |
| Any staff | Move between days | Daily | Low | Both |

The user model is assumed (no research material was provided).

## Information architecture and direction
One screen: date header with previous, today and next; a "Next patient" summary; the day as a list of 30-minute slots. Direction: "front-desk ledger", calm neutral surfaces, one accent for the primary action, status always in words, never color alone.

## Tokens
| Token | Value | Check |
|---|---|---|
| color.text / bg | #1b1f24 on #ffffff | Body text |
| color.text-secondary | #4a5461 | Meta text on white and on the free-slot tint |
| color.accent / on-accent | #1f5fbf / #ffffff | Lowest measured text contrast on the page: 6.09:1 (Book button) |
| color.danger-text | #a3271f | Cancel text |
| space | 4, 8, 12, 16, 24 | |
| radius | 6 px | |
| type | system UI, 16 px body, 14 px meta, 20 px title | |

## Components and states
- Slot row: time, who (patient, or "Free" plus the reason if freed by a cancellation), one action. Booked rows: Cancel (quiet, danger text). Free rows: Book (primary).
- Buttons: default, focus-visible (2 px accent outline), at least 44 by 44 px.
- Screen states: populated, empty ("No appointments on this day" + "Book the first slot"), loading (`aria-busy`), error (`role="alert"`, reassurance, "Try again").
- Content: long names wrap; accessible names give context ("Cancel Ada Lindqvist at 09:00").

## Responsive
Below 600 px: "Next patient" first, then the day; action buttons full width under each row. From 600 px: list left, summary panel right; header spans the width.

## Accessibility results (measured by `design/verify-day-view.js`, Playwright with Chromium)
| Check | 320 px | 390 px | 1280 px |
|---|---|---|---|
| Horizontal overflow | none | none | none |
| Buttons under 44 px | none | none | none |
| Lowest text contrast | 6.09:1 | 6.09:1 | 6.09:1 |
| First heading is h1 | yes | yes | yes |

Keyboard order: previous day, today, next day, then each slot's action in time order. Not tested: screen reader output (no screen reader in this environment), reduced-motion (no motion used).

## Open issues
- Cancelling is one tap on phones: add a confirmation step naming the patient and time before release.
- The counts line and summary use static numbers; real data must drive them.

## Artifacts
| Artifact | Type | Location |
|---|---|---|
| Day view | Prototype (static HTML) | `design/staff-day-view.html` |
| Screenshots | Evidence | `design/day-view-320.png`, `day-view-390.png`, `day-view-1280.png` |
