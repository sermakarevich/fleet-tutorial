"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_merges_two_isolated_worktrees() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "result: result for first line" in out.stdout
    assert "result: result for second line" in out.stdout
    assert "apples are green" in out.stdout
    assert "carrots are purple" in out.stdout
    assert "queue empty: all beads merged and closed" in out.stdout
