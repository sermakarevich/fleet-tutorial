"""Schedules: due entries fire once per slot, the rest stay quiet."""

from datetime import datetime
from pathlib import Path

import fake_beads
import pytest

from swarm import queue, schedule

NOW = datetime(2026, 9, 22, 9, 30)
OTHER_MINUTE = (NOW.minute + 1) % 60


def write_sched(tmp_path: Path, lines: str) -> Path:
    path = tmp_path / "sched.txt"
    path.write_text(lines)
    return path


def test_due_schedule_fires_once_per_slot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    path = write_sched(tmp_path, "morning report | * * * * * | task: write daily report\n")
    entries = schedule.load(path)
    fired: dict[str, str] = {}

    due = schedule.tick(entries, NOW, fired)
    assert [entry.name for entry in due] == ["morning report"]
    bead = schedule.fire(due[0], NOW, fired)

    assert isinstance(bead, str)
    assert [task.title for task in queue.list_ready()] == ["write daily report"]
    assert schedule.tick(entries, NOW, fired) == []


def test_not_due_schedule_stays_quiet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    path = write_sched(tmp_path, f"later job | {OTHER_MINUTE} * * * * | task: write later report\n")
    entries = schedule.load(path)

    assert schedule.tick(entries, NOW, {}) == []
    assert queue.list_ready() == []


def test_firing_starts_a_workflow_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    flow = tmp_path / "flow.txt"
    flow.write_text("write spec\nwrite code: write spec\n")
    path = write_sched(tmp_path, f"spec chain | * * * * * | workflow: {flow}\n")
    entries = schedule.load(path)
    fired: dict[str, str] = {}

    run = schedule.fire(entries[0], NOW, fired)

    assert isinstance(run, dict)
    assert sorted(run) == ["write code", "write spec"]
    assert [task.title for task in queue.list_ready()] == ["write spec"]
    assert fired == {"spec chain": schedule.slot(NOW)}


def test_next_slot_fires_again(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    path = write_sched(tmp_path, "morning report | * * * * * | task: write daily report\n")
    entries = schedule.load(path)
    fired: dict[str, str] = {}
    schedule.fire(entries[0], NOW, fired)

    later = datetime(2026, 9, 22, 9, 31)
    assert [entry.name for entry in schedule.tick(entries, later, fired)] == ["morning report"]


def test_step_and_plain_values_match(tmp_path: Path) -> None:
    assert schedule.matches("*/15 * * * *", datetime(2026, 9, 22, 9, 30))
    assert not schedule.matches("*/15 * * * *", datetime(2026, 9, 22, 9, 31))
    assert schedule.matches(f"{NOW.minute} * * * *", NOW)
    assert not schedule.matches(f"{OTHER_MINUTE} * * * *", NOW)


def test_bad_line_fails_fast(tmp_path: Path) -> None:
    path = write_sched(tmp_path, "morning report * * * * *\n")

    with pytest.raises(ValueError, match="bad schedule"):
        schedule.load(path)
