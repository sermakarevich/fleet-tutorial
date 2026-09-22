# Tutorial 10 — Workflows as saved graphs

After this tutorial you save a repeating chain of tasks in one file and stop retyping it.

## In short

### The concepts

- You store the chain once as a directed acyclic graph (DAG): each line names one step
  and the steps it waits for, so one file replaces a hand-typed queue of beads, like
  a recipe card the kitchen follows in order.
- The shape is one small module beside the supervisor, not a new queue. The full-size
  fleet orchestrator this series learns from keeps saved workflows in a database with
  named runs and per-step records, while this tutorial keeps one plain text file and
  reads the run state off the beads themselves.
- Tutorial 9 drove single beads through claim, build, merge, and close, but every chain
  still started from retyped beads: nothing saved the order of spec, code, and check.
- One trap is closed here. A step that names an unknown dependency fails fast at load
  time, so a typo stops the run before any bead opens instead of stalling halfway.

### Scope

1. Write one workflow file with three steps: spec, code after spec, check after code.
2. Open one bead per step, with each bead blocked until its parent steps close.
3. Drive the beads through the supervisor until every step closes, in order.

Left out on purpose: starting a run on a timer instead of by hand. Tutorial 11 fires
runs from a schedule you define once.

### The problem

```text
$ just tutorial
tut09: supervisor claims, spawns, reaps
uv run python -m swarm
spawn: first line -> opencode/smart
closed: result for first line
spawn: second line -> opencode/cheap
closed: result for second line
queue ready: none (two beads claimed, built, merged, closed)
```

The supervisor runs each bead you hand it, but the chain itself lives nowhere: run
spec, code, and check again tomorrow and you retype all three beads and their order.

### What changes

```text
src/swarm/
+   workflows.py        one file holds the saved chain of steps
~   queue.py            open a bead with parents, read one bead state
~   __main__.py         demo opens one workflow, closes each step in order
tests/
+   test_workflows.py
```

`+` is new, `~` is changed. The full change is `git diff tut09..tut10`.

## In detail

### How it works

Each line of the workflow file is one step: a name, plus the names it waits for after
a colon. Starting the workflow opens one bead per step in file order and maps each
waiting name to the bead already opened for it, so the beads carry the order as
ordinary dependencies. The demo then ticks the supervisor from tutorial 9: each tick
claims the one ready bead, builds it apart, merges it back, and closes it, which
unblocks the next step. The run state is derived from the bead states, so all closed
means done, any blocked means blocked, and anything running means running.

### Design decisions

- The file format stays plain text with one step per line. Three steps need no parser,
  and the loader still rejects unknown names before anything opens.
- Later steps wait on bead ids, not on step names. Names are for humans; the queue
  only understands bead ids, so the start step translates once and the queue never
  learns a new vocabulary.
- The run state is derived, not stored. A separate record could drift from the beads,
  so one function reads the bead states and answers done, blocked, running, or
  waiting each time you ask.

### The excerpt that carries the idea

**src/swarm/workflows.py**

```python
def start(path: Path, opener: Callable[..., str] = queue.create) -> dict[str, str]:
    """Open one bead per workflow step, in file order. Return step names to ids."""
    ids: dict[str, str] = {}
    for step in load(path):
        ids[step.name] = opener(step.name, tuple(ids[dep] for dep in step.deps))
    return ids
```

### Run it

```bash
git checkout tut10
just tutorial
```

```text
tut10: one workflow runs spec, code, check in order
uv run python -m swarm
opened: 3 steps (spec, code, check)
ready: write spec
closed: result for write spec
ready: write code
closed: result for write code
ready: check work
closed: result for check work
run status: done (3 of 3 steps closed in order)
```

### Key takeaways

- A workflow is a saved chain of steps: one file names each step and what it waits
  for, so you stop retyping the same graph of beads.
- Each step is one bead blocked on its parents, so it starts only when they close.
- Run state is derived from bead states, so it always agrees with the queue.

### What is still missing

Every run still starts by hand: nothing wakes the workflow on its own. A saved timer
that opens a run when its time comes is a schedule, and it arrives in tutorial 11.
