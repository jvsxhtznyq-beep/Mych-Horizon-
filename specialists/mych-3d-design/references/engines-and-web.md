# Engines and the Web

How common engines and web libraries treat imported assets, and how to verify an import.

| Target | Coordinate system and units | glTF support | Notes |
|---|---|---|---|
| three.js | Right-handed, +Y up; units are whatever the scene uses (meters by convention) | `GLTFLoader` (add Draco, meshopt or KTX2 loaders for compressed assets) | Set the renderer's output color space correctly for sRGB textures |
| Babylon.js | Left-handed by default, +Y up | glTF loader plugin converts handedness | Check orientation after import |
| Godot | Right-handed, +Y up, meters | Native glTF import | Import settings control materials and animation |
| Unity | Left-handed, +Y up, meters | Through glTF importer packages | Check scale and material conversion |
| Unreal Engine | Left-handed, +Z up, centimeters | glTF import support in recent versions | Expect a 100x unit difference against glTF meters if import scaling is not applied |

Capabilities change between versions; verify with the version in use.

## Web delivery

- Keep GLB files small: compress geometry (Draco or meshopt) and textures (KTX2 or Basis) when the loader supports the extensions; uncompressed assets load everywhere.
- Serve with correct MIME types (`model/gltf-binary` for GLB, `model/gltf+json` for glTF).
- Lazy-load large assets and show progress.

## Verifying an import

1. Validate the file (`gltf_tool.py inspect`; the Khronos glTF-Validator when available).
2. Load it in the target engine next to a reference object of known size.
3. Check orientation (front faces the expected direction), scale, materials, transparency and animation playback.
4. Record the engine version and what was checked in the asset sheet.
