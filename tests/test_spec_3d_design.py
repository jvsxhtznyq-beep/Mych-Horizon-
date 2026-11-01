"""Tests for the mych-3d-design specialist's gltf_tool.py and Blender templates.

When the Khronos glTF-Validator is available (set GLTF_VALIDATOR_JS to a
Node script that prints its JSON report, as used in the MYCH-HORIZON
evaluation), generated files are also checked by it. Blender templates are
compile-checked only: Blender is not part of the test environment.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import py_compile
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

SKILL = REPO_ROOT / "specialists" / "mych-3d-design"
SCRIPT = SKILL / "scripts" / "gltf_tool.py"


def load():
    name = "mych_gltf_tool"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


g = load()


def run(*args):
    return subprocess.run([sys.executable, "-B", str(SCRIPT)] + [str(a) for a in args], capture_output=True, text=True)


def write_stl(path: Path, triangles, ascii_format=False):
    if ascii_format:
        lines = ["solid test"]
        for tri in triangles:
            lines += ["facet normal 0 0 0", " outer loop"] + ["  vertex {} {} {}".format(*v) for v in tri] + \
                     [" endloop", "endfacet"]
        lines.append("endsolid test")
        path.write_text("\n".join(lines) + "\n")
        return
    data = bytearray(b"\0" * 80) + struct.pack("<I", len(triangles))
    for tri in triangles:
        data += struct.pack("<12fH", 0, 0, 0, *tri[0], *tri[1], *tri[2], 0)
    path.write_bytes(bytes(data))


def mesh_triangles(mesh):
    return [tuple(mesh.positions[i] for i in mesh.indices[k:k + 3]) for k in range(0, len(mesh.indices), 3)]


class PrimitiveTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_primitives_are_valid_outward_and_closed(self):
        for shape in ("box", "plane", "uvsphere", "cylinder"):
            with self.subTest(shape=shape):
                out = self.dir / (shape + ".glb")
                result = run("make-primitive", "--shape", shape, "--out", out, "--size", "2", "1", "0.5")
                self.assertEqual(result.returncode, 0, result.stderr)
                report = g.inspect(out)
                self.assertTrue(report["ok"], report["errors"])
                self.assertEqual(report["container"], "glb")
                self.assertGreater(report["triangles"], 0)
        box = g.inspect(self.dir / "box.glb")
        self.assertEqual(box["bounds"]["size"], [2.0, 1.0, 0.5])
        self.assertEqual(box["triangles"], 12)
        for mesh in (g.make_box(1, 1, 1), g.make_uvsphere(1, 16, 8), g.make_cylinder(1, 2, 12)):
            stl = self.dir / (mesh.name + ".stl")
            write_stl(stl, mesh_triangles(mesh))
            check = g.stl_check(stl)
            self.assertTrue(check["watertight"], (mesh.name, check))
            self.assertEqual(check["orientation_conflicts"], 0, mesh.name)
            self.assertTrue(check["ok"], (mesh.name, check["errors"]))
            normals_outward = all(g.dot(g.cross(g.sub(b, a), g.sub(c, a)), a) > -1e-9
                                  for a, b, c in mesh_triangles(mesh))
            self.assertTrue(normals_outward, mesh.name)

    def test_color_is_stored_linear(self):
        linear = g.parse_color("#808080")
        self.assertAlmostEqual(linear[0], 0.2158605, places=5)

    def test_glb_layout_is_aligned(self):
        blob = g.build_glb(g.make_box(1, 1, 1))
        magic, version, length = struct.unpack("<III", blob[:12])
        self.assertEqual((magic, version, length), (g.GLB_MAGIC, 2, len(blob)))
        json_length, json_type = struct.unpack("<II", blob[12:20])
        self.assertEqual(json_type, g.CHUNK_JSON)
        self.assertEqual(json_length % 4, 0)
        bin_length, bin_type = struct.unpack("<II", blob[20 + json_length:28 + json_length])
        self.assertEqual((bin_type, bin_length % 4), (g.CHUNK_BIN, 0))

    @unittest.skipUnless(os.environ.get("GLTF_VALIDATOR_JS") and shutil.which("node"),
                         "Khronos glTF-Validator not configured (set GLTF_VALIDATOR_JS)")
    def test_khronos_validator_reports_no_errors_or_warnings(self):
        files = []
        for shape in ("box", "plane", "uvsphere", "cylinder"):
            out = self.dir / (shape + ".glb")
            run("make-primitive", "--shape", shape, "--out", out)
            files.append(out)
        obj = self.dir / "quad.obj"
        obj.write_text("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\nf 1/1 2/2 3/3 4/4\n")
        run("obj-to-glb", obj, "--out", self.dir / "quad.glb")
        files.append(self.dir / "quad.glb")
        result = subprocess.run(["node", os.environ["GLTF_VALIDATOR_JS"]] + [str(f) for f in files],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        for item in json.loads(result.stdout):
            self.assertEqual((item["errors"], item["warnings"]), (0, 0), item)


class InspectValidationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def gltf_with(self, mutate):
        blob = g.build_glb(g.make_box(1, 1, 1))
        json_length = struct.unpack("<I", blob[12:16])[0]
        document = json.loads(blob[20:20 + json_length])
        binary = blob[28 + json_length:]
        bin_path = self.dir / "box.bin"
        bin_path.write_bytes(binary)
        document["buffers"][0]["uri"] = "box.bin"
        mutate(document)
        path = self.dir / "box.gltf"
        path.write_text(json.dumps(document))
        return path

    def test_separate_gltf_reads_external_buffer(self):
        self.assertTrue(g.inspect(self.gltf_with(lambda d: None))["ok"])

    def test_structural_errors_are_reported(self):
        cases = {
            "bad index": (lambda d: d["accessors"][3].update(componentType=5126), "unsigned integer type"),
            "minmax": (lambda d: d["accessors"][0].pop("min"), "lacks min and max"),
            "wrong minmax": (lambda d: d["accessors"][0].update(max=[9, 9, 9]), "do not match the data"),
            "short view": (lambda d: d["bufferViews"][0].update(byteLength=12), "needs 288 bytes"),
            "version": (lambda d: d["asset"].update(version="1.0"), "expected '2.0'"),
            "traversal": (lambda d: d["buffers"][0].update(uri="../outside.bin"), "outside the asset folder"),
        }
        for label, (mutate, expected) in cases.items():
            with self.subTest(label=label):
                report = g.inspect(self.gltf_with(mutate))
                self.assertFalse(report["ok"])
                self.assertTrue(any(expected in e for e in report["errors"]), report["errors"])

    def test_cli_exit_codes(self):
        bad = self.gltf_with(lambda d: d["asset"].update(version="1.0"))
        self.assertEqual(run("inspect", bad).returncode, 1)
        self.assertEqual(run("make-primitive", "--shape", "box", "--out", self.dir / "x.glb",
                             "--size", "0", "1", "1").returncode, 2)
        garbage = self.dir / "garbage.glb"
        garbage.write_bytes(b"not a model")
        self.assertEqual(run("inspect", garbage).returncode, 1)


class StlAndObjTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.cube = mesh_triangles(g.make_box(10, 10, 10))

    def tearDown(self):
        self._tmp.cleanup()

    def test_closed_cube_binary_and_ascii(self):
        for ascii_format in (False, True):
            path = self.dir / "cube{}.stl".format("-ascii" if ascii_format else "")
            write_stl(path, self.cube, ascii_format)
            report = g.stl_check(path)
            self.assertTrue(report["watertight"] and report["ok"], report)
            self.assertAlmostEqual(report["volume"], 1000.0, places=3)
            self.assertEqual(report["bounds"]["size"], [10.0, 10.0, 10.0])

    def test_holes_flipped_faces_and_inverted_normals(self):
        open_box = self.dir / "open.stl"
        write_stl(open_box, self.cube[:-2])
        report = g.stl_check(open_box)
        self.assertFalse(report["watertight"])
        self.assertEqual(report["open_edges"], 4)
        flipped = self.dir / "flipped.stl"
        a, b, c = self.cube[0]
        write_stl(flipped, [(a, c, b)] + self.cube[1:])
        self.assertGreater(g.stl_check(flipped)["orientation_conflicts"], 0)
        inverted = self.dir / "inverted.stl"
        write_stl(inverted, [(a, c, b) for a, b, c in self.cube])
        result = g.stl_check(inverted)
        self.assertTrue(any("normals point inward" in e for e in result["errors"]))
        self.assertEqual(run("stl-check", inverted).returncode, 1)

    def test_obj_conversion_with_quads_negative_indices_and_missing_normals(self):
        obj = self.dir / "cube.obj"
        vertices = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
        lines = ["# cube", *["v {} {} {}".format(*v) for v in vertices]]
        faces = [(1, 2, 4, 3), (5, 7, 8, 6), (1, 5, 6, 2), (3, 4, 8, 7), (1, 3, 7, 5), (2, 6, 8, 4)]
        lines += ["f " + " ".join(str(i - 9) for i in face) for face in faces]  # negative (relative) indices
        obj.write_text("\n".join(lines) + "\n")
        result = run("obj-to-glb", obj, "--out", self.dir / "cube.glb")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = g.inspect(self.dir / "cube.glb")
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["triangles"], 12)
        bad = self.dir / "bad.obj"
        bad.write_text("v 0 0 0\nf 1 2 3\n")
        failed = run("obj-to-glb", bad, "--out", self.dir / "bad.glb")
        self.assertEqual(failed.returncode, 1)
        self.assertIn("out of range", failed.stderr)


class BlenderTemplateTest(unittest.TestCase):
    """Blender is not installed in the test environment: these checks are static."""

    def test_templates_compile_and_import_bpy_only_inside_main(self):
        for name in ("blender_export_gltf.py", "blender_scene_report.py"):
            with self.subTest(name=name):
                path = SKILL / "scripts" / name
                with tempfile.TemporaryDirectory() as tmp:
                    py_compile.compile(str(path), cfile=str(Path(tmp) / "x.pyc"), doraise=True)
                tree = ast.parse(path.read_text(encoding="utf-8"))
                top_imports = [alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
                               for alias in node.names]
                self.assertNotIn("bpy", top_imports)
                self.assertTrue(any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body))
                source = path.read_text(encoding="utf-8")
                self.assertIn('argv.index("--")', source)
                for forbidden in ("subprocess", "urllib", "socket", "eval(", "exec("):
                    self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
