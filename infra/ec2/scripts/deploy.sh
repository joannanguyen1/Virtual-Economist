#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/virtual-economist}"
WEB_ROOT="${WEB_ROOT:-/var/www/virtual-economist/current}"

cd "$APP_DIR"

echo "Syncing Python dependencies..."
uv --project backend sync

echo "Installing auth dependencies..."
cd "$APP_DIR/backend"
npm ci

echo "Building frontend..."
cd "$APP_DIR/frontend"
npm ci
npm run build

echo "Publishing frontend build..."
sudo mkdir -p "$WEB_ROOT"
sudo rsync -av --delete "$APP_DIR/frontend/build/" "$WEB_ROOT/"

echo "Restarting services..."
sudo systemctl daemon-reload
sudo systemctl restart virtual-economist-fastapi
sudo systemctl restart virtual-economist-auth
sudo nginx -t
sudo systemctl reload nginx

echo "Running smoke checks..."
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:800/health

echo
echo "Deploy complete."
