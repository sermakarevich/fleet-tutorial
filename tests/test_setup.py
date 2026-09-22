"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_runs_workflow_schedule_and_trigger() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "workflow: 2 steps (write spec, write code)" in out.stdout
    assert "fired: morning report -> bead-3" in out.stdout
    assert "quiet: later job (not due)" in out.stdout
    assert "trigger: blocked bead-1 -> bead-4" in out.stdout
