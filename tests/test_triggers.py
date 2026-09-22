"""Triggers: one blocked bead opens one read-only investigator, once."""

import fake_beads
import pytest

from swarm import queue, triggers


def block_one(tmp_path, monkeypatch, title="stuck work"):
    fake_beads.install(tmp_path, monkeypatch, {"bead-9": title})
    task = queue.claim_next()
    assert task is not None
    queue.block(task, "needs a human to look")
    return task


def test_blocked_bead_fires_once_not_twice(tmp_path, monkeypatch):
    stuck = block_one(tmp_path, monkeypatch)
    seen: set[str] = set()

    first = triggers.poll(seen)

    assert len(first) == 1
    assert stuck.bead_id in seen
    assert triggers.poll(seen) == []


def test_cap_limits_new_investigations(tmp_path, monkeypatch: pytest.MonkeyPatch):
    fake_beads.install(
        tmp_path,
        monkeypatch,
        {"bead-1": "first", "bead-2": "second", "bead-3": "third"},
    )
    for _ in range(3):
        task = queue.claim_next()
        assert task is not None
        queue.block(task, "needs a human to look")

    found = triggers.poll(set(), limit=2)

    assert len(found) == 2


def test_investigator_bead_is_read_only(tmp_path, monkeypatch):
    stuck = block_one(tmp_path, monkeypatch)

    triggers.poll(set())

    titles = [task.title for task in queue.list_ready()]
    investigators = [title for title in titles if stuck.bead_id in title]
    assert len(investigators) == 1
    assert "Read-only" in investigators[0]
    assert "change no files" in investigators[0]
