"""TODO list: read the next item, remove it when done."""

from pathlib import Path

from swarm import todo


def test_next_task_returns_first_line(tmp_path: Path) -> None:
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("first\nsecond\n")
    assert todo.next_task(todo_file) == "first"


def test_next_task_skips_blank_lines(tmp_path: Path) -> None:
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("\n  \nsecond\n")
    assert todo.next_task(todo_file) == "second"


def test_next_task_empty_file_gives_none(tmp_path: Path) -> None:
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("")
    assert todo.next_task(todo_file) is None


def test_next_task_missing_file_gives_none(tmp_path: Path) -> None:
    assert todo.next_task(tmp_path / "TODO.md") is None


def test_mark_done_removes_first_match(tmp_path: Path) -> None:
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("first\nsecond\n")
    todo.mark_done(todo_file, "first")
    assert todo.next_task(todo_file) == "second"


def test_mark_done_empties_file(tmp_path: Path) -> None:
    todo_file = tmp_path / "TODO.md"
    todo_file.write_text("only\n")
    todo.mark_done(todo_file, "only")
    assert todo.next_task(todo_file) is None
