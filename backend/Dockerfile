FROM python:3.11-slim

WORKDIR /app

# Helpful for building some wheels (numpy/pandas/etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency metadata first for caching
COPY pyproject.toml ./
# If you have a lock file, COPY it too (recommended):
# COPY uv.lock ./

# Install runtime deps into the system python
# --no-dev ensures only runtime deps (not dev/test groups)
RUN uv pip install --system .

# Copy the backend code
COPY . .

EXPOSE 8000

# CHANGE THIS if your FastAPI app path is different
# Common: backend/app/main.py defines `app = FastAPI()`
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
