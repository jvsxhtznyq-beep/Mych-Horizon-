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
        self.assertEqual(leftovers, [], "temporary or lock files left behind")
        self.assertEqual(self.data()["schema"], "mych-task-ledger/2")

    # -- schema 2: failed checks, evidence rules, approvals, locking, migration --

    def finish(self, task_id):
        self.run_ok("start", task_id)
        self.run_ok("complete", task_id)

    def test_failed_check_moves_task_to_failed_and_requires_rework(self):
        self.add("T1")
        self.finish("T1")
        self.run_ok("fail", "T1", "--evidence", "pytest tests/unit: 2 failed (test_slots, test_cancel)")
        task = self.task("T1")
        self.assertEqual(task["status"], "failed")
        self.assertEqual(task["checks"][-1]["result"], "fail")
        self.assertIn("| Failed | It exists | unit tests pass | FAILED: pytest tests/unit: 2 failed", self.run_ok("render"))
        err = self.run_fail(1, "verify", "T1", "--evidence", "pytest tests/unit: 14 passed")
        self.assertIn("fix it", err)
        self.run_ok("start", "T1")
        self.run_ok("complete", "T1")
        self.run_ok("verify", "T1", "--evidence", "pytest tests/unit: 14 passed")
        self.assertEqual([check["result"] for check in self.task("T1")["checks"]], ["fail", "pass"])
        self.assertEqual(ledger.check_ledger(self.data()), ([], []))

    def test_verify_refuses_evidence_with_failure_markers(self):
        self.add("T1")
        self.finish("T1")
        for evidence in ("pytest: 10 passed, 2 failed", "Ran 0 tests in 0.000s OK", "FAILED (failures=1)",
                         "Traceback (most recent call last): KeyError", "npm test exited with code 1",
                         "not ok 3 - parses dates", "jest: FAIL src/cart.test.js", "suite was not run (no DB)",
                         "could not connect to the staging database"):
            with self.subTest(evidence=evidence):
                err = self.run_fail(1, "verify", "T1", "--evidence", evidence)
                self.assertIn("evidence refused", err)
        self.assertEqual(self.task("T1")["status"], "completed")
        self.run_ok("verify", "T1", "--evidence", "pytest: 12 passed, 0 failed, exit 0")

    def test_verify_refuses_restated_and_vague_evidence_unless_overridden(self):
        self.add("T1")
        self.finish("T1")
        err = self.run_fail(1, "verify", "T1", "--evidence", "Unit tests pass.")
        self.assertIn("restates the verification method", err)
        err = self.run_fail(1, "verify", "T1", "--evidence", "it seems to work fine now")
        self.assertIn("not concrete", err)
        self.run_ok("verify", "T1", "--evidence", "Owner tried the flow and confirmed it",
                    "--override", "manual acceptance by the owner during the call")
        task = self.task("T1")
        self.assertEqual(task["status"], "verified")
        self.assertIn("override", task["checks"][-1])
        self.assertEqual(ledger.check_ledger(self.data()), ([], []))

    def test_prose_observation_counts_as_concrete(self):
        self.add("T1")
        self.finish("T1")
        self.run_ok("verify", "T1", "--evidence",
                    "Opened the settings screen in Chromium; the reduced-motion toggle rendered and saved")

    def test_task_needing_approval_cannot_start_until_approved(self):
        self.add("T1", "--needs-approval", "push to the shared main branch")
        err = self.run_fail(1, "start", "T1")
        self.assertIn("needs approval", err)
        self.assertIn("[needs approval]", self.run_ok("list"))
        self.run_fail(2, "approve", "T1", "--by", " ")
        self.run_ok("approve", "T1", "--by", "Kim", "--note", "this branch only")
        self.run_ok("start", "T1")
        task = self.task("T1")
        self.assertEqual(task["approval"]["granted_by"], "Kim")
        self.assertEqual(task["approvals"][0]["for"], "push to the shared main branch")
        self.assertEqual(ledger.check_ledger(self.data()), ([], []))
        self.run_fail(1, "approve", "T1", "--by", "Kim")
        self.assertIn("| T1 | push to the shared main branch | Kim |", self.run_ok("render"))

    def test_check_flags_started_task_without_recorded_approval(self):
        self.add("T1", "--needs-approval", "deploy to production")
        data = self.data()
        data["tasks"][0]["status"] = "in-progress"
        self.path.write_text(json.dumps(data), encoding="utf-8")
        status, out, _ = self.invoke("check")
        self.assertEqual(status, 1)
        self.assertIn("required approval was never recorded", out)

    def test_approval_block_requires_approver_to_lift(self):
        self.add("T1")
        self.run_ok("start", "T1")
        self.run_ok("block", "T1", "--reason", "migration drops a column", "--needs-approval")
        err = self.run_fail(1, "start", "T1")
        self.assertIn("blocked pending approval", err)
        err = self.run_fail(1, "unblock", "T1")
        self.assertIn("--approved-by", err)
        self.run_ok("unblock", "T1", "--approved-by", "Kim")
        task = self.task("T1")
        self.assertEqual(task["status"], "in-progress")
        self.assertEqual(task["approvals"][0]["by"], "Kim")
        self.assertEqual(task["history"][-1]["by"], "Kim")

    def test_completed_task_can_be_blocked_and_unblock_restores_it(self):
        self.add("T1")
        self.finish("T1")
        self.run_ok("block", "T1", "--reason", "staging is down, cannot run the smoke test")
        self.run_ok("unblock", "T1", "--note", "staging restored")
        self.assertEqual(self.task("T1")["status"], "completed")
        self.run_fail(1, "unblock", "T1")

    def test_v1_ledger_is_read_and_upgraded_on_write(self):
        v1 = {"schema": "mych-task-ledger/1", "project": "Old", "created_at": "2026-01-01T00:00:00Z",
              "updated_at": "2026-01-01T00:00:00Z", "tasks": [
                  {"id": "T1", "title": "Old task", "priority": "P1", "depends_on": [], "status": "verified",
                   "expected_result": "x", "verification_method": "pytest", "evidence": "pytest: 3 passed",
                   "blocker": None, "notes": [], "history": [
                       {"at": "2026-01-01T00:00:00Z", "from": None, "to": "not-started", "note": "created"},
                       {"at": "2026-01-02T00:00:00Z", "from": "completed", "to": "verified", "note": "e"}]},
                  {"id": "T2", "title": "Blocked task", "priority": "P2", "depends_on": [], "status": "blocked",
                   "expected_result": "y", "verification_method": "manual check", "evidence": None,
                   "blocker": {"reason": "keys", "unblock_when": None}, "notes": [], "history": [
                       {"at": "2026-01-01T00:00:00Z", "from": None, "to": "not-started", "note": "created"},
                       {"at": "2026-01-01T00:00:01Z", "from": "in-progress", "to": "blocked", "note": "keys"}]}]}
        self.path.write_text(json.dumps(v1), encoding="utf-8")
        status, out, _ = self.invoke("check")
        self.assertEqual(status, 0, out)
        self.assertIn("upgraded to mych-task-ledger/2 on the next write", out)
        self.run_ok("unblock", "T2")
        data = self.data()
        self.assertEqual(data["schema"], "mych-task-ledger/2")
        self.assertEqual(data["migrated_from"], "mych-task-ledger/1")
        self.assertNotIn("_upgrade_pending", data)
        self.assertIn("migrated_at", data)
        status, out, _ = self.invoke("check")
        self.assertNotIn("upgraded to", out)
        self.assertEqual(data["tasks"][0]["checks"][0]["evidence"], "pytest: 3 passed")
        self.assertEqual(data["tasks"][1]["status"], "in-progress")

    def test_concurrent_writers_do_not_lose_tasks(self):
        import subprocess
        import sys
        script = str(Path(ledger.__file__))
        procs = [subprocess.Popen([sys.executable, "-B", script, "--file", str(self.path), "add", "C{}".format(n),
                                   "--title", "Concurrent {}".format(n), "--expect", "exists",
                                   "--verify", "ledger lists it"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for n in range(12)]
        outputs = [proc.communicate(timeout=60) for proc in procs]
        self.assertEqual([proc.returncode for proc in procs], [0] * 12, outputs)
        self.assertEqual(sorted(task["id"] for task in self.data()["tasks"]),
                         sorted("C{}".format(n) for n in range(12)))
        self.assertFalse(ledger.lock_path_for(self.path).exists())

    def test_lock_wait_times_out_with_usage_error(self):
        with ledger.ledger_lock(self.path):
            with self.assertRaises(ledger.LedgerError) as caught:
                with ledger.ledger_lock(self.path, timeout=0.2):
                    pass
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("timed out", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
