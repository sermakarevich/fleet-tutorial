"""Entry point of the swarm runner: claim beads, run them, close them."""

import os
import tempfile
from pathlib import Path

from swarm import queue, runner

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
      printf '%s\n' "$6" > "$dir/blocked_$2.reason"
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

SEED_TASKS = {"open_flaky": "flaky chore\n", "open_hopeless": "hopeless chore\n"}


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


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = install_fake_bd(Path(tmp))
        for name, title in SEED_TASKS.items():
            (state_dir / name).write_text(title)
        tries: dict[str, int] = {}

        def demo(task: str) -> str:
            tries[task] = tries.get(task, 0) + 1
            if "hopeless" in task:
                raise RuntimeError("always fails")
            if tries[task] <= 2:
                raise RuntimeError(f"flaky fails, try {tries[task]}")
            return f"result for {task}"

        results = runner.run_parallel(count=1, run_task=demo, lease_ttl=0.2, beat_every=0.01)
        for result in results:
            print(f"result: {result}")
        reason = (state_dir / "blocked_hopeless.reason").read_text().strip()
        print(f"blocked: hopeless chore — {reason}")
        assert queue.claim_next() is None
        print("queue ready: none (one closed, one parked for a human)")


if __name__ == "__main__":
    main()
