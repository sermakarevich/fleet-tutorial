# Tutorial 9 — Supervisor

After this tutorial one supervisor tick claims a bead, runs it apart, merges it back,
and closes it.

## In short

### The concepts

- You run one tick per bead: claim, spawn, reap, merge, close. The tick does bounded
  work and exits, so an empty queue or a failure is one quiet return, not a stuck loop.
  Think of a lifeguard who watches one swimmer at a time and only blows the whistle
  when needed.
- The shape is one small function beside the parallel loop, not a new runner. The
  full-size fleet orchestrator this series learns from ticks the same way, except it
  also asks a human when a bead blocks instead of only reopening it.
- Tutorial 8 routed each task to the right model and harness, but you still started
  every run by hand and the demo touched no queue, so nothing claimed, merged, or
  closed on its own.
- Two traps are closed here. Failures count up across ticks through one shared
  record, so a flaky bead retries and a hopeless one blocks instead of looping
  forever, and a merge clash reopens the bead instead of closing half-merged work.

### Scope

1. Claim one ready bead per tick and stop quietly when the queue is empty.
2. Run the bead apart in its own worktree branch, then merge the branch back.
3. Close on a clean merge, reopen on failure or clash, block past the retry limit.

Left out on purpose: saving a whole chain of beads as one reusable file. Tutorial 10
stores that chain as a workflow that opens spec, code, and check tasks in order.

### The problem

```text
$ just tutorial
plan: design the queue -> opencode/smart: result for design the queue
exec: write the loop -> opencode/cheap: result for write the loop
exec: write the tests -> opencode/cheap: result for write the tests
queue ready: none (demo tasks need no beads)
```

Tutorial 8 routes each task well but knows nothing about the queue: you hand-hold
every bead yourself, and nothing claims, merges, or closes on its own.

### What changes

```text
src/swarm/
~   runner.py           one tick claims, spawns, reaps, merges, closes
~   __main__.py         demo runs two beads through the supervisor
tests/
+   test_supervisor.py
```

`+` is new, `~` is changed. The full change is `git diff tut08..tut09`.

## In detail

### How it works

Each tick claims one ready bead and resolves its route, then builds it apart in its
own worktree branch. The worker runs there, the branch commits and merges back, and a
clean merge closes the bead. A crash or a bad result reopens the bead for another
tick, a merge clash reopens it for repair, and a bead that fails past the limit
blocks with a reason instead of retrying forever.

### Design decisions

- One tick does bounded work and exits. An empty queue needs no special case, so the
  demo drives the run with a plain loop that stops when a tick returns nothing.
- The failure record travels across ticks in one shared mapping. Retries count up
  instead of restarting, so a flaky bead recovers and a hopeless one blocks.
- A merge clash never closes. Half-merged work reopens for repair, so the base
  branch only ever gains clean merges.

### The excerpt that carries the idea

**src/swarm/runner.py**

```python
        merged = worktree.merge_back(repo, branch, base)
        if merged:
            queue.close(task)
            return result
        queue.reopen(task)
        return None
```

### Run it

```bash
git checkout tut09
just tutorial
```

```text
tut09: supervisor claims, spawns, reaps
uv run python -m swarm
spawn: first line -> opencode/smart
closed: result for first line
spawn: second line -> opencode/cheap
closed: result for second line
queue ready: none (two beads claimed, built, merged, closed)
```

### Key takeaways

- One supervisor tick claims a bead, runs it apart, merges it back, and closes it,
  so the loop finally drives itself instead of needing hand-holding.
- Failures count up across ticks in one shared record, so flaky beads retry and
  hopeless ones block with a reason.
- A merge clash reopens instead of closing, so the base branch only gains clean
  merges.

### What is still missing

You still retype the same chain of beads every time: nothing saves spec, code, and
check as one reusable chain yet. That saved chain is a workflow, and it arrives in
tutorial 10.
