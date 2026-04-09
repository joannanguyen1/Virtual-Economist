#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1}"

echo "Testing frontend..."
curl -fsS "$BASE_URL/" >/dev/null

echo "Testing FastAPI health..."
curl -fsS "$BASE_URL/api/../health" >/dev/null || curl -fsS "$BASE_URL:8000/health" >/dev/null

echo "Testing auth health..."
curl -fsS "$BASE_URL/auth/health" >/dev/null || curl -fsS "$BASE_URL:800/health" >/dev/null

echo "Testing unified chat..."
curl -fsS -X POST "$BASE_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is Apple current stock price?"}' >/dev/null

echo "Smoke test passed."
