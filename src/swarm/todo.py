"""Plain text TODO list: read the next item, remove it when done."""

from pathlib import Path


def next_task(todo_file: Path) -> str | None:
    """First non-empty line of the file, or None when the list is empty."""
    if not todo_file.exists():
        return None
    for line in todo_file.read_text().splitlines():
        task = line.strip()
        if task:
            return task
    return None


def mark_done(todo_file: Path, task: str) -> None:
    """Remove the first line matching the task."""
    lines = todo_file.read_text().splitlines()
    for index, line in enumerate(lines):
        if line.strip() == task:
            del lines[index]
            break
    todo_file.write_text("\n".join(lines) + ("\n" if lines else ""))
