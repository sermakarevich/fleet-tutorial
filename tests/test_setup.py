"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_claims_two_beads_once_each() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "result: result for first chore" in out.stdout
    assert "result: result for second chore" in out.stdout
    assert "done: claimed 2, ran 2, double-runs 0" in out.stdout
    assert "queue empty: both beads closed" in out.stdout
