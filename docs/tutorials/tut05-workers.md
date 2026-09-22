# Tutorial 5 — Parallel workers and leases

After this tutorial your loop runs three tasks at once, and a task held by a
crashed worker returns to the queue on its own.

## In short

### The concepts

- Three workers stay busy at once, and each bead is still claimed exactly
  once. Tutorial 4 made claims safe but ran one worker at a time, so the
  queue was correct and slow.
- A claim becomes a lease: a claim with a heartbeat that expires. Each running task
  refreshes its heartbeat, and a lease quiet past its limit returns to the queue,
  so a dead worker cannot lock a bead forever.
- The shape is a small runner that fans tasks out to threads, not a new queue.
  The full-size fleet orchestrator this series learns from runs real worker
  processes instead and caps how many may run, since ten workers can burn
  through a model subscription in minutes.
- One trap is closed here. A quiet lease is retried only after a fixed quiet
  period, so a slow task is not mistaken for a dead one.

### Scope

1. Claim beads up to a fixed worker count at a time.
2. Refresh one heartbeat per running task and reap each result.
3. Reopen leases quiet past the limit, so they run again.

Left out on purpose: keeping workers out of each other's files. Tutorial 6
gives each task its own worktree and merges the result back.

### The problem

```text
$ just tutorial
crashed: worker died holding second chore
result: second chore never runs again
```

The loop from tutorial 4 reopens a bead only when the task raises. A worker
that dies without answering never returns, so its bead stays claimed forever.

### What changes

```text
src/swarm/
+   runner.py           parallel loop with leases that expire
~   __main__.py         demo where three workers run and one crashes
tests/
+   test_runner.py
```

`+` is a new file, `~` is a changed file. The full change is `git diff tut04..tut05`.

## In detail

### How it works

Three workers share one queue. The runner claims beads until every worker is
busy, and each claim becomes a lease stamped with the current time. While a task
runs, its worker refreshes the lease heartbeat in the background. Each worker
runs its task through the opencode harness, the agent command line tool that
starts headless sessions. When a task finishes, the runner closes its bead and
claims the next one. When a task raises, the runner marks its lease dead, and
the next sweep reopens beads quiet past the limit, so the queue hands them out.

### Design decisions

- The heartbeat lives beside the task, not inside the queue. Beads still only
  claims and closes, so the lease limit is retuned without touching it.
- A dead lease reopens instead of failing the run. One crash costs a retry,
  not a stuck queue, so a bad task cannot block healthy ones.

### The excerpt that carries the idea

**src/swarm/runner.py**

```python
    def sweep(now: float) -> None:
        with lock:
            dead = [
                bead_id
                for bead_id, lease in leases.items()
                if not lease.alive and now - lease.heartbeat > lease_ttl
            ]
        for bead_id in dead:
            with lock:
                lease = leases.pop(bead_id, None)
            if lease is None:
                continue
            try:
                queue.reopen(lease.task)
            except Exception:
                with lock:
                    leases[bead_id] = lease
```

### Run it

```bash
git checkout tut05
just tutorial
```

```text
tut05: parallel workers and leases
crashed: second chore died holding its lease
result: result for first chore
result: result for second chore
result: result for third chore
workers at peak: 3
dead lease reclaimed: second chore ran again and closed
done: claimed 3, ran 4, double-runs 0
queue empty: all beads closed
```

### Key takeaways

- Three workers share one queue: the runner claims a new bead whenever a
  worker goes idle, so no bead runs twice and no worker sits idle.
- A lease is a claim with a heartbeat: a lease quiet past its limit reopens,
  so a crashed worker costs a retry instead of a stuck task.
- The queue module is unchanged: claiming, closing and reopening still live
  in beads, and leases sit beside them.

### What is still missing

Workers now run side by side in one folder, so two tasks editing the same files
still clash. Tutorial 6 gives each task its own worktree and merges it back.
