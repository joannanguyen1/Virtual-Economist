#!/usr/bin/env bash
set -e

# Simple unified linter for the Virtual-Economists backend

# Move to the backend root (adjust if this file sits elsewhere)
cd "$(dirname "$0")/../backend" || exit 1

echo "Running Ruff lint & format check..."
uv run ruff format .
uv run ruff check --fix .

echo "Running mypy type checks..."
uv run mypy .

echo "Running pre-commit hooks on staged files..."
uv run pre-commit run --all-files

echo "All linting and type checks passed!"
