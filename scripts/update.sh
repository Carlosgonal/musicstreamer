#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="${MUSICSTREAMER_SERVICE_NAME:-musicstreamer}"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

cd "$PROJECT_DIR"

git pull
./scripts/install.sh

if command -v systemctl >/dev/null 2>&1 && [ -f "$SERVICE_FILE" ]; then
  sudo systemctl daemon-reload
  sudo systemctl restart "$SERVICE_NAME"
fi

echo "Updated and restarted $SERVICE_NAME."
