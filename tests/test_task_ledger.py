"""Tests for mych-plugin/scripts/task-ledger.py."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import call_main, load_script

ledger = load_script("task-ledger")


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / ".mych" / "tasks.json"
        self.run_ok("init", "--project", "Test project")

    def tearDown(self):
        self._tmp.cleanup()

    def invoke(self, *args):
        return call_main(ledger, ["--file", str(self.path)] + list(args))

    def run_ok(self, *args):
        status, out, err = call_main(ledger, ["--file", str(self.path)] + list(args))
        self.assertEqual(status, 0, "{} failed: {}{}".format(args, out, err))
        return out

    def run_fail(self, expected_status, *args):
        status, out, err = call_main(ledger, ["--file", str(self.path)] + list(args))
        self.assertEqual(status, expected_status, "{} returned {}: {}{}".format(args, status, out, err))
        return err

    def data(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def task(self, task_id):
        return next(task for task in self.data()["tasks"] if task["id"] == task_id)

    def add(self, task_id, *extra):
        self.run_ok("add", task_id, "--title", "Task " + task_id, "--expect", "It exists",
                    "--verify", "unit tests pass", *extra)

    def test_happy_path_to_verified(self):
        self.add("T1", "--priority", "P1")
        self.run_ok("start", "T1")
        self.run_ok("complete", "T1", "--note", "implemented")
        self.run_ok("verify", "T1", "--evidence", "pytest tests/unit: 12 passed")
        task = self.task("T1")
        self.assertEqual(task["status"], "verified")
        self.assertEqual(task["evidence"], "pytest tests/unit: 12 passed")
        self.assertEqual([entry["to"] for entry in task["history"]],
                         ["not-started", "in-progress", "completed", "verified"])

    def test_init_refuses_to_overwrite(self):
        err = self.run_fail(1, "init", "--project", "Again")
        self.assertIn("refusing to overwrite", err)

    def test_add_rules(self):
        self.add("T1")
        self.run_fail(1, "add", "T1", "--title", "x", "--expect", "y", "--verify", "z")
        self.run_fail(1, "add", "T2", "--title", "x", "--expect", "y", "--verify", "z", "--depends", "T9")
        self.run_fail(2, "add", "9bad", "--title", "x", "--expect", "y", "--verify", "z")
        self.run_fail(2, "add", "T3", "--title", " ", "--expect", "y", "--verify", "z")

    def test_start_waits_for_dependencies_unless_forced(self):
        self.add("T1")
        self.add("T2", "--depends", "T1")
        err = self.run_fail(1, "start", "T2")
        self.assertIn("not finished", err)
        self.run_ok("start", "T2", "--force")
        self.assertIn("unfinished dependencies", self.task("T2")["history"][-1]["note"])
        errors, warnings = ledger.check_ledger(self.data())
        self.assertEqual((errors, warnings), ([], []))

    def test_verify_requires_completion(self):
        self.add("T1")
        self.run_ok("start", "T1")
        err = self.run_fail(1, "verify", "T1", "--evidence", "pytest: 12 passed")
        self.assertIn("complete it first", err)

    def test_verify_rejects_placeholder_evidence(self):
        self.add("T1")
        self.run_ok("start", "T1")
        self.run_ok("complete", "T1")
        for evidence in ("done", "Passed.", "LGTM", "ok ok", ""):
            with self.subTest(evidence=evidence):
                self.run_fail(1, "verify", "T1", "--evidence", evidence)
        self.assertEqual(self.task("T1")["status"], "completed")

    def test_block_and_resume(self):
        self.add("T1")
        self.run_ok("block", "T1", "--reason", "waiting for API keys", "--unblock", "owner provides keys")
        self.assertEqual(self.task("T1")["blocker"]["reason"], "waiting for API keys")
        self.run_ok("start", "T1")
        task = self.task("T1")
        self.assertEqual(task["status"], "in-progress")
        self.assertIsNone(task["blocker"])

    def test_reopen_clears_evidence_but_keeps_history(self):
        self.add("T1")
        self.run_ok("start", "T1")
        self.run_ok("complete", "T1")
        self.run_ok("verify", "T1", "--evidence", "pytest tests/unit: 12 passed")
        self.run_ok("reopen", "T1", "--reason", "regression found in staging")
        task = self.task("T1")
        self.assertEqual(task["status"], "in-progress")
        self.assertIsNone(task["evidence"])
        self.assertIn("previous evidence: pytest tests/unit: 12 passed", task["history"][-1]["note"])
        self.run_fail(1, "reopen", "T1", "--reason", "again")

    def test_complete_requires_in_progress(self):
        self.add("T1")
        err = self.run_fail(1, "complete", "T1")
        self.assertIn("start it first", err)

    def test_check_detects_tampering(self):
        self.add("T1")
        self.add("T2", "--depends", "T1")
        data = self.data()
        data["tasks"][0]["status"] = "verified"
        data["tasks"][0]["depends_on"] = ["T2"]
        data["tasks"][1]["depends_on"] = ["T1", "T9"]
        self.path.write_text(json.dumps(data), encoding="utf-8")
        status, out, _ = self.invoke("check")
        self.assertEqual(status, 1)
        self.assertIn("verified without valid evidence", out)
        self.assertIn("unknown task 'T9'", out)
        self.assertIn("dependency cycle", out)

    def test_render_and_list(self):
        self.add("T1", "--priority", "P0")
        markdown = self.run_ok("render")
        self.assertIn("| ID | Description | Priority | Depends on | Status |", markdown)
        self.assertIn("| T1 | Task T1 | P0 | none | Not started |", markdown)
        listed = json.loads(self.run_ok("list", "--json"))
        self.assertEqual([task["id"] for task in listed], ["T1"])
        shown = self.run_ok("show", "T1")
        self.assertIn("verification: unit tests pass", shown)

    def test_missing_ledger_is_a_usage_error(self):
        status, _, err = call_main(ledger, ["--file", str(self.path.parent / "none.json"), "list"])
        self.assertEqual(status, 2)
        self.assertIn("no ledger", err)

    def test_new_ledger_has_normal_permissions_and_existing_mode_is_kept(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o644)
        self.path.chmod(0o600)
        self.add("T1")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_writes_leave_no_temporary_files(self):
        self.add("T1")
        self.run_ok("start", "T1")
        leftovers = [p.name for p in self.path.parent.iterdir() if p.name != "tasks.json"]
        self.assertEqual(leftovers, [])
        self.assertEqual(self.data()["schema"], "mych-task-ledger/1")


if __name__ == "__main__":
    unittest.main()
