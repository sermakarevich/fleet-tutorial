"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_shows_routing_picks() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "plan: design the queue -> opencode/" in out.stdout
    assert "exec: write the loop -> opencode/" in out.stdout
    assert "exec: write the tests -> opencode/" in out.stdout
    assert "queue ready: none" in out.stdout
