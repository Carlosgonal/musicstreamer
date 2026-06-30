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

HOST="${MUSICSTREAMER_HOST:-0.0.0.0}"
PORT="${MUSICSTREAMER_PORT:-8080}"

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found. Run ./scripts/install.sh first."
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

export MUSICSTREAMER_HOST="$HOST"
export MUSICSTREAMER_PORT="$PORT"

exec python src/app.py
