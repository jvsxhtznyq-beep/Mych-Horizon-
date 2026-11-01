# Text Sprite Format

A plain-text format for drawing pixel art precisely, designed so people and language models can write and review sprites line by line. `scripts/pixel_tool.py render` turns it into PNG frames or a sprite sheet with JSON.

## Example

```text
# Comments start with '#'.
name: slime
palette:
  k #1a1c2c
  g #38b764
  w #f4f4f4
frame idle_0 220
.kk.
kgwk
kggk
frame idle_1 220
....
.kk.
kwgk
tag idle idle_0 idle_1 pingpong
anchor 2 2
```

## Lines

| Line | Meaning |
|---|---|
| `name: NAME` | Output file name stem (defaults to the file name) |
| `size: WxH` | Optional; otherwise taken from the first frame |
| `palette:` | Starts palette entries, one per line: a single character, then `#rrggbb`, `#rrggbbaa` or `transparent` |
| `palette: use NAME` | Maps hex digits `0` to `f` to a built-in palette (`pico8`, `sweetie16`; shorter palettes map fewer digits) |
| `frame NAME [MS]` | Starts a frame; following lines are pixel rows. Duration defaults to 100 ms |
| `tag NAME FIRST LAST [DIRECTION]` | Animation from frame FIRST to LAST; direction `forward`, `reverse` or `pingpong` |
| `anchor X Y` | Pivot point in frame pixels, usually at the feet |

## Rules

- `.` is transparent unless the palette redefines it.
- `#` starts a comment and cannot be a palette character; spaces cannot be pixels.
- Every row of every frame has exactly the frame width; every frame has exactly the frame height.
- Every character in a row must be in the palette. Errors name the file, line and column.
- Frame names are unique. Without `tag` lines, consecutive frames named `PREFIX_N` become one tag named `PREFIX`.
- Palette entries and custom palettes may be mixed with `palette: use NAME`; later entries override earlier ones.

## Writing tips

- Draw the silhouette with one character first, then replace characters for shading.
- Keep one character per material and value step (`k` outline, `g` base, `l` light) so the grid stays readable.
- Comment non-obvious frames (`# contact pose, left foot forward`).
