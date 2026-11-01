# Image Processing Recipes

Deterministic operations with `scripts/imagegen.py process` (Pillow), and the reasoning behind each default.

## Operations

| Operation | Command | Notes |
|---|---|---|
| Resize to fit | `process resize IN --size 512x512 --fit contain --out OUT` | Letterboxes with transparency (RGBA) to keep the aspect ratio |
| Resize to fill | `process resize IN --size 512x512 --fit cover --out OUT` | Crops the overflow, centered |
| Exact stretch | `--fit stretch` | Distorts; rarely what you want |
| Crop | `process crop IN --box 10,10,210,110 --out OUT` | Box is left, top, right, bottom |
| Pad to aspect | `process pad IN --aspect 16:9 --color "#000000" --out OUT` | `--color transparent` keeps alpha |
| Trim transparent edges | `process trim IN --out OUT` | Crops to the bounding box of non-transparent pixels |
| Convert or quantize | `process convert IN --mode P --colors 16 --out OUT` | Modes RGB, RGBA, L, P |
| Strip metadata | `process strip IN --out OUT` | Saves pixels only: EXIF, GPS and text chunks are dropped |
| Contact sheet | `process contact-sheet A B C --columns 3 --cell 256 --out OUT` | Review many outputs at once |
| Batch recipe | `process batch DIR --recipe R.json --out DIR2` | Writes `manifest.json` with input and output hashes |

Every processed file is written without metadata.

## Choosing a resampling filter

| Content | Filter |
|---|---|
| Photos and renders, downscaling | `lanczos` (default) |
| Pixel art or UI with hard edges, any scaling | `nearest` |
| Quick previews | `bilinear` |

## Formats

- **PNG:** lossless, supports alpha; use for UI, sprites, anything with sharp edges or transparency.
- **JPEG:** lossy, no alpha; photos only.
- **WebP:** lossy or lossless, supports alpha; good for the web when the target supports it.
- Keep a lossless master; export lossy versions from it, never re-encode lossy files repeatedly.

## Color

- Convert to RGB before saving JPEG; RGBA will be refused or flattened.
- Quantizing to a palette (`--mode P`) reduces size and enforces a limited palette, but dithering and color choices are automatic; for brand-exact colors, define the palette explicitly elsewhere.
- Color profiles (ICC) are dropped when metadata is stripped; for color-critical print work, keep a profile-managed master.

## Background removal and upscaling

These need extra models or packages that are not bundled (for example rembg for background removal, or ESRGAN-class upscalers). Check whether they are installed (`detect-capabilities.py`), ask before installing them, and record which model was used in the provenance notes.

## Batch recipe example

```json
{"include": ["*.png", "*.jpg"],
 "steps": [{"op": "trim"}, {"op": "pad", "aspect": "1:1", "color": "transparent"},
           {"op": "resize", "size": "256x256", "fit": "contain", "filter": "lanczos"}],
 "format": "png"}
```
