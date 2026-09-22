"""Entry point of the swarm runner: demo a crash and a resume."""

import tempfile
from functools import partial
from pathlib import Path

from swarm import checkpoint, loop, worker

DEMO_TASKS = ["summarise the inbox", "draft the status update"]


def demo_harness(prompt: str) -> str:
    """Canned stand-in for the headless harness, so the demo runs offline."""
    first_line = prompt.splitlines()[0]
    return f"demo result for: {first_line.split(': ', 1)[-1]}"


class CrashingHarness:
    """Fake harness that answers once and then crashes like a dropped session."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("simulated crash: network dropped")
        return demo_harness(prompt)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "checkpoints"
        todo_file = Path(tmp) / "TODO.md"
        todo_file.write_text("\n".join(DEMO_TASKS) + "\n")
        crashed = partial(worker.run_task, harness=CrashingHarness())
        try:
            loop.run(todo_file, crashed, checkpoint_root=root)
        except RuntimeError as crash:
            print(f"crashed: {crash}")
        stuck = checkpoint.task_dir(root, DEMO_TASKS[1])
        print(f"checkpoint: {checkpoint.read_checkpoint(stuck)}")
        print("resuming from checkpoint...")
        steady = partial(worker.run_task, harness=demo_harness)
        results = loop.run(todo_file, steady, checkpoint_root=root)
        print(f"task: {DEMO_TASKS[1]}\nresult: {results[0]}")
        print("done: 1 resumed, 1 reused from checkpoint")


if __name__ == "__main__":
    main()
