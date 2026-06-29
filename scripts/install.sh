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
RASPOTIFY_RELEASE_API="https://api.github.com/repos/dtcooper/raspotify/releases/latest"
RASPOTIFY_ASOUND_DEB_FILE="/tmp/raspotify-asound-conf-wizard.deb"
RASPOTIFY_DEB_FILE="/tmp/raspotify-package.deb"

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

raspotify_deb_arch() {
  case "$(uname -m)" in
    aarch64|arm64)
      printf '%s\n' "arm64"
      ;;
    armv6l|armv7l|armhf)
      printf '%s\n' "armhf"
      ;;
    x86_64|amd64)
      printf '%s\n' "amd64"
      ;;
    *)
      echo "Unsupported architecture for manual Raspotify install: $(uname -m)"
      exit 1
      ;;
  esac
}

download_raspotify_debs() {
  local arch
  local release_json
  local asound_url
  local raspotify_url

  arch="$(raspotify_deb_arch)"
  release_json="$(mktemp)"

  curl -fsSL "$RASPOTIFY_RELEASE_API" -o "$release_json"

  readarray -t package_urls < <(
    python3 - "$release_json" "$arch" <<'PY'
import json
import sys

release_file, arch = sys.argv[1], sys.argv[2]

with open(release_file, "r", encoding="utf-8") as handle:
    release = json.load(handle)

def find_url(prefix):
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        url = asset.get("browser_download_url", "")

        if name.startswith(prefix) and name.endswith(f"_{arch}.deb") and url:
            return url

    return ""

print(find_url("asound-conf-wizard_"))
print(find_url("raspotify_"))
PY
  )

  rm -f "$release_json"
  asound_url="${package_urls[0]:-}"
  raspotify_url="${package_urls[1]:-}"

  if [ -z "$asound_url" ] || [ -z "$raspotify_url" ]; then
    echo "Could not find all Raspotify .deb packages for architecture '$arch'."
    exit 1
  fi

  echo "Downloading Raspotify packages for '$arch'"
  curl -fL "$asound_url" -o "$RASPOTIFY_ASOUND_DEB_FILE"
  curl -fL "$raspotify_url" -o "$RASPOTIFY_DEB_FILE"
}

install_raspotify() {
  if [ "${SPOTIFY_ENABLED:-false}" != "true" ]; then
    return
  fi

  echo "Installing Raspotify for Spotify Connect"

  if ! dpkg-query -W -f='${Status}' raspotify 2>/dev/null | grep -q "install ok installed"; then
    download_raspotify_debs
    sudo apt-get install -y "$RASPOTIFY_ASOUND_DEB_FILE" "$RASPOTIFY_DEB_FILE"
    rm -f "$RASPOTIFY_ASOUND_DEB_FILE" "$RASPOTIFY_DEB_FILE"
  else
    echo "Raspotify package is already installed."
  fi

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

prepare_runtime_permissions() {
  mkdir -p "$PROJECT_DIR/var/config"
  migrate_runtime_config_file "audio.json"
  migrate_runtime_config_file "radio.json"
  migrate_runtime_config_file "spotify.json"
  migrate_runtime_config_file "spotify-settings.json"
  sudo chown -R "$SERVICE_USER" "$PROJECT_DIR/var"
}

migrate_runtime_config_file() {
  local filename="$1"
  local legacy_file="$PROJECT_DIR/config/$filename"
  local runtime_file="$PROJECT_DIR/var/config/$filename"

  if [ -f "$legacy_file" ] && [ ! -f "$runtime_file" ]; then
    cp "$legacy_file" "$runtime_file"
  fi
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
prepare_runtime_permissions

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
