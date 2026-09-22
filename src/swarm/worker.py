"""One worker: run a single task through a headless harness."""

import subprocess
from collections.abc import Callable
from pathlib import Path

from swarm import checkpoint, human

PROMPT_FILE = Path(__file__).parent / "prompts" / "do_task.txt"
RESUME_PROMPT_FILE = Path(__file__).parent / "prompts" / "resume_task.txt"
ANSWER_PROMPT_FILE = Path(__file__).parent / "prompts" / "answer_task.txt"
HARNESS_BIN = "opencode"
HARNESS_ARGS = ("run",)


def build_prompt(task: str) -> str:
    """Fill the worker prompt with the task text."""
    return PROMPT_FILE.read_text().format(task=task)


def build_resume_prompt(task: str, note: str) -> str:
    """Fill the resume prompt with the task text and the last checkpoint."""
    return RESUME_PROMPT_FILE.read_text().format(task=task, checkpoint=note)


def build_answer_prompt(task: str, question: str, answer: str) -> str:
    """Fill the continue prompt with the task text, the question, and its answer."""
    return ANSWER_PROMPT_FILE.read_text().format(task=task, question=question, answer=answer)


def run_harness(prompt: str) -> str:
    """Call the harness command line interface and return its output."""
    done = subprocess.run(
        [HARNESS_BIN, *HARNESS_ARGS, prompt],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def run_task(
    task: str,
    harness: Callable[[str], str] = run_harness,
    checkpoint_dir: Path | None = None,
    ask: Callable[..., str] = human.ask,
    ask_timeout: float = human.ASK_TIMEOUT,
) -> str:
    """Run one task, pausing for a human answer when the harness asks."""
    if checkpoint_dir is None:
        return harness(build_prompt(task))
    if human.has_open_question(checkpoint_dir):
        return continue_with_answer(
            task, harness, checkpoint_dir, human.read_question(checkpoint_dir), ask, ask_timeout
        )
    prior = checkpoint.read_checkpoint(checkpoint_dir)
    if checkpoint.should_resume(checkpoint_dir):
        result = harness(build_resume_prompt(task, prior))
        checkpoint.log_attempt(checkpoint_dir, result)
        checkpoint.save_progress(checkpoint_dir, prior + "\n\nfinished: " + result)
    else:
        checkpoint.save_progress(checkpoint_dir, "starting: " + task)
        result = harness(build_prompt(task))
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
