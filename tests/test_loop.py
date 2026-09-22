"""For-loop and worker: tasks run in order over a faked harness boundary."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from swarm import loop, worker


@pytest.fixture
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        seen.append(cmd[-1])
        return SimpleNamespace(stdout=f"result for {cmd[-1]}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


def test_build_prompt_names_the_task() -> None:
    assert "wipe the board" in worker.build_prompt("wipe the board")


def test_run_task_calls_harness_cli(fake_harness: list[str]) -> None:
    result = worker.run_task("wipe the board")
    assert "wipe the board" in result
    assert any("wipe the board" in prompt for prompt in fake_harness)


def test_loop_runs_every_task_in_order(tmp_path: Path, fake_harness: list[str]) -> None:
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("first\nsecond\n")
    results = loop.run(todo_file)
    assert len(results) == 2
    assert "first" in results[0]
    assert "second" in results[1]
    assert todo_file.read_text() == ""
    assert len(fake_harness) == 2


def test_loop_empty_list_runs_nothing(tmp_path: Path, fake_harness: list[str]) -> None:
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("")
    assert loop.run(todo_file) == []
    assert fake_harness == []
