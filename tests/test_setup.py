"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_runs_kill_and_resume_demo() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "crashed: simulated crash" in out.stdout
    assert "checkpoint: starting: draft the status update" in out.stdout
    assert "resuming from checkpoint..." in out.stdout
    assert "task: draft the status update" in out.stdout
    assert "done: 1 resumed, 1 reused from checkpoint" in out.stdout
