import json
from os import getenv
from pathlib import Path
from threading import Lock


PROJECT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_DIR = PROJECT_DIR / "var" / "config"
SYSTEM_CONFIG_FILE = RUNTIME_CONFIG_DIR / "system.json"

_lock = Lock()
_state = {
    "volume": 50,
    "audio_output": getenv("MUSICSTREAMER_AUDIO_OUTPUT", "jack"),
}


def _read_config() -> dict:
    try:
        with SYSTEM_CONFIG_FILE.open("r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def _write_config() -> None:
    SYSTEM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SYSTEM_CONFIG_FILE.open("w", encoding="utf-8") as config_file:
        json.dump(_state, config_file, indent=2)
        config_file.write("\n")


def _load_state() -> None:
    config = _read_config()

    with _lock:
        if isinstance(config.get("volume"), int):
            _state["volume"] = max(0, min(100, config["volume"]))

        audio_output = config.get("audio_output")
        if isinstance(audio_output, str) and audio_output.strip():
            _state["audio_output"] = audio_output.strip().lower()


_load_state()


def get_system_status() -> dict:
    return {
        "service": getenv("MUSICSTREAMER_SERVICE_NAME", "musicstreamer"),
        "status": "running",
        "audio": get_audio_status(),
    }


def get_runtime_status() -> str:
    return get_system_status()["status"]


def get_volume() -> int:
    with _lock:
        return _state["volume"]


def set_volume(volume: int) -> int:
    with _lock:
        _state["volume"] = max(0, min(100, int(volume)))
        _write_config()
        return _state["volume"]


def get_audio_device() -> str:
    with _lock:
        output = _state["audio_output"]

    if output == "hdmi":
        return getenv("MUSICSTREAMER_HDMI_AUDIO_DEVICE", "default")

    if output == "jack":
        return getenv("MUSICSTREAMER_JACK_AUDIO_DEVICE", "default")

    return output or "default"


def get_audio_status() -> dict:
    with _lock:
        output = _state["audio_output"]

    return {
        "output": output,
        "outputs": [
            {"id": "jack", "label": "Jack"},
            {"id": "hdmi", "label": "HDMI"},
        ],
    }


def set_audio_output(output_id: str) -> dict:
    normalized = (output_id or "jack").strip().lower() or "jack"

    if normalized not in {"jack", "hdmi"}:
        normalized = "jack"

    with _lock:
        _state["audio_output"] = normalized
        _write_config()

    return {
        "id": normalized,
        "label": normalized.upper() if normalized == "hdmi" else "Jack",
    }
