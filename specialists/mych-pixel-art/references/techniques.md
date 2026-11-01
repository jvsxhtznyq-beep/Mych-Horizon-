# Pixel-Art Techniques

Craft rules for sprites and tiles that read well at 1x. Each rule names the failure it prevents.

## Readability

- **Design the silhouette first.** Fill the shape in one dark color; if it is not recognizable, no amount of shading will fix it.
- **Exaggerate.** At 16 px a head is a quarter of the body; eyes are one or two pixels. Proportions that are realistic at high resolution disappear at low resolution.
- **Value before hue.** Convert to grayscale (or view with saturation removed): form must survive. Hue identifies objects; value describes them.
- **Test on the real background** at the game's integer scale. Contrast against a flat gray canvas lies.

## Clusters and noise

- Shade in **clusters** of several pixels per color. Single isolated pixels read as noise unless they are deliberate highlights (eye glints, sparkles). `pixel_tool.py validate` warns about isolated pixels so each can be confirmed as intentional.
- **Pillow shading** (light from the outline toward the center, ignoring the light source) flattens form. Choose a light direction (usually top-left or top) and shade by the shape's planes.
- **Banding** is parallel stair-steps of adjacent ramp colors that echo the outline. Break bands by varying cluster widths and offsetting edges.

## Lines and curves

- Keep line segments in **consistent slopes**: 1:1, 2:1, 3:1 and so on. Irregular runs (2, 1, 3, 1) look jagged.
- Curves change segment length gradually (4, 3, 2, 1, 1, 2, 3, 4).
- Remove **doubles**: an L-shaped corner pixel inside a diagonal makes it look thick. Keep lines one pixel wide unless intentionally bold.

## Outlines

| Style | When |
|---|---|
| Full dark outline | Busy backgrounds, small sprites, high readability needs |
| Selective outline (sel-out) | Outline darker on the shadow side, lighter or absent on the lit side; richer look on calmer backgrounds |
| No outline | Large sprites, painterly styles, tiles that must blend |

Outline color is usually the darkest ramp color, slightly hue-shifted, rather than pure black.

## Anti-aliasing

- Hand-placed intermediate colors smooth jagged edges **inside** a sprite or against a known background.
- Never anti-alias the outer edge of a game sprite against transparency: the sprite will show a halo on other backgrounds. Keep alpha at 0 or 255.

## Dithering

- Ordered dithering (checkerboard and patterns) simulates an intermediate color or texture with two palette colors.
- Use it sparingly for large surfaces (skies, rock texture) and transitions; avoid it on small or animated sprites, where it shimmers.
- A 50 percent checker between two close ramp colors reads smoothly; between distant colors it reads as texture.

## Sub-pixel animation

Shifting a few interior pixels by one color step (rather than moving an edge by a whole pixel) suggests movement smaller than a pixel: breathing, bobbing eyes, cloth sway. It keeps idle animations subtle.

## Common review checklist

- [ ] Silhouette readable in a single color.
- [ ] Consistent light direction across all assets.
- [ ] No pillow shading or banding.
- [ ] Clean slopes; no doubles.
- [ ] Alpha only 0 or 255.
- [ ] Palette respected (`validate --palette`).
