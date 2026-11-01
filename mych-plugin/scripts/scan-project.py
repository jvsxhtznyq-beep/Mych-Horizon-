#!/usr/bin/env python3
"""Summarize a project for the Discovery and Investigation phases. Read-only.

Reports languages, stack and framework signals, likely test, lint and build
commands, CI configuration, documentation and project-memory files (agent
instructions, decision records, task ledgers), environment templates, and
secret-bearing files, which are listed but never opened.

Usage:
  python3 scan-project.py [PROJECT_DIR] [--format markdown|json] [--max-files N]

PROJECT_DIR defaults to the current directory. The scan writes nothing and
never reads files that may hold secrets. Git details come from read-only
commands with optional locks and repository-configured fsmonitor hooks
disabled. Commands in the report are inferred from configuration and have
not been run. Exit status is 0 on success and 2 for usage errors.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:  # Python 3.11+
    import tomllib  # type: ignore
except ImportError:  # pragma: no cover - exercised on older interpreters
    tomllib = None

# Folders that hold dependencies, build output or caches rather than project
# source. Scanning them would drown the signal and slow large repositories.
SKIP_DIRS = frozenset({
    "node_modules", "bower_components", "vendor", "Pods", "venv", "env", "__pycache__", "site-packages",
    "dist", "build", "out", "target", "obj", "coverage", "htmlcov", "tmp", "temp",
})
# Hidden folders are skipped except these, which carry CI, agent or project-memory files.
KEEP_HIDDEN_DIRS = frozenset({".github", ".gitlab", ".circleci", ".buildkite", ".mych", ".claude", ".devcontainer",
                              ".husky", ".cursor"})
# Manifests above 1 MB are unusual; skip parsing rather than load huge files.
MAX_MANIFEST_BYTES = 1_000_000
# Upper bound on files examined, so scans of very large monorepos stay quick.
DEFAULT_MAX_FILES = 50_000
# Git commands normally answer in milliseconds; this guards against hangs.
GIT_TIMEOUT_SECONDS = 5

LANGUAGES = {
    ".py": "Python", ".pyi": "Python", ".ipynb": "Jupyter Notebook", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".jsx": "JavaScript (JSX)", ".ts": "TypeScript", ".tsx": "TypeScript (TSX)",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C++", ".c": "C", ".h": "C/C++ header",
    ".cc": "C++", ".cpp": "C++", ".cxx": "C++", ".hpp": "C++ header", ".cs": "C#", ".fs": "F#",
    ".rb": "Ruby", ".php": "PHP", ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang", ".hs": "Haskell",
    ".clj": "Clojure", ".dart": "Dart", ".lua": "Lua", ".r": "R", ".jl": "Julia", ".pl": "Perl",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ps1": "PowerShell", ".sql": "SQL",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "Sass", ".less": "Less", ".vue": "Vue",
    ".svelte": "Svelte", ".astro": "Astro", ".tf": "Terraform", ".proto": "Protocol Buffers",
    ".graphql": "GraphQL", ".gql": "GraphQL", ".sol": "Solidity", ".zig": "Zig", ".nim": "Nim",
}
DATA_FORMATS = {
    ".md": "Markdown", ".mdx": "MDX", ".rst": "reStructuredText", ".json": "JSON", ".yml": "YAML",
    ".yaml": "YAML", ".toml": "TOML", ".xml": "XML", ".csv": "CSV", ".ini": "INI",
}

SECRET_FILE_RE = re.compile(
    r"^(?:\.env(?:\.(?!example$|sample$|template$)[\w.-]+)?|id_(?:rsa|dsa|ecdsa|ed25519)|credentials\.json"
    r"|.+\.(?:pem|key|p12|pfx|keystore|jks)|\.npmrc|\.pypirc|\.netrc|secrets?\.(?:json|ya?ml|toml))$",
    re.IGNORECASE,
)
# Files that usually hold data rather than code: databases, dumps, backups and
# serialized datasets. They may contain personal or production data, so they
# are listed but never opened.
DATA_FILE_RE = re.compile(
    r"^.+\.(?:db|db3|sqlite|sqlite3|mdb|accdb|dump|bak|parquet|feather|h5|hdf5|pkl|pickle|xlsx|xls|npy|npz)$"
    r"|^.*(?:dump|backup).*\.sql(?:\.gz)?$",
    re.IGNORECASE,
)
ENV_TEMPLATE_RE = re.compile(r"^(?:\.env\.(?:example|sample|template)|env\.example|example\.env)$", re.IGNORECASE)
ENV_VAR_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")

NODE_FRAMEWORKS = {
    "next": "Next.js", "react": "React", "react-native": "React Native", "expo": "Expo", "vue": "Vue",
    "nuxt": "Nuxt", "svelte": "Svelte", "@sveltejs/kit": "SvelteKit", "@angular/core": "Angular",
    "solid-js": "Solid", "astro": "Astro", "@remix-run/react": "Remix", "express": "Express",
    "fastify": "Fastify", "koa": "Koa", "hono": "Hono", "@nestjs/core": "NestJS", "electron": "Electron",
    "vite": "Vite", "webpack": "webpack", "typescript": "TypeScript", "tailwindcss": "Tailwind CSS",
    "prisma": "Prisma", "@prisma/client": "Prisma", "drizzle-orm": "Drizzle ORM", "jest": "Jest",
    "vitest": "Vitest", "mocha": "Mocha", "@playwright/test": "Playwright", "cypress": "Cypress",
    "tap": "node-tap", "ava": "AVA", "uvu": "uvu", "phaser": "Phaser", "pixi.js": "PixiJS", "three": "three.js",
}
PYTHON_FRAMEWORKS = {
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI", "starlette": "Starlette", "pydantic": "Pydantic",
    "sqlalchemy": "SQLAlchemy", "celery": "Celery", "pytest": "pytest", "numpy": "NumPy", "pandas": "pandas",
    "torch": "PyTorch", "tensorflow": "TensorFlow", "scikit-learn": "scikit-learn", "streamlit": "Streamlit",
    "typer": "Typer", "click": "Click", "aiohttp": "aiohttp", "tornado": "Tornado",
}
NODE_SCRIPT_PURPOSES = (
    ("test", "test"), ("test:unit", "test"), ("test:e2e", "test"), ("e2e", "test"), ("lint", "quality"),
    ("typecheck", "quality"), ("type-check", "quality"), ("check", "quality"), ("format", "quality"),
    ("build", "build"), ("dev", "run"), ("start", "run"),
)
TOOLING_FILES = (
    (re.compile(r"^(?:\.eslintrc(?:\.\w+)?|eslint\.config\.\w+)$"), "ESLint"),
    (re.compile(r"^(?:\.prettierrc(?:\.\w+)?|prettier\.config\.\w+)$"), "Prettier"),
    (re.compile(r"^biome\.jsonc?$"), "Biome"),
    (re.compile(r"^tsconfig(?:\.[\w-]+)?\.json$"), "TypeScript compiler configuration"),
    (re.compile(r"^\.editorconfig$"), "EditorConfig"),
    (re.compile(r"^\.pre-commit-config\.ya?ml$"), "pre-commit hooks"),
    (re.compile(r"^\.?ruff\.toml$"), "Ruff"),
    (re.compile(r"^\.flake8$"), "Flake8"),
    (re.compile(r"^\.?mypy\.ini$"), "mypy"),
    (re.compile(r"^pyrightconfig\.json$"), "Pyright"),
    (re.compile(r"^\.?rustfmt\.toml$"), "rustfmt"),
    (re.compile(r"^clippy\.toml$"), "Clippy"),
    (re.compile(r"^\.golangci\.ya?ml$"), "golangci-lint"),
    (re.compile(r"^\.rubocop\.yml$"), "RuboCop"),
    (re.compile(r"^phpstan\.neon(?:\.dist)?$"), "PHPStan"),
    (re.compile(r"^\.stylelintrc(?:\.\w+)?$"), "Stylelint"),
    (re.compile(r"^lefthook\.ya?ml$"), "Lefthook"),
    (re.compile(r"^commitlint\.config\.\w+$"), "commitlint"),
    (re.compile(r"^renovate\.json5?$"), "Renovate"),
    (re.compile(r"^dependabot\.ya?ml$"), "Dependabot"),
)
DEPLOY_FILES = {
    "Dockerfile": "Container image (Dockerfile)", "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose", "compose.yml": "Docker Compose", "compose.yaml": "Docker Compose",
    "serverless.yml": "Serverless Framework", "vercel.json": "Vercel", "netlify.toml": "Netlify",
    "fly.toml": "Fly.io", "render.yaml": "Render", "Procfile": "Procfile-based platform", "app.yaml": "App Engine",
}
DECISION_DIR_NAMES = frozenset({"adr", "adrs", "decisions", "decision-records", "architecture-decisions"})
AGENT_INSTRUCTION_NAMES = frozenset({"CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "GEMINI.md", ".cursorrules",
                                     "copilot-instructions.md"})


def _read_small(path: Path) -> Optional[str]:
    try:
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    text = _read_small(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _load_toml(path: Path) -> Optional[Dict[str, Any]]:
    text = _read_small(path)
    if text is None or tomllib is None:
        return None
    try:
        return tomllib.loads(text)
    except (ValueError, TypeError):
        return None


def _requirement_name(spec: str) -> Optional[str]:
    match = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    return match.group(1).lower().replace("_", "-") if match else None


class Scanner:
    def __init__(self, root: Path, max_files: int = DEFAULT_MAX_FILES) -> None:
        self.root = root
        self.max_files = max_files
        self.files: List[str] = []
        self._file_set: set = set()
        self.skipped_dirs: List[str] = []
        self.truncated = False
        self.result: Dict[str, Any] = {
            "root": str(root), "files_scanned": 0, "truncated": False, "skipped_dirs": [],
            "git": {}, "languages": {}, "formats": {}, "stack": [], "commands": [], "tooling": [],
            "ci": [], "docs": [], "task_ledgers": [], "env_templates": [], "sensitive_files": [], "data_files": [],
            "notes": [],
        }

    # -- collection -------------------------------------------------------------

    def walk(self) -> None:
        skipped = set()
        for current, dirnames, filenames in os.walk(self.root, followlinks=False):
            current_path = Path(current)
            kept = []
            for dirname in sorted(dirnames):
                hidden = dirname.startswith(".") and dirname not in KEEP_HIDDEN_DIRS
                if dirname in SKIP_DIRS or hidden or dirname.endswith(".egg-info"):
                    skipped.add(dirname)
                elif not (current_path / dirname).is_symlink():
                    kept.append(dirname)
            dirnames[:] = kept
            rel_dir = current_path.relative_to(self.root).as_posix()
            for filename in sorted(filenames):
                self.files.append(filename if rel_dir == "." else "{}/{}".format(rel_dir, filename))
                if len(self.files) >= self.max_files:
                    self.truncated = True
                    break
            if self.truncated:
                break
        self.skipped_dirs = sorted(skipped)
        self.result.update({"files_scanned": len(self.files), "truncated": self.truncated,
                            "skipped_dirs": self.skipped_dirs})

    def exists(self, rel: str) -> bool:
        return rel in self._file_set

    def add_stack(self, signal: str, evidence: str) -> None:
        entry = {"signal": signal, "evidence": evidence}
        if entry not in self.result["stack"]:
            self.result["stack"].append(entry)

    def add_command(self, purpose: str, command: str, source: str) -> None:
        if not any(item["command"] == command for item in self.result["commands"]):
            self.result["commands"].append({"purpose": purpose, "command": command, "source": source})

    # -- analysis ---------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        self.walk()
        self._file_set = set(self.files)
        self.result["git"] = self.git_info()
        self.count_languages()
        self.detect_node()
        self.detect_python()
        self.detect_other_ecosystems()
        self.detect_make_and_just()
        self.detect_tooling_and_deploy()
        self.detect_ci()
        self.detect_docs()
        self.detect_env_and_secrets()
        self.result["notes"].append("Commands are inferred from project files and have not been run.")
        if self.truncated:
            self.result["notes"].append(
                "Stopped after {} files; pass --max-files to scan further.".format(self.max_files))
        return self.result

    def git_info(self) -> Dict[str, Any]:
        if shutil.which("git") is None:
            return {"available": False, "detail": "git is not installed"}
        env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", LC_ALL="C")
        base = ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-C", str(self.root)]

        def git(*args: str) -> Optional[str]:
            try:
                completed = subprocess.run(base + list(args), capture_output=True, text=True,
                                           timeout=GIT_TIMEOUT_SECONDS, env=env)
            except (OSError, subprocess.SubprocessError):
                return None
            return completed.stdout.strip() if completed.returncode == 0 else None

        if git("rev-parse", "--is-inside-work-tree") != "true":
            return {"available": True, "repository": False}
        info: Dict[str, Any] = {"available": True, "repository": True}
        info["toplevel"] = git("rev-parse", "--show-toplevel")
        info["branch"] = git("symbolic-ref", "--short", "HEAD") or git("rev-parse", "--short", "HEAD")
        status = git("status", "--porcelain")
        info["uncommitted_changes"] = len([line for line in (status or "").splitlines() if line.strip()])
        log = git("log", "-n", "5", "--date=short", "--format=%h %ad %s")
        info["recent_commits"] = log.splitlines() if log else []
        return info

    def count_languages(self) -> None:
        languages: Dict[str, int] = {}
        formats: Dict[str, int] = {}
        for rel in self.files:
            suffix = os.path.splitext(rel)[1].lower()
            if suffix in LANGUAGES:
                languages[LANGUAGES[suffix]] = languages.get(LANGUAGES[suffix], 0) + 1
            elif suffix in DATA_FORMATS:
                formats[DATA_FORMATS[suffix]] = formats.get(DATA_FORMATS[suffix], 0) + 1
        self.result["languages"] = dict(sorted(languages.items(), key=lambda item: (-item[1], item[0])))
        self.result["formats"] = dict(sorted(formats.items(), key=lambda item: (-item[1], item[0])))

    def detect_node(self) -> None:
        nested = [rel for rel in self.files if rel.endswith("/package.json")]
        if nested:
            self.result["notes"].append("{} nested package.json files (possible monorepo).".format(len(nested)))
        if not self.exists("package.json"):
            node_tests = [rel for rel in self.files if re.search(r"(?:^|/)[\w.-]+\.test\.(?:mjs|cjs|js)$", rel)]
            if node_tests:
                self.add_command("test", "node --test", "{} *.test.js files and no package.json (assumes the "
                                 "Node.js built-in runner; check the files' imports)".format(len(node_tests)))
            return
        data = _load_json(self.root / "package.json") or {}
        manager, lockfile = "npm", None
        for candidate, name in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lockb", "bun"),
                                ("bun.lock", "bun"), ("package-lock.json", "npm")):
            if self.exists(candidate):
                manager, lockfile = name, candidate
                break
        evidence = "package.json" + (", " + lockfile if lockfile else ", no lockfile found")
        self.add_stack("Node.js project ({})".format(manager), evidence)
        engines = data.get("engines") if isinstance(data.get("engines"), dict) else {}
        if isinstance(engines.get("node"), str):
            self.add_stack("Node.js version {}".format(engines["node"]), "package.json engines.node")
        if data.get("workspaces"):
            self.add_stack("Workspaces (monorepo)", "package.json workspaces")
        dependencies: Dict[str, Any] = {}
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            if isinstance(data.get(key), dict):
                dependencies.update(data[key])
        for package, label in NODE_FRAMEWORKS.items():
            if package in dependencies:
                self.add_stack(label, 'package.json dependency "{}"'.format(package))
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        for script, purpose in NODE_SCRIPT_PURPOSES:
            if script not in scripts:
                continue
            if manager == "npm":
                command = "npm test" if script == "test" else "npm start" if script == "start" else "npm run " + script
            elif manager == "bun":
                command = "bun run " + script
            else:
                command = "{} {}".format(manager, script)
            body = str(scripts[script])
            self.add_command(purpose, command, 'package.json scripts.{}: "{}"'.format(
                script, body if len(body) <= 80 else body[:77] + "..."))
            if purpose == "test" and re.search(r"\bnode\s+(?:[\w=-]+\s+)*--test\b", body):
                self.add_stack("Node.js built-in test runner", 'package.json scripts.{} uses "node --test"'.format(script))

    def detect_python(self) -> None:
        prefix = ""
        for lockfile, runner in (("uv.lock", "uv run "), ("poetry.lock", "poetry run "),
                                 ("Pipfile.lock", "pipenv run "), ("pdm.lock", "pdm run ")):
            if self.exists(lockfile):
                prefix = runner
                self.add_stack("Python dependencies managed with {}".format(runner.split()[0]), lockfile)
                break
        names: Dict[str, str] = {}
        tools: List[str] = []
        if self.exists("pyproject.toml"):
            data = _load_toml(self.root / "pyproject.toml")
            if data is None:
                text = _read_small(self.root / "pyproject.toml") or ""
                self.add_stack("Python project", "pyproject.toml")
                for section in re.findall(r"^\[tool\.([A-Za-z0-9_-]+)", text, flags=re.MULTILINE):
                    tools.append(section)
                for spec in re.findall(r"""["']([A-Za-z0-9][A-Za-z0-9._-]*)[^"']*["']""", text):
                    name = _requirement_name(spec)
                    if name:
                        names.setdefault(name, "pyproject.toml")
            else:
                project = data.get("project") if isinstance(data.get("project"), dict) else {}
                requires = project.get("requires-python")
                self.add_stack("Python project" + (" (requires-python {})".format(requires) if requires else ""),
                               "pyproject.toml")
                specs: List[str] = list(project.get("dependencies") or [])
                for group in (project.get("optional-dependencies") or {}).values():
                    specs.extend(group if isinstance(group, list) else [])
                for group in (data.get("dependency-groups") or {}).values():
                    specs.extend(item for item in (group if isinstance(group, list) else []) if isinstance(item, str))
                tool = data.get("tool") if isinstance(data.get("tool"), dict) else {}
                poetry = tool.get("poetry") if isinstance(tool.get("poetry"), dict) else {}
                for section in ("dependencies", "dev-dependencies"):
                    specs.extend((poetry.get(section) or {}).keys())
                for spec in specs:
                    name = _requirement_name(str(spec))
                    if name:
                        names.setdefault(name, "pyproject.toml")
                tools.extend(tool.keys())
                backend = (data.get("build-system") or {}).get("build-backend")
                if backend:
                    self.add_stack("Build backend {}".format(backend), "pyproject.toml build-system")
        requirement_files = [rel for rel in self.files
                             if re.match(r"^(?:requirements[\w.-]*\.txt|requirements/[\w.-]+\.txt)$", rel)]
        for rel in requirement_files:
            for line in (_read_small(self.root / rel) or "").splitlines():
                name = _requirement_name(line) if not line.strip().startswith(("#", "-")) else None
                if name:
                    names.setdefault(name, rel)
        if requirement_files and not self.exists("pyproject.toml"):
            self.add_stack("Python project (pip requirements)", ", ".join(requirement_files[:3]))
        for marker, label in (("setup.py", "setuptools (setup.py)"), ("setup.cfg", "setuptools (setup.cfg)"),
                              ("Pipfile", "Pipenv")):
            if self.exists(marker):
                self.add_stack("Python packaging: " + label, marker)
        for package, label in PYTHON_FRAMEWORKS.items():
            if package in names:
                self.add_stack(label, "{} lists {}".format(names[package], package))
        tool_labels = {"pytest": "pytest", "ruff": "Ruff", "black": "Black", "mypy": "mypy", "isort": "isort",
                       "coverage": "coverage.py", "poetry": "Poetry", "hatch": "Hatch", "pdm": "PDM", "uv": "uv",
                       "pyright": "Pyright"}
        for name in tools:
            if name in tool_labels:
                self.result["tooling"].append({"tool": tool_labels[name], "evidence": "pyproject.toml [tool.{}]".format(name)})
        has_pytest = ("pytest" in tools or "pytest" in names or self.exists("pytest.ini") or self.exists("conftest.py")
                      or any(rel.endswith("/conftest.py") for rel in self.files))
        test_files = [rel for rel in self.files if re.search(r"(?:^|/)(?:test_[\w-]+|[\w-]+_test)\.py$", rel)]
        if has_pytest:
            self.add_command("test", prefix + "pytest", "pytest configuration or dependency found")
        elif test_files:
            self.add_command("test", prefix + unittest_command(test_files),
                             "{} test files, no pytest configuration found".format(len(test_files)))
        if "ruff" in tools or self.exists("ruff.toml") or self.exists(".ruff.toml"):
            self.add_command("quality", prefix + "ruff check .", "Ruff configuration")
        if "black" in tools:
            self.add_command("quality", prefix + "black --check .", "pyproject.toml [tool.black]")
        if "mypy" in tools or self.exists("mypy.ini"):
            self.add_command("quality", prefix + "mypy .", "mypy configuration")
        if self.exists("tox.ini"):
            self.add_command("test", "tox", "tox.ini")
        if self.exists("noxfile.py"):
            self.add_command("test", "nox", "noxfile.py")

    def detect_other_ecosystems(self) -> None:
        if self.exists("Cargo.toml"):
            self.add_stack("Rust (Cargo)", "Cargo.toml")
            for command, purpose in (("cargo test", "test"), ("cargo clippy", "quality"),
                                     ("cargo fmt --check", "quality"), ("cargo build", "build")):
                self.add_command(purpose, command, "Cargo.toml")
        if self.exists("go.mod"):
            text = _read_small(self.root / "go.mod") or ""
            module = re.search(r"^module\s+(\S+)", text, flags=re.MULTILINE)
            version = re.search(r"^go\s+(\S+)", text, flags=re.MULTILINE)
            self.add_stack("Go module {}{}".format(module.group(1) if module else "",
                                                   " (go {})".format(version.group(1)) if version else ""), "go.mod")
            for command, purpose in (("go test ./...", "test"), ("go vet ./...", "quality"), ("go build ./...", "build")):
                self.add_command(purpose, command, "go.mod")
        if self.exists("pom.xml"):
            self.add_stack("Java or Kotlin (Maven)", "pom.xml")
            self.add_command("test", "mvn test", "pom.xml")
        gradle = [name for name in ("build.gradle", "build.gradle.kts") if self.exists(name)]
        if gradle:
            self.add_stack("Java or Kotlin (Gradle)", gradle[0])
            wrapper = "./gradlew" if self.exists("gradlew") else "gradle"
            self.add_command("test", wrapper + " test", gradle[0])
        if self.exists("Gemfile"):
            text = _read_small(self.root / "Gemfile") or ""
            self.add_stack("Ruby (Bundler)", "Gemfile")
            rails = re.search(r"""gem\s+["']rails["']""", text) is not None
            if rails:
                self.add_stack("Rails", "Gemfile")
            if re.search(r"""gem\s+["']rspec""", text) or any(rel.startswith("spec/") for rel in self.files):
                self.add_command("test", "bundle exec rspec", "RSpec in Gemfile or spec/ folder")
            elif any(rel.startswith("test/") for rel in self.files):
                self.add_command("test", "bin/rails test" if rails else "bundle exec rake test", "test/ folder")
        if self.exists("composer.json"):
            data = _load_json(self.root / "composer.json") or {}
            self.add_stack("PHP (Composer)", "composer.json")
            required = {}
            for key in ("require", "require-dev"):
                if isinstance(data.get(key), dict):
                    required.update(data[key])
            if "laravel/framework" in required:
                self.add_stack("Laravel", "composer.json")
            if any(name.startswith("symfony/") for name in required):
                self.add_stack("Symfony components", "composer.json")
            scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
            if "test" in scripts:
                self.add_command("test", "composer test", "composer.json scripts.test")
            elif "phpunit/phpunit" in required:
                self.add_command("test", "vendor/bin/phpunit", "composer.json requires phpunit")
        dotnet = [rel for rel in self.files if rel.endswith((".sln", ".csproj", ".fsproj"))]
        if dotnet:
            self.add_stack(".NET", dotnet[0])
            self.add_command("test", "dotnet test", dotnet[0])
        if self.exists("mix.exs"):
            text = _read_small(self.root / "mix.exs") or ""
            self.add_stack("Elixir (Mix)", "mix.exs")
            if ":phoenix" in text:
                self.add_stack("Phoenix", "mix.exs")
            self.add_command("test", "mix test", "mix.exs")
        if self.exists("pubspec.yaml"):
            text = _read_small(self.root / "pubspec.yaml") or ""
            flutter = re.search(r"^\s*flutter:", text, flags=re.MULTILINE) is not None
            self.add_stack("Flutter" if flutter else "Dart", "pubspec.yaml")
            self.add_command("test", "flutter test" if flutter else "dart test", "pubspec.yaml")
        if self.exists("Package.swift"):
            self.add_stack("Swift Package Manager", "Package.swift")
            self.add_command("test", "swift test", "Package.swift")
        if self.exists("CMakeLists.txt"):
            self.add_stack("C or C++ (CMake)", "CMakeLists.txt")
            self.add_command("build", "cmake -S . -B build && cmake --build build", "CMakeLists.txt")
            self.add_command("test", "ctest --test-dir build", "CMakeLists.txt")
        if self.exists("meson.build"):
            self.add_stack("Meson build", "meson.build")
        for name in ("deno.json", "deno.jsonc"):
            if self.exists(name):
                self.add_stack("Deno", name)
                self.add_command("test", "deno test", name)

    def detect_make_and_just(self) -> None:
        for makefile in ("Makefile", "makefile", "GNUmakefile"):
            if not self.exists(makefile):
                continue
            text = _read_small(self.root / makefile) or ""
            targets = re.findall(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)\s*:(?![:=])", text, flags=re.MULTILINE)
            for target in targets:
                purpose = {"test": "test", "check": "quality", "lint": "quality", "fmt": "quality",
                           "format": "quality", "build": "build", "run": "run", "dev": "run"}.get(target)
                if purpose:
                    self.add_command(purpose, "make " + target, "{} target '{}'".format(makefile, target))
            break
        if self.exists("justfile") or self.exists("Justfile"):
            name = "justfile" if self.exists("justfile") else "Justfile"
            text = _read_small(self.root / name) or ""
            for recipe in re.findall(r"^([A-Za-z0-9][A-Za-z0-9_-]*)(?:\s+[^:\n]*)?:(?!=)", text, flags=re.MULTILINE):
                if recipe in ("test", "lint", "check", "build", "fmt"):
                    self.add_command("test" if recipe == "test" else "build" if recipe == "build" else "quality",
                                     "just " + recipe, "{} recipe '{}'".format(name, recipe))

    def detect_tooling_and_deploy(self) -> None:
        for rel in self.files:
            name = rel.rsplit("/", 1)[-1]
            depth = rel.count("/")
            for pattern, label in TOOLING_FILES:
                if pattern.match(name) and (depth == 0 or rel.startswith(".github/")):
                    entry = {"tool": label, "evidence": rel}
                    if entry not in self.result["tooling"]:
                        self.result["tooling"].append(entry)
            if name in DEPLOY_FILES and depth <= 1:
                self.add_stack(DEPLOY_FILES[name], rel)
            if name.endswith(".tf") and depth <= 2:
                self.add_stack("Terraform", rel)
        if any(rel.startswith(".husky/") for rel in self.files):
            self.result["tooling"].append({"tool": "Husky Git hooks", "evidence": ".husky/"})
        for folder in ("k8s", "kubernetes", "helm", "charts"):
            if any(rel.startswith(folder + "/") for rel in self.files):
                self.add_stack("Kubernetes or Helm manifests", folder + "/")

    def detect_ci(self) -> None:
        ci = self.result["ci"]
        for rel in self.files:
            if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", rel):
                ci.append("GitHub Actions: {}".format(rel))
        for rel, label in ((".gitlab-ci.yml", "GitLab CI"), (".circleci/config.yml", "CircleCI"),
                           ("Jenkinsfile", "Jenkins"), ("azure-pipelines.yml", "Azure Pipelines"),
                           ("bitbucket-pipelines.yml", "Bitbucket Pipelines"), (".travis.yml", "Travis CI"),
                           (".drone.yml", "Drone CI")):
            if self.exists(rel):
                ci.append("{}: {}".format(label, rel))
        if any(rel.startswith(".buildkite/") for rel in self.files):
            ci.append("Buildkite: .buildkite/")

    def detect_docs(self) -> None:
        docs = self.result["docs"]

        def add(kind: str, path: str, details: str = "") -> None:
            docs.append({"kind": kind, "path": path, "details": details})

        top = [rel for rel in self.files if "/" not in rel]
        patterns = (
            (r"^README(?:\.\w+)?$", "Project overview"),
            (r"^(?:CHANGELOG|HISTORY|RELEASES)(?:\.\w+)?$", "Change history"),
            (r"^CONTRIBUTING(?:\.\w+)?$", "Contributor guide"),
            (r"^SECURITY(?:\.\w+)?$", "Security policy"),
            (r"^(?:LICENSE|LICENCE|COPYING)(?:\.\w+)?$", "License"),
            (r"^(?:TASKS|TODO|ROADMAP)\.md$", "Task or roadmap list"),
        )
        for rel in top:
            for pattern, kind in patterns:
                if re.match(pattern, rel, flags=re.IGNORECASE):
                    add(kind, rel)
        for rel in self.files:
            name = rel.rsplit("/", 1)[-1]
            if name in AGENT_INSTRUCTION_NAMES and rel.count("/") <= 3:
                add("Agent instructions", rel)
            if name == "project-context.md" and "templates" not in rel.split("/")[:-1]:
                add("Project context", rel)
            if name == "CODEOWNERS":
                add("Code owners", rel)
        for folder in ("docs", "doc"):
            count = sum(1 for rel in self.files if rel.startswith(folder + "/") and rel.endswith((".md", ".mdx", ".rst")))
            if count:
                add("Documentation folder", folder + "/", "{} documents".format(count))
        decision_dirs: Dict[str, int] = {}
        for rel in self.files:
            parts = rel.split("/")
            for index, part in enumerate(parts[:-1]):
                if part.lower() in DECISION_DIR_NAMES and index <= 3:
                    folder = "/".join(parts[: index + 1]) + "/"
                    if rel.endswith(".md"):
                        decision_dirs[folder] = decision_dirs.get(folder, 0) + 1
                    break
        for folder, count in sorted(decision_dirs.items()):
            add("Decision records", folder, "{} records".format(count))
        for rel in self.files:
            if rel.startswith(".mych/") and rel.endswith(".json"):
                self.result["task_ledgers"].append(self._ledger_summary(rel))

    def _ledger_summary(self, rel: str) -> Dict[str, Any]:
        data = _load_json(self.root / rel)
        if not data or not isinstance(data.get("tasks"), list):
            return {"path": rel, "readable": False}
        counts: Dict[str, int] = {}
        for task in data["tasks"]:
            status = task.get("status", "unknown") if isinstance(task, dict) else "unknown"
            counts[status] = counts.get(status, 0) + 1
        return {"path": rel, "readable": True, "project": data.get("project"), "tasks": len(data["tasks"]),
                "by_status": counts}

    def detect_env_and_secrets(self) -> None:
        for rel in self.files:
            name = rel.rsplit("/", 1)[-1]
            if ENV_TEMPLATE_RE.match(name):
                variables = []
                for line in (_read_small(self.root / rel) or "").splitlines():
                    match = ENV_VAR_RE.match(line)
                    if match:
                        variables.append(match.group(1))
                self.result["env_templates"].append({"path": rel, "variables": variables})
            elif SECRET_FILE_RE.match(name):
                self.result["sensitive_files"].append(rel)
            elif DATA_FILE_RE.match(name):
                self.result["data_files"].append(rel)


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def unittest_command(test_files: List[str]) -> str:
    """Build a unittest discovery command that finds the project's tests.

    Plain 'python -m unittest discover' starts in the current folder and only
    descends into packages, so tests in a tests/ folder without __init__.py
    are missed (0 tests ran). Point -s at the folder holding most test files
    and match their naming pattern.
    """
    folders: Dict[str, int] = {}
    for rel in test_files:
        folder = rel.rsplit("/", 1)[0] if "/" in rel else "."
        top = folder.split("/", 1)[0]
        folders[top] = folders.get(top, 0) + 1
    start = max(sorted(folders), key=lambda name: folders[name])
    command = "python3 -m unittest discover"
    if start != ".":
        command += " -s " + start
    if all(re.search(r"_test\.py$", rel) for rel in test_files):
        command += ' -p "*_test.py"'
    return command


def render_markdown(result: Dict[str, Any]) -> str:
    out: List[str] = ["# Project scan: {}".format(Path(result["root"]).name), ""]
    out.append("- Path: `{}`".format(result["root"]))
    scanned = "{} files".format(result["files_scanned"]) + (" (truncated)" if result["truncated"] else "")
    out.append("- Scanned: {}".format(scanned))
    if result["skipped_dirs"]:
        out.append("- Skipped folders: {}".format(", ".join(result["skipped_dirs"])))
    out.append("")

    git = result["git"]
    out.append("## Version control")
    if not git.get("available"):
        out.append("- Git is not available here.")
    elif not git.get("repository"):
        out.append("- Not a Git repository.")
    else:
        out.append("- Branch: {}".format(git.get("branch") or "unknown"))
        out.append("- Uncommitted changes: {}".format(git.get("uncommitted_changes", 0)))
        commits = git.get("recent_commits") or []
        out.append("- Recent commits: {}".format("none yet" if not commits else ""))
        for commit in commits:
            out.append("  - {}".format(commit))
    out.append("")

    def table(title: str, headers: Sequence[str], rows: List[Sequence[Any]], empty: str) -> None:
        out.append("## " + title)
        if not rows:
            out.append(empty)
        else:
            out.append("| " + " | ".join(headers) + " |")
            out.append("|" + "|".join("---" for _ in headers) + "|")
            for row in rows:
                out.append("| " + " | ".join(_cell(value) for value in row) + " |")
        out.append("")

    table("Languages", ("Language", "Files"), list(result["languages"].items()), "No source files recognized.")
    table("Stack signals", ("Signal", "Evidence"), [(s["signal"], s["evidence"]) for s in result["stack"]],
          "No stack manifests recognized.")
    table("Likely commands", ("Purpose", "Command", "Source"),
          [(c["purpose"], "`{}`".format(c["command"]), c["source"]) for c in result["commands"]],
          "No commands could be inferred.")
    table("Quality tooling", ("Tool", "Evidence"), [(t["tool"], t["evidence"]) for t in result["tooling"]],
          "No linters, formatters or hooks recognized.")
    out.append("## Continuous integration")
    if result["ci"]:
        out.extend("- {}".format(item) for item in result["ci"])
    else:
        out.append("None found.")
    out.append("")
    table("Documentation and project memory", ("Kind", "Path", "Details"),
          [(d["kind"], d["path"], d["details"]) for d in result["docs"]], "No documentation files found.")
    if result["task_ledgers"]:
        rows = []
        for ledger in result["task_ledgers"]:
            if ledger.get("readable"):
                status = ", ".join("{} {}".format(count, name) for name, count in sorted(ledger["by_status"].items()))
                rows.append((ledger["path"], ledger.get("project") or "", "{} tasks: {}".format(ledger["tasks"], status)))
            else:
                rows.append((ledger["path"], "", "not a readable task ledger"))
        table("Task ledgers", ("Path", "Project", "Summary"), rows, "")
    if result["env_templates"]:
        table("Environment templates", ("File", "Variables"),
              [(e["path"], ", ".join(e["variables"]) or "none declared") for e in result["env_templates"]], "")
    out.append("## Secret-bearing files (listed, not opened)")
    if result["sensitive_files"]:
        out.extend("- {}".format(path) for path in result["sensitive_files"])
    else:
        out.append("None found.")
    out.append("")
    out.append("## Data files (listed, not opened; may hold personal or production data, so ask before reading)")
    if result["data_files"]:
        out.extend("- {}".format(path) for path in result["data_files"])
    else:
        out.append("None found.")
    out.append("")
    out.append("## Notes")
    out.extend("- {}".format(note) for note in result["notes"])
    return "\n".join(out) + "\n"


def scan(root: Path, max_files: int = DEFAULT_MAX_FILES) -> Dict[str, Any]:
    return Scanner(root.resolve(), max_files=max_files).run()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize a project's languages, stack, commands, CI, docs and project memory. Read-only.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 scan-project.py                  scan the current directory\n"
            "  python3 scan-project.py ../my-app --format json\n"
            "\nexit status: 0 success, 2 usage error"
        ),
    )
    parser.add_argument("project_dir", nargs="?", default=".", help="project folder (default: current directory)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown", help="output format")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES,
                        help="stop after this many files (default: {})".format(DEFAULT_MAX_FILES))
    args = parser.parse_args(argv)
    root = Path(args.project_dir).expanduser()
    if not root.is_dir():
        print("error: {} is not a directory".format(root), file=sys.stderr)
        return 2
    if args.max_files < 1:
        print("error: --max-files must be at least 1", file=sys.stderr)
        return 2
    result = scan(root, max_files=args.max_files)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        sys.stdout.write(render_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
