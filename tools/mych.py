#!/usr/bin/env python3
"""MYCH-HORIZON command-line tool.

The core skill and the domain specialists say WHAT to do. This tool handles
HOW they reach a particular model or host:

  route         suggest tier, disciplines, workflow and specialists for a task
  bundle        build a single system prompt plus translated tool definitions
                for a model that cannot load skills itself
  export        copy skills into a host's skills folder, rewriting the
                ${CLAUDE_SKILL_DIR} placeholder for hosts that do not expand it
  tools-schema  print the neutral tool definitions in a provider's format
  run-tool      execute one neutral tool call (argument lists, no shell),
                confined to a workspace folder
  harness       run an agent loop against a model API with the bundle and tools
  validate-all  validate the core skill and every built specialist
  package-all   build verified ZIP archives of all built skills
  registry-check  check that registries, skills, scripts and tests agree

Every command supports --help. Standard library only; Python 3.8 or newer.
Exit status: 0 success, 1 failed check or refused action, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parent.parent
CORE = REPO / "mych-plugin"
REGISTRY = REPO / "registry"
SKILL_DIR_PLACEHOLDER = "${CLAUDE_SKILL_DIR}"
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
# Schema keywords every provider format accepts. Tool parameters must stay within them.
PORTABLE_SCHEMA_KEYS = frozenset({"type", "description", "enum", "properties", "required", "items", "minimum",
                                  "maximum", "minItems", "maxItems", "minLength", "maxLength"})
OUTPUT_LIMIT = 20000
TOOL_TIMEOUT = 120
TOOL_FORMATS = ("openai", "anthropic", "gemini", "openai-compatible")


class MychError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_json(name: str) -> Dict[str, Any]:
    path = REGISTRY / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MychError("cannot read {}: {}".format(path, exc), code=2) from exc


def load_module(path: Path, name: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise MychError("cannot load {}".format(path), code=2)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def validator() -> Any:
    return load_module(CORE / "scripts" / "validate-skill.py", "mych_validate_skill")


def packager() -> Any:
    return load_module(CORE / "scripts" / "package-skill.py", "mych_package_skill")


def specialists_registry() -> List[Dict[str, Any]]:
    return load_json("specialists.json")["specialists"]


def skill_dirs(include_planned: bool = False) -> Dict[str, Path]:
    """Skill name -> folder, for the core and every specialist that exists."""
    found = {"mych-plugin": CORE}
    for spec in specialists_registry():
        path = REPO / spec["path"]
        if (path / "SKILL.md").is_file() and (include_planned or spec.get("status") != "planned"):
            found[spec["id"]] = path
    return found


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip("\n")
    return text


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _words(text: str) -> str:
    return " ".join(text.lower().replace("-", " ").replace("_", " ").split())


def phrase_in(text: str, phrase: str) -> bool:
    """Whole-word, case-insensitive match; hyphens count as spaces (pixel-art matches pixel art)."""
    return re.search(r"(?<![a-z0-9])" + re.escape(_words(phrase)) + r"(?![a-z0-9])", _words(text)) is not None


def route(task: str) -> Dict[str, Any]:
    text = " ".join(task.lower().split())
    workflows = load_json("workflows.json")
    specialists = []
    for spec in specialists_registry():
        hits = [trigger for trigger in spec["triggers"] if phrase_in(text, trigger)]
        avoided = [phrase for phrase in spec.get("avoid", []) if phrase_in(text, phrase)]
        if hits and len(hits) > len(avoided):
            specialists.append({"id": spec["id"], "matched": hits, "status": spec.get("status", "planned")})
    specialists.sort(key=lambda item: -len(item["matched"]))

    matched = [flow for flow in workflows["workflows"] if any(phrase_in(text, t) for t in flow["triggers"])]
    sensitive = next((flow for flow in matched if flow["id"] == "sensitive-change"), None)
    others = [flow for flow in matched if flow["id"] != "sensitive-change"]
    default = next(flow for flow in workflows["workflows"] if flow["id"] == "execution-lifecycle")
    primary = others[0] if others else (sensitive or default)
    also_follow = ["sensitive-change"] if sensitive and primary is not sensitive else []

    tiers = workflows["tiers"]
    tier = int(primary.get("min_tier", 2))
    change_words = ("build", "create", "make", "implement", "fix", "change", "add", "write", "deploy", "refactor",
                    "update", "remove", "delete", "migrate")
    asks_question = any(phrase_in(text, phrase) for phrase in tiers["tier0"])
    wants_change = any(phrase_in(text, word) for word in change_words)
    if asks_question and not wants_change:
        tier = 0
    elif any(phrase_in(text, phrase) for phrase in tiers["tier1"]) and not sensitive:
        tier = 1
    elif any(phrase_in(text, phrase) for phrase in tiers["tier3"]) or len(specialists) >= 3:
        tier = 3
    if sensitive:
        tier = max(tier, 2)

    signals = {name: [k for k in keywords if phrase_in(text, k)] for name, keywords in workflows["disciplines"].items()}
    lead = primary["lead"]
    disciplines = [lead]
    for name, hits in sorted(signals.items(), key=lambda item: -len(item[1])):
        if name != lead and hits and (tier >= 2 or len(hits) >= 2):
            disciplines.append(name)
    if primary["id"] == "new-software-project" and tier >= 3 and "Architect" not in disciplines:
        disciplines.append("Architect")
    order = ["Architect", "Researcher", "Designer", "Engineer", "Inventor"]
    disciplines = sorted(set(disciplines), key=order.index)
    workflow = {"id": primary["id"], "file": primary["file"]}
    if primary.get("template"):
        workflow["template"] = primary["template"]
    if tier == 0 and primary["id"] in ("execution-lifecycle", "technical-research"):
        # Tier 0: answer directly (Discovery, Verification, Delivery); research questions keep their workflow.
        if primary["id"] == "execution-lifecycle":
            workflow = {"id": "direct-answer", "file": "mych-plugin/SKILL.md"}
        lead, disciplines = "Researcher", ["Researcher"]
    return {
        "task": task, "tier": tier, "lead": lead, "disciplines": disciplines,
        "workflow": workflow,
        "also_follow": also_follow, "specialists": specialists, "signals": {k: v for k, v in signals.items() if v},
        "note": "Heuristic suggestion from keyword matching; confirm it with the orientation questions in SKILL.md.",
    }


def render_route(result: Dict[str, Any]) -> str:
    lines = ["Task: {}".format(result["task"]),
             "Tier: {}".format(result["tier"]),
             "Lead: {}; disciplines: {}".format(result["lead"], ", ".join(result["disciplines"])),
             "Workflow: {} ({})".format(result["workflow"]["id"], result["workflow"]["file"])]
    if result["workflow"].get("template"):
        lines.append("Template: {}".format(result["workflow"]["template"]))
    if result["also_follow"]:
        lines.append("Also follow: {}".format(", ".join(result["also_follow"])))
    if result["specialists"]:
        for spec in result["specialists"]:
            lines.append("Specialist: {} (matched: {}){}".format(
                spec["id"], ", ".join(spec["matched"]), "" if spec["status"] != "planned" else " [not built yet]"))
    else:
        lines.append("Specialists: none")
    lines.append(result["note"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools: definitions, translation, execution
# ---------------------------------------------------------------------------

def all_tools(specialist_ids: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    tools = list(load_json("tools.json")["tools"])
    wanted = set(specialist_ids or [])
    for spec in specialists_registry():
        if spec["id"] in wanted:
            tools.extend(spec.get("tools", []))
    return tools


def find_tool(name: str) -> Tuple[Dict[str, Any], Optional[str]]:
    for tool in load_json("tools.json")["tools"]:
        if tool["name"] == name:
            return tool, None
    for spec in specialists_registry():
        for tool in spec.get("tools", []):
            if tool["name"] == name:
                return tool, spec["id"]
    raise MychError("unknown tool '{}'".format(name))


def gemini_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only keywords in the OpenAPI subset that Gemini function declarations accept."""
    kept: Dict[str, Any] = {}
    for key, value in schema.items():
        if key not in PORTABLE_SCHEMA_KEYS:
            continue
        if key == "properties":
            kept[key] = {name: gemini_schema(sub) for name, sub in value.items()}
        elif key == "items":
            kept[key] = gemini_schema(value)
        else:
            kept[key] = value
    if kept.get("required") == []:
        del kept["required"]
    return kept


def translate(tools: List[Dict[str, Any]], fmt: str) -> Any:
    if fmt in ("openai", "openai-compatible"):
        return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                   "parameters": t["parameters"]}} for t in tools]
    if fmt == "anthropic":
        return [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
    if fmt == "gemini":
        declarations = []
        for tool in tools:
            declaration = {"name": tool["name"], "description": tool["description"]}
            params = gemini_schema(tool["parameters"])
            if params.get("properties"):
                declaration["parameters"] = params
            declarations.append(declaration)
        return [{"functionDeclarations": declarations}]
    raise MychError("unknown tool format '{}' (choose from {})".format(fmt, ", ".join(TOOL_FORMATS)), code=2)


TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
}


def check_arguments(tool: Dict[str, Any], args: Dict[str, Any]) -> List[str]:
    """Validate call arguments against the tool's (portable) parameter schema."""
    schema = tool["parameters"]
    problems = []
    if not isinstance(args, dict):
        return ["arguments must be an object"]
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in args:
            problems.append("missing required argument '{}'".format(name))
    for name, value in args.items():
        if name not in properties:
            problems.append("unknown argument '{}'".format(name))
            continue
        spec = properties[name]
        expected = spec.get("type")
        if expected and not TYPE_CHECKS[expected](value):
            problems.append("argument '{}' must be of type {}".format(name, expected))
            continue
        if "enum" in spec and value not in spec["enum"]:
            problems.append("argument '{}' must be one of {}".format(name, ", ".join(map(str, spec["enum"]))))
        if expected == "array" and "items" in spec:
            item_type = spec["items"].get("type")
            if item_type and not all(TYPE_CHECKS[item_type](item) for item in value):
                problems.append("every item of '{}' must be of type {}".format(name, item_type))
        if expected in ("integer", "number") and "minimum" in spec and value < spec["minimum"]:
            problems.append("argument '{}' must be at least {}".format(name, spec["minimum"]))
    return problems


def resolve_inside(workspace: Path, value: str) -> Path:
    candidate = (workspace / value).resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError as exc:
        raise MychError("path '{}' is outside the workspace {}".format(value, workspace)) from exc
    return candidate


def build_command(tool: Dict[str, Any], args: Dict[str, Any], workspace: Path) -> List[str]:
    dirs = skill_dirs(include_planned=True)
    command: List[str] = []
    for token in tool["command"]:
        if isinstance(token, str):
            command.append(sys.executable if token == "{python}" else token)
        elif "skill" in token:
            base = dirs.get(token["skill"])
            if base is None:
                raise MychError("tool '{}' needs skill '{}', which is not available".format(tool["name"], token["skill"]))
            command.append(str(base / token["path"]))
        elif "repo" in token:
            command.append(str(REPO / token["repo"]))
        elif "flag" in token:
            if args.get(token["when"]) is True:
                command.append(token["flag"])
        elif "option" in token:
            value = args.get(token["param"])
            if value is not None:
                command += [token["option"], str(value)]
        elif "param" in token:
            if token["param"] in args:
                command.append(str(args[token["param"]]))
        elif "spread" in token:
            command += [str(item) for item in args.get(token["spread"], [])]
        else:
            raise MychError("tool '{}' has an unknown command token {}".format(tool["name"], token), code=2)
    return command


def run_tool(name: str, args: Dict[str, Any], workspace: Path, timeout: int = TOOL_TIMEOUT,
             approved: bool = False) -> Dict[str, Any]:
    """Execute a neutral tool call. Paths stay inside the workspace; no shell is involved.

    Tools marked requires_approval run only when the caller passes approved=True,
    which a person must decide; the harness never sets it on a model's behalf.
    """
    tool, _ = find_tool(name)
    problems = check_arguments(tool, args)
    if problems:
        return {"tool": name, "ok": False, "error": "; ".join(problems)}
    dry = args.get("dry_run") is True
    if tool.get("requires_approval") and not approved and not dry:
        return {"tool": name, "ok": False, "needs_approval": tool["requires_approval"],
                "error": "this tool needs the owner's approval ({}); ask them, or call it with dry_run".format(
                    tool["requires_approval"])}
    workspace = workspace.resolve()
    for key in tool.get("path_params", ["path", "file"]):
        if isinstance(args.get(key), str):
            resolve_inside(workspace, args[key])
    for forbidden in tool.get("forbidden_arguments", []):
        for item in args.get("arguments", []) or []:
            if str(item) == forbidden or str(item).startswith(forbidden + "="):
                return {"tool": name, "ok": False, "error": "argument '{}' is not allowed here".format(forbidden)}
    command = build_command(tool, args, workspace)
    try:
        result = subprocess.run(command, cwd=str(workspace), capture_output=True, text=True, timeout=timeout,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    except subprocess.TimeoutExpired:
        return {"tool": name, "ok": False, "error": "timed out after {}s".format(timeout)}
    except OSError as exc:
        return {"tool": name, "ok": False, "error": "could not start: {}".format(exc)}

    def clip(text: str) -> str:
        return text if len(text) <= OUTPUT_LIMIT else text[:OUTPUT_LIMIT] + "\n[output truncated]"

    return {"tool": name, "ok": result.returncode == 0, "exit_code": result.returncode,
            "stdout": clip(result.stdout), "stderr": clip(result.stderr)}


# ---------------------------------------------------------------------------
# Bundles for models without native skill loading
# ---------------------------------------------------------------------------

BUNDLE_HEADER = """# MYCH-HORIZON bundle

You are operating under the MYCH-HORIZON framework. Your host does not load skill folders, so the framework
is inlined below. Files mentioned by path are available only if your host gives you file or shell tools; the
references this task needs most are inlined in this prompt. Paths such as `mych-plugin/scripts/...` are
relative to the MYCH-HORIZON workspace. The tools listed in the accompanying tool definitions run those
scripts for you; when a tool is not offered, do not claim to have run it.
"""


def find_provider(provider_id: str) -> Dict[str, Any]:
    for provider in load_json("providers.json")["providers"]:
        if provider["id"] == provider_id:
            return provider
    known = ", ".join(p["id"] for p in load_json("providers.json")["providers"])
    raise MychError("unknown provider '{}' (known: {})".format(provider_id, known), code=2)


def approx_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def bundle(provider_id: str, specialist_ids: Optional[List[str]], task: Optional[str], out_dir: Path,
           max_tokens: int, includes: Sequence[str]) -> Dict[str, Any]:
    provider = find_provider(provider_id)
    dirs = skill_dirs()
    chosen = list(specialist_ids or [])
    route_result = route(task) if task else None
    if route_result and specialist_ids is None:
        chosen = [item["id"] for item in route_result["specialists"] if item["id"] in dirs]
    missing = [name for name in chosen if name not in dirs]
    if missing:
        raise MychError("specialists not built or unknown: {}".format(", ".join(missing)))
    sections: List[Tuple[str, str]] = []

    def add_file(label: str, path: Path, placeholder_path: str) -> None:
        text = strip_frontmatter(path.read_text(encoding="utf-8"))
        sections.append((label, text.replace(SKILL_DIR_PLACEHOLDER, placeholder_path)))

    add_file("mych-plugin/SKILL.md", CORE / "SKILL.md", "mych-plugin")
    extra = list(includes)
    if route_result:
        extra.insert(0, route_result["workflow"]["file"])
        if route_result["workflow"].get("template"):
            extra.insert(1, route_result["workflow"]["template"])
    seen = set()
    for rel in extra:
        if rel in seen:
            continue
        seen.add(rel)
        path = resolve_inside(REPO, rel)
        if not path.is_file():
            raise MychError("include '{}' does not exist".format(rel), code=2)
        add_file(rel, path, "mych-plugin")
    for name in chosen:
        add_file("{}/SKILL.md".format(dirs[name].relative_to(REPO).as_posix()), dirs[name] / "SKILL.md",
                 dirs[name].relative_to(REPO).as_posix())
    prompt = BUNDLE_HEADER
    if route_result:
        prompt += "\nSuggested routing for the current task (heuristic): tier {}, lead {}, workflow {}.\n".format(
            route_result["tier"], route_result["lead"], route_result["workflow"]["id"])
    for label, text in sections:
        prompt += "\n\n<!-- begin {} -->\n\n{}\n<!-- end {} -->\n".format(label, text.rstrip(), label)
    tools = translate(all_tools(chosen), provider["tool_format"])
    tokens = approx_tokens(prompt) + approx_tokens(json.dumps(tools))
    manifest = {
        "schema": "mych-bundle/1", "provider": provider["id"], "api_style": provider["api_style"],
        "tool_format": provider["tool_format"], "specialists": chosen,
        "files": [{"path": label, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()} for label, text in sections],
        "approx_tokens": tokens, "token_estimate_method": "characters / 4 (approximate; providers tokenize differently)",
        "tools": [t["name"] for t in all_tools(chosen)],
        "route": route_result,
    }
    if tokens > max_tokens:
        sizes = ", ".join("{} ~{}".format(label, approx_tokens(text)) for label, text in sections)
        raise MychError("bundle needs ~{} tokens, over the limit of {} ({}); drop includes or specialists, or raise "
                        "--max-tokens if the model's context allows it".format(tokens, max_tokens, sizes))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "system-prompt.md").write_text(prompt, encoding="utf-8")
    (out_dir / "tools.json").write_text(json.dumps(tools, indent=2) + "\n", encoding="utf-8")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


# ---------------------------------------------------------------------------
# Export to agent hosts
# ---------------------------------------------------------------------------

def find_host(host_id: str) -> Dict[str, Any]:
    for host in load_json("providers.json")["hosts"]:
        if host["id"] == host_id:
            return host
    known = ", ".join(h["id"] for h in load_json("providers.json")["hosts"])
    raise MychError("unknown host '{}' (known: {})".format(host_id, known), code=2)


def export(host_id: str, project: Optional[Path], target: Optional[Path], skill_names: Optional[List[str]],
           dry_run: bool, force: bool, keep_placeholders: bool) -> List[str]:
    host = find_host(host_id)
    dirs = skill_dirs()
    names = skill_names or list(dirs)
    unknown = [name for name in names if name not in dirs]
    if unknown:
        raise MychError("skills not built or unknown: {}".format(", ".join(unknown)), code=2)
    if target is None:
        if project is None:
            raise MychError("pass --project DIR (uses the host's project skills folder) or --target DIR", code=2)
        if not host["project_paths"]:
            raise MychError("no documented project skills folder for host '{}'; pass --target".format(host_id), code=2)
        base = project / host["project_paths"][0]
        rewrite_base = host["project_paths"][0]
    else:
        base = target
        rewrite_base = str(target.expanduser().resolve())
    actions = []
    collect = packager().collect_files
    check = validator()
    for name in names:
        destination = base / name
        if destination.exists() and not force:
            raise MychError("{} already exists; pass --force to replace it (this overwrites files)".format(destination))
        files, _ = collect(dirs[name], check)
        actions.append("copy {} files: {} -> {}".format(len(files), dirs[name].relative_to(REPO), destination))
        rewrite = not host.get("substitutes_skill_dir") and not keep_placeholders
        if rewrite:
            actions.append("rewrite {} -> {}/{} in Markdown files".format(SKILL_DIR_PLACEHOLDER, rewrite_base, name))
        if dry_run:
            continue
        if destination.exists():
            shutil.rmtree(str(destination))
        for rel, source in files:
            out = destination / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            if rewrite and source.suffix == ".md":
                text = source.read_text(encoding="utf-8")
                out.write_text(text.replace(SKILL_DIR_PLACEHOLDER, "{}/{}".format(rewrite_base, name)), encoding="utf-8")
            else:
                shutil.copyfile(str(source), str(out))
            os.chmod(str(out), packager().file_mode(rel))  # same modes as the release archives
    note = "evidence for host '{}': {} ({})".format(host_id, host["evidence"], host["evidence_note"])
    actions.append(note)
    return actions


# ---------------------------------------------------------------------------
# Validation, packaging and registry checks
# ---------------------------------------------------------------------------

def validate_all(strict: bool) -> Tuple[bool, List[Dict[str, Any]]]:
    check = validator()
    results = []
    ok = True
    for name, path in skill_dirs().items():
        report = check.validate_skill(path)
        passed = report.ok(strict)
        ok = ok and passed
        results.append({"skill": name, "path": str(path.relative_to(REPO)), "ok": passed,
                        "errors": report.error_count(), "warnings": report.warning_count(),
                        "report": check.format_report(report, strict)})
    return ok, results


def package_all(out_dir: Path, strict: bool) -> Tuple[bool, List[Dict[str, Any]]]:
    results = []
    ok = True
    for name, path in skill_dirs().items():
        status, result = packager().package(path, out_dir, validate=True, strict=strict)
        ok = ok and status == 0
        results.append({"skill": name, "status": status, "archive": result.get("archive"),
                        "sha256": (result.get("facts") or {}).get("sha256"), "error": result.get("error")})
    return ok, results


def schema_problems(schema: Any, where: str) -> List[str]:
    problems = []
    if not isinstance(schema, dict):
        return ["{}: schema must be an object".format(where)]
    for key, value in schema.items():
        if key not in PORTABLE_SCHEMA_KEYS:
            problems.append("{}: keyword '{}' is not portable across providers".format(where, key))
        if key == "properties":
            for name, sub in value.items():
                problems += schema_problems(sub, "{}.{}".format(where, name))
        if key == "items":
            problems += schema_problems(value, where + "[]")
    return problems


def registry_check() -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    check = validator()
    detector = load_module(CORE / "scripts" / "detect-capabilities.py", "mych_detect_capabilities")
    specs = specialists_registry()
    seen = set()
    for spec in specs:
        sid = spec["id"]
        if sid in seen:
            errors.append("specialists.json: duplicate id {}".format(sid))
        seen.add(sid)
        if not spec.get("triggers"):
            errors.append("{}: no triggers".format(sid))
        needs = detector.SPECIALIST_NEEDS.get(sid)
        if needs is None:
            errors.append("{}: missing from detect-capabilities.py SPECIALIST_NEEDS".format(sid))
        elif needs["required"] != spec["requires"] or needs["optional"] != spec["optional"]:
            errors.append("{}: requires/optional differ between specialists.json and detect-capabilities.py".format(sid))
        path = REPO / spec["path"]
        if spec.get("status") == "planned":
            if (path / "SKILL.md").exists():
                warnings.append("{}: skill exists but is still marked planned".format(sid))
            continue
        if not (path / "SKILL.md").is_file():
            errors.append("{}: status {} but {} has no SKILL.md".format(sid, spec["status"], spec["path"]))
            continue
        parsed = check.parse_frontmatter((path / "SKILL.md").read_text(encoding="utf-8"))
        data = parsed.data or {}
        if data.get("name") != sid:
            errors.append("{}: SKILL.md name is {!r}".format(sid, data.get("name")))
        version = (data.get("metadata") or {}).get("version")
        if version != spec["version"]:
            errors.append("{}: registry version {} but SKILL.md metadata version {}".format(sid, spec["version"], version))
        for script in spec.get("scripts", []):
            if not (path / script["path"]).is_file():
                errors.append("{}: listed script {} is missing".format(sid, script["path"]))
        for test in spec.get("tests", []):
            if not (REPO / test).is_file():
                errors.append("{}: listed test {} is missing".format(sid, test))
        if spec["status"] in ("tested", "verified") and not spec.get("tests"):
            errors.append("{}: status {} requires listed tests".format(sid, spec["status"]))
    for flow in load_json("workflows.json")["workflows"]:
        for key in ("file", "template"):
            if flow.get(key) and not (REPO / flow[key]).is_file():
                errors.append("workflows.json: {} file {} is missing".format(flow["id"], flow[key]))
    names = set()
    for tool in all_tools([spec["id"] for spec in specs]):
        name = tool.get("name", "")
        if not TOOL_NAME_RE.match(name):
            errors.append("tool {!r}: name must match {}".format(name, TOOL_NAME_RE.pattern))
        if name in names:
            errors.append("tool {}: duplicate name".format(name))
        names.add(name)
        if len(tool.get("description", "")) < 20:
            errors.append("tool {}: description too short".format(name))
        errors += schema_problems(tool.get("parameters"), "tool {} parameters".format(name))
        params = set((tool.get("parameters") or {}).get("properties", {}))
        for token in tool.get("command", []):
            if isinstance(token, dict):
                for key in ("param", "when", "spread"):
                    if key in token and token[key] not in params:
                        errors.append("tool {}: command uses undefined parameter '{}'".format(name, token[key]))
                if "skill" in token:
                    base = skill_dirs(include_planned=True).get(token["skill"])
                    if base and not (base / token["path"]).is_file():
                        errors.append("tool {}: {} is missing in {}".format(name, token["path"], token["skill"]))
                if "repo" in token and not (REPO / token["repo"]).is_file():
                    errors.append("tool {}: {} is missing".format(name, token["repo"]))
    providers = load_json("providers.json")
    for provider in providers["providers"]:
        for key in ("id", "api_style", "endpoint", "auth", "tool_format", "evidence"):
            if key not in provider:
                errors.append("provider {}: missing {}".format(provider.get("id"), key))
        if provider.get("tool_format") not in TOOL_FORMATS:
            errors.append("provider {}: unknown tool format".format(provider.get("id")))
        for value in provider.get("evidence", {}).values():
            if value.split(" ")[0] not in providers["evidence_levels"]:
                errors.append("provider {}: unknown evidence level {!r}".format(provider.get("id"), value))
        for source in provider.get("sources", []):
            if not source.startswith("https://"):
                errors.append("provider {}: source {} is not an https URL".format(provider.get("id"), source))
    for host in providers["hosts"]:
        if host.get("evidence") not in providers["evidence_levels"]:
            errors.append("host {}: unknown evidence level".format(host.get("id")))
        if host.get("evidence") != "unknown" and not host.get("sources"):
            errors.append("host {}: evidence without sources".format(host.get("id")))
    integrations = REGISTRY / "integrations.json"
    if integrations.exists():
        try:
            data = json.loads(integrations.read_text(encoding="utf-8"))
            for item in data.get("integrations", []):
                for key in ("id", "kind", "url", "evidence", "specialists", "trust", "status"):
                    if key not in item:
                        errors.append("integrations.json: {} missing {}".format(item.get("id"), key))
        except ValueError as exc:
            errors.append("integrations.json: invalid JSON ({})".format(exc))
    return errors, warnings


# ---------------------------------------------------------------------------
# Harness (agent loop against a model API)
# ---------------------------------------------------------------------------

def harness(args: argparse.Namespace) -> int:
    chatkit_path = REPO / "specialists" / "mych-chatbot-engineering" / "scripts" / "chatkit.py"
    if not chatkit_path.is_file():
        raise MychError("the harness needs specialists/mych-chatbot-engineering/scripts/chatkit.py", code=2)
    chatkit = load_module(chatkit_path, "mych_chatkit")
    provider = find_provider(args.provider)
    out = Path(args.bundle_dir) if args.bundle_dir else REPO / "build" / "harness-bundle"
    manifest = bundle(provider["id"], args.specialists.split(",") if args.specialists else None, args.task, out,
                      args.max_tokens, [])
    system_prompt = (out / "system-prompt.md").read_text(encoding="utf-8")
    neutral_tools = all_tools(manifest["specialists"])
    workspace = Path(args.workspace).resolve()

    def execute(name: str, call_args: Dict[str, Any]) -> str:
        return json.dumps(run_tool(name, call_args, workspace))

    tools = [chatkit.Tool(t["name"], t["description"], t["parameters"], lambda a, n=t["name"]: execute(n, a))
             for t in neutral_tools]
    model = chatkit.adapter_for(provider, model=args.model, base_url=args.base_url, api_key_env=args.api_key_env,
                                dry_run=args.dry_run)
    agent = chatkit.Agent(model=model, system=system_prompt, tools=tools, max_steps=args.max_steps)
    result = agent.run(args.task)
    print(json.dumps({"provider": provider["id"], "model": args.model, "dry_run": args.dry_run,
                      "final": result.final_text, "steps": result.steps, "tool_calls": result.tool_calls,
                      "stopped": result.stop_reason}, indent=2))
    return 0 if result.stop_reason in ("final", "dry-run") else 1


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MYCH-HORIZON: route, bundle, export, validate and package skills.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p = sub.add_parser("route", help="suggest tier, disciplines, workflow and specialists for a task")
    p.add_argument("task", nargs="+", help="task description")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("bundle", help="build a system prompt and tool definitions for a model without skill loading")
    p.add_argument("--provider", required=True, help="provider id from registry/providers.json")
    p.add_argument("--task", help="task description; picks the workflow and specialists to inline")
    p.add_argument("--specialists", help="comma-separated specialist ids (overrides routing)")
    p.add_argument("--include", action="append", default=[], help="extra repository file to inline (repeatable)")
    p.add_argument("--out", default="build/bundle", help="output folder (default: build/bundle)")
    p.add_argument("--max-tokens", type=int, default=60000, help="refuse bundles larger than this (default 60000)")

    p = sub.add_parser("export", help="copy skills into a host's skills folder")
    p.add_argument("--host", required=True, help="host id from registry/providers.json")
    p.add_argument("--project", help="project root; skills go to the host's project skills folder")
    p.add_argument("--target", help="explicit skills folder (for example ~/.agents/skills)")
    p.add_argument("--skills", help="comma-separated skill names (default: all built skills)")
    p.add_argument("--dry-run", action="store_true", help="show what would happen")
    p.add_argument("--force", action="store_true", help="replace existing skill folders (overwrites files)")
    p.add_argument("--keep-placeholders", action="store_true", help="do not rewrite ${CLAUDE_SKILL_DIR}")

    p = sub.add_parser("tools-schema", help="print tool definitions in a provider format")
    p.add_argument("--format", required=True, choices=TOOL_FORMATS)
    p.add_argument("--specialists", help="comma-separated specialist ids whose tools to include")

    p = sub.add_parser("run-tool", help="execute one neutral tool call inside a workspace")
    p.add_argument("name")
    p.add_argument("--args", default="{}", help="JSON object of arguments")
    p.add_argument("--workspace", default=".", help="folder the tool may read and write (default: current)")
    p.add_argument("--timeout", type=int, default=TOOL_TIMEOUT)
    p.add_argument("--approved", action="store_true",
                   help="the owner approved this call (needed for tools that spend money or change external state)")

    p = sub.add_parser("harness", help="run an agent loop against a model API (or --dry-run)")
    p.add_argument("--provider", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--base-url", help="override the provider endpoint base (for gateways, local servers or stubs)")
    p.add_argument("--api-key-env", help="environment variable holding the key (default: the provider's)")
    p.add_argument("--specialists", help="comma-separated specialist ids")
    p.add_argument("--workspace", default=".")
    p.add_argument("--bundle-dir", help="where to write the bundle (default: build/harness-bundle)")
    p.add_argument("--max-steps", type=int, default=8)
    p.add_argument("--max-tokens", type=int, default=60000)
    p.add_argument("--dry-run", action="store_true", help="build the first request and stop; sends nothing")

    p = sub.add_parser("validate-all", help="validate the core skill and every built specialist")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("package-all", help="build verified ZIP archives of all built skills")
    p.add_argument("--out", default="dist")
    p.add_argument("--strict", action="store_true")

    sub.add_parser("registry-check", help="check registries against skills, scripts and tests")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "route":
            result = route(" ".join(args.task))
            print(json.dumps(result, indent=2) if args.json else render_route(result))
            return 0
        if args.command == "bundle":
            manifest = bundle(args.provider, args.specialists.split(",") if args.specialists else None, args.task,
                              Path(args.out), args.max_tokens, args.include)
            print("Bundle for {} written to {} (~{} tokens; tools: {}; specialists: {})".format(
                manifest["provider"], args.out, manifest["approx_tokens"], ", ".join(manifest["tools"]),
                ", ".join(manifest["specialists"]) or "none"))
            return 0
        if args.command == "export":
            actions = export(args.host, Path(args.project) if args.project else None,
                             Path(args.target).expanduser() if args.target else None,
                             args.skills.split(",") if args.skills else None, args.dry_run, args.force,
                             args.keep_placeholders)
            print("\n".join(("[dry run] " if args.dry_run else "") + action for action in actions))
            return 0
        if args.command == "tools-schema":
            ids = args.specialists.split(",") if args.specialists else None
            print(json.dumps(translate(all_tools(ids), args.format), indent=2))
            return 0
        if args.command == "run-tool":
            try:
                call_args = json.loads(args.args)
            except ValueError as exc:
                raise MychError("--args is not valid JSON: {}".format(exc), code=2) from exc
            result = run_tool(args.name, call_args, Path(args.workspace), args.timeout, approved=args.approved)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        if args.command == "harness":
            return harness(args)
        if args.command == "validate-all":
            ok, results = validate_all(args.strict)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                for item in results:
                    print("{:<28} {}  ({} errors, {} warnings)".format(item["skill"], "PASS" if item["ok"] else "FAIL",
                                                                      item["errors"], item["warnings"]))
                    if not item["ok"]:
                        print(item["report"])
            return 0 if ok else 1
        if args.command == "package-all":
            ok, results = package_all(Path(args.out), args.strict)
            for item in results:
                print("{:<28} {}  {}".format(item["skill"], "OK  " if item["status"] == 0 else "FAIL",
                                             item["archive"] or item["error"]))
            return 0 if ok else 1
        if args.command == "registry-check":
            errors, warnings = registry_check()
            for item in errors:
                print("error: " + item)
            for item in warnings:
                print("warning: " + item)
            print("Registry check: {} ({} errors, {} warnings)".format("OK" if not errors else "PROBLEMS FOUND",
                                                                        len(errors), len(warnings)))
            return 1 if errors else 0
    except MychError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return exc.code
    return 2


if __name__ == "__main__":
    sys.exit(main())
