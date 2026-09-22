"""Retry policy: flaky tasks close after retries, hopeless ones block."""

from pathlib import Path

import fake_beads
import pytest

from swarm import checkpoint, queue, retry, runner


def test_flaky_task_retries_twice_then_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = fake_beads.install(tmp_path, monkeypatch, {"bead-1": "flaky chore"})
    calls = 0

    def flaky(task: str) -> str:
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise RuntimeError(f"boom {calls}")
        return f"result for {task}"

    results = runner.run_parallel(count=1, run_task=flaky, lease_ttl=0.05, beat_every=0.01)

    assert results == ["result for flaky chore"]
    assert calls == 3
    assert (state_dir / "closed_bead-1").exists()
    assert queue.list_ready() == []


def test_hopeless_task_blocks_with_reason(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir = fake_beads.install(tmp_path, monkeypatch, {"bead-9": "hopeless chore"})
    calls = 0

    def hopeless(task: str) -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("always fails")

    results = runner.run_parallel(count=1, run_task=hopeless, lease_ttl=0.05, beat_every=0.01)

    assert results == []
    assert calls == 1 + retry.MAX_RETRIES
    assert (state_dir / "blocked_bead-9").exists()
    reason = (state_dir / "blocked_bead-9.reason").read_text().strip()
    assert "crash" in reason and "human" in reason
    assert queue.list_ready() == []


def test_timeout_counts_as_stall_then_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-2": "slow chore"})
    assert retry.classify_error(TimeoutError("no answer")) == retry.Kind.STALL
    calls = 0

    def slow(task: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("no answer")
        return f"result for {task}"

    results = runner.run_parallel(count=1, run_task=slow, lease_ttl=0.05, beat_every=0.01)

    assert results == ["result for slow chore"]
    assert calls == 2


def test_partial_result_retries_then_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-3": "half chore"})
    calls = 0

    def half(task: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            return "PARTIAL: half done"
        return f"result for {task}"

    results = runner.run_parallel(count=1, run_task=half, lease_ttl=0.05, beat_every=0.01)

    assert results == ["result for half chore"]
    assert calls == 2


def test_streak_ends_at_limit_and_logs_show_kinds(tmp_path: Path) -> None:
    assert retry.should_retry([retry.Kind.CRASH] * 3)
    assert not retry.should_retry([retry.Kind.CRASH] * 4)
    assert retry.backoff_for(1) <= retry.backoff_for(4)

    task_folder = tmp_path / "chore"
    checkpoint.log_attempt(task_folder, "Traceback: boom")
    checkpoint.log_attempt(task_folder, "TimeoutError: timed out")
    assert retry.kinds_from_logs(task_folder) == [retry.Kind.CRASH, retry.Kind.STALL]
    checkpoint.log_attempt(task_folder, "all good")
    assert retry.kinds_from_logs(task_folder) == []
