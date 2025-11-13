# Virtual Economist Backend Setup

## 1. Install `uv`

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Add `uv` to your PATH
```bash
echo 'source $HOME/.local/bin/env' >> ~/.zshrc && source ~/.zshrc
```

Then confirm the installation:
```bash
uv --version
```

---

## 2. Set Up the Backend Environment
```bash
cd backend
```

### Install Python 3.11
```bash
uv python install 3.11
```

### Create and Activate Virtual Environment
```bash
uv venv .venv --python 3.11
source .venv/bin/activate       # macOS/Linux
# .\.venv\Scripts\activate    # Windows
```

### Install Dependencies (runtime + dev/test)
```bash
uv sync --group dev --group test
```

---

## 3. Pre-Commit Hooks

Pre-commit automatically runs **Ruff**, **Mypy**, and other checks before every commit.

### Install Hooks
```bash
uv run pre-commit install
```

### Run Hooks Manually
```bash
uv run pre-commit run --all-files
```

Whenever you `git commit`, these hooks will run automatically.
If something fails (like formatting), fix it, re-stage the files, and commit again.

---

## 4. Common Commands

| Purpose | Command |
|----------|----------|
| **Run API (dev server)** | `uv run uvicorn backend.app.api.main:app --reload` |
| **Lint & format** | `uv run ruff format . && uv run ruff check --fix .` |
| **Type check** | `uv run mypy .` |
| **Tests + coverage** | `uv run pytest && uv run coverage run -m pytest` |
| **Run all checks** | `./scripts/lint.sh` |

---

## 5. Typical Developer Workflow

```bash
git checkout -b feat/new-endpoint
./scripts/lint.sh       # Run formatter + type checks
uv run pytest           # Run tests
git add .
git commit -m "feat: add new endpoint"
git push
```

---

## 6. Quick Setup Summary

```bash
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
```

---

Use `./scripts/lint.sh` to check formatting and type safety before every commit.
