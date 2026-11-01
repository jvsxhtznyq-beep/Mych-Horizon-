#!/usr/bin/env python3
"""Inventory what this environment can actually do, without changing anything.

Reports the platform, commands on PATH, Python modules (located, not
imported), GPUs, credential variables that are set (names only, never
values), installed skills, MCP server names from known host configuration
files, host hints, optional network reachability, and how ready each
MYCH-HORIZON domain specialist is here.

Usage:
  python3 detect-capabilities.py [--json] [--deep] [--network] [--root DIR]

  --json     machine-readable output
  --deep     also run version commands and list global npm packages
  --network  probe a few public hosts over HTTPS (read-only requests)
  --root     project folder to inspect for project-level skills and MCP
             configuration (default: current directory)

Only names are reported for credentials, skills and MCP servers; values,
arguments and environment blocks are never printed. Every probe has a short
timeout. Exit status: 0 success, 2 usage error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

PROBE_TIMEOUT = 5

COMMANDS = {
    "core": ["python3", "python", "pip", "pip3", "uv", "git", "make", "curl", "wget", "sqlite3"],
    "javascript": ["node", "npm", "npx", "pnpm", "yarn", "bun", "deno", "tsc"],
    "compiled": ["gcc", "clang", "cmake", "go", "cargo", "rustc", "java", "dotnet"],
    "containers_cloud": ["docker", "podman", "kubectl", "helm", "terraform", "tofu", "pulumi", "aws", "gcloud",
                         "az", "flyctl", "vercel", "netlify", "wrangler", "runpodctl"],
    "repositories": ["gh", "glab"],
    "media": ["ffmpeg", "ffprobe", "convert", "magick", "inkscape", "optipng", "pngquant"],
    "graphics_3d": ["blender", "aseprite", "libresprite", "gltf-validator", "gltf-transform"],
    "models": ["ollama", "llama-server", "llama-cli", "vllm", "lms"],
    "gpu": ["nvidia-smi", "rocm-smi"],
    "browsers": ["chromium", "chromium-browser", "google-chrome", "firefox"],
}

PYTHON_MODULES = ["PIL", "numpy", "yaml", "requests", "httpx", "pytest", "playwright", "torch", "diffusers",
                  "transformers", "cv2", "onnxruntime", "trimesh", "pygltflib", "bpy", "openai", "anthropic",
                  "google.genai", "runpod", "discord", "fastapi", "flask"]

# Names of credential variables reported as set or not set. Values are never read out.
CREDENTIAL_VARIABLES = {
    "model_providers": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "ZHIPUAI_API_KEY",
                        "ZAI_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY", "TOGETHER_API_KEY", "OPENROUTER_API_KEY",
                        "DEEPSEEK_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"],
    "model_endpoints": ["ANTHROPIC_BASE_URL", "OPENAI_BASE_URL", "OLLAMA_HOST"],
    "image_generation": ["STABILITY_API_KEY", "REPLICATE_API_TOKEN", "FAL_KEY", "BFL_API_KEY"],
    "cloud": ["AWS_ACCESS_KEY_ID", "AWS_PROFILE", "GOOGLE_APPLICATION_CREDENTIALS", "AZURE_CLIENT_ID",
              "CLOUDFLARE_API_TOKEN", "DIGITALOCEAN_ACCESS_TOKEN", "FLY_API_TOKEN", "VERCEL_TOKEN"],
    "gpu_cloud": ["RUNPOD_API_KEY"],
    "repositories": ["GITHUB_TOKEN", "GH_TOKEN", "GITLAB_TOKEN"],
    "chat_platforms": ["DISCORD_TOKEN", "DISCORD_BOT_TOKEN", "SLACK_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"],
}
CREDENTIAL_LIKE = re.compile(r"(?:_API_KEY|_TOKEN|_SECRET|_SECRET_KEY|_PASSWORD)$")

HOST_HINTS = {
    "CLAUDECODE": "Claude Code", "CLAUDE_CODE_ENTRYPOINT": "Claude Code", "CODEX_HOME": "Codex CLI",
    "CODEX_SANDBOX": "Codex CLI", "GEMINI_CLI": "Gemini CLI", "CURSOR_TRACE_ID": "Cursor",
    "GITHUB_ACTIONS": "GitHub Actions", "CI": "a CI system", "CODESPACES": "GitHub Codespaces",
}

SKILL_LOCATIONS = [".claude/skills", ".agents/skills", ".github/skills", ".gemini/skills", ".codex/skills",
                   ".cursor/skills", ".opencode/skills"]

NETWORK_TARGETS = {
    "pypi": "https://pypi.org/simple/pip/", "npm": "https://registry.npmjs.org/-/ping",
    "github": "https://github.com/", "huggingface": "https://huggingface.co/",
}

# What each domain specialist needs. Kept in sync with registry/specialists.json
# in the MYCH-HORIZON repository by its tests.
SPECIALIST_NEEDS: Dict[str, Dict[str, Any]] = {
    "mych-pixel-art": {"required": ["python3"], "optional": ["aseprite|libresprite", "module:PIL", "convert|magick"],
                       "live": None},
    "mych-image-generation": {"required": ["python3"], "optional": ["module:PIL"],
                              "live": "a generation backend: GPU with module:torch and module:diffusers, a local "
                                      "ComfyUI server, or an image API credential"},
    "mych-3d-design": {"required": ["python3"], "optional": ["blender", "gltf-validator", "gpu"],
                       "live": "Blender for modeling and rendering"},
    "mych-chatbot-engineering": {"required": ["python3"], "optional": ["node"],
                                 "live": "a model credential or a local model runtime"},
    "mych-api-integration": {"required": ["python3"], "optional": ["curl"], "live": "network access to the API"},
    "mych-emoji-language": {"required": ["python3"], "optional": ["module:PIL"], "live": None},
    "mych-cloud-infrastructure": {"required": ["python3"],
                                  "optional": ["docker|podman", "terraform|tofu", "kubectl", "aws|gcloud|az"],
                                  "live": "cloud credentials and the owner's approval for spending or deploying"},
    "mych-runpod": {"required": ["python3"], "optional": ["runpodctl"],
                    "live": "RUNPOD_API_KEY and the owner's approval for spending"},
}


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def run_quiet(command: Sequence[str], timeout: int = PROBE_TIMEOUT) -> Optional[str]:
    """Run a read-only command; return its first output line, or None."""
    try:
        result = subprocess.run(list(command), capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or result.stderr or "").strip()
    first = text.splitlines()[0].strip() if text else ""
    return first if len(first) <= 80 else first[:77] + "..."


def memory_total_gb() -> Optional[float]:
    try:
        with open("/proc/meminfo", encoding="ascii") as stream:
            for line in stream:
                if line.startswith("MemTotal:"):
                    return round(int(line.split()[1]) / 1024 / 1024, 1)
    except (OSError, ValueError, IndexError):
        pass
    if sys.platform == "darwin":
        value = run_quiet(["sysctl", "-n", "hw.memsize"])
        if value and value.isdigit():
            return round(int(value) / 1024 ** 3, 1)
    return None


def container_hints() -> List[str]:
    hints = []
    if Path("/.dockerenv").exists():
        hints.append("/.dockerenv present")
    if Path("/run/.containerenv").exists():
        hints.append("/run/.containerenv present")
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="replace")
        if any(word in cgroup for word in ("docker", "kubepods", "containerd", "lxc")):
            hints.append("container cgroup")
    except OSError:
        pass
    return hints


def platform_info(root: Path) -> Dict[str, Any]:
    try:
        usage = shutil.disk_usage(str(root))
        disk_free = round(usage.free / 1024 ** 3, 1)
    except OSError:
        disk_free = None
    return {
        "os": platform.system(), "release": platform.release(), "machine": platform.machine(),
        "python": platform.python_version(), "cpu_count": os.cpu_count(), "memory_total_gb": memory_total_gb(),
        "disk_free_gb": disk_free, "container_hints": container_hints(),
    }


def find_commands() -> Dict[str, Dict[str, Optional[str]]]:
    return {group: {name: shutil.which(name) for name in names} for group, names in COMMANDS.items()}


def command_versions(found: Dict[str, Dict[str, Optional[str]]], deep: bool) -> Dict[str, Optional[str]]:
    wanted = ["python3", "node", "git"]
    if deep:
        wanted = [name for names in found.values() for name, path in names.items() if path]
    versions = {}
    for name in wanted:
        path = next((names[name] for names in found.values() if name in names), None)
        if path:
            flag = "version" if name in ("go",) else "--version"
            versions[name] = run_quiet([path, flag])
    return versions


def find_modules() -> Dict[str, bool]:
    found = {}
    for name in PYTHON_MODULES:
        try:
            found[name] = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError, AttributeError):
            found[name] = False
    return found


def gpu_info(found: Dict[str, Dict[str, Optional[str]]]) -> Dict[str, Any]:
    info: Dict[str, Any] = {"devices": [], "notes": []}
    nvidia = found["gpu"].get("nvidia-smi")
    if nvidia:
        try:
            result = subprocess.run([nvidia, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True, timeout=PROBE_TIMEOUT)
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    parts = [part.strip() for part in line.split(",")]
                    if len(parts) == 2:
                        memory = int(parts[1]) if parts[1].isdigit() else None
                        info["devices"].append({"vendor": "NVIDIA", "name": parts[0],
                                                "memory_gb": round(memory / 1024, 1) if memory else None})
            else:
                info["notes"].append("nvidia-smi is installed but reported no usable GPU")
        except (OSError, subprocess.SubprocessError):
            info["notes"].append("nvidia-smi did not answer within {}s".format(PROBE_TIMEOUT))
    if found["gpu"].get("rocm-smi"):
        info["notes"].append("rocm-smi is installed (AMD GPU tooling); not queried")
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        info["notes"].append("Apple silicon: an integrated GPU with unified memory is likely; not queried")
    if not info["devices"] and not info["notes"]:
        info["notes"].append("no GPU tooling found")
    return info


def credentials() -> Dict[str, Any]:
    report: Dict[str, Any] = {group: {name: bool(os.environ.get(name)) for name in names}
                              for group, names in CREDENTIAL_VARIABLES.items()}
    known = {name for names in CREDENTIAL_VARIABLES.values() for name in names}
    report["other_credential_like_variables"] = sum(
        1 for name, value in os.environ.items() if value and name not in known and CREDENTIAL_LIKE.search(name))
    return report


def host_hints() -> List[str]:
    seen: List[str] = []
    for variable, host in HOST_HINTS.items():
        if os.environ.get(variable) and host not in seen:
            seen.append(host)
    term = os.environ.get("TERM_PROGRAM", "")
    if term == "vscode" and "VS Code or a fork of it" not in seen:
        seen.append("VS Code or a fork of it")
    return seen


def installed_skills(root: Path) -> Dict[str, List[str]]:
    found: Dict[str, List[str]] = {}
    bases = [(root, "project"), (Path.home(), "user")]
    for base, scope in bases:
        for location in SKILL_LOCATIONS:
            folder = base / location
            if not folder.is_dir():
                continue
            names = sorted(child.name for child in folder.iterdir() if (child / "SKILL.md").is_file())
            if names:
                found["{} {}".format(scope, location)] = names
    return found


def _json_keys(path: Path, *keys: str) -> List[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    names: List[str] = []
    for key in keys:
        block = data.get(key) if isinstance(data, dict) else None
        if isinstance(block, dict):
            names.extend(str(name) for name in block)
    if isinstance(data, dict) and isinstance(data.get("projects"), dict):
        for project in data["projects"].values():
            if isinstance(project, dict) and isinstance(project.get("mcpServers"), dict):
                names.extend(str(name) for name in project["mcpServers"])
    return sorted(set(names))


def mcp_servers(root: Path) -> Dict[str, List[str]]:
    home = Path.home()
    json_files = [
        (root / ".mcp.json", ("mcpServers",)), (root / ".vscode" / "mcp.json", ("servers", "mcpServers")),
        (root / ".cursor" / "mcp.json", ("mcpServers",)), (root / ".gemini" / "settings.json", ("mcpServers",)),
        (home / ".claude.json", ("mcpServers",)), (home / ".cursor" / "mcp.json", ("mcpServers",)),
        (home / ".gemini" / "settings.json", ("mcpServers",)),
        (home / ".codeium" / "windsurf" / "mcp_config.json", ("mcpServers",)),
    ]
    found: Dict[str, List[str]] = {}
    for path, keys in json_files:
        if path.is_file():
            names = _json_keys(path, *keys)
            if names:
                found[str(path).replace(str(home), "~", 1)] = names
    codex = home / ".codex" / "config.toml"
    if codex.is_file():
        try:
            names = sorted(set(re.findall(r"^\[mcp_servers\.([A-Za-z0-9_-]+)\]", codex.read_text(encoding="utf-8"),
                                          re.M)))
        except OSError:
            names = []
        if names:
            found["~/.codex/config.toml"] = names
    return found


def network_probe() -> Dict[str, str]:
    results = {}
    for name, url in NETWORK_TARGETS.items():
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "mych-detect-capabilities"})
        try:
            with urllib.request.urlopen(request, timeout=PROBE_TIMEOUT) as response:
                results[name] = "reachable (HTTP {})".format(response.status)
        except urllib.error.HTTPError as exc:
            results[name] = "reachable (HTTP {})".format(exc.code)
        except urllib.error.URLError as exc:
            reason = exc.reason
            results[name] = "unreachable ({})".format(type(reason).__name__ if not isinstance(reason, str) else reason)
        except OSError as exc:
            results[name] = "unreachable ({})".format(type(exc).__name__)
    return results


def npm_globals() -> List[str]:
    root = run_quiet(["npm", "root", "-g"], timeout=10)
    if not root:
        return []
    folder = Path(root)
    if not folder.is_dir():
        return []
    names = []
    for child in sorted(folder.iterdir()):
        if child.name.startswith("@") and child.is_dir():
            names.extend("{}/{}".format(child.name, sub.name) for sub in sorted(child.iterdir()))
        elif not child.name.startswith("."):
            names.append(child.name)
    return names


# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------

def has(requirement: str, commands: Dict[str, Dict[str, Optional[str]]], modules: Dict[str, bool],
        gpu: Dict[str, Any]) -> bool:
    for option in requirement.split("|"):
        if option.startswith("module:"):
            if modules.get(option[len("module:"):]):
                return True
        elif option == "gpu":
            if gpu["devices"]:
                return True
        elif any(names.get(option) for names in commands.values()) or (option == "python3" and sys.executable):
            return True
    return False


def image_generation_backend(commands, modules, gpu, creds) -> Optional[str]:
    if gpu["devices"] and modules.get("torch") and modules.get("diffusers"):
        return "local diffusers on {}".format(gpu["devices"][0]["name"])
    for name, label in (("OPENAI_API_KEY", "OpenAI image API"), ("GEMINI_API_KEY", "Gemini image API"),
                        ("GOOGLE_API_KEY", "Google image API"), ("STABILITY_API_KEY", "Stability API"),
                        ("REPLICATE_API_TOKEN", "Replicate"), ("FAL_KEY", "fal"), ("BFL_API_KEY", "BFL API")):
        for group in creds.values():
            if isinstance(group, dict) and group.get(name):
                return "{} (credential set; reachability not tested)".format(label)
    return None


def readiness(commands, modules, gpu, creds) -> Dict[str, Dict[str, Any]]:
    report = {}
    any_model = any(creds["model_providers"].values()) or any(commands["models"].values())
    for name, needs in SPECIALIST_NEEDS.items():
        missing = [req for req in needs["required"] if not has(req, commands, modules, gpu)]
        optional = {req: has(req, commands, modules, gpu) for req in needs["optional"]}
        live_ok: Optional[bool] = None
        live_detail = needs["live"]
        if name == "mych-image-generation":
            backend = image_generation_backend(commands, modules, gpu, creds)
            live_ok = backend is not None
            live_detail = backend or "no backend found: generation is unavailable; processing and planning still work"
        elif name == "mych-chatbot-engineering":
            live_ok = any_model
            if live_ok:
                live_detail = "model credential variable or local runtime present (not tested)"
        elif name == "mych-runpod":
            live_ok = creds["gpu_cloud"]["RUNPOD_API_KEY"]
            if live_ok:
                live_detail = "RUNPOD_API_KEY set (not tested); spending still needs the owner's approval"
        elif name == "mych-3d-design":
            live_ok = bool(commands["graphics_3d"].get("blender"))
        elif name == "mych-cloud-infrastructure":
            live_ok = any(creds["cloud"].values())
            if live_ok:
                live_detail = "cloud credential variable set (not tested); deploying or spending still needs the " \
                              "owner's approval"
        if missing:
            level = "unavailable"
        elif live_ok is False:
            level = "partial"
        else:
            level = "ready"
        report[name] = {"level": level, "missing": missing, "optional": optional,
                        "live_capability": live_detail, "live_available": live_ok}
    return report


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def collect(root: Path, deep: bool, network: bool) -> Dict[str, Any]:
    commands = find_commands()
    modules = find_modules()
    gpu = gpu_info(commands)
    creds = credentials()
    report: Dict[str, Any] = {
        "schema": "mych-capabilities/1", "root": str(root), "platform": platform_info(root),
        "commands": commands, "versions": command_versions(commands, deep), "python_modules": modules, "gpu": gpu,
        "credentials": creds, "host_hints": host_hints(), "skills": installed_skills(root),
        "mcp_servers": mcp_servers(root), "network": network_probe() if network else "not probed (use --network)",
        "readiness": readiness(commands, modules, gpu, creds),
    }
    if deep:
        report["npm_global_packages"] = npm_globals()
    return report


def render_markdown(report: Dict[str, Any]) -> str:
    plat = report["platform"]
    lines = ["# Capability report", "",
             "- Platform: {} {} ({}), Python {}, {} CPUs, {} GB RAM, {} GB free disk{}".format(
                 plat["os"], plat["release"], plat["machine"], plat["python"], plat["cpu_count"],
                 plat["memory_total_gb"] if plat["memory_total_gb"] is not None else "?",
                 plat["disk_free_gb"] if plat["disk_free_gb"] is not None else "?",
                 "; container: " + ", ".join(plat["container_hints"]) if plat["container_hints"] else ""),
             "- Host hints: {}".format(", ".join(report["host_hints"]) or "none detected")]
    gpu = report["gpu"]
    if gpu["devices"]:
        lines.append("- GPU: " + "; ".join("{} {} ({} GB)".format(d["vendor"], d["name"], d["memory_gb"])
                                           for d in gpu["devices"]))
    else:
        lines.append("- GPU: none detected ({})".format("; ".join(gpu["notes"])))
    lines += ["", "## Commands on PATH", ""]
    for group, names in report["commands"].items():
        present = [name for name, path in names.items() if path]
        missing = [name for name, path in names.items() if not path]
        lines.append("- {}: {}{}".format(group.replace("_", " "), ", ".join(present) or "none",
                                         " (missing: {})".format(", ".join(missing)) if missing else ""))
    if report["versions"]:
        lines.append("- versions: " + "; ".join("{} {}".format(k, v) for k, v in report["versions"].items() if v))
    modules = report["python_modules"]
    lines += ["", "## Python modules (located, not imported)", "",
              "- present: " + (", ".join(name for name, ok in modules.items() if ok) or "none"),
              "- missing: " + (", ".join(name for name, ok in modules.items() if not ok) or "none")]
    lines += ["", "## Credentials (names only; values are never read out)", ""]
    for group, names in report["credentials"].items():
        if isinstance(names, dict):
            set_names = [name for name, ok in names.items() if ok]
            lines.append("- {}: {}".format(group.replace("_", " "), ", ".join(set_names) or "none set"))
    lines.append("- other credential-like variables set: {}".format(
        report["credentials"]["other_credential_like_variables"]))
    lines += ["", "## Skills and MCP servers (names only)", ""]
    for location, names in report["skills"].items():
        lines.append("- skills in {}: {}".format(location, ", ".join(names)))
    if not report["skills"]:
        lines.append("- no skill folders found in known locations")
    for location, names in report["mcp_servers"].items():
        lines.append("- MCP servers in {}: {}".format(location, ", ".join(names)))
    if not report["mcp_servers"]:
        lines.append("- no MCP server configuration found in known files (hosts may provide servers another way)")
    lines += ["", "## Network", ""]
    if isinstance(report["network"], dict):
        lines += ["- {}: {}".format(name, status) for name, status in report["network"].items()]
    else:
        lines.append("- " + report["network"])
    if report.get("npm_global_packages") is not None:
        lines.append("- global npm packages: " + (", ".join(report["npm_global_packages"]) or "none"))
    lines += ["", "## Specialist readiness", "", "| Specialist | Level | Live capability | Missing optional tools |",
              "|---|---|---|---|"]
    for name, item in report["readiness"].items():
        live = item["live_capability"] or "not needed"
        if item["live_available"] is True:
            live = "available: " + live
        elif item["live_available"] is False:
            live = "unavailable: " + live
        missing_optional = [req for req, ok in item["optional"].items() if not ok]
        lines.append("| {} | {} | {} | {} |".format(name, item["level"], live.replace("|", "/"),
                                                     ", ".join(missing_optional).replace("|", " or ") or "none"))
    lines += ["", "Levels: ready = tools and live capability present; partial = planning and offline tools work, "
              "live capability missing; unavailable = required tools missing."]
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inventory this environment's capabilities without changing anything.")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--deep", action="store_true", help="run version commands and list global npm packages")
    parser.add_argument("--network", action="store_true", help="probe a few public hosts over HTTPS")
    parser.add_argument("--root", default=".", help="project folder to inspect (default: current directory)")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print("error: {} is not a directory".format(root), file=sys.stderr)
        return 2
    report = collect(root, args.deep, args.network)
    print(json.dumps(report, indent=2) if args.json else render_markdown(report).rstrip("\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
