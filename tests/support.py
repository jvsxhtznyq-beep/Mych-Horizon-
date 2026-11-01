"""Shared helpers for the MYCH-PLUGIN script tests.

The scripts use kebab-case file names, so they are loaded by path. Bytecode
writing is disabled while loading so tests never leave __pycache__ folders
inside the skill package.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "mych-plugin"
SCRIPTS_DIR = SKILL_DIR / "scripts"

DEFAULT_DESCRIPTION = "Formats demo reports for the team. Use when the user asks for a demo report."
DEFAULT_BODY = "# Demo\n\n" + "\n".join(
    "Step {}: follow the demo procedure carefully.".format(number) for number in range(1, 10)) + "\n"


def load_script(name: str):
    """Import scripts/<name>.py as a module (cached in sys.modules)."""
    module_name = "mych_" + name.replace("-", "_")
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = SCRIPTS_DIR / "{}.py".format(name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def run_script(name: str, *args: str, cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None):
    """Run a script in a subprocess, without writing bytecode."""
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS_DIR / "{}.py".format(name))] + list(args),
        capture_output=True, text=True, cwd=str(cwd) if cwd else None, env=env,
    )


def call_main(module, argv: Sequence[str]) -> Tuple[int, str, str]:
    """Call module.main(argv) in-process and capture its output."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = module.main(list(argv))
    return status, out.getvalue(), err.getvalue()


def make_skill(root: Path, name: str = "demo-skill", frontmatter: Optional[str] = None,
               body: Optional[str] = None, files: Optional[Dict[str, str]] = None) -> Path:
    """Create a minimal valid skill folder, optionally overriding parts of it."""
    skill = root / name
    skill.mkdir(parents=True)
    if frontmatter is None:
        frontmatter = "name: {}\ndescription: {}\n".format(name, DEFAULT_DESCRIPTION)
    (skill / "SKILL.md").write_text("---\n{}---\n{}".format(frontmatter, DEFAULT_BODY if body is None else body),
                                    encoding="utf-8")
    for rel, content in (files or {}).items():
        path = skill / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return skill
