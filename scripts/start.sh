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

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

export FLASK_ENV="${FLASK_ENV:-development}"
export MUSICSTREAMER_HOST="$HOST"
export MUSICSTREAMER_PORT="$PORT"

echo "Starting MusicStreamer on http://$HOST:$PORT"
python src/app.py
