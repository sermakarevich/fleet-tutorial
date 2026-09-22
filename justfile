# Task runner for the swarm tutorial. `just` alone lists recipes.
set dotenv-load := true

default:
    @just --list

# Install the exact locked environment
setup:
    uv sync

# Shows what this tutorial built: a blocked bead opens one investigator
tutorial:
    @echo "tut12: blocked task opens an investigator; demo swarm runs"
    uv run python -m swarm

# Tiny end-to-end swarm on fake beads: workflow, schedule, trigger
demo:
    @echo "capstone: one workflow, one schedule firing, one trigger firing"
    uv run python -m swarm

fmt:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff check .
    uv run ruff format --check .

test:
    uv run pytest -q
