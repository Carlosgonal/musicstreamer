#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
ENV_FILE="$PROJECT_DIR/env/.env"
ENV_TEMPLATE="$PROJECT_DIR/env/template.env"
RADIO_TEMPLATE="$PROJECT_DIR/deploy/radio.json.template"
RADIO_CONFIG_DIR="$PROJECT_DIR/var/config"
RADIO_CONFIG_FILE="$RADIO_CONFIG_DIR/radio.json"
SERVICE_NAME="${MUSICSTREAMER_SERVICE_NAME:-musicstreamer}"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"
SERVICE_TEMPLATE="$PROJECT_DIR/deploy/musicstreamer.service"
SERVICE_USER="${MUSICSTREAMER_SERVICE_USER:-$USER}"
SERVICE_BUILD_FILE="/tmp/$SERVICE_NAME.service"
RASPOTIFY_CONFIG_FILE="/etc/raspotify/conf"
RASPOTIFY_BUILD_FILE="/tmp/raspotify.conf"
MISSING_PACKAGES=()

cd "$PROJECT_DIR"

mkdir -p "$PROJECT_DIR/env"
mkdir -p "$RADIO_CONFIG_DIR"

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
  if command -v sudo >/dev/null 2>&1; then
    echo "Installing missing system packages: ${MISSING_PACKAGES[*]}"
    sudo apt-get update
    sudo apt-get install -y --no-upgrade "${MISSING_PACKAGES[@]}"
  else
    echo "Missing system packages: ${MISSING_PACKAGES[*]}"
    echo "sudo is required to install them."
    exit 1
  fi
fi

if [ ! -f "$ENV_FILE" ] && [ -f "$ENV_TEMPLATE" ]; then
  echo "Creating env/.env from template"
  cp "$ENV_TEMPLATE" "$ENV_FILE"
fi

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

if [ ! -f "$RADIO_CONFIG_FILE" ] && [ -f "$RADIO_TEMPLATE" ]; then
  echo "Creating var/config/radio.json from template"
  cp "$RADIO_TEMPLATE" "$RADIO_CONFIG_FILE"
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

if command -v sudo >/dev/null 2>&1; then
  if command -v systemctl >/dev/null 2>&1 && { systemctl list-unit-files raspotify.service >/dev/null 2>&1 || [ -f "$RASPOTIFY_CONFIG_FILE" ]; }; then
    AUDIO_OUTPUT="${MUSICSTREAMER_AUDIO_OUTPUT:-jack}"
    if [ "$AUDIO_OUTPUT" = "hdmi" ]; then
      SPOTIFY_AUDIO_DEVICE="${MUSICSTREAMER_HDMI_AUDIO_DEVICE:-alsa/hdmi:CARD=vc4hdmi0,DEV=0}"
    else
      SPOTIFY_AUDIO_DEVICE="${MUSICSTREAMER_JACK_AUDIO_DEVICE:-alsa/plughw:CARD=Headphones,DEV=0}"
    fi
    SPOTIFY_AUDIO_DEVICE="${SPOTIFY_AUDIO_DEVICE#alsa/}"

    echo "Configuring Raspotify audio output: $SPOTIFY_AUDIO_DEVICE"
    {
      printf '%s\n' "# Managed by MusicStreamer install.sh"
      printf 'LIBRESPOT_NAME="%s"\n' "${SPOTIFY_DEVICE_NAME:-MusicStreamer}"
      printf 'LIBRESPOT_BACKEND="alsa"\n'
      printf 'LIBRESPOT_DEVICE="%s"\n' "$SPOTIFY_AUDIO_DEVICE"
      printf 'LIBRESPOT_BITRATE="%s"\n' "${SPOTIFY_BITRATE:-320}"
      printf 'LIBRESPOT_VOLUME_CTRL="alsa"\n'
      printf 'LIBRESPOT_INITIAL_VOLUME="%s"\n' "80"
      printf 'LIBRESPOT_DISABLE_AUDIO_CACHE="true"\n'
    } > "$RASPOTIFY_BUILD_FILE"
    sudo install -m 0644 "$RASPOTIFY_BUILD_FILE" "$RASPOTIFY_CONFIG_FILE"
    rm -f "$RASPOTIFY_BUILD_FILE"
    sudo systemctl daemon-reload
    sudo systemctl restart raspotify || true
  fi

  echo "Installing systemd service: $SERVICE_NAME"
  sed \
    -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
    -e "s|__SERVICE_USER__|$SERVICE_USER|g" \
    "$SERVICE_TEMPLATE" > "$SERVICE_BUILD_FILE"

  sudo install -m 0644 "$SERVICE_BUILD_FILE" "$SERVICE_FILE"
  rm -f "$SERVICE_BUILD_FILE"

  sudo systemctl daemon-reload
  sudo systemctl enable "$SERVICE_NAME"
else
  echo "Skipping systemd service install because sudo is not available."
fi

echo "Installation complete."
echo "Start now with: sudo systemctl start $SERVICE_NAME"
