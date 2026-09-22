"""Entry point of the swarm runner: claim beads, run them, close them."""

import os
import subprocess
import tempfile
from pathlib import Path

from swarm import queue, runner, worktree

FAKE_BD = """#!/bin/sh
dir="$FAKE_BEADS_DIR"
case "$1" in
  ready)
    printf '['
    first=1
    for f in "$dir"/open_*; do
      [ -e "$f" ] || continue
      if [ $first -eq 0 ]; then printf ','; fi
      first=0
      printf '{"id":"%s","title":"%s"}' "${f##*/open_}" "$(cat "$f")"
    done
    printf ']\\n'
    ;;
  update)
    if [ "$3" = "--claim" ]; then
      [ -e "$dir/open_$2" ] || exit 1
      mv "$dir/open_$2" "$dir/prog_$2"
    else
      [ -e "$dir/prog_$2" ] || exit 1
      mv "$dir/prog_$2" "$dir/open_$2"
    fi
    ;;
  close)
    rm -f "$dir/open_$2" "$dir/prog_$2"
    touch "$dir/closed_$2"
    ;;
esac
"""

SEED_FILE = "apples are red\nsoup is hot\ncarrots are orange\n"


def install_fake_bd(tmp: Path) -> Path:
    """Put a fake `bd` first on PATH, backed by files in the state folder."""
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    fake_bd = bin_dir / "bd"
    fake_bd.write_text(FAKE_BD)
    fake_bd.chmod(0o755)
    state_dir = tmp / "beads"
    state_dir.mkdir()
    os.environ["FAKE_BEADS_DIR"] = str(state_dir)
    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
    return state_dir


def seed_demo_beads(state_dir: Path) -> None:
    """Two open beads that edit different lines of the same file."""
    (state_dir / "open_bead-1").write_text("first line\n")
    (state_dir / "open_bead-2").write_text("second line\n")


def git(repo: Path, *args: str) -> str:
    """Run one git command in the demo repo."""
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def seed_demo_repo(tmp: Path) -> Path:
    """A git repo whose shared file both demo tasks will edit."""
    repo = tmp / "demo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    (repo / "shared.txt").write_text(SEED_FILE)
    git(repo, "add", "-A")
    git(
        repo,
        "-c",
        "user.name=swarm",
        "-c",
        "user.email=swarm@example.com",
        "commit",
        "-m",
        "seed",
    )
    return repo


def edit_line(path: Path, old: str, new: str) -> None:
    """Swap one line of the shared file inside a task worktree."""
    shared = path / "shared.txt"
    shared.write_text(shared.read_text().replace(old, new))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = install_fake_bd(Path(tmp))
        seed_demo_beads(state_dir)
        repo = seed_demo_repo(Path(tmp))

        def isolated(task: str, workdir: Path) -> str:
            if "first" in task:
                edit_line(workdir, "apples are red", "apples are green")
            else:
                edit_line(workdir, "carrots are orange", "carrots are purple")
            worktree.commit(workdir, task)
            return f"result for {task}"

        results = runner.run_parallel(count=2, run_task=isolated, repo=repo, base="main")
        for result in sorted(results):
            print(f"result: {result}")
        print("merged shared.txt:")
        print((repo / "shared.txt").read_text().strip())
        print("branches:")
        print(git(repo, "branch", "--list"))
        assert queue.claim_next() is None
        print("queue empty: all beads merged and closed")


if __name__ == "__main__":
    main()
