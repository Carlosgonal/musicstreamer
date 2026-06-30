from copy import deepcopy
import json
import shutil
import subprocess
import threading
from pathlib import Path

from services.player import set_state


PROJECT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_DIR = PROJECT_DIR / "var" / "config"
RADIO_CONFIG_FILE = RUNTIME_CONFIG_DIR / "radio.json"
LEGACY_RADIO_CONFIG_FILE = PROJECT_DIR / "config" / "radio.json"

DEFAULT_RADIO_STATUS = {
    "stations": [],
    "state": "idle",
    "current_station_id": None,
}

_lock = threading.Lock()
_status = deepcopy(DEFAULT_RADIO_STATUS)
_process: subprocess.Popen | None = None
_backend: str | None = None
_last_error: str | None = None


def _read_config() -> dict:
    config_path = RADIO_CONFIG_FILE if RADIO_CONFIG_FILE.exists() else LEGACY_RADIO_CONFIG_FILE

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return deepcopy(DEFAULT_RADIO_STATUS)

    if not isinstance(data, dict):
        return deepcopy(DEFAULT_RADIO_STATUS)

    stations = data.get("stations", [])
    current_station_id = data.get("current_station_id")

    return {
        "stations": stations if isinstance(stations, list) else [],
        "state": str(data.get("state", "idle")),
        "current_station_id": current_station_id if isinstance(current_station_id, str) else None,
    }


def _write_config(status: dict) -> None:
    RADIO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RADIO_CONFIG_FILE.open("w", encoding="utf-8") as config_file:
        json.dump(status, config_file, indent=2)
        config_file.write("\n")


def _station_title(station: dict | None) -> str:
    if not station:
        return "Radio Ready"
    return str(station.get("name") or "Radio").strip() or "Radio Ready"


def _current_station_locked() -> dict | None:
    stations = list(_status["stations"])

    if not stations:
        return None

    current_id = _status.get("current_station_id")

    if current_id:
        for station in stations:
            if station.get("id") == current_id:
                return station

    return stations[0]


def _snapshot_locked() -> dict:
    current_station = _current_station_locked()
    return {
        "stations": deepcopy(_status["stations"]),
        "state": _status["state"],
        "current_station": deepcopy(current_station) if current_station else None,
        "backend": _backend,
        "error": _last_error,
    }


def _available_backends() -> list[tuple[str, list[str]]]:
    return [
        ("mpv", ["mpv", "--no-video", "--really-quiet"]),
        ("cvlc", ["cvlc", "--intf", "dummy", "--quiet", "--play-and-exit"]),
        ("vlc", ["vlc", "--intf", "dummy", "--quiet", "--play-and-exit"]),
        ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
        ("mplayer", ["mplayer", "-really-quiet"]),
    ]


def _start_stream(url: str) -> tuple[str, subprocess.Popen]:
    last_error: Exception | None = None

    for backend_name, command in _available_backends():
        executable = shutil.which(command[0])
        if not executable:
            continue

        try:
            process = subprocess.Popen(
                [executable, *command[1:], url],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            last_error = error
            continue

        if process.poll() is None:
            return backend_name, process

        last_error = RuntimeError(f"{backend_name} exited with {process.returncode}")

    if last_error is not None:
        raise RuntimeError(str(last_error))

    raise RuntimeError("No radio player found. Install mpv, cvlc, vlc, ffplay or mplayer.")


def _stop_process_locked() -> None:
    global _process, _backend

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
    _backend = None


def get_radio_status() -> dict:
    with _lock:
        return _snapshot_locked()


def list_stations() -> list[dict]:
    return get_radio_status()["stations"]


def save_station(station: dict) -> dict:
    name = str(station.get("name", "")).strip()
    url = str(station.get("url", "")).strip()
    frequency = str(station.get("frequency", "")).strip()

    if not name or not url:
        raise ValueError("station requires name and url")

    saved = {
        "id": str(station.get("id", "")).strip() or name.lower().replace(" ", "-"),
        "name": name,
        "url": url,
    }

    if frequency:
        saved["frequency"] = frequency

    with _lock:
        stations = list(_status["stations"])
        stations = [entry for entry in stations if entry["id"] != saved["id"]]
        stations.append(saved)
        _status["stations"] = stations
        _write_config(_status)

    return saved


def delete_station(station_id: str) -> dict:
    with _lock:
        stations = [entry for entry in _status["stations"] if entry["id"] != station_id]
        _status["stations"] = stations
        if _status.get("current_station_id") == station_id:
            _status["current_station_id"] = stations[0]["id"] if stations else None
        _write_config(_status)
        return _snapshot_locked()


def play_station(station_id: str | None = None) -> dict:
    global _last_error, _backend, _process

    with _lock:
        if station_id:
            _status["current_station_id"] = station_id

        current_station = _current_station_locked()
        if current_station is None:
            _status["state"] = "idle"
            _last_error = "No radio station selected"
            _write_config(_status)
            set_state(source="radio", state="idle", artist=None, title="Radio Ready", album=None, artwork_url=None)
            return _snapshot_locked()

        _stop_process_locked()

        try:
            backend_name, process = _start_stream(str(current_station["url"]))
        except RuntimeError as error:
            _status["state"] = "idle"
            _last_error = str(error)
            _write_config(_status)
            set_state(
                source="radio",
                state="idle",
                artist=None,
                title="Radio Ready",
                album=None,
                artwork_url=None,
            )
            raise

        _process = process
        _backend = backend_name
        _status["state"] = "playing"
        _last_error = None
        _write_config(_status)

    set_state(
        source="radio",
        state="playing",
        artist=current_station.get("frequency") or current_station.get("url"),
        title=_station_title(current_station),
        album="Internet Radio",
        artwork_url=None,
    )

    return get_radio_status()


def stop_radio() -> dict:
    global _last_error

    with _lock:
        _stop_process_locked()
        _status["state"] = "idle"
        _last_error = None
        _write_config(_status)

    set_state(
        source="radio",
        state="idle",
        artist=None,
        title="Radio Ready",
        album=None,
        artwork_url=None,
    )

    return get_radio_status()


def load_radio_state() -> dict:
    with _lock:
        _status.update(_read_config())
        return _snapshot_locked()


load_radio_state()
