#!/usr/bin/env python3
"""Keep a project's task list in a JSON ledger that enforces status rules.

Statuses: not-started, in-progress, blocked, completed, failed, verified.

Rules:
  - a task starts only when its dependencies are completed or verified
    (--force overrides, and the override is recorded in the task history);
  - a task that needs approval starts only after 'approve' records who
    approved it; an approval block is lifted only with --approved-by;
  - only an in-progress task can be completed;
  - only a completed task can be verified. Verification requires evidence
    from a check that ran: not a placeholder, not a restatement of the
    verification method, concrete (a count, path, command or output), and
    free of failure markers such as "2 failed", "Traceback" or "Ran 0 tests".
    A failed check is recorded with 'fail', which moves the task to failed;
  - blocking requires a reason; unblocking restores the earlier status;
    reopening requires a reason and clears the evidence, which stays in the
    history.

Every write happens under a lock file next to the ledger, so concurrent
writers wait for each other instead of overwriting each other's changes.
Ledgers in the older mych-task-ledger/1 format are read and upgraded on the
next write.

Usage:
  python3 task-ledger.py [--file LEDGER] COMMAND [options]

Commands: init, add, start, block, unblock, approve, complete, verify, fail,
reopen, list, show, render, check. 'task-ledger.py COMMAND --help' explains
each. The ledger defaults to .mych/tasks.json under the current directory.
Exit status: 0 success, 1 rule violation or failed check, 2 usage or file
error.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import json
import os
import re
import stat
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

try:  # POSIX advisory locks; Windows falls back to an exclusive lock file.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on Windows
    fcntl = None  # type: ignore[assignment]

SCHEMA = "mych-task-ledger/2"
LEGACY_SCHEMAS = ("mych-task-ledger/1",)
STATUSES = ("not-started", "in-progress", "blocked", "completed", "failed", "verified")
STATUS_LABELS = {
    "not-started": "Not started", "in-progress": "In progress", "blocked": "Blocked",
    "completed": "Completed", "failed": "Failed", "verified": "Verified",
}
PRIORITIES = ("P0", "P1", "P2", "P3")
DEFAULT_PRIORITY = "P2"
FINISHED = ("completed", "verified")
STARTED = ("in-progress", "completed", "failed", "verified")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,31}$")
DEFAULT_LEDGER = Path(".mych") / "tasks.json"
# Permissions for a newly created ledger file (an existing ledger keeps its own).
LEDGER_FILE_MODE = 0o644
LOCK_TIMEOUT_SECONDS = 20.0
LOCK_POLL_SECONDS = 0.02
# Used only without fcntl: a lock file older than this is treated as left
# behind by a crashed writer. Ledger writes take milliseconds.
STALE_LOCK_SECONDS = 60.0

# Evidence must name a check and its result. Text shorter than this cannot,
# and these stand-ins describe a belief rather than an observation.
MIN_EVIDENCE_CHARS = 8
PLACEHOLDER_EVIDENCE = frozenset({
    "done", "ok", "okay", "yes", "pass", "passed", "passes", "works", "it works", "verified", "tested",
    "complete", "completed", "fixed", "good", "fine", "lgtm", "looks good", "todo", "tbd", "n/a", "na",
    "none", "-", "?", "see above", "as expected", "works as expected", "all good", "tests pass",
    "tests passed", "all tests pass", "all tests passed", "checked", "verified manually", "manually verified",
})
# Text that shows the check failed, errored or never ran. Verification refuses
# evidence that matches unless --override explains why the match is harmless.
FAILURE_MARKERS: Tuple[Tuple["re.Pattern[str]", str], ...] = (
    (re.compile(r"(?<![\d.])[1-9]\d*\s+(?:tests?\s+)?(?:failed|failures?|errors?|failing)\b", re.I),
     "reports failures or errors"),
    (re.compile(r"\b(?:failed|failures|errors)\s*[:=]\s*[1-9]", re.I), "reports failures or errors"),
    (re.compile(r"(?<!0 )\bFAILED\b"), "contains FAILED"),
    (re.compile(r"\bFAIL\b"), "contains FAIL"),
    (re.compile(r"Traceback \(most recent call last\)"), "contains a traceback"),
    (re.compile(r"\bAssertionError\b"), "contains an assertion error"),
    (re.compile(r"\bexit(?:ed)?(?:\s+with)?(?:\s+(?:code|status))?\s*[:=]?\s*[1-9]\d*\b", re.I),
     "reports a non-zero exit status"),
    (re.compile(r"(?:^|\n)\s*not ok\b|\bnot ok \d", re.I), "contains a TAP failure line"),
    (re.compile(r"\bRan 0 tests\b|\bcollected 0 items\b|(?<![\d.])0 tests?\b|"
                r"\bno tests? (?:ran|run|found|collected|executed)\b", re.I), "shows that no tests ran"),
    (re.compile(r"\b(?:not|never) (?:run|ran|executed|tested|checked|verified)\b", re.I),
     "says the check did not run"),
    (re.compile(r"\b(?:could not|couldn't|unable to|cannot|can't) "
                r"(?:run|execute|test|connect|reach|verify|build|compile|start|load)\b", re.I),
     "says the check could not run"),
)
# Concrete evidence names something checkable: a number, a command in
# backticks, a URL, a path or file name. Longer prose that reports an
# observation also counts.
CONCRETE_RE = re.compile(
    r"\d|`[^`]+`|https?://|[\w.-]+/[\w./-]+|\b[\w-]+\.(?:py|js|mjs|ts|tsx|jsx|json|md|html|css|png|jpe?g|gif|"
    r"svg|txt|log|ya?ml|toml|sh|go|rs|java|kt|rb|php|sql|csv|glb|gltf|zip)\b", re.I)
OBSERVATION_RE = re.compile(
    r"\b(?:ran|executed|opened|loaded|rendered|returned|responded|printed|output|logged|measured|compared|"
    r"inspected|observed|screenshot|showed|shows|displayed|reported|matched|matches|played|replayed)\b", re.I)
MIN_PROSE_EVIDENCE_CHARS = 40

# Allowed transitions: target status -> statuses it may be reached from.
# Unblocking restores the status a task had before it was blocked.
TRANSITIONS = {
    "in-progress": ("not-started", "blocked", "failed"),
    "blocked": ("not-started", "in-progress", "completed", "failed"),
    "completed": ("in-progress",),
    "failed": ("in-progress", "completed", "verified"),
    "verified": ("completed",),
}


class LedgerError(Exception):
    """A refused operation. code 1 = rule violation, code 2 = usage or file problem."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Storage and locking
# ---------------------------------------------------------------------------

def lock_path_for(path: Path) -> Path:
    return path.with_name(path.name + ".lock")


@contextlib.contextmanager
def ledger_lock(path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    """Hold an exclusive lock for one read-modify-write cycle of the ledger.

    The lock file is removed on release. With fcntl, a writer that locked a
    file which another writer has since removed notices that the path no
    longer names its file and tries again, so two writers never hold the
    lock at once.
    """
    lock_path = lock_path_for(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout

    def waited_too_long() -> None:
        if time.monotonic() > deadline:
            raise LedgerError("timed out after {:.0f}s waiting for {}; if no other ledger command is running, "
                              "delete that file and retry".format(timeout, lock_path), code=2)
        time.sleep(LOCK_POLL_SECONDS)

    if fcntl is not None:
        while True:
            fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
            try:
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except OSError as exc:
                        if exc.errno not in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
                            raise
                        waited_too_long()
                try:
                    current = os.stat(str(lock_path)).st_ino == os.fstat(fd).st_ino
                except FileNotFoundError:
                    current = False
            except BaseException:
                os.close(fd)
                raise
            if current:
                break
            os.close(fd)
        try:
            yield
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(str(lock_path))
            os.close(fd)
        return

    while True:  # pragma: no cover - exercised only without fcntl
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o644)
            break
        except FileExistsError:
            try:
                if time.time() - os.stat(str(lock_path)).st_mtime > STALE_LOCK_SECONDS:
                    os.unlink(str(lock_path))
                    continue
            except FileNotFoundError:
                continue
            waited_too_long()
    try:  # pragma: no cover
        yield
    finally:  # pragma: no cover
        os.close(fd)
        with contextlib.suppress(FileNotFoundError):
            os.unlink(str(lock_path))


def migrate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Bring a ledger to the current schema in memory; it is written on the next save."""
    if data.get("schema") in LEGACY_SCHEMAS:
        data["migrated_from"] = data["schema"]
        data["schema"] = SCHEMA
        data["_upgrade_pending"] = True  # dropped when saved
        for task in data["tasks"]:
            if not isinstance(task, dict):
                continue
            if task.get("status") == "verified" and task.get("evidence"):
                verified_at = next((entry.get("at") for entry in reversed(task.get("history", []))
                                    if entry.get("to") == "verified"), None)
                task.setdefault("checks", [{"at": verified_at, "result": "pass", "evidence": task["evidence"],
                                            "note": "recorded before schema 2"}])
            blocker = task.get("blocker")
            if isinstance(blocker, dict):
                blocker.setdefault("kind", "dependency")
                blocker.setdefault("previous", previous_status_from_history(task))
    for task in data["tasks"]:
        if isinstance(task, dict):
            task.setdefault("checks", [])
            task.setdefault("approval", None)
            task.setdefault("approvals", [])
            task.setdefault("notes", [])
            task.setdefault("history", [])
    return data


def previous_status_from_history(task: Dict[str, Any]) -> str:
    for entry in reversed(task.get("history", [])):
        if entry.get("to") == "blocked" and entry.get("from") in STATUSES:
            return entry["from"]
    return "not-started"


def load_ledger(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise LedgerError("no ledger at {}; create one with 'init --project NAME'".format(path), code=2)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerError("cannot read ledger {}: {}".format(path, exc), code=2) from exc
    if (not isinstance(data, dict) or data.get("schema") not in (SCHEMA,) + LEGACY_SCHEMAS
            or not isinstance(data.get("tasks"), list)):
        raise LedgerError("{} is not a {} ledger".format(path, SCHEMA), code=2)
    return migrate(data)


def save_ledger(path: Path, data: Dict[str, Any]) -> None:
    """Write the ledger atomically: a crash leaves either the old or the new file."""
    data["updated_at"] = now()
    if data.pop("_upgrade_pending", False):
        data["migrated_at"] = data["updated_at"]
    path.parent.mkdir(parents=True, exist_ok=True)
    # Temporary files are created private (0600); keep the ledger's existing
    # permissions, or use normal read permissions for a new ledger.
    final_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else LEDGER_FILE_MODE
    handle, temp_name = tempfile.mkstemp(prefix=".ledger-", suffix=".json", dir=str(path.parent))
    try:
        os.chmod(temp_name, final_mode)
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temp_name, str(path))
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


@contextlib.contextmanager
def editing(path: Path) -> Iterator[Dict[str, Any]]:
    """Lock, load, let the caller change the data, then save it."""
    with ledger_lock(path):
        data = load_ledger(path)
        yield data
        save_ledger(path, data)


def find_task(data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    for task in data["tasks"]:
        if task.get("id") == task_id:
            return task
    known = ", ".join(task.get("id", "?") for task in data["tasks"]) or "none"
    raise LedgerError("unknown task '{}' (known: {})".format(task_id, known))


def record(task: Dict[str, Any], previous: Optional[str], target: str, note: str, by: Optional[str] = None) -> None:
    entry: Dict[str, Any] = {"at": now(), "from": previous, "to": target, "note": note}
    if by:
        entry["by"] = by
    task["history"].append(entry)


def transition(task: Dict[str, Any], target: str, note: str = "", by: Optional[str] = None) -> None:
    current = task["status"]
    allowed = TRANSITIONS.get(target, ())
    if current not in allowed:
        hint = ""
        if target == "verified" and current == "in-progress":
            hint = "; complete it first, then verify it with evidence"
        elif target == "verified" and current == "failed":
            hint = "; fix it ('start'), complete it, then verify it again"
        elif target == "completed" and current in ("not-started", "blocked", "failed"):
            hint = "; start it first"
        raise LedgerError("{}: cannot move from {} to {}{}".format(task["id"], current, target, hint))
    task["status"] = target
    record(task, current, target, note, by)


def unfinished_dependencies(data: Dict[str, Any], task: Dict[str, Any]) -> List[str]:
    statuses = {item.get("id"): item.get("status") for item in data["tasks"]}
    return [dep for dep in task.get("depends_on", []) if statuses.get(dep) not in FINISHED]


def approval_pending(task: Dict[str, Any]) -> bool:
    approval = task.get("approval")
    return isinstance(approval, dict) and bool(approval.get("required")) and not approval.get("granted_by")


# ---------------------------------------------------------------------------
# Evidence rules
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def evidence_problem(text: Optional[str]) -> Optional[str]:
    """Basic rules that no override can waive: present, substantive, not a placeholder."""
    if text is None or not text.strip():
        return "evidence is required: say which check ran and what it showed"
    normalized = re.sub(r"[\s.!]+$", "", text.strip().lower())
    if normalized in PLACEHOLDER_EVIDENCE:
        return "evidence {!r} states a belief, not an observation; name the check and its result".format(text.strip())
    if len(text.strip()) < MIN_EVIDENCE_CHARS:
        return "evidence is too short to name a check and its result"
    return None


def failure_markers(text: str) -> List[str]:
    """Describe each failure marker found in the text, quoting what matched."""
    found = []
    for pattern, meaning in FAILURE_MARKERS:
        match = pattern.search(text)
        if match:
            found.append("{} ({!r})".format(meaning, match.group(0).strip()))
    return found


def evidence_warnings(text: str, method: str) -> List[str]:
    """Heuristic rules that --override can waive, each with a reason to record."""
    problems = []
    evidence_norm, method_norm = _normalize(text), _normalize(method or "")
    if evidence_norm and method_norm and (evidence_norm == method_norm or evidence_norm in method_norm):
        problems.append("it restates the verification method instead of reporting what the check showed")
    markers = failure_markers(text)
    if markers:
        problems.append("it " + "; it ".join(markers))
    if not CONCRETE_RE.search(text) and not (len(text.strip()) >= MIN_PROSE_EVIDENCE_CHARS
                                             and OBSERVATION_RE.search(text)):
        problems.append("it is not concrete: include a count, command, path, URL or the observed output")
    return problems


# ---------------------------------------------------------------------------
# Integrity check
# ---------------------------------------------------------------------------

def find_cycle(data: Dict[str, Any]) -> Optional[List[str]]:
    graph = {task.get("id"): list(task.get("depends_on", [])) for task in data["tasks"]}
    state: Dict[str, int] = {}
    stack: List[str] = []

    def visit(node: str) -> Optional[List[str]]:
        state[node] = 1
        stack.append(node)
        for dep in graph.get(node, []):
            if dep not in graph:
                continue
            if state.get(dep) == 1:
                return stack[stack.index(dep):] + [dep]
            if state.get(dep) is None:
                found = visit(dep)
                if found:
                    return found
        stack.pop()
        state[node] = 2
        return None

    for node in graph:
        if state.get(node) is None:
            found = visit(node)
            if found:
                return found
    return None


def check_ledger(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    if data.get("_upgrade_pending"):
        warnings.append("ledger uses {}; it is upgraded to {} on the next write".format(
            data["migrated_from"], SCHEMA))
    seen = set()
    ids = {task.get("id") for task in data["tasks"] if isinstance(task, dict)}
    for task in data["tasks"]:
        if not isinstance(task, dict):
            errors.append("a task entry is not an object")
            continue
        task_id = task.get("id")
        label = task_id or "<missing id>"
        if not isinstance(task_id, str) or not ID_RE.match(task_id):
            errors.append("{}: invalid task id".format(label))
        if task_id in seen:
            errors.append("{}: duplicate task id".format(label))
        seen.add(task_id)
        status = task.get("status")
        if status not in STATUSES:
            errors.append("{}: invalid status {!r}".format(label, status))
        if task.get("priority") not in PRIORITIES:
            errors.append("{}: invalid priority {!r}".format(label, task.get("priority")))
        for field_name in ("title", "expected_result", "verification_method"):
            if not str(task.get(field_name) or "").strip():
                errors.append("{}: missing {}".format(label, field_name.replace("_", " ")))
        for dep in task.get("depends_on", []):
            if dep not in ids:
                errors.append("{}: depends on unknown task '{}'".format(label, dep))
            if dep == task_id:
                errors.append("{}: depends on itself".format(label))
        if status == "verified":
            problem = evidence_problem(task.get("evidence"))
            if problem:
                errors.append("{}: verified without valid evidence ({})".format(label, problem))
            else:
                overridden = any("override:" in (entry.get("note") or "") for entry in task.get("history", []))
                for issue in evidence_warnings(task["evidence"], task.get("verification_method") or ""):
                    if not overridden:
                        warnings.append("{}: verified evidence is questionable: {}".format(label, issue))
        elif task.get("evidence"):
            warnings.append("{}: has evidence but is {}, not verified".format(label, status))
        if status == "failed" and not any(check.get("result") == "fail" for check in task.get("checks", [])):
            errors.append("{}: failed without a recorded failing check".format(label))
        if status == "blocked":
            blocker = task.get("blocker") or {}
            if not str(blocker.get("reason") or "").strip():
                errors.append("{}: blocked without a recorded reason".format(label))
        if status in STARTED and approval_pending(task):
            errors.append("{}: is {} but its required approval was never recorded".format(label, status))
        if status in ("in-progress", "completed", "verified"):
            pending = unfinished_dependencies(data, task)
            forced = any("unfinished dependencies" in (entry.get("note") or "") for entry in task.get("history", []))
            if pending and not forced:
                warnings.append("{}: is {} while dependencies {} are unfinished".format(label, status, ", ".join(pending)))
    cycle = find_cycle(data)
    if cycle:
        errors.append("dependency cycle: {}".format(" -> ".join(cycle)))
    return errors, warnings


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(data: Dict[str, Any]) -> str:
    lines = ["# Task plan: {}".format(data.get("project") or "untitled"), "",
             "Updated: {}".format(data.get("updated_at") or data.get("created_at") or ""), "",
             "| ID | Description | Priority | Depends on | Status | Expected result | Verification method | Evidence |",
             "|---|---|---|---|---|---|---|---|"]
    for task in data["tasks"]:
        evidence = task.get("evidence") or ""
        if task["status"] == "failed":
            failing = [check for check in task.get("checks", []) if check.get("result") == "fail"]
            evidence = "FAILED: " + failing[-1]["evidence"] if failing else ""
        lines.append("| " + " | ".join(_cell(value) for value in (
            task["id"], task["title"], task["priority"], ", ".join(task.get("depends_on", [])) or "none",
            STATUS_LABELS.get(task["status"], task["status"]), task["expected_result"],
            task["verification_method"], evidence)) + " |")
    blocked = [task for task in data["tasks"] if task["status"] == "blocked"]
    if blocked:
        lines += ["", "| Blocked task | Blocker | Kind | Unblocks when |", "|---|---|---|---|"]
        for task in blocked:
            blocker = task.get("blocker") or {}
            lines.append("| {} | {} | {} | {} |".format(
                _cell(task["id"]), _cell(blocker.get("reason", "")), _cell(blocker.get("kind") or "dependency"),
                _cell(blocker.get("unblock_when") or "")))
    gated = [task for task in data["tasks"] if task.get("approval") or task.get("approvals")]
    if gated:
        lines += ["", "| Task | Approval for | Approved by | When |", "|---|---|---|---|"]
        for task in gated:
            approval = task.get("approval") or {}
            if approval.get("required"):
                lines.append("| {} | {} | {} | {} |".format(
                    _cell(task["id"]), _cell(approval["required"]), _cell(approval.get("granted_by") or "pending"),
                    _cell(approval.get("granted_at") or "")))
            for item in task.get("approvals", []):
                if item.get("for") != approval.get("required"):
                    lines.append("| {} | {} | {} | {} |".format(_cell(task["id"]), _cell(item.get("for", "")),
                                                               _cell(item.get("by", "")), _cell(item.get("at", ""))))
    return "\n".join(lines) + "\n"


def render_list(data: Dict[str, Any], status: Optional[str] = None) -> str:
    rows = [task for task in data["tasks"] if status is None or task["status"] == status]
    if not rows:
        return "No tasks{}.\n".format(" with status " + status if status else "")
    widths = (max(2, max(len(task["id"]) for task in rows)), 11, 3)
    lines = ["{:<{w0}}  {:<{w1}}  {:<{w2}}  {}".format("ID", "Status", "Pri", "Task", w0=widths[0], w1=widths[1],
                                                        w2=widths[2])]
    for task in rows:
        deps = " (after {})".format(", ".join(task["depends_on"])) if task.get("depends_on") else ""
        gate = " [needs approval]" if approval_pending(task) else ""
        lines.append("{:<{w0}}  {:<{w1}}  {:<{w2}}  {}{}{}".format(
            task["id"], task["status"], task["priority"], task["title"], deps, gate, w0=widths[0], w1=widths[1],
            w2=widths[2]))
    counts = {name: sum(1 for task in data["tasks"] if task["status"] == name) for name in STATUSES}
    lines.append("")
    lines.append(", ".join("{} {}".format(count, name) for name, count in counts.items() if count))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _required_text(value: Optional[str], option: str) -> str:
    if value is None or not value.strip():
        raise LedgerError("{} must not be empty".format(option), code=2)
    return value.strip()


def cmd_init(path: Path, args: argparse.Namespace) -> str:
    with ledger_lock(path):
        if path.exists():
            raise LedgerError("{} already exists; refusing to overwrite it".format(path))
        stamp = now()
        save_ledger(path, {"schema": SCHEMA, "project": args.project, "created_at": stamp, "updated_at": stamp,
                           "tasks": []})
    return "Created ledger {} for project '{}'".format(path, args.project)


def cmd_add(path: Path, args: argparse.Namespace) -> str:
    if not ID_RE.match(args.id):
        raise LedgerError("task id must start with a letter and use letters, digits, '.', '_' or '-' (max 32)",
                          code=2)
    title = _required_text(args.title, "--title")
    expect = _required_text(args.expect, "--expect")
    verify = _required_text(args.verify, "--verify")
    with editing(path) as data:
        if any(task["id"] == args.id for task in data["tasks"]):
            raise LedgerError("task '{}' already exists".format(args.id))
        known = {task["id"] for task in data["tasks"]}
        missing = [dep for dep in args.depends if dep not in known]
        if missing:
            raise LedgerError("unknown dependencies: {}; add those tasks first".format(", ".join(missing)))
        task = {
            "id": args.id, "title": title, "priority": args.priority, "depends_on": list(args.depends),
            "status": "not-started", "expected_result": expect, "verification_method": verify,
            "evidence": None, "blocker": None, "checks": [], "approvals": [], "notes": [],
            "approval": ({"required": args.needs_approval.strip(), "granted_by": None, "granted_at": None}
                         if args.needs_approval and args.needs_approval.strip() else None),
            "history": [{"at": now(), "from": None, "to": "not-started", "note": "created"}],
        }
        if args.note:
            task["notes"].append(args.note)
        data["tasks"].append(task)
    gate = " (needs approval before it starts)" if task["approval"] else ""
    return "Added {} ({}): {}{}".format(args.id, args.priority, title, gate)


def cmd_start(path: Path, args: argparse.Namespace) -> str:
    with editing(path) as data:
        task = find_task(data, args.id)
        if task["status"] == "blocked" and (task.get("blocker") or {}).get("kind") == "approval":
            raise LedgerError("{}: blocked pending approval ({}); after the owner approves, run 'approve {} --by "
                              "NAME' or 'unblock {} --approved-by NAME'".format(
                                  task["id"], task["blocker"]["reason"], task["id"], task["id"]))
        if approval_pending(task):
            raise LedgerError("{}: needs approval before it starts: {}; after the owner approves, record it with "
                              "'approve {} --by NAME'".format(task["id"], task["approval"]["required"], task["id"]))
        pending = unfinished_dependencies(data, task)
        note = "started" if task["status"] != "failed" else "rework after a failed check"
        if pending:
            if not args.force:
                raise LedgerError("{}: dependencies {} are not finished; finish them, record a blocker with 'block', "
                                  "or use --force".format(task["id"], ", ".join(pending)))
            note = "started with unfinished dependencies: {}".format(", ".join(pending))
        previous = task["status"]
        transition(task, "in-progress", note)
        task["blocker"] = None
    return "{}: {} -> in-progress{}".format(task["id"], previous, " (forced)" if pending else "")


def cmd_block(path: Path, args: argparse.Namespace) -> str:
    reason = _required_text(args.reason, "--reason")
    with editing(path) as data:
        task = find_task(data, args.id)
        previous = task["status"]
        kind = "approval" if args.needs_approval else "dependency"
        transition(task, "blocked", ("awaiting approval: " if args.needs_approval else "") + reason)
        task["blocker"] = {"reason": reason, "kind": kind, "previous": previous,
                           "unblock_when": (args.unblock or "").strip() or None}
    return "{}: {} -> blocked ({}{})".format(task["id"], previous, "approval: " if args.needs_approval else "", reason)


def _lift_block(task: Dict[str, Any], approved_by: Optional[str], note: str) -> str:
    blocker = task.get("blocker") or {}
    target = blocker.get("previous") or previous_status_from_history(task)
    if target not in STATUSES or target == "blocked":
        target = "not-started"
    if blocker.get("kind") == "approval":
        if not approved_by:
            raise LedgerError("{}: blocked pending approval ({}); pass --approved-by with the name of the person who "
                              "approved".format(task["id"], blocker.get("reason")))
        task["approvals"].append({"at": now(), "by": approved_by, "for": blocker.get("reason"), "note": note or None})
    task["status"] = target
    task["blocker"] = None
    text = "unblocked" + (": " + note if note else "")
    if approved_by:
        text = "approved by {}; {}".format(approved_by, text)
    record(task, "blocked", target, text, approved_by)
    return target


def cmd_unblock(path: Path, args: argparse.Namespace) -> str:
    with editing(path) as data:
        task = find_task(data, args.id)
        if task["status"] != "blocked":
            raise LedgerError("{}: is {}, not blocked".format(task["id"], task["status"]))
        approved_by = (args.approved_by or "").strip() or None
        target = _lift_block(task, approved_by, (args.note or "").strip())
    return "{}: blocked -> {}".format(task["id"], target)


def cmd_approve(path: Path, args: argparse.Namespace) -> str:
    by = _required_text(args.by, "--by")
    note = (args.note or "").strip()
    actions = []
    with editing(path) as data:
        task = find_task(data, args.id)
        if approval_pending(task):
            task["approval"]["granted_by"] = by
            task["approval"]["granted_at"] = now()
            if note:
                task["approval"]["note"] = note
            task["approvals"].append({"at": task["approval"]["granted_at"], "by": by,
                                      "for": task["approval"]["required"], "note": note or None})
            record(task, task["status"], task["status"], "approved by {}: {}".format(by, task["approval"]["required"]),
                   by)
            actions.append("approval recorded")
        if task["status"] == "blocked" and (task.get("blocker") or {}).get("kind") == "approval":
            target = _lift_block(task, by, note)
            actions.append("blocked -> {}".format(target))
        if not actions:
            raise LedgerError("{}: nothing awaits approval on this task".format(task["id"]))
    return "{}: {} (by {})".format(task["id"], ", ".join(actions), by)


def cmd_complete(path: Path, args: argparse.Namespace) -> str:
    with editing(path) as data:
        task = find_task(data, args.id)
        transition(task, "completed", args.note or "completed")
        if args.note:
            task["notes"].append(args.note)
    return "{}: in-progress -> completed (run its verification next: {})".format(task["id"],
                                                                               task["verification_method"])


def cmd_verify(path: Path, args: argparse.Namespace) -> str:
    evidence = (args.evidence or "").strip()
    override = (args.override or "").strip()
    with editing(path) as data:
        task = find_task(data, args.id)
        if task["status"] != "completed":
            transition(task, "verified")  # raises with a helpful message
        problem = evidence_problem(evidence)
        if problem:
            raise LedgerError("{}: {}".format(task["id"], problem))
        issues = evidence_warnings(evidence, task["verification_method"])
        if issues and not override:
            advice = ("record a failed check with 'fail {} --evidence ...'".format(task["id"])
                      if failure_markers(evidence) else "rewrite the evidence with what the check showed")
            raise LedgerError("{}: evidence refused because {}. Either {}, or, if the evidence is genuine, pass "
                              "--override 'why it is acceptable'".format(task["id"], "; ".join(issues), advice))
        note = "evidence: " + evidence
        if issues:
            note += " (override: {}; waived: {})".format(override, "; ".join(issues))
        transition(task, "verified", note)
        task["evidence"] = evidence
        check = {"at": now(), "result": "pass", "evidence": evidence}
        if issues:
            check["override"] = override
        task["checks"].append(check)
    return "{}: completed -> verified{}".format(task["id"], " (override recorded)" if issues else "")


def cmd_fail(path: Path, args: argparse.Namespace) -> str:
    evidence = _required_text(args.evidence, "--evidence")
    if len(evidence) < MIN_EVIDENCE_CHARS:
        raise LedgerError("evidence is too short to say which check failed and how")
    with editing(path) as data:
        task = find_task(data, args.id)
        previous = task["status"]
        transition(task, "failed", "check failed: " + evidence)
        task["checks"].append({"at": now(), "result": "fail", "evidence": evidence})
        task["evidence"] = None
    return "{}: {} -> failed (fix it, then 'start', 'complete' and 'verify' again)".format(task["id"], previous)


def cmd_reopen(path: Path, args: argparse.Namespace) -> str:
    reason = _required_text(args.reason, "--reason")
    with editing(path) as data:
        task = find_task(data, args.id)
        if task["status"] not in FINISHED:
            raise LedgerError("{}: only completed or verified tasks can be reopened (it is {})".format(
                task["id"], task["status"]))
        previous = task["status"]
        note = "reopened: {}".format(reason)
        if task.get("evidence"):
            note += " (previous evidence: {})".format(task["evidence"])
        task["status"] = "in-progress"
        task["evidence"] = None
        record(task, previous, "in-progress", note)
    return "{}: {} -> in-progress ({})".format(task["id"], previous, reason)


def cmd_list(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    if args.json:
        tasks = [task for task in data["tasks"] if args.status is None or task["status"] == args.status]
        return json.dumps(tasks, indent=2, ensure_ascii=False)
    return render_list(data, args.status).rstrip("\n")


def cmd_show(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    task = find_task(data, args.id)
    if args.json:
        return json.dumps(task, indent=2, ensure_ascii=False)
    lines = ["{}: {}".format(task["id"], task["title"]),
             "  status:       {}".format(STATUS_LABELS[task["status"]]),
             "  priority:     {}".format(task["priority"]),
             "  depends on:   {}".format(", ".join(task.get("depends_on", [])) or "none"),
             "  expected:     {}".format(task["expected_result"]),
             "  verification: {}".format(task["verification_method"]),
             "  evidence:     {}".format(task.get("evidence") or "none")]
    approval = task.get("approval")
    if approval and approval.get("required"):
        lines.append("  approval:     {} ({})".format(
            approval["required"], "approved by " + approval["granted_by"] if approval.get("granted_by") else "pending"))
    if task.get("blocker"):
        lines.append("  blocker:      {} [{}] (unblocks when: {})".format(
            task["blocker"]["reason"], task["blocker"].get("kind") or "dependency",
            task["blocker"].get("unblock_when") or "unspecified"))
    for check in task.get("checks", []):
        lines.append("  check:        {} {}: {}".format(check.get("at") or "?", check.get("result"),
                                                         check.get("evidence")))
    for note in task.get("notes", []):
        lines.append("  note:         {}".format(note))
    lines.append("  history:")
    for entry in task.get("history", []):
        lines.append("    {}  {} -> {}  {}".format(entry["at"], entry.get("from") or "-", entry["to"],
                                                    entry.get("note") or ""))
    return "\n".join(lines)


def cmd_render(path: Path, args: argparse.Namespace) -> str:
    return render_markdown(load_ledger(path)).rstrip("\n")


def cmd_check(path: Path, args: argparse.Namespace) -> Tuple[str, int]:
    data = load_ledger(path)
    errors, warnings = check_ledger(data)
    if args.json:
        return json.dumps({"ledger": str(path), "ok": not errors, "errors": errors, "warnings": warnings},
                          indent=2), (1 if errors else 0)
    lines = ["error: " + item for item in errors] + ["warning: " + item for item in warnings]
    lines.append("Ledger {}: {} ({} tasks, {} errors, {} warnings)".format(
        path, "OK" if not errors else "PROBLEMS FOUND", len(data["tasks"]), len(errors), len(warnings)))
    return "\n".join(lines), (1 if errors else 0)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--file", default=argparse.SUPPRESS, help="ledger path (default: .mych/tasks.json)")
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="JSON output (list, show, check)")
    parser = argparse.ArgumentParser(
        description="Task ledger with enforced statuses: verified requires evidence from a check that ran.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  task-ledger.py init --project 'Clinic booking'\n"
            "  task-ledger.py add T1 --title 'Data model' --expect 'Tables exist' --verify 'pytest tests/models'\n"
            "  task-ledger.py add T9 --title 'Deploy' --expect 'Live' --verify 'smoke test' "
            "--needs-approval 'deploy to production'\n"
            "  task-ledger.py start T1\n"
            "  task-ledger.py complete T1\n"
            "  task-ledger.py verify T1 --evidence 'pytest tests/models: 12 passed'\n"
            "  task-ledger.py fail T1 --evidence 'pytest tests/models: 2 failed (test_slots)'\n"
            "  task-ledger.py approve T9 --by 'Kim'\n"
            "  task-ledger.py render\n"
            "\nexit status: 0 success, 1 rule violation or failed check, 2 usage or file error"
        ),
    )
    parser.add_argument("--file", default=None, help="ledger path (default: .mych/tasks.json)")
    parser.add_argument("--json", action="store_true", default=False, help="JSON output (list, show, check)")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    p = sub.add_parser("init", parents=[common], help="create a new ledger")
    p.add_argument("--project", required=True, help="project name")

    p = sub.add_parser("add", parents=[common], help="add a task")
    p.add_argument("id", help="task id, for example T1")
    p.add_argument("--title", required=True, help="what will exist when the task is done")
    p.add_argument("--priority", choices=PRIORITIES, default=DEFAULT_PRIORITY, help="P0 to P3 (default: P2)")
    p.add_argument("--depends", nargs="*", default=[], metavar="ID", help="ids of tasks this one depends on")
    p.add_argument("--expect", required=True, help="observable expected result")
    p.add_argument("--verify", required=True, help="verification method: the check that proves it")
    p.add_argument("--needs-approval", metavar="ACTION",
                   help="the gated action this task performs; the task cannot start until 'approve' records who "
                        "approved it")
    p.add_argument("--note", help="optional note")

    p = sub.add_parser("start", parents=[common], help="move a task to in-progress (also after a failed check)")
    p.add_argument("id")
    p.add_argument("--force", action="store_true", help="start despite unfinished dependencies (recorded)")

    p = sub.add_parser("block", parents=[common], help="mark a task blocked")
    p.add_argument("id")
    p.add_argument("--reason", required=True, help="what blocks it")
    p.add_argument("--unblock", help="what would unblock it")
    p.add_argument("--needs-approval", action="store_true",
                   help="the blocker is an approval; lifting it requires the approver's name")

    p = sub.add_parser("unblock", parents=[common], help="lift a block and restore the earlier status")
    p.add_argument("id")
    p.add_argument("--approved-by", help="who approved (required for approval blocks)")
    p.add_argument("--note", help="what changed")

    p = sub.add_parser("approve", parents=[common],
                       help="record the owner's approval for a task (only after they actually gave it)")
    p.add_argument("id")
    p.add_argument("--by", required=True, help="name of the person who approved")
    p.add_argument("--note", help="conditions or scope of the approval")

    p = sub.add_parser("complete", parents=[common], help="mark an in-progress task completed")
    p.add_argument("id")
    p.add_argument("--note", help="optional note")

    p = sub.add_parser("verify", parents=[common], help="mark a completed task verified, with evidence")
    p.add_argument("id")
    p.add_argument("--evidence", required=True, help="which check ran and what it showed")
    p.add_argument("--override", metavar="REASON",
                   help="accept evidence that trips a heuristic rule (restated, failure words, not concrete); the "
                        "reason is recorded")

    p = sub.add_parser("fail", parents=[common], help="record a failed check; the task moves to failed")
    p.add_argument("id")
    p.add_argument("--evidence", required=True, help="which check ran and how it failed")

    p = sub.add_parser("reopen", parents=[common], help="move a completed or verified task back to in-progress")
    p.add_argument("id")
    p.add_argument("--reason", required=True, help="why it is reopened")

    p = sub.add_parser("list", parents=[common], help="list tasks")
    p.add_argument("--status", choices=STATUSES, help="only tasks with this status")

    p = sub.add_parser("show", parents=[common], help="show one task with its checks and history")
    p.add_argument("id")

    sub.add_parser("render", parents=[common], help="print the ledger as a Markdown task plan")
    sub.add_parser("check", parents=[common], help="check ledger integrity; exit 1 on errors")
    return parser


COMMANDS = {
    "init": cmd_init, "add": cmd_add, "start": cmd_start, "block": cmd_block, "unblock": cmd_unblock,
    "approve": cmd_approve, "complete": cmd_complete, "verify": cmd_verify, "fail": cmd_fail,
    "reopen": cmd_reopen, "list": cmd_list, "show": cmd_show, "render": cmd_render,
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.file).expanduser() if args.file else DEFAULT_LEDGER
    try:
        if args.command == "check":
            output, status = cmd_check(path, args)
            print(output)
            return status
        print(COMMANDS[args.command](path, args))
        return 0
    except LedgerError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
