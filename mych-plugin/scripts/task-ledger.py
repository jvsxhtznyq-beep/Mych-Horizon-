#!/usr/bin/env python3
"""Keep a project's task list in a JSON ledger that enforces status rules.

Statuses: not-started, in-progress, blocked, completed, verified.

Rules:
  - a task starts only when its dependencies are completed or verified
    (--force overrides, and the override is recorded in the task history);
  - only an in-progress task can be completed;
  - only a completed task can be verified, and verification requires
    substantive evidence: what check ran and what it showed;
  - blocking requires a reason; reopening requires a reason and clears
    the evidence, which stays in the history.

Usage:
  python3 task-ledger.py [--file LEDGER] COMMAND [options]

Commands: init, add, start, block, complete, verify, reopen, list, show,
render, check. 'task-ledger.py COMMAND --help' explains each. The ledger
defaults to .mych/tasks.json under the current directory and is written
atomically. Exit status: 0 success, 1 rule violation or failed check,
2 usage or file error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA = "mych-task-ledger/1"
STATUSES = ("not-started", "in-progress", "blocked", "completed", "verified")
STATUS_LABELS = {
    "not-started": "Not started", "in-progress": "In progress", "blocked": "Blocked",
    "completed": "Completed", "verified": "Verified",
}
PRIORITIES = ("P0", "P1", "P2", "P3")
DEFAULT_PRIORITY = "P2"
FINISHED = ("completed", "verified")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,31}$")
DEFAULT_LEDGER = Path(".mych") / "tasks.json"
# Permissions for a newly created ledger file (an existing ledger keeps its own).
LEDGER_FILE_MODE = 0o644
# Evidence must name a check and its result. Text shorter than this cannot,
# and these stand-ins describe a belief rather than an observation.
MIN_EVIDENCE_CHARS = 8
PLACEHOLDER_EVIDENCE = frozenset({
    "done", "ok", "okay", "yes", "pass", "passed", "passes", "works", "it works", "verified", "tested",
    "complete", "completed", "fixed", "good", "fine", "lgtm", "looks good", "todo", "tbd", "n/a", "na",
    "none", "-", "?", "see above", "as expected",
})
# Allowed transitions: target status -> statuses it may be reached from.
TRANSITIONS = {
    "in-progress": ("not-started", "blocked"),
    "blocked": ("not-started", "in-progress"),
    "completed": ("in-progress",),
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
# Storage
# ---------------------------------------------------------------------------

def load_ledger(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise LedgerError("no ledger at {}; create one with 'init --project NAME'".format(path), code=2)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerError("cannot read ledger {}: {}".format(path, exc), code=2) from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("tasks"), list):
        raise LedgerError("{} is not a {} ledger".format(path, SCHEMA), code=2)
    return data


def save_ledger(path: Path, data: Dict[str, Any]) -> None:
    """Write the ledger atomically: a crash leaves either the old or the new file."""
    data["updated_at"] = now()
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


def find_task(data: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    for task in data["tasks"]:
        if task.get("id") == task_id:
            return task
    known = ", ".join(task.get("id", "?") for task in data["tasks"]) or "none"
    raise LedgerError("unknown task '{}' (known: {})".format(task_id, known))


def transition(task: Dict[str, Any], target: str, note: str = "") -> None:
    current = task["status"]
    allowed = TRANSITIONS.get(target, ())
    if current not in allowed:
        hint = ""
        if target == "verified" and current == "in-progress":
            hint = "; complete it first, then verify it with evidence"
        elif target == "completed" and current in ("not-started", "blocked"):
            hint = "; start it first"
        raise LedgerError("{}: cannot move from {} to {}{}".format(task["id"], current, target, hint))
    task["status"] = target
    task["history"].append({"at": now(), "from": current, "to": target, "note": note})


def unfinished_dependencies(data: Dict[str, Any], task: Dict[str, Any]) -> List[str]:
    statuses = {item.get("id"): item.get("status") for item in data["tasks"]}
    return [dep for dep in task.get("depends_on", []) if statuses.get(dep) not in FINISHED]


def evidence_problem(text: Optional[str]) -> Optional[str]:
    if text is None or not text.strip():
        return "evidence is required: say which check ran and what it showed"
    normalized = re.sub(r"[\s.!]+$", "", text.strip().lower())
    if normalized in PLACEHOLDER_EVIDENCE:
        return "evidence {!r} states a belief, not an observation; name the check and its result".format(text.strip())
    if len(text.strip()) < MIN_EVIDENCE_CHARS:
        return "evidence is too short to name a check and its result"
    return None


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
        elif task.get("evidence"):
            warnings.append("{}: has evidence but is {}, not verified".format(label, status))
        if status == "blocked":
            blocker = task.get("blocker") or {}
            if not str(blocker.get("reason") or "").strip():
                errors.append("{}: blocked without a recorded reason".format(label))
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
        lines.append("| " + " | ".join(_cell(value) for value in (
            task["id"], task["title"], task["priority"], ", ".join(task.get("depends_on", [])) or "none",
            STATUS_LABELS.get(task["status"], task["status"]), task["expected_result"],
            task["verification_method"], task.get("evidence") or "")) + " |")
    blocked = [task for task in data["tasks"] if task["status"] == "blocked"]
    if blocked:
        lines += ["", "| Blocked task | Blocker | Unblocks when |", "|---|---|---|"]
        for task in blocked:
            blocker = task.get("blocker") or {}
            lines.append("| {} | {} | {} |".format(_cell(task["id"]), _cell(blocker.get("reason", "")),
                                                    _cell(blocker.get("unblock_when") or "")))
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
        lines.append("{:<{w0}}  {:<{w1}}  {:<{w2}}  {}{}".format(
            task["id"], task["status"], task["priority"], task["title"], deps, w0=widths[0], w1=widths[1],
            w2=widths[2]))
    counts = {name: sum(1 for task in data["tasks"] if task["status"] == name) for name in STATUSES}
    lines.append("")
    lines.append(", ".join("{} {}".format(count, name) for name, count in counts.items() if count))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(path: Path, args: argparse.Namespace) -> str:
    if path.exists():
        raise LedgerError("{} already exists; refusing to overwrite it".format(path))
    stamp = now()
    save_ledger(path, {"schema": SCHEMA, "project": args.project, "created_at": stamp, "updated_at": stamp,
                       "tasks": []})
    return "Created ledger {} for project '{}'".format(path, args.project)


def cmd_add(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    if not ID_RE.match(args.id):
        raise LedgerError("task id must start with a letter and use letters, digits, '.', '_' or '-' (max 32)",
                          code=2)
    if any(task["id"] == args.id for task in data["tasks"]):
        raise LedgerError("task '{}' already exists".format(args.id))
    for field_name, value in (("--title", args.title), ("--expect", args.expect), ("--verify", args.verify)):
        if not value or not value.strip():
            raise LedgerError("{} must not be empty".format(field_name), code=2)
    known = {task["id"] for task in data["tasks"]}
    missing = [dep for dep in args.depends if dep not in known]
    if missing:
        raise LedgerError("unknown dependencies: {}; add those tasks first".format(", ".join(missing)))
    task = {
        "id": args.id, "title": args.title.strip(), "priority": args.priority, "depends_on": list(args.depends),
        "status": "not-started", "expected_result": args.expect.strip(), "verification_method": args.verify.strip(),
        "evidence": None, "blocker": None, "notes": [],
        "history": [{"at": now(), "from": None, "to": "not-started", "note": "created"}],
    }
    if args.note:
        task["notes"].append(args.note)
    data["tasks"].append(task)
    save_ledger(path, data)
    return "Added {} ({}): {}".format(args.id, args.priority, task["title"])


def cmd_start(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    task = find_task(data, args.id)
    pending = unfinished_dependencies(data, task)
    note = "started"
    if pending:
        if not args.force:
            raise LedgerError("{}: dependencies {} are not finished; finish them, record a blocker with 'block', or "
                              "use --force".format(task["id"], ", ".join(pending)))
        note = "started with unfinished dependencies: {}".format(", ".join(pending))
    previous = task["status"]
    transition(task, "in-progress", note)
    task["blocker"] = None
    save_ledger(path, data)
    return "{}: {} -> in-progress{}".format(task["id"], previous, " (forced)" if pending else "")


def cmd_block(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    task = find_task(data, args.id)
    if not args.reason.strip():
        raise LedgerError("--reason must not be empty", code=2)
    previous = task["status"]
    transition(task, "blocked", args.reason.strip())
    task["blocker"] = {"reason": args.reason.strip(), "unblock_when": (args.unblock or "").strip() or None}
    save_ledger(path, data)
    return "{}: {} -> blocked ({})".format(task["id"], previous, args.reason.strip())


def cmd_complete(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    task = find_task(data, args.id)
    transition(task, "completed", args.note or "completed")
    if args.note:
        task["notes"].append(args.note)
    save_ledger(path, data)
    return "{}: in-progress -> completed (run its verification next: {})".format(task["id"],
                                                                               task["verification_method"])


def cmd_verify(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    task = find_task(data, args.id)
    if task["status"] != "completed":
        transition(task, "verified")  # raises with a helpful message
    problem = evidence_problem(args.evidence)
    if problem:
        raise LedgerError("{}: {}".format(task["id"], problem))
    transition(task, "verified", "evidence: " + args.evidence.strip())
    task["evidence"] = args.evidence.strip()
    save_ledger(path, data)
    return "{}: completed -> verified".format(task["id"])


def cmd_reopen(path: Path, args: argparse.Namespace) -> str:
    data = load_ledger(path)
    task = find_task(data, args.id)
    if task["status"] not in FINISHED:
        raise LedgerError("{}: only completed or verified tasks can be reopened (it is {})".format(
            task["id"], task["status"]))
    if not args.reason.strip():
        raise LedgerError("--reason must not be empty", code=2)
    previous = task["status"]
    note = "reopened: {}".format(args.reason.strip())
    if task.get("evidence"):
        note += " (previous evidence: {})".format(task["evidence"])
    task["status"] = "in-progress"
    task["evidence"] = None
    task["history"].append({"at": now(), "from": previous, "to": "in-progress", "note": note})
    save_ledger(path, data)
    return "{}: {} -> in-progress ({})".format(task["id"], previous, args.reason.strip())


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
    if task.get("blocker"):
        lines.append("  blocker:      {} (unblocks when: {})".format(
            task["blocker"]["reason"], task["blocker"].get("unblock_when") or "unspecified"))
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
            "  task-ledger.py start T1\n"
            "  task-ledger.py complete T1\n"
            "  task-ledger.py verify T1 --evidence 'pytest tests/models: 12 passed'\n"
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
    p.add_argument("--note", help="optional note")

    p = sub.add_parser("start", parents=[common], help="move a task to in-progress")
    p.add_argument("id")
    p.add_argument("--force", action="store_true", help="start despite unfinished dependencies (recorded)")

    p = sub.add_parser("block", parents=[common], help="mark a task blocked")
    p.add_argument("id")
    p.add_argument("--reason", required=True, help="what blocks it")
    p.add_argument("--unblock", help="what would unblock it")

    p = sub.add_parser("complete", parents=[common], help="mark an in-progress task completed")
    p.add_argument("id")
    p.add_argument("--note", help="optional note")

    p = sub.add_parser("verify", parents=[common], help="mark a completed task verified, with evidence")
    p.add_argument("id")
    p.add_argument("--evidence", required=True, help="which check ran and what it showed")

    p = sub.add_parser("reopen", parents=[common], help="move a completed or verified task back to in-progress")
    p.add_argument("id")
    p.add_argument("--reason", required=True, help="why it is reopened")

    p = sub.add_parser("list", parents=[common], help="list tasks")
    p.add_argument("--status", choices=STATUSES, help="only tasks with this status")

    p = sub.add_parser("show", parents=[common], help="show one task with its history")
    p.add_argument("id")

    sub.add_parser("render", parents=[common], help="print the ledger as a Markdown task plan")
    sub.add_parser("check", parents=[common], help="check ledger integrity; exit 1 on errors")
    return parser


COMMANDS = {
    "init": cmd_init, "add": cmd_add, "start": cmd_start, "block": cmd_block, "complete": cmd_complete,
    "verify": cmd_verify, "reopen": cmd_reopen, "list": cmd_list, "show": cmd_show, "render": cmd_render,
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
