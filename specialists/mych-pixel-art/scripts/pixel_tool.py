#!/usr/bin/env python3
"""Pixel-art toolchain using only the Python standard library.

Commands:
  render   SPRITE --out DIR [--scale N] [--sheet]   text sprite -> PNG frames or a sheet with JSON
  sheet    PNG... --out SHEET.png [--json FILE]       pack equal-sized frames into a sprite sheet
  validate PNG [--palette NAME|FILE] [--max-colors N] [--cell WxH] [--allow-semi-transparency]
  palette  list | show NAME | extract PNG [--format hex|gpl]
  scale    PNG --factor N --out OUT                   nearest-neighbor upscale
  inspect  PNG                                        size, colors, alpha, opaque bounds

Sprite sheets come with JSON in the array layout used by Aseprite exports
(frames with x/y/w/h and duration; meta.frameTags), which several engines
import. PNG output is deterministic: no timestamps, fixed compression.

Decoding supports non-interlaced PNGs of color types 0, 2, 3, 4 and 6 at
bit depths 1-16 (16-bit samples are reduced to 8 bits). Interlaced PNGs are
refused with a clear message. Exit status: 0 success, 1 validation findings
or invalid input, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

VERSION = "2.0.0"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_DIMENSION = 16384
RGBA = Tuple[int, int, int, int]
TRANSPARENT: RGBA = (0, 0, 0, 0)

# Built-in palettes. Hex digits 0-9 and a-f map to the first 16 colors when a
# sprite says "palette: use NAME".
PALETTES: Dict[str, Dict[str, object]] = {
    "pico8": {"source": "PICO-8 fantasy console palette (Lexaloffle)", "colors": [
        "#000000", "#1d2b53", "#7e2553", "#008751", "#ab5236", "#5f574f", "#c2c3c7", "#fff1e8",
        "#ff004d", "#ffa300", "#ffec27", "#00e436", "#29adff", "#83769c", "#ff77a8", "#ffccaa"]},
    "sweetie16": {"source": "Sweetie 16 by GrafxKid (published on Lospec)", "colors": [
        "#1a1c2c", "#5d275d", "#b13e53", "#ef7d57", "#ffcd75", "#a7f070", "#38b764", "#257179",
        "#29366f", "#3b5dc9", "#41a6f6", "#73eff7", "#f4f4f4", "#94b0c2", "#566c86", "#333c57"]},
    "gameboy": {"source": "Four greens commonly used to imitate the original Game Boy screen", "colors": [
        "#0f380f", "#306230", "#8bac0f", "#9bbc0f"]},
    "grayscale4": {"source": "Four evenly spaced grays", "colors": ["#000000", "#555555", "#aaaaaa", "#ffffff"]},
}
HEX_DIGITS = "0123456789abcdef"


class PixelError(Exception):
    """Invalid input. code 1 = bad data, code 2 = usage problem."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Image and PNG codec
# ---------------------------------------------------------------------------

class Image:
    """RGBA image stored as a flat bytearray, 4 bytes per pixel."""

    def __init__(self, width: int, height: int, data: Optional[bytearray] = None) -> None:
        if not (0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION):
            raise PixelError("image size {}x{} is outside 1..{}".format(width, height, MAX_DIMENSION))
        self.width = width
        self.height = height
        self.data = data if data is not None else bytearray(width * height * 4)
        if len(self.data) != width * height * 4:
            raise PixelError("pixel buffer has the wrong length")

    def get(self, x: int, y: int) -> RGBA:
        i = (y * self.width + x) * 4
        d = self.data
        return (d[i], d[i + 1], d[i + 2], d[i + 3])

    def set(self, x: int, y: int, rgba: RGBA) -> None:
        i = (y * self.width + x) * 4
        self.data[i:i + 4] = bytes(rgba)

    def pixels(self) -> Iterable[RGBA]:
        d = self.data
        for i in range(0, len(d), 4):
            yield (d[i], d[i + 1], d[i + 2], d[i + 3])

    def crop(self, x: int, y: int, w: int, h: int) -> "Image":
        out = Image(w, h)
        for row in range(h):
            start = ((y + row) * self.width + x) * 4
            out.data[row * w * 4:(row + 1) * w * 4] = self.data[start:start + w * 4]
        return out

    def paste(self, other: "Image", x: int, y: int) -> None:
        for row in range(other.height):
            start = ((y + row) * self.width + x) * 4
            self.data[start:start + other.width * 4] = other.data[row * other.width * 4:(row + 1) * other.width * 4]

    def colors(self) -> Dict[RGBA, int]:
        counts: Dict[RGBA, int] = {}
        for pixel in self.pixels():
            key = TRANSPARENT if pixel[3] == 0 else pixel
            counts[key] = counts.get(key, 0) + 1
        return counts


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def encode_png(image: Image) -> bytes:
    """Encode deterministically: indexed color when 256 or fewer colors, otherwise RGBA."""
    palette: Dict[RGBA, int] = {}
    for pixel in image.pixels():
        key = TRANSPARENT if pixel[3] == 0 else pixel
        if key not in palette:
            if len(palette) == 256:
                palette = {}
                break
            palette[key] = len(palette)
    rows = []
    if palette:
        # Transparent entries first keeps the tRNS chunk short.
        ordered = sorted(palette, key=lambda c: (c[3] == 255, palette[c]))
        index = {color: i for i, color in enumerate(ordered)}
        bit_depth = 8
        for y in range(image.height):
            row = bytearray([0])
            for x in range(image.width):
                pixel = image.get(x, y)
                row.append(index[TRANSPARENT if pixel[3] == 0 else pixel])
            rows.append(bytes(row))
        header = struct.pack(">IIBBBBB", image.width, image.height, bit_depth, 3, 0, 0, 0)
        plte = b"".join(bytes(color[:3]) for color in ordered)
        alphas = [color[3] for color in ordered]
        while alphas and alphas[-1] == 255:
            alphas.pop()
        chunks = [_chunk(b"IHDR", header), _chunk(b"PLTE", plte)]
        if alphas:
            chunks.append(_chunk(b"tRNS", bytes(alphas)))
    else:
        stride = image.width * 4
        for y in range(image.height):
            rows.append(b"\x00" + bytes(image.data[y * stride:(y + 1) * stride]))
        header = struct.pack(">IIBBBBB", image.width, image.height, 8, 6, 0, 0, 0)
        chunks = [_chunk(b"IHDR", header)]
    chunks.append(_chunk(b"IDAT", zlib.compress(b"".join(rows), 9)))
    chunks.append(_chunk(b"IEND", b""))
    return PNG_SIGNATURE + b"".join(chunks)


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _unfilter(raw: bytes, width_bytes: int, height: int, bpp: int) -> bytearray:
    out = bytearray(width_bytes * height)
    previous = bytearray(width_bytes)
    pos = 0
    for y in range(height):
        if pos >= len(raw):
            raise PixelError("image data ends early")
        kind = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + width_bytes])
        pos += 1 + width_bytes
        if len(line) != width_bytes:
            raise PixelError("image data ends early")
        if kind == 1:
            for i in range(bpp, width_bytes):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif kind == 2:
            for i in range(width_bytes):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif kind == 3:
            for i in range(width_bytes):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(width_bytes):
                left = line[i - bpp] if i >= bpp else 0
                up_left = previous[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(left, previous[i], up_left)) & 0xFF
        elif kind != 0:
            raise PixelError("unknown PNG filter type {}".format(kind))
        out[y * width_bytes:(y + 1) * width_bytes] = line
        previous = line
    return out


def decode_png(blob: bytes) -> Image:
    if not blob.startswith(PNG_SIGNATURE):
        raise PixelError("not a PNG file (bad signature)")
    pos = len(PNG_SIGNATURE)
    header = None
    palette: List[Tuple[int, int, int]] = []
    transparency = b""
    idat = []
    while pos + 8 <= len(blob):
        length, kind = struct.unpack(">I4s", blob[pos:pos + 8])
        payload = blob[pos + 8:pos + 8 + length]
        crc = blob[pos + 8 + length:pos + 12 + length]
        if len(payload) != length or len(crc) != 4:
            raise PixelError("truncated {} chunk".format(kind.decode("latin-1")))
        if struct.unpack(">I", crc)[0] != zlib.crc32(kind + payload) & 0xFFFFFFFF:
            raise PixelError("CRC mismatch in {} chunk".format(kind.decode("latin-1")))
        pos += 12 + length
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"PLTE":
            palette = [tuple(payload[i:i + 3]) for i in range(0, len(payload), 3)]  # type: ignore[misc]
        elif kind == b"tRNS":
            transparency = payload
        elif kind == b"IDAT":
            idat.append(payload)
        elif kind == b"IEND":
            break
    if header is None:
        raise PixelError("missing IHDR chunk")
    width, height, depth, color_type, _, _, interlace = header
    if interlace:
        raise PixelError("interlaced PNGs are not supported; re-save without interlacing")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None or depth not in (1, 2, 4, 8, 16) or (color_type in (2, 4, 6) and depth < 8) or \
            (color_type == 3 and depth == 16):
        raise PixelError("unsupported PNG color type {} with bit depth {}".format(color_type, depth))
    if not (0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION):
        raise PixelError("image size {}x{} is outside 1..{}".format(width, height, MAX_DIMENSION))
    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error as exc:
        raise PixelError("corrupt image data: {}".format(exc)) from exc
    bits_per_pixel = channels * depth
    width_bytes = (width * bits_per_pixel + 7) // 8
    data = _unfilter(raw, width_bytes, height, max(1, bits_per_pixel // 8))
    image = Image(width, height)
    out = image.data
    trns_gray = struct.unpack(">H", transparency[:2])[0] if color_type == 0 and len(transparency) >= 2 else None
    trns_rgb = struct.unpack(">HHH", transparency[:6]) if color_type == 2 and len(transparency) >= 6 else None
    max_value = (1 << depth) - 1
    for y in range(height):
        line = data[y * width_bytes:(y + 1) * width_bytes]
        for x in range(width):
            if depth < 8:
                bit = x * depth
                value = (line[bit // 8] >> (8 - depth - bit % 8)) & max_value
                samples = [value]
            elif depth == 8:
                samples = list(line[x * channels:(x + 1) * channels])
            else:
                samples = [line[(x * channels + c) * 2] << 8 | line[(x * channels + c) * 2 + 1] for c in range(channels)]
            i = (y * width + x) * 4
            if color_type == 3:
                index = samples[0]
                if index >= len(palette):
                    raise PixelError("palette index {} out of range".format(index))
                r, g, b = palette[index]
                a = transparency[index] if index < len(transparency) else 255
            elif color_type in (0, 4):
                full = samples[0]
                gray = full * 255 // max_value if depth < 8 else (full >> 8 if depth == 16 else full)
                r = g = b = gray
                if color_type == 4:
                    a = samples[1] >> 8 if depth == 16 else samples[1]
                else:
                    a = 0 if trns_gray is not None and full == trns_gray else 255
            else:
                values = samples if depth == 8 else [s >> 8 for s in samples]
                r, g, b = values[0], values[1], values[2]
                if color_type == 6:
                    a = values[3]
                else:
                    a = 0 if trns_rgb is not None and tuple(samples[:3]) == trns_rgb else 255
            out[i:i + 4] = bytes((r, g, b, a))
    return image


def read_png(path: Path) -> Image:
    try:
        return decode_png(path.read_bytes())
    except OSError as exc:
        raise PixelError("cannot read {}: {}".format(path, exc)) from exc


def write_png(image: Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encode_png(image))


# ---------------------------------------------------------------------------
# Colors and palettes
# ---------------------------------------------------------------------------

def parse_color(text: str) -> RGBA:
    value = text.strip().lower()
    if value in ("transparent", "none", "clear"):
        return TRANSPARENT
    match = re.fullmatch(r"#?([0-9a-f]{6})([0-9a-f]{2})?", value)
    if not match:
        raise PixelError("invalid color {!r}; use #rrggbb, #rrggbbaa or 'transparent'".format(text))
    rgb = bytes.fromhex(match.group(1))
    alpha = int(match.group(2), 16) if match.group(2) else 255
    return TRANSPARENT if alpha == 0 else (rgb[0], rgb[1], rgb[2], alpha)


def hex_color(rgba: RGBA) -> str:
    if rgba[3] == 0:
        return "transparent"
    text = "#{:02x}{:02x}{:02x}".format(*rgba[:3])
    return text if rgba[3] == 255 else text + "{:02x}".format(rgba[3])


def load_palette(spec: str) -> Tuple[str, List[RGBA]]:
    if spec in PALETTES:
        return spec, [parse_color(c) for c in PALETTES[spec]["colors"]]  # type: ignore[union-attr]
    path = Path(spec)
    if not path.is_file():
        raise PixelError("unknown palette {!r}: not built in ({}) and not a file".format(spec, ", ".join(PALETTES)),
                         code=2)
    text = path.read_text(encoding="utf-8")
    colors = []
    if text.startswith("GIMP Palette"):
        for line in text.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
                colors.append((int(parts[0]), int(parts[1]), int(parts[2]), 255))
    else:
        for token in re.findall(r"#?[0-9a-fA-F]{6}\b", text):
            colors.append(parse_color(token))
    if not colors:
        raise PixelError("no colors found in palette file {}".format(path))
    return path.name, colors


# ---------------------------------------------------------------------------
# Text sprite format
# ---------------------------------------------------------------------------

class Sprite:
    def __init__(self, name: str) -> None:
        self.name = name
        self.width = 0
        self.height = 0
        self.palette: Dict[str, RGBA] = {".": TRANSPARENT}
        self.frames: List[Tuple[str, int, Image]] = []
        self.tags: List[Dict[str, object]] = []
        self.anchor: Optional[Tuple[int, int]] = None


def parse_sprite(text: str, source: str = "<sprite>") -> Sprite:
    """Parse the text sprite format described in references/sprite-format.md."""
    sprite = Sprite(Path(source).stem if source != "<sprite>" else "sprite")
    lines = text.splitlines()
    mode = "header"
    current: Optional[Tuple[str, int, List[Tuple[int, str]]]] = None
    pending: List[Tuple[str, int, List[Tuple[int, str]]]] = []
    declared_size: Optional[Tuple[int, int]] = None

    def fail(number: int, message: str) -> PixelError:
        return PixelError("{}:{}: {}".format(source, number, message))

    for number, raw in enumerate(lines, 1):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") and mode != "frame":
            continue
        if mode == "frame" and current is not None and not re.match(r"^(frame|tag|anchor)\s", stripped):
            if stripped.startswith("#"):
                continue
            current[2].append((number, stripped))
            continue
        if stripped.startswith("name:"):
            sprite.name = stripped.split(":", 1)[1].strip() or sprite.name
        elif stripped.startswith("size:"):
            match = re.fullmatch(r"size:\s*(\d+)\s*x\s*(\d+)", stripped)
            if not match:
                raise fail(number, "size must look like 'size: 16x16'")
            declared_size = (int(match.group(1)), int(match.group(2)))
        elif stripped.startswith("palette:"):
            rest = stripped.split(":", 1)[1].strip()
            if rest.startswith("use "):
                name = rest[4:].strip()
                if name not in PALETTES:
                    raise fail(number, "unknown built-in palette {!r} (available: {})".format(name, ", ".join(PALETTES)))
                for digit, color in zip(HEX_DIGITS, PALETTES[name]["colors"]):  # type: ignore[arg-type]
                    sprite.palette[digit] = parse_color(color)
            elif rest:
                raise fail(number, "write 'palette:' alone and list entries below it, or 'palette: use NAME'")
            mode = "palette"
        elif stripped.startswith("frame"):
            parts = stripped.split()
            if len(parts) not in (2, 3) or (len(parts) == 3 and not parts[2].isdigit()):
                raise fail(number, "frame lines look like 'frame NAME [DURATION_MS]'")
            if current is not None:
                pending.append(current)
            current = (parts[1], int(parts[2]) if len(parts) == 3 else 100, [])
            mode = "frame"
        elif stripped.startswith("tag"):
            parts = stripped.split()
            if len(parts) < 3:
                raise fail(number, "tag lines look like 'tag NAME FIRST_FRAME LAST_FRAME [forward|reverse|pingpong]'")
            direction = parts[4] if len(parts) > 4 else "forward"
            if direction not in ("forward", "reverse", "pingpong"):
                raise fail(number, "tag direction must be forward, reverse or pingpong")
            sprite.tags.append({"name": parts[1], "from_name": parts[2], "to_name": parts[3] if len(parts) > 3 else parts[2],
                                "direction": direction, "line": number})
            if current is not None:
                pending.append(current)
                current = None
            mode = "tags"
        elif stripped.startswith("anchor"):
            match = re.fullmatch(r"anchor\s+(\d+)\s+(\d+)", stripped)
            if not match:
                raise fail(number, "anchor lines look like 'anchor X Y'")
            sprite.anchor = (int(match.group(1)), int(match.group(2)))
            if current is not None:
                pending.append(current)
                current = None
            mode = "tags"
        elif mode == "palette":
            match = re.fullmatch(r"(\S)\s+(\S+)(?:\s+.*)?", stripped)
            if not match:
                raise fail(number, "palette entries look like 'k #1a1c2c' (one character, then a color)")
            if match.group(1) == "#":
                raise fail(number, "'#' starts comments and cannot be a palette character")
            try:
                sprite.palette[match.group(1)] = parse_color(match.group(2))
            except PixelError as exc:
                raise fail(number, str(exc)) from exc
        else:
            raise fail(number, "unexpected line {!r}".format(stripped[:40]))
    if current is not None:
        pending.append(current)
    if not pending:
        raise PixelError("{}: no frames found; add 'frame NAME' followed by pixel rows".format(source))
    first_rows = pending[0][2]
    width = declared_size[0] if declared_size else (len(first_rows[0][1]) if first_rows else 0)
    height = declared_size[1] if declared_size else len(first_rows)
    if width == 0 or height == 0:
        raise PixelError("{}: frame '{}' has no pixel rows".format(source, pending[0][0]))
    sprite.width, sprite.height = width, height
    names = set()
    for name, duration, rows in pending:
        if name in names:
            raise PixelError("{}: duplicate frame name '{}'".format(source, name))
        names.add(name)
        if len(rows) != height:
            line = rows[0][0] if rows else 0
            raise fail(line, "frame '{}' has {} rows, expected {}".format(name, len(rows), height))
        image = Image(width, height)
        for y, (number, row) in enumerate(rows):
            if len(row) != width:
                raise fail(number, "row has {} pixels, expected {}".format(len(row), width))
            for x, char in enumerate(row):
                if char not in sprite.palette:
                    raise fail(number, "character {!r} at column {} is not in the palette".format(char, x + 1))
                image.set(x, y, sprite.palette[char])
        sprite.frames.append((name, duration, image))
    order = [name for name, _, _ in sprite.frames]
    resolved = []
    for tag in sprite.tags:
        for key in ("from_name", "to_name"):
            if tag[key] not in order:
                raise PixelError("{}:{}: tag '{}' refers to unknown frame '{}'".format(source, tag["line"], tag["name"],
                                                                                     tag[key]))
        start, end = order.index(tag["from_name"]), order.index(tag["to_name"])  # type: ignore[arg-type]
        if end < start:
            raise PixelError("{}:{}: tag '{}' ends before it starts".format(source, tag["line"], tag["name"]))
        resolved.append({"name": tag["name"], "from": start, "to": end, "direction": tag["direction"]})
    if not resolved:
        resolved = derive_tags(order)
    sprite.tags = resolved
    if sprite.anchor and not (0 <= sprite.anchor[0] < width and 0 <= sprite.anchor[1] < height):
        raise PixelError("{}: anchor {} is outside the {}x{} frame".format(source, sprite.anchor, width, height))
    return sprite


def derive_tags(names: Sequence[str]) -> List[Dict[str, object]]:
    """Group consecutive frames named PREFIX_N into tags named PREFIX."""
    tags: List[Dict[str, object]] = []
    for index, name in enumerate(names):
        match = re.fullmatch(r"(.+?)[_-]?(\d+)", name)
        base = match.group(1) if match else name
        if tags and tags[-1]["name"] == base and tags[-1]["to"] == index - 1:
            tags[-1]["to"] = index
        else:
            tags.append({"name": base, "from": index, "to": index, "direction": "forward"})
    return tags


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def scale_image(image: Image, factor: int) -> Image:
    if not 1 <= factor <= 64:
        raise PixelError("scale factor must be between 1 and 64", code=2)
    out = Image(image.width * factor, image.height * factor)
    for y in range(image.height):
        row = bytearray()
        for x in range(image.width):
            row += bytes(image.get(x, y)) * factor
        for k in range(factor):
            start = ((y * factor + k) * out.width) * 4
            out.data[start:start + len(row)] = row
    return out


def pack_sheet(frames: Sequence[Tuple[str, int, Image]], columns: Optional[int] = None, padding: int = 0,
               extrude: int = 0, tags: Optional[List[Dict[str, object]]] = None, image_name: str = "sheet.png",
               anchor: Optional[Tuple[int, int]] = None, scale: int = 1) -> Tuple[Image, Dict[str, object]]:
    if not frames:
        raise PixelError("no frames to pack", code=2)
    width, height = frames[0][2].width, frames[0][2].height
    for name, _, image in frames:
        if (image.width, image.height) != (width, height):
            raise PixelError("frame '{}' is {}x{}, expected {}x{}; all frames must share one size".format(
                name, image.width, image.height, width, height))
    count = len(frames)
    cols = columns or int(math.ceil(math.sqrt(count)))
    rows = int(math.ceil(count / cols))
    cell_w = width * scale + 2 * extrude + padding
    cell_h = height * scale + 2 * extrude + padding
    sheet = Image(cols * cell_w - padding if cols else 1, rows * cell_h - padding if rows else 1)
    meta_frames = []
    for index, (name, duration, image) in enumerate(frames):
        frame = scale_image(image, scale) if scale > 1 else image
        col, row = index % cols, index // cols
        x0 = col * cell_w + extrude
        y0 = row * cell_h + extrude
        sheet.paste(frame, x0, y0)
        if extrude:
            fw, fh = frame.width, frame.height
            for e in range(1, extrude + 1):
                for x in range(fw):
                    sheet.set(x0 + x, y0 - e, frame.get(x, 0))
                    sheet.set(x0 + x, y0 + fh - 1 + e, frame.get(x, fh - 1))
                for y in range(-extrude, fh + extrude):
                    sy = min(max(y, 0), fh - 1)
                    sheet.set(x0 - e, y0 + y, frame.get(0, sy))
                    sheet.set(x0 + fw - 1 + e, y0 + y, frame.get(fw - 1, sy))
        meta_frames.append({
            "filename": name, "frame": {"x": x0, "y": y0, "w": frame.width, "h": frame.height}, "rotated": False,
            "trimmed": False, "spriteSourceSize": {"x": 0, "y": 0, "w": frame.width, "h": frame.height},
            "sourceSize": {"w": frame.width, "h": frame.height}, "duration": duration,
        })
    meta: Dict[str, object] = {
        "app": "mych-pixel-art pixel_tool.py", "version": VERSION, "image": image_name, "format": "RGBA8888",
        "size": {"w": sheet.width, "h": sheet.height}, "scale": str(scale),
        "frameTags": tags if tags is not None else derive_tags([f[0] for f in frames]),
    }
    if anchor:
        meta["anchor"] = {"x": anchor[0] * scale, "y": anchor[1] * scale}
    return sheet, {"frames": meta_frames, "meta": meta}


def validate_image(image: Image, palette: Optional[List[RGBA]] = None, max_colors: Optional[int] = None,
                   cell: Optional[Tuple[int, int]] = None, allow_semi: bool = False,
                   max_reports: int = 10) -> Dict[str, object]:
    errors: List[str] = []
    warnings: List[str] = []
    colors = image.colors()
    opaque_colors = [c for c in colors if c[3] > 0]
    semi = [(x, y) for y in range(image.height) for x in range(image.width) if 0 < image.get(x, y)[3] < 255]
    if semi and not allow_semi:
        errors.append("{} semi-transparent pixels (alpha between 0 and 255), first at {}; pixel art normally uses "
                      "fully opaque or fully transparent pixels".format(len(semi), semi[0]))
    if max_colors is not None and len(opaque_colors) > max_colors:
        errors.append("{} colors used, more than the limit of {}".format(len(opaque_colors), max_colors))
    if palette is not None:
        allowed = {c[:3] for c in palette}
        outside = [c for c in opaque_colors if c[:3] not in allowed]
        if outside:
            where = []
            for y in range(image.height):
                for x in range(image.width):
                    pixel = image.get(x, y)
                    if pixel[3] and pixel[:3] not in allowed and len(where) < max_reports:
                        where.append("{} at ({}, {})".format(hex_color(pixel), x, y))
            errors.append("{} colors outside the palette: {}".format(len(outside), "; ".join(where)))
    if cell is not None:
        cw, ch = cell
        if image.width % cw or image.height % ch:
            errors.append("size {}x{} is not a multiple of the {}x{} cell".format(image.width, image.height, cw, ch))
        else:
            empty = []
            for cy in range(image.height // ch):
                for cx in range(image.width // cw):
                    if all(image.get(cx * cw + x, cy * ch + y)[3] == 0 for y in range(ch) for x in range(cw)):
                        empty.append("({}, {})".format(cx, cy))
            if empty:
                warnings.append("{} empty cells: {}".format(len(empty), ", ".join(empty[:max_reports])))
    orphans = []
    for y in range(image.height):
        for x in range(image.width):
            pixel = image.get(x, y)
            if pixel[3] == 0:
                continue
            # Eight neighbors: diagonal steps connect pixel lines (1:1 slopes are normal).
            neighbors = [image.get(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                         if (dx or dy) and 0 <= x + dx < image.width and 0 <= y + dy < image.height]
            if neighbors and all(n != pixel for n in neighbors):
                orphans.append((x, y))
    if orphans:
        warnings.append("{} isolated single pixels (no neighbor of the same color), first at {}; intentional "
                        "highlights are fine, stray noise is not".format(len(orphans), orphans[:3]))
    return {"width": image.width, "height": image.height, "colors": len(opaque_colors),
            "has_transparency": TRANSPARENT in colors or bool(semi), "errors": errors, "warnings": warnings,
            "ok": not errors}


def opaque_bounds(image: Image) -> Optional[Tuple[int, int, int, int]]:
    xs, ys = [], []
    for y in range(image.height):
        for x in range(image.width):
            if image.get(x, y)[3]:
                xs.append(x)
                ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def parse_cell(text: str) -> Tuple[int, int]:
    match = re.fullmatch(r"(\d+)x(\d+)", text or "")
    if not match or int(match.group(1)) == 0 or int(match.group(2)) == 0:
        raise PixelError("cell must look like 16x16", code=2)
    return int(match.group(1)), int(match.group(2))


def cmd_render(args: argparse.Namespace) -> int:
    source = Path(args.sprite)
    sprite = parse_sprite(source.read_text(encoding="utf-8"), str(source))
    out = Path(args.out)
    if args.sheet:
        sheet, meta = pack_sheet(sprite.frames, columns=args.columns, padding=args.padding, extrude=args.extrude,
                                 tags=sprite.tags, image_name=sprite.name + ".png", anchor=sprite.anchor,
                                 scale=args.scale)
        write_png(sheet, out / (sprite.name + ".png"))
        (out / (sprite.name + ".json")).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print("Wrote {} ({}x{}, {} frames) and {}".format(out / (sprite.name + ".png"), sheet.width, sheet.height,
                                                        len(sprite.frames), out / (sprite.name + ".json")))
    else:
        for name, _, image in sprite.frames:
            target = out / "{}-{}.png".format(sprite.name, name)
            write_png(scale_image(image, args.scale) if args.scale > 1 else image, target)
            print("Wrote {}".format(target))
    return 0


def cmd_sheet(args: argparse.Namespace) -> int:
    frames = []
    for name in args.frames:
        path = Path(name)
        frames.append((path.stem, args.duration, read_png(path)))
    out = Path(args.out)
    sheet, meta = pack_sheet(frames, columns=args.columns, padding=args.padding, extrude=args.extrude,
                             image_name=out.name)
    write_png(sheet, out)
    json_path = Path(args.json) if args.json else out.with_suffix(".json")
    json_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("Wrote {} ({}x{}, {} frames) and {}".format(out, sheet.width, sheet.height, len(frames), json_path))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    image = read_png(Path(args.png))
    palette = load_palette(args.palette)[1] if args.palette else None
    result = validate_image(image, palette=palette, max_colors=args.max_colors,
                            cell=parse_cell(args.cell) if args.cell else None,
                            allow_semi=args.allow_semi_transparency)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("{}: {}x{}, {} colors{}".format(args.png, result["width"], result["height"], result["colors"],
                                              ", transparency" if result["has_transparency"] else ""))
        for item in result["errors"]:
            print("error: " + item)
        for item in result["warnings"]:
            print("warning: " + item)
        print("Result: {}".format("PASS" if result["ok"] else "FAIL"))
    return 0 if result["ok"] else 1


def cmd_palette(args: argparse.Namespace) -> int:
    if args.action == "list":
        for name, info in PALETTES.items():
            print("{:<11} {:>2} colors  {}".format(name, len(info["colors"]), info["source"]))  # type: ignore[arg-type]
        return 0
    if args.action == "show":
        if not args.target or args.target not in PALETTES:
            raise PixelError("show needs a built-in palette name: {}".format(", ".join(PALETTES)), code=2)
        for digit, color in zip(HEX_DIGITS, PALETTES[args.target]["colors"]):  # type: ignore[arg-type]
            print("{} {}".format(digit, color))
        return 0
    if not args.target:
        raise PixelError("extract needs a PNG path", code=2)
    image = read_png(Path(args.target))
    counts = image.colors()
    ordered = sorted((c for c in counts if c[3]), key=lambda c: -counts[c])
    if args.format == "gpl":
        print("GIMP Palette\nName: {}\nColumns: 8\n#".format(Path(args.target).stem))
        for color in ordered:
            print("{:3d} {:3d} {:3d}\t{} ({} px)".format(color[0], color[1], color[2], hex_color(color), counts[color]))
    else:
        for color in ordered:
            print("{}  {} px".format(hex_color(color), counts[color]))
    return 0


def cmd_scale(args: argparse.Namespace) -> int:
    image = read_png(Path(args.png))
    out = scale_image(image, args.factor)
    write_png(out, Path(args.out))
    print("Wrote {} ({}x{})".format(args.out, out.width, out.height))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    image = read_png(Path(args.png))
    colors = image.colors()
    bounds = opaque_bounds(image)
    info = {"path": args.png, "width": image.width, "height": image.height,
            "colors": len([c for c in colors if c[3]]), "transparent_pixels": colors.get(TRANSPARENT, 0),
            "semi_transparent_pixels": sum(1 for p in image.pixels() if 0 < p[3] < 255),
            "opaque_bounds": bounds}
    print(json.dumps(info, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pixel-art toolchain (standard library only).",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    p = sub.add_parser("render", help="render a text sprite to PNG frames or a sheet")
    p.add_argument("sprite")
    p.add_argument("--out", required=True, help="output folder")
    p.add_argument("--scale", type=int, default=1, help="integer upscale (default 1)")
    p.add_argument("--sheet", action="store_true", help="write one sheet PNG plus JSON instead of frame files")
    p.add_argument("--columns", type=int, help="sheet columns (default: near-square)")
    p.add_argument("--padding", type=int, default=0, help="transparent pixels between frames")
    p.add_argument("--extrude", type=int, default=0, help="repeat edge pixels around frames (prevents bleeding)")
    p = sub.add_parser("sheet", help="pack equal-sized PNG frames into a sprite sheet")
    p.add_argument("frames", nargs="+")
    p.add_argument("--out", required=True)
    p.add_argument("--json", help="JSON path (default: next to the sheet)")
    p.add_argument("--columns", type=int)
    p.add_argument("--padding", type=int, default=0)
    p.add_argument("--extrude", type=int, default=0)
    p.add_argument("--duration", type=int, default=100, help="frame duration in milliseconds (default 100)")
    p = sub.add_parser("validate", help="check a PNG against pixel-art rules")
    p.add_argument("png")
    p.add_argument("--palette", help="built-in palette name or a palette file (.gpl or hex list)")
    p.add_argument("--max-colors", type=int)
    p.add_argument("--cell", help="frame or tile size, for example 16x16")
    p.add_argument("--allow-semi-transparency", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("palette", help="list, show or extract palettes")
    p.add_argument("action", choices=("list", "show", "extract"))
    p.add_argument("target", nargs="?")
    p.add_argument("--format", choices=("hex", "gpl"), default="hex")
    p = sub.add_parser("scale", help="nearest-neighbor upscale")
    p.add_argument("png")
    p.add_argument("--factor", type=int, required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("inspect", help="describe a PNG")
    p.add_argument("png")
    return parser


COMMANDS = {"render": cmd_render, "sheet": cmd_sheet, "validate": cmd_validate, "palette": cmd_palette,
            "scale": cmd_scale, "inspect": cmd_inspect}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except PixelError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return exc.code
    except OSError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
