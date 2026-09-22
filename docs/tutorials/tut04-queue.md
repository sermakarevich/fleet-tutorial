# Tutorial 4 — Beads queue

After this tutorial your loop hands each task out exactly once, so two workers
never run the same item.

## In short

### The concepts

- You stop double-running tasks. The TODO (to-do) file is gone. Each task is a
  bead in a beads queue, and claiming a bead is atomic: it succeeds for exactly
  one caller, so a second worker that arrives late simply takes the next bead.
- The shape is one small module that shells out to the `bd` tool, not a new
  database you maintain. The full-size fleet orchestrator this series learns
  from uses the same beads claims and adds expiring leases with a heartbeat, so
  a crashed worker cannot hold a task forever.
- Tutorial 3 let one worker ask you a question mid-task, but the list was still
  a text file: two workers reading it at once would both take the top line.
- Two traps are closed here. A claim lost to a faster worker is skipped instead
  of rerun, and a task that fails goes back to open instead of vanishing.

### Scope

1. List the beads that are ready to run.
2. Claim one bead at a time, skipping beads another worker claimed first.
3. Close the bead on success, reopen it on failure.

Left out on purpose: parallel workers and crash recovery. Tutorial 5 runs
several workers at once and gives each claim a lease that expires.

### The problem

```text
$ just tutorial
worker A: draft the launch note
worker B: draft the launch note
result: ran twice, billed twice
```

The loop from tutorial 3 reads tasks from a plain TODO file. The file has no
safe way to hand a line out, so two workers that read it together grab the
same line.

### What changes

```text
src/swarm/
+   queue.py              beads claims through the bd tool, one caller wins
~   loop.py               claims beads instead of reading the TODO file
~   worker.py             defaults to the opencode harness
~   __main__.py           demo where two beads are claimed with no double-run
tests/
+   test_queue.py
```

`+` is a new file, `~` is a changed file. The full change is `git diff tut03..tut04`.

## In detail

### How it works

One task waits as one bead in the queue. The loop asks for the ready beads,
then claims the first one: beads grants the claim to exactly one caller. On a
win the loop runs the task and closes the bead. On a lost race the claim
raises, the loop tries the next bead, and nothing runs twice. On failure the
loop reopens the bead, so the next run picks it up again.

### Design decisions

- The claim is the only place where workers meet, and it lives inside beads.
  The loop needs no locks of its own, so adding workers later changes nothing here.
- Failure reopens the bead instead of closing it. A crashed task returns to the
  queue on its own, so one bad run cannot silently drop work.
- The queue module knows nothing about checkpoints or questions. It lists,
  claims, closes and reopens, so tutorials 2 and 3 keep working unchanged on
  top of beads. The fleet orchestrator this series learns from keeps this split
  and adds priorities and dependencies around it at scale.

### The excerpt that carries the idea

**src/swarm/queue.py**

```python
def claim_next() -> Task | None:
    """Claim one ready bead, or None when the queue is empty.

    Beads grants each claim to one caller only. A lost race raises here,
    so the loop just tries the next bead instead of running one twice.
    """
    for task in list_ready():
        try:
            _run_bd(["update", task.bead_id, "--claim"])
        except subprocess.CalledProcessError:
            continue
        return task
    return None
```

### Run it

```bash
git checkout tut04
just tutorial
```

```text
tut04: beads queue
uv run python -m swarm
result: result for first chore
result: result for second chore
done: claimed 2, ran 2, double-runs 0
queue empty: both beads closed
```

### Key takeaways

- A beads claim is atomic: exactly one worker wins it, and the loser takes the
  next bead instead of rerunning the same one.
- The loop closes a bead on success and reopens it on failure, so failed tasks
  return to the queue instead of vanishing.
- Checkpoints and human questions sit on top unchanged: the queue only decides
  which task runs next.

### What is still missing

One worker claiming in a loop is safe but slow, and a worker that dies while
holding a bead leaves it claimed forever. Tutorial 5 runs workers in parallel
and turns each claim into a lease that expires.
