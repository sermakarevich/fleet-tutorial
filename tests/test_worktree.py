"""Worktree isolation: separate builds per bead, clean merges land, clashes reopen."""

import subprocess
import time
from pathlib import Path

import fake_beads
import pytest

from swarm import queue, runner, worktree

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


def branches(repo: Path) -> str:
    return git(repo, "branch", "--list")


def test_unmerged_work_stays_out_of_base(repo: Path) -> None:
    path, branch = worktree.create(repo, "bead-1")
    assert branch == "task-bead-1"

    edit(path, "apples are red", "apples are green")
    assert (repo / "shared.txt").read_text() == SEED_FILE

    worktree.commit(path, "first line")
    assert (repo / "shared.txt").read_text() == SEED_FILE

    assert worktree.merge_back(repo, branch) is True
    worktree.remove(repo, path, branch)
    assert "apples are green" in (repo / "shared.txt").read_text()
    assert "task-bead-1" not in branches(repo)
    assert not (repo / worktree.CONFLICT_FILE).exists()


def test_create_twice_starts_fresh(repo: Path) -> None:
    path, _ = worktree.create(repo, "bead-1")
    edit(path, "apples are red", "apples are green")
    worktree.commit(path, "stale")

    fresh, branch = worktree.create(repo, "bead-1")
    assert (fresh / "shared.txt").read_text() == SEED_FILE
    assert branch == "task-bead-1"


def test_parallel_tasks_merge_clean_and_close(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-1": "first line", "bead-2": "second line"})

    def isolated(task: str, workdir: Path) -> str:
        if "first" in task:
            edit(workdir, "apples are red", "apples are green")
        else:
            edit(workdir, "carrots are orange", "carrots are purple")
        worktree.commit(workdir, task)
        return f"result for {task}"

    results = runner.run_parallel(count=2, run_task=isolated, repo=repo)

    assert sorted(results) == ["result for first line", "result for second line"]
    merged = (repo / "shared.txt").read_text()
    assert "apples are green" in merged
    assert "carrots are purple" in merged
    assert queue.list_ready() == []
    assert not (repo / worktree.CONFLICT_FILE).exists()


def test_conflict_leaves_markers_and_reopens(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_beads.install(tmp_path, monkeypatch, {"bead-1": "red apples", "bead-2": "green apples"})
    peers = [worktree.work_path(repo, bead_id) for bead_id in ("bead-1", "bead-2")]

    def clashing(task: str, workdir: Path) -> str:
        deadline = time.monotonic() + 10.0
        while not all(peer.exists() for peer in peers) and time.monotonic() < deadline:
            time.sleep(0.01)
        shared = workdir / "shared.txt"
        lines = shared.read_text().splitlines()
        lines[0] = task
        shared.write_text("\n".join(lines) + "\n")
        worktree.commit(workdir, task)
        return f"result for {task}"

    results = runner.run_parallel(count=2, run_task=clashing, repo=repo)

    assert len(results) == 1
    assert len(queue.list_ready()) == 1
    assert "task-bead" in (repo / worktree.CONFLICT_FILE).read_text()
    assert "<<<<<<<" in (repo / "shared.txt").read_text()
    assert "task-bead" in branches(repo)
