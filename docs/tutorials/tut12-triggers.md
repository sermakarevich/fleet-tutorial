# Tutorial 12 — Triggers and capstone

After this tutorial a blocked bead calls for help on its own, and one demo
runs a workflow, a schedule, and a trigger together as a small swarm.

## In short

### The concepts

- You watch one event source each poll and open an investigator bead for every
  new blocked task, like a nurse who calls a doctor for each new patient.
- The shape is one small module beside the supervisor, same as schedules in
  tutorial 11. The full-size fleet orchestrator stores triggers and fired
  events in a database, while this tutorial keeps one function and a seen set.
- Tutorial 11 woke runs by the clock, but a task that got stuck between ticks
  waited for the next minute: nothing reacted to the world outside the timer.
- Two traps are closed here. A second poll must not open a second investigator
  for the same blocked bead, so each firing is remembered in a seen set, and
  each poll opens at most two investigators against a flood of blocked beads.

### Scope

1. List the blocked beads and keep the ones no earlier poll has handled.
2. Open one read-only investigator bead per new blocked bead, at most two per poll.
3. Run the capstone demo: one workflow, one schedule firing, one trigger firing.

Left out on purpose: the knowledge wiki and phone-chat patterns from article
sections 15 and 16 stay usage, not code this series builds.

### The problem

```text
$ just tutorial
tut11: one due schedule fires, one stays quiet
uv run python -m swarm
fired: morning report -> bead-1
quiet: later job (not due)
```

The timer fires, but a worker that parks a task as blocked gets no answer: no
investigator opens, because nothing watches the world outside the clock.

### What changes

```text
src/swarm/
+   triggers.py         one module opens an investigator per new blocked bead
+   prompts/investigate_blocked.txt   read-only prompt naming the stuck bead
~   queue.py            a blocked-bead reader beside the ready reader
~   __main__.py         demo runs a workflow, a schedule, and a trigger
tests/
+   test_triggers.py
~   test_setup.py       entrypoint now expects all three firings
```

`+` is new, `~` is changed. The full change is `git diff tut11..tut12`.

## In detail

### How it works

Each poll asks the queue for its blocked beads and drops every id the seen set
already holds, so only new events stay due. Firing opens one ordinary bead
whose prompt names the stuck bead and orders a read-only analysis, then adds
the id to the seen set, so the next poll stays quiet. The capstone demo runs
all three starters at once: a two-step workflow, a due schedule line, and one
step parked as blocked so the trigger opens its investigator.

### Design decisions

- The investigator prompt is read-only: it analyses the stuck bead but never
  edits it. A second writer on blocked work would collide with the human who
  owns the decision, so the investigator reports and stops.
- The seen set remembers fired bead ids, not poll counts. A repeat poll sees
  its own marks and stays quiet, while a newly blocked bead is a new id that
  fires at once.
- Each poll opens at most two investigators, so a flood of blocked beads
  becomes a short queue of analyses instead of a burst of workers.

### The excerpt that carries the idea

**src/swarm/triggers.py**

```python
def poll(
    seen: set[str],
    lister: Callable[[], list[queue.Task]] = queue.list_blocked,
    opener: Callable[..., str] = queue.create,
    limit: int = MAX_OPEN,
) -> list[str]:
    """Open investigators for new blocked beads, at most `limit` per poll."""
    found: list[str] = []
    for task in due(lister(), seen):
        if len(found) >= limit:
            break
        found.append(fire(task, seen, opener))
    return found
```

### Run it

```bash
git checkout tut12
just tutorial
```

```text
tut12: blocked task opens an investigator; demo swarm runs
uv run python -m swarm
workflow: 2 steps (write spec, write code)
fired: morning report -> bead-3
quiet: later job (not due)
trigger: blocked bead-1 -> bead-4
```

### Key takeaways

- A trigger is a saved watcher: when a new event appears in the world, it opens
  one ordinary bead or starts one workflow run without you typing anything.
- Each event fires exactly once, because fired bead ids stay in a seen set that
  every later poll checks first.
- Schedules, workflows, and triggers all create ordinary beads, so the series
  ends where it started: one queue grown from a plain loop into your swarm.

### Where to go next

Reread article sections 15 to 17 for the wiki and phone patterns this runner
feeds. Then keep building toward the full-size fleet orchestrator when one
machine stops being enough.
