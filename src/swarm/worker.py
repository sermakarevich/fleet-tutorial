"""One worker: run a single task through a headless harness."""

import subprocess
from collections.abc import Callable
from pathlib import Path

PROMPT_FILE = Path(__file__).parent / "prompts" / "do_task.txt"
HARNESS_BIN = "claude"
HEADLESS_FLAG = "-p"


def build_prompt(task: str) -> str:
    """Fill the worker prompt with the task text."""
    return PROMPT_FILE.read_text().format(task=task)


def run_harness(prompt: str) -> str:
    """Call the harness command line interface and return its output."""
    done = subprocess.run(
        [HARNESS_BIN, HEADLESS_FLAG, prompt],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def run_task(task: str, harness: Callable[[str], str] = run_harness) -> str:
    """Build the prompt for one task and run it through the harness."""
    return harness(build_prompt(task))
