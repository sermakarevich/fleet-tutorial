# Tutorial 11 — Schedules on cron

After this tutorial a saved timer opens your beads for you, so the daily report
starts itself.

## In short

### The concepts

- You read one schedule file each minute and open a bead or a workflow run whenever
  its timer line matches the clock, like an alarm clock that files the paperwork
  itself.
- The shape is one small module beside the supervisor, not a new queue. The
  full-size fleet orchestrator this series learns from keeps schedules in a database
  with an overlap policy, time zones, and next-firing math, while this tutorial keeps
  one plain text file and a record of what already fired this minute.
- Tutorial 10 saved the chain of spec, code, and check in one file, but every run
  still started by hand: nothing woke the workflow on its own.
- Two traps are closed here. A second tick inside the same minute must not open the
  bead twice, so each firing is recorded against its minute slot, and a bad timer
  line fails fast at load instead of silently never firing.

### Scope

1. Write one schedule file with two lines: one due now, one due in another minute.
2. Tick the schedules at the current minute and fire what is due into the queue.
3. Prove the quiet line stays quiet and a repeat tick in the same minute fires
   nothing.

Left out on purpose: starting work when something happens in the world instead of
when the clock says so. Tutorial 12 fires runs from event triggers and ends with
the capstone swarm.

### The problem

```text
$ just tutorial
tut10: one workflow runs spec, code, check in order
uv run python -m swarm
opened: 3 steps (spec, code, check)
...
run status: done (3 of 3 steps closed in order)
```

The chain runs, but only because you typed the command: want the daily report again
tomorrow and you retype everything by hand, because nothing wakes a run on its own.

### What changes

```text
src/swarm/
+   schedule.py         one file holds timer lines that fire beads or runs
~   __main__.py         demo fires the due schedule, skips the quiet one
tests/
+   test_schedule.py
~   test_setup.py       entrypoint now expects fired plus quiet lines
```

`+` is new, `~` is changed. The full change is `git diff tut10..tut11`.

## In detail

### How it works

Each line of the schedule file names one timer: a name, a cron expression with five
time fields, and an action that opens one bead or starts one workflow run. A tick
asks every line two questions: does the timer match this minute, and did this name
already fire in this minute slot. Firing opens an ordinary bead or starts an
ordinary workflow run through the queue and workflow modules from tutorials 4 and
10, then records the name against the minute slot, so a second tick in the same
minute finds nothing due and the next minute fires again.

### Design decisions

- The timer language stays tiny: a star, a step such as every fifteen minutes, or
  one plain number per field. Full cron needs names and ranges, so the small matcher
  covers daily and interval schedules with far less code to get wrong.
- The fired record is one minute slot per name, not a timestamp log. A repeat tick
  in the same minute sees its own mark and stays quiet, while the next minute is a
  new slot that fires again.
- A fired schedule creates ordinary beads and runs, never a special kind of task.
  The queue already knows how to claim, merge, and close them, so the timer adds no
  second vocabulary for workers to learn.

### The excerpt that carries the idea

**src/swarm/schedule.py**

```python
def tick(schedules: list[Schedule], now: datetime, fired: dict[str, str]) -> list[Schedule]:
    """Due schedules at `now`: cron matches and this minute slot never fired."""
    return [
        entry
        for entry in schedules
        if matches(entry.cron, now) and fired.get(entry.name) != slot(now)
    ]
```

### Run it

```bash
git checkout tut11
just tutorial
```

```text
tut11: one due schedule fires, one stays quiet
uv run python -m swarm
fired: morning report -> bead-1
quiet: later job (not due)
```

### Key takeaways

- A schedule is a saved timer line: when its cron expression matches the minute, it
  opens one bead or starts one workflow run without you typing anything.
- Each firing is recorded against its minute slot, so a timer fires exactly once
  per minute no matter how often the tick runs.
- Fired work is ordinary beads and runs, so everything the queue already enforces
  still applies.

### What is still missing

Some work should start when something happens, not when the clock says so: a blocked
task wants an investigator now, not at the next minute. That watcher is a trigger,
and it arrives in tutorial 12, which ends with the capstone swarm running a
workflow, a schedule, and a trigger together.
