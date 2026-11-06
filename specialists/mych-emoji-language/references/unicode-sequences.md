# Unicode Emoji Sequences

How emoji are encoded, and what that means for code that stores, counts, cuts or compares them.

## Building blocks

| Element | Code points | Example |
|---|---|---|
| Basic emoji | One code point (many in U+1F300 to U+1FAFF; older symbols elsewhere) | 😀 U+1F600 |
| Emoji presentation selector | U+FE0F after a base | ❤️ = U+2764 U+FE0F |
| Text presentation selector | U+FE0E after a base | ❤︎ = U+2764 U+FE0E |
| Skin tone modifier | U+1F3FB (light) to U+1F3FF (dark) after a modifier base | 👍🏽 = U+1F44D U+1F3FD |
| Zero-width joiner (ZWJ) sequence | Emoji joined by U+200D | 👨‍👩‍👧 = man ZWJ woman ZWJ girl |
| Keycap sequence | 0-9, #, * then U+FE0F then U+20E3 | 1️⃣ |
| Flag sequence | Two regional indicators U+1F1E6 to U+1F1FF (ISO 3166 region code) | 🇳🇴 = N O |
| Tag sequence | U+1F3F4 then tag characters (U+E0020 to U+E007E) then U+E007F | England, Scotland and Wales subdivision flags |

## Fully qualified forms

Unicode's emoji data distinguishes fully qualified sequences (with the U+FE0F the standard expects) from minimally qualified and unqualified ones. Platforms render fully qualified forms most reliably; keyboards emit them. When generating emoji in code, emit the fully qualified form.

## Graphemes

A grapheme cluster is what users perceive as one character. Unicode Standard Annex #29 defines extended grapheme clusters; emoji sequences, combining marks, modifiers and regional-indicator pairs each form one cluster. Use a grapheme-aware library in production code:

- JavaScript: `Intl.Segmenter` with `granularity: "grapheme"`.
- Swift: `String.count` counts graphemes.
- Python: no standard-library API; `emoji_tool.py` approximates the emoji rules, and third-party libraries implement UAX #29 fully.

## Lengths in practice

For 👨‍👩‍👧: 1 grapheme, 5 code points, 8 UTF-16 units (JavaScript `length`), 18 UTF-8 bytes. Database column limits often count bytes or characters differently from the UI: test with long emoji sequences.

## Versions

New emoji arrive with Unicode releases (Unicode 17.0 was released in September 2025), and platforms adopt them months to years later. Code points newer than a system's Unicode data show as boxes or as separate parts. `emoji_tool.py` reports the local database version and flags unknown code points.
