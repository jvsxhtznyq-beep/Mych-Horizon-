"""Export a .blend scene to glTF from the command line (Blender's bundled Python).

Usage (headless):
  blender -b scene.blend --python blender_export_gltf.py -- --out model.glb [--selected] [--no-apply]

Uses Blender's built-in glTF exporter (bpy.ops.export_scene.gltf). Exporter
options vary between Blender versions; check them with --help output of your
version if an argument is rejected. Not executed in the MYCH-HORIZON test
environment (Blender is not installed there): compile-checked only.
"""

import argparse
import sys


def parse_args(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Export the open scene to glTF or GLB.")
    parser.add_argument("--out", required=True, help="output path ending in .glb or .gltf")
    parser.add_argument("--selected", action="store_true", help="export only selected objects")
    parser.add_argument("--no-apply", action="store_true", help="do not apply modifiers")
    return parser.parse_args(args)


def main():
    import bpy  # available only inside Blender

    options = parse_args(sys.argv)
    export_format = "GLB" if options.out.lower().endswith(".glb") else "GLTF_SEPARATE"
    result = bpy.ops.export_scene.gltf(
        filepath=options.out,
        export_format=export_format,
        use_selection=options.selected,
        export_apply=not options.no_apply,
        export_yup=True,
    )
    if "FINISHED" not in result:
        print("glTF export did not finish: {}".format(result), file=sys.stderr)
        sys.exit(1)
    print("Exported {} ({})".format(options.out, export_format))


if __name__ == "__main__":
    main()
