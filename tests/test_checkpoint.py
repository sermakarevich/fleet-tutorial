"""Checkpoints: crash mid-task, resume from STATE.md, record RESULT.json."""

from functools import partial
from pathlib import Path

import pytest

from swarm import checkpoint, loop, worker


def test_task_dir_is_stable_and_file_safe(tmp_path: Path) -> None:
    first = checkpoint.task_dir(tmp_path, "Wipe the board!")
    assert first == checkpoint.task_dir(tmp_path, "Wipe the board!")
    assert first.parent == tmp_path
    assert first.name == "wipe_the_board"


def test_checkpoint_roundtrip_and_resume_states(tmp_path: Path) -> None:
    task_folder = checkpoint.task_dir(tmp_path, "wipe the board")
    assert checkpoint.read_checkpoint(task_folder) == ""
    assert not checkpoint.should_resume(task_folder)
    checkpoint.save_progress(task_folder, "step 1 of 2 done")
    assert checkpoint.read_checkpoint(task_folder) == "step 1 of 2 done"
    assert checkpoint.should_resume(task_folder)
    assert not checkpoint.has_result(task_folder)
    checkpoint.write_result(task_folder, "wipe the board", "all clean")
    assert checkpoint.has_result(task_folder)
    assert not checkpoint.should_resume(task_folder)
    assert checkpoint.read_result(task_folder) == "all clean"


def test_log_attempt_numbers_logs_in_order(tmp_path: Path) -> None:
    task_folder = checkpoint.task_dir(tmp_path, "wipe the board")
    first = checkpoint.log_attempt(task_folder, "try one")
    second = checkpoint.log_attempt(task_folder, "try two")
    assert first.name == "000.log"
    assert second.name == "001.log"
    assert "try two" in second.read_text()


def test_worker_resumes_from_checkpoint_after_crash(tmp_path: Path) -> None:
    task_folder = checkpoint.task_dir(tmp_path, "wipe the board")

    def crashing(prompt: str) -> str:
        raise RuntimeError("network dropped")

    with pytest.raises(RuntimeError, match="network dropped"):
        worker.run_task("wipe the board", harness=crashing, checkpoint_dir=task_folder)
    assert checkpoint.should_resume(task_folder)
    assert not checkpoint.has_result(task_folder)
    prior = checkpoint.read_checkpoint(task_folder)

    seen: list[str] = []

    def steady(prompt: str) -> str:
        seen.append(prompt)
        return "board wiped"

    result = worker.run_task("wipe the board", harness=steady, checkpoint_dir=task_folder)
    assert result == "board wiped"
    assert len(seen) == 1
    assert prior in seen[0]
    assert checkpoint.has_result(task_folder)
    assert checkpoint.read_result(task_folder) == "board wiped"


def test_loop_skips_finished_tasks_on_rerun(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    todo_file = tmp_path / "TODO.md"
    calls: list[str] = []

    def counting(prompt: str) -> str:
        calls.append(prompt)
        return f"result for {prompt}"

    run = partial(worker.run_task, harness=counting)
    todo_file.write_text("first\nsecond\n")
    assert loop.run(todo_file, run, checkpoint_root=root) != []
    first_pass = len(calls)
    assert first_pass == 2
    todo_file.write_text("first\nsecond\n")
    assert loop.run(todo_file, run, checkpoint_root=root) == []
    assert len(calls) == first_pass
