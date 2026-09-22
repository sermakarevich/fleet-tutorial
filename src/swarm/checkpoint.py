"""Per-task folders where workers save progress so the next session can resume."""

import json
from pathlib import Path

STATE_NAME = "STATE.md"
RESULT_NAME = "RESULT.json"
ATTEMPTS_DIR = "attempts"
DONE = "done"
MAX_SLUG = 40


def task_dir(root: Path, task: str) -> Path:
    """Folder for one task, derived from its text, safe for file names."""
    words = "".join(char.lower() if char.isalnum() else " " for char in task).split()
    return root / ("_".join(words)[:MAX_SLUG] or "task")


def save_progress(task_folder: Path, note: str) -> None:
    """Store the latest progress note, replacing the one before."""
    task_folder.mkdir(parents=True, exist_ok=True)
    (task_folder / STATE_NAME).write_text(note + "\n")


def read_checkpoint(task_folder: Path) -> str:
    """Last progress note, or empty text when no session wrote one yet."""
    state_file = task_folder / STATE_NAME
    return state_file.read_text().strip() if state_file.exists() else ""


def has_result(task_folder: Path) -> bool:
    """True once a session finished the task and recorded its outcome."""
    return (task_folder / RESULT_NAME).exists()


def should_resume(task_folder: Path) -> bool:
    """True when a session left progress behind without finishing the task."""
    return read_checkpoint(task_folder) != "" and not has_result(task_folder)


def log_attempt(task_folder: Path, text: str) -> Path:
    """Append one numbered log for an attempt, return the log file."""
    folder = task_folder / ATTEMPTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    log_file = folder / f"{len(list(folder.glob('*.log'))):03d}.log"
    log_file.write_text(text + "\n")
    return log_file


def write_result(task_folder: Path, task: str, result: str) -> None:
    """Record the finished outcome of a task."""
    task_folder.mkdir(parents=True, exist_ok=True)
    (task_folder / RESULT_NAME).write_text(
        json.dumps({"task": task, "result": result, "status": DONE})
    )


def read_result(task_folder: Path) -> str | None:
    """Finished outcome of a task, or None when the task is not done yet."""
    result_file = task_folder / RESULT_NAME
    if not result_file.exists():
        return None
    return str(json.loads(result_file.read_text())["result"])
