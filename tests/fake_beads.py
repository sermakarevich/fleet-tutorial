"""Fake `bd` task tool for offline tests: state lives in plain files."""

import os
from pathlib import Path

import pytest

SCRIPT = """#!/bin/sh
dir="$FAKE_BEADS_DIR"
ready_one() {
  f="$1"
  id="${f##*/open_}"
  deps=""
  [ -f "$dir/deps_$id" ] && deps="$(cat "$dir/deps_$id")"
  saved="$IFS"
  IFS=','
  # shellcheck disable=SC2162
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
      [ "$2" = "$FAKE_BEADS_FAIL_CLAIM" ] && exit 1
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


def install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tasks: dict[str, str]) -> Path:
    """Put a fake `bd` first on PATH, seeded with open bead ids to titles."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake_bd = bin_dir / "bd"
    fake_bd.write_text(SCRIPT)
    fake_bd.chmod(0o755)
    state_dir = tmp_path / "beads"
    state_dir.mkdir(exist_ok=True)
    for bead_id, title in tasks.items():
        (state_dir / f"open_{bead_id}").write_text(title + "\n")
    monkeypatch.setenv("FAKE_BEADS_DIR", str(state_dir))
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.delenv("FAKE_BEADS_FAIL_CLAIM", raising=False)
    return state_dir
