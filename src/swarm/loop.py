"""For-loop: claim beads one by one until the queue is empty."""

from collections.abc import Callable
from pathlib import Path

from swarm import checkpoint, queue, worker


def run(
    run_task: Callable[..., str] = worker.run_task,
    checkpoint_root: Path | None = None,
) -> list[str]:
    """Claim each ready bead in turn, closing it on success."""
    results = []
    while (task := queue.claim_next()) is not None:
        task_folder = checkpoint.task_dir(checkpoint_root, task.title) if checkpoint_root else None
        if task_folder is not None and checkpoint.has_result(task_folder):
            queue.close(task)
            continue
        try:
            if task_folder is None:
                results.append(run_task(task.title))
            else:
                try:
                    results.append(run_task(task.title, checkpoint_dir=task_folder))
                except TypeError:
                    results.append(run_task(task.title))
        except Exception:
            queue.reopen(task)
            raise
        queue.close(task)
    return results
