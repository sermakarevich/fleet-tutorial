"""For-loop and worker: beads claimed in order over a faked harness boundary."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import fake_beads
import pytest

from swarm import loop, queue, worker


@pytest.fixture
def beads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return fake_beads.install(tmp_path, monkeypatch, {"bead-1": "first", "bead-2": "second"})


@pytest.fixture
def fake_harness(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    real_run = subprocess.run

    def fake_run(cmd: list[str], **kwargs: object) -> object:
        if cmd[0] == worker.HARNESS_BIN:
            seen.append(cmd[-1])
            return SimpleNamespace(stdout=f"result for {cmd[-1]}")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return seen


def test_build_prompt_names_the_task() -> None:
    assert "wipe the board" in worker.build_prompt("wipe the board")


def test_run_task_calls_harness_cli(fake_harness: list[str]) -> None:
    result = worker.run_task("wipe the board")
    assert "wipe the board" in result
    assert any("wipe the board" in prompt for prompt in fake_harness)


def test_loop_claims_every_bead_in_order(beads: Path, fake_harness: list[str]) -> None:
    results = loop.run()
    assert len(results) == 2
    assert "first" in results[0]
    assert "second" in results[1]
    assert queue.list_ready() == []
    assert len(fake_harness) == 2


def test_loop_empty_queue_runs_nothing(beads: Path, fake_harness: list[str]) -> None:
    for task in queue.list_ready():
        queue.close(task)
    assert loop.run() == []
    assert fake_harness == []


def test_loop_reopens_the_bead_on_failure(beads: Path) -> None:
    def failing(task: str) -> str:
        raise RuntimeError("network dropped")

    with pytest.raises(RuntimeError, match="network dropped"):
        loop.run(failing)
    assert [task.bead_id for task in queue.list_ready()] == ["bead-1", "bead-2"]
