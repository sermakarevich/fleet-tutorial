# Tutorial 3 — Human in the loop

After this tutorial a worker that needs a decision only you can make asks you
mid-task, waits for your answer, and continues instead of guessing.

## In short

### The concepts

- You stop losing tasks to unanswered questions. The worker spots a question
  in the harness output, saves it, blocks until you answer, and reruns the
  harness with your answer attached.
- The shape stays plain files, not a chat server. The question and the answer
  are two small files next to the checkpoint note, so a crashed wait is
  re-asked by the next session. The full-size fleet orchestrator this series
  learns from asks through an ask_human tool over Model Context Protocol
  (MCP) with a chat ping instead, because polling cannot reach a human away
  from the machine.
- Tutorial 2 resumed crashed tasks from a saved note, but a task that needs
  your call got its question filed as a done result, so the dead end repeated
  on every resume.
- Two traps are closed here. A question that arrives twice is asked once, and
  a wait nobody answers raises through a timeout instead of hanging forever.

### Scope

1. Spot a harness reply that is a question, not a result.
2. Save the question and block until the answer file arrives.
3. Rerun the harness with the answer and record the result as usual.

Left out on purpose: running two workers at once. Tutorial 4 swaps the TODO
(to-do) file for a beads queue, which hands items out safely to parallel workers.

### The problem

```text
$ just tutorial
task: draft the launch note
result: ASK: one line or two?
```

The loop from tutorial 2 stores whatever the harness returns as a done
result, so the question is filed away and nothing ever asks you.

### What changes

```text
src/swarm/
+   human.py                ask one question mid-task and wait for the answer
+   prompts/answer_task.txt the prompt that continues with the human answer
~   worker.py               pauses for a human answer when the harness asks
~   __main__.py             demo where the worker asks and the human answers
tests/
+   test_human.py
```

`+` is a new file, `~` is a changed file. The full change is `git diff tut02..tut03`.

## In detail

### How it works

One task waits as one line in the TODO file plus one folder on disk. The
worker runs one harness session as a subprocess and reads its output. Output
starting with the ask marker is a question: the worker saves it next to the
checkpoint note and blocks, polling for the answer file. When you write the
answer, the worker builds the answer prompt from the task, the question and
your answer, runs the harness once more, and records the result like any
finished task. A crashed wait leaves the question file behind with no answer,
so the next session re-asks instead of rerunning the dead end.

### Design decisions

- A question is plain text behind a short marker, never a special return
  type. The worker needs no new harness contract, so the same fake harness
  keeps `just test` offline with no key and no network.
- The question and the answer are files, not memory, so a crash mid-wait
  leaves an open question the next session picks up. The fleet orchestrator
  this series learns from keeps the shape and swaps polling for a chat ping.
- Every wait carries a timeout. A question you never see raises instead of
  holding the loop hostage, so one unanswered task cannot freeze the rest of
  the list.

### The excerpt that carries the idea

**src/swarm/human.py**

```python
def ask(task_folder: Path, question: str, timeout: float = ASK_TIMEOUT) -> str:
    """Save the question, then block until the answer file arrives."""
    save_question(task_folder, question)
    deadline = time.monotonic() + timeout
    while (answer := read_answer(task_folder)) is None:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"no answer arrived within {timeout} seconds")
        time.sleep(POLL_INTERVAL)
    return answer
```

### Run it

```bash
git checkout tut03
just tutorial
```

```text
tut03: human in the loop
uv run python -m swarm
question: one line or two?
answer: one line
result: demo result for draft the launch note: one line
done: asked 1, answered 1, continued 1
```

### Key takeaways

- A harness reply starting with the ask marker is a question, not a result:
  the worker saves it and blocks until the answer file arrives.
- The answer reruns the harness with the answer prompt, recorded like any finished task.
- An open question survives a crash, so the next session re-asks it, and a
  timeout keeps an unanswered question from freezing the loop.

### What is still missing

One worker at a time is fine while the list is a text file, but two workers
would grab the same line: the file has no safe way to hand items out.
Tutorial 4 replaces the TODO file with a beads queue, where each task is
claimed exactly once.
