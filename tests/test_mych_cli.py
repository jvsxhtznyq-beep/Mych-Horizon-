"""Tests for tools/mych.py: routing, tool translation and execution, bundles, export, registry checks."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from support import REPO_ROOT, call_main


def load_cli():
    name = "mych_cli"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, str(REPO_ROOT / "tools" / "mych.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


mych = load_cli()


class RouteTest(unittest.TestCase):
    def route(self, text):
        return mych.route(text)

    def test_game_routes_to_new_project_with_pixel_art_and_no_3d(self):
        result = self.route("Build a complete 2D pixel-art platformer game with menus, settings, sound and save/load")
        self.assertEqual(result["workflow"]["id"], "new-software-project")
        self.assertEqual(result["tier"], 3)
        self.assertEqual(result["lead"], "Engineer")
        self.assertTrue({"Architect", "Designer", "Engineer"} <= set(result["disciplines"]))
        ids = [item["id"] for item in result["specialists"]]
        self.assertIn("mych-pixel-art", ids)
        self.assertNotIn("mych-3d-design", ids)

    def test_small_change_is_tier_one_engineer_only(self):
        result = self.route("Fix the typo in the README")
        self.assertEqual((result["tier"], result["disciplines"], result["workflow"]["id"]),
                         (1, ["Engineer"], "lightweight-task"))

    def test_comparison_is_research(self):
        result = self.route("Compare PostgreSQL versus MongoDB for our analytics workload")
        self.assertEqual((result["lead"], result["workflow"]["id"]), ("Researcher", "technical-research"))

    def test_sensitive_terms_add_the_sensitive_workflow(self):
        result = self.route("Build a login system with password reset for the clinic app")
        self.assertEqual(result["workflow"]["id"], "new-software-project")
        self.assertEqual(result["also_follow"], ["sensitive-change"])
        self.assertGreaterEqual(result["tier"], 2)
        only = self.route("Rotate the leaked API key in production")
        self.assertEqual(only["workflow"]["id"], "sensitive-change")

    def test_runpod_prefers_the_runpod_specialist_over_generic_cloud(self):
        ids = [item["id"] for item in self.route("Deploy inference to RunPod serverless; estimate VRAM")["specialists"]]
        self.assertIn("mych-runpod", ids)
        self.assertNotIn("mych-cloud-infrastructure", ids)

    def test_question_takes_the_direct_path(self):
        result = self.route("What is a ZWJ emoji sequence?")
        self.assertEqual((result["tier"], result["workflow"]["id"], result["lead"]), (0, "direct-answer", "Researcher"))
        self.assertEqual(result["specialists"][0]["id"], "mych-emoji-language")

    def test_cli_json(self):
        status, out, _ = call_main(mych, ["route", "--json", "Fix", "the", "typo"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out)["tier"], 1)


class ToolTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_translations_have_the_documented_shapes(self):
        tools = mych.all_tools()
        openai = mych.translate(tools, "openai")
        self.assertEqual(openai[0]["type"], "function")
        self.assertIn("parameters", openai[0]["function"])
        anthropic = mych.translate(tools, "anthropic")
        self.assertIn("input_schema", anthropic[0])
        gemini = mych.translate(tools, "gemini")
        self.assertEqual(len(gemini), 1)
        names = [item["name"] for item in gemini[0]["functionDeclarations"]]
        self.assertEqual(names, [tool["name"] for tool in tools])
        self.assertEqual(mych.translate(tools, "openai-compatible"), openai)

    def test_gemini_schema_drops_non_portable_keywords(self):
        cleaned = mych.gemini_schema({"type": "object", "additionalProperties": False, "$schema": "x",
                                      "properties": {"a": {"type": "string", "default": "x", "description": "d"}},
                                      "required": []})
        self.assertEqual(cleaned, {"type": "object", "properties": {"a": {"type": "string", "description": "d"}}})

    def test_argument_validation(self):
        tool, _ = mych.find_tool("mych_task_ledger")
        self.assertEqual(mych.check_arguments(tool, {"command": "list"}), [])
        problems = mych.check_arguments(tool, {"command": "explode", "arguments": [1], "extra": True})
        self.assertTrue(any("must be one of" in p for p in problems))
        self.assertTrue(any("unknown argument 'extra'" in p for p in problems))
        self.assertTrue(any("every item of 'arguments'" in p for p in problems))
        self.assertIn("missing required argument 'command'", mych.check_arguments(tool, {}))

    def test_run_tool_executes_the_ledger_inside_the_workspace(self):
        result = mych.run_tool("mych_task_ledger", {"command": "init", "arguments": ["--project", "Demo"]},
                               self.workspace)
        self.assertTrue(result["ok"], result)
        self.assertTrue((self.workspace / ".mych" / "tasks.json").is_file())
        listed = mych.run_tool("mych_task_ledger", {"command": "list"}, self.workspace)
        self.assertIn("No tasks", listed["stdout"])

    def test_run_tool_refuses_paths_outside_the_workspace_and_forbidden_arguments(self):
        with self.assertRaises(mych.MychError):
            mych.run_tool("mych_scan_project", {"path": "../.."}, self.workspace)
        result = mych.run_tool("mych_task_ledger", {"command": "list", "arguments": ["--file", "/tmp/x.json"]},
                               self.workspace)
        self.assertFalse(result["ok"])
        self.assertIn("not allowed", result["error"])
        bad = mych.run_tool("mych_task_ledger", {"command": "rm -rf"}, self.workspace)
        self.assertFalse(bad["ok"])

    def test_tools_that_spend_money_need_approval(self):
        args = {"prompt": "x", "out": "out", "backend": "openai", "model": "m"}
        refused = mych.run_tool("mych_image_generate", args, self.workspace)
        self.assertFalse(refused["ok"])
        self.assertIn("approval", refused["error"])
        dry = mych.run_tool("mych_image_generate", dict(args, dry_run=True), self.workspace)
        self.assertTrue(dry["ok"], dry)
        self.assertIn('"dry_run": true', dry["stdout"])

    def test_run_tool_detect_capabilities_returns_json(self):
        result = mych.run_tool("mych_detect_capabilities", {}, self.workspace)
        self.assertTrue(result["ok"], result)
        self.assertEqual(json.loads(result["stdout"])["schema"], "mych-capabilities/1")


class BundleExportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_bundle_inlines_core_and_workflow_and_rewrites_placeholders(self):
        out = self.root / "bundle"
        manifest = mych.bundle("gemini", None, "Fix the flaky failing test in the cart module", out, 60000, [])
        prompt = (out / "system-prompt.md").read_text(encoding="utf-8")
        self.assertIn("<!-- begin mych-plugin/SKILL.md -->", prompt)
        self.assertIn("<!-- begin mych-plugin/workflows/debugging.md -->", prompt)
        self.assertNotIn("${CLAUDE_SKILL_DIR}", prompt)
        self.assertIn("mych-plugin/scripts/task-ledger.py", prompt)
        tools = json.loads((out / "tools.json").read_text(encoding="utf-8"))
        self.assertIn("functionDeclarations", tools[0])
        self.assertEqual(manifest["route"]["workflow"]["id"], "debugging")
        self.assertGreater(manifest["approx_tokens"], 1000)

    def test_bundle_refuses_to_exceed_the_token_budget(self):
        with self.assertRaises(mych.MychError) as caught:
            mych.bundle("openai", [], None, self.root / "b", 500, [])
        self.assertIn("over the limit of 500", str(caught.exception))

    def test_export_to_codex_project_rewrites_skill_dir_placeholder(self):
        project = self.root / "project"
        project.mkdir()
        actions = mych.export("codex", project, None, ["mych-plugin"], dry_run=False, force=False,
                              keep_placeholders=False)
        skill = project / ".agents" / "skills" / "mych-plugin"
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("${CLAUDE_SKILL_DIR}", text)
        self.assertIn("python3 .agents/skills/mych-plugin/scripts/task-ledger.py", text)
        self.assertTrue(any("documented" in action for action in actions))
        self.assertTrue((skill / "scripts" / "task-ledger.py").stat().st_mode & 0o100)
        with self.assertRaises(mych.MychError):
            mych.export("codex", project, None, ["mych-plugin"], dry_run=False, force=False, keep_placeholders=False)

    def test_export_to_claude_code_keeps_placeholders_and_dry_run_writes_nothing(self):
        project = self.root / "p2"
        project.mkdir()
        mych.export("claude-code", project, None, ["mych-plugin"], dry_run=True, force=False, keep_placeholders=False)
        self.assertFalse((project / ".claude").exists())
        mych.export("claude-code", project, None, ["mych-plugin"], dry_run=False, force=False, keep_placeholders=False)
        self.assertIn("${CLAUDE_SKILL_DIR}", (project / ".claude" / "skills" / "mych-plugin" / "SKILL.md").read_text())


class RegistryTest(unittest.TestCase):
    def test_registry_check_passes(self):
        errors, _ = mych.registry_check()
        self.assertEqual(errors, [])

    def test_tool_schemas_stay_portable(self):
        for tool in mych.all_tools([spec["id"] for spec in mych.specialists_registry()]):
            self.assertEqual(mych.schema_problems(tool["parameters"], tool["name"]), [])
            self.assertRegex(tool["name"], mych.TOOL_NAME_RE)

    def test_validate_all_passes(self):
        ok, results = mych.validate_all(strict=True)
        self.assertTrue(ok, "\n".join(item["report"] for item in results if not item["ok"]))


if __name__ == "__main__":
    unittest.main()
