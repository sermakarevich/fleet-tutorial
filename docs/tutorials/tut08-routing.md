# Tutorial 8 — Model routing and harnesses

After this tutorial planning tasks run on a smart model, execution tasks on a cheap one,
and each task names its harness.

## In short

### The concepts

- You split tasks into planning and execution. A plan task needs judgment, so it gets
  the smart, dear model; an execution task follows a plan, so it gets the cheap model.
  Think of an architect who draws the house and a crew who builds it.
- The shape is a small routing module beside the worker, not a new runner. The
  full-size fleet orchestrator this series learns from routes the same way, except it
  picks from five harnesses while this tutorial knows two.
- Tutorial 7 counted failures and parked hopeless tasks, but every task still ran
  through one harness with one model, so a costly smart model did cheap work too.
- Two traps are closed here. A task with no labels still routes somewhere sensible
  instead of crashing, and an unknown harness name falls back with a warning instead
  of failing the run.

### Scope

1. Label each task as a plan or an execution in its metadata.
2. Route each task to the smart or the cheap model from environment settings.
3. Pick the task harness per task, with opencode as the default harness.

Left out on purpose: a supervisor that watches the queue and spawns workers on its
own. Tutorial 9 turns the loop into an orchestrator that claims, spawns, reaps, and
merges.

### The problem

```text
$ just tutorial
result: result for flaky chore
blocked: hopeless chore — crash failed 4 times in a row, needs a human to look
```

Tutorial 7 runs every task through one harness with one model, so the dear smart model
also does the cheap execution work.

### What changes

```text
src/swarm/
+   routing.py          smart model plans, cheap model executes
~   worker.py           picks harness and model per task
~   __main__.py         demo with plan and execution tasks
tests/
+   test_routing.py
```

`+` is new, `~` is changed. The full change is `git diff tut07..tut08`.

## In detail

### How it works

Each task carries small metadata: its kind, plan or execution, and its harness name.
The worker asks the routing module before spawning the harness, and the routing module
answers with a route: a harness plus a model. Plan tasks get the smart model,
everything else gets the cheap one, and both model names come from environment
variables so you change them without touching code. The worker then starts that
harness binary with the prompt, so one run can plan in one harness and execute in
another.

### Design decisions

- The kind travels in task metadata, not in code branches. New task kinds need no new
  call sites, so adding a reviewer pass later is one label, not a rewrite.
- An unknown harness falls back with a warning. One typo parks nothing, so a
  mislabeled task still runs instead of blocking the queue.
- Model names live in environment variables with plain fallbacks. The demo runs with
  no keys set, so you see the routing before you pay for a model.

### The excerpt that carries the idea

**src/swarm/routing.py**

```python
def pick(meta: Mapping[str, str] | None = None, settings: Settings | None = None) -> Route:
    """Harness plus model for one bead from its metadata mapping."""
    active = settings or Settings.load()
    labels = dict(meta or {})
    kind = labels.get(KIND_KEY, DEFAULT_KIND)
    model = active.smart_model if kind == Kind.PLAN.value else active.cheap_model
    name = labels.get(HARNESS_KEY, DEFAULT_HARNESS)
    if name not in (Harness.OPENCODE.value, Harness.PI.value):
        warnings.warn(f"unknown harness {name!r}, using {DEFAULT_HARNESS}", stacklevel=2)
        name = DEFAULT_HARNESS
    return Route(harness=name, model=model)
```

### Run it

```bash
git checkout tut08
just tutorial
```

```text
tut08: model routing and second harness
uv run python -m swarm
plan: design the queue -> opencode/smart: result for design the queue
exec: write the loop -> opencode/cheap: result for write the loop
exec: write the tests -> opencode/cheap: result for write the tests
queue ready: none (demo tasks need no beads)
```

### Key takeaways

- Plan tasks route to the smart model and execution tasks to the cheap one, so you
  spend the dear model only where judgment matters.
- The harness is per-task metadata too, so one run can mix harnesses instead of
  marrying one.
- Missing labels and unknown harness names fall back to safe choices with a warning,
  so routing never blocks the queue on its own.

### What is still missing

You still start the run by hand and the demo needs no queue: nothing watches beads,
spawns workers, and merges results on its own. Tutorial 9 turns this loop into a
supervisor that does exactly that.
