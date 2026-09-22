"""One git worktree per task: build in isolation, merge back when done."""

import subprocess
from pathlib import Path

BRANCH_PREFIX = "task-"
CONFLICT_FILE = "CONFLICT"
WORKER_NAME = "swarm"
WORKER_EMAIL = "swarm@example.com"


def branch_name(bead_id: str) -> str:
    """Branch that holds one bead's work."""
    return BRANCH_PREFIX + bead_id


def work_path(repo: Path, bead_id: str) -> Path:
    """Folder next to the repo where the bead's worktree lives."""
    return repo.parent / f"{repo.name}-{bead_id}"


def _git(workdir: Path, args: list[str]) -> str:
    """Run one git command in a folder, raising when git reports failure."""
    done = subprocess.run(["git", *args], cwd=workdir, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def remove(repo: Path, path: Path, branch: str | None = None) -> None:
    """Forget a worktree folder, and its branch when the merge landed."""
    try:
        _git(repo, ["worktree", "remove", "--force", str(path)])
    except subprocess.CalledProcessError:
        pass
    if branch is not None:
        try:
            _git(repo, ["branch", "-d", branch])
        except subprocess.CalledProcessError:
            pass
    _git(repo, ["worktree", "prune"])


def create(repo: Path, bead_id: str, base: str = "main") -> tuple[Path, str]:
    """Copy the base branch into a fresh worktree for one bead."""
    path = work_path(repo, bead_id)
    branch = branch_name(bead_id)
    remove(repo, path)
    try:
        _git(repo, ["branch", "-D", branch])
    except subprocess.CalledProcessError:
        pass
    _git(repo, ["worktree", "add", "-b", branch, str(path), base])
    return path, branch


def commit(path: Path, message: str) -> None:
    """Record everything the worker changed inside its worktree."""
    _git(path, ["add", "-A"])
    _git(
        path,
        [
            "-c",
            f"user.name={WORKER_NAME}",
            "-c",
            f"user.email={WORKER_EMAIL}",
            "commit",
            "-m",
            message,
        ],
    )


def merge_back(repo: Path, branch: str, base: str = "main") -> bool:
    """Merge a bead branch into base. True when clean, False on conflict.

    On conflict the markers stay in the files and CONFLICT names the
    branch, so a repair worker or human can resolve it by hand.
    """
    _git(repo, ["checkout", base])
    done = subprocess.run(
        ["git", "merge", "--no-ff", "--no-edit", branch],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if done.returncode == 0:
        return True
    (repo / CONFLICT_FILE).write_text(
        f"merge conflict from {branch}: resolve markers, commit, close by hand\n"
        + done.stdout
        + done.stderr
    )
    return False
