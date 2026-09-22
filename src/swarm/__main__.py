"""Entry point of the swarm runner: claim beads, run them, close them."""

import os
import tempfile
import threading
import time
from collections import Counter
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


def seed_demo_beads(state_dir: Path) -> None:
    """Three open beads the fake `bd` can list, claim, and close."""
    (state_dir / "open_bead-1").write_text("first chore\n")
    (state_dir / "open_bead-2").write_text("second chore\n")
    (state_dir / "open_bead-3").write_text("third chore\n")


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
        seed_demo_beads(state_dir)
        runs: Counter[str] = Counter()
        lock = threading.Lock()
        live = 0
        peak = 0

        def canned(task: str) -> str:
            nonlocal live, peak
            with lock:
                runs[task] += 1
                attempt = runs[task]
                live += 1
                peak = max(peak, live)
            try:
                time.sleep(0.2)
                if task == "second chore" and attempt == 1:
                    print(f"crashed: {task} died holding its lease")
                    raise RuntimeError("simulated crash")
                return f"result for {task}"
            finally:
                with lock:
                    live -= 1

        results = runner.run_parallel(count=3, run_task=canned, lease_ttl=0.2, beat_every=0.05)
        for result in sorted(results):
            print(f"result: {result}")
        print(f"workers at peak: {peak}")
        if runs["second chore"] > 1:
            print("dead lease reclaimed: second chore ran again and closed")
        doubles = sum(count - 1 for task, count in runs.items() if task != "second chore")
        print(f"done: claimed {len(results)}, ran {sum(runs.values())}, double-runs {doubles}")
        assert queue.claim_next() is None
        print("queue empty: all beads closed")


if __name__ == "__main__":
    main()
