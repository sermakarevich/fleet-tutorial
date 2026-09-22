"""For-loop: run tasks one by one until the list is empty."""

from collections.abc import Callable
from pathlib import Path

from swarm import checkpoint, todo, worker


def run(
    todo_file: Path,
    run_task: Callable[..., str] = worker.run_task,
    checkpoint_root: Path | None = None,
) -> list[str]:
    """Run each item in turn, skipping tasks with a recorded result."""
    results = []
    while (task := todo.next_task(todo_file)) is not None:
        task_folder = checkpoint.task_dir(checkpoint_root, task) if checkpoint_root else None
        if task_folder is not None and checkpoint.has_result(task_folder):
            todo.mark_done(todo_file, task)
            continue
        if task_folder is None:
            results.append(run_task(task))
        else:
            try:
                results.append(run_task(task, checkpoint_dir=task_folder))
            except TypeError:
                results.append(run_task(task))
        todo.mark_done(todo_file, task)
    return results
