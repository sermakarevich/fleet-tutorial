# Tutorial 6 — Worktree isolation and merge

After this tutorial each task builds in its own copy of the code, then merges back.

## In short

### The concepts

- You stop workers overwriting each other. Each task gets its own git
  worktree (a separate folder checked out from the same repository), so two
  tasks can edit the same file at once. Think of separate desks instead of
  one shared desk.
- The shape is a small module that shells out to git, not a new service. The
  full-size fleet orchestrator this series learns from does the same merge
  and starts a repair worker to resolve clashes, where this tutorial leaves
  markers for you to fix by hand.
- Tutorial 5 ran workers in parallel with leases, but they shared one folder:
  tasks editing the same files clashed and one edit won silently.
- Two traps are closed here. A stale worktree or branch from a crashed run is
  removed before a fresh one is made, and a clashing merge leaves markers
  plus a CONFLICT file and reopens the bead instead of closing it.

### Scope

1. Create one worktree and branch per bead.
2. Run each task inside its own worktree and commit its edits there.
3. Merge each branch back, and reopen the bead when the merge clashes.

Left out on purpose: bounded retries and a place for hopeless tasks.
Tutorial 7 retries a failing task twice, then parks it for a human.

### The problem

```text
$ just tutorial
worker A: edits shared.txt
worker B: edits shared.txt
result: one edit lost
```

The loop from tutorial 5 runs workers side by side in one folder. Two tasks
editing the same file overwrite each other, so one result vanishes.

### What changes

```text
src/swarm/
+   worktree.py         one folder and branch per task, merged back
~   runner.py           each bead builds in its own worktree
~   worker.py           harness runs inside the task worktree
~   __main__.py         demo where two tasks edit one file and merge
tests/
+   test_worktree.py
```

`+` is new, `~` is changed. The full change is `git diff tut05..tut06`.

## In detail

### How it works

One task waits as one bead in the queue. The runner claims it, creates a
worktree on a fresh branch named after the bead, and runs the task with that
folder as its working directory. The task edits files, the runner commits
them, and the branch merges back into the base branch. On a clean merge the
runner removes the worktree and its branch and closes the bead. On a clash
the markers stay in the files, a CONFLICT file names the branch, and the bead
reopens for repair instead of closing. Git merges run through one lock, so
two merges never interleave.

### Design decisions

- The worktree module knows nothing about the queue. It creates, commits,
  merges and removes, so leases and claims keep working unchanged beside it.
- A clashing bead reopens instead of failing the run. One clash costs a
  repair pass, not a lost task, so healthy beads keep merging. The fleet
  orchestrator this series learns from goes one step further at scale and
  spawns a repair worker before asking a human.

### The excerpt that carries the idea

**src/swarm/worktree.py**

```python
def merge_back(repo: Path, branch: str, base: str = "main") -> bool:
    """Merge a bead branch into base. True when clean, False on conflict.

    On conflict the markers stay in the files and CONFLICT names the
    branch, so a repair worker or human can resolve it by hand.
    """
```

### Run it

```bash
git checkout tut06
just tutorial
```

```text
tut06: worktree isolation and merge
uv run python -m swarm
result: result for first line
result: result for second line
merged shared.txt:
apples are green
soup is hot
carrots are purple
branches:
* main
queue empty: all beads merged and closed
```

### Key takeaways

- One worktree per task: each bead builds on its own branch in its own
  folder, so parallel edits never overwrite each other.
- A clean merge closes the bead and removes the worktree and its branch, so
  nothing piles up between runs.
- A clashing merge reopens the bead with markers and a CONFLICT file, so a
  repair worker or human can resolve it instead of losing work.

### What is still missing

A task that fails on its own keeps coming back forever: nothing counts its
attempts or parks it after too many. Tutorial 7 adds retries with a limit and
a dead-letter queue for tasks that need a human.
