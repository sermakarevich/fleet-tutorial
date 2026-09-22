"""Supervisor tick: claim, spawn, reap, merge, close — failures retry, clashes reopen."""

import subprocess
from collections.abc import Mapping
from pathlib import Path

import fake_beads
import pytest

from swarm import queue, retry, runner, worker, worktree

SEED_FILE = "apples are red\nsoup is hot\ncarrots are orange\n"


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    (root / "shared.txt").write_text(SEED_FILE)
    git(root, "add", "-A")
    git(
        root,
        "-c",
        "user.name=swarm",
        "-c",
        "user.email=swarm@example.com",
        "commit",
        "-m",
        "seed",
    )
    return root


def edit(path: Path, old: str, new: str) -> None:
    shared = path / "shared.txt"
    shared.write_text(shared.read_text().replace(old, new))


def test_tick_closes_two_beads_and_merges_both(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-1": "first line", "bead-2": "second line"})
    seen: list[Mapping[str, str] | None] = []

    def isolated(task: str, workdir: Path, meta: Mapping[str, str] | None = None) -> str:
        seen.append(meta)
        if "first" in task:
            edit(workdir, "apples are red", "apples are green")
        else:
            edit(workdir, "carrots are orange", "carrots are purple")
        worktree.commit(workdir, task)
        return f"result for {task}"

    failures: dict[str, list[retry.Kind]] = {}
    labels = {"bead-1": {"kind": "plan"}, "bead-2": {"kind": "exec"}}

    def by_bead(task: queue.Task) -> Mapping[str, str]:
        return labels[task.bead_id]

    first = runner.supervise(isolated, repo=repo, failures=failures, meta_for=by_bead)
    second = runner.supervise(isolated, repo=repo, failures=failures, meta_for=by_bead)
    third = runner.supervise(isolated, repo=repo, failures=failures, meta_for=by_bead)

    assert sorted([first, second]) == ["result for first line", "result for second line"]
    assert third is None
    merged = (repo / "shared.txt").read_text()
    assert "apples are green" in merged
    assert "carrots are purple" in merged
    assert queue.list_ready() == []
    assert not (repo / worktree.CONFLICT_FILE).exists()
    assert failures == {}


def test_failure_reopens_then_closes_on_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-1": "flaky chore"})
    calls = 0

    def flaky(task: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("worker crashed")
        return f"result for {task}"

    failures: dict[str, list[retry.Kind]] = {}
    assert runner.supervise(flaky, failures=failures) is None
    assert [task.bead_id for task in queue.list_ready()] == ["bead-1"]

    assert runner.supervise(flaky, failures=failures) == "result for flaky chore"
    assert calls == 2
    assert queue.list_ready() == []


def test_exhausted_failures_block_with_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = fake_beads.install(tmp_path, monkeypatch, {"bead-9": "hopeless chore"})
    calls = 0

    def hopeless(task: str) -> str:
        nonlocal calls
        calls += 1
        raise RuntimeError("always fails")

    failures: dict[str, list[retry.Kind]] = {}
    for _ in range(10):
        runner.supervise(hopeless, failures=failures)
        if (state_dir / "blocked_bead-9").exists():
            break

    assert calls == 1 + retry.MAX_RETRIES
    reason = (state_dir / "blocked_bead-9.reason").read_text().strip()
    assert "crash" in reason and "human" in reason
    assert queue.list_ready() == []


def test_merge_conflict_reopens_for_repair(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-1": "red apples"})

    def rival(task: str, workdir: Path) -> str:
        shared = workdir / "shared.txt"
        lines = shared.read_text().splitlines()
        lines[0] = task
        shared.write_text("\n".join(lines) + "\n")
        main_file = repo / "shared.txt"
        main_lines = main_file.read_text().splitlines()
        main_lines[0] = "rival apples"
        main_file.write_text("\n".join(main_lines) + "\n")
        git(repo, "add", "-A")
        git(
            repo,
            "-c",
            "user.name=swarm",
            "-c",
            "user.email=swarm@example.com",
            "commit",
            "-m",
            "rival merge lands first",
        )
        worktree.commit(workdir, task)
        return f"result for {task}"

    failures: dict[str, list[retry.Kind]] = {}
    assert runner.supervise(rival, repo=repo, failures=failures) is None

    assert [task.bead_id for task in queue.list_ready()] == ["bead-1"]
    assert "task-bead-1" in (repo / worktree.CONFLICT_FILE).read_text()
    assert "<<<<<<<" in (repo / "shared.txt").read_text()


def test_tick_routes_plan_to_smart_and_defaults_to_opencode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-1": "design the queue"})
    monkeypatch.setenv("SWARM_SMART_MODEL", "smart-one")
    monkeypatch.setenv("SWARM_CHEAP_MODEL", "cheap-one")
    seen: list[Mapping[str, str] | None] = []

    def recording(
        task: str,
        workdir: Path | None = None,
        meta: Mapping[str, str] | None = None,
    ) -> str:
        seen.append(meta)
        return f"result for {task}"

    result = runner.supervise(recording, meta_for=lambda task: {"kind": "plan"})

    assert result == "result for design the queue"
    assert seen == [{"kind": "plan"}]
    route = worker.resolve(seen[0])
    assert route.model == "smart-one"
    assert route.harness == "opencode"
    assert queue.list_ready() == []


def test_empty_queue_tick_does_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_beads.install(tmp_path, monkeypatch, {})
    assert runner.supervise(lambda task: "never runs") is None
