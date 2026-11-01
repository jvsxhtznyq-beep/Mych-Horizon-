"""Tests for mych-plugin/scripts/detect-capabilities.py."""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from support import run_script

SECRET = "sk-test-DO-NOT-PRINT-4f9a1c"


class DetectCapabilitiesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.project = self.root / "project"
        self.home.mkdir()
        self.project.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def env(self, **extra):
        env = {key: value for key, value in os.environ.items()
               if not key.endswith(("_API_KEY", "_TOKEN", "_KEY")) and key not in ("ANTHROPIC_BASE_URL", "AWS_PROFILE")}
        env["HOME"] = str(self.home)
        env.update(extra)
        return env

    def run_json(self, *args, **extra):
        result = run_script("detect-capabilities", "--json", "--root", str(self.project), *args, env=self.env(**extra))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout), result.stdout

    def test_report_structure_and_speed(self):
        started = time.monotonic()
        report, _ = self.run_json()
        self.assertLess(time.monotonic() - started, 20)
        for key in ("platform", "commands", "python_modules", "gpu", "credentials", "skills", "mcp_servers",
                    "readiness", "host_hints"):
            self.assertIn(key, report)
        self.assertEqual(report["schema"], "mych-capabilities/1")
        self.assertTrue(report["commands"]["core"]["python3"] or report["commands"]["core"]["python"])
        self.assertEqual(report["network"], "not probed (use --network)")
        self.assertEqual(set(report["readiness"]), {
            "mych-pixel-art", "mych-image-generation", "mych-3d-design", "mych-chatbot-engineering",
            "mych-api-integration", "mych-emoji-language", "mych-cloud-infrastructure", "mych-runpod"})

    def test_credential_values_are_never_printed(self):
        report, raw = self.run_json(OPENAI_API_KEY=SECRET, MY_SERVICE_TOKEN=SECRET)
        self.assertNotIn(SECRET, raw)
        self.assertTrue(report["credentials"]["model_providers"]["OPENAI_API_KEY"])
        self.assertGreaterEqual(report["credentials"]["other_credential_like_variables"], 1)
        markdown = run_script("detect-capabilities", "--root", str(self.project),
                              env=self.env(OPENAI_API_KEY=SECRET)).stdout
        self.assertNotIn(SECRET, markdown)
        self.assertIn("OPENAI_API_KEY", markdown)

    def test_image_generation_is_partial_without_a_backend(self):
        report, _ = self.run_json()
        item = report["readiness"]["mych-image-generation"]
        if report["gpu"]["devices"] and report["python_modules"]["torch"] and report["python_modules"]["diffusers"]:
            self.skipTest("this machine has a local generation backend")
        self.assertEqual(item["level"], "partial")
        self.assertFalse(item["live_available"])
        self.assertIn("generation is unavailable", item["live_capability"])
        report, _ = self.run_json(STABILITY_API_KEY=SECRET)
        item = report["readiness"]["mych-image-generation"]
        self.assertTrue(item["live_available"])
        self.assertIn("not tested", item["live_capability"])

    def test_skills_and_mcp_names_without_their_configuration(self):
        skill = self.project / ".agents" / "skills" / "mych-pixel-art"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: mych-pixel-art\n---\n", encoding="utf-8")
        (self.project / ".mcp.json").write_text(json.dumps({"mcpServers": {"blender": {
            "command": "uvx", "args": ["blender-mcp"], "env": {"TOKEN": SECRET}}}}), encoding="utf-8")
        (self.home / ".codex").mkdir()
        (self.home / ".codex" / "config.toml").write_text(
            '[mcp_servers.docs]\ncommand = "npx"\nenv = {{ API_KEY = "{}" }}\n'.format(SECRET), encoding="utf-8")
        report, raw = self.run_json()
        self.assertNotIn(SECRET, raw)
        self.assertNotIn("blender-mcp", raw)
        self.assertEqual(report["skills"]["project .agents/skills"], ["mych-pixel-art"])
        self.assertEqual(report["mcp_servers"][str(self.project / ".mcp.json")], ["blender"])
        self.assertEqual(report["mcp_servers"]["~/.codex/config.toml"], ["docs"])

    def test_bad_root_is_a_usage_error(self):
        result = run_script("detect-capabilities", "--root", str(self.root / "missing"), env=self.env())
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
