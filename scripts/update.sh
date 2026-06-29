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

git pull

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
