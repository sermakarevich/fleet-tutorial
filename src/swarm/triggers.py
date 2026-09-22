"""Event triggers: open one investigator bead per blocked bead."""

from collections.abc import Callable
from pathlib import Path

from swarm import queue

PROMPT_FILE = Path(__file__).parent / "prompts" / "investigate_blocked.txt"
MAX_OPEN = 2


def build_prompt(bead_id: str, title: str) -> str:
    """Read-only analysis task naming the blocked bead and its title."""
    return PROMPT_FILE.read_text().format(bead_id=bead_id, title=title)


def due(blocked: list[queue.Task], seen: set[str]) -> list[queue.Task]:
    """Blocked beads never seen before, so each one fires exactly once."""
    return [task for task in blocked if task.bead_id not in seen]


def fire(
    task: queue.Task,
    seen: set[str],
    opener: Callable[..., str] = queue.create,
) -> str:
    """Open one investigator bead for a blocked bead, then remember it fired."""
    bead = opener(build_prompt(task.bead_id, task.title))
    seen.add(task.bead_id)
    return bead


def poll(
    seen: set[str],
    lister: Callable[[], list[queue.Task]] = queue.list_blocked,
    opener: Callable[..., str] = queue.create,
    limit: int = MAX_OPEN,
) -> list[str]:
    """Open investigators for new blocked beads, at most `limit` per poll."""
    found: list[str] = []
    for task in due(lister(), seen):
        if len(found) >= limit:
            break
        found.append(fire(task, seen, opener))
    return found
