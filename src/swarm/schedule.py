"""Cron schedules: open a bead or start a workflow run when due."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from swarm import queue, workflows

TASK = "task"
WORKFLOW = "workflow"


@dataclass(frozen=True)
class Schedule:
    name: str
    cron: str
    kind: str
    target: str


def load(path: Path) -> list[Schedule]:
    """Read schedules from a text file, one per line.

    Each line is `name | cron | task: title` or `name | cron | workflow: path`.
    """
    found: list[Schedule] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        name, bar, rest = line.partition("|")
        cron, bar2, action = rest.partition("|")
        if not bar or not bar2:
            raise ValueError(f"bad schedule line {line!r} in {path}")
        kind, _, target = action.partition(":")
        kind = kind.strip()
        if kind not in (TASK, WORKFLOW):
            raise ValueError(f"bad schedule kind {kind!r} in {path}")
        entry = Schedule(name=name.strip(), cron=cron.strip(), kind=kind, target=target.strip())
        _fields(entry.cron, path)
        found.append(entry)
    return found


def _fields(cron: str, path: Path) -> list[str]:
    fields = cron.split()
    if len(fields) != 5:
        raise ValueError(f"bad cron {cron!r} in {path}")
    return fields


def _match(field: str, value: int) -> bool:
    if field == "*":
        return True
    if field.startswith("*/"):
        return value % int(field[2:]) == 0
    return value == int(field)


def matches(cron: str, now: datetime) -> bool:
    """True when a cron expression fires at `now`.

    Fields are minute, hour, day of month, month, day of week. Each field is
    a star, a step such as every fifteen minutes, or one plain number.
    """
    minute, hour, day, month, weekday = cron.split()
    values = (now.minute, now.hour, now.day, now.month, now.isoweekday() % 7)
    fields = (minute, hour, day, month, weekday)
    return all(_match(field, value) for field, value in zip(fields, values, strict=True))


def slot(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M")


def tick(schedules: list[Schedule], now: datetime, fired: dict[str, str]) -> list[Schedule]:
    """Due schedules at `now`: cron matches and this minute slot never fired."""
    return [
        entry
        for entry in schedules
        if matches(entry.cron, now) and fired.get(entry.name) != slot(now)
    ]


def fire(
    entry: Schedule,
    now: datetime,
    fired: dict[str, str],
    opener: Callable[..., str] = queue.create,
    starter: Callable[[Path], dict[str, str]] = workflows.start,
) -> str | dict[str, str]:
    """Open one bead or start one workflow run, then mark this slot fired."""
    if entry.kind == WORKFLOW:
        run = starter(Path(entry.target))
    else:
        run = opener(entry.target)
    fired[entry.name] = slot(now)
    return run
