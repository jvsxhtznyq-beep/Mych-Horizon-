"""Tests for the mych-pixel-art specialist's pixel_tool.py.

The PNG codec is cross-checked against independent implementations when they
are installed: Pillow (decoding its files and having it decode ours) and
ImageMagick's convert (adaptive filters, interlacing).
"""

from __future__ import annotations

import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "specialists" / "mych-pixel-art" / "scripts" / "pixel_tool.py"


def load():
    name = "mych_pixel_tool"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    sys.dont_write_bytecode, previous = True, sys.dont_write_bytecode
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


px = load()

try:
    from PIL import Image as PILImage
except ImportError:  # pragma: no cover
    PILImage = None

SLIME = """# test sprite
name: slime
palette:
  k #1a1c2c
  g #38b764
  w #f4f4f4
frame idle_0 150
.kk.
kgwk
kggk
frame idle_1 150
....
.kk.
kwgk
frame jump_0 80
kkkk
kggk
.kk.
anchor 2 2
"""


def run(*args):
    return subprocess.run([sys.executable, "-B", str(SCRIPT)] + [str(a) for a in args], capture_output=True, text=True)


class CodecTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def random_image(self, width, height, colors=None, seed=1):
        rng = random.Random(seed)
        image = px.Image(width, height)
        palette = colors or [(rng.randrange(256), rng.randrange(256), rng.randrange(256), 255) for _ in range(8)]
        for y in range(height):
            for x in range(width):
                image.set(x, y, rng.choice(palette + [px.TRANSPARENT]))
        return image

    def test_roundtrip_indexed_and_truecolor(self):
        small = self.random_image(17, 9)
        self.assertEqual(px.decode_png(px.encode_png(small)).data, small.data)
        rng = random.Random(7)
        many = px.Image(40, 40)
        for y in range(40):
            for x in range(40):
                many.set(x, y, (rng.randrange(256), rng.randrange(256), rng.randrange(256), rng.choice((255, 128))))
        blob = px.encode_png(many)
        self.assertEqual(blob[25], 6, "more than 256 colors must use RGBA color type 6")
        self.assertEqual(px.decode_png(blob).data, many.data)

    def test_encoding_is_deterministic(self):
        image = self.random_image(8, 8)
        self.assertEqual(px.encode_png(image), px.encode_png(image))

    def test_corruption_is_detected(self):
        blob = bytearray(px.encode_png(self.random_image(4, 4)))
        blob[40] ^= 0xFF
        with self.assertRaises(px.PixelError):
            px.decode_png(bytes(blob))
        with self.assertRaises(px.PixelError):
            px.decode_png(b"GIF89a")

    @unittest.skipIf(PILImage is None, "Pillow not installed")
    def test_decodes_pillow_files_in_every_supported_mode(self):
        base = PILImage.new("RGBA", (13, 7))
        rng = random.Random(3)
        for y in range(7):
            for x in range(13):
                base.putpixel((x, y), (rng.randrange(256), rng.randrange(256), rng.randrange(256),
                                       rng.choice((0, 255, 255))))
        for mode in ("RGBA", "RGB", "L", "LA", "P", "1"):
            with self.subTest(mode=mode):
                path = self.dir / "pil-{}.png".format(mode)
                converted = base.convert(mode) if mode != "P" else base.convert("RGB").quantize(colors=16)
                converted.save(path)
                ours = px.read_png(path)
                theirs = PILImage.open(path).convert("RGBA")
                for y in range(7):
                    for x in range(13):
                        self.assertEqual(ours.get(x, y), theirs.getpixel((x, y)), (mode, x, y))

    @unittest.skipIf(PILImage is None, "Pillow not installed")
    def test_pillow_decodes_our_files(self):
        for image in (self.random_image(10, 6), self.random_image(30, 30, seed=9)):
            path = self.dir / "ours.png"
            px.write_png(image, path)
            theirs = PILImage.open(path).convert("RGBA")
            self.assertEqual(theirs.size, (image.width, image.height))
            for y in range(image.height):
                for x in range(image.width):
                    expected = image.get(x, y)
                    got = theirs.getpixel((x, y))
                    if expected[3] == 0:
                        self.assertEqual(got[3], 0)
                    else:
                        self.assertEqual(got, expected)

    @unittest.skipIf(shutil.which("convert") is None or PILImage is None, "ImageMagick or Pillow not installed")
    def test_decodes_imagemagick_adaptive_filters_and_refuses_interlacing(self):
        source = self.dir / "src.png"
        px.write_png(self.random_image(31, 17, seed=11), source)
        plain = self.dir / "im.png"
        subprocess.run(["convert", str(source), "-define", "png:color-type=6", str(plain)], check=True)
        ours = px.read_png(plain)
        theirs = PILImage.open(plain).convert("RGBA")
        for y in range(17):
            for x in range(31):
                if theirs.getpixel((x, y))[3]:
                    self.assertEqual(ours.get(x, y), theirs.getpixel((x, y)))
        interlaced = self.dir / "interlaced.png"
        subprocess.run(["convert", str(source), "-interlace", "PNG", str(interlaced)], check=True)
        with self.assertRaises(px.PixelError) as caught:
            px.read_png(interlaced)
        self.assertIn("interlaced", str(caught.exception))


class SpriteTest(unittest.TestCase):
    def test_parse_frames_tags_and_anchor(self):
        sprite = px.parse_sprite(SLIME, "slime.sprite")
        self.assertEqual((sprite.width, sprite.height), (4, 3))
        self.assertEqual([f[0] for f in sprite.frames], ["idle_0", "idle_1", "jump_0"])
        self.assertEqual(sprite.tags, [{"name": "idle", "from": 0, "to": 1, "direction": "forward"},
                                       {"name": "jump", "from": 2, "to": 2, "direction": "forward"}])
        self.assertEqual(sprite.anchor, (2, 2))
        self.assertEqual(sprite.frames[0][2].get(0, 0), px.TRANSPARENT)
        self.assertEqual(sprite.frames[0][2].get(2, 1), (0xf4, 0xf4, 0xf4, 255))

    def test_errors_name_the_line(self):
        cases = {
            "undefined": (SLIME.replace("kgwk", "kgzk"), "slime.sprite:9: character 'z' at column 3"),
            "width": (SLIME.replace("kggk\nframe idle_1", "kgk\nframe idle_1"), "row has 3 pixels, expected 4"),
            "rows": (SLIME.replace(".kk.\nanchor", "anchor"), "frame 'jump_0' has 2 rows, expected 3"),
            "hash": (SLIME.replace("  w #f4f4f4", "  # #f4f4f4\n  w #f4f4f4").replace("# test sprite\n", ""), None),
            "noframes": ("name: x\npalette:\n  k #000000\n", "no frames found"),
        }
        for label, (text, expected) in cases.items():
            with self.subTest(label=label):
                if label == "hash":
                    sprite = px.parse_sprite(text, "slime.sprite")  # '# ...' inside palette is a comment
                    self.assertNotIn("#", sprite.palette)
                    continue
                with self.assertRaises(px.PixelError) as caught:
                    px.parse_sprite(text, "slime.sprite")
                self.assertIn(expected, str(caught.exception))

    def test_builtin_palette_maps_hex_digits(self):
        sprite = px.parse_sprite("palette: use pico8\nframe a\n08\nf.\n", "p.sprite")
        image = sprite.frames[0][2]
        self.assertEqual(image.get(0, 0), (0, 0, 0, 255))
        self.assertEqual(image.get(1, 0), (0xff, 0x00, 0x4d, 255))
        self.assertEqual(image.get(0, 1), (0xff, 0xcc, 0xaa, 255))


class SheetAndValidationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_sheet_layout_metadata_and_extrusion(self):
        sprite = px.parse_sprite(SLIME, "slime.sprite")
        sheet, meta = px.pack_sheet(sprite.frames, columns=2, padding=1, extrude=1, tags=sprite.tags,
                                    anchor=sprite.anchor, scale=2)
        cell_w, cell_h = 4 * 2 + 2 + 1, 3 * 2 + 2 + 1
        self.assertEqual((sheet.width, sheet.height), (2 * cell_w - 1, 2 * cell_h - 1))
        frames = meta["frames"]
        self.assertEqual(frames[1]["frame"], {"x": cell_w + 1, "y": 1, "w": 8, "h": 6})
        self.assertEqual(frames[2]["frame"]["y"], cell_h + 1)
        self.assertEqual([f["duration"] for f in frames], [150, 150, 80])
        self.assertEqual(meta["meta"]["frameTags"][0], {"name": "idle", "from": 0, "to": 1, "direction": "forward"})
        self.assertEqual(meta["meta"]["anchor"], {"x": 4, "y": 4})
        first = frames[0]["frame"]
        self.assertEqual(sheet.get(first["x"] - 1, first["y"] + 2), sheet.get(first["x"], first["y"] + 2))
        self.assertEqual(sheet.get(first["x"] + 2, first["y"] - 1), sheet.get(first["x"] + 2, first["y"]))

    def test_validation_findings(self):
        image = px.Image(4, 4)
        image.set(0, 0, (255, 0, 0, 255))
        image.set(1, 0, (0, 255, 0, 128))
        image.set(3, 3, (1, 2, 3, 255))
        image.set(2, 3, (9, 9, 9, 255))
        result = px.validate_image(image, palette=px.load_palette("pico8")[1], max_colors=2, cell=(3, 3))
        text = " ".join(result["errors"])
        self.assertIn("semi-transparent", text)
        self.assertIn("more than the limit of 2", text)
        self.assertIn("outside the palette", text)
        self.assertIn("not a multiple of the 3x3 cell", text)
        self.assertFalse(result["ok"])
        self.assertTrue(any("isolated single pixels" in w for w in result["warnings"]))
        clean = px.parse_sprite(SLIME, "s.sprite").frames[0][2]
        self.assertTrue(px.validate_image(clean, max_colors=3).get("ok"))

    def test_cli_render_validate_and_exit_codes(self):
        sprite_path = self.dir / "slime.sprite"
        sprite_path.write_text(SLIME, encoding="utf-8")
        result = run("render", sprite_path, "--out", self.dir / "out", "--sheet", "--scale", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        meta = json.loads((self.dir / "out" / "slime.json").read_text())
        self.assertEqual(meta["meta"]["image"], "slime.png")
        self.assertEqual(run("validate", self.dir / "out" / "slime.png", "--max-colors", "3").returncode, 0)
        failed = run("validate", self.dir / "out" / "slime.png", "--palette", "gameboy")
        self.assertEqual(failed.returncode, 1)
        self.assertIn("outside the palette", failed.stdout)
        frames = run("render", sprite_path, "--out", self.dir / "frames")
        self.assertEqual(frames.returncode, 0)
        pngs = sorted(p.name for p in (self.dir / "frames").iterdir())
        self.assertEqual(pngs, ["slime-idle_0.png", "slime-idle_1.png", "slime-jump_0.png"])
        packed = run("sheet", *[self.dir / "frames" / n for n in pngs], "--out", self.dir / "packed.png")
        self.assertEqual(packed.returncode, 0, packed.stderr)
        self.assertEqual(len(json.loads((self.dir / "packed.json").read_text())["frames"]), 3)
        bad = self.dir / "bad.sprite"
        bad.write_text("frame a\nxx\n", encoding="utf-8")
        self.assertEqual(run("render", bad, "--out", self.dir / "x").returncode, 1)
        self.assertEqual(run("palette", "show", "nope").returncode, 2)
        listed = run("palette", "list")
        self.assertIn("sweetie16", listed.stdout)


if __name__ == "__main__":
    unittest.main()
