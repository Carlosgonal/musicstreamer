#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

cd "$PROJECT_DIR"

if [ -f "$PROJECT_DIR/env/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$PROJECT_DIR/env/.env"
  set +a
fi

SERVICE_NAME="${MUSICSTREAMER_SERVICE_NAME:-musicstreamer}"
SERVICE_USER="${MUSICSTREAMER_SERVICE_USER:-$USER}"

migrate_runtime_config_file() {
  local filename="$1"
  local legacy_file="$PROJECT_DIR/config/$filename"
  local runtime_file="$PROJECT_DIR/var/config/$filename"

  if [ -f "$legacy_file" ] && [ ! -f "$runtime_file" ]; then
    cp "$legacy_file" "$runtime_file"
  fi
}

prepare_runtime_permissions() {
  mkdir -p "$PROJECT_DIR/var/config"
  migrate_runtime_config_file "audio.json"
  migrate_runtime_config_file "radio.json"
  migrate_runtime_config_file "spotify.json"
  migrate_runtime_config_file "spotify-settings.json"
  sudo chown -R "$SERVICE_USER" "$PROJECT_DIR/var"
}

git pull
prepare_runtime_permissions

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found. Run ./scripts/install.sh first."
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

pip install -r requirements.txt

sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE_NAME"

echo "Updated and restarted $SERVICE_NAME."
