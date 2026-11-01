# Palettes

How to choose, build and enforce a palette. A palette is a project decision: record it, validate against it, and change it deliberately.

## Building ramps

- A **ramp** is a sequence of colors from shadow to highlight for one material (skin, foliage, stone).
- Shift **hue** along the ramp, not only value: shadows toward cool hues (blue, purple), highlights toward warm hues (yellow, orange). Pure value ramps look muddy.
- Lower saturation at both ends (deep shadows and bright highlights), keep it highest in the midtones.
- Share colors between ramps (the darkest shadow can serve several materials) to keep the palette small.
- Aim for clear **value steps**: neighbors in a ramp should be distinguishable in grayscale.

## Size guidance

| Palette size | Typical use |
|---|---|
| 4 colors | Handheld-style monochrome looks, strict retro constraints |
| 8 to 16 colors | Small games, strong cohesive style, jam projects |
| 24 to 32 colors | Most indie games with several environments |
| 48 or more | Painterly styles; harder to keep cohesive |

## Built-in palettes

`pixel_tool.py palette list` shows them; `palette show NAME` prints them with the hex digit each maps to when a sprite says `palette: use NAME`.

| Name | Colors | Source |
|---|---|---|
| `pico8` | 16 | PICO-8 fantasy console palette (Lexaloffle) |
| `sweetie16` | 16 | Sweetie 16 by GrafxKid, published on Lospec |
| `gameboy` | 4 | Greens commonly used to imitate the original Game Boy screen |
| `grayscale4` | 4 | Evenly spaced grays |

Credit palette authors in the project's credits when a community palette is used.

## Custom palettes

- Store the palette in the repository as a GIMP `.gpl` file or a text file of `#rrggbb` values; `validate --palette FILE` reads both.
- Extract the palette of existing art with `palette extract FILE --format gpl`, then prune near-duplicates.

## Palette swaps

Recolor variants (enemy tiers, team colors) by mapping one ramp to another of the same length. Keep ramp lengths equal so swaps are one-to-one.

## Accessibility

- Do not distinguish gameplay-critical objects by hue alone (red versus green is the most common confusion). Add value contrast, shape or animation differences.
- Keep important foreground objects at a clearly different value from the background.
- Test screenshots with a color-vision-deficiency simulator when one is available, and say so in the report when it is not.
