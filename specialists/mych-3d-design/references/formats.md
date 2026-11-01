# 3D File Formats

What each format stores, its conventions, and the conversion traps between them.

| Format | Stores | Units and axes | Best for | Watch out for |
|---|---|---|---|---|
| glTF 2.0 (`.gltf` + `.bin` + images) | Meshes, PBR materials, textures, scenes, skins, animations, morph targets | Meters, right-handed, +Y up, front faces counter-clockwise, asset front facing +Z | Engines and the web | Separate files must travel together |
| GLB | glTF in one binary container | As glTF | Delivery of single assets | Harder to inspect by hand; use `gltf_tool.py inspect` |
| OBJ (+ MTL) | Positions, UVs, normals, polygon faces; basic materials | No units; usually Y-up by convention | Simple static geometry exchange | No animation, no PBR; OBJ texture V runs bottom-up while glTF runs top-down |
| FBX | Meshes, materials, skins, animation, cameras | Configurable units and axes | Pipelines built around Autodesk tools | Proprietary; conversions lose or alter data; version differences |
| STL | Triangles only | No units (printing assumes mm), no colors | 3D printing | No materials or units; often non-manifold |
| 3MF | Meshes with units, colors, materials, print settings | Explicit units | Modern 3D printing | Fewer viewers outside printing tools |
| USD, USDZ | Scenes with layers, variants, materials; USDZ is a zipped package | Configurable (stage metadata) | Film pipelines, AR viewers that require USDZ | Large ecosystem of schemas; tool support varies |
| PLY | Points or meshes with per-vertex properties | No units | Scans and point clouds | Many variants |

## glTF details that matter

- **Accessors** describe typed views into buffers; `POSITION` accessors must carry `min` and `max`.
- **Materials:** metallic-roughness PBR. `baseColorFactor` is linear; base color and emissive textures are sRGB; metallic-roughness, normal and occlusion textures are linear data.
- **Extensions:** `extensionsUsed` lists extensions present; `extensionsRequired` lists those a loader must support (for example Draco or meshopt compression, KTX2 textures). Required extensions make files unloadable in loaders without them.
- **Animation:** channels target node translation, rotation (quaternions), scale or morph weights; interpolation is LINEAR, STEP or CUBICSPLINE.

## Conversion checklist

- [ ] Units and scale verified against a known reference object.
- [ ] Up axis and handedness converted (Blender is Z-up; its glTF exporter converts to +Y up by default).
- [ ] Normals preserved or recomputed outward; smoothing intent kept (hard edges).
- [ ] UV V axis flipped when moving between OBJ and glTF.
- [ ] Texture paths relative, files present, color spaces correct.
- [ ] Animations baked when constraints or drivers do not export.
- [ ] Result validated (`gltf_tool.py inspect`; the Khronos glTF-Validator when available).
