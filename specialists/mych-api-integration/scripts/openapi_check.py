#!/usr/bin/env python3
"""Check API usage against an OpenAPI 3 description, so code never relies on invented endpoints.

Usage:
  python3 openapi_check.py endpoints SPEC [--json]          list operations (method, path, operationId, auth)
  python3 openapi_check.py verify SPEC --uses FILE           check "METHOD /path" lines used by a client
  python3 openapi_check.py diff OLD_SPEC NEW_SPEC            report breaking changes between two versions

SPEC is JSON, or YAML when PyYAML is installed. Paths in --uses may contain
concrete values (/users/42) or templates (/users/{id}); both match /users/{userId}.
Exit status: 0 OK, 1 problems found, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def load_spec(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise SystemExit("error: {} is YAML; install PyYAML or convert it to JSON".format(path)) from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict) or not str(data.get("openapi", "")).startswith("3"):
        raise SystemExit("error: {} is not an OpenAPI 3 document".format(path))
    return data


def operations(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    found = []
    global_security = spec.get("security")
    for path, item in (spec.get("paths") or {}).items():
        shared = item.get("parameters", []) if isinstance(item, dict) else []
        for method in METHODS:
            op = item.get(method) if isinstance(item, dict) else None
            if not isinstance(op, dict):
                continue
            params = shared + op.get("parameters", [])
            required = sorted(p.get("name") for p in params if isinstance(p, dict) and p.get("required"))
            body = op.get("requestBody") or {}
            security = op.get("security", global_security)
            found.append({"method": method.upper(), "path": path, "operationId": op.get("operationId"),
                          "summary": op.get("summary"), "required_parameters": required,
                          "body_required": bool(body.get("required")),
                          "auth": [list(s) for s in security] if security else [],
                          "responses": sorted(str(code) for code in (op.get("responses") or {}))})
    return found


def path_regex(template: str) -> "re.Pattern[str]":
    parts = re.split(r"(\{[^}]+\})", template.rstrip("/") or "/")
    pattern = "".join("[^/]+" if part.startswith("{") else re.escape(part) for part in parts)
    return re.compile("^" + pattern + "/?$")


def normalize_use(path: str) -> str:
    path = path.split("?", 1)[0]
    return re.sub(r"\{[^}]+\}", "x", path)


def verify_uses(spec: Dict[str, Any], uses: List[Tuple[str, str]]) -> List[str]:
    ops = operations(spec)
    problems = []
    for method, path in uses:
        candidate = normalize_use(path)
        matches = [op for op in ops if path_regex(op["path"]).match(candidate)]
        if not matches:
            problems.append("{} {}: no such path in the API description".format(method, path))
        elif not any(op["method"] == method for op in matches):
            allowed = ", ".join(sorted({op["method"] for op in matches}))
            problems.append("{} {}: path exists but method {} is not documented (documented: {})".format(
                method, path, method, allowed))
    return problems


def parse_uses(text: str) -> List[Tuple[str, str]]:
    uses = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2 or parts[0].upper() not in [m.upper() for m in METHODS]:
            raise SystemExit("error: line {}: expected 'METHOD /path', got {!r}".format(number, line))
        uses.append((parts[0].upper(), parts[1]))
    return uses


def diff(old: Dict[str, Any], new: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    breaking, additions = [], []
    old_ops = {(o["method"], o["path"]): o for o in operations(old)}
    new_ops = {(o["method"], o["path"]): o for o in operations(new)}
    for key, op in old_ops.items():
        if key not in new_ops:
            breaking.append("removed operation {} {}".format(*key))
            continue
        newer = new_ops[key]
        added_required = sorted(set(newer["required_parameters"]) - set(op["required_parameters"]))
        if added_required:
            breaking.append("{} {}: new required parameters {}".format(key[0], key[1], ", ".join(added_required)))
        if newer["body_required"] and not op["body_required"]:
            breaking.append("{} {}: request body became required".format(*key))
        removed_codes = sorted(set(op["responses"]) - set(newer["responses"]))
        if removed_codes:
            breaking.append("{} {}: responses removed {}".format(key[0], key[1], ", ".join(removed_codes)))
    for key in new_ops:
        if key not in old_ops:
            additions.append("added operation {} {}".format(*key))
    return breaking, additions


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check API usage against OpenAPI descriptions.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    p = sub.add_parser("endpoints")
    p.add_argument("spec")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("verify")
    p.add_argument("spec")
    p.add_argument("--uses", required=True, help="file with one 'METHOD /path' per line")
    p = sub.add_parser("diff")
    p.add_argument("old")
    p.add_argument("new")
    args = parser.parse_args(argv)
    try:
        if args.command == "endpoints":
            ops = operations(load_spec(Path(args.spec)))
            if args.json:
                print(json.dumps(ops, indent=2))
            else:
                for op in ops:
                    print("{:<7} {:<40} {}{}".format(op["method"], op["path"], op["operationId"] or "",
                                                     "  [auth]" if op["auth"] else ""))
                print("{} operations".format(len(ops)))
            return 0
        if args.command == "verify":
            spec = load_spec(Path(args.spec))
            uses = parse_uses(Path(args.uses).read_text(encoding="utf-8"))
            problems = verify_uses(spec, uses)
            for item in problems:
                print("error: " + item)
            print("{} of {} used endpoints are documented".format(len(uses) - len(problems), len(uses)))
            return 1 if problems else 0
        breaking, additions = diff(load_spec(Path(args.old)), load_spec(Path(args.new)))
        for item in breaking:
            print("breaking: " + item)
        for item in additions:
            print("added: " + item)
        print("{} breaking changes, {} additions".format(len(breaking), len(additions)))
        return 1 if breaking else 0
    except (OSError, ValueError) as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
