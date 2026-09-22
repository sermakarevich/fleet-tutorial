"""Entry point of the swarm runner: demo the TODO list and for-loop."""

import tempfile
from functools import partial
from pathlib import Path

from swarm import loop, worker

DEMO_TASKS = ["summarise the inbox", "draft the status update"]


def demo_harness(prompt: str) -> str:
    """Canned stand-in for the headless harness, so the demo runs offline."""
    return f"demo result for: {prompt.split(': ', 1)[-1]}"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        todo_file = Path(tmp) / "TODO.md"
        todo_file.write_text("\n".join(DEMO_TASKS) + "\n")
        run = partial(worker.run_task, harness=demo_harness)
        for task, result in zip(DEMO_TASKS, loop.run(todo_file, run), strict=True):
            print(f"task: {task}\nresult: {result}")
        print(f"done: {len(DEMO_TASKS)} tasks")


if __name__ == "__main__":
    main()
