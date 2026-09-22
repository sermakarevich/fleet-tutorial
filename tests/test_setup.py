"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_retries_flaky_and_blocks_hopeless() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "result: result for flaky chore" in out.stdout
    assert "blocked: hopeless chore" in out.stdout
    assert "needs a human" in out.stdout
    assert "queue ready: none" in out.stdout
