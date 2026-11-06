#!/usr/bin/env python3
"""Inspect emoji sequences and check custom emoji assets (standard library only).

Commands:
  inspect TEXT [--json]                  graphemes, code points with names, sequence types, counts, warnings
  length TEXT                            lengths as different systems count them (graphemes, code points,
                                         UTF-16 units, UTF-8 bytes)
  check-asset FILE --platform discord|generic [--json]
                                         dimensions, file size and animation against platform guidance

Names come from Python's unicodedata module, whose Unicode version is
reported; code points newer than that version are flagged as unknown, never
guessed. Grapheme segmentation follows the Unicode extended grapheme cluster
rules for emoji (ZWJ sequences, modifiers, variation selectors, keycaps,
regional-indicator pairs, tag sequences, combining marks); it is an
approximation of UAX #29, not a full implementation.
Exit status: 0 OK, 1 warnings found (inspect) or asset fails guidance, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

ZWJ = 0x200D
VS15, VS16 = 0xFE0E, 0xFE0F
KEYCAP = 0x20E3
CANCEL_TAG = 0xE007F
KEYCAP_BASES = set(map(ord, "0123456789#*"))
# Common emoji whose default presentation is text: without U+FE0F they may render
# as monochrome symbols on some platforms. A curated subset, not the full list.
TEXT_DEFAULT = {
    0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x2194, 0x2195, 0x2196, 0x2197, 0x2198, 0x2199, 0x2600,
    0x2601, 0x260E, 0x2611, 0x261D, 0x263A, 0x2639, 0x2640, 0x2642, 0x2660, 0x2663, 0x2665, 0x2666, 0x267B,
    0x26A0, 0x2702, 0x2708, 0x2709, 0x270C, 0x270D, 0x270F, 0x2712, 0x2714, 0x2716, 0x2733, 0x2734, 0x2744,
    0x2747, 0x2763, 0x2764, 0x27A1, 0x2B05, 0x2B06, 0x2B07, 0x3030, 0x303D, 0x3297, 0x3299,
}
SKIN_TONES = {0x1F3FB: "light", 0x1F3FC: "medium-light", 0x1F3FD: "medium", 0x1F3FE: "medium-dark", 0x1F3FF: "dark"}

# Guidance for custom emoji assets. Platform limits change: verify against current documentation.
PLATFORMS: Dict[str, Dict[str, Any]] = {
    "discord": {"max_bytes": 256 * 1024, "recommended": (128, 128), "square": True,
                "source": "secondary sources (community guides, retrieved 2026-11-01): 256 KB and 128x128; Discord's "
                          "help center pages found did not state the file size; verify before relying on it"},
    "generic": {"max_bytes": 128 * 1024, "recommended": (128, 128), "square": True,
                "source": "conservative defaults that fit common chat platforms; not a platform rule"},
}


def is_regional(cp: int) -> bool:
    return 0x1F1E6 <= cp <= 0x1F1FF


def is_tag(cp: int) -> bool:
    return 0xE0020 <= cp <= 0xE007F


def is_modifier(cp: int) -> bool:
    return cp in SKIN_TONES


def is_extend(cp: int) -> bool:
    if cp in (VS15, VS16, KEYCAP, ZWJ) or is_modifier(cp) or is_tag(cp):
        return True
    category = unicodedata.category(chr(cp))
    return category in ("Mn", "Me", "Mc")


def graphemes(text: str) -> List[str]:
    """Split text into (approximate) extended grapheme clusters, emoji-aware."""
    clusters: List[List[int]] = []
    for ch in text:
        cp = ord(ch)
        if clusters:
            current = clusters[-1]
            previous = current[-1]
            if is_extend(cp):  # variation selectors, modifiers, keycap, ZWJ, tags, combining marks
                current.append(cp)
                continue
            if previous == ZWJ and len(current) > 1:
                current.append(cp)
                continue
            if is_regional(cp) and is_regional(previous) and sum(1 for c in current if is_regional(c)) % 2 == 1:
                current.append(cp)
                continue
        clusters.append([cp])
    return ["".join(map(chr, cluster)) for cluster in clusters]


def name_of(cp: int) -> Optional[str]:
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        return None


def classify(cluster: str) -> Dict[str, Any]:
    cps = [ord(c) for c in cluster]
    kinds: List[str] = []
    warnings: List[str] = []
    if len(cps) >= 2 and all(is_regional(c) for c in cps[:2]) and len(cps) == 2:
        letters = "".join(chr(c - 0x1F1E6 + ord("A")) for c in cps)
        kinds.append("flag sequence ({})".format(letters))
    elif len(cps) == 1 and is_regional(cps[0]):
        kinds.append("regional indicator")
        warnings.append("lone regional indicator: flags need a pair")
    if ZWJ in cps:
        kinds.append("ZWJ sequence")
        if cps[0] == ZWJ or cps[-1] == ZWJ:
            warnings.append("zero-width joiner at the start or end of a sequence")
    if any(is_modifier(c) for c in cps):
        tones = [SKIN_TONES[c] for c in cps if is_modifier(c)]
        kinds.append("skin tone modifier ({})".format(", ".join(tones)))
        if is_modifier(cps[0]):
            warnings.append("skin tone modifier without a base emoji")
    if KEYCAP in cps:
        kinds.append("keycap sequence")
        if cps[0] not in KEYCAP_BASES:
            warnings.append("keycap mark on a base other than 0-9, # or *")
        elif VS16 not in cps:
            warnings.append("keycap sequence without U+FE0F (fully qualified form is base + FE0F + 20E3)")
    if cps[0] == 0x1F3F4 and len(cps) > 1 and all(is_tag(c) for c in cps[1:]):
        tag_text = "".join(chr(c - 0xE0000) for c in cps[1:] if c != CANCEL_TAG)
        kinds.append("tag sequence ({})".format(tag_text))
        if cps[-1] != CANCEL_TAG:
            warnings.append("tag sequence without the CANCEL TAG terminator")
    if VS16 in cps:
        kinds.append("emoji presentation selector (FE0F)")
    if VS15 in cps:
        kinds.append("text presentation selector (FE0E)")
    if len(cps) == 1 and cps[0] in TEXT_DEFAULT:
        warnings.append("U+{:04X} defaults to text presentation on some platforms; add U+FE0F for emoji style".format(cps[0]))
    for cp in cps:
        if name_of(cp) is None and unicodedata.category(chr(cp)) == "Cn":
            warnings.append("U+{:04X} is unassigned in this Python's Unicode {} database; it may be a newer emoji that "
                            "older systems cannot show".format(cp, unicodedata.unidata_version))
    if not kinds:
        kinds.append("single code point" if len(cps) == 1 else "combined sequence")
    return {"text": cluster, "code_points": ["U+{:04X}".format(c) for c in cps],
            "names": [name_of(c) or "<unknown in Unicode {}>".format(unicodedata.unidata_version) for c in cps],
            "kinds": kinds, "warnings": warnings}


def lengths(text: str) -> Dict[str, int]:
    return {"graphemes": len(graphemes(text)), "code_points": len(text),
            "utf16_units": len(text.encode("utf-16-le")) // 2, "utf8_bytes": len(text.encode("utf-8"))}


def inspect(text: str) -> Dict[str, Any]:
    clusters = [classify(cluster) for cluster in graphemes(text)]
    return {"unicode_version": unicodedata.unidata_version, "lengths": lengths(text), "graphemes": clusters,
            "warnings": [w for c in clusters for w in c["warnings"]]}


def read_image_facts(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    facts: Dict[str, Any] = {"file": str(path), "bytes": len(data)}
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        facts["format"] = "png"
        facts["width"], facts["height"] = struct.unpack(">II", data[16:24])
        facts["animated"] = b"acTL" in data[:4096]
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        facts["format"] = "gif"
        facts["width"], facts["height"] = struct.unpack("<HH", data[6:10])
        facts["animated"] = data.count(b"\x21\xf9\x04") > 1
    else:
        raise ValueError("{} is not a PNG or GIF file".format(path))
    return facts


def check_asset(path: Path, platform: str) -> Dict[str, Any]:
    rules = PLATFORMS[platform]
    facts = read_image_facts(path)
    errors, warnings = [], []
    if facts["bytes"] > rules["max_bytes"]:
        errors.append("file is {} bytes, over the {} byte guidance".format(facts["bytes"], rules["max_bytes"]))
    if rules["square"] and facts["width"] != facts["height"]:
        warnings.append("image is {}x{}; square images avoid letterboxing".format(facts["width"], facts["height"]))
    rw, rh = rules["recommended"]
    if (facts["width"], facts["height"]) != (rw, rh):
        warnings.append("recommended size is {}x{}; check legibility at small display sizes".format(rw, rh))
    return dict(facts, platform=platform, guidance_source=rules["source"], errors=errors, warnings=warnings,
                ok=not errors)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Emoji sequence inspector and custom emoji asset checker.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    p = sub.add_parser("inspect")
    p.add_argument("text")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("length")
    p.add_argument("text")
    p = sub.add_parser("check-asset")
    p.add_argument("file")
    p.add_argument("--platform", choices=tuple(PLATFORMS), default="generic")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "length":
        print(json.dumps(lengths(args.text), indent=2))
        return 0
    if args.command == "inspect":
        report = inspect(args.text)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("Unicode database: {}; lengths: {}".format(report["unicode_version"], report["lengths"]))
            for index, cluster in enumerate(report["graphemes"], 1):
                print("{}. {}  {}  [{}]".format(index, cluster["text"], " ".join(cluster["code_points"]),
                                                "; ".join(cluster["kinds"])))
                for name in cluster["names"]:
                    print("     {}".format(name))
                for warning in cluster["warnings"]:
                    print("   warning: {}".format(warning))
        return 1 if report["warnings"] else 0
    try:
        report = check_asset(Path(args.file), args.platform)
    except (OSError, ValueError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("{}: {} {}x{}, {} bytes{}".format(report["file"], report["format"], report["width"], report["height"],
                                                report["bytes"], ", animated" if report["animated"] else ""))
        for item in report["errors"]:
            print("error: " + item)
        for item in report["warnings"]:
            print("warning: " + item)
        print("Guidance source: " + report["guidance_source"])
        print("Result: {}".format("PASS" if report["ok"] else "FAIL"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
