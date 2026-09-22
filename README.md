# Swarm

A hands-on tutorial that builds a *swarm runner* (a small program that runs a
list of tasks through AI workers without you watching each step) from a TODO
(to-do) loop to a parallel orchestrator (the program that decides which task
runs where and when), one small step at a time in Python.

## Quick start

```bash
cp .env.example .env   # then add your keys as later tutorials ask
just setup
just tutorial          # shows what the current tutorial built
just test              # offline unit tests, no network needed
```

## How to follow the tutorials

Each tutorial is a document in `docs/tutorials/` and a git tag (`tut00`,
`tut01`, ...). Read the documents here on `main`; run the code at the tag.
`main` is the latest code and is not kept runnable for older tutorials. The
tag freezes the code exactly as that tutorial built it. A document is improved
in place on `main`, so the copy inside an older tag may be behind the one you
read here.

The document has two layers. **In short** gives the concepts, the scope and
the problem in plain language, no code. **In detail** explains how the code
works and why it is built that way. Read only the first layer of every
tutorial for the story; read the second to build it.

For each tutorial:

```bash
git checkout tut01              # the code exactly as the tutorial describes it
just setup                      # once per checkout, installs the locked setup
just tutorial                   # shows what this tutorial built
just test                       # the tests for this tutorial, no network needed
git diff tut00..tut01 --stat    # every file this tutorial added or changed
```

Each tutorial adds one concept and fixes one limitation of the step before, so
the diff between two neighbouring tags is one concept. `git tag --list 'tut*'`
shows how far the series goes. `git checkout main` returns to the latest code.

You need `uv`, `just` and, from tut08 on, a model key in `.env` (see
`.env.example`). Tutorials that call the model say so; everything else runs
offline.

## Tutorials

| Tutorial | Tag | Document |
|---|---|---|
| 0 — Setup | `tut00` | [tut00-setup.md](docs/tutorials/tut00-setup.md) |
| 1 — TODO list and loop | `tut01` | [tut01-loop.md](docs/tutorials/tut01-loop.md) |
| 2 — Checkpoint and resume | `tut02` | [tut02-checkpoint.md](docs/tutorials/tut02-checkpoint.md) |
| 3 — Human in the loop | `tut03` | [tut03-human.md](docs/tutorials/tut03-human.md) |
| 4 — Beads queue | `tut04` | [tut04-queue.md](docs/tutorials/tut04-queue.md) |
| 5 — Parallel workers plus leases | `tut05` | [tut05-workers.md](docs/tutorials/tut05-workers.md) |
| 6 — Worktree isolation plus merge | `tut06` | [tut06-worktree.md](docs/tutorials/tut06-worktree.md) |
| 7 — Retries plus dead-letter | `tut07` | [tut07-retry.md](docs/tutorials/tut07-retry.md) |
| 8 — Model routing plus multi-harness | `tut08` | [tut08-routing.md](docs/tutorials/tut08-routing.md) |
| 9 — The runner becomes an orchestrator | `tut09` | [tut09-supervisor.md](docs/tutorials/tut09-supervisor.md) |
| 10 — Workflows as saved graphs | `tut10` | [tut10-workflows.md](docs/tutorials/tut10-workflows.md) |
| 11 — Schedules on cron | `tut11` | [tut11-schedule.md](docs/tutorials/tut11-schedule.md) |
| 12 — Triggers on events plus capstone | `tut12` | [tut12-triggers.md](docs/tutorials/tut12-triggers.md) |

All thirteen tutorials are published; the series is complete.

The concept behind each row and the order of the story are in `docs/dev/GOAL.md`.

## For contributors

Everything about how this repo is built lives in `docs/dev/`: the goal
(`GOAL.md`), the finished shape (`VISION.md`), the tutorial method
(`TUTORIAL_METHOD.md`) and the tutorial template. Coding rules are in
`AGENTS.md`.
