"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_runs_demo_loop() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "task: summarise the inbox" in out.stdout
    assert "task: draft the status update" in out.stdout
    assert "done: 2 tasks" in out.stdout
