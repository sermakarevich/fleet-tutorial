"""Parallel runner: N workers at once, dead leases return, beads never double-run."""

import threading
import time
from pathlib import Path

import fake_beads
import pytest

from swarm import queue, runner


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now
        self.lock = threading.Lock()

    def __call__(self) -> float:
        with self.lock:
            return self.now

    def advance(self, seconds: float) -> None:
        with self.lock:
            self.now += seconds


def wait_until(predicate: object, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():  # type: ignore[operator]
            return True
        time.sleep(0.01)
    return False


def test_three_workers_run_at_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_beads.install(
        tmp_path, monkeypatch, {"bead-1": "first", "bead-2": "second", "bead-3": "third"}
    )
    lock = threading.Lock()
    live: set[str] = set()
    started: set[str] = set()
    calls: dict[str, int] = {}
    peak = 0
    overlap: list[str] = []

    def fake(task: str) -> str:
        nonlocal peak
        with lock:
            calls[task] = calls.get(task, 0) + 1
            if task in live:
                overlap.append(task)
            live.add(task)
            started.add(task)
            peak = max(peak, len(live))
        assert wait_until(lambda: len(started) >= 3, timeout=5.0)
        time.sleep(0.05)
        with lock:
            live.discard(task)
        return f"result for {task}"

    results = runner.run_parallel(count=3, run_task=fake, beat_every=0.01)

    assert sorted(results) == ["result for first", "result for second", "result for third"]
    assert peak == 3
    assert overlap == []
    assert calls == {"first": 1, "second": 1, "third": 1}
    assert queue.list_ready() == []


def test_crashed_lease_expires_back_to_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = fake_beads.install(tmp_path, monkeypatch, {"bead-1": "solo"})
    clock = FakeClock()
    lock = threading.Lock()
    calls = 0
    live = 0
    overlap = 0

    def flaky(task: str) -> str:
        nonlocal calls, live, overlap
        with lock:
            calls += 1
            live += 1
            overlap = max(overlap, live)
        try:
            if calls == 1:
                raise RuntimeError("worker crashed")
            return f"result for {task}"
        finally:
            with lock:
                live -= 1

    outcomes: list[str] = []
    errors: list[BaseException] = []

    def target() -> None:
        try:
            outcomes.extend(
                runner.run_parallel(
                    count=1, run_task=flaky, clock=clock, lease_ttl=100.0, beat_every=0.01
                )
            )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()

    assert wait_until(lambda: calls >= 1)
    assert wait_until(lambda: (state_dir / "prog_bead-1").exists())

    clock.advance(50.0)
    time.sleep(0.3)
    assert [task.bead_id for task in queue.list_ready()] == []
    assert thread.is_alive()

    clock.advance(60.0)
    thread.join(timeout=10.0)
    assert not thread.is_alive()
    assert errors == []
    assert outcomes == ["result for solo"]
    assert calls == 2
    assert overlap == 1
    assert queue.list_ready() == []
