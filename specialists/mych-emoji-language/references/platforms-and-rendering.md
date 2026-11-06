# Platforms and Rendering

Why the same emoji looks different, or does not appear at all, across systems, and how to plan for it.

## Who draws the emoji

Each operating system, browser or app ships an emoji font or image set (for example Apple, Google Noto, Microsoft, Samsung, and open sets such as Twemoji and OpenMoji used by some apps and websites). Designs differ in color, gesture and detail, which can change perceived meaning (a "grimacing" face can read as awkward on one platform and happy on another).

## Support lag

- Platforms add new Unicode emoji on their own release schedules; older devices never get them.
- Unsupported ZWJ sequences fall back to their component emoji side by side (a family shows as separate people); unsupported single code points show as boxes or replacement glyphs.
- Flags depend on the platform: some show letters instead of flag images for regional-indicator pairs.

## Web delivery

- Specify a font stack that includes the platform emoji fonts; avoid forcing a text font that lacks emoji.
- For consistent appearance across platforms, use an image set (with its license) and keep text alternatives (`alt` with the emoji name).
- Do not strip U+200D or U+FE0F in sanitizers or minifiers.

## Storage and transport

- Use UTF-8 end to end; in MySQL use `utf8mb4` (the legacy `utf8` charset stores at most three bytes per character and rejects or corrupts most emoji).
- Normalize identifiers deliberately; Unicode normalization does not remove ZWJ or variation selectors.
- Escape emoji correctly in JSON and URLs (UTF-8 percent-encoding).

## Testing set

Keep a fixture string with: a basic emoji, a text-default symbol with and without U+FE0F, a skin-tone sequence, a ZWJ family, a profession ZWJ sequence with a skin tone, a keycap, two adjacent flags and a subdivision flag. Run it through input, storage, truncation, search and rendering.
