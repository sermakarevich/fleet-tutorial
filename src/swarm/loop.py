"""For-loop: run tasks one by one until the list is empty."""

from collections.abc import Callable
from pathlib import Path

from swarm import todo, worker


def run(todo_file: Path, run_task: Callable[[str], str] = worker.run_task) -> list[str]:
    """Run each item in turn, removing it when done, return all results."""
    results = []
    while (task := todo.next_task(todo_file)) is not None:
        results.append(run_task(task))
        todo.mark_done(todo_file, task)
    return results
