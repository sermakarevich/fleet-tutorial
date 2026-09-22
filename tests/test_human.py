"""Human in the loop: ask mid-task, wait for the answer, resume re-asks."""

from functools import partial
from pathlib import Path

import pytest

from swarm import checkpoint, human, loop, worker


def test_question_answer_roundtrip_through_files(tmp_path: Path) -> None:
    assert human.read_question(tmp_path) == ""
    assert human.read_answer(tmp_path) is None
    assert not human.has_open_question(tmp_path)
    human.save_question(tmp_path, "one line or two?")
    assert human.read_question(tmp_path) == "one line or two?"
    assert human.has_open_question(tmp_path)
    with pytest.raises(TimeoutError):
        human.ask(tmp_path, "one line or two?", timeout=0.01)


def test_ask_returns_answer_written_to_file(tmp_path: Path) -> None:
    human.answer_question(tmp_path, "one line")
    assert human.ask(tmp_path, "one line or two?", timeout=1.0) == "one line"
    assert not human.has_open_question(tmp_path)


def test_ask_times_out_and_keeps_the_open_question(tmp_path: Path) -> None:
    with pytest.raises(TimeoutError):
        human.ask(tmp_path, "one line or two?", timeout=0.05)
    assert human.has_open_question(tmp_path)
    assert human.read_question(tmp_path) == "one line or two?"


def test_wants_input_detects_the_ask_marker() -> None:
    assert human.wants_input("ASK: one line or two?")
    assert human.take_question("ASK: one line or two?") == "one line or two?"
    assert not human.wants_input("here is the finished note")


def test_worker_pauses_for_answer_then_continues(tmp_path: Path) -> None:
    task_folder = checkpoint.task_dir(tmp_path, "draft the launch note")
    human.answer_question(task_folder, "one line")
    seen: list[str] = []

    def asking(prompt: str) -> str:
        seen.append(prompt)
        if len(seen) == 1:
            return "ASK: one line or two?"
        return "note drafted: one line"

    result = worker.run_task("draft the launch note", harness=asking, checkpoint_dir=task_folder)
    assert result == "note drafted: one line"
    assert "one line" in seen[1]
    assert checkpoint.read_result(task_folder) == "note drafted: one line"


def test_worker_timeout_leaves_question_for_resume(tmp_path: Path) -> None:
    task_folder = checkpoint.task_dir(tmp_path, "draft the launch note")
    seen: list[str] = []

    def asking(prompt: str) -> str:
        seen.append(prompt)
        return "ASK: one line or two?"

    with pytest.raises(TimeoutError):
        worker.run_task(
            "draft the launch note",
            harness=asking,
            checkpoint_dir=task_folder,
            ask_timeout=0.05,
        )
    assert human.has_open_question(task_folder)
    assert "waiting: one line or two?" in checkpoint.read_checkpoint(task_folder)
    assert not checkpoint.has_result(task_folder)

    def steady(prompt: str) -> str:
        seen.append(prompt)
        return "note drafted: one line"

    def late_answer(task_folder: Path, question: str, timeout: float = 1.0) -> str:
        assert question == "one line or two?"
        human.answer_question(task_folder, "one line")
        return "one line"

    resumed = worker.run_task(
        "draft the launch note", harness=steady, checkpoint_dir=task_folder, ask=late_answer
    )
    assert resumed == "note drafted: one line"
    assert "Human answer" in seen[-1]
    assert "one line" in seen[-1]
    assert checkpoint.read_result(task_folder) == "note drafted: one line"


def test_tutorial_demo_flow_through_loop(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("draft the launch note\n")

    def asking(prompt: str) -> str:
        if "Human answer" in prompt:
            return "note drafted: one line"
        return "ASK: one line or two?"

    def canned(task_folder: Path, question: str, timeout: float = 1.0) -> str:
        human.answer_question(task_folder, "one line")
        return "one line"

    run = partial(worker.run_task, harness=asking, ask=canned)
    assert loop.run(todo_file, run, checkpoint_root=root) == ["note drafted: one line"]
    assert todo_file.read_text() == ""
