# Tutorial 0 — Setup

After this tutorial you own a runnable project where one command runs the offline checks.

## In short

### The concepts

- You build the shared starting point: one layout, one tool chain, one command
  that proves it works.
- The shape mirrors the finished runner from the start: code under `src/swarm/`,
  behaviour checks under `tests/`, recipes in one `justfile`, prose in `docs/`.
  The fleet orchestrator this series learns from grew the same way, except it
  also carries schedules, triggers and model routing you meet from tutorial 7 on.
- There is no earlier tutorial, so nothing is fixed yet. This one removes the
  "it works on my machine" failure before any runner code exists.
- Two traps are closed on day one. Dependencies are locked, so every reader
  installs the same versions. Secrets stay out of git, so no key ever lands in
  the history.

### Scope

1. Describe the package and its tools in `pyproject.toml`, locked in `uv.lock`.
2. Add `justfile` recipes: `setup`, `tutorial`, `fmt`, `lint`, `test`.
3. Add the smallest runnable package plus one offline test.
4. Write the contributor rules, the series home page and this document.

What is left out on purpose: every runner behaviour. Tutorial 1 adds the TODO
(to-do) list and the loop.

### The problem

```text
$ just tutorial
error: no justfile found
```

Without a shared starting point every reader invents their own layout, and no
command proves the setup works.

### What changes

```text
.
+ AGENTS.md           coding rules every worker follows
+ README.md           series home page with the tutorial table
+ justfile            setup, tutorial, fmt, lint and test recipes
+ pyproject.toml      package metadata and tool settings
+ uv.lock             exact dependency versions
docs/tutorials/
+ tut00-setup.md      this document
src/swarm/
+ __init__.py         package marker
+ __main__.py         entry point, prints setup OK
tests/
+ test_setup.py       offline checks the package imports and runs
```

New files are marked `+`. Nothing is changed or removed yet, so no `~` or `-`
rows appear.

## In detail

### How it works

`just tutorial` runs two steps. First it runs the test suite, which checks the
package imports and runs the entry point as a subprocess with no network. Then
it runs the entry point itself and prints `setup OK`. Either step fails loudly
when the setup is broken, so one command tells you the ground is solid.

### Design decisions

- One recipe proves the setup. A reader who runs `just tutorial` and sees
  `setup OK` knows the tools, the lockfile and the package agree.
- Tests run offline. The boundary rule for the whole series starts here: workers
  are faked at the subprocess edge, so `just test` never needs a network or a key.
- Nothing ships that nothing uses. The tree holds only what tutorial 0 needs;
  each later tutorial adds its own file instead of filling a placeholder.

### The excerpt that carries the idea

**src/swarm/__main__.py**

```python
"""Entry point of the swarm runner: print what this tutorial built."""


def main() -> None:
    print("setup OK")


if __name__ == "__main__":
    main()
```

### Run it

```bash
git checkout tut00
just tutorial
```

```text
uv run pytest -q
..                                                                       [100%]
2 passed in 0.05s
uv run python -m swarm
setup OK
setup OK
```

### Key takeaways

- `just tutorial` runs the offline tests and prints `setup OK`.
- `uv.lock` is committed, so every reader installs the same dependency versions.
- Secrets live in `.env`, which is never committed; `.env.example` holds
  placeholders only.

### What is still missing

The runner does nothing yet: there is no list of tasks and no loop. Tutorial 1
adds a plain text TODO list and a for-loop that runs one headless session after
another.
