# Blender Scripting

Automating Blender with its bundled Python (`bpy`), headless and repeatable.

## Running scripts

```bash
blender -b scene.blend --python script.py -- --out model.glb
```

- `-b` runs in the background (no window); `--python` runs a script after loading the file.
- Arguments after `--` are for the script; read them from `sys.argv` after the `--` marker (the templates do this).
- Use `--factory-startup` to ignore user preferences and add-ons when reproducibility matters.

## bpy essentials

- **Data API (`bpy.data`)** creates and edits objects, meshes and materials directly; prefer it in scripts.
- **Operators (`bpy.ops`)** mimic user actions and depend on context (active object, selection, mode); they are convenient for exporters and some modeling tools but fragile in background mode.
- **bmesh** gives low-level mesh access for analysis and edits (manifold checks, cleanup).
- APIs change between Blender versions: record the version (`bpy.app.version_string`) in outputs and test scripts on the version in use.

## Templates in this skill

| Script | Purpose |
|---|---|
| [blender_export_gltf.py](../scripts/blender_export_gltf.py) | Export the open scene to GLB or separate glTF using the built-in exporter |
| [blender_scene_report.py](../scripts/blender_scene_report.py) | JSON report of triangles, n-gons, unapplied scale, UV maps, non-manifold edges, loose vertices, materials and textures |

Both were compile-checked only in this repository (Blender was not installed in the test environment). Run them on a real file before relying on them, and report whether they ran.

## Safety

- .blend files can contain Python that runs when the file opens if auto-run is enabled; keep auto-run disabled for files from untrusted sources.
- Add-ons are code: install only reviewed add-ons from trusted sources.
- Scripts that delete or overwrite data should work on copies or write to new files.
