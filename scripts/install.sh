#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
ENV_FILE="$PROJECT_DIR/env/.env"
ENV_TEMPLATE="$PROJECT_DIR/env/template.env"

cd "$PROJECT_DIR"

mkdir -p "$PROJECT_DIR/env"

if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_TEMPLATE" ]; then
  echo "Creating env/.env from template"
  cp "$ENV_TEMPLATE" "$ENV_FILE"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR"
  python3 -m venv --system-site-packages "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "Installing Python dependencies"
if ! python -m pip install -r requirements.txt; then
  echo "Warning: dependency install failed; continuing with available system packages."
fi

echo "Installation complete."
echo "Start now with: ./scripts/start.sh"
