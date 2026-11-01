#!/usr/bin/env python3
"""3D asset tooling using only the Python standard library.

Commands:
  inspect         FILE.glb|FILE.gltf [--json]   structure, counts, bounds, materials, animations, and
                                                 structural validation (buffers, accessors, indices)
  make-primitive  --shape box|plane|uvsphere|cylinder --out FILE.glb [--size X Y Z] [--color #rrggbb]
                  [--segments N] [--rings N]     a valid GLB with positions, normals, UVs and indices
  stl-check       FILE.stl [--json]              print readiness: watertight, manifold, orientation,
                                                 degenerate faces, volume, bounding box
  obj-to-glb      FILE.obj --out FILE.glb        triangulated mesh with normals and UVs (materials not kept)

glTF conventions used: right-handed coordinates, +Y up, meters, counter-clockwise
front faces, baseColorFactor in linear color. Validation here is structural;
run the Khronos glTF-Validator for full conformance when it is available.
Exit status: 0 success, 1 problems found or invalid input, 2 usage error.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERSION = "2.0.0"
GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
TYPE_SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
MODES = {0: "points", 1: "lines", 2: "line loop", 3: "line strip", 4: "triangles", 5: "triangle strip", 6: "triangle fan"}
MAX_FILE_BYTES = 512 * 1024 * 1024
Vec3 = Tuple[float, float, float]


class AssetError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Small vector helpers
# ---------------------------------------------------------------------------

def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def normalize(a: Vec3) -> Vec3:
    length = math.sqrt(dot(a, a))
    return (a[0] / length, a[1] / length, a[2] / length) if length > 0 else (0.0, 0.0, 0.0)


def srgb_to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


# ---------------------------------------------------------------------------
# GLB writing
# ---------------------------------------------------------------------------

class Mesh:
    def __init__(self, name: str) -> None:
        self.name = name
        self.positions: List[Vec3] = []
        self.normals: List[Vec3] = []
        self.uvs: List[Tuple[float, float]] = []
        self.indices: List[int] = []

    def add_vertex(self, position: Vec3, normal: Vec3, uv: Tuple[float, float]) -> int:
        self.positions.append(position)
        self.normals.append(normal)
        self.uvs.append(uv)
        return len(self.positions) - 1


def _pad(data: bytes, filler: bytes) -> bytes:
    return data + filler * ((4 - len(data) % 4) % 4)


def build_glb(mesh: Mesh, color: Tuple[float, float, float] = (0.8, 0.8, 0.8), metallic: float = 0.0,
              roughness: float = 0.8) -> bytes:
    if not mesh.positions or not mesh.indices:
        raise AssetError("mesh is empty")
    count = len(mesh.positions)
    if max(mesh.indices) >= count:
        raise AssetError("index out of range while building the mesh")
    blobs: List[bytes] = []
    views: List[Dict[str, Any]] = []
    accessors: List[Dict[str, Any]] = []
    offset = 0

    def add_view(data: bytes, target: int) -> int:
        nonlocal offset
        padded = _pad(data, b"\x00")
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        blobs.append(padded)
        offset += len(padded)
        return len(views) - 1

    flat_pos = [c for p in mesh.positions for c in p]
    view = add_view(struct.pack("<{}f".format(len(flat_pos)), *flat_pos), 34962)
    mins = [min(p[i] for p in mesh.positions) for i in range(3)]
    maxs = [max(p[i] for p in mesh.positions) for i in range(3)]
    # Accessor min/max must equal the stored float32 values exactly.
    as_f32 = [struct.unpack("<f", struct.pack("<f", v))[0] for v in mins + maxs]
    accessors.append({"bufferView": view, "componentType": 5126, "count": count, "type": "VEC3",
                      "min": as_f32[:3], "max": as_f32[3:]})
    flat_nrm = [c for n in mesh.normals for c in n]
    accessors.append({"bufferView": add_view(struct.pack("<{}f".format(len(flat_nrm)), *flat_nrm), 34962),
                      "componentType": 5126, "count": count, "type": "VEC3"})
    flat_uv = [c for uv in mesh.uvs for c in uv]
    accessors.append({"bufferView": add_view(struct.pack("<{}f".format(len(flat_uv)), *flat_uv), 34962),
                      "componentType": 5126, "count": count, "type": "VEC2"})
    wide = count > 65535
    index_data = struct.pack("<{}{}".format(len(mesh.indices), "I" if wide else "H"), *mesh.indices)
    accessors.append({"bufferView": add_view(index_data, 34963), "componentType": 5125 if wide else 5123,
                      "count": len(mesh.indices), "type": "SCALAR"})
    document = {
        "asset": {"version": "2.0", "generator": "mych-3d-design gltf_tool.py {}".format(VERSION)},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": mesh.name}],
        "meshes": [{"name": mesh.name, "primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                                                       "indices": 3, "material": 0, "mode": 4}]}],
        "materials": [{"name": mesh.name + "-material", "pbrMetallicRoughness": {
            "baseColorFactor": [round(color[0], 6), round(color[1], 6), round(color[2], 6), 1.0],
            "metallicFactor": metallic, "roughnessFactor": roughness}}],
        "buffers": [{"byteLength": offset}], "bufferViews": views, "accessors": accessors,
    }
    json_chunk = _pad(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = b"".join(blobs)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    return (struct.pack("<III", GLB_MAGIC, 2, total) + struct.pack("<II", len(json_chunk), CHUNK_JSON) + json_chunk
            + struct.pack("<II", len(bin_chunk), CHUNK_BIN) + bin_chunk)


# ---------------------------------------------------------------------------
# Primitive shapes (counter-clockwise front faces, outward normals)
# ---------------------------------------------------------------------------

def make_box(sx: float, sy: float, sz: float) -> Mesh:
    mesh = Mesh("box")
    faces = [((1, 0, 0), (0, 0, -1), (0, 1, 0)), ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
             ((0, 1, 0), (1, 0, 0), (0, 0, -1)), ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
             ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (-1, 0, 0), (0, 1, 0))]
    scale = (sx, sy, sz)
    for normal, u, v in faces:
        corners = []
        for cu, cv, uv in ((-1, -1, (0.0, 1.0)), (1, -1, (1.0, 1.0)), (1, 1, (1.0, 0.0)), (-1, 1, (0.0, 0.0))):
            point = tuple((normal[i] * 0.5 + u[i] * 0.5 * cu + v[i] * 0.5 * cv) * scale[i] for i in range(3))
            corners.append(mesh.add_vertex(point, tuple(float(c) for c in normal), uv))  # type: ignore[arg-type]
        a, b, c, d = corners
        mesh.indices += [a, b, c, a, c, d]
    return mesh


def make_plane(sx: float, sz: float) -> Mesh:
    mesh = Mesh("plane")
    for x, z, uv in ((-0.5, 0.5, (0.0, 1.0)), (0.5, 0.5, (1.0, 1.0)), (0.5, -0.5, (1.0, 0.0)), (-0.5, -0.5, (0.0, 0.0))):
        mesh.add_vertex((x * sx, 0.0, z * sz), (0.0, 1.0, 0.0), uv)
    mesh.indices = [0, 1, 2, 0, 2, 3]
    return mesh


def make_uvsphere(radius: float, segments: int, rings: int) -> Mesh:
    mesh = Mesh("uvsphere")
    for i in range(rings + 1):
        theta = math.pi * i / rings
        for j in range(segments + 1):
            phi = 2 * math.pi * j / segments
            normal = (math.sin(theta) * math.cos(phi), math.cos(theta), math.sin(theta) * math.sin(phi))
            mesh.add_vertex(tuple(radius * c for c in normal), normal, (j / segments, i / rings))  # type: ignore[arg-type]
    stride = segments + 1
    for i in range(rings):
        for j in range(segments):
            a = i * stride + j
            b = a + stride
            if i != 0:
                mesh.indices += [a, a + 1, b]
            if i != rings - 1:
                mesh.indices += [a + 1, b + 1, b]
    return mesh


def make_cylinder(radius: float, height: float, segments: int) -> Mesh:
    mesh = Mesh("cylinder")
    half = height / 2
    for j in range(segments + 1):
        phi = 2 * math.pi * j / segments
        normal = (math.cos(phi), 0.0, math.sin(phi))
        mesh.add_vertex((radius * normal[0], -half, radius * normal[2]), normal, (j / segments, 1.0))
        mesh.add_vertex((radius * normal[0], half, radius * normal[2]), normal, (j / segments, 0.0))
    for j in range(segments):
        bottom, top, bottom_next, top_next = 2 * j, 2 * j + 1, 2 * j + 2, 2 * j + 3
        mesh.indices += [bottom, top, bottom_next, bottom_next, top, top_next]
    for y, normal in ((half, (0.0, 1.0, 0.0)), (-half, (0.0, -1.0, 0.0))):
        center = mesh.add_vertex((0.0, y, 0.0), normal, (0.5, 0.5))
        ring = []
        for j in range(segments):
            phi = 2 * math.pi * j / segments
            ring.append(mesh.add_vertex((radius * math.cos(phi), y, radius * math.sin(phi)), normal,
                                        (0.5 + 0.5 * math.cos(phi), 0.5 + 0.5 * math.sin(phi))))
        for j in range(segments):
            current, following = ring[j], ring[(j + 1) % segments]
            mesh.indices += [center, following, current] if y > 0 else [center, current, following]
    return mesh


# ---------------------------------------------------------------------------
# Reading and validating glTF / GLB
# ---------------------------------------------------------------------------

def load_gltf(path: Path) -> Tuple[Dict[str, Any], List[bytes], List[str]]:
    """Return the JSON document, buffer contents and loading problems."""
    if path.stat().st_size > MAX_FILE_BYTES:
        raise AssetError("{} is larger than {} bytes".format(path, MAX_FILE_BYTES))
    data = path.read_bytes()
    problems: List[str] = []
    glb_bin: Optional[bytes] = None
    if data[:4] == b"glTF":
        if len(data) < 20:
            raise AssetError("GLB file is truncated")
        magic, version, length = struct.unpack("<III", data[:12])
        if version != 2:
            raise AssetError("GLB container version {} is not 2".format(version))
        if length != len(data):
            problems.append("GLB header length {} does not match the file size {}".format(length, len(data)))
        pos = 12
        chunks = []
        while pos + 8 <= len(data):
            chunk_length, chunk_type = struct.unpack("<II", data[pos:pos + 8])
            if chunk_length % 4:
                problems.append("GLB chunk length {} is not 4-byte aligned".format(chunk_length))
            chunks.append((chunk_type, data[pos + 8:pos + 8 + chunk_length]))
            pos += 8 + chunk_length
        if not chunks or chunks[0][0] != CHUNK_JSON:
            raise AssetError("the first GLB chunk must be JSON")
        try:
            document = json.loads(chunks[0][1].decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise AssetError("GLB JSON chunk is not valid JSON: {}".format(exc)) from exc
        if len(chunks) > 1:
            if chunks[1][0] != CHUNK_BIN:
                problems.append("the second GLB chunk is not BIN")
            glb_bin = chunks[1][1]
    else:
        try:
            document = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise AssetError("{} is neither GLB nor glTF JSON: {}".format(path, exc)) from exc
    buffers: List[bytes] = []
    base = path.parent.resolve()
    for index, buffer in enumerate(document.get("buffers", [])):
        uri = buffer.get("uri")
        if uri is None:
            if glb_bin is None:
                problems.append("buffer {} has no uri and there is no GLB BIN chunk".format(index))
                buffers.append(b"")
            else:
                buffers.append(glb_bin)
        elif uri.startswith("data:"):
            try:
                buffers.append(base64.b64decode(uri.split(",", 1)[1]))
            except (ValueError, IndexError):
                problems.append("buffer {} has an invalid data URI".format(index))
                buffers.append(b"")
        else:
            target = (base / uri).resolve()
            try:
                target.relative_to(base)
            except ValueError:
                problems.append("buffer {} uri '{}' points outside the asset folder; not read".format(index, uri))
                buffers.append(b"")
                continue
            if not target.is_file():
                problems.append("buffer {} file '{}' is missing".format(index, uri))
                buffers.append(b"")
            else:
                buffers.append(target.read_bytes())
        if len(buffers[-1]) < buffer.get("byteLength", 0):
            problems.append("buffer {} holds {} bytes but declares byteLength {}".format(
                index, len(buffers[-1]), buffer.get("byteLength")))
    return document, buffers, problems


def read_accessor(document: Dict[str, Any], buffers: List[bytes], index: int) -> List[Tuple[float, ...]]:
    accessor = document["accessors"][index]
    fmt, size = COMPONENT[accessor["componentType"]]
    width = TYPE_SIZE[accessor["type"]]
    count = accessor["count"]
    if "bufferView" not in accessor:
        return [tuple([0.0] * width) for _ in range(count)]  # sparse-only or zero-filled accessor
    view = document["bufferViews"][accessor["bufferView"]]
    data = buffers[view["buffer"]]
    stride = view.get("byteStride") or size * width
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    values = []
    for i in range(count):
        offset = start + i * stride
        values.append(struct.unpack_from("<{}{}".format(width, fmt), data, offset))
    return values


def inspect(path: Path) -> Dict[str, Any]:
    document, buffers, problems = load_gltf(path)
    errors = list(problems)
    warnings: List[str] = []
    asset = document.get("asset") or {}
    if asset.get("version") != "2.0":
        errors.append("asset.version is {!r}, expected '2.0'".format(asset.get("version")))
    views = document.get("bufferViews", [])
    accessors = document.get("accessors", [])
    for index, view in enumerate(views):
        buffer_index = view.get("buffer", -1)
        if not 0 <= buffer_index < len(buffers):
            errors.append("bufferView {} refers to missing buffer {}".format(index, buffer_index))
            continue
        end = view.get("byteOffset", 0) + view.get("byteLength", 0)
        if end > len(buffers[buffer_index]):
            errors.append("bufferView {} ends at byte {} beyond buffer {} ({} bytes)".format(
                index, end, buffer_index, len(buffers[buffer_index])))
    for index, accessor in enumerate(accessors):
        if accessor.get("componentType") not in COMPONENT or accessor.get("type") not in TYPE_SIZE:
            errors.append("accessor {} has an invalid componentType or type".format(index))
            continue
        if "bufferView" in accessor:
            view_index = accessor["bufferView"]
            if not 0 <= view_index < len(views):
                errors.append("accessor {} refers to missing bufferView {}".format(index, view_index))
                continue
            view = views[view_index]
            size = COMPONENT[accessor["componentType"]][1]
            element = size * TYPE_SIZE[accessor["type"]]
            stride = view.get("byteStride") or element
            needed = accessor.get("byteOffset", 0) + stride * (accessor["count"] - 1) + element
            if needed > view.get("byteLength", 0):
                errors.append("accessor {} needs {} bytes but bufferView {} has {}".format(
                    index, needed, view_index, view.get("byteLength", 0)))
            if (view.get("byteOffset", 0) + accessor.get("byteOffset", 0)) % size:
                errors.append("accessor {} is not aligned to its component size".format(index))
    meshes_report = []
    total_triangles = 0
    bounds_min = [math.inf] * 3
    bounds_max = [-math.inf] * 3
    for mesh_index, mesh in enumerate(document.get("meshes", [])):
        prims = []
        for prim_index, prim in enumerate(mesh.get("primitives", [])):
            label = "mesh {} primitive {}".format(mesh_index, prim_index)
            attributes = prim.get("attributes", {})
            if "POSITION" not in attributes:
                errors.append("{} has no POSITION attribute".format(label))
                continue
            counts = {name: accessors[i]["count"] for name, i in attributes.items() if 0 <= i < len(accessors)}
            if len(set(counts.values())) > 1:
                errors.append("{} attributes have different counts: {}".format(label, counts))
            position = accessors[attributes["POSITION"]]
            vertex_count = position["count"]
            if "min" not in position or "max" not in position:
                errors.append("{} POSITION accessor lacks min and max (required by glTF 2.0)".format(label))
            else:
                for axis in range(3):
                    bounds_min[axis] = min(bounds_min[axis], position["min"][axis])
                    bounds_max[axis] = max(bounds_max[axis], position["max"][axis])
                if not errors:
                    values = read_accessor(document, buffers, attributes["POSITION"])
                    for axis in range(3):
                        actual_min = min(v[axis] for v in values)
                        actual_max = max(v[axis] for v in values)
                        if actual_min != position["min"][axis] or actual_max != position["max"][axis]:
                            errors.append("{} POSITION min/max do not match the data on axis {}".format(label, axis))
                            break
            mode = prim.get("mode", 4)
            index_count = None
            if "indices" in prim:
                index_accessor = accessors[prim["indices"]]
                if index_accessor.get("componentType") not in (5121, 5123, 5125):
                    errors.append("{} indices must use an unsigned integer type".format(label))
                index_count = index_accessor["count"]
                if not errors:
                    largest = max((v[0] for v in read_accessor(document, buffers, prim["indices"])), default=0)
                    if largest >= vertex_count:
                        errors.append("{} index {} is out of range for {} vertices".format(label, largest,
                                                                                          vertex_count))
            primitives_count = index_count if index_count is not None else vertex_count
            triangles = primitives_count // 3 if mode == 4 else max(0, primitives_count - 2) if mode in (5, 6) else 0
            total_triangles += triangles
            if "NORMAL" not in attributes and mode in (4, 5, 6):
                warnings.append("{} has no NORMAL attribute; viewers will compute flat normals".format(label))
            prims.append({"mode": MODES.get(mode, mode), "vertices": vertex_count, "indices": index_count,
                          "triangles": triangles, "attributes": sorted(attributes), "material": prim.get("material")})
        meshes_report.append({"name": mesh.get("name"), "primitives": prims})
    materials = []
    for material in document.get("materials", []):
        pbr = material.get("pbrMetallicRoughness", {})
        materials.append({"name": material.get("name"), "base_color": pbr.get("baseColorFactor", [1, 1, 1, 1]),
                          "metallic": pbr.get("metallicFactor", 1.0), "roughness": pbr.get("roughnessFactor", 1.0),
                          "textures": sorted(k for k in list(pbr) + list(material) if k.endswith("Texture"))})
    animations = []
    for animation in document.get("animations", []):
        duration = 0.0
        for sampler in animation.get("samplers", []):
            accessor = accessors[sampler["input"]] if sampler.get("input", -1) < len(accessors) else {}
            if accessor.get("max"):
                duration = max(duration, accessor["max"][0])
        animations.append({"name": animation.get("name"), "channels": len(animation.get("channels", [])),
                           "duration_s": duration})
    for index, image in enumerate(document.get("images", [])):
        uri = image.get("uri")
        if uri and not uri.startswith("data:"):
            target = (path.parent / uri).resolve()
            if not target.is_file():
                warnings.append("image {} file '{}' is missing".format(index, uri))
    required = document.get("extensionsRequired", [])
    if required:
        warnings.append("extensions required by this asset: {} (loaders without them will refuse it)".format(
            ", ".join(required)))
    has_bounds = bounds_min[0] != math.inf
    return {
        "file": str(path), "container": "glb" if path.read_bytes()[:4] == b"glTF" else "gltf",
        "generator": asset.get("generator"), "version": asset.get("version"),
        "scenes": len(document.get("scenes", [])), "nodes": len(document.get("nodes", [])),
        "meshes": meshes_report, "triangles": total_triangles, "materials": materials,
        "textures": len(document.get("textures", [])), "images": len(document.get("images", [])),
        "animations": animations, "skins": len(document.get("skins", [])),
        "extensions_used": document.get("extensionsUsed", []),
        "bounds": {"min": bounds_min, "max": bounds_max,
                   "size": [round(bounds_max[i] - bounds_min[i], 6) for i in range(3)]} if has_bounds else None,
        "errors": errors, "warnings": warnings, "ok": not errors,
    }


# ---------------------------------------------------------------------------
# STL checks
# ---------------------------------------------------------------------------

def read_stl(path: Path) -> List[Tuple[Vec3, Vec3, Vec3]]:
    data = path.read_bytes()
    if len(data) >= 84:
        count = struct.unpack("<I", data[80:84])[0]
        if 84 + count * 50 == len(data):
            triangles = []
            for i in range(count):
                values = struct.unpack_from("<12f", data, 84 + i * 50)
                triangles.append((values[3:6], values[6:9], values[9:12]))
            return triangles  # type: ignore[return-value]
    text = data.decode("utf-8", "replace")
    if not text.lstrip().lower().startswith("solid"):
        raise AssetError("{} is neither binary STL (size mismatch) nor ASCII STL".format(path))
    numbers = r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
    vertices = [tuple(float(v) for v in match) for match in
                re.findall(r"vertex\s+" + numbers + r"\s+" + numbers + r"\s+" + numbers, text)]
    if len(vertices) % 3:
        raise AssetError("ASCII STL has {} vertices, not a multiple of 3".format(len(vertices)))
    return [(vertices[i], vertices[i + 1], vertices[i + 2]) for i in range(0, len(vertices), 3)]  # type: ignore[misc]


def stl_check(path: Path, weld: float = 1e-5) -> Dict[str, Any]:
    triangles = read_stl(path)
    if not triangles:
        raise AssetError("{} contains no triangles".format(path))
    key_of: Dict[Tuple[int, int, int], int] = {}

    def vertex_id(point: Vec3) -> int:
        key = (round(point[0] / weld), round(point[1] / weld), round(point[2] / weld))
        return key_of.setdefault(key, len(key_of))

    undirected: Dict[Tuple[int, int], int] = {}
    directed: Dict[Tuple[int, int], int] = {}
    degenerate = 0
    volume = 0.0
    area = 0.0
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for a, b, c in triangles:
        for point in (a, b, c):
            for axis in range(3):
                lo[axis] = min(lo[axis], point[axis])
                hi[axis] = max(hi[axis], point[axis])
        ids = (vertex_id(a), vertex_id(b), vertex_id(c))
        face_area = 0.5 * math.sqrt(dot(cross(sub(b, a), sub(c, a)), cross(sub(b, a), sub(c, a))))
        if len(set(ids)) < 3 or face_area < 1e-12:
            degenerate += 1
            continue
        area += face_area
        volume += dot(a, cross(b, c)) / 6.0
        for start, end in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            directed[(start, end)] = directed.get((start, end), 0) + 1
            key = (min(start, end), max(start, end))
            undirected[key] = undirected.get(key, 0) + 1
    boundary = sum(1 for n in undirected.values() if n == 1)
    non_manifold = sum(1 for n in undirected.values() if n > 2)
    # In a consistently oriented surface each directed edge occurs once; twice means two faces disagree.
    flipped = sum(1 for n in directed.values() if n > 1)
    watertight = boundary == 0 and non_manifold == 0
    errors, warnings = [], []
    if boundary:
        errors.append("{} open (boundary) edges: the mesh has holes and is not watertight".format(boundary))
    if non_manifold:
        errors.append("{} non-manifold edges (shared by more than two faces)".format(non_manifold))
    if flipped:
        errors.append("{} edges with inconsistent face orientation (flipped normals)".format(flipped))
    if degenerate:
        warnings.append("{} degenerate (zero-area) triangles were ignored".format(degenerate))
    if watertight and not flipped and volume < 0:
        errors.append("signed volume is negative: all normals point inward; flip the faces")
    return {"file": str(path), "triangles": len(triangles), "vertices": len(key_of), "degenerate": degenerate,
            "open_edges": boundary, "non_manifold_edges": non_manifold, "orientation_conflicts": flipped,
            "watertight": watertight, "volume": round(abs(volume), 6), "surface_area": round(area, 6),
            "bounds": {"min": lo, "max": hi, "size": [round(hi[i] - lo[i], 6) for i in range(3)]},
            "units_note": "STL has no units; 3D printing tools usually assume millimeters",
            "errors": errors, "warnings": warnings, "ok": not errors}


# ---------------------------------------------------------------------------
# OBJ import
# ---------------------------------------------------------------------------

def obj_to_mesh(path: Path) -> Mesh:
    positions: List[Vec3] = []
    uvs: List[Tuple[float, float]] = []
    normals: List[Vec3] = []
    mesh = Mesh(path.stem)
    corner_ids: Dict[Tuple[int, int, int, int], int] = {}

    def resolve(token: str, size: int, number: int) -> int:
        value = int(token)
        index = value - 1 if value > 0 else size + value
        if not 0 <= index < size:
            raise AssetError("{}:{}: index {} out of range".format(path.name, number, value))
        return index

    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        try:
            if parts[0] == "v":
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == "vt":
                uvs.append((float(parts[1]), float(parts[2]) if len(parts) > 2 else 0.0))
            elif parts[0] == "vn":
                normals.append(normalize((float(parts[1]), float(parts[2]), float(parts[3]))))
            elif parts[0] == "f":
                corners = []
                for token in parts[1:]:
                    fields = token.split("/")
                    vi = resolve(fields[0], len(positions), number)
                    ti = resolve(fields[1], len(uvs), number) if len(fields) > 1 and fields[1] else -1
                    ni = resolve(fields[2], len(normals), number) if len(fields) > 2 and fields[2] else -1
                    corners.append((vi, ti, ni))
                if len(corners) < 3:
                    raise AssetError("{}:{}: a face needs at least 3 vertices".format(path.name, number))
                face_normal = normalize(cross(sub(positions[corners[1][0]], positions[corners[0][0]]),
                                              sub(positions[corners[2][0]], positions[corners[0][0]])))
                face_key = len(mesh.indices)
                ids = []
                for vi, ti, ni in corners:
                    key = (vi, ti, ni, face_key if ni < 0 else -1)
                    if key not in corner_ids:
                        uv = uvs[ti] if ti >= 0 else (0.0, 0.0)
                        corner_ids[key] = mesh.add_vertex(positions[vi], normals[ni] if ni >= 0 else face_normal,
                                                          (uv[0], 1.0 - uv[1]))
                    ids.append(corner_ids[key])
                for k in range(1, len(ids) - 1):
                    mesh.indices += [ids[0], ids[k], ids[k + 1]]
        except (ValueError, IndexError) as exc:
            raise AssetError("{}:{}: cannot parse {!r}".format(path.name, number, line.strip()[:60])) from exc
    if not mesh.indices:
        raise AssetError("{} contains no faces".format(path))
    return mesh


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def parse_color(text: str) -> Tuple[float, float, float]:
    match = re.fullmatch(r"#?([0-9a-fA-F]{6})", text)
    if not match:
        raise AssetError("color must look like #rrggbb", 2)
    rgb = bytes.fromhex(match.group(1))
    return tuple(srgb_to_linear(c / 255.0) for c in rgb)  # type: ignore[return-value]


def print_report(report: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2))
        return
    for key, value in report.items():
        if key in ("errors", "warnings"):
            continue
        print("{}: {}".format(key, json.dumps(value) if isinstance(value, (dict, list)) else value))
    for item in report["errors"]:
        print("error: " + item)
    for item in report["warnings"]:
        print("warning: " + item)
    print("Result: {}".format("PASS" if report["ok"] else "FAIL"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="glTF, STL and OBJ tooling (standard library only).",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub_parsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub_parsers.required = True
    p = sub_parsers.add_parser("inspect", help="describe and structurally validate a .glb or .gltf file")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p = sub_parsers.add_parser("make-primitive", help="write a primitive mesh as GLB")
    p.add_argument("--shape", choices=("box", "plane", "uvsphere", "cylinder"), required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--size", nargs=3, type=float, default=[1.0, 1.0, 1.0], metavar=("X", "Y", "Z"),
                   help="box extents; plane uses X and Z; sphere radius is X/2; cylinder radius X/2 and height Y")
    p.add_argument("--segments", type=int, default=32)
    p.add_argument("--rings", type=int, default=16)
    p.add_argument("--color", default="#cccccc", help="base color in sRGB hex (stored linear)")
    p.add_argument("--metallic", type=float, default=0.0)
    p.add_argument("--roughness", type=float, default=0.8)
    p = sub_parsers.add_parser("stl-check", help="check an STL mesh for 3D printing")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p = sub_parsers.add_parser("obj-to-glb", help="convert an OBJ mesh to GLB")
    p.add_argument("file")
    p.add_argument("--out", required=True)
    p.add_argument("--color", default="#cccccc")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            report = inspect(Path(args.file))
            print_report(report, args.json)
            return 0 if report["ok"] else 1
        if args.command == "stl-check":
            report = stl_check(Path(args.file))
            print_report(report, args.json)
            return 0 if report["ok"] else 1
        if args.command == "make-primitive":
            x, y, z = args.size
            if min(x, y, z) <= 0 or not 3 <= args.segments <= 512 or not 2 <= args.rings <= 512:
                raise AssetError("sizes must be positive; segments 3-512; rings 2-512", 2)
            mesh = {"box": lambda: make_box(x, y, z), "plane": lambda: make_plane(x, z),
                    "uvsphere": lambda: make_uvsphere(x / 2, args.segments, args.rings),
                    "cylinder": lambda: make_cylinder(x / 2, y, args.segments)}[args.shape]()
            blob = build_glb(mesh, parse_color(args.color), args.metallic, args.roughness)
        else:
            mesh = obj_to_mesh(Path(args.file))
            blob = build_glb(mesh, parse_color(args.color))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(blob)
        print("Wrote {} ({} vertices, {} triangles, {} bytes)".format(out, len(mesh.positions), len(mesh.indices) // 3,
                                                                    len(blob)))
        return 0
    except AssetError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return exc.code
    except (OSError, KeyError, IndexError, struct.error) as exc:
        print("error: cannot process the file: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
