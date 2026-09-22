"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_runs_three_beads_and_reclaims_one_lease() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "result: result for first chore" in out.stdout
    assert "result: result for second chore" in out.stdout
    assert "result: result for third chore" in out.stdout
    assert "dead lease reclaimed: second chore ran again and closed" in out.stdout
    assert "done: claimed 3, ran 4, double-runs 0" in out.stdout
    assert "queue empty: all beads closed" in out.stdout
