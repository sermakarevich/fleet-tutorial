# VISION — What the finished swarm runner looks like

This is the target. Every tutorial adds one file to this tree. No tutorial
reshuffles it. Reference build: /Users/sergii/git/fleet.

Full form: a beads-backed parallel orchestrator. It claims tasks, spawns one
headless worker per task in its own git worktree, merges results, retries
with sense, routes smart versus cheap models, and runs workflows, schedules,
and triggers.

---

## 1. Final folder tree of `src/swarm/`

```text
src/swarm/
├── __init__.py        # package marker
├── __main__.py        # entry point: python -m swarm
├── todo.py            # plain text TODO list (tut01 only, replaced by beads)
├── loop.py            # for-loop that runs one headless session after another
├── checkpoint.py      # per-task STATE.md plus RESULT.json: save and resume
├── human.py           # human-in-the-loop questions: ask, block, continue
├── queue.py           # beads queue: list, claim, close, reopen
├── runner.py          # parallel loop: how many workers, spawn, reap
├── worker.py          # one worker: build prompt, run harness CLI, write result
├── worktree.py        # one git worktree per task: create, merge, clean up
├── retry.py           # retry policy: which failures retry, when to block
├── routing.py         # model routing: smart plans, cheap executes, per-task pick
├── workflows.py       # saved graphs of steps: stages run in order
├── schedule.py        # cron schedules: open a task or workflow run on time
└── triggers.py        # event triggers: open a task when a signal fires
```

One line per file, what it does:

- `__main__.py` — parses the command and starts the runner.
- `todo.py` — reads the next item from a text file; beads replaces it.
- `loop.py` — runs tasks one by one until the list is empty.
- `checkpoint.py` — writes progress often so a new session can resume.
- `human.py` — lets a worker ask one question and wait for the answer.
- `queue.py` — the only module that talks to `bd`; claim, close, reopen.
- `runner.py` — keeps N workers busy; owns the claim-lease heartbeat.
- `worker.py` — spawns one headless harness CLI as a subprocess.
- `worktree.py` — isolates each task in its own branch copy; merges back.
- `retry.py` — counts failures per kind; blocks after the limit is hit.
- `routing.py` — picks harness plus model per task from its metadata.
- `workflows.py` — opens one bead per step when its parents are done.
- `schedule.py` — ticks on cron math; opens beads when a schedule is due.
- `triggers.py` — polls event sources; opens one bead per new event.

Rules the tree follows: one file, one job. High calls low. Imports point
down. Small files. No file named `utils.py`. Behaviour from tut04 on reads
task state from beads, never from the text file.

---

## 2. Justfile recipes (final set)

```text
just setup       # install deps with uv, check bd and harness CLI exist
just tutorial    # show what the current tag built (body changes per tag)
just test        # offline unit tests, no network, fake harness boundary
just lint        # ruff check
just fmt         # ruff format
just demo        # tiny end-to-end swarm on demo beads (needs real tools)
```

`just tutorial` is the only recipe the tutorial prose may call. Its body at
each tag shows that tag's concept. `just demo` is the capstone run: one
workflow, one schedule firing, one trigger firing.

---

## 3. What the finished runner can do

- Run tasks one by one from beads with `python -m swarm run`.
- Run up to N workers at once, each in its own worktree.
- Resume a crashed task from its checkpoint files.
- Ask a human one question and continue when the answer arrives.
- Retry crashes and stalls, then block with a reason instead of looping.
- Route planning tasks to a smart model and execution to a cheap one.
- Run a saved workflow file: spec, code, check, in order with dependencies.
- Open tasks on a cron schedule and on events such as a blocked task.
- Leave every run visible in beads: status, attempts, result.

Out of scope on purpose: the knowledge wiki and the phone chat from ARTICLE.md
sections 15–16. They use the runner; they are not part of it. The capstone
shows them as inputs and outputs only.

---

## 4. Definition of green

`just lint && just test` passes. `just tutorial` at the tag prints the output
copied into that tutorial's document. No secrets in the tree. Docs wrap at 100
characters.
