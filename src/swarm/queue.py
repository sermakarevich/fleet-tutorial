"""Beads queue: the only module that talks to the `bd` task tool."""

import json
import subprocess
from dataclasses import dataclass

BD_BIN = "bd"


@dataclass(frozen=True)
class Task:
    bead_id: str
    title: str


def _run_bd(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run one `bd` command, raising when beads reports a failure."""
    return subprocess.run([BD_BIN, *args], capture_output=True, text=True, check=True)


def _tasks_from(stdout: str) -> list[Task]:
    """Bead rows parsed from one `bd --json` answer."""
    rows = json.loads(stdout or "[]")
    if isinstance(rows, dict):
        rows = rows.get("data", [])
    return [
        Task(bead_id=row["id"], title=str(row.get("title") or row["id"]))
        for row in rows
        if isinstance(row, dict) and row.get("id")
    ]


def list_ready() -> list[Task]:
    """Ready beads: open tasks whose dependencies already closed."""
    done = _run_bd(["ready", "--json"])
    return _tasks_from(done.stdout)


def list_blocked() -> list[Task]:
    """Blocked beads: parked for a human, each one event for a trigger."""
    done = _run_bd(["blocked", "--json"])
    return _tasks_from(done.stdout)


def create(title: str, deps: tuple[str, ...] = ()) -> str:
    """Open one bead, blocked on `deps` until those beads close. Return its id."""
    args = ["create", title]
    if deps:
        args += ["--deps", ",".join(deps)]
    args += ["--silent"]
    done = _run_bd(args)
    return done.stdout.strip()


def state(bead_id: str) -> str:
    """Current status word of one bead: open, in_progress, closed, or blocked."""
    done = _run_bd(["show", bead_id, "--json"])
    rows = json.loads(done.stdout or "[]")
    if rows and isinstance(rows[0], dict):
        return str(rows[0].get("status") or "open")
    return "open"


def claim_next() -> Task | None:
    """Claim one ready bead, or None when the queue is empty.

    Beads grants each claim to one caller only. A lost race raises here,
    so the loop just tries the next bead instead of running one twice.
    """
    for task in list_ready():
        try:
            _run_bd(["update", task.bead_id, "--claim"])
        except subprocess.CalledProcessError:
            continue
        return task
    return None


def close(task: Task) -> None:
    """Mark a finished bead done."""
    _run_bd(["close", task.bead_id])


def reopen(task: Task) -> None:
    """Send a failed bead back to the queue for the next run."""
    _run_bd(["update", task.bead_id, "--status", "open"])


def block(task: Task, reason: str = "") -> None:
    """Park an exhausted bead as blocked with the reason, for a human."""
    args = ["update", task.bead_id, "--status", "blocked"]
    if reason:
        args += ["--notes", reason]
    _run_bd(args)
