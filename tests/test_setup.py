"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_runs_ask_answer_continue_demo() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "question: one line or two?" in out.stdout
    assert "answer: one line" in out.stdout
    assert "result: demo result for draft the launch note: one line" in out.stdout
    assert "done: asked 1, answered 1, continued 1" in out.stdout
