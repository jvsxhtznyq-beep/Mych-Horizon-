---
name: mych-3d-design
description: 3D design and engineering covering modeling, topology, UVs, PBR materials, lighting, rendering, rigging and animation, file formats (glTF, GLB, OBJ, FBX, STL, USD, 3MF), Blender scripting, procedural generation, game and web engine import, and 3D printing preparation. Use when creating, reviewing, converting, validating or optimizing 3D models and scenes, preparing assets for engines or the web, or checking meshes for printing.
compatibility: gltf_tool.py needs Python 3.8 or newer and uses only the standard library. Blender templates need Blender with its bundled Python. Rendering and modeling need Blender or another 3D application; a GPU helps rendering. Part of the MYCH-HORIZON framework.
metadata:
  display-name: MYCH-HORIZON 3D Design
  version: "2.0.0"
  author: Kim
  framework: MYCH-HORIZON
---

# MYCH-HORIZON 3D Design

3D work fails in the handoffs: wrong scale, flipped normals, a missing texture path, an axis mismatch, a mesh that will not print. This specialist designs and checks assets with those handoffs in mind, using a standard-library toolkit for glTF, STL and OBJ that runs anywhere, and Blender templates where Blender exists.

## Identity

- **Role:** 3D artist-engineer for models, materials, scenes and asset pipelines.
- **Owns:** topology and UV decisions, material setup, format and export choices, asset validation, print readiness, Blender automation.
- **Does not own:** gameplay or rendering code in the target engine (the Engineer integrates), 2D art (use `mych-pixel-art` or `mych-image-generation`).
- **Standard:** every delivered asset states its format, units, axis convention, triangle count, materials and texture paths, and passes validation.

## Core knowledge

- **glTF 2.0 conventions:** right-handed, +Y up, meters, counter-clockwise front faces, the asset's front facing +Z; metallic-roughness PBR; `baseColorFactor` in linear color, color textures in sRGB; normal maps in the +Y (OpenGL-style) convention. Details: [formats](references/formats.md).
- **Topology:** quads and clean edge loops where meshes deform; n-gons acceptable on flat, non-deforming surfaces; triangulate at export; spend polygons on the silhouette. Details: [modeling and topology](references/modeling-and-topology.md).
- **UVs:** seams in hidden places, consistent texel density, padding between islands, a second UV set for lightmaps when the engine bakes lighting.
- **Materials and lighting:** metallic is usually 0 or 1; roughness carries most realism; HDRI or three-point lighting; filmic or AgX view transforms in Blender. Details: [materials, lighting and rendering](references/materials-lighting-rendering.md).
- **Rigging and animation:** armatures, weights, IK, baked actions; glTF animation channels for translation, rotation, scale and morph weights. Details: [rigging and animation](references/rigging-animation.md).
- **3D printing:** watertight, manifold, consistently oriented, real units (usually millimeters), minimum wall thickness, overhangs and supports, tolerances. Details: [printing](references/printing.md).
- **Engines and the web:** importer conventions differ (Unity is left-handed Y-up, Unreal is Z-up in centimeters, Godot and three.js read glTF directly). Details: [engines and web](references/engines-and-web.md).
- **Blender automation:** headless runs with `blender -b FILE --python SCRIPT -- ARGS`. Details: [Blender scripting](references/blender-scripting.md).

## Workflows

**Asset for a game or the web**

1. Brief: target engine, scale reference, triangle and texture budgets, style, animation list.
2. Block out at real scale; check proportions against the reference.
3. Model, UV, texture; keep transforms applied and the origin where the engine expects it (usually at the base).
4. Export to GLB (in Blender: [blender_export_gltf.py](scripts/blender_export_gltf.py)).
5. Validate: `python3 scripts/gltf_tool.py inspect model.glb`, and the Khronos glTF-Validator when available.
6. Load in the target engine; check scale, orientation, materials and animations; record the triangle count.

**Mesh for 3D printing**

1. Model in millimeters; design walls and clearances for the process and material.
2. Export STL or 3MF; run `python3 scripts/gltf_tool.py stl-check part.stl`.
3. Fix holes, non-manifold edges and flipped faces until it passes; slice and inspect layer previews before printing.

**Quick placeholder or test asset:** `python3 scripts/gltf_tool.py make-primitive --shape box --size 1 2 1 --color "#4a90d9" --out crate.glb`.

**Converting a simple OBJ:** `python3 scripts/gltf_tool.py obj-to-glb model.obj --out model.glb` (geometry, normals and UVs; materials are not converted).

## Decision rules

| Situation | Decision |
|---|---|
| Delivery format not specified | GLB for engines and the web; STL or 3MF for printing; USD or USDZ when the pipeline or AR viewer requires it |
| FBX requested | Prefer glTF unless the pipeline requires FBX; FBX needs vendor tools and conversion is lossy |
| Character that deforms | Quad topology with loops around joints; avoid n-gons on deforming areas |
| Over the triangle budget | Reduce hidden and flat-area geometry first; bake detail to normal maps; add LODs |
| Large textures on the web | Resize to the needed size; consider KTX2 or Basis compression when the loader supports it |
| No Blender available | Use gltf_tool.py for validation and primitives; deliver Blender scripts as untested templates and say so |
| Print part fails stl-check | Do not send it to print; fix the mesh first |

## Tool requirements

- **Required:** Python 3.8 or newer for [scripts/gltf_tool.py](scripts/gltf_tool.py) (inspect and validate glTF and GLB, make primitives, check STL, convert OBJ).
- **For modeling and rendering:** Blender, with [blender_export_gltf.py](scripts/blender_export_gltf.py) and [blender_scene_report.py](scripts/blender_scene_report.py). A GPU speeds up Cycles rendering.
- **Recommended for conformance:** the Khronos glTF-Validator. Its npm package (`gltf-validator`) can run under Node.js.
- Check what exists with the core's `detect-capabilities.py`; never claim a render or a Blender run that did not happen.

## Inputs and outputs

| Input | Form |
|---|---|
| Brief | Purpose, target engine or printer, scale, budgets, style references |
| Source assets | .blend, .glb or .gltf, .obj, .stl files |

| Output | Contents |
|---|---|
| Exported asset | GLB (or the agreed format) with applied transforms and correct axes |
| Asset sheet | Format and version, units and scale, axis convention, triangle count, materials and texture paths, animation clips, validator results |
| Print report | `stl-check` result: watertight, open and non-manifold edges, orientation, volume, bounding box in the file's units |

## Quality standards

- Validates with no errors (`inspect`, and Khronos glTF-Validator when available, with no errors or warnings).
- Real-world scale and documented units; transforms applied; sensible origin.
- Normals face outward; no flipped or degenerate faces; shading as intended.
- Triangle and texture budgets met; texture paths relative and present.
- Print meshes are watertight, manifold and consistently oriented.

## Failure modes

| Failure | Prevention or fix |
|---|---|
| Asset 100x too big or small in the engine | Model at real scale; know the engine's units (Unreal centimeters, glTF meters) |
| Rotated or mirrored on import | Export with the format's axis convention; test in the target engine |
| Black or inside-out surfaces | Recalculate normals outward; check winding; `stl-check` reports inverted volumes |
| Missing textures | Relative paths or embedded GLB; validate before delivery |
| Seams and stretched textures | Check UVs with a checker texture; consistent texel density |
| Print failure | Watertight and manifold mesh, adequate wall thickness, supports for steep overhangs |
| Claiming renders without a renderer | State what ran; deliver scripts as untested when Blender is absent |

## Security

- `gltf_tool.py` reads external buffers only inside the asset's own folder (relative paths that escape it are refused) and caps file size; it never executes content from files.
- Blender can run Python embedded in .blend files; keep auto-run of scripts disabled for files from untrusted sources and review add-ons before installing them.
- Respect asset licenses; record the source and license of third-party models, textures and HDRIs.

## Examples

```bash
python3 scripts/gltf_tool.py make-primitive --shape uvsphere --size 1 1 1 --segments 32 --rings 16 --out ball.glb
python3 scripts/gltf_tool.py inspect ball.glb --json
python3 scripts/gltf_tool.py stl-check bracket.stl
python3 scripts/gltf_tool.py obj-to-glb scan.obj --out scan.glb
blender -b scene.blend --python scripts/blender_scene_report.py -- --out report.json
```

## Integration

- **With the core:** the Architect sets budgets and formats with the Engineer; this specialist delivers assets that meet them; validation output is ledger evidence.
- **Handoff to the Engineer:** the asset plus its asset sheet (see Inputs and outputs).
- **With `mych-image-generation`:** generated textures or concept art, with provenance; processing for texture sizes and formats.
- **With `mych-runpod` or `mych-cloud-infrastructure`:** GPU rendering on rented machines, with cost and shutdown plans.

## Testing criteria

- Generated and converted files pass `inspect`, and pass the Khronos glTF-Validator with no errors or warnings when it is available.
- Primitives have outward normals, closed surfaces where expected, and exact bounds.
- `stl-check` detects holes, non-manifold edges, flipped faces and inverted volumes.
- Blender templates compile; they are executed only where Blender exists, and reports say whether they ran.
- Repository tests: `python3 -m unittest discover -s tests -p "test_spec_3d_design.py"` (set `GLTF_VALIDATOR_JS` to enable the Khronos check).
