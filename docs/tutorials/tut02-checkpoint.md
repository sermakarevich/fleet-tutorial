# Tutorial 2 — Checkpoint and resume

After this tutorial a task that crashes halfway keeps its progress, and the next
session picks up where the dead one stopped instead of starting over.

## In short

### The concepts

- You stop losing work when a session dies. Each task gets a folder where the
  worker saves a short progress note before and after every session.
- The shape stays plain files, not a database. The full-size fleet orchestrator
  this series learns from keeps the same per-task notes and only swaps the TODO
  (to-do) file for a queue database later, when parallel workers must never grab
  the same item.
- Tutorial 1 ran tasks one by one but remembered nothing, so a crash meant the
  next run repeated the whole task from zero.
- One trap is closed here. The note is written before the session starts, so even
  a crash on the first try leaves something to resume from.

### Scope

1. Give each task a folder with a progress note, attempt logs and a result file.
2. Send the last note back into the next session through a resume prompt.
3. Skip tasks that already recorded a result when the loop runs again.

Left out on purpose: asking a human when the worker is stuck. Tutorial 3 adds the
human in the loop.

### The problem

```text
$ just tutorial
task: summarise the inbox
result: demo result for: summarise the inbox
task: draft the status update
crashed: simulated crash: network dropped
```

The loop from tutorial 1 keeps no notes. The crashed task restarts from zero, and
the finished result survives only in your terminal scrollback.

### What changes

```text
src/swarm/
+   checkpoint.py           folders where workers save and read progress
+   prompts/resume_task.txt the prompt that carries the last checkpoint
~   worker.py               saves progress around each harness session
~   loop.py                 reuses recorded results instead of rerunning
~   __main__.py             demo of a crash followed by a resume
tests/
+   test_checkpoint.py
```

`+` is a new file, `~` is a changed file. The full change is `git diff tut01..tut02`.

## In detail

### How it works

One task waits as one line in the TODO file plus one folder on disk. The worker
writes a starting note into the folder, runs one headless harness session as a
subprocess, then appends an attempt log and writes a done note with a result file.
When the session crashes, the exception escapes before any result file exists, so
the task stays on the list with its note behind it. The next run sees a note with
no result, builds the resume prompt from the task and the note, and the new session
continues instead of repeating finished steps. The loop also skips any task whose
result file already exists, so finished work is never paid for twice.

### Design decisions

- Progress is a text note plus a separate result file, never one record. The split
  is what makes "interrupted" visible: a note without a result means resume, and a
  result means skip.
- The worker saves the starting note before calling the harness. A crash on the
  very first session still leaves a checkpoint, so the resume prompt always has
  something to carry.
- The loop trusts the result file on disk, not memory. Results survive the process
  dying, so rerunning the loop reuses finished tasks. The fleet orchestrator this
  series learns from keeps the same files and adds a queue around them at scale.

### The excerpt that carries the idea

**src/swarm/checkpoint.py**

```python
def should_resume(task_folder: Path) -> bool:
    """True when a session left progress behind without finishing the task."""
    return read_checkpoint(task_folder) != "" and not has_result(task_folder)
```

### Run it

```bash
git checkout tut02
just tutorial
```

```text
tut02: checkpoint and resume
uv run python -m swarm
crashed: simulated crash: network dropped
checkpoint: starting: draft the status update
resuming from checkpoint...
task: draft the status update
result: demo result for: draft the status update
done: 1 resumed, 1 reused from checkpoint
```

### Key takeaways

- Each task owns a folder with a progress note, numbered attempt logs and one
  result file.
- A crash leaves a note with no result, and the next session resumes from that
  note through the resume prompt.
- A result file means done: reruns skip finished tasks instead of redoing them.

### What is still missing

Resume replays the same dead end when the worker needs a decision only you can
make, such as which of two designs to pick. Tutorial 3 gives the worker a way to
ask you a question mid-task and wait for your answer.
