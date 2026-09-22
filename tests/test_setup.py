"""Setup checks for the swarm runner: the package imports and runs offline."""

import subprocess


def test_package_imports() -> None:
    import swarm

    assert swarm.__doc__


def test_entrypoint_runs_workflow_in_order() -> None:
    out = subprocess.run(
        ["python", "-m", "swarm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "opened: 3 steps (spec, code, check)" in out.stdout
    assert "ready: write spec" in out.stdout
    assert "closed: result for write spec" in out.stdout
    assert "ready: write code" in out.stdout
    assert "closed: result for write code" in out.stdout
    assert "ready: check work" in out.stdout
    assert "closed: result for check work" in out.stdout
    assert "run status: done (3 of 3 steps closed in order)" in out.stdout
    assert out.stdout.index("ready: write spec") < out.stdout.index("ready: write code")
    assert out.stdout.index("ready: write code") < out.stdout.index("ready: check work")
