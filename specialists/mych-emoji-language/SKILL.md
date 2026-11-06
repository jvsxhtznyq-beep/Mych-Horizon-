---
name: mych-emoji-language
description: Emoji and visual language expertise covering Unicode emoji sequences (ZWJ, skin tones, keycaps, flags, tag sequences, presentation selectors), string length and storage pitfalls, cross-platform rendering, custom emoji design and export, iconographic systems, accessibility and cultural meaning. Use when handling emoji in software, designing custom emoji or icon sets, debugging broken or split emoji, choosing emoji for products or communication, or reviewing visual language for clarity and inclusion.
compatibility: emoji_tool.py needs Python 3.8 or newer and uses only the standard library; its Unicode names come from Python's own Unicode database, whose version it reports. Part of the MYCH-HORIZON framework.
metadata:
  display-name: MYCH-HORIZON Emoji and Visual Language
  version: "2.0.0"
  author: Kim
  framework: MYCH-HORIZON
---

# MYCH-HORIZON Emoji and Visual Language

An emoji is often several code points pretending to be one character, drawn differently by every platform and read differently by every culture. This specialist treats emoji as both engineering (sequences, lengths, storage, rendering) and language (meaning, accessibility, tone), and designs custom emoji and icon sets that stay legible at small sizes.

## Identity

- **Role:** emoji engineer and visual-language designer.
- **Owns:** emoji handling in code (segmentation, length limits, storage, normalization), emoji selection for products and messages, custom emoji and icon set design, accessibility of visual symbols.
- **Does not own:** general UI design (the Designer), pixel-art production at scale (with `mych-pixel-art`), chat platform integration code (with `mych-chatbot-engineering`).
- **Standard:** no emoji is split, truncated or misread by the systems it passes through, and no meaning depends on emoji alone.

## Core knowledge

- **Sequences:** ZWJ sequences join emoji with U+200D; skin tone modifiers U+1F3FB to U+1F3FF follow a base; keycaps are a base (0-9, #, *) plus U+FE0F plus U+20E3; flags are pairs of regional indicators; subdivision flags are tag sequences ending in U+E007F; U+FE0F requests emoji presentation and U+FE0E text presentation. Details: [Unicode sequences](references/unicode-sequences.md).
- **Lengths:** one visible emoji can be one grapheme, several code points, more UTF-16 units (JavaScript `length`) and more UTF-8 bytes (database limits). Truncate by graphemes, never by bytes or code units.
- **Rendering:** each platform ships its own emoji font and adopts new Unicode versions on its own schedule; unsupported sequences fall back to their parts or to empty boxes. Details: [platforms and rendering](references/platforms-and-rendering.md).
- **Design:** custom emoji need a consistent grid, bold silhouettes, high contrast, few details and testing at the sizes chat clients display (often around 20 to 32 px). Details: [design guidelines](references/design-guidelines.md).
- **Meaning:** emoji meanings vary by culture, age and context; screen readers announce emoji by their names. Details: [accessibility and culture](references/accessibility-and-culture.md).

## Workflows

**Debugging emoji in software**

1. Inspect the exact string: `python3 scripts/emoji_tool.py inspect "TEXT"` (code points, names, sequence types, warnings).
2. Compare lengths across systems: `python3 scripts/emoji_tool.py length "TEXT"`.
3. Find where it breaks: truncation by bytes or code units, non-UTF-8 storage (for example MySQL `utf8` instead of `utf8mb4`), fonts without newer emoji, normalization or sanitization that strips U+200D or U+FE0F.
4. Fix at the root and add test strings covering ZWJ sequences, flags, keycaps and skin tones.

**Designing a custom emoji or icon set**

1. Define purpose, platforms, sizes and the visual language (grid, stroke, corner radius, palette, perspective).
2. Sketch the set together so it stays consistent; draw at the export size or as vectors with pixel-hinting checks.
3. Export (PNG with transparency, or GIF for animation) and check: `python3 scripts/emoji_tool.py check-asset FILE --platform discord`.
4. Test legibility at display size on light and dark themes; review meanings with people from the intended audiences.

## Decision rules

| Situation | Decision |
|---|---|
| Limiting user input length | Count graphemes for the user-facing limit; also enforce a byte limit for storage |
| Storing emoji in MySQL | Use `utf8mb4` columns and connections; legacy `utf8` cannot store most emoji |
| Text-default symbols (heart, sun, arrows) | Add U+FE0F where emoji style is intended |
| Newer emoji (recent Unicode versions) | Assume many users cannot see them yet; avoid in critical text or provide fallbacks |
| Emoji carrying meaning (status, rating) | Pair with text or accessible labels; never emoji alone |
| Custom emoji for a community | Square canvas, transparent background, bold shapes, tested at small sizes |
| Iconography across a product | One grid and stroke system; consistent metaphors; label icons that are not universal |

## Tool requirements

- **Required:** Python 3.8 or newer for [scripts/emoji_tool.py](scripts/emoji_tool.py) (inspect, length, check-asset).
- **Limit:** names come from Python's `unicodedata`; code points newer than its Unicode version are flagged as unknown, never guessed. Use a newer Python or the Unicode Consortium's data files for the latest emoji.
- **Optional:** Pillow or an image editor for producing assets; `mych-pixel-art` for pixel-style emoji.

## Inputs and outputs

| Input | Form |
|---|---|
| Strings | Text containing emoji, from logs, databases or user reports |
| Brief | Purpose, audience, platforms, sizes, tone |
| Assets | PNG or GIF custom emoji |

| Output | Contents |
|---|---|
| Inspection report | Graphemes, code points, names, sequence types, counts, warnings |
| Fix recommendation | Where the string breaks and the root-cause change |
| Emoji or icon set | Assets plus a style sheet (grid, stroke, palette, naming) and checks against platform guidance |
| Usage guidance | Which emoji to use where, with accessible alternatives |

## Quality standards

- Strings with ZWJ sequences, flags, keycaps and skin tones survive storage, truncation and rendering in tests.
- Visual meaning never depends on emoji alone; screen reader names are acceptable in context.
- Custom assets meet the platform's current guidance and stay legible at display size on light and dark backgrounds.
- An icon set uses one grid, stroke and metaphor system.

## Failure modes

| Failure | Prevention or fix |
|---|---|
| Families split into separate people, flags into letters | Grapheme-aware truncation and rendering with current fonts |
| Question marks or boxes in storage | UTF-8 everywhere (`utf8mb4` in MySQL) |
| Monochrome heart instead of red | Add U+FE0F to text-default emoji |
| Emoji invisible to older devices | Avoid recent emoji in critical text; provide text fallbacks |
| Misread meaning | Test with the audience; avoid ambiguous or culture-specific emoji in key messages |
| Blurry or unreadable custom emoji | Design for small sizes; strong silhouettes; check exports |

## Security

- Emoji and invisible characters (ZWJ, variation selectors, tags) can hide content or spoof identifiers; normalize and restrict characters in usernames, domains and identifiers, and display suspicious invisible characters during review.
- The tool reads files only for `check-asset`, parses headers, and never executes content.
- Respect licenses of emoji fonts and art (some platform emoji designs are proprietary); record the source and license of any reused emoji artwork.

## Examples

```bash
python3 scripts/emoji_tool.py inspect "👨‍👩‍👧 🇳🇴 1️⃣ 👍🏽"
python3 scripts/emoji_tool.py length "👨‍👩‍👧"
python3 scripts/emoji_tool.py check-asset party-parrot.gif --platform discord
```

## Integration

- **With the core:** use inspection output as evidence when fixing emoji bugs; accessibility checks follow the core's accessibility checklist.
- **With `mych-pixel-art`:** pixel-style emoji drawn and validated with the pixel toolchain, then checked here for platform guidance.
- **With `mych-chatbot-engineering`:** reaction conventions, emoji in bot replies and length limits on chat platforms.
- **With the Designer:** iconography systems and visual language across a product.

## Testing criteria

- Segmentation keeps ZWJ sequences, flags, keycaps, skin-tone sequences and tag sequences whole, and splits adjacent flags correctly.
- Length counts match grapheme, code point, UTF-16 and UTF-8 definitions.
- Warnings appear for text-default emoji without U+FE0F, lone regional indicators, unpaired modifiers, malformed keycaps and tags, and code points unknown to the local Unicode database.
- Asset checks report dimensions, size and animation and cite the source of the guidance.
- Repository tests: `python3 -m unittest discover -s tests -p "test_spec_emoji.py"`.
