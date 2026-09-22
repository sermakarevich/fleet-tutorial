# GOAL — Tutorial: Build a Swarm Runner Step by Step

**Status:** planning · **Owner:** Sergii

---

## 1. What we are building

A **hands-on tutorial** that builds a *swarm runner* from scratch, one small
step at a time, in Python.

> **Swarm runner** = a small program that takes a list of tasks and runs them
> through AI workers without you watching each step. It starts as a loop over
> a text file. It ends as a parallel orchestrator.
>
> **Orchestrator** = the program that decides which task runs where and when.
> Fleet, in /Users/sergii/git/fleet, is the full-size example this tutorial
> learns from.
>
> **Worker** = one headless session doing one task. Headless means started by
> a script with a prompt, with no human at the keyboard.
>
> **Harness** = the agent command line interface (CLI) that runs a session,
> for example Claude Code, OpenCode, Codex, or pi. CLI means a tool you run in
> a terminal.
>
> **Beads** = an open-source issue tracker built for AI agents. We use it as
> our task queue. Each record is one task. Its command line tool is `bd`.

Each tutorial ends with **runnable code** that does something visible. Each
tutorial fixes **one limitation** of the previous step. The tutorial is the
deliverable. The swarm runner it produces is the worked example.

The arc, following docs/ARTICLE.md: a for-loop over a TODO file becomes a
loop over beads. Then parallel workers, leases, worktrees, retries, model
routing (a smart model plans, a cheap model executes), workflows (a saved
sequence of tasks with dependencies), schedules (cron, meaning run on a
timer), and triggers (event-driven, meaning run when something happens).

---

## 2. Audience

A Python engineer who has called a Large Language Model (LLM) Application
Programming Interface (API) before but has never built a runner that spawns
AI sessions.

Plain language. Short sentences. One idea per sentence. Every abbreviation is
spelled out on first use.

We never explain Python basics. That reads as Captain Obvious.

---

## 3. Hard constraints

| Constraint | Decision |
|---|---|
| Language | **Python** only (3.12+) |
| Package / env manager | **uv** — `uv init`, `uv add`, `uv run`, lockfile committed |
| Task runner | **justfile** — every tutorial runnable as `just tutorial`, plus `just fmt`, `just lint`, `just test` |
| Task queue | **beads** — `bd` CLI. Safe claiming, dependencies, priorities |
| Workers | **headless harness CLI** — the runner spawns it as a subprocess and reads its output |
| Secrets | Never committed, never printed, never pasted into chat |

**No hidden magic rule:** if a step can be written with ~30 lines of our own
code instead of importing a prebuilt abstraction, we write the 30 lines
first. The point is to see the machinery.

Method source: /Users/sergii/git/harness/docs/dev/TUTORIAL_METHOD.md,
_Template.md (`_TEMPLATE.md`), GOAL.md, and coding rules in
/Users/sergii/git/harness/AGENTS.md.

---

## 4. Tutorial outline (each tutorial = one limitation fixed)

ARTICLE.md has 17 sections. We map them into 13 tutorials, tut00–tut12.
Sections 15–16 (knowledge wiki, chat-from-phone) are usage patterns. They
appear in the capstone as inputs and outputs, not as code we build.

| # | Concept | Limitation fixed | What reader sees |
|---|---|---|---|
| tut00 | Project setup | no shared starting point | `just tutorial` runs the offline tests |
| tut01 | TODO list plus for-loop (Art. 1–2) | you type "next please" by hand | loop runs two demo tasks in a row |
| tut02 | Checkpoint and resume (Art. 3) | a crash loses all progress | killed task resumes from STATE.md |
| tut03 | Human in the loop (Art. 4) | worker cannot ask a question | worker blocks, human answers, run continues |
| tut04 | Beads queue (Art. 5–6) | two workers grab the same item | two tasks claimed with no double-run |
| tut05 | Parallel workers plus leases (Art. 7) | crashed worker locks a task forever | 3 workers run, dead lease returns to queue |
| tut06 | Worktree isolation plus merge (Art. 8) | workers overwrite each other | each task builds in its own worktree, merges clean |
| tut07 | Retries plus dead-letter (Art. 6 tail) | one failure retries forever | flaky task retries twice, then blocks for human |
| tut08 | Model routing plus multi-harness (Art. 9–10) | one dear model does everything | plan on smart model, execute on cheap one |
| tut09 | The runner becomes an orchestrator (Art. 11) | the loop knows nothing | one supervisor claims, spawns, reaps, merges |
| tut10 | Workflows as saved graphs (Art. 12) | same task graph retyped each time | one workflow file runs spec, code, check in order |
| tut11 | Schedules on cron (Art. 13) | someone must start each run | daily report task opens on its own |
| tut12 | Triggers on events plus capstone (Art. 14–17) | nothing reacts to the world | blocked task opens an investigator; demo swarm runs |

Tutorials tut00–tut06 are the **minimum viable runner**. Tutorials tut07–tut12
are the parts teams add once tasks run longer than a few minutes. Each is
skippable on its own, which is itself a lesson: match the runner to the job.

---

## 5. Repository layout (target)

```text
fleet-tutorial/
├── justfile             # just tutorial, just fmt, just lint, just test
├── pyproject.toml       # uv-managed
├── uv.lock
├── docs/
│   ├── ARTICLE.md       # the 17-stage story this series follows
│   ├── dev/             # GOAL, method, template, vision (these files)
│   └── tutorials/      # tutorial prose, one file per tutorial
├── src/swarm/           # the runner package, grown tutorial by tutorial
└── tests/
```

Each tutorial adds code rather than rewriting it. The final `src/swarm/` is
the sum of every step. The git history *is* the tutorial. Full file list is
in `docs/dev/VISION.md`.

---

## 6. Definition of done

1. `just setup && just tutorial` works on a clean machine with only `uv`,
   `bd`, and one harness CLI installed.
2. Every tutorial runs standalone and prints something a reader can see.
3. Tutorial tut12 runs a small swarm: one workflow, one schedule firing, one
   trigger firing, all visible in beads.
4. No secret ever appears in the repo, in the logs, or in tutorial output.
5. Prose is readable by a Python engineer who has never spawned a worker.
6. Each doc file is under 200 lines, except the template. Prose wraps at 100
   characters.
