"""Model routing: plan beads get the smart model, exec beads the cheap one."""

import pytest

from swarm import routing, worker


def test_plan_picks_smart_model() -> None:
    settings = routing.Settings(smart_model="smart-one", cheap_model="cheap-one")

    assert routing.pick({"kind": "plan"}, settings).model == "smart-one"


def test_exec_picks_cheap_model() -> None:
    settings = routing.Settings(smart_model="smart-one", cheap_model="cheap-one")

    assert routing.pick({"kind": "exec"}, settings).model == "cheap-one"
    assert routing.pick(None, settings).model == "cheap-one"


def test_second_harness_selected_when_requested() -> None:
    assert routing.pick({"kind": "exec", "harness": "pi"}).harness == "pi"


def test_unknown_harness_falls_back_to_opencode() -> None:
    with pytest.warns(UserWarning, match="unknown harness"):
        route = routing.pick({"kind": "exec", "harness": "mystery"})

    assert route.harness == "opencode"


def test_worker_resolves_routing_per_task() -> None:
    settings = routing.Settings(smart_model="smart-one", cheap_model="cheap-one")

    assert worker.resolve({"kind": "plan"}, settings).model == "smart-one"
    assert worker.resolve({"kind": "exec"}, settings).model == "cheap-one"
    assert worker.resolve({"kind": "exec", "harness": "pi"}, settings).harness == "pi"
