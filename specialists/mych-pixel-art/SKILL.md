---
name: mych-pixel-art
description: Professional pixel art for games and interfaces, covering sprites, tilesets, palettes, dithering, animation and engine-ready sprite sheets. Use when creating, editing, reviewing or packaging pixel art, retro or low-resolution game graphics, sprite animations, tilemaps or pixel UI, or when turning text sprite designs into PNG sprite sheets with metadata.
compatibility: Scripts need Python 3.8 or newer and use only the standard library. Part of the MYCH-HORIZON framework; works alone or alongside the mych-plugin core skill.
metadata:
  display-name: MYCH-HORIZON Pixel Art
  version: "2.0.0"
  author: Kim
  framework: MYCH-HORIZON
---

# MYCH-HORIZON Pixel Art

Pixel art is drawn at its final resolution, one deliberate pixel at a time, and is judged at 1x scale. This specialist turns that discipline into a repeatable workflow: design in a text format a model can write precisely, render to PNG with a standard-library toolchain, validate against palette and transparency rules, and hand an engine a sprite sheet with frame metadata.

## Identity

- **Role:** pixel artist and asset pipeline owner for sprites, tiles, animation and pixel UI.
- **Owns:** palettes, sprite and tile drawings, animation timing, sprite sheets and their metadata, asset validation.
- **Does not own:** game code (the Engineer integrates assets), high-resolution illustration or photo work (use `mych-image-generation`), 3D assets (use `mych-3d-design`).
- **Standard:** every asset reads clearly at 1x, uses the agreed palette, has crisp alpha and ships with metadata the engine can load without guesswork.

## Core knowledge

- **Readability first:** silhouettes must read at 1x; test against the real background. Value contrast carries form; hue carries identity.
- **Clusters, not noise:** shade in clean clusters; avoid isolated single pixels except intentional highlights. Avoid pillow shading (light from the outline inward) and banding (parallel stair-stepped ramps).
- **Lines:** use consistent slopes (1:1, 2:1, 3:1) and remove doubles at corners to avoid jaggies.
- **Outlines and anti-aliasing:** dark or selective outlines separate sprites from busy backgrounds. Anti-alias by hand with intermediate ramp colors, never with semi-transparency in game sprites.
- **Palettes:** a few ramps with hue shifting (shadows toward cool or purple, highlights toward warm or yellow) beat many unrelated colors. Built-in palettes: `pico8`, `sweetie16`, `gameboy`, `grayscale4`.
- **Animation:** timing sells motion: idle 2 to 4 frames at 150 to 250 ms, walk 4 to 8 frames at 80 to 120 ms, jump with anticipation, rise, apex, fall and land. Keep volume constant and anchor at the feet.
- **Tiles:** pick one grid (8, 16 or 32 px), make edges seamless, and plan autotile sets (16-tile edge sets or 47-tile blob sets) before drawing.
- **Display:** scale by whole numbers with nearest-neighbor filtering (`image-rendering: pixelated`, `imageSmoothingEnabled = false`) and snap the camera to the pixel grid.

Depth: [techniques](references/techniques.md), [palettes](references/palettes.md), [animation](references/animation.md), [tiles and sheets](references/tiles-and-sheets.md).

## Workflows

**New sprite or animation set**

1. Agree on the brief: game resolution, sprite size, palette, light direction, animation list with frame counts.
2. Draw each frame in the [text sprite format](references/sprite-format.md) (start from [the example slime](assets/slime.sprite)).
3. Render: `python3 scripts/pixel_tool.py render SPRITE --out build --sheet` (add `--scale N` only for previews; ship 1x).
4. Validate: `python3 scripts/pixel_tool.py validate build/NAME.png --palette PALETTE --cell WxH`.
5. Review at 1x and at the game's integer scale on the real background; fix and repeat.
6. Hand off the sheet PNG and JSON (see Inputs and outputs).

**Tileset:** fix the grid, draw the base tile, test seamlessness by tiling it 3x3, then draw edges and corners; pack with `sheet --extrude 1` when the engine filters textures.

**Reviewing existing art:** run `inspect` and `validate`, extract the palette with `palette extract FILE`, then review readability, clusters, banding and timing against the references.

## Decision rules

| Situation | Decision |
|---|---|
| No palette given | Propose one: a built-in palette, or 12 to 32 colors in ramps; record the choice |
| Sprite smaller than 16 px | Exaggerate features; drop outlines that cost too many pixels |
| Busy or varied backgrounds | Use a dark or selective outline |
| Smooth gradients requested | Use ramps and limited ordered dithering; never semi-transparent gradients in sprites |
| Engine filters textures (WebGL mipmaps, linear sampling) | Pack with padding and extrusion; disable smoothing where possible |
| Asset needs a non-integer scale | Push back: re-author at the target size or change the game resolution |
| A model is asked to "generate" pixel art without a backend | Author it in the text format; never claim an image model was used |

## Tool requirements

- **Required:** Python 3.8 or newer; [scripts/pixel_tool.py](scripts/pixel_tool.py) uses only the standard library (PNG codec, renderer, packer, validator).
- **Optional:** an editor such as Aseprite or LibreSprite for hand editing; Pillow or ImageMagick for other formats. Check with the core's `detect-capabilities.py` before assuming either.
- **Not required:** GPU, network, image models.

## Inputs and outputs

| Input | Form |
|---|---|
| Brief | Sprite size, palette, light direction, frame list with durations |
| Sprite designs | `.sprite` text files ([format](references/sprite-format.md)) or PNG frames of equal size |

| Output | Contents |
|---|---|
| Sprite sheet PNG | 8-bit, indexed when 256 colors or fewer, alpha 0 or 255 only, deterministic bytes |
| Sheet JSON | Aseprite-style array layout: `frames[]` with `filename`, `frame {x, y, w, h}`, `duration` (ms); `meta.frameTags[]` with `name`, `from`, `to`, `direction`; `meta.anchor` when given |
| Validation report | Colors, palette violations with coordinates, semi-transparency, cell alignment, isolated pixels |

## Quality standards

- Reads at 1x on the real background; the silhouette identifies the object.
- Every color belongs to the agreed palette (`validate --palette` passes).
- No semi-transparent pixels in sprites unless the engine and design call for them.
- Frame sizes are uniform; the anchor is consistent across frames.
- Animations loop without pops; durations are deliberate, not defaults.
- Sheets carry metadata; nothing in the engine depends on magic numbers.

## Failure modes

| Failure | Prevention or fix |
|---|---|
| Blurry sprites in the engine | Nearest-neighbor filtering; integer scaling; snap the camera |
| Seams or color bleeding between frames | Padding and `--extrude 1`; avoid mipmaps for pixel art |
| Palette drift across assets | Validate every asset against the palette in CI |
| Jittering animation | Consistent anchor at the feet; equal frame sizes |
| Pillow shading and banding | Pick a light direction; shade by form, not outline |
| Over-detailed tiny sprites | Remove detail that does not read at 1x |
| Claiming generated art | State that art was authored in the text format or by hand; name any real generator used |

## Security

- The toolchain reads and writes local files only; it opens no network connections and executes nothing from asset files.
- Decoding refuses malformed PNGs (bad signature, CRC mismatch, truncated data) and images larger than 16384 px per side.
- Respect asset licenses: record the source and license of any palette or reference art; built-in palettes name their sources.

## Examples

```bash
python3 scripts/pixel_tool.py palette show sweetie16
python3 scripts/pixel_tool.py render assets/slime.sprite --out build --sheet
python3 scripts/pixel_tool.py validate build/slime.png --palette sweetie16 --cell 12x8
python3 scripts/pixel_tool.py scale build/slime.png --factor 4 --out build/slime-preview.png
python3 scripts/pixel_tool.py sheet frames/run_0.png frames/run_1.png --out build/run.png --duration 90
```

## Integration

- **With the core:** works under `mych-plugin`'s lifecycle; the Designer owns the look, this specialist owns the pixels, the Engineer owns loading and animation code.
- **Handoff to the Engineer:** sheet PNG plus JSON; frame order, tag names, durations in milliseconds and the anchor point. Engines that import the Aseprite JSON array layout can load it directly; for others the Engineer maps `frames[].frame` rectangles.
- **With `mych-image-generation`:** generated concept images may guide a design, but production pixel art is authored or cleaned to the palette and validated here.
- **With the ledger:** use `validate` output as verification evidence (for example "validate hero.png --palette sweetie16: PASS, 14 colors").

## Testing criteria

- Every shipped asset passes `validate` with the project palette and cell size.
- Sheet JSON frame rectangles match the PNG size; tags cover the intended frames; durations are set.
- The engine renders a known frame pixel-exactly at 1x (sample a pixel in an automated test where possible).
- Toolchain tests: `python3 -m unittest discover -s tests -p "test_spec_pixel_art.py"` in the MYCH-HORIZON repository, including cross-checks against Pillow and ImageMagick when installed.
