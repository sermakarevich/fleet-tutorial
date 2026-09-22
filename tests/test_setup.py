"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_fires_due_schedule_and_skips_quiet_one() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "fired: morning report -> bead-1" in out.stdout
    assert "quiet: later job (not due)" in out.stdout
    assert out.stdout.index("fired: morning report") < out.stdout.index("quiet: later job")
