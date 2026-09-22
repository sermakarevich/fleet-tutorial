"""Workflows: one bead per step, later steps wait, status derived from beads."""

from pathlib import Path

import fake_beads
import pytest

from swarm import queue, runner, workflows

FLOW = "write spec\nwrite code: write spec\ncheck work: write code\n"


@pytest.fixture
def flow(tmp_path: Path) -> Path:
    path = tmp_path / "flow.txt"
    path.write_text(FLOW)
    return path


def test_start_opens_three_beads_with_deps(
    flow: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})

    ids = workflows.start(flow)

    assert sorted(ids) == ["check work", "write code", "write spec"]
    assert [task.title for task in queue.list_ready()] == ["write spec"]


def test_stage_two_stays_unready_until_stage_one_closes(
    flow: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    ids = workflows.start(flow)

    first = queue.claim_next()
    assert first is not None and first.bead_id == ids["write spec"]
    assert queue.list_ready() == []
    queue.close(first)

    assert [task.bead_id for task in queue.list_ready()] == [ids["write code"]]


def test_run_status_comes_from_bead_states(
    flow: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    ids = workflows.start(flow)

    def states() -> dict[str, str]:
        return {name: queue.state(bead_id) for name, bead_id in ids.items()}

    assert workflows.run_status(states()) == workflows.WAITING
    task = queue.claim_next()
    assert task is not None
    assert workflows.run_status(states()) == workflows.RUNNING
    queue.close(task)
    assert workflows.run_status(states()) == workflows.WAITING


def test_supervisor_runs_steps_in_order(
    flow: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    ids = workflows.start(flow)
    ran: list[str] = []

    for _ in range(3):
        result = runner.supervise(lambda title: ran.append(title) or f"result for {title}")
        assert result is not None

    assert ran == ["write spec", "write code", "check work"]
    assert queue.list_ready() == []
    assert workflows.run_status({name: queue.state(bead) for name, bead in ids.items()}) == (
        workflows.DONE
    )


def test_blocked_step_blocks_the_run(
    flow: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    ids = workflows.start(flow)
    task = queue.claim_next()
    assert task is not None
    queue.block(task, "needs a human")

    assert workflows.run_status({name: queue.state(bead) for name, bead in ids.items()}) == (
        workflows.BLOCKED
    )


def test_unknown_dep_fails_fast(tmp_path: Path) -> None:
    path = tmp_path / "bad.txt"
    path.write_text("write code: missing spec\n")

    with pytest.raises(ValueError, match="missing spec"):
        workflows.load(path)
