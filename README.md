1. Install uv
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Add uv to your PATH

echo 'source $HOME/.local/bin/env' >> ~/.zshrc && source ~/.zshrc


Then confirm it works:

uv --version

2. Set up the backend environment
cd backend

# Install Python 3.11
uv python install 3.11

# Create a virtual environment
uv venv .venv --python 3.11

# Activate it
source .venv/bin/activate       # macOS/Linux
# .\.venv\Scripts\activate      # Windows

# Install dependencies (runtime + dev/test groups)
uv sync --group dev --group test

4. Pre-commit Hooks

Pre-commit automatically runs Ruff, Mypy, and other checks before every commit.

Install the hooks:

uv run pre-commit install


Run them manually on all files:

uv run pre-commit run --all-files


Whenever you git commit, these hooks will trigger automatically.
If something fails (like formatting), fix it or stage the modified files and re-commit.

 5. Common Commands
Purpose	Command
Run API (dev server)	uv run uvicorn backend.app.api.main:app --reload
Lint & format	uv run ruff format . && uv run ruff check --fix .
Type check	uv run mypy .
Tests + coverage	uv run pytest && uv run coverage run -m pytest
Run all checks	./scripts/lint.sh
6. Typical Developer Workflow
git checkout -b feat/new-endpoint
./scripts/lint.sh     # run formatter + type checks
uv run pytest         # run tests
git add .
git commit -m "feat: add new endpoint"
git push

7. Quick Setup Summary
# one-time setup
curl -LsSf https://astral.sh/uv/install.sh | sh
echo 'source $HOME/.local/bin/env' >> ~/.zshrc && source ~/.zshrc

# project setup
cd Virtual-Economist/backend
uv python install 3.11
uv venv .venv --python 3.11
source .venv/bin/activate
uv sync --group dev --group test
uv run pre-commit install
