"""Entry point of the swarm runner: one workflow, one schedule, one trigger."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

from swarm import queue, schedule, triggers, workflows

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
  blocked)
    printf '['
    first=1
    for f in "$dir"/blocked_*; do
      [ -e "$f" ] || continue
      case "$f" in *.reason) continue ;; esac
      if [ $first -eq 0 ]; then printf ','; fi
      first=0
      printf '{"id":"%s","title":"%s"}' "${f##*/blocked_}" "$(cat "$f")"
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


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        install_fake_bd(Path(tmp))
        now = datetime.now()
        flow = Path(tmp) / "flow.txt"
        flow.write_text("write spec\nwrite code: write spec\n")
        run = workflows.start(flow)
        print(f"workflow: {len(run)} steps (write spec, write code)")
        other = (now.minute + 1) % 60
        sched = Path(tmp) / "sched.txt"
        sched.write_text(
            "morning report | * * * * * | task: write daily report\n"
            f"later job | {other} * * * * | task: write later report\n"
        )
        entries = schedule.load(sched)
        fired: dict[str, str] = {}
        for entry in schedule.tick(entries, now, fired):
            bead = schedule.fire(entry, now, fired)
            print(f"fired: {entry.name} -> {bead}")
        for entry in entries:
            if entry.name not in fired:
                print(f"quiet: {entry.name} (not due)")
        stuck = queue.claim_next()
        assert stuck is not None
        queue.block(stuck, "needs a human to look")
        seen: set[str] = set()
        opened = triggers.poll(seen)
        assert len(opened) == 1
        print(f"trigger: blocked {stuck.bead_id} -> {opened[0]}")
        assert triggers.poll(seen) == []
        ready = sorted(task.title for task in queue.list_ready())
        assert "write daily report" in ready
        assert any("Read-only" in title for title in ready)


if __name__ == "__main__":
    main()
