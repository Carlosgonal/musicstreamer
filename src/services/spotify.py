import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import time
from urllib.parse import urlencode

import requests

from services.player import get_source, set_state
from services.system import get_audio_device


PROJECT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_DIR = PROJECT_DIR / "var" / "config"
SPOTIFY_CONFIG_FILE = RUNTIME_CONFIG_DIR / "spotify.json"
SPOTIFY_SETTINGS_FILE = RUNTIME_CONFIG_DIR / "spotify-settings.json"
LEGACY_SPOTIFY_CONFIG_FILE = PROJECT_DIR / "config" / "spotify.json"
LEGACY_SPOTIFY_SETTINGS_FILE = PROJECT_DIR / "config" / "spotify-settings.json"
SPOTIFY_ACCOUNTS_URL = "https://accounts.spotify.com"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
SPOTIFY_SCOPES = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
RASPOTIFY_SERVICE_FILES = (
    Path("/etc/systemd/system/raspotify.service"),
    Path("/lib/systemd/system/raspotify.service"),
    Path("/usr/lib/systemd/system/raspotify.service"),
)
RASPOTIFY_CONFIG_FILE = Path("/etc/raspotify/conf")

_process: subprocess.Popen | None = None
_last_error: str | None = None
_lock = threading.Lock()


def _is_enabled() -> bool:
    return _setting_bool("enabled", "SPOTIFY_ENABLED", False)


def _is_process_running() -> bool:
    return _process is not None and _process.poll() is None


def _path_exists_safe(path: Path) -> bool:
    try:
        return path.exists()
    except PermissionError:
        return False


def _raspotify_installed() -> bool:
    return _path_exists_safe(RASPOTIFY_CONFIG_FILE) or any(_path_exists_safe(path) for path in RASPOTIFY_SERVICE_FILES)


def _run_systemctl(*args: str) -> subprocess.CompletedProcess[str]:
    systemctl = shutil.which("systemctl")

    if systemctl is None:
        raise RuntimeError("systemctl is not installed")

    return subprocess.run(
        [systemctl, "--no-ask-password", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _raspotify_running() -> bool:
    if not _raspotify_installed():
        return False

    try:
        result = _run_systemctl("is-active", "raspotify")
    except (RuntimeError, subprocess.CalledProcessError):
        return False

    return result.stdout.strip() == "active"


def _client_id() -> str:
    return _setting("client_id", "SPOTIFY_CLIENT_ID")


def _client_secret() -> str:
    return _setting("client_secret", "SPOTIFY_CLIENT_SECRET")


def _redirect_uri() -> str:
    return _setting("redirect_uri", "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8080/api/spotify/callback")


def _read_config() -> dict:
    config_path = SPOTIFY_CONFIG_FILE if SPOTIFY_CONFIG_FILE.exists() else LEGACY_SPOTIFY_CONFIG_FILE

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    return config if isinstance(config, dict) else {}


def _write_config(config: dict) -> None:
    SPOTIFY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with SPOTIFY_CONFIG_FILE.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)
        config_file.write("\n")


def _read_settings() -> dict:
    settings_path = SPOTIFY_SETTINGS_FILE if SPOTIFY_SETTINGS_FILE.exists() else LEGACY_SPOTIFY_SETTINGS_FILE

    try:
        with settings_path.open("r", encoding="utf-8") as settings_file:
            settings = json.load(settings_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    return settings if isinstance(settings, dict) else {}


def _write_settings(settings: dict) -> None:
    SPOTIFY_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with SPOTIFY_SETTINGS_FILE.open("w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, indent=2)
        settings_file.write("\n")


def _setting(key: str, env_name: str, default: str = "") -> str:
    value = str(_read_settings().get(key, "")).strip()

    if value:
        return value

    return os.getenv(env_name, default).strip()


def _setting_bool(key: str, env_name: str, default: bool = False) -> bool:
    value = _read_settings().get(key)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

    env_value = os.getenv(env_name)

    if env_value is not None:
        normalized = env_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False

    return default


def _token_config() -> dict:
    token = _read_config().get("token", {})
    return token if isinstance(token, dict) else {}


def _has_credentials() -> bool:
    return bool(_client_id() and _client_secret() and _redirect_uri())


def get_admin_settings() -> dict:
    settings = _read_settings()

    return {
        "enabled": _is_enabled(),
        "device_name": _setting("device_name", "SPOTIFY_DEVICE_NAME", "MusicStreamer"),
        "bitrate": _setting("bitrate", "SPOTIFY_BITRATE", "320"),
        "cache_dir": _setting("cache_dir", "SPOTIFY_CACHE_DIR", ""),
        "client_id": _client_id(),
        "client_secret_set": bool(settings.get("client_secret") or os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()),
        "redirect_uri": _redirect_uri(),
        "linked": is_authenticated(),
    }


def save_admin_settings(payload: dict) -> dict:
    current = _read_settings()
    next_settings = dict(current)

    enabled_value = payload.get("enabled", current.get("enabled", True))

    if isinstance(enabled_value, str):
        enabled_value = enabled_value.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enabled_value = bool(enabled_value)

    next_settings["enabled"] = enabled_value

    device_name = str(payload.get("device_name", "")).strip()
    bitrate = str(payload.get("bitrate", "")).strip()
    cache_dir = str(payload.get("cache_dir", "")).strip()
    client_id = str(payload.get("client_id", "")).strip()
    client_secret = str(payload.get("client_secret", "")).strip()
    redirect_uri = str(payload.get("redirect_uri", "")).strip()

    if device_name:
        next_settings["device_name"] = device_name

    if bitrate:
        next_settings["bitrate"] = bitrate

    next_settings["cache_dir"] = cache_dir

    if client_id:
        next_settings["client_id"] = client_id

    if client_secret:
        next_settings["client_secret"] = client_secret

    if redirect_uri:
        next_settings["redirect_uri"] = redirect_uri

    _write_settings(next_settings)

    if not next_settings.get("enabled", True):
        stop_spotify()

    return get_admin_settings()


def is_authenticated() -> bool:
    token = _token_config()
    return bool(token.get("access_token") or token.get("refresh_token"))


def get_authorize_url() -> str:
    if not _has_credentials():
        raise RuntimeError("Spotify credentials are not configured")

    config = _read_config()
    state = secrets.token_urlsafe(24)
    config["oauth_state"] = state
    _write_config(config)

    params = {
        "client_id": _client_id(),
        "response_type": "code",
        "redirect_uri": _redirect_uri(),
        "scope": SPOTIFY_SCOPES,
        "state": state,
    }

    return f"{SPOTIFY_ACCOUNTS_URL}/authorize?{urlencode(params)}"


def _auth_header() -> dict:
    raw_credentials = f"{_client_id()}:{_client_secret()}".encode("utf-8")
    encoded_credentials = base64.b64encode(raw_credentials).decode("ascii")
    return {"Authorization": f"Basic {encoded_credentials}"}


def _save_token(token: dict) -> None:
    config = _read_config()
    previous_token = config.get("token", {}) if isinstance(config.get("token"), dict) else {}

    if "refresh_token" not in token and previous_token.get("refresh_token"):
        token["refresh_token"] = previous_token["refresh_token"]

    token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600)) - 60
    config["token"] = token
    config.pop("oauth_state", None)
    _write_config(config)


def handle_oauth_callback(code: str, state: str) -> None:
    config = _read_config()

    if not _has_credentials():
        raise RuntimeError("Spotify credentials are not configured")

    if not state or state != config.get("oauth_state"):
        raise RuntimeError("Spotify authorization state mismatch")

    response = requests.post(
        f"{SPOTIFY_ACCOUNTS_URL}/api/token",
        headers=_auth_header(),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
        },
        timeout=10,
    )
    response.raise_for_status()
    _save_token(response.json())


def _refresh_access_token() -> str | None:
    token = _token_config()
    refresh_token = token.get("refresh_token")

    if not refresh_token or not _has_credentials():
        return None

    response = requests.post(
        f"{SPOTIFY_ACCOUNTS_URL}/api/token",
        headers=_auth_header(),
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=10,
    )
    response.raise_for_status()
    _save_token(response.json())
    return _token_config().get("access_token")


def _access_token() -> str | None:
    token = _token_config()
    access_token = token.get("access_token")

    if not access_token:
        return _refresh_access_token()

    if int(token.get("expires_at", 0)) <= int(time.time()):
        return _refresh_access_token()

    return access_token


def _spotify_request(method: str, path: str, **kwargs) -> requests.Response | None:
    access_token = _access_token()

    if not access_token:
        return None

    response = requests.request(
        method,
        f"{SPOTIFY_API_URL}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
        **kwargs,
    )

    if response.status_code == 401 and _refresh_access_token():
        response = requests.request(
            method,
            f"{SPOTIFY_API_URL}{path}",
            headers={"Authorization": f"Bearer {_access_token()}"},
            timeout=10,
            **kwargs,
        )

    return response


def _current_playback() -> dict | None:
    global _last_error

    if not is_authenticated():
        return None

    response = _spotify_request("GET", "/me/player")

    if response is None or response.status_code == 204:
        return None

    if not response.ok:
        _last_error = f"Spotify API returned {response.status_code}"
        return None

    data = response.json()
    item = data.get("item") or {}
    album = item.get("album") or {}
    images = album.get("images") or []
    device = data.get("device") or {}

    return {
        "is_playing": bool(data.get("is_playing")),
        "progress_ms": int(data.get("progress_ms") or 0),
        "duration_ms": int(item.get("duration_ms") or 0),
        "track": item.get("name") or "Spotify",
        "artist": ", ".join(artist.get("name", "") for artist in item.get("artists", []) if artist.get("name")),
        "album": album.get("name") or "",
        "image": images[0]["url"] if images else "",
        "device": {
            "id": device.get("id"),
            "name": device.get("name"),
            "volume_percent": device.get("volume_percent"),
            "is_active": device.get("is_active"),
        },
    }


def _librespot_device() -> str:
    audio_device = get_audio_device()

    if audio_device.startswith("alsa/"):
        return audio_device.removeprefix("alsa/")

    return audio_device


def _raspotify_config_content() -> str:
    return "\n".join([
        "# Managed by MusicStreamer",
        f'LIBRESPOT_NAME="{_setting("device_name", "SPOTIFY_DEVICE_NAME", "MusicStreamer")}"',
        'LIBRESPOT_BACKEND="alsa"',
        f'LIBRESPOT_DEVICE="{_librespot_device()}"',
        f'LIBRESPOT_BITRATE="{_setting("bitrate", "SPOTIFY_BITRATE", "320")}"',
        'LIBRESPOT_VOLUME_CTRL="alsa"',
        'LIBRESPOT_INITIAL_VOLUME="80"',
        'LIBRESPOT_DISABLE_AUDIO_CACHE="true"',
        "",
    ])


def _sync_raspotify_config() -> None:
    if not _raspotify_installed():
        return

    RASPOTIFY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    RASPOTIFY_CONFIG_FILE.write_text(_raspotify_config_content(), encoding="utf-8")


def _build_librespot_command(player: str) -> list[str]:
    command = [
        player,
        "--name",
        _setting("device_name", "SPOTIFY_DEVICE_NAME", "MusicStreamer"),
        "--backend",
        "alsa",
        "--bitrate",
        _setting("bitrate", "SPOTIFY_BITRATE", "320"),
        "--disable-audio-cache",
    ]
    device = _librespot_device()

    if device:
        command.extend(["--device", device])

    cache_dir = _setting("cache_dir", "SPOTIFY_CACHE_DIR")

    if cache_dir:
        command.extend(["--cache", cache_dir])

    return command


def _stop_locked() -> None:
    global _process

    if _process is None:
        return

    if _process.poll() is None:
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
            _process.wait(timeout=2)

    _process = None


def start_spotify() -> dict:
    global _last_error, _process

    player = shutil.which("librespot")

    if not _is_enabled():
        _last_error = "Spotify disabled"
        set_state(
            source="spotify",
            state="idle",
            artist=None,
            title="Spotify Disabled",
            album=None,
            artwork_url=None,
        )
        return get_spotify_status()

    if _raspotify_installed():
        try:
            _sync_raspotify_config()
        except OSError as error:
            _last_error = str(error)

        try:
            _run_systemctl("start", "raspotify")
            if _last_error is None or "raspotify" in _last_error.lower():
                _last_error = None
        except (RuntimeError, subprocess.CalledProcessError) as error:
            _last_error = str(error)

        return get_spotify_status()

    if player is None:
        _last_error = "Raspotify is not installed"
        set_state(
            source="spotify",
            state="idle",
            artist=None,
            title="Install Raspotify",
            album=None,
            artwork_url=None,
        )
        return get_spotify_status()

    with _lock:
        _stop_locked()
        _last_error = None
        _process = subprocess.Popen(
            _build_librespot_command(player),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return get_spotify_status()


def stop_spotify() -> dict:
    global _last_error

    if _raspotify_installed():
        try:
            _run_systemctl("stop", "raspotify")
            _last_error = None
        except (RuntimeError, subprocess.CalledProcessError) as error:
            _last_error = str(error)

        set_state(
            source="spotify",
            state="idle",
            artist=None,
            title="Spotify Ready",
            album=None,
            artwork_url=None,
        )
        return get_spotify_status()

    with _lock:
        _stop_locked()
        _last_error = None

    set_state(
        source="spotify",
        state="idle",
        artist=None,
        title="Spotify Ready",
        album=None,
        artwork_url=None,
    )

    return get_spotify_status()


def control_playback(action: str) -> dict:
    global _last_error

    endpoints = {
        "play": ("PUT", "/me/player/play"),
        "pause": ("PUT", "/me/player/pause"),
        "next": ("POST", "/me/player/next"),
        "previous": ("POST", "/me/player/previous"),
    }

    if action not in endpoints:
        raise ValueError("unknown Spotify action")

    if not is_authenticated():
        raise RuntimeError("Spotify account is not linked")

    method, endpoint = endpoints[action]

    try:
        response = _spotify_request(method, endpoint)
    except requests.RequestException as error:
        _last_error = str(error)
        raise RuntimeError(_last_error) from error

    if response is None:
        raise RuntimeError("Spotify account is not linked")

    if response.status_code not in {200, 202, 204}:
        _last_error = f"Spotify API returned {response.status_code}"
        raise RuntimeError(_last_error)

    _last_error = None
    return get_spotify_status()


def pause_spotify() -> dict:
    if not is_authenticated():
        return get_spotify_status()

    try:
        return control_playback("pause")
    except RuntimeError:
        return get_spotify_status()


def release_spotify_audio() -> dict:
    global _last_error

    if _raspotify_installed():
        try:
            _run_systemctl("stop", "raspotify")
            _last_error = None
            return get_spotify_status()
        except (RuntimeError, subprocess.CalledProcessError) as error:
            _last_error = str(error)

    with _lock:
        _stop_locked()

    return pause_spotify()


def set_spotify_volume(volume: int) -> dict:
    global _last_error

    if not is_authenticated():
        return get_spotify_status()

    clamped_volume = max(0, min(100, int(volume)))

    try:
        response = _spotify_request("PUT", f"/me/player/volume?volume_percent={clamped_volume}")
    except requests.RequestException as error:
        _last_error = str(error)
        return get_spotify_status()

    if response is not None and response.status_code not in {200, 202, 204}:
        _last_error = f"Spotify volume returned {response.status_code}"

    return get_spotify_status()


def _current_playback_safe() -> dict | None:
    global _last_error

    try:
        return _current_playback()
    except Exception as error:
        _last_error = str(error)
        return None


def get_spotify_status() -> dict:
    global _last_error

    enabled = _is_enabled()
    raspotify_installed = _raspotify_installed()
    installed = raspotify_installed or shutil.which("librespot") is not None
    available = enabled and installed
    playing = _raspotify_running() if raspotify_installed else _is_process_running()
    authenticated = is_authenticated()
    ready_for_controls = _has_credentials() and authenticated
    playback = _current_playback_safe()

    if playback and playback["is_playing"]:
        state = "playing"
        label = "On"
    elif not enabled:
        state = "disabled"
        label = "Disabled"
    elif not _has_credentials():
        state = "setup"
        label = "Add API keys"
    elif not authenticated:
        state = "auth"
        label = "Link account"
    elif not installed:
        state = "missing"
        label = "Install Raspotify"
    elif playing:
        state = "standby"
        label = "Connect"
    elif _last_error:
        state = "error"
        label = _last_error
    else:
        state = "standby"
        label = "Ready"

    if playback and get_source() == "spotify":
        _last_error = None
        set_state(
            source="spotify",
            state="playing" if playback["is_playing"] else "idle",
            artist=playback["artist"] or None,
            title=playback["track"] or "Spotify",
            album=playback["album"] or None,
            artwork_url=playback["image"] or None,
        )

    return {
        "available": available,
        "service": "Spotify Connect",
        "state": state,
        "label": label,
        "error": _last_error,
        "device_name": _setting("device_name", "SPOTIFY_DEVICE_NAME", "MusicStreamer"),
        "audio_device": _librespot_device(),
        "authenticated": authenticated,
        "credentials_configured": _has_credentials(),
        "controls_available": ready_for_controls,
        "player": playback,
        "admin": get_admin_settings(),
    }
