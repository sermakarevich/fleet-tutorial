"""Beads queue: list, claim once, close, reopen, all through a fake `bd`."""

from pathlib import Path

import fake_beads
import pytest

from swarm import queue


@pytest.fixture
def beads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return fake_beads.install(
        tmp_path, monkeypatch, {"bead-1": "first chore", "bead-2": "second chore"}
    )


def test_list_ready_shows_open_beads(beads: Path) -> None:
    assert [(task.bead_id, task.title) for task in queue.list_ready()] == [
        ("bead-1", "first chore"),
        ("bead-2", "second chore"),
    ]


def test_claim_next_hands_each_bead_out_once(beads: Path) -> None:
    first = queue.claim_next()
    second = queue.claim_next()
    assert first is not None and second is not None
    assert {first.bead_id, second.bead_id} == {"bead-1", "bead-2"}
    assert queue.claim_next() is None


def test_claim_skips_a_bead_claimed_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-1": "first chore", "bead-2": "second chore"})
    monkeypatch.setenv("FAKE_BEADS_FAIL_CLAIM", "bead-1")
    claimed = queue.claim_next()
    assert claimed is not None and claimed.bead_id == "bead-2"


def test_close_removes_the_bead_from_ready(beads: Path) -> None:
    task = queue.claim_next()
    assert task is not None
    queue.close(task)
    assert [task.bead_id for task in queue.list_ready()] == [
        bead for bead in ("bead-1", "bead-2") if bead != task.bead_id
    ]
    assert (beads / f"closed_{task.bead_id}").exists()


def test_reopen_returns_a_failed_bead_to_ready(beads: Path) -> None:
    task = queue.claim_next()
    assert task is not None
    queue.reopen(task)
    assert task.bead_id in [ready.bead_id for ready in queue.list_ready()]
    again = queue.claim_next()
    assert again is not None and again.bead_id == task.bead_id
