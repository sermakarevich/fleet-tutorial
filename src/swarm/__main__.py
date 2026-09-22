"""Entry point of the swarm runner: ask a human, get the answer, continue."""

import tempfile
from functools import partial
from pathlib import Path

from swarm import human, loop, worker

DEMO_TASK = "draft the launch note"
DEMO_ANSWER = "one line"


def demo_harness(prompt: str) -> str:
    """Canned stand-in for the headless harness, so the demo runs offline."""
    if "Human answer" in prompt:
        return f"demo result for {DEMO_TASK}: {DEMO_ANSWER}"
    return "ASK: one line or two?"


def canned_human(task_folder: Path, question: str, timeout: float = 1.0) -> str:
    """Canned stand-in for the human: print the question, answer at once."""
    print(f"question: {question}")
    human.answer_question(task_folder, DEMO_ANSWER)
    print(f"answer: {DEMO_ANSWER}")
    return DEMO_ANSWER


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "checkpoints"
        todo_file = Path(tmp) / "TODO.md"
        todo_file.write_text(DEMO_TASK + "\n")
        run = partial(worker.run_task, harness=demo_harness, ask=canned_human)
        results = loop.run(todo_file, run, checkpoint_root=root)
        print(f"result: {results[0]}")
        print("done: asked 1, answered 1, continued 1")


if __name__ == "__main__":
    main()
