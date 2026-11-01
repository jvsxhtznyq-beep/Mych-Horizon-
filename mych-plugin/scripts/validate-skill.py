#!/usr/bin/env python3
"""Validate an Agent Skill folder before it is packaged or uploaded.

Checks, in order:

  1. structure    required files and folders exist
  2. frontmatter  SKILL.md opens with YAML frontmatter that parses
  3. metadata     required fields are present and within documented limits
  4. naming       the skill name is valid and matches its folder
  5. references   every referenced file exists
  6. links        internal Markdown links and heading anchors resolve
  7. content      no empty or placeholder files; Python scripts compile
  8. hygiene      expected layout, no development artifacts or secrets

Usage:
  python3 validate-skill.py [SKILL_DIR] [--strict] [--json]

SKILL_DIR defaults to the skill that contains this script. Exit status is 0
when no errors are found (with --strict, also no warnings), 1 when problems
are found, and 2 for usage errors. Only the standard library is required. If
PyYAML is installed, the frontmatter is also parsed with yaml.safe_load and
the two results are compared.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Limits and rules
# ---------------------------------------------------------------------------

# Field limits from the Agent Skills specification, also documented by
# Anthropic for SKILL.md frontmatter.
NAME_MAX_CHARS = 64
DESCRIPTION_MAX_CHARS = 1024
COMPATIBILITY_MAX_CHARS = 500
# Anthropic's authoring guidance: keep the SKILL.md body under 500 lines.
SKILL_BODY_MAX_LINES = 500
# Authoring guidance: reference files longer than 100 lines should open with
# a table of contents, so a partial read still shows the file's scope.
TOC_THRESHOLD_LINES = 100
# A Markdown file with fewer non-blank lines than this is almost certainly a
# stub rather than meaningful guidance.
MIN_MEANINGFUL_LINES = 8
# Shorter descriptions rarely give Claude enough to decide when to load a skill.
DESCRIPTION_MIN_USEFUL_CHARS = 40

ALLOWED_FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")
REQUIRED_FIELDS = ("name", "description")
RESERVED_NAME_WORDS = ("anthropic", "claude")
LICENSE_FILE_NAMES = frozenset({"LICENSE", "LICENSE.txt", "LICENSE.md", "NOTICE", "NOTICE.txt"})

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEBAB_FILE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+)+$")
KEBAB_DIR_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
XML_TAG_RE = re.compile(r"<\s*/?\s*[A-Za-z!?][^<>]*>")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
WHEN_CUE_RE = re.compile(r"\b(use|used|using|when|whenever|for)\b", re.IGNORECASE)
FIRST_OR_SECOND_PERSON_RE = re.compile(r"^\s*(i|i'm|i am|we|you|you can|this skill lets you)\b", re.IGNORECASE)

# Folder layouts enforced for skills with these names. Other skills get the
# generic checks only. Add an entry when another skill needs a fixed layout.
LAYOUTS: Dict[str, Dict[str, Any]] = {
    "mych-plugin": {
        "directories": [
            "core", "modes", "workflows", "standards", "systems", "templates", "references", "scripts",
        ],
        "files": [
            "SKILL.md",
            "core/intelligence-coordinator.md",
            "core/specialist-selection.md",
            "modes/architect.md",
            "modes/researcher.md",
            "modes/designer.md",
            "modes/engineer.md",
            "modes/inventor.md",
            "workflows/execution-lifecycle.md",
            "standards/quality-framework.md",
            "standards/testing-strategy.md",
            "standards/completion-criteria.md",
            "standards/security.md",
            "standards/transparency-and-reporting.md",
            "systems/task-management.md",
            "systems/project-memory.md",
            "systems/decision-records.md",
            "systems/tool-availability.md",
            "systems/autonomy-and-approval.md",
            "scripts/validate-skill.py",
            "scripts/package-skill.py",
        ],
        "metadata": ["version", "display-name"],
        # Kebab-case violations are errors instead of warnings.
        "strict_naming": True,
        # Every file must be referenced from SKILL.md (references one level deep).
        "full_coverage": True,
    },
}

# What never belongs in a packaged skill. The packager imports these rules,
# so this module is the single source of truth for exclusions.
EXCLUDED_DIR_NAMES = frozenset({"__pycache__", "node_modules", "venv", "dist", "build", "htmlcov"})
EXCLUDED_DIR_SUFFIXES = (".egg-info",)
EXCLUDED_FILE_NAMES = frozenset({"Thumbs.db", "desktop.ini"})
EXCLUDED_FILE_SUFFIXES = (".pyc", ".pyo", ".swp", ".swo", ".tmp", ".bak", ".orig", ".rej", ".log", ".zip")
SECRET_NAME_RE = re.compile(
    r"^(?:\.env(?:\.(?!example$|sample$|template$)[\w.-]+)?"
    r"|id_(?:rsa|dsa|ecdsa|ed25519)"
    r"|credentials\.json"
    r"|.+\.(?:pem|key|p12|pfx|keystore|jks))$",
    re.IGNORECASE,
)

TEXT_SUFFIXES = frozenset({
    ".md", ".txt", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".csv", ".js", ".ts", ".html", ".css",
})
# Placeholder markers: a TODO-style word at the start of a line (after optional
# list, quote, heading or comment markers), filler text, or a line that is only
# a placeholder phrase.
PLACEHOLDER_PATTERNS = (
    re.compile(r"^\s*(?:[-*+>#]+\s*|//\s*|<!--\s*)?(?:TODO|TBD|FIXME|XXX)\b"),
    re.compile(r"lorem\s+ipsum", re.IGNORECASE),
    re.compile(
        r"^\s*(?:[-*+>#]+\s*)?(?:coming soon|placeholder|content goes here|to be written)\.?\s*$",
        re.IGNORECASE,
    ),
)

CHECKS = (
    ("structure", "Required files and folders exist"),
    ("frontmatter", "Frontmatter is valid YAML"),
    ("metadata", "Required metadata is present and within limits"),
    ("naming", "Skill name is valid and matches its folder"),
    ("references", "Referenced files exist"),
    ("links", "Internal links and anchors resolve"),
    ("content", "No empty or placeholder files; scripts compile"),
    ("hygiene", "Expected layout; no development artifacts or secrets"),
)

DEFAULT_SKILL_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Exclusion rules (shared with the packager)
# ---------------------------------------------------------------------------

def classify_path(parts: Sequence[str], is_dir: bool = False) -> Optional[Tuple[str, str]]:
    """Classify a path relative to the skill root.

    Returns None for files that belong in a package, ("secret", reason) for
    secret-like files, or ("artifact", reason) for development artifacts.
    """
    if not parts:
        return None
    folders = list(parts) if is_dir else list(parts[:-1])
    for folder in folders:
        if folder.startswith("."):
            return ("artifact", "hidden folder '{}'".format(folder))
        if folder in EXCLUDED_DIR_NAMES or folder.endswith(EXCLUDED_DIR_SUFFIXES):
            return ("artifact", "development folder '{}'".format(folder))
    if is_dir:
        return None
    name = parts[-1]
    if SECRET_NAME_RE.match(name):
        return ("secret", "secret-like file '{}'".format(name))
    if name.startswith("."):
        return ("artifact", "hidden file '{}'".format(name))
    if name in EXCLUDED_FILE_NAMES or name.endswith("~") or name.lower().endswith(EXCLUDED_FILE_SUFFIXES):
        return ("artifact", "development artifact '{}'".format(name))
    return None


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

class FrontmatterError(Exception):
    """A frontmatter problem with the SKILL.md line number where it occurs.

    ``fatal`` marks violations of YAML itself (such as duplicate keys) that
    stay errors even when a lenient parser like PyYAML accepts them.
    """

    def __init__(self, message: str, line: Optional[int] = None, fatal: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.fatal = fatal

    def __str__(self) -> str:
        return "line {}: {}".format(self.line, self.message) if self.line else self.message


# Plain (unquoted) YAML scalars that standard parsers convert to non-strings.
IMPLICIT_TYPE_PATTERNS = (
    ("boolean", re.compile(
        r"^(?:y|Y|yes|Yes|YES|n|N|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF)$")),
    ("null", re.compile(r"^(?:~|null|Null|NULL)$")),
    ("integer", re.compile(r"^(?:[-+]?(?:0|[1-9][0-9_]*)|0x[0-9a-fA-F_]+|0o[0-7_]+|0b[01_]+)$")),
    ("number", re.compile(
        r"^(?:[-+]?(?:[0-9][0-9_]*\.[0-9_]*|\.[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)?"
        r"|[-+]?[0-9][0-9_]*[eE][-+]?[0-9]+|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$")),
    ("date", re.compile(
        r"^\d{4}-\d{1,2}-\d{1,2}(?:(?:[Tt]|[ \t]+)\d{1,2}:\d{2}:\d{2}(?:\.\d*)?"
        r"(?:[ \t]*(?:Z|[-+]\d{1,2}(?::\d{2})?))?)?$")),
)

_KEY_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*)[ ]*:(?:[ ]+(.*)|[ ]*)$")
_BLOCK_HEADER_RE = re.compile(r"^([|>])([+-]?)([1-9]?)([+-]?)[ ]*(?:#.*)?$")
_DOUBLE_ESCAPES = {
    "0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f",
    "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85",
    "_": "\xa0", "L": " ", "P": " ",
}


def _format_path(path: Sequence[Any]) -> str:
    text = ""
    for part in path:
        if isinstance(part, int):
            text += "[{}]".format(part)
        else:
            text += ("." if text else "") + str(part)
    return text


class _FrontmatterParser:
    """A strict parser for the YAML subset that skill frontmatter needs.

    Supported: top-level ``key: value`` fields; plain, single-quoted and
    double-quoted scalars; literal and folded block scalars; one level of
    nested mapping (for ``metadata``); block sequences of scalars. Anything
    else (anchors, tags, flow collections, deeper nesting, multi-line quoted
    strings) is rejected rather than guessed at.
    """

    def __init__(self, lines: List[str], first_line_number: int) -> None:
        self.lines = lines
        self.base = first_line_number
        self.i = 0
        self.plain_scalars: List[Tuple[Tuple[Any, ...], str, int]] = []
        self.warnings: List[str] = []

    # -- helpers ------------------------------------------------------------

    def _line_no(self, index: Optional[int] = None) -> int:
        return self.base + (self.i if index is None else index)

    def _error(self, message: str, index: Optional[int] = None) -> FrontmatterError:
        return FrontmatterError(message, self._line_no(index))

    @staticmethod
    def _skippable(raw: str) -> bool:
        stripped = raw.strip()
        return not stripped or stripped.startswith("#")

    @staticmethod
    def _indent(raw: str) -> int:
        return len(raw) - len(raw.lstrip(" "))

    def _check_tabs(self, raw: str, index: Optional[int] = None) -> None:
        leading = raw[: len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in leading:
            raise self._error("tab characters cannot indent YAML; use spaces", index)

    def _next_content_index(self, start: int) -> Optional[int]:
        for index in range(start, len(self.lines)):
            if not self._skippable(self.lines[index]):
                return index
        return None

    def _split_key(self, text: str) -> Tuple[str, str]:
        match = _KEY_RE.match(text)
        if not match:
            if text.startswith("- ") or text == "-":
                raise self._error("a list item appears where a 'field: value' line was expected")
            if text[:1] in ("'", '"'):
                raise self._error("quoted field names are not supported in skill frontmatter")
            raise self._error("expected 'field: value', found {!r}".format(text[:60]))
        return match.group(1), (match.group(2) or "").rstrip()

    # -- entry point --------------------------------------------------------

    def parse(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if self._skippable(raw):
                self.i += 1
                continue
            self._check_tabs(raw)
            if self._indent(raw) != 0:
                raise self._error("unexpected indentation: top-level fields start in the first column")
            key, rest = self._split_key(raw.strip())
            if key in result:
                raise FrontmatterError("duplicate field '{}'".format(key), self._line_no(), fatal=True)
            result[key] = self._parse_value(rest, indent=0, path=(key,), allow_containers=True)
        return result

    # -- values -------------------------------------------------------------

    def _parse_value(self, rest: str, indent: int, path: Tuple[Any, ...], allow_containers: bool) -> Any:
        key_index = self.i
        self.i += 1
        if rest == "" or rest.startswith("#"):
            next_index = self._next_content_index(self.i)
            if next_index is None:
                return None
            nxt = self.lines[next_index]
            self._check_tabs(nxt, next_index)
            next_indent = self._indent(nxt)
            is_item = nxt.strip() == "-" or nxt.strip().startswith("- ")
            if is_item and next_indent >= indent:
                if not allow_containers:
                    raise self._error("lists nested inside '{}' are not supported".format(_format_path(path[:-1])),
                                      next_index)
                return self._parse_sequence(next_indent, path)
            if next_indent > indent:
                if not allow_containers:
                    raise self._error(
                        "nesting deeper than one level is not supported in skill frontmatter", next_index)
                return self._parse_mapping(next_indent, path)
            return None
        first = rest[0]
        if first in "|>":
            return self._parse_block_scalar(rest, indent, key_index)
        if first in "[{":
            raise self._error("flow collections ([...] or {...}) are not supported; use block style", key_index)
        if first in "&*!":
            raise self._error("anchors, aliases and tags are not supported in skill frontmatter", key_index)
        if first in "@`%":
            raise self._error("a value cannot start with '{}'; quote it".format(first), key_index)
        if first in "-?:" and (len(rest) == 1 or rest[1] == " "):
            raise self._error("a value cannot start with '{} '; quote it".format(first), key_index)
        if first in "\"'":
            return self._parse_quoted(rest, key_index)
        return self._parse_plain(rest, indent, path, key_index)

    def _parse_quoted(self, text: str, index: int) -> str:
        quote = text[0]
        out: List[str] = []
        pos = 1
        while True:
            if pos >= len(text):
                raise self._error(
                    "unterminated {}-quoted value (multi-line quoted values are not supported; "
                    "use a block scalar such as '>-')".format("double" if quote == '"' else "single"), index)
            char = text[pos]
            if quote == "'":
                if char == "'":
                    if pos + 1 < len(text) and text[pos + 1] == "'":
                        out.append("'")
                        pos += 2
                        continue
                    pos += 1
                    break
                out.append(char)
                pos += 1
                continue
            if char == '"':
                pos += 1
                break
            if char == "\\":
                if pos + 1 >= len(text):
                    raise self._error("a double-quoted value ends with a lone backslash", index)
                code = text[pos + 1]
                if code in _DOUBLE_ESCAPES:
                    out.append(_DOUBLE_ESCAPES[code])
                    pos += 2
                    continue
                widths = {"x": 2, "u": 4, "U": 8}
                if code in widths:
                    digits = text[pos + 2: pos + 2 + widths[code]]
                    if len(digits) != widths[code] or not re.fullmatch(r"[0-9A-Fa-f]+", digits):
                        raise self._error("invalid \\{} escape in a double-quoted value".format(code), index)
                    out.append(chr(int(digits, 16)))
                    pos += 2 + widths[code]
                    continue
                raise self._error("unknown escape '\\{}' in a double-quoted value".format(code), index)
            out.append(char)
            pos += 1
        remainder = text[pos:]
        if remainder.strip() and not re.match(r"^\s+#", remainder):
            raise self._error("unexpected text after the closing quote: {!r}".format(remainder.strip()), index)
        return "".join(out)

    def _strip_plain_comment(self, text: str, path: Tuple[Any, ...], index: int) -> str:
        match = re.search(r"[ \t]#", text)
        if match:
            self.warnings.append(
                "line {}: text after ' #' in '{}' is a YAML comment and is dropped; quote the value if "
                "the '#' is part of it".format(self._line_no(index), _format_path(path)))
            text = text[: match.start()]
        return text.rstrip()

    def _check_plain_text(self, text: str, index: int) -> None:
        if ": " in text or text.endswith(":"):
            raise self._error("an unquoted value cannot contain ': ' or end with ':'; quote the value", index)

    def _parse_plain(self, rest: str, indent: int, path: Tuple[Any, ...], key_index: int) -> str:
        text = self._strip_plain_comment(rest, path, key_index)
        self._check_plain_text(text, key_index)
        parts = [text]
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if not raw.strip() or self._indent(raw) <= indent:
                break
            self._check_tabs(raw)
            stripped = raw.strip()
            if stripped.startswith("#"):
                raise self._error("comment lines cannot interrupt a multi-line value")
            continuation = self._strip_plain_comment(stripped, path, self.i)
            self._check_plain_text(continuation, self.i)
            parts.append(continuation)
            self.i += 1
        value = " ".join(part for part in parts if part)
        self.plain_scalars.append((path, value, self._line_no(key_index)))
        return value

    def _parse_block_scalar(self, header: str, indent: int, key_index: int) -> str:
        match = _BLOCK_HEADER_RE.match(header)
        if not match or (match.group(2) and match.group(4)):
            raise self._error("invalid block scalar header {!r}".format(header), key_index)
        style = match.group(1)
        chomping = match.group(2) or match.group(4)
        explicit_indent = int(match.group(3)) if match.group(3) else None
        raw_lines: List[Tuple[int, str]] = []
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if raw.strip() and self._indent(raw) <= indent:
                break
            raw_lines.append((self.i, raw))
            self.i += 1
        content_indent: Optional[int] = None
        if explicit_indent is not None:
            content_indent = indent + explicit_indent
        else:
            for index, raw in raw_lines:
                if raw.strip():
                    self._check_tabs(raw, index)
                    content_indent = self._indent(raw)
                    break
        if content_indent is None:
            return "\n" * len(raw_lines) if chomping == "+" and raw_lines else ""
        lines: List[str] = []
        for index, raw in raw_lines:
            if not raw.strip():
                lines.append("")
                continue
            if self._indent(raw) < content_indent:
                raise self._error("a line inside the block value is indented less than the first line", index)
            lines.append(raw[content_indent:])
        trailing = 0
        while lines and lines[-1] == "":
            lines.pop()
            trailing += 1
        if style == "|":
            body = "\n".join(lines)
        else:
            body = _fold_lines(lines)
        if not lines:
            return "\n" * trailing if chomping == "+" else ""
        if chomping == "-":
            return body
        if chomping == "+":
            return body + "\n" + "\n" * trailing
        return body + "\n"

    def _parse_sequence(self, seq_indent: int, path: Tuple[Any, ...]) -> List[str]:
        items: List[str] = []
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if self._skippable(raw):
                self.i += 1
                continue
            self._check_tabs(raw)
            line_indent = self._indent(raw)
            stripped = raw.strip()
            is_item = stripped == "-" or stripped.startswith("- ")
            if line_indent < seq_indent or (line_indent == seq_indent and not is_item):
                break
            if line_indent > seq_indent:
                raise self._error("unexpected indentation inside a list")
            item = stripped[1:].strip()
            item_path = path + (len(items),)
            if not item or item.startswith("#"):
                raise self._error("empty list items and nested structures in lists are not supported")
            if item[0] in "[{&*!|>@`%" or (item[0] in "-?:" and (len(item) == 1 or item[1] == " ")):
                raise self._error("unsupported list item {!r}; quote it".format(item))
            if item[0] in "\"'":
                items.append(self._parse_quoted(item, self.i))
            else:
                if _KEY_RE.match(item):
                    raise self._error("mappings inside lists are not supported in skill frontmatter")
                text = self._strip_plain_comment(item, item_path, self.i)
                self._check_plain_text(text, self.i)
                self.plain_scalars.append((item_path, text, self._line_no()))
                items.append(text)
            self.i += 1
        return items

    def _parse_mapping(self, map_indent: int, path: Tuple[Any, ...]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if self._skippable(raw):
                self.i += 1
                continue
            self._check_tabs(raw)
            line_indent = self._indent(raw)
            if line_indent < map_indent:
                break
            if line_indent > map_indent:
                raise self._error("unexpected indentation inside '{}'".format(_format_path(path)))
            key, rest = self._split_key(raw.strip())
            if key in result:
                raise FrontmatterError("duplicate field '{}' inside '{}'".format(key, _format_path(path)),
                                       self._line_no(), fatal=True)
            result[key] = self._parse_value(rest, indent=map_indent, path=path + (key,), allow_containers=False)
        return result


def _fold_lines(lines: List[str]) -> str:
    """Apply YAML folded-style line folding to block content lines."""
    out = ""
    previous_more_indented = False
    for index, line in enumerate(lines):
        more_indented = line.startswith((" ", "\t"))
        if index == 0:
            out = line if line else "\n"
        elif line == "":
            out += "\n"
        elif lines[index - 1] == "":
            out += line
        elif more_indented or previous_more_indented:
            out += "\n" + line
        else:
            out += " " + line
        previous_more_indented = more_indented and line != ""
    return out


@dataclass
class Frontmatter:
    """Result of parsing SKILL.md frontmatter."""

    data: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    body_start_line: int = 1
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    plain_scalars: List[Tuple[Tuple[Any, ...], str, int]] = field(default_factory=list)


def _first_difference(ours: Any, theirs: Any, path: Tuple[Any, ...], skip: Set[Tuple[Any, ...]]) -> Optional[str]:
    if path in skip:
        return None
    if isinstance(ours, dict) and isinstance(theirs, dict):
        if set(ours) != set(theirs):
            return "fields differ at '{}': {} versus {}".format(
                _format_path(path) or "top level", sorted(ours), sorted(theirs))
        for key in ours:
            found = _first_difference(ours[key], theirs[key], path + (key,), skip)
            if found:
                return found
        return None
    if isinstance(ours, list) and isinstance(theirs, list):
        if len(ours) != len(theirs):
            return "list lengths differ at '{}'".format(_format_path(path))
        # Lengths are equal (checked above); zip(strict=True) needs Python 3.10.
        for index, (left, right) in enumerate(zip(ours, theirs)):  # noqa: B905
            found = _first_difference(left, right, path + (index,), skip)
            if found:
                return found
        return None
    if ours != theirs:
        return "'{}': built-in parser read {!r}, PyYAML read {!r}".format(_format_path(path), ours, theirs)
    return None


def parse_frontmatter(text: str) -> Frontmatter:
    """Split SKILL.md text into frontmatter data and body, collecting problems."""
    result = Frontmatter()
    if text.startswith("﻿"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        result.errors.append("line 1: SKILL.md must start with a '---' line that opens the YAML frontmatter")
        result.body = text
        return result
    closing = None
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            closing = index
            break
    if closing is None:
        result.errors.append("the frontmatter is never closed: add a '---' line after the last field")
        return result
    fm_lines = lines[1:closing]
    result.body = "\n".join(lines[closing + 1:])
    result.body_start_line = closing + 2
    # Every frontmatter line ends with a newline in the file; keep the last one
    # so block scalars with 'keep' chomping parse the same in both parsers.
    fm_text = "\n".join(fm_lines) + "\n"
    if not fm_text.strip():
        result.errors.append("the frontmatter is empty; it needs at least 'name' and 'description'")
        return result

    parser = _FrontmatterParser(fm_lines, first_line_number=2)
    builtin_error: Optional[FrontmatterError] = None
    try:
        result.data = parser.parse()
        result.plain_scalars = parser.plain_scalars
        result.warnings.extend(parser.warnings)
    except FrontmatterError as exc:
        builtin_error = exc

    # Plain scalars that YAML parsers would convert to booleans, numbers,
    # nulls or dates. Skill fields must be strings.
    flagged: Set[Tuple[Any, ...]] = set()
    for path, value, line in result.plain_scalars:
        for kind, pattern in IMPLICIT_TYPE_PATTERNS:
            if pattern.match(value):
                flagged.add(path)
                result.errors.append(
                    "line {}: '{}' value {!r} is read as a {} by YAML parsers; wrap it in quotes".format(
                        line, _format_path(path), value, kind))
                break

    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is None:
        if builtin_error is not None:
            result.errors.append(str(builtin_error))
        else:
            result.notes.append("PyYAML is not installed; checked with the built-in strict parser only")
        return result

    try:
        theirs = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        detail = " ".join(str(exc).split())
        if builtin_error is not None:
            result.errors.append(str(builtin_error))
        result.errors.append("standard YAML parsing failed: {}".format(detail))
        return result

    if builtin_error is not None:
        if builtin_error.fatal or not isinstance(theirs, dict):
            result.errors.append(str(builtin_error))
            return result
        result.warnings.append(
            "{} (outside the conservative subset this validator checks; standard YAML accepts it, "
            "but simpler frontmatter is safer across skill loaders)".format(builtin_error))
        result.data = theirs
        return result

    if not isinstance(theirs, dict):
        result.errors.append("the frontmatter must be a mapping of fields")
        return result
    difference = _first_difference(result.data, theirs, (), flagged)
    if difference:
        result.errors.append("parsers disagree, so skill loaders may read this differently: " + difference)
    else:
        result.notes.append("cross-checked with PyYAML {}: results agree".format(getattr(yaml, "__version__", "")))
    return result


# ---------------------------------------------------------------------------
# Markdown scanning
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_HEADING_RE = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_INLINE_LINK_RE = re.compile(
    r"(!?)\[((?:[^\[\]\\]|\\.|\[[^\[\]]*\])*)\]"
    r"\(\s*<?([^\s<>()]*(?:\([^\s()]*\)[^\s<>()]*)*)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
_REF_DEF_RE = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*<?(\S+?)>?(?:\s+.*)?$")
_CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
_HTML_ANCHOR_RE = re.compile(r"<a\s[^>]*?(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_SKILL_DIR_REF_RE = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/([A-Za-z0-9._/-]+)")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_PATH_TOKEN_RE = re.compile(r"^(?:\./)?([A-Za-z0-9_-]+)/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]*\.[A-Za-z0-9]+$")


def github_slug(text: str) -> str:
    """Return the anchor GitHub generates for a heading's text."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(r"\*\*|\*", "", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


@dataclass
class MarkdownInfo:
    """What the validator extracts from one Markdown file."""

    path: Path
    line_count: int = 0
    anchors: Set[str] = field(default_factory=set)
    headings: List[Tuple[int, int, str]] = field(default_factory=list)
    links: List[Tuple[int, str]] = field(default_factory=list)
    code_spans: List[Tuple[int, str]] = field(default_factory=list)
    skill_dir_refs: List[Tuple[int, str]] = field(default_factory=list)


def scan_markdown(path: Path, text: str) -> MarkdownInfo:
    """Extract headings, anchors, links, code spans and skill-path references."""
    info = MarkdownInfo(path=path)
    lines = text.split("\n")
    info.line_count = len(lines)
    in_fence = False
    fence_char = ""
    fence_len = 0
    slug_counts: Dict[str, int] = {}
    for number, line in enumerate(lines, start=1):
        for match in _SKILL_DIR_REF_RE.finditer(line):
            info.skill_dir_refs.append((number, match.group(1)))
        if in_fence:
            close = re.match(r"^ {0,3}(`{3,}|~{3,})[ \t]*$", line)
            if close and close.group(1)[0] == fence_char and len(close.group(1)) >= fence_len:
                in_fence = False
            continue
        opening = _FENCE_OPEN_RE.match(line)
        if opening and not (opening.group(1)[0] == "`" and "`" in opening.group(2)):
            in_fence = True
            fence_char = opening.group(1)[0]
            fence_len = len(opening.group(1))
            continue
        heading = _HEADING_RE.match(line)
        if heading:
            title = heading.group(2) or ""
            title = re.sub(r"[ \t]+#+$", "", title).strip()
            if re.fullmatch(r"#+", title):
                title = ""
            info.headings.append((number, len(heading.group(1)), title))
            base = github_slug(title)
            count = slug_counts.get(base, 0)
            info.anchors.add(base if count == 0 else "{}-{}".format(base, count))
            slug_counts[base] = count + 1
        for match in _HTML_ANCHOR_RE.finditer(line):
            info.anchors.add(match.group(1))
        for match in _CODE_SPAN_RE.finditer(line):
            info.code_spans.append((number, match.group(2).strip()))
        without_code = _CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)
        for match in _INLINE_LINK_RE.finditer(without_code):
            info.links.append((number, match.group(3)))
        definition = _REF_DEF_RE.match(without_code)
        if definition:
            info.links.append((number, definition.group(2)))
    return info


def _path_tokens(code: str) -> List[str]:
    """Return tokens in a code span that look like relative file paths."""
    found = []
    for token in code.split():
        token = token.strip("'\"")
        token = token.rstrip(",;:)")
        if token.endswith(".") and _PATH_TOKEN_RE.match(token[:-1]):
            token = token[:-1]
        if _PATH_TOKEN_RE.match(token):
            found.append(token[2:] if token.startswith("./") else token)
    return found


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    key: str
    title: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "PASS"


@dataclass
class Report:
    skill_dir: Path
    checks: Dict[str, CheckResult]
    skill_name: Optional[str] = None
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    files_checked: int = 0

    def error_count(self) -> int:
        return sum(len(check.errors) for check in self.checks.values())

    def warning_count(self) -> int:
        return sum(len(check.warnings) for check in self.checks.values())

    def ok(self, strict: bool = False) -> bool:
        return self.error_count() == 0 and (not strict or self.warning_count() == 0)

    def to_dict(self, strict: bool = False) -> Dict[str, Any]:
        return {
            "skill_dir": str(self.skill_dir),
            "skill_name": self.skill_name,
            "files_checked": self.files_checked,
            "passed": self.ok(strict),
            "strict": strict,
            "errors": self.error_count(),
            "warnings": self.warning_count(),
            "checks": [
                {
                    "key": check.key,
                    "title": check.title,
                    "status": check.status,
                    "errors": check.errors,
                    "warnings": check.warnings,
                    "notes": check.notes,
                }
                for check in self.checks.values()
            ],
        }


def format_report(report: Report, strict: bool = False) -> str:
    lines = ["Validating skill: {}".format(report.skill_dir)]
    for number, check in enumerate(report.checks.values(), start=1):
        lines.append("  [{}] {}. {}".format(check.status, number, check.title))
        for message in check.errors:
            lines.append("         error: {}".format(message))
        for message in check.warnings:
            lines.append("         warning: {}".format(message))
        for message in check.notes:
            lines.append("         note: {}".format(message))
    verdict = "PASSED" if report.ok(strict) else "FAILED"
    lines.append("Result: {} ({} errors, {} warnings{}), {} files checked".format(
        verdict, report.error_count(), report.warning_count(), ", strict" if strict else "", report.files_checked))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    except (UnicodeDecodeError, OSError):
        return None


def validate_skill(skill_dir: Path) -> Report:
    """Run every check on a skill folder and return the report."""
    root = Path(skill_dir).resolve()
    checks = {key: CheckResult(key, title) for key, title in CHECKS}
    report = Report(skill_dir=root, checks=checks)
    structure, frontmatter_check, metadata, naming = (
        checks["structure"], checks["frontmatter"], checks["metadata"], checks["naming"])
    references, links, content, hygiene = (
        checks["references"], checks["links"], checks["content"], checks["hygiene"])

    if not root.is_dir():
        structure.errors.append("{} is not a directory".format(root))
        return report

    # -- walk the folder ------------------------------------------------------
    included: List[Path] = []
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_dirs = []
        for dirname in sorted(dirnames):
            dir_path = current_path / dirname
            rel_parts = dir_path.relative_to(root).parts
            if dir_path.is_symlink():
                hygiene.errors.append("{}: symbolic links are not allowed in a skill package".format(
                    _rel(dir_path, root)))
                continue
            verdict = classify_path(rel_parts, is_dir=True)
            if verdict:
                hygiene.warnings.append("{}: {} (excluded from packages; remove it from the skill folder)".format(
                    _rel(dir_path, root), verdict[1]))
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs
        for filename in sorted(filenames):
            file_path = current_path / filename
            rel_parts = file_path.relative_to(root).parts
            if file_path.is_symlink():
                hygiene.errors.append("{}: symbolic links are not allowed in a skill package".format(
                    _rel(file_path, root)))
                continue
            verdict = classify_path(rel_parts)
            if verdict and verdict[0] == "secret":
                hygiene.errors.append("{}: {}; secrets must never ship in a skill".format(
                    _rel(file_path, root), verdict[1]))
                continue
            if verdict:
                hygiene.warnings.append("{}: {} (excluded from packages; remove it from the skill folder)".format(
                    _rel(file_path, root), verdict[1]))
                continue
            included.append(file_path)
    report.files_checked = len(included)
    included_set = {path.resolve() for path in included}

    # -- SKILL.md and frontmatter ------------------------------------------
    entries = {entry.name for entry in root.iterdir()}
    skill_md = root / "SKILL.md"
    if "SKILL.md" not in entries:
        variants = [name for name in entries if name.lower() == "skill.md"]
        if variants:
            structure.errors.append("found {} but the file must be named exactly SKILL.md".format(variants[0]))
        else:
            structure.errors.append("SKILL.md is missing; every skill needs one at its top level")
        return report

    skill_text = _read_text(skill_md)
    if skill_text is None:
        content.errors.append("SKILL.md is not readable UTF-8 text")
        return report
    parsed = parse_frontmatter(skill_text)
    frontmatter_check.errors.extend(parsed.errors)
    frontmatter_check.warnings.extend(parsed.warnings)
    frontmatter_check.notes.extend(parsed.notes)
    data = parsed.data if isinstance(parsed.data, dict) else {}
    report.frontmatter = data

    # -- metadata -----------------------------------------------------------
    if data:
        unknown = [key for key in data if key not in ALLOWED_FIELDS]
        if unknown:
            metadata.errors.append("unknown frontmatter field(s): {}; allowed fields are {}".format(
                ", ".join(sorted(unknown)), ", ".join(ALLOWED_FIELDS)))
        for key in REQUIRED_FIELDS:
            value = data.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                metadata.errors.append("required field '{}' is missing or empty".format(key))
            elif not isinstance(value, str):
                metadata.errors.append("field '{}' must be a string".format(key))
        description = data.get("description")
        if isinstance(description, str) and description.strip():
            if len(description) > DESCRIPTION_MAX_CHARS:
                metadata.errors.append("description is {} characters; the limit is {}".format(
                    len(description), DESCRIPTION_MAX_CHARS))
            if XML_TAG_RE.search(description):
                metadata.errors.append("description must not contain XML or HTML tags")
            if len(description.strip()) < DESCRIPTION_MIN_USEFUL_CHARS:
                metadata.warnings.append("description is very short; say what the skill does and when to use it")
            if not WHEN_CUE_RE.search(description):
                metadata.warnings.append("description should say when to use the skill (for example 'Use when ...')")
            if FIRST_OR_SECOND_PERSON_RE.match(description):
                metadata.warnings.append("write the description in the third person ('Processes ...', not 'I can ...')")
        compatibility = data.get("compatibility")
        if compatibility is not None:
            if not isinstance(compatibility, str) or not compatibility.strip():
                metadata.errors.append("'compatibility' must be a non-empty string")
            elif len(compatibility) > COMPATIBILITY_MAX_CHARS:
                metadata.errors.append("'compatibility' is {} characters; the limit is {}".format(
                    len(compatibility), COMPATIBILITY_MAX_CHARS))
        license_value = data.get("license")
        if license_value is not None and (not isinstance(license_value, str) or not license_value.strip()):
            metadata.errors.append("'license' must be a non-empty string")
        tools = data.get("allowed-tools")
        if tools is not None:
            if isinstance(tools, list):
                metadata.warnings.append(
                    "the Agent Skills specification defines 'allowed-tools' as a space-delimited string")
                if not all(isinstance(item, str) for item in tools):
                    metadata.errors.append("'allowed-tools' entries must be strings")
            elif not isinstance(tools, str):
                metadata.errors.append("'allowed-tools' must be a space-delimited string")
        meta = data.get("metadata")
        if meta is not None:
            if not isinstance(meta, dict):
                metadata.errors.append("'metadata' must be a mapping of string keys to string values")
            else:
                for key, value in meta.items():
                    if not isinstance(value, str):
                        metadata.errors.append("metadata '{}' must be a string value (quote it)".format(key))

    # -- naming -------------------------------------------------------------
    name = data.get("name") if isinstance(data.get("name"), str) else None
    if name is not None:
        report.skill_name = name
        if len(name) > NAME_MAX_CHARS:
            naming.errors.append("name is {} characters; the limit is {}".format(len(name), NAME_MAX_CHARS))
        if not NAME_RE.match(name):
            naming.errors.append(
                "name {!r} must use lowercase letters, digits and single hyphens, and must not start or end "
                "with a hyphen".format(name))
        for word in RESERVED_NAME_WORDS:
            if word in name.lower():
                naming.errors.append("name must not contain the reserved word '{}'".format(word))
        if name != root.name:
            naming.errors.append("name {!r} must match the folder name {!r}".format(name, root.name))
    elif data:
        naming.errors.append("no valid 'name' to check")

    # -- layout -------------------------------------------------------------
    layout = LAYOUTS.get(name or "")
    if layout:
        structure.notes.append("applied the '{}' layout rules".format(name))
        for directory in layout["directories"]:
            dir_path = root / directory
            if not dir_path.is_dir():
                structure.errors.append("required folder '{}/' is missing".format(directory))
            elif not any(path.parent == dir_path.resolve() or _inside(path, dir_path.resolve())
                         for path in included_set):
                structure.errors.append("required folder '{}/' has no files".format(directory))
        for required in layout["files"]:
            if not (root / required).is_file():
                structure.errors.append("required file '{}' is missing".format(required))
        meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        for key in layout["metadata"]:
            if not meta.get(key):
                metadata.errors.append("this layout requires metadata '{}'".format(key))
        version = meta.get("version")
        if isinstance(version, str) and version and not SEMVER_RE.match(version):
            metadata.errors.append("metadata 'version' {!r} is not semantic versioning (MAJOR.MINOR.PATCH)".format(
                version))

    # -- content and Markdown scanning ---------------------------------------
    markdown: Dict[Path, MarkdownInfo] = {}
    for path in included:
        rel = _rel(path, root)
        try:
            size = path.stat().st_size
        except OSError as exc:
            content.errors.append("{}: cannot be read ({})".format(rel, exc))
            continue
        if size == 0:
            content.errors.append("{}: file is empty".format(rel))
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = _read_text(path)
        if text is None:
            content.errors.append("{}: not valid UTF-8 text".format(rel))
            continue
        if not text.strip():
            content.errors.append("{}: file contains only whitespace".format(rel))
            continue
        for number, line in enumerate(text.split("\n"), start=1):
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(line):
                    content.errors.append("{}:{}: placeholder text {!r}".format(rel, number, line.strip()[:60]))
                    break
        if path.suffix.lower() == ".py":
            try:
                compile(text, str(path), "exec")
            except SyntaxError as exc:
                content.errors.append("{}:{}: Python syntax error: {}".format(rel, exc.lineno, exc.msg))
        if path.suffix.lower() == ".md":
            info = scan_markdown(path.resolve(), text)
            markdown[path.resolve()] = info
            meaningful = [line for line in text.split("\n") if line.strip()]
            if len(meaningful) < MIN_MEANINGFUL_LINES:
                content.warnings.append("{}: only {} non-blank lines; is it a stub?".format(rel, len(meaningful)))
            if path.resolve() != skill_md.resolve() and info.line_count > TOC_THRESHOLD_LINES:
                has_contents = any(re.match(r"^(table of )?contents$", title.strip(), re.IGNORECASE)
                                   for _, level, title in info.headings if level in (2, 3))
                if not has_contents:
                    content.warnings.append("{}: {} lines without a 'Contents' section near the top".format(
                        rel, info.line_count))
    body_lines = parsed.body.rstrip("\n").split("\n") if parsed.body else []
    if len(body_lines) > SKILL_BODY_MAX_LINES:
        content.warnings.append("SKILL.md body has {} lines; keep it under {} and move detail into files".format(
            len(body_lines), SKILL_BODY_MAX_LINES))

    # -- links ----------------------------------------------------------------
    link_count = 0
    for md_path, info in sorted(markdown.items()):
        rel = _rel(md_path, root)
        for number, target in info.links:
            link_count += 1
            where = "{}:{}".format(rel, number)
            if not target:
                links.errors.append("{}: empty link target".format(where))
                continue
            if _SCHEME_RE.match(target) or target.startswith("//"):
                continue
            if "\\" in target:
                links.warnings.append("{}: use forward slashes in link {!r}".format(where, target))
            path_part, _, anchor = target.partition("#")
            path_part = unquote(path_part)
            destination = md_path if not path_part else (md_path.parent / path_part).resolve()
            if not _inside(destination, root):
                links.errors.append("{}: link {!r} points outside the skill folder, so it breaks once packaged".format(
                    where, target))
                continue
            if not destination.exists():
                links.errors.append("{}: link target {!r} does not exist".format(where, target))
                continue
            if anchor:
                if destination.suffix.lower() == ".md":
                    target_info = markdown.get(destination)
                    if target_info is None:
                        text = _read_text(destination) or ""
                        target_info = scan_markdown(destination, text)
                        markdown[destination] = target_info
                    if anchor not in target_info.anchors:
                        links.errors.append("{}: anchor '#{}' not found in {}".format(
                            where, anchor, _rel(destination, root)))
                else:
                    links.warnings.append("{}: cannot check anchor '#{}' in a non-Markdown file".format(where, anchor))
    links.notes.append("{} Markdown links checked in {} files".format(link_count, len(markdown)))

    # -- references -----------------------------------------------------------
    top_level_dirs = {entry.name for entry in root.iterdir() if entry.is_dir()}
    covered: Set[Path] = set()
    reference_count = 0
    for md_path, info in sorted(markdown.items()):
        rel = _rel(md_path, root)
        found: List[Tuple[int, str, str]] = []
        for number, ref in info.skill_dir_refs:
            found.append((number, ref.rstrip("."), "${CLAUDE_SKILL_DIR}/"))
        for number, code in info.code_spans:
            if "${CLAUDE_SKILL_DIR}" in code:
                continue
            for token in _path_tokens(code):
                if token.split("/", 1)[0] in top_level_dirs:
                    found.append((number, token, ""))
        for number, ref, prefix in found:
            reference_count += 1
            destination = (root / ref).resolve()
            if not _inside(destination, root) or not destination.exists():
                references.errors.append("{}:{}: referenced file '{}{}' does not exist".format(
                    rel, number, prefix, ref))
            elif md_path == skill_md.resolve():
                covered.add(destination)
        if md_path == skill_md.resolve():
            for _, target in info.links:
                if not target or _SCHEME_RE.match(target) or target.startswith("//"):
                    continue
                path_part = unquote(target.partition("#")[0])
                if not path_part:
                    continue
                destination = (md_path.parent / path_part).resolve()
                if destination.is_dir():
                    covered.update(p for p in included_set if _inside(p, destination))
                else:
                    covered.add(destination)
    references.notes.append("{} file references checked".format(reference_count))
    full_coverage = bool(layout and layout.get("full_coverage"))
    for path in sorted(included_set):
        if path == skill_md.resolve() or path in covered:
            continue
        message = "{}: not referenced from SKILL.md; Claude only finds files that SKILL.md points to".format(
            _rel(path, root))
        (references.errors if full_coverage else references.warnings).append(message)

    # -- hygiene: naming conventions and stray documentation ------------------
    strict_naming = bool(layout and layout.get("strict_naming"))
    for path in included:
        rel_parts = path.relative_to(root).parts
        for folder in rel_parts[:-1]:
            if not KEBAB_DIR_RE.match(folder):
                message = "{}: folder name '{}' is not lowercase kebab-case".format(_rel(path, root), folder)
                (hygiene.errors if strict_naming else hygiene.warnings).append(message)
                break
        filename = rel_parts[-1]
        if len(rel_parts) == 1 and filename == "SKILL.md":
            continue
        if filename in LICENSE_FILE_NAMES:
            continue
        if not KEBAB_FILE_RE.match(filename):
            message = "{}: file name is not lowercase kebab-case".format(_rel(path, root))
            (hygiene.errors if strict_naming else hygiene.warnings).append(message)
        if len(rel_parts) == 1 and filename.lower() in ("readme.md", "changelog.md"):
            hygiene.warnings.append(
                "{}: human-facing documentation belongs outside the skill folder".format(filename))

    return report


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate an Agent Skill folder (frontmatter, naming, references, links, content, hygiene).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 validate-skill.py                 validate the skill containing this script\n"
            "  python3 validate-skill.py path/to/skill   validate another skill\n"
            "  python3 validate-skill.py --strict --json treat warnings as failures; print JSON\n"
            "\nexit status: 0 passed, 1 problems found, 2 usage error"
        ),
    )
    parser.add_argument("skill_dir", nargs="?", default=str(DEFAULT_SKILL_DIR),
                        help="skill folder to validate (default: the skill containing this script)")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    skill_dir = Path(args.skill_dir).expanduser()
    if not skill_dir.exists():
        print("error: {} does not exist".format(skill_dir), file=sys.stderr)
        return 2
    if not skill_dir.is_dir():
        print("error: {} is not a directory".format(skill_dir), file=sys.stderr)
        return 2

    report = validate_skill(skill_dir)
    if args.json:
        print(json.dumps(report.to_dict(strict=args.strict), indent=2))
    else:
        print(format_report(report, strict=args.strict))
    return 0 if report.ok(strict=args.strict) else 1


if __name__ == "__main__":
    sys.exit(main())
