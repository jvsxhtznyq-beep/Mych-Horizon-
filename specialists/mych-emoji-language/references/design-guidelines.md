# Designing Custom Emoji and Icon Sets

Making emoji and icons that read at a glance and belong together.

## Visual system

- **Grid and keylines:** design on a square grid with consistent padding so shapes have similar visual weight (circles slightly larger than squares).
- **Stroke and corners:** one stroke weight and corner radius across the set (or one deliberate set of weights).
- **Palette:** a limited palette with a dark outline or strong contrast so emoji work on light and dark themes.
- **Perspective and lighting:** one viewpoint and light direction for the whole set.

## Legibility at small sizes

- Chat clients often display custom emoji around 20 to 32 px and reactions even smaller. Test at those sizes, not only at the 128 px export.
- Exaggerate the key feature (the expression, the object's silhouette); remove details that disappear when scaled down.
- Avoid text inside emoji; it becomes unreadable and cannot be translated.
- For pixel-style emoji, draw at the target resolution with `mych-pixel-art` and scale by whole numbers.

## Export

- Square canvas with a transparent background.
- PNG for static, GIF (or APNG where supported) for animation; keep animations short and avoid rapid flashing (no more than three flashes per second).
- Check platform guidance before uploading: `emoji_tool.py check-asset FILE --platform discord` (the guidance source is reported; verify limits in the platform's current documentation).
- Name files consistently (`party-cat.png`) and keep a source file (vector or layered) for edits.

## Icon sets in products

- Use metaphors users already know; label icons whose meaning is not universal.
- Provide accessible names for icon-only controls.
- Keep a living specification: grid, stroke, sizes, colors, naming and a catalog of icons with their meanings.
