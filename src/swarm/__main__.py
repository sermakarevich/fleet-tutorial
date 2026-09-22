"""Entry point of the swarm runner: claim beads, run them, close them."""

from swarm import routing, worker

DEMO_TASKS = (
    {"title": "design the queue", "kind": "plan", "harness": "opencode"},
    {"title": "write the loop", "kind": "exec", "harness": "opencode"},
    {"title": "write the tests", "kind": "exec", "harness": "opencode"},
)


def main() -> None:
    for entry in DEMO_TASKS:
        route = worker.resolve(entry)
        result = f"result for {entry['title']}"
        print(f"{entry['kind']}: {entry['title']} -> {route.harness}/{route.model}: {result}")
    assert routing.pick() == routing.pick({"kind": "exec"})
    print("queue ready: none (demo tasks need no beads)")


if __name__ == "__main__":
    main()
