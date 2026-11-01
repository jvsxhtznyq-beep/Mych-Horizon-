"""Report mesh quality facts for a .blend scene as JSON (Blender's bundled Python).

Usage (headless):
  blender -b scene.blend --python blender_scene_report.py -- [--out report.json]

Reports per mesh object: triangles, n-gons, unapplied scale, missing UV maps,
non-manifold edges and loose vertices (via bmesh), and materials without image
textures. Not executed in the MYCH-HORIZON test environment (Blender is not
installed there): compile-checked only.
"""

import argparse
import json
import sys


def parse_args(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Report mesh quality facts as JSON.")
    parser.add_argument("--out", help="write the report to this file instead of printing it")
    return parser.parse_args(args)


def mesh_facts(obj, bmesh):
    mesh = obj.data
    mesh.calc_loop_triangles()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
        loose = sum(1 for vert in bm.verts if not vert.link_edges)
    finally:
        bm.free()
    textures = []
    for slot in obj.material_slots:
        material = slot.material
        if material and material.use_nodes:
            textures += [node.image.name for node in material.node_tree.nodes
                         if node.type == "TEX_IMAGE" and node.image]
    return {
        "object": obj.name,
        "triangles": len(mesh.loop_triangles),
        "ngons": sum(1 for poly in mesh.polygons if len(poly.vertices) > 4),
        "unapplied_scale": [round(v, 4) for v in obj.scale] if any(abs(v - 1.0) > 1e-4 for v in obj.scale) else None,
        "uv_maps": [uv.name for uv in mesh.uv_layers],
        "non_manifold_edges": non_manifold,
        "loose_vertices": loose,
        "materials": [slot.material.name for slot in obj.material_slots if slot.material],
        "image_textures": textures,
    }


def main():
    import bmesh
    import bpy  # available only inside Blender

    options = parse_args(sys.argv)
    meshes = [mesh_facts(obj, bmesh) for obj in bpy.context.scene.objects if obj.type == "MESH"]
    report = {"blend_file": bpy.data.filepath, "blender": bpy.app.version_string, "meshes": meshes,
              "total_triangles": sum(item["triangles"] for item in meshes)}
    text = json.dumps(report, indent=2)
    if options.out:
        with open(options.out, "w", encoding="utf-8") as stream:
            stream.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
