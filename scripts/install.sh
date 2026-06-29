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
RASPOTIFY_KEYRING="/usr/share/keyrings/raspotify.gpg"
RASPOTIFY_SOURCE_LIST="/etc/apt/sources.list.d/raspotify.list"

collect_missing_packages() {
  MISSING_PACKAGES=()

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

  if ! command -v amixer >/dev/null 2>&1; then
    MISSING_PACKAGES+=("alsa-utils")
  fi

  if ! command -v curl >/dev/null 2>&1; then
    MISSING_PACKAGES+=("curl")
  fi

  if ! command -v gpg >/dev/null 2>&1; then
    MISSING_PACKAGES+=("gnupg")
  fi
}

spotify_alsa_device() {
  local output="${MUSICSTREAMER_AUDIO_OUTPUT:-jack}"
  local device

  if [ "$output" = "hdmi" ]; then
    device="${MUSICSTREAMER_HDMI_AUDIO_DEVICE:-alsa/hdmi:CARD=vc4hdmi0,DEV=0}"
  else
    device="${MUSICSTREAMER_JACK_AUDIO_DEVICE:-alsa/plughw:CARD=Headphones,DEV=0}"
  fi

  printf '%s\n' "${device#alsa/}"
}

install_raspotify() {
  if [ "${SPOTIFY_ENABLED:-false}" != "true" ]; then
    return
  fi

  echo "Installing Raspotify for Spotify Connect"

  if [ ! -f "$RASPOTIFY_KEYRING" ]; then
    curl -fsSL https://dtcooper.github.io/raspotify/key.asc | sudo gpg --dearmor -o "$RASPOTIFY_KEYRING"
  fi

  if [ ! -f "$RASPOTIFY_SOURCE_LIST" ]; then
    echo "deb [signed-by=$RASPOTIFY_KEYRING] https://dtcooper.github.io/raspotify raspotify main" | sudo tee "$RASPOTIFY_SOURCE_LIST" >/dev/null
  fi

  sudo apt-get update
  sudo apt-get install -y --no-upgrade raspotify

  local conf_file="/tmp/raspotify.conf"
  local device_name="${SPOTIFY_DEVICE_NAME:-MusicStreamer}"
  local bitrate="${SPOTIFY_BITRATE:-320}"
  local audio_device
  audio_device="$(spotify_alsa_device)"

  cat > "$conf_file" <<EOF
# Managed by MusicStreamer install.sh
LIBRESPOT_NAME="$device_name"
LIBRESPOT_BACKEND="alsa"
LIBRESPOT_DEVICE="$audio_device"
LIBRESPOT_BITRATE="$bitrate"
LIBRESPOT_OPTIONS="--disable-audio-cache"
EOF

  sudo install -m 0644 "$conf_file" /etc/raspotify/conf
  rm -f "$conf_file"

  sudo systemctl daemon-reload
  sudo systemctl enable raspotify
  sudo systemctl restart raspotify

  echo "Raspotify installed and configured for device '$device_name' on ALSA device '$audio_device'."
}

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required to install system packages and the systemd service."
  exit 1
fi

collect_missing_packages

if [ "${#MISSING_PACKAGES[@]}" -gt 0 ]; then
  echo "Installing missing system packages: ${MISSING_PACKAGES[*]}"
  sudo apt-get update
  if ! sudo apt-get install -y --no-upgrade "${MISSING_PACKAGES[@]}"; then
    collect_missing_packages

    if [ "${#MISSING_PACKAGES[@]}" -gt 0 ]; then
      echo "apt failed and these packages are still missing: ${MISSING_PACKAGES[*]}"
      echo "Repair apt/dpkg on the Raspberry Pi and run this script again."
      exit 1
    fi

    echo "apt reported an error, but required packages are now available."
    echo "Continuing with MusicStreamer setup. Repair apt/dpkg later."
  fi
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

install_raspotify

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
