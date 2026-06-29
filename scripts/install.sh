#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
ENV_FILE="$PROJECT_DIR/env/.env"
ENV_TEMPLATE="$PROJECT_DIR/env/template.env"

cd "$PROJECT_DIR"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

SERVICE_NAME="${MUSICSTREAMER_SERVICE_NAME:-musicstreamer}"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
SERVICE_TEMPLATE="$PROJECT_DIR/deploy/musicstreamer.service"
SERVICE_USER="${MUSICSTREAMER_SERVICE_USER:-$USER}"
SERVICE_BUILD_FILE="/tmp/$SERVICE_NAME.service"
MISSING_PACKAGES=()

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install system packages and the systemd service."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  MISSING_PACKAGES+=("python3")
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  MISSING_PACKAGES+=("python3-venv")
fi

if ! python3 -m pip --version >/dev/null 2>&1; then
  MISSING_PACKAGES+=("python3-pip")
fi

if ! command -v git >/dev/null 2>&1; then
  MISSING_PACKAGES+=("git")
fi

if ! command -v mpv >/dev/null 2>&1; then
  MISSING_PACKAGES+=("mpv")
fi

if [ "${#MISSING_PACKAGES[@]}" -gt 0 ]; then
  echo "Installing missing system packages: ${MISSING_PACKAGES[*]}"
  sudo apt-get update
  sudo apt-get install -y --no-upgrade "${MISSING_PACKAGES[@]}"
else
  echo "System packages already available; skipping apt install."
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Creating env/.env from template"
  cp "$ENV_TEMPLATE" "$ENV_FILE"
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

echo "Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Installing systemd service: $SERVICE_NAME"
sed \
  -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
  -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
  "$SERVICE_TEMPLATE" > "$SERVICE_BUILD_FILE"

sudo install -m 0644 "$SERVICE_BUILD_FILE" "$SERVICE_FILE"
rm -f "$SERVICE_BUILD_FILE"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo "Installation complete."
echo "Start now with: sudo systemctl start $SERVICE_NAME"
echo "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
