"""Tests for the mych-emoji-language specialist's emoji_tool.py."""

from __future__ import annotations

import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unicodedata
import unittest
import zlib
from pathlib import Path

from support import REPO_ROOT

SCRIPT = REPO_ROOT / "specialists" / "mych-emoji-language" / "scripts" / "emoji_tool.py"


def load():
    name = "mych_emoji_tool"
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


em = load()
FAMILY = "\U0001F468‍\U0001F469‍\U0001F467"          # man ZWJ woman ZWJ girl
FLAG_NO = "\U0001F1F3\U0001F1F4"                                 # regional indicators N O
KEYCAP_ONE = "1️⃣"
THUMBS_MEDIUM = "\U0001F44D\U0001F3FD"
ENGLAND = "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"
HEART_TEXT = "❤"
HEART_EMOJI = "❤️"


def png(width, height, extra=b""):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    raw = b"".join(b"\0" + b"\0\0\0\0" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw)) + extra + chunk(b"IEND", b""))


class SegmentationTest(unittest.TestCase):
    def test_sequences_are_single_graphemes_with_correct_kinds(self):
        text = "Hi " + FAMILY + FLAG_NO + KEYCAP_ONE + THUMBS_MEDIUM + ENGLAND + HEART_EMOJI
        clusters = em.graphemes(text)
        self.assertEqual(clusters, ["H", "i", " ", FAMILY, FLAG_NO, KEYCAP_ONE, THUMBS_MEDIUM, ENGLAND, HEART_EMOJI])
        kinds = {c: em.classify(c)["kinds"] for c in clusters[3:]}
        self.assertIn("ZWJ sequence", kinds[FAMILY])
        self.assertIn("flag sequence (NO)", kinds[FLAG_NO])
        self.assertIn("keycap sequence", kinds[KEYCAP_ONE])
        self.assertIn("skin tone modifier (medium)", kinds[THUMBS_MEDIUM])
        self.assertIn("tag sequence (gbeng)", kinds[ENGLAND])
        self.assertIn("emoji presentation selector (FE0F)", kinds[HEART_EMOJI])

    def test_two_flags_split_into_two_graphemes(self):
        self.assertEqual(em.graphemes(FLAG_NO + FLAG_NO), [FLAG_NO, FLAG_NO])

    def test_lengths_differ_by_counting_system(self):
        self.assertEqual(em.lengths(FAMILY), {"graphemes": 1, "code_points": 5, "utf16_units": 8, "utf8_bytes": 18})


class WarningTest(unittest.TestCase):
    def test_text_default_heart_warns_and_fully_qualified_does_not(self):
        self.assertTrue(any("FE0F" in w for w in em.inspect(HEART_TEXT)["warnings"]))
        self.assertEqual(em.inspect(HEART_EMOJI)["warnings"], [])

    def test_structural_problems(self):
        self.assertTrue(any("lone regional indicator" in w for w in em.inspect("\U0001F1F3")["warnings"]))
        self.assertTrue(any("without a base" in w for w in em.inspect("\U0001F3FD")["warnings"]))
        self.assertTrue(any("without U+FE0F" in w for w in em.inspect("1⃣")["warnings"]))
        self.assertTrue(any("CANCEL TAG" in w for w in em.inspect("\U0001F3F4\U000E0067\U000E0062")["warnings"]))

    def test_newer_code_points_are_flagged_not_guessed(self):
        candidate = 0x1FAE9  # proposed after Unicode 15.1; unassigned in older databases
        if unicodedata.category(chr(candidate)) != "Cn":
            self.skipTest("this Python's Unicode database already includes U+1FAE9")
        report = em.inspect(chr(candidate))
        self.assertTrue(any("unassigned in this Python's Unicode" in w for w in report["warnings"]))
        self.assertTrue(report["graphemes"][0]["names"][0].startswith("<unknown in Unicode"))

    def test_cli_inspect_json_and_exit_codes(self):
        ok = subprocess.run([sys.executable, "-B", str(SCRIPT), "inspect", HEART_EMOJI, "--json"], capture_output=True,
                            text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["graphemes"][0]["names"][0], "HEAVY BLACK HEART")
        warn = subprocess.run([sys.executable, "-B", str(SCRIPT), "inspect", HEART_TEXT], capture_output=True, text=True)
        self.assertEqual(warn.returncode, 1)


class AssetTest(unittest.TestCase):
    def test_png_asset_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.png"
            good.write_bytes(png(128, 128))
            report = em.check_asset(good, "discord")
            self.assertTrue(report["ok"])
            self.assertEqual((report["width"], report["height"], report["animated"]), (128, 128, False))
            self.assertIn("secondary sources", report["guidance_source"])
            wide = Path(tmp) / "wide.png"
            wide.write_bytes(png(200, 100, extra=b"\0\0\0\x08acTL" + b"\0" * 12))
            report = em.check_asset(wide, "generic")
            self.assertTrue(any("square" in w for w in report["warnings"]))
            self.assertTrue(report["animated"])
            big = Path(tmp) / "big.png"
            big.write_bytes(png(128, 128) + b"\0" * (300 * 1024))
            self.assertFalse(em.check_asset(big, "discord")["ok"])
            bad = Path(tmp) / "bad.png"
            bad.write_bytes(b"hello")
            result = subprocess.run([sys.executable, "-B", str(SCRIPT), "check-asset", str(bad)], capture_output=True,
                                    text=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
