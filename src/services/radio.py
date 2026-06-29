import json
from pathlib import Path
import shutil
import subprocess
import threading

from services.system import get_audio_device


DEFAULT_STATIONS = [
    {
        "id": "ser",
        "name": "Cadena SER",
        "frequency": "105.4",
        "url": "https://playerservices.streamtheworld.com/api/livestream-redirect/CADENASER.mp3",
    },
    {
        "id": "los40",
        "name": "LOS40",
        "frequency": "93.9",
        "url": "https://playerservices.streamtheworld.com/api/livestream-redirect/LOS40.mp3",
    },
    {
        "id": "dial",
        "name": "Cadena Dial",
        "frequency": "91.7",
        "url": "https://playerservices.streamtheworld.com/api/livestream-redirect/CADENADIAL.mp3",
    },
    {
        "id": "radio3",
        "name": "Radio 3",
        "frequency": "93.2",
        "url": "https://rtvelivestream.akamaized.net/rtvesec/rne/rne_r3_main.m3u8",
    },
    {
        "id": "rne",
        "name": "RNE",
        "frequency": "88.2",
        "url": "https://rtvelivestream.akamaized.net/rtvesec/rne/rne_r1_main.m3u8",
    },
]

PROJECT_DIR = Path(__file__).resolve().parents[2]
RADIO_CONFIG_FILE = PROJECT_DIR / "config" / "radio.json"
_process: subprocess.Popen | None = None
_current_station: dict | None = None
_last_error: str | None = None
_lock = threading.Lock()


def _build_mpv_command(player: str, url: str) -> list[str]:
    command = [
        player,
        "--no-video",
        "--really-quiet",
        "--force-window=no",
    ]
    audio_device = get_audio_device()

    if audio_device:
        command.append(f"--audio-device={audio_device}")

    command.append(url)
    return command


def _station_id(frequency: str, name: str) -> str:
    normalized_frequency = "".join(character for character in frequency if character.isdigit())
    normalized_name = "".join(character.lower() for character in name if character.isalnum())
    return f"{normalized_name or 'station'}-{normalized_frequency or 'fm'}"


def _normalize_station(station: dict) -> dict | None:
    name = str(station.get("name", "")).strip()
    frequency = str(station.get("frequency", "")).strip()
    url = str(station.get("url", "")).strip()

    if not name or not frequency or not url:
        return None

    try:
        frequency_value = float(frequency)
    except ValueError:
        return None

    if frequency_value < 87.5 or frequency_value > 108:
        return None

    frequency = f"{frequency_value:.1f}"

    return {
        "id": str(station.get("id", "")).strip() or _station_id(frequency, name),
        "name": name,
        "frequency": frequency,
        "url": url,
    }


def _read_station_config() -> list[dict]:
    try:
        with RADIO_CONFIG_FILE.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return DEFAULT_STATIONS

    raw_stations = config.get("stations", []) if isinstance(config, dict) else []
    stations = [
        normalized
        for station in raw_stations
        if isinstance(station, dict)
        for normalized in [_normalize_station(station)]
        if normalized is not None
    ]

    return stations or DEFAULT_STATIONS


def _write_station_config(stations: list[dict]) -> None:
    RADIO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with RADIO_CONFIG_FILE.open("w", encoding="utf-8") as config_file:
        json.dump({"stations": stations}, config_file, indent=2)
        config_file.write("\n")


def _find_station(station_id: str | None) -> dict:
    stations = list_stations()

    if station_id:
        for station in stations:
            if station["id"] == station_id or station["frequency"] == station_id:
                return station

    return stations[0]


def _is_process_running() -> bool:
    return _process is not None and _process.poll() is None


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


def list_stations() -> list[dict]:
    return _read_station_config()


def save_station(station: dict) -> dict:
    normalized = _normalize_station(station)

    if normalized is None:
        raise ValueError("station requires name, frequency and url")

    stations = [
        existing
        for existing in list_stations()
        if existing["id"] != normalized["id"] and existing["frequency"] != normalized["frequency"]
    ]
    stations.append(normalized)
    stations.sort(key=lambda item: float(item["frequency"]))
    _write_station_config(stations)
    return normalized


def play_station(station_id: str | None = None) -> dict:
    global _current_station, _last_error, _process

    station = _find_station(station_id)
    player = shutil.which("mpv")

    if player is None:
        _last_error = "mpv is not installed"
        return get_radio_status()

    with _lock:
        _stop_locked()

        _current_station = station
        _last_error = None
        _process = subprocess.Popen(
            _build_mpv_command(player, station["url"]),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return get_radio_status()


def stop_radio() -> dict:
    global _current_station, _last_error

    with _lock:
        _stop_locked()
        _current_station = None
        _last_error = None

    return get_radio_status()


def get_radio_status() -> dict:
    with _lock:
        playing = _is_process_running()
        station = _current_station if playing else None
        state = "playing" if playing else "standby"

        if _current_station is not None and not playing and _last_error is None:
            state = "stopped"

        label = station["name"] if station else "Radio Ready"

        return {
            "available": shutil.which("mpv") is not None,
            "service": "Internet Radio",
            "state": state,
            "label": label,
            "station": station,
            "error": _last_error,
        }
