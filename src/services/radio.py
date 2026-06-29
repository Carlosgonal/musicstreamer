import os
import shutil
import subprocess
import threading


DEFAULT_STATIONS = [
    {
        "id": "fip",
        "name": "FIP",
        "url": "https://icecast.radiofrance.fr/fip-midfi.mp3",
    },
    {
        "id": "bbc6",
        "name": "BBC 6 Music",
        "url": "https://stream.live.vc.bbcmedia.co.uk/bbc_6music",
    },
    {
        "id": "ambient",
        "name": "Ambient Sleeping Pill",
        "url": "https://radio.stereoscenic.com/asp-h",
    },
]

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
    audio_device = os.getenv("MUSICSTREAMER_MPV_AUDIO_DEVICE", "").strip()

    if audio_device:
        command.append(f"--audio-device={audio_device}")

    command.append(url)
    return command


def _find_station(station_id: str | None) -> dict:
    if station_id:
        for station in DEFAULT_STATIONS:
            if station["id"] == station_id:
                return station

    return DEFAULT_STATIONS[0]


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
    return DEFAULT_STATIONS


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
