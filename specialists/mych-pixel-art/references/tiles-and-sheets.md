# Tiles and Sprite Sheets

Grid choices, seamless tiles, autotiling, sheet packing and how engines should display pixel art.

## Grids

- Choose one tile size for the project: 8 px (very low resolution), 16 px (most common for 2D games), 32 px (more detail).
- Sprites need not match the tile size, but should align to the same pixel scale.
- Pick the game's internal resolution first (for example 320x180 for 16:9 at 16 px tiles), then scale by whole numbers to the screen.

## Seamless tiles

- Draw the base tile, then preview it tiled 3x3. Seams show as repeating lines; break them by moving detail away from the edges.
- Avoid strong single features in repeating tiles; a distinctive rock repeated every 16 px reads as a pattern.
- Make variants (2 to 4 per terrain) and scatter them to hide repetition.

## Autotiling

| Set | Tiles | Use |
|---|---|---|
| Edge set (4-bit) | 16 | Each tile chosen by which of the 4 orthogonal neighbors match; simple terrain |
| Blob set (8-bit reduced) | 47 | Considers diagonals too; clean inner and outer corners |

Plan the set before drawing, and lay tiles out in the sheet in the order the engine's autotiler expects.

## Packing sheets

- `pixel_tool.py render SPRITE --sheet` or `pixel_tool.py sheet FRAMES... --out SHEET.png` pack equal-sized frames row by row, near-square by default (`--columns N` to fix the width).
- `--padding P` adds transparent pixels between frames; `--extrude E` repeats each frame's edge pixels around it. Both prevent neighboring frames from bleeding into each other when an engine samples textures with filtering or sub-pixel offsets.
- Power-of-two sheet sizes are no longer required by modern WebGL 2 or desktop engines, but some older pipelines and mipmapping still expect them; pad the sheet if the target needs it.

## Metadata format

The JSON follows the array layout used by Aseprite exports:

```json
{
  "frames": [
    {"filename": "idle_0", "frame": {"x": 0, "y": 0, "w": 12, "h": 8}, "rotated": false, "trimmed": false,
     "spriteSourceSize": {"x": 0, "y": 0, "w": 12, "h": 8}, "sourceSize": {"w": 12, "h": 8}, "duration": 220}
  ],
  "meta": {"image": "slime.png", "format": "RGBA8888", "size": {"w": 24, "h": 8}, "scale": "1",
           "frameTags": [{"name": "idle", "from": 0, "to": 1, "direction": "pingpong"}], "anchor": {"x": 6, "y": 7}}
}
```

Engines with Aseprite JSON import can use it directly; otherwise read `frames[i].frame` for source rectangles, `duration` for timing and `meta.frameTags` for animations. `meta.anchor` is an addition of this toolchain. Compatibility with specific engines has not been tested here; verify the import in the target engine.

## Displaying pixel art

- **Nearest-neighbor sampling only.** In browsers: `image-rendering: pixelated` on the canvas element and `ctx.imageSmoothingEnabled = false`. In engines: point or nearest filtering, no mipmaps.
- **Integer scaling.** Scale the internal resolution by whole numbers; letterbox the remainder instead of stretching.
- **Pixel-snapped camera.** Round the camera position to whole internal pixels when drawing, or sprites shimmer as they move.
- **Draw at integer coordinates.** Keep physics positions as floats, but round when drawing.
