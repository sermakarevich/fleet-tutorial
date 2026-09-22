# Tutorial 1 — TODO list and loop

After this tutorial your runner works through a plain text task list on its own, one
headless session (a session started by a script, with no human at the keyboard) after
another.

## In short

### The concepts

- You stop typing "next please" by hand. A text file holds the tasks and a loop pulls
  the top item, runs it, and crosses it off when done.
- The shape stays tiny on purpose. The list is one task per line and the loop is a
  while loop around a single worker call. The full-size fleet orchestrator this series
  learns from swaps the file for a queue database later, because a plain file cannot
  hand items out safely to workers running at the same time. The loop keeps its job:
  pull the next ready task and run it.
- Tutorial 0 gave you a runnable project that only proved the setup. It could run no
  task at all, so this tutorial adds the first real behaviour.
- One trap is closed here. A missing or empty list ends the run instead of crashing,
  so running the loop twice is safe: the second run simply does nothing.

### Scope

1. Keep tasks in a plain text TODO (to-do) file, one task per line.
2. Run each task through one headless worker session using the harness command line
   interface (CLI).
3. Loop until the list is empty and print each result with a final count.

Left out on purpose: surviving a crash mid-task. Tutorial 2 adds checkpoint and resume.

### The problem

```text
$ just tutorial
setup OK
```

The setup check passes but knows no task. Anything you need doing still waits for you
to type it by hand, one prompt at a time.

### What changes

```text
src/swarm/
+   todo.py               next task out, finished task off the list
+   loop.py               run tasks one by one until the list is empty
+   worker.py             one task through one headless harness session
+   prompts/do_task.txt   the prompt every worker session receives
~   __main__.py           demo that runs two tasks through the loop
tests/
+   test_todo.py          list reads, removals, empty and missing file
+   test_loop.py          tasks run in order over a faked harness
~   test_setup.py         entry point now runs the demo, not the setup print
```

`+` is a new file, `~` is a changed file. The full change is `git diff tut00..tut01`.

## In detail

### How it works

One task waits as one line in the TODO file. The loop reads the first non-empty line,
hands it to the worker, and the worker fills the prompt file with the task text and
starts one headless harness session as a subprocess. When the session exits, the loop
crosses the finished line off the file and reads the next one. When no lines are left,
the loop stops and returns every result.
The demo in the entry point writes two tasks to a throwaway TODO file, runs the loop
with a canned stand-in instead of the real harness, and prints each task with its
result. The stand-in keeps the demo offline: no network and no model key needed.

### Design decisions

- The list is a plain text file, not a queue database. One loop and one worker need no
  safe claiming, and the file shows the mechanism with nothing new to install. The
  fleet orchestrator this series learns from uses a queue database instead, because
  many workers running at once must never grab the same item.
- A task leaves the list only after its session returns. A crash therefore keeps the
  task on the list, so the next run retries it instead of silently skipping it.
- Tests fake the harness at the subprocess edge. `just test` never starts a real
  session, so the suite stays offline with no key and no network.

### The excerpt that carries the idea

**src/swarm/loop.py**

```python
def run(todo_file: Path, run_task: Callable[[str], str] = worker.run_task) -> list[str]:
    """Run each item in turn, removing it when done, return all results."""
    results = []
    while (task := todo.next_task(todo_file)) is not None:
        results.append(run_task(task))
        todo.mark_done(todo_file, task)
    return results
```

### Run it

```bash
git checkout tut01
just tutorial
```

```text
uv run python -m swarm
task: summarise the inbox
result: demo result for: summarise the inbox

task: draft the status update
result: demo result for: draft the status update

done: 2 tasks
```

### Key takeaways

- A plain text file holds the task list: the loop pulls the top item and crosses it
  off when done.
- A loop replaces the human repeater: each pass starts one headless harness session
  with a "do the next task" prompt.
- `just tutorial` runs two demo tasks in a row and prints each result with a final
  count.

### What is still missing

A crash in the middle of a task loses everything that session did: the task stays on
the list, but the next run starts it from scratch. Tutorial 2 adds checkpoint and
resume, so a killed task continues from its last saved state instead of starting over.
