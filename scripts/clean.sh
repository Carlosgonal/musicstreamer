#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
ENV_FILE="$PROJECT_DIR/env/.env"
SERVICE_NAME="${MUSICSTREAMER_SERVICE_NAME:-musicstreamer}"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

cd "$PROJECT_DIR"

if [ -f "$ENV_FILE" ]; then
  echo "Removing env/.env"
  rm -f "$ENV_FILE"
fi

if [ -d "$VENV_DIR" ]; then
  echo "Removing virtual environment"
  rm -rf "$VENV_DIR"
fi

if [ -d "$PROJECT_DIR/var" ]; then
  echo "Removing runtime data"
  rm -rf "$PROJECT_DIR/var"
fi

if [ -d "$PROJECT_DIR/config" ]; then
  echo "Removing legacy config files"
  rm -f "$PROJECT_DIR/config/spotify.json" \
        "$PROJECT_DIR/config/spotify-settings.json" \
        "$PROJECT_DIR/config/radio.json"
fi

find "$PROJECT_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +

if command -v systemctl >/dev/null 2>&1 && [ -f "$SERVICE_FILE" ]; then
  echo "Disabling and removing systemd service: $SERVICE_NAME"
  sudo systemctl stop "$SERVICE_NAME" || true
  sudo systemctl disable "$SERVICE_NAME" || true
  sudo rm -f "$SERVICE_FILE"
  sudo systemctl daemon-reload
fi

echo "Clean complete."
