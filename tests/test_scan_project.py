"""Tests for mych-plugin/scripts/scan-project.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import call_main, load_script, run_script

scanner = load_script("scan-project")

SECRET_VALUE = "supersecretvalue-do-not-print"


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class ScanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "sample-app"
        self.root.mkdir()
        write(self.root, "package.json", json.dumps({
            "name": "sample-app",
            "scripts": {"test": "vitest run", "lint": "eslint .", "build": "vite build"},
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"vite": "^5.0.0", "vitest": "^1.0.0"},
        }))
        write(self.root, "package-lock.json", "{}")
        write(self.root, "pyproject.toml",
              '[project]\nname = "svc"\nrequires-python = ">=3.10"\ndependencies = ["fastapi>=0.100", "pytest"]\n'
              "\n[tool.ruff]\nline-length = 100\n")
        write(self.root, "src/app.tsx", "export const App = () => null;\n")
        write(self.root, "src/server.py", "print('hi')\n")
        write(self.root, "node_modules/left-pad/index.js", "module.exports = 1;\n")
        write(self.root, "Makefile", "test:\n\tpytest\n\nlint:\n\truff check .\n")
        write(self.root, ".github/workflows/ci.yml", "on: push\n")
        write(self.root, "CLAUDE.md", "# Instructions\n")
        write(self.root, "README.md", "# Sample\n")
        write(self.root, "docs/decisions/0001-use-postgres.md", "# 1. Use PostgreSQL\n")
        write(self.root, "docs/decisions/0002-use-react.md", "# 2. Use React\n")
        write(self.root, "templates/project-context.md", "# Template\n")
        write(self.root, ".env", "API_KEY={}\n".format(SECRET_VALUE))
        write(self.root, ".env.example", "API_KEY=\nexport DATABASE_URL=postgres://localhost/db\n")
        write(self.root, ".mych/tasks.json", json.dumps({
            "schema": "mych-task-ledger/1", "project": "Sample",
            "tasks": [{"id": "T1", "status": "verified"}, {"id": "T2", "status": "in-progress"}],
        }))
        self.result = scanner.scan(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def signals(self):
        return [entry["signal"] for entry in self.result["stack"]]

    def commands(self):
        return [entry["command"] for entry in self.result["commands"]]

    def test_dependency_folders_are_skipped(self):
        self.assertIn("node_modules", self.result["skipped_dirs"])
        self.assertNotIn("JavaScript", self.result["languages"])
        self.assertEqual(self.result["languages"].get("TypeScript (TSX)"), 1)

    def test_stack_signals(self):
        signals = self.signals()
        for expected in ("Node.js project (npm)", "React", "Vite", "Vitest", "FastAPI", "pytest"):
            self.assertIn(expected, signals)
        self.assertTrue(any(signal.startswith("Python project (requires-python >=3.10)") for signal in signals)
                        or scanner.tomllib is None)

    def test_inferred_commands(self):
        commands = self.commands()
        for expected in ("npm test", "npm run lint", "npm run build", "pytest", "make test", "make lint"):
            self.assertIn(expected, commands)

    def test_ci_and_docs(self):
        self.assertIn("GitHub Actions: .github/workflows/ci.yml", self.result["ci"])
        kinds = {(doc["kind"], doc["path"]) for doc in self.result["docs"]}
        self.assertIn(("Agent instructions", "CLAUDE.md"), kinds)
        self.assertIn(("Project overview", "README.md"), kinds)
        self.assertIn(("Decision records", "docs/decisions/"), kinds)
        self.assertNotIn(("Project context", "templates/project-context.md"), kinds)

    def test_task_ledger_summary(self):
        ledger = self.result["task_ledgers"][0]
        self.assertEqual(ledger["tasks"], 2)
        self.assertEqual(ledger["by_status"], {"verified": 1, "in-progress": 1})

    def test_env_templates_list_names_only(self):
        template = self.result["env_templates"][0]
        self.assertEqual(template["variables"], ["API_KEY", "DATABASE_URL"])

    def test_secret_files_are_listed_but_never_read(self):
        self.assertIn(".env", self.result["sensitive_files"])
        status, out, _ = call_main(scanner, [str(self.root), "--format", "json"])
        self.assertEqual(status, 0)
        self.assertNotIn(SECRET_VALUE, out)
        status, out, _ = call_main(scanner, [str(self.root)])
        self.assertNotIn(SECRET_VALUE, out)
        self.assertIn("## Secret-bearing files (listed, not opened)", out)

    def test_markdown_sections(self):
        text = scanner.render_markdown(self.result)
        for heading in ("# Project scan: sample-app", "## Languages", "## Stack signals", "## Likely commands",
                        "## Documentation and project memory", "## Notes"):
            self.assertIn(heading, text)

    def test_max_files_truncates(self):
        result = scanner.scan(self.root, max_files=3)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["files_scanned"], 3)

    def test_usage_errors(self):
        status, _, err = call_main(scanner, [str(self.root / "missing")])
        self.assertEqual(status, 2)
        self.assertIn("not a directory", err)
        completed = run_script("scan-project", str(self.root), "--max-files", "0")
        self.assertEqual(completed.returncode, 2)

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_git_information(self):
        git = ["git", "-C", str(self.root), "-c", "user.email=test@example.com", "-c", "user.name=Test"]
        subprocess.run(git + ["init", "-q", "-b", "main"], check=True)
        subprocess.run(git + ["add", "README.md"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "Initial commit"], check=True)
        info = scanner.scan(self.root)["git"]
        self.assertTrue(info["repository"])
        self.assertEqual(info["branch"], "main")
        self.assertEqual(len(info["recent_commits"]), 1)
        self.assertIn("Initial commit", info["recent_commits"][0])
        self.assertGreater(info["uncommitted_changes"], 0)


if __name__ == "__main__":
    unittest.main()


class ScannerFixesTest(unittest.TestCase):
    """Fixes for weaknesses found in the 1.0 live test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def commands(self, result, purpose="test"):
        return [item["command"] for item in result["commands"] if item["purpose"] == purpose]

    def test_unittest_command_points_at_the_tests_folder_and_runs_tests(self):
        write(self.root, "app/__init__.py", "")
        write(self.root, "app/core.py", "def add(a, b):\n    return a + b\n")
        write(self.root, "tests/test_core.py",
              "import unittest\nfrom app.core import add\n\nclass T(unittest.TestCase):\n"
              "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n")
        result = scanner.scan(self.root)
        self.assertEqual(self.commands(result), ["python3 -m unittest discover -s tests"])
        run = subprocess.run(["python3", "-B", "-m", "unittest", "discover", "-s", "tests"], cwd=str(self.root),
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Ran 1 test", run.stderr)

    def test_unittest_pattern_for_suffix_named_tests(self):
        write(self.root, "checks/core_test.py", "import unittest\n")
        self.assertEqual(self.commands(scanner.scan(self.root)),
                         ['python3 -m unittest discover -s checks -p "*_test.py"'])

    def test_data_files_are_listed_but_not_opened(self):
        write(self.root, "data/production.db", "SQLite format 3\x00 " + SECRET_VALUE)
        write(self.root, "backups/2026-01-01-dump.sql", SECRET_VALUE)
        write(self.root, "migrations/0001_init.sql", "create table t (id int);\n")
        result = scanner.scan(self.root)
        self.assertEqual(sorted(result["data_files"]), ["backups/2026-01-01-dump.sql", "data/production.db"])
        rendered = scanner.render_markdown(result)
        self.assertIn("## Data files (listed, not opened", rendered)
        self.assertNotIn(SECRET_VALUE, rendered + json.dumps(result))

    def test_node_tap_and_builtin_runner_are_recognized(self):
        write(self.root, "package.json", json.dumps({"scripts": {"test": "node --test test/"},
                                                     "devDependencies": {"tap": "^18.0.0"}}))
        result = scanner.scan(self.root)
        stacks = [item["signal"] for item in result["stack"]]
        self.assertIn("node-tap", stacks)
        self.assertIn("Node.js built-in test runner", stacks)

    def test_node_test_files_without_package_json(self):
        write(self.root, "tests/physics.test.mjs", "import test from 'node:test';\n")
        self.assertEqual(self.commands(scanner.scan(self.root)), ["node --test"])
