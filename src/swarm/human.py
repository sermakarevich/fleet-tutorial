"""A worker asks one question mid-task and waits for the human answer."""

import time
from pathlib import Path

QUESTION_NAME = "QUESTION.md"
ANSWER_NAME = "ANSWER.md"
ASK_PREFIX = "ASK:"
ASK_TIMEOUT = 300.0
POLL_INTERVAL = 0.05


def wants_input(output: str) -> bool:
    """True when the harness output is a request for human input."""
    return output.strip().startswith(ASK_PREFIX)


def take_question(output: str) -> str:
    """The question text carried inside a harness input request."""
    return output.strip()[len(ASK_PREFIX) :].strip()


def save_question(task_folder: Path, question: str) -> Path:
    """Write the open question so a later session can re-ask it."""
    task_folder.mkdir(parents=True, exist_ok=True)
    question_file = task_folder / QUESTION_NAME
    question_file.write_text(question.strip() + "\n")
    return question_file


def read_question(task_folder: Path) -> str:
    """The open question, or empty text when no question was asked yet."""
    question_file = task_folder / QUESTION_NAME
    return question_file.read_text().strip() if question_file.exists() else ""


def answer_question(task_folder: Path, answer: str) -> Path:
    """Record the human answer; this is what unblocks a waiting worker."""
    task_folder.mkdir(parents=True, exist_ok=True)
    answer_file = task_folder / ANSWER_NAME
    answer_file.write_text(answer.strip() + "\n")
    return answer_file


def read_answer(task_folder: Path) -> str | None:
    """The human answer, or None while the worker is still waiting."""
    answer_file = task_folder / ANSWER_NAME
    if not answer_file.exists():
        return None
    answer = answer_file.read_text().strip()
    return answer if answer else None


def has_open_question(task_folder: Path) -> bool:
    """True when a question waits for an answer that never arrived."""
    return read_question(task_folder) != "" and read_answer(task_folder) is None


def ask(task_folder: Path, question: str, timeout: float = ASK_TIMEOUT) -> str:
    """Save the question, then block until the answer file arrives."""
    save_question(task_folder, question)
    deadline = time.monotonic() + timeout
    while (answer := read_answer(task_folder)) is None:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"no answer arrived within {timeout} seconds")
        time.sleep(POLL_INTERVAL)
    return answer
