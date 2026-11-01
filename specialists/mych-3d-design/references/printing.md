# 3D Printing Preparation

Meshes that slice cleanly and parts that come out as designed.

## Mesh requirements

| Requirement | Why | Check |
|---|---|---|
| Watertight (no holes) | Slicers need a closed volume to know inside from outside | `stl-check`: open edges = 0 |
| Manifold (each edge shared by exactly two faces) | Ambiguous geometry slices unpredictably | `stl-check`: non-manifold edges = 0 |
| Consistent orientation | Flipped faces confuse inside and outside | `stl-check`: orientation conflicts = 0; positive volume |
| No degenerate faces | Zero-area faces add noise | `stl-check` warns |
| Real units | STL has no units; slicers usually assume millimeters | Bounding box matches the intended size |

## Design guidance

The right values depend on the printer, process and material; confirm them with the printer's or service's guidelines. Common starting points:

- **Walls:** design walls at least a few nozzle widths thick for filament printers (around 1 mm or more is a common starting point); thin features may not print at all.
- **Overhangs:** surfaces steeper than about 45 degrees from vertical usually need supports on filament printers; chamfer instead of filleting downward-facing edges.
- **Bridges:** short horizontal spans can print without support; long ones sag.
- **Clearances for fits:** leave a gap between mating parts (often a few tenths of a millimeter for filament printers) and test with a small coupon before printing the full part.
- **Orientation:** choose it for strength (layer lines are the weak direction), support needs and surface quality.
- **Holes:** small vertical holes print undersized on filament printers; ream or design them slightly larger.

## Formats

- **STL:** universal, triangles only, no units or colors.
- **3MF:** carries units, colors, materials and print settings; prefer it when the slicer supports it.

## Workflow

1. Model in millimeters with walls and clearances for the process.
2. Export STL or 3MF and run `python3 scripts/gltf_tool.py stl-check part.stl`.
3. Fix problems (fill holes, recalculate normals, remove internal faces), then check again.
4. Slice; inspect the layer preview for gaps, thin walls and unsupported areas.
5. Print a test coupon for critical fits before the full part.
