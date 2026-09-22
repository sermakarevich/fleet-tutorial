"""Entry point of the swarm runner: claim beads, run them, close them."""

import os
import tempfile
from collections import Counter
from pathlib import Path

from swarm import loop, queue

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
    """Two open beads the fake `bd` can list, claim, and close."""
    (state_dir / "open_bead-1").write_text("first chore\n")
    (state_dir / "open_bead-2").write_text("second chore\n")


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

        def canned(task: str) -> str:
            runs[task] += 1
            return f"result for {task}"

        results = loop.run(canned)
        for result in results:
            print(f"result: {result}")
        doubles = sum(count - 1 for count in runs.values())
        print(f"done: claimed {len(results)}, ran {sum(runs.values())}, double-runs {doubles}")
        assert queue.claim_next() is None
        print("queue empty: both beads closed")


if __name__ == "__main__":
    main()
