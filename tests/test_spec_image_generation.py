"""Tests for the mych-image-generation specialist's imagegen.py.

Generation is tested against local stub servers that imitate the documented
request and response shapes of ComfyUI and an OpenAI-style images endpoint.
No real generation service is contacted.
"""

from __future__ import annotations

import base64
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from support import REPO_ROOT

SKILL = REPO_ROOT / "specialists" / "mych-image-generation"
SCRIPT = SKILL / "scripts" / "imagegen.py"
WORKFLOW = SKILL / "assets" / "comfyui-txt2img-api.json"

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


def tiny_png() -> bytes:
    sys.path.insert(0, str(REPO_ROOT / "specialists" / "mych-pixel-art" / "scripts"))
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        import pixel_tool  # noqa: E402
    finally:
        sys.path.pop(0)
        sys.dont_write_bytecode = previous
    image = pixel_tool.Image(2, 2)
    image.set(0, 0, (255, 0, 0, 255))
    return pixel_tool.encode_png(image)


PNG = tiny_png()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Stub:
    """A tiny HTTP server whose behavior is a function of (method, path, body)."""

    def __init__(self, handler):
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self, method):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                stub.requests.append({"method": method, "path": self.path, "headers": dict(self.headers),
                                      "body": json.loads(body) if body else None})
                status, content_type, payload = handler(method, self.path, stub.requests[-1]["body"])
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                self.respond("GET")

            def do_POST(self):
                self.respond("POST")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:{}".format(self.server.server_address[1])
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def comfy_handler(state):
    def handle(method, path, body):
        parsed = urlparse(path)
        if method == "POST" and parsed.path == "/prompt":
            state["graph"] = body["prompt"]
            return 200, "application/json", json.dumps({"prompt_id": "abc123", "number": 1, "node_errors": {}}).encode()
        if method == "GET" and parsed.path == "/history/abc123":
            state["polls"] = state.get("polls", 0) + 1
            if state.get("fail"):
                return 200, "application/json", json.dumps({"abc123": {"status": {"status_str": "error",
                                                                                  "messages": ["OOM"]}}}).encode()
            if state["polls"] < 2:
                return 200, "application/json", b"{}"
            return 200, "application/json", json.dumps({"abc123": {"outputs": {"9": {"images": [
                {"filename": "mych_00001_.png", "subfolder": "", "type": "output"}]}}, "status": {
                "status_str": "success"}}}).encode()
        if method == "GET" and parsed.path == "/view":
            state["view_query"] = parse_qs(parsed.query)
            return 200, "image/png", PNG
        if parsed.path == "/system_stats":
            return 200, "application/json", b"{}"
        return 404, "text/plain", b"not found"
    return handle


def openai_handler(method, path, body):
    if method == "POST" and path == "/v1/images/generations":
        return 200, "application/json", json.dumps({"data": [{"b64_json": base64.b64encode(PNG).decode()}]}).encode()
    return 404, "text/plain", b"not found"


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in (
        "OPENAI_API_KEY", "STABILITY_API_KEY", "REPLICATE_API_TOKEN", "FAL_KEY", "GEMINI_API_KEY", "BFL_API_KEY")}
    env.update(extra)
    return env


def run(*args, env=None, python_flags=("-B",)):
    return subprocess.run([sys.executable, *python_flags, str(SCRIPT)] + [str(a) for a in args], capture_output=True,
                          text=True, env=env or clean_env(), timeout=120)


class HonestyTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_detect_reports_no_backend_honestly(self):
        result = run("detect", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        local = next(b for b in report["backends"] if b["id"] == "diffusers-local")
        if local["available"]:
            self.skipTest("this machine has a local diffusers backend")
        self.assertFalse(report["generation_available"])
        self.assertIn("No image will be generated", report["statement"])

    def test_auto_without_backend_generates_nothing_and_exits_3(self):
        out = self.dir / "out"
        closed = "http://127.0.0.1:{}".format(free_port())
        result = run("generate", "--prompt", "a red fox", "--out", out, "--base-url", closed,
                     "--workflow", WORKFLOW)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("No image was generated", result.stderr)
        self.assertFalse(out.exists())

    def test_openai_without_key_exits_3(self):
        result = run("generate", "--backend", "openai", "--model", "test-model", "--prompt", "x",
                     "--out", self.dir / "o")
        self.assertEqual(result.returncode, 3)
        self.assertIn("no image was generated", result.stderr)


class BackendTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_comfyui_flow_substitutes_placeholders_and_records_provenance(self):
        state = {}
        stub = Stub(comfy_handler(state))
        try:
            result = run("generate", "--backend", "comfyui", "--base-url", stub.url, "--workflow", WORKFLOW,
                         "--checkpoint", "sdxl_base.safetensors", "--prompt", "a red fox in snow", "--negative", "blurry",
                         "--seed", "42", "--size", "768x512", "--out", self.dir / "out", "--name", "fox", "--poll", "0.05")
        finally:
            stub.close()
        self.assertEqual(result.returncode, 0, result.stderr)
        graph = state["graph"]
        self.assertEqual(graph["3"]["inputs"]["seed"], 42)
        self.assertEqual(graph["5"]["inputs"]["width"], 768)
        self.assertEqual(graph["6"]["inputs"]["text"], "a red fox in snow")
        self.assertEqual(graph["7"]["inputs"]["text"], "blurry")
        self.assertEqual(graph["4"]["inputs"]["ckpt_name"], "sdxl_base.safetensors")
        self.assertEqual(state["view_query"]["filename"], ["mych_00001_.png"])
        image = self.dir / "out" / "fox-0.png"
        self.assertEqual(image.read_bytes(), PNG)
        record = json.loads((self.dir / "out" / "fox-0.provenance.json").read_text())
        self.assertEqual((record["backend"], record["seed"], record["prompt_id"]), ("comfyui", 42, "abc123"))
        import hashlib
        self.assertEqual(record["sha256"], hashlib.sha256(PNG).hexdigest())

    def test_comfyui_missing_placeholder_and_server_error(self):
        result = run("generate", "--backend", "comfyui", "--workflow", WORKFLOW, "--prompt", "x", "--out",
                     self.dir / "o", "--base-url", "http://127.0.0.1:9")
        self.assertEqual(result.returncode, 2)
        self.assertIn("CHECKPOINT", result.stderr)
        state = {"fail": True}
        stub = Stub(comfy_handler(state))
        try:
            failed = run("generate", "--backend", "comfyui", "--base-url", stub.url, "--workflow", WORKFLOW,
                         "--checkpoint", "c", "--prompt", "x", "--out", self.dir / "o2", "--poll", "0.05")
        finally:
            stub.close()
        self.assertEqual(failed.returncode, 1)
        self.assertIn("OOM", failed.stderr)
        self.assertFalse((self.dir / "o2").exists())

    def test_openai_style_endpoint_and_dry_run(self):
        stub = Stub(openai_handler)
        try:
            dry = run("generate", "--backend", "openai", "--model", "test-model", "--prompt", "a lighthouse",
                      "--out", self.dir / "dry", "--base-url", stub.url, "--dry-run",
                      env=clean_env(OPENAI_API_KEY="sk-secret-value"))
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertEqual(stub.requests, [])
            self.assertNotIn("sk-secret-value", dry.stdout)
            self.assertFalse((self.dir / "dry").exists())
            real = run("generate", "--backend", "openai", "--model", "test-model", "--prompt", "a lighthouse",
                       "--out", self.dir / "o", "--base-url", stub.url, "--name", "lh",
                       env=clean_env(OPENAI_API_KEY="sk-secret-value"))
        finally:
            stub.close()
        self.assertEqual(real.returncode, 0, real.stderr)
        self.assertEqual(stub.requests[0]["headers"]["Authorization"], "Bearer sk-secret-value")
        self.assertEqual(stub.requests[0]["body"]["model"], "test-model")
        self.assertEqual((self.dir / "o" / "lh-0.png").read_bytes(), PNG)
        record = json.loads((self.dir / "o" / "lh-0.provenance.json").read_text())
        self.assertEqual(record["model"], "test-model")
        self.assertNotIn("sk-secret-value", json.dumps(record))


@unittest.skipIf(Image is None, "Pillow not installed")
class ProcessingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.src = self.dir / "src.png"
        image = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
        for x in range(50, 150):
            for y in range(20, 80):
                image.putpixel((x, y), (200, 50, 50, 255))
        image.save(self.src)

    def tearDown(self):
        self._tmp.cleanup()

    def size_of(self, path):
        with Image.open(path) as image:
            return image.size, image.mode

    def test_resize_pad_trim_convert(self):
        self.assertEqual(run("process", "resize", self.src, "--out", self.dir / "c.png", "--size", "64x64").returncode, 0)
        self.assertEqual(self.size_of(self.dir / "c.png")[0], (64, 64))
        run("process", "resize", self.src, "--out", self.dir / "v.png", "--size", "64x64", "--fit", "cover")
        self.assertEqual(self.size_of(self.dir / "v.png")[0], (64, 64))
        run("process", "pad", self.src, "--out", self.dir / "p.png", "--aspect", "1:1")
        self.assertEqual(self.size_of(self.dir / "p.png")[0], (200, 200))
        run("process", "trim", self.src, "--out", self.dir / "t.png")
        self.assertEqual(self.size_of(self.dir / "t.png")[0], (100, 60))
        run("process", "convert", self.src, "--out", self.dir / "q.png", "--mode", "P", "--colors", "4")
        self.assertEqual(self.size_of(self.dir / "q.png")[1], "P")

    def test_strip_removes_metadata(self):
        jpeg = self.dir / "photo.jpg"
        exif = Image.Exif()
        exif[0x010F] = "SecretCam"  # Make
        Image.new("RGB", (32, 32), (10, 20, 30)).save(jpeg, exif=exif)
        with Image.open(jpeg) as before:
            self.assertIn(0x010F, before.getexif())
        self.assertEqual(run("process", "strip", jpeg, "--out", self.dir / "clean.jpg").returncode, 0)
        with Image.open(self.dir / "clean.jpg") as after:
            self.assertNotIn(0x010F, after.getexif())
        self.assertNotIn(b"SecretCam", (self.dir / "clean.jpg").read_bytes())

    def test_contact_sheet_and_batch_manifest(self):
        frames = []
        for index in range(3):
            path = self.dir / "in" / "img{}.png".format(index)
            path.parent.mkdir(exist_ok=True)
            Image.new("RGB", (40 + index * 10, 30), (index * 60, 100, 150)).save(path)
            frames.append(path)
        sheet = run("process", "contact-sheet", *frames, "--out", self.dir / "sheet.png", "--columns", "2", "--cell", "64")
        self.assertEqual(sheet.returncode, 0, sheet.stderr)
        self.assertEqual(self.size_of(self.dir / "sheet.png")[0], (128, 128))
        recipe = self.dir / "recipe.json"
        recipe.write_text(json.dumps({"steps": [{"op": "resize", "size": "32x32", "fit": "cover"},
                                                {"op": "convert", "mode": "RGB"}], "format": "png"}))
        batch = run("process", "batch", self.dir / "in", "--out", self.dir / "batch", "--recipe", recipe)
        self.assertEqual(batch.returncode, 0, batch.stderr)
        manifest = json.loads((self.dir / "batch" / "manifest.json").read_text())
        self.assertEqual([item["input"] for item in manifest["items"]], ["img0.png", "img1.png", "img2.png"])
        self.assertTrue(all(item["size"] == [32, 32] for item in manifest["items"]))

    def test_processing_without_pillow_refuses_clearly(self):
        result = run("process", "resize", self.src, "--out", self.dir / "x.png", python_flags=("-B", "-S"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("needs Pillow", result.stderr)
        self.assertFalse((self.dir / "x.png").exists())


if __name__ == "__main__":
    unittest.main()
