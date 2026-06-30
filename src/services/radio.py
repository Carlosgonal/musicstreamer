from copy import deepcopy
import json
from pathlib import Path
from threading import Lock

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

_lock = Lock()
_status = deepcopy(DEFAULT_RADIO_STATUS)


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
    }


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
    with _lock:
        if station_id:
            _status["current_station_id"] = station_id

        current_station = _current_station_locked()
        _status["state"] = "playing" if current_station else "idle"
        _write_config(_status)

    set_state(
        source="radio",
        state="playing" if current_station else "idle",
        artist=None,
        title=_station_title(current_station),
        album="Internet Radio" if current_station else None,
        artwork_url=None,
    )

    return get_radio_status()


def stop_radio() -> dict:
    with _lock:
        _status["state"] = "idle"
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
