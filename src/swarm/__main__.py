"""Entry point of the swarm runner: run one saved workflow through beads."""

import os
import subprocess
import tempfile
from pathlib import Path

from swarm import queue, retry, runner, workflows, worktree

FAKE_BD = """#!/bin/sh
dir="$FAKE_BEADS_DIR"
ready_one() {
  f="$1"
  id="${f##*/open_}"
  deps=""
  [ -f "$dir/deps_$id" ] && deps="$(cat "$dir/deps_$id")"
  saved="$IFS"
  IFS=','
  for dep in $deps; do
    dep="$(printf '%s' "$dep" | tr -d ' ')"
    [ -z "$dep" ] && continue
    [ -f "$dir/closed_$dep" ] || { IFS="$saved"; return 1; }
  done
  IFS="$saved"
  return 0
}
case "$1" in
  ready)
    printf '['
    first=1
    for f in "$dir"/open_*; do
      [ -e "$f" ] || continue
      ready_one "$f" || continue
      if [ $first -eq 0 ]; then printf ','; fi
      first=0
      printf '{"id":"%s","title":"%s"}' "${f##*/open_}" "$(cat "$f")"
    done
    printf ']\\n'
    ;;
  create)
    title="$2"
    deps=""
    shift 2
    while [ $# -gt 0 ]; do
      case "$1" in
        --deps) deps="$2"; shift 2 ;;
        *) shift ;;
      esac
    done
    n=1
    while [ -e "$dir/open_bead-$n" ] || [ -e "$dir/prog_bead-$n" ] \\
        || [ -e "$dir/closed_bead-$n" ] || [ -e "$dir/blocked_bead-$n" ]; do
      n=$((n + 1))
    done
    printf '%s\\n' "$title" > "$dir/open_bead-$n"
    printf '%s\\n' "$deps" > "$dir/deps_bead-$n"
    printf 'bead-%s\\n' "$n"
    ;;
  show)
    id="$2"
    status="open"
    [ -e "$dir/prog_$id" ] && status="in_progress"
    [ -e "$dir/blocked_$id" ] && status="blocked"
    [ -e "$dir/closed_$id" ] && status="closed"
    title=""
    for f in "$dir"/open_"$id" "$dir"/prog_"$id" "$dir"/blocked_"$id"; do
      [ -f "$f" ] && title="$(cat "$f")"
    done
    printf '[{"id":"%s","title":"%s","status":"%s"}]\\n' "$id" "$title" "$status"
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

WORKFLOW = "write spec\nwrite code: write spec\ncheck work: write code\n"


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
    (repo / "progress.txt").write_text("")
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


def demo_task(task: str, workdir: Path, meta=None) -> str:
    log = workdir / "progress.txt"
    log.write_text(log.read_text() + task + "\n")
    worktree.commit(workdir, task)
    return f"result for {task}"


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        install_fake_bd(Path(tmp))
        flow = Path(tmp) / "flow.txt"
        flow.write_text(WORKFLOW)
        ids = workflows.start(flow)
        print(f"opened: {len(ids)} steps (spec, code, check)")
        repo = Path(tmp) / "repo"
        seed_repo(repo)
        failures: dict[str, list[retry.Kind]] = {}
        for _ in range(10):
            ready = queue.list_ready()
            if not ready:
                break
            print(f"ready: {ready[0].title}")
            result = runner.supervise(demo_task, repo=repo, failures=failures)
            if result is not None:
                print(f"closed: {result}")
        status = workflows.run_status({name: queue.state(bead) for name, bead in ids.items()})
        done = (repo / "progress.txt").read_text().splitlines()
        assert done == ["write spec", "write code", "check work"]
        assert status == workflows.DONE
        print(f"run status: {status} (3 of 3 steps closed in order)")


if __name__ == "__main__":
    main()
