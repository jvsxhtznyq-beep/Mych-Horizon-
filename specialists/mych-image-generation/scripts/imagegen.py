#!/usr/bin/env python3
"""Image generation front door and deterministic image processing.

Commands:
  detect    [--probe-local] [--json]      which generation backends exist here (honest inventory)
  generate  --prompt TEXT --out DIR [--backend auto|comfyui|openai] ...
            Generates only through a backend that is actually available.
            With no backend it exits with status 3, writes nothing and says
            that no image was generated. Every image gets a provenance
            sidecar (backend, model, prompt, seed, parameters, hashes).
  process   resize|crop|pad|convert|trim|strip|contact-sheet|batch ...
            Pillow-based processing; refuses clearly when Pillow is missing.

Backends:
  comfyui   a ComfyUI server (default http://127.0.0.1:8188) with an API-format
            workflow containing placeholders such as {{PROMPT}} and {{SEED}}
  openai    an OpenAI-style images endpoint (POST /v1/images/generations);
            needs --model and an API key variable (default OPENAI_API_KEY)
  --dry-run prints the request that would be sent and sends nothing.

Exit status: 0 success, 1 failed request or invalid input, 2 usage error,
3 no backend available (nothing generated).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

VERSION = "2.0.0"
NO_BACKEND_EXIT = 3
COMFYUI_DEFAULT = "http://127.0.0.1:8188"
API_CREDENTIALS = {
    "OPENAI_API_KEY": "openai", "STABILITY_API_KEY": "stability", "REPLICATE_API_TOKEN": "replicate",
    "FAL_KEY": "fal", "GEMINI_API_KEY": "gemini", "BFL_API_KEY": "bfl",
}
IMPLEMENTED_BACKENDS = ("comfyui", "openai")
HTTP_TIMEOUT = 30
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024


class ImageGenError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# HTTP helpers (standard library only)
# ---------------------------------------------------------------------------

def http_json(method: str, url: str, payload: Optional[Dict[str, Any]] = None,
              headers: Optional[Dict[str, str]] = None, timeout: float = HTTP_TIMEOUT) -> Dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method,
                                     headers=dict({"Content-Type": "application/json",
                                                   "User-Agent": "mych-image-generation"}, **(headers or {})))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.HTTPError as exc:
        detail = exc.read(2000).decode("utf-8", "replace")
        raise ImageGenError("{} {} returned HTTP {}: {}".format(method, redact_url(url), exc.code, detail[:500])) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise ImageGenError("{} {} failed: {}".format(method, redact_url(url), getattr(exc, "reason", exc))) from exc
    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise ImageGenError("response from {} exceeds {} bytes".format(redact_url(url), MAX_DOWNLOAD_BYTES))
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ImageGenError("{} {} did not return JSON".format(method, redact_url(url))) from exc


def http_bytes(url: str, timeout: float = HTTP_TIMEOUT) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "mych-image-generation"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    except (urllib.error.URLError, OSError) as exc:
        raise ImageGenError("download from {} failed: {}".format(redact_url(url), getattr(exc, "reason", exc))) from exc
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ImageGenError("download from {} exceeds {} bytes".format(redact_url(url), MAX_DOWNLOAD_BYTES))
    return data


def redact_url(url: str) -> str:
    """Drop query values that might carry keys before a URL is shown or logged."""
    parts = urllib.parse.urlsplit(url)
    if not parts.query:
        return url
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    safe = [(k, "REDACTED" if re.search(r"key|token|secret|sig", k, re.I) else v) for k, v in query]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(safe)))


def reachable(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mych-image-generation"}),
                                    timeout=timeout) as response:
            return 200 <= response.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def gpu_present() -> bool:
    from shutil import which
    import subprocess
    tool = which("nvidia-smi")
    if not tool:
        return False
    try:
        result = subprocess.run([tool, "-L"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and "GPU" in result.stdout


def detect(probe_local: bool = False, comfyui_url: str = COMFYUI_DEFAULT) -> Dict[str, Any]:
    backends: List[Dict[str, Any]] = []
    has_torch, has_diffusers, gpu = module_present("torch"), module_present("diffusers"), gpu_present()
    backends.append({"id": "diffusers-local", "available": bool(has_torch and has_diffusers and gpu),
                     "implemented_here": False,
                     "detail": "torch {}, diffusers {}, NVIDIA GPU {}".format(
                         "present" if has_torch else "missing", "present" if has_diffusers else "missing",
                         "present" if gpu else "missing"),
                     "note": "use the diffusers library directly; this script does not drive it"})
    if probe_local:
        up = reachable(comfyui_url.rstrip("/") + "/system_stats")
        backends.append({"id": "comfyui", "available": up, "implemented_here": True,
                         "detail": "{} {}".format(comfyui_url, "answered" if up else "did not answer")})
    else:
        backends.append({"id": "comfyui", "available": None, "implemented_here": True,
                         "detail": "not probed (use --probe-local)"})
    for variable, backend in API_CREDENTIALS.items():
        present = bool(os.environ.get(variable))
        backends.append({"id": backend, "available": present, "implemented_here": backend in IMPLEMENTED_BACKENDS,
                         "detail": "{} {}".format(variable, "set (key not tested)" if present else "not set")})
    usable = [b["id"] for b in backends if b["available"] and b["implemented_here"]]
    processing = module_present("PIL")
    return {
        "schema": "mych-imagegen-detect/1", "backends": backends, "usable_backends": usable,
        "generation_available": bool(usable), "processing_available": processing,
        "statement": ("Image generation is available through: {}.".format(", ".join(usable)) if usable else
                      "No image generation backend is available here. No image will be generated; planning, "
                      "prompt writing and {}processing still work.".format("" if processing else "(without Pillow, no) ")),
    }


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_with_provenance(out_dir: Path, stem: str, data: bytes, provenance: Dict[str, Any]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    extension = ".png" if data.startswith(b"\x89PNG") else ".jpg" if data[:3] == b"\xff\xd8\xff" else \
        ".webp" if data[8:12] == b"WEBP" else ".bin"
    path = out_dir / (stem + extension)
    path.write_bytes(data)
    record = dict(provenance, file=path.name, sha256=sha256(data), bytes=len(data),
                  created_by="mych-image-generation imagegen.py {}".format(VERSION))
    (out_dir / (stem + ".provenance.json")).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def fill_placeholders(node: Any, values: Dict[str, Any]) -> Any:
    if isinstance(node, dict):
        return {k: fill_placeholders(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [fill_placeholders(v, values) for v in node]
    if isinstance(node, str):
        match = re.fullmatch(r"\{\{([A-Z_]+)\}\}", node)
        if match and match.group(1) in values:
            return values[match.group(1)]
        return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: str(values.get(m.group(1), m.group(0))), node)
    return node


def unfilled_placeholders(node: Any) -> List[str]:
    text = json.dumps(node)
    return sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", text)))


def generate_comfyui(args: argparse.Namespace, seed: int) -> List[Path]:
    if not args.workflow:
        raise ImageGenError("the comfyui backend needs --workflow FILE (an API-format workflow with placeholders)", 2)
    workflow = json.loads(Path(args.workflow).read_text(encoding="utf-8"))
    width, height = parse_size(args.size)
    values = {"PROMPT": args.prompt, "NEGATIVE": args.negative or "", "SEED": seed, "WIDTH": width, "HEIGHT": height,
              "STEPS": args.steps, "CFG": args.cfg}
    if args.checkpoint:
        values["CHECKPOINT"] = args.checkpoint
    graph = fill_placeholders(workflow, values)
    missing = unfilled_placeholders(graph)
    if missing:
        raise ImageGenError("workflow placeholders without values: {} (pass --checkpoint for CHECKPOINT)".format(
            ", ".join(missing)), 2)
    base = (args.base_url or COMFYUI_DEFAULT).rstrip("/")
    request = {"prompt": graph, "client_id": "mych-{}".format(seed)}
    if args.dry_run:
        print(json.dumps({"dry_run": True, "method": "POST", "url": base + "/prompt", "body": request}, indent=2))
        return []
    queued = http_json("POST", base + "/prompt", request)
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise ImageGenError("ComfyUI did not return a prompt_id: {}".format(json.dumps(queued)[:300]))
    if queued.get("node_errors"):
        raise ImageGenError("ComfyUI reported node errors: {}".format(json.dumps(queued["node_errors"])[:500]))
    deadline = time.monotonic() + args.timeout
    outputs: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        history = http_json("GET", "{}/history/{}".format(base, urllib.parse.quote(prompt_id)))
        entry = history.get(prompt_id) or {}
        status = entry.get("status") or {}
        if status.get("status_str") == "error":
            raise ImageGenError("ComfyUI reported an error for prompt {}: {}".format(
                prompt_id, json.dumps(status.get("messages", []))[:500]))
        if entry.get("outputs"):
            outputs = entry["outputs"]
            break
        time.sleep(args.poll)
    if not outputs:
        raise ImageGenError("ComfyUI produced no outputs within {}s for prompt {}; no image was saved".format(
            args.timeout, prompt_id))
    saved = []
    images = [image for node in outputs.values() for image in node.get("images", [])]
    for index, image in enumerate(images):
        query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""),
                                        "type": image.get("type", "output")})
        data = http_bytes("{}/view?{}".format(base, query))
        saved.append(write_with_provenance(Path(args.out), "{}-{}".format(args.name, index), data, {
            "backend": "comfyui", "server": base, "prompt_id": prompt_id, "model": args.checkpoint,
            "prompt": args.prompt, "negative": args.negative, "seed": seed,
            "parameters": {"size": args.size, "steps": args.steps, "cfg": args.cfg},
            "workflow_sha256": sha256(json.dumps(workflow, sort_keys=True).encode("utf-8"))}))
    if not saved:
        raise ImageGenError("ComfyUI outputs contained no images; no image was saved")
    return saved


def generate_openai(args: argparse.Namespace, seed: int) -> List[Path]:
    if not args.model:
        raise ImageGenError("the openai backend needs --model (use a model name from the provider's documentation)", 2)
    base = (args.base_url or "https://api.openai.com").rstrip("/")
    url = base + "/v1/images/generations"
    payload: Dict[str, Any] = {"model": args.model, "prompt": args.prompt, "n": args.count, "size": args.size}
    key_name = args.api_key_env or "OPENAI_API_KEY"
    if args.dry_run:
        print(json.dumps({"dry_run": True, "method": "POST", "url": url, "headers": {"Authorization": "Bearer ${}".format(
            key_name)}, "body": payload}, indent=2))
        return []
    key = os.environ.get(key_name)
    if not key:
        raise ImageGenError("{} is not set; no image was generated".format(key_name), NO_BACKEND_EXIT)
    response = http_json("POST", url, payload, headers={"Authorization": "Bearer " + key}, timeout=args.timeout)
    items = response.get("data") or []
    if not items:
        raise ImageGenError("the images endpoint returned no data; no image was saved")
    saved = []
    for index, item in enumerate(items):
        if item.get("b64_json"):
            try:
                data = base64.b64decode(item["b64_json"], validate=True)
            except (ValueError, TypeError) as exc:
                raise ImageGenError("image {} is not valid base64".format(index)) from exc
        elif item.get("url"):
            data = http_bytes(item["url"])
        else:
            raise ImageGenError("image {} has neither b64_json nor url".format(index))
        saved.append(write_with_provenance(Path(args.out), "{}-{}".format(args.name, index), data, {
            "backend": "openai-images", "endpoint": url, "model": args.model, "prompt": args.prompt,
            "revised_prompt": item.get("revised_prompt"), "seed": None,
            "parameters": {"size": args.size, "n": args.count},
            "note": "this endpoint does not take a seed; results are not reproducible"}))
    return saved


def parse_size(text: str) -> Tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", text or "")
    if not match:
        raise ImageGenError("size must look like 1024x1024", 2)
    return int(match.group(1)), int(match.group(2))


def cmd_generate(args: argparse.Namespace) -> int:
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2 ** 31)
    backend = args.backend
    if backend == "auto":
        found = detect(probe_local=True, comfyui_url=args.base_url or COMFYUI_DEFAULT)
        usable = [name for name in found["usable_backends"] if name != "comfyui" or args.workflow]
        if not usable:
            print("No image was generated: no usable generation backend is available. {}".format(found["statement"]),
                  file=sys.stderr)
            return NO_BACKEND_EXIT
        backend = usable[0]
    if backend == "comfyui":
        saved = generate_comfyui(args, seed)
    else:
        saved = generate_openai(args, seed)
    for path in saved:
        print("Generated {} with backend {} (provenance: {})".format(path, backend, path.with_suffix("").name +
                                                                  ".provenance.json"))
    return 0


# ---------------------------------------------------------------------------
# Processing (Pillow)
# ---------------------------------------------------------------------------

def pil() -> Any:
    try:
        from PIL import Image, ImageOps  # noqa: F401
        return Image
    except ImportError as exc:
        raise ImageGenError("image processing needs Pillow, which is not installed here; install it (pip install "
                            "pillow) or use another tool. Nothing was processed.", 2) from exc


FILTERS = {"nearest": "NEAREST", "bilinear": "BILINEAR", "bicubic": "BICUBIC", "lanczos": "LANCZOS"}


def resample(name: str) -> Any:
    Image = pil()
    holder = getattr(Image, "Resampling", Image)
    return getattr(holder, FILTERS[name])


def op_resize(image: Any, size: str, fit: str, filter_name: str) -> Any:
    Image = pil()
    from PIL import ImageOps
    width, height = parse_size(size)
    method = resample(filter_name)
    if fit == "stretch":
        return image.resize((width, height), method)
    if fit == "cover":
        return ImageOps.fit(image, (width, height), method=method)
    copy = image.copy()
    copy.thumbnail((width, height), method)
    canvas = Image.new("RGBA" if "A" in image.getbands() else image.mode, (width, height), (0, 0, 0, 0)
                       if "A" in image.getbands() else 0)
    canvas.paste(copy, ((width - copy.width) // 2, (height - copy.height) // 2))
    return canvas


def op_pad(image: Any, aspect: str, color: str) -> Any:
    Image = pil()
    match = re.fullmatch(r"(\d+):(\d+)", aspect)
    if not match:
        raise ImageGenError("aspect must look like 16:9", 2)
    aw, ah = int(match.group(1)), int(match.group(2))
    width, height = image.size
    if width * ah > height * aw:
        new_w, new_h = width, (width * ah + aw - 1) // aw
    else:
        new_w, new_h = (height * aw + ah - 1) // ah, height
    mode = "RGBA" if color == "transparent" or "A" in image.getbands() else "RGB"
    fill = (0, 0, 0, 0) if color == "transparent" else tuple(bytes.fromhex(color.lstrip("#"))) + ((255,) if mode == "RGBA" else ())
    canvas = Image.new(mode, (new_w, new_h), fill)
    canvas.paste(image.convert(mode), ((new_w - width) // 2, (new_h - height) // 2))
    return canvas


def op_trim(image: Any) -> Any:
    rgba = image.convert("RGBA")
    box = rgba.getchannel("A").getbbox()
    return rgba.crop(box) if box else rgba


def op_convert(image: Any, mode: str, colors: Optional[int]) -> Any:
    if mode == "P":
        return image.convert("RGBA").quantize(colors=colors or 256)
    return image.convert(mode)


def save_clean(image: Any, path: Path) -> None:
    """Save without metadata: a fresh image carries only pixels."""
    Image = pil()
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = Image.new(image.mode, image.size)
    if image.mode == "P":
        clean.putpalette(image.getpalette())
        if "transparency" in image.info:
            clean.info["transparency"] = image.info["transparency"]
    clean.putdata(list(image.getdata()))
    params = {}
    if clean.mode == "P" and "transparency" in image.info:
        params["transparency"] = image.info["transparency"]
    clean.save(path, **params)


def contact_sheet(paths: Sequence[Path], columns: int, cell: int) -> Any:
    Image = pil()
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell, rows * cell), (32, 32, 32, 255))
    for index, path in enumerate(paths):
        with Image.open(path) as source:
            thumb = source.convert("RGBA")
            thumb.thumbnail((cell, cell), resample("lanczos"))
            x = (index % columns) * cell + (cell - thumb.width) // 2
            y = (index // columns) * cell + (cell - thumb.height) // 2
            sheet.paste(thumb, (x, y), thumb)
    return sheet


def apply_steps(image: Any, steps: List[Dict[str, Any]]) -> Any:
    for step in steps:
        op = step.get("op")
        if op == "resize":
            image = op_resize(image, step["size"], step.get("fit", "contain"), step.get("filter", "lanczos"))
        elif op == "crop":
            image = image.crop(tuple(step["box"]))
        elif op == "pad":
            image = op_pad(image, step["aspect"], step.get("color", "transparent"))
        elif op == "trim":
            image = op_trim(image)
        elif op == "convert":
            image = op_convert(image, step["mode"], step.get("colors"))
        else:
            raise ImageGenError("unknown recipe step {!r}".format(op), 2)
    return image


def cmd_process(args: argparse.Namespace) -> int:
    Image = pil()
    if args.operation == "contact-sheet":
        paths = [Path(p) for p in args.inputs]
        sheet = contact_sheet(paths, args.columns, args.cell)
        save_clean(sheet, Path(args.out))
        print("Wrote contact sheet {} ({} images)".format(args.out, len(paths)))
        return 0
    if args.operation == "batch":
        recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
        source_dir, out_dir = Path(args.inputs[0]), Path(args.out)
        patterns = recipe.get("include", ["*.png", "*.jpg", "*.jpeg", "*.webp"])
        files = sorted({p for pattern in patterns for p in source_dir.glob(pattern) if p.is_file()})
        manifest = {"schema": "mych-imagegen-batch/1", "recipe": recipe.get("steps", []), "items": []}
        for path in files:
            with Image.open(path) as image:
                result = apply_steps(image.copy(), recipe.get("steps", []))
            target = out_dir / (path.stem + "." + recipe.get("format", "png"))
            save_clean(result, target)
            manifest["items"].append({"input": path.name, "input_sha256": sha256(path.read_bytes()),
                                      "output": target.name, "output_sha256": sha256(target.read_bytes()),
                                      "size": list(result.size), "mode": result.mode})
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print("Processed {} images into {} (manifest.json lists inputs and outputs with hashes)".format(
            len(files), out_dir))
        return 0
    source = Path(args.inputs[0])
    with Image.open(source) as image:
        image.load()
        if args.operation == "resize":
            result = op_resize(image, args.size, args.fit, args.filter)
        elif args.operation == "crop":
            box = tuple(int(v) for v in args.box.split(","))
            if len(box) != 4:
                raise ImageGenError("--box must be LEFT,TOP,RIGHT,BOTTOM", 2)
            result = image.crop(box)
        elif args.operation == "pad":
            result = op_pad(image, args.aspect, args.color)
        elif args.operation == "convert":
            result = op_convert(image, args.mode, args.colors)
        elif args.operation == "trim":
            result = op_trim(image)
        else:  # strip
            result = image.copy()
    save_clean(result, Path(args.out))
    print("Wrote {} ({}x{}, mode {}, metadata removed)".format(args.out, result.size[0], result.size[1], result.mode))
    return 0


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Honest image generation and Pillow-based processing.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    p = sub.add_parser("detect", help="inventory generation backends")
    p.add_argument("--probe-local", action="store_true", help="probe a local ComfyUI server")
    p.add_argument("--comfyui-url", default=COMFYUI_DEFAULT)
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("generate", help="generate images through an available backend")
    p.add_argument("--prompt", required=True)
    p.add_argument("--negative", help="negative prompt (backends that support it)")
    p.add_argument("--out", required=True, help="output folder")
    p.add_argument("--name", default="image", help="output file stem (default: image)")
    p.add_argument("--backend", choices=("auto",) + IMPLEMENTED_BACKENDS, default="auto")
    p.add_argument("--model", help="model name (required for API backends)")
    p.add_argument("--checkpoint", help="ComfyUI checkpoint name for the {{CHECKPOINT}} placeholder")
    p.add_argument("--workflow", help="ComfyUI API-format workflow JSON with placeholders")
    p.add_argument("--size", default="1024x1024")
    p.add_argument("--seed", type=int)
    p.add_argument("--steps", type=int, default=25)
    p.add_argument("--cfg", type=float, default=6.5)
    p.add_argument("--count", type=int, default=1, help="number of images (API backends)")
    p.add_argument("--base-url", help="backend base URL (ComfyUI server, API gateway or a local stub)")
    p.add_argument("--api-key-env", help="variable holding the API key (default OPENAI_API_KEY)")
    p.add_argument("--timeout", type=float, default=300)
    p.add_argument("--poll", type=float, default=1.0, help="seconds between ComfyUI history polls")
    p.add_argument("--dry-run", action="store_true", help="print the request and send nothing")
    p = sub.add_parser("process", help="deterministic processing with Pillow")
    p.add_argument("operation", choices=("resize", "crop", "pad", "convert", "trim", "strip", "contact-sheet", "batch"))
    p.add_argument("inputs", nargs="+", help="input file (or files for contact-sheet, folder for batch)")
    p.add_argument("--out", required=True)
    p.add_argument("--size", default="512x512")
    p.add_argument("--fit", choices=("contain", "cover", "stretch"), default="contain")
    p.add_argument("--filter", choices=tuple(FILTERS), default="lanczos")
    p.add_argument("--box", help="crop box LEFT,TOP,RIGHT,BOTTOM")
    p.add_argument("--aspect", default="1:1")
    p.add_argument("--color", default="transparent", help="pad color #rrggbb or transparent")
    p.add_argument("--mode", choices=("RGB", "RGBA", "L", "P"), default="RGBA")
    p.add_argument("--colors", type=int, help="palette size for mode P")
    p.add_argument("--columns", type=int, default=4)
    p.add_argument("--cell", type=int, default=256)
    p.add_argument("--recipe", help="batch recipe JSON: {\"steps\": [...], \"format\": \"png\"}")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "detect":
            report = detect(args.probe_local, args.comfyui_url)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                for backend in report["backends"]:
                    state = {True: "available", False: "unavailable", None: "unknown"}[backend["available"]]
                    print("{:<16} {:<12} {}{}".format(backend["id"], state, backend["detail"],
                                                      "" if backend["implemented_here"] else " (not driven by this script)"))
                print(report["statement"])
            return 0
        if args.command == "generate":
            return cmd_generate(args)
        return cmd_process(args)
    except ImageGenError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return exc.code
    except (OSError, ValueError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
