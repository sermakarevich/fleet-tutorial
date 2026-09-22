"""Entry point of the swarm runner: claim beads, run them, close them."""

import os
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

from swarm import queue, retry, runner, worker, worktree

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
    elif [ "$4" = "blocked" ]; then
      [ -e "$dir/prog_$2" ] || exit 1
      mv "$dir/prog_$2" "$dir/blocked_$2"
      printf '%s\\n' "$6" > "$dir/blocked_$2.reason"
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
SEED_TASKS = {"bead-1": "first line", "bead-2": "second line"}
LABELS = {
    "bead-1": {"kind": "plan", "harness": "opencode"},
    "bead-2": {"kind": "exec", "harness": "opencode"},
}


def install_fake_bd(tmp: Path) -> Path:
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


def seed_repo(repo: Path) -> None:
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    (repo / "shared.txt").write_text(SEED_FILE)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=swarm",
            "-c",
            "user.email=swarm@example.com",
            "commit",
            "-m",
            "seed",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def by_bead(task: queue.Task) -> Mapping[str, str]:
    return LABELS[task.bead_id]


def demo_task(task: str, workdir: Path, meta: Mapping[str, str] | None = None) -> str:
    route = worker.resolve(meta)
    print(f"spawn: {task} -> {route.harness}/{route.model}")
    shared = workdir / "shared.txt"
    if "first" in task:
        shared.write_text(shared.read_text().replace("apples are red", "apples are green"))
    else:
        shared.write_text(shared.read_text().replace("carrots are orange", "carrots are purple"))
    worktree.commit(workdir, task)
    return f"result for {task}"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = install_fake_bd(Path(tmp))
        for bead_id, title in SEED_TASKS.items():
            (state_dir / f"open_{bead_id}").write_text(title + "\n")
        repo = Path(tmp) / "repo"
        seed_repo(repo)
        failures: dict[str, list[retry.Kind]] = {}
        for _ in range(10):
            if not queue.list_ready():
                break
            result = runner.supervise(demo_task, repo=repo, failures=failures, meta_for=by_bead)
            if result is not None:
                print(f"closed: {result}")
        assert queue.claim_next() is None
        assert "apples are green" in (repo / "shared.txt").read_text()
        print("queue ready: none (two beads claimed, built, merged, closed)")


if __name__ == "__main__":
    main()
