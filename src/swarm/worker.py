"""One worker: run a single task through a headless harness."""

import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

from swarm import checkpoint, human, routing

PROMPT_FILE = Path(__file__).parent / "prompts" / "do_task.txt"
RESUME_PROMPT_FILE = Path(__file__).parent / "prompts" / "resume_task.txt"
ANSWER_PROMPT_FILE = Path(__file__).parent / "prompts" / "answer_task.txt"
HARNESS_BIN = "opencode"
HARNESS_ARGS = ("run",)
HARNESS_BINS = {
    routing.Harness.OPENCODE.value: (HARNESS_BIN, HARNESS_ARGS),
    routing.Harness.PI.value: ("pi", ()),
}


def build_prompt(task: str) -> str:
    """Fill the worker prompt with the task text."""
    return PROMPT_FILE.read_text().format(task=task)


def build_resume_prompt(task: str, note: str) -> str:
    """Fill the resume prompt with the task text and the last checkpoint."""
    return RESUME_PROMPT_FILE.read_text().format(task=task, checkpoint=note)


def build_answer_prompt(task: str, question: str, answer: str) -> str:
    """Fill the continue prompt with the task text, the question, and its answer."""
    return ANSWER_PROMPT_FILE.read_text().format(task=task, question=question, answer=answer)


def resolve(
    meta: Mapping[str, str] | None = None, settings: routing.Settings | None = None
) -> routing.Route:
    """Harness plus model for one task from its metadata mapping."""
    return routing.pick(meta, settings)


def run_harness(
    prompt: str, workdir: Path | None = None, route: routing.Route | None = None
) -> str:
    """Call the harness command line interface and return its output."""
    picked = route or routing.Route(harness=HARNESS_BIN, model="")
    binary, args = HARNESS_BINS.get(picked.harness, (HARNESS_BIN, HARNESS_ARGS))
    done = subprocess.run(
        [binary, *args, prompt],
        capture_output=True,
        text=True,
        check=True,
        cwd=workdir,
    )
    return done.stdout.strip()


def run_task(
    task: str,
    harness: Callable[[str], str] = run_harness,
    checkpoint_dir: Path | None = None,
    ask: Callable[..., str] = human.ask,
    ask_timeout: float = human.ASK_TIMEOUT,
    workdir: Path | None = None,
    meta: Mapping[str, str] | None = None,
) -> str:
    """Run one task, pausing for a human answer when the harness asks.

    Runs the harness in `workdir` when set, so edits land in the task worktree.
    """

    def call(prompt: str) -> str:
        if harness is run_harness:
            return run_harness(prompt, workdir, resolve(meta))
        return harness(prompt)

    if checkpoint_dir is None:
        return call(build_prompt(task))
    if human.has_open_question(checkpoint_dir):
        return continue_with_answer(
            task, harness, checkpoint_dir, human.read_question(checkpoint_dir), ask, ask_timeout
        )
    prior = checkpoint.read_checkpoint(checkpoint_dir)
    if checkpoint.should_resume(checkpoint_dir):
        result = call(build_resume_prompt(task, prior))
        checkpoint.log_attempt(checkpoint_dir, result)
        checkpoint.save_progress(checkpoint_dir, prior + "\n\nfinished: " + result)
    else:
        checkpoint.save_progress(checkpoint_dir, "starting: " + task)
        result = call(build_prompt(task))
    if human.wants_input(result):
        return continue_with_answer(
            task, harness, checkpoint_dir, human.take_question(result), ask, ask_timeout
        )
    checkpoint.log_attempt(checkpoint_dir, result)
    checkpoint.save_progress(checkpoint_dir, "done: " + task + "\n\nresult: " + result)
    checkpoint.write_result(checkpoint_dir, task, result)
    return result


def continue_with_answer(
    task: str,
    harness: Callable[[str], str],
    checkpoint_dir: Path,
    question: str,
    ask: Callable[..., str],
    ask_timeout: float,
) -> str:
    """Wait for the human answer, run the harness once more, record the outcome."""
    checkpoint.save_progress(checkpoint_dir, "waiting: " + question)
    answer = ask(checkpoint_dir, question, timeout=ask_timeout)
    result = harness(build_answer_prompt(task, question, answer))
    checkpoint.log_attempt(checkpoint_dir, result)
    checkpoint.save_progress(checkpoint_dir, "done: " + task + "\n\nresult: " + result)
    checkpoint.write_result(checkpoint_dir, task, result)
    return result
