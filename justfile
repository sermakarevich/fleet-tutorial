# Task runner for the swarm tutorial. `just` alone lists recipes.
set dotenv-load := true

default:
    @just --list

# Install the exact locked environment
setup:
    uv sync

# Shows what this tutorial built: retries with a dead-letter queue
tutorial:
    @echo "tut07: retries and dead-letter"
    uv run python -m swarm

fmt:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff check .
    uv run ruff format --check .

test:
    uv run pytest -q
