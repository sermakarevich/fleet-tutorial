"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_runs_supervisor_over_two_beads() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "spawn: first line -> opencode/" in out.stdout
    assert "spawn: second line -> opencode/" in out.stdout
    assert "closed: result for first line" in out.stdout
    assert "closed: result for second line" in out.stdout
    assert "queue ready: none" in out.stdout
