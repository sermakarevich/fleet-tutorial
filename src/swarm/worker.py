"""One worker: run a single task through a headless harness."""

import subprocess
from collections.abc import Callable
from pathlib import Path

from swarm import checkpoint

PROMPT_FILE = Path(__file__).parent / "prompts" / "do_task.txt"
RESUME_PROMPT_FILE = Path(__file__).parent / "prompts" / "resume_task.txt"
HARNESS_BIN = "claude"
HEADLESS_FLAG = "-p"


def build_prompt(task: str) -> str:
    """Fill the worker prompt with the task text."""
    return PROMPT_FILE.read_text().format(task=task)


def build_resume_prompt(task: str, note: str) -> str:
    """Fill the resume prompt with the task text and the last checkpoint."""
    return RESUME_PROMPT_FILE.read_text().format(task=task, checkpoint=note)


def run_harness(prompt: str) -> str:
    """Call the harness command line interface and return its output."""
    done = subprocess.run(
        [HARNESS_BIN, HEADLESS_FLAG, prompt],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def run_task(
    task: str,
    harness: Callable[[str], str] = run_harness,
    checkpoint_dir: Path | None = None,
) -> str:
    """Run one task, resuming from its checkpoint folder when one is given."""
    if checkpoint_dir is None:
        return harness(build_prompt(task))
    prior = checkpoint.read_checkpoint(checkpoint_dir)
    if checkpoint.should_resume(checkpoint_dir):
        result = harness(build_resume_prompt(task, prior))
        checkpoint.log_attempt(checkpoint_dir, result)
        checkpoint.save_progress(checkpoint_dir, prior + "\n\nfinished: " + result)
    else:
        checkpoint.save_progress(checkpoint_dir, "starting: " + task)
        result = harness(build_prompt(task))
        checkpoint.log_attempt(checkpoint_dir, result)
        checkpoint.save_progress(checkpoint_dir, "done: " + task + "\n\nresult: " + result)
    checkpoint.write_result(checkpoint_dir, task, result)
    return result
