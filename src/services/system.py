from os import getenv
from threading import Lock


_lock = Lock()
_state = {
    "volume": 50,
    "audio_output": getenv("MUSICSTREAMER_AUDIO_OUTPUT", "jack"),
}


def get_system_status() -> dict:
    return {
        "service": getenv("MUSICSTREAMER_SERVICE_NAME", "musicstreamer"),
        "status": "running",
    }


def get_runtime_status() -> str:
    return get_system_status()["status"]


def get_volume() -> int:
    with _lock:
        return _state["volume"]


def set_volume(volume: int) -> int:
    with _lock:
        _state["volume"] = max(0, min(100, int(volume)))
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

    return {
        "id": normalized,
        "label": normalized.upper() if normalized == "hdmi" else "Jack",
    }
