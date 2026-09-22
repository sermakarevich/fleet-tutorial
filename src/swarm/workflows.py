"""Saved graphs of steps: open one bead per step, later steps wait on parents."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from swarm import queue

DONE = "done"
RUNNING = "running"
WAITING = "waiting"
BLOCKED = "blocked"
CLOSED = "closed"
IN_PROGRESS = "in_progress"
OPEN = "open"
BLOCKED_STATE = "blocked"


@dataclass(frozen=True)
class Step:
    name: str
    deps: tuple[str, ...] = ()


def load(path: Path) -> list[Step]:
    """Read workflow steps from a text file, one step per line.

    Each line is `name` or `name: dep1, dep2`. Names before the colon run
    first; names after it wait until those steps close.
    """
    steps: list[Step] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        name, _, rest = line.partition(":")
        deps = tuple(part.strip() for part in rest.split(",") if part.strip())
        steps.append(Step(name=name.strip(), deps=deps))
    known = {step.name for step in steps}
    for step in steps:
        for dep in step.deps:
            if dep not in known:
                raise ValueError(f"unknown step {dep!r} in {path}")
    return steps


def start(path: Path, opener: Callable[..., str] = queue.create) -> dict[str, str]:
    """Open one bead per workflow step, in file order. Return step names to ids."""
    ids: dict[str, str] = {}
    for step in load(path):
        ids[step.name] = opener(step.name, tuple(ids[dep] for dep in step.deps))
    return ids


def run_status(states: Mapping[str, str]) -> str:
    """Whole-run state derived from per-step bead states, never stored by hand."""
    if states and all(state == CLOSED for state in states.values()):
        return DONE
    if any(state == BLOCKED_STATE for state in states.values()):
        return BLOCKED
    if any(state == IN_PROGRESS for state in states.values()):
        return RUNNING
    return WAITING
