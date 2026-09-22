# Tutorial 7 — Retries and dead-letter

After this tutorial a failing task retries a few times, then parks for a human.

## In short

### The concepts

- You stop one bad task from spinning the loop forever. Each failure is
  counted, retries wait longer each time, and a task past the limit parks as
  blocked with a reason, in a place queue people call a dead-letter queue.
  Think of a bouncer who lets you knock three times, then takes your name.
- The shape is a small retry module beside the runner, not a new queue. The
  full-size fleet orchestrator this series learns from counts the same way,
  and also sends the parked task to the human as a question.
- Tutorial 6 reopened beads that clashed on merge, but a bead that fails on
  its own came back forever: nothing counted its attempts or parked it.
- Two traps are closed here. A dead lease from a crashed worker obeys the
  same limit, so silence cannot loop forever either, and the wait between
  tries grows from a short capped table.

### Scope

1. Name each failure as a crash, a stall, or a partial result.
2. Retry a failing bead while its streak of failures is within the limit.
3. Park the bead as blocked with a reason once the limit is reached.

Left out on purpose: picking a model and harness per task. Tutorial 8 plans
on a smart model, executes on a cheap one, and adds a second harness.

### The problem

```text
$ just tutorial
failed: hopeless chore raised, reopened for retry
failed: hopeless chore raised, reopened for retry
... never stops
```

Tutorial 6 reopens every failed bead, so a hopeless task is claimed again on every pass.

### What changes

```text
src/swarm/
+   retry.py            failure kinds, retry limit, wait between tries
~   runner.py           failing beads retry, exhausted ones park as blocked
~   queue.py            new block call that parks a bead with a reason
~   __main__.py         demo where one task is flaky and one is hopeless
tests/
+   test_retry.py
```

`+` is new, `~` is changed. The full change is `git diff tut06..tut07`.

## In detail

### How it works

One task waits as one bead in the queue. The runner claims it and runs it.
When the task raises, the runner names the failure: a timeout is a stall and
anything else is a crash, while output starting with `PARTIAL:` names a
partial result without raising. The runner appends the kind to that bead's
streak and checks the limit: inside the limit it waits a short growing pause
and reopens the bead, past it the bead parks as blocked with a reason and is
never claimed again. A dead lease found by the heartbeat sweep goes through
the same check, so a worker that dies quietly parks too.

### Design decisions

- The limit counts failures in a row of the same kind. One odd crash does not
  doom a task, so a bead that fails differently each time keeps its chances.
- The dead-lease sweep obeys the same limit. A silent crash costs a few
  retries instead of a stuck loop. The fleet orchestrator this series learns
  from also sends the parked bead to the human as a question.
- The wait between tries grows from a short table with a cap. A flaky task
  gets room to recover, so retries pause instead of hammering the queue.

### The excerpt that carries the idea

**src/swarm/retry.py**

```python
def should_retry(history: list[Kind]) -> bool:
    """True while the latest failure streak is still within the limit."""
    if not history:
        return True
    return consecutive(history, history[-1]) <= MAX_RETRIES


def backoff_for(streak: int) -> float:
    """Seconds to wait before retrying a streak this long."""
    return BACKOFF[min(max(streak, 1), len(BACKOFF)) - 1]
```

### Run it

```bash
git checkout tut07
just tutorial
```

```text
tut07: retries and dead-letter
uv run python -m swarm
result: result for flaky chore
blocked: hopeless chore — crash failed 4 times in a row, needs a human to look
queue ready: none (one closed, one parked for a human)
```

### Under the hood

A task can ask for a retry without raising: `PARTIAL:` output counts as a
partial result.

### Key takeaways

- Failure kinds decide the streak: timeouts stall, raised errors crash, and
  `PARTIAL:` text reports a half-done task.
- A bead inside the limit reopens after a short growing pause, so a flaky
  task recovers on its own: the demo task fails twice, then succeeds.
- A bead past the limit parks as blocked with a reason, so a hopeless task
  waits for a human instead of looping forever.

### What is still missing

Every task still runs through one harness with one model, so a costly smart
model does cheap work. Tutorial 8 routes planning to a smart model and
execution to a cheap one, on more than one harness starting with opencode.
