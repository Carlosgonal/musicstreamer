from datetime import datetime
import os
import re
import shutil
import subprocess


DEFAULT_VOLUME = 50
VOLUME_CONTROLS = ("Headphone", "Master", "PCM")


def get_runtime_status() -> str:
    if os.getenv("FLASK_DEBUG", "0") == "1" or os.getenv("FLASK_ENV") == "development":
        return "Development mode"

    return "Ready"


def _configured_volume_controls() -> list[str]:
    configured = os.getenv("MUSICSTREAMER_ALSA_MIXER", "").strip()

    if configured:
        return [control.strip() for control in configured.split(",") if control.strip()]

    return list(VOLUME_CONTROLS)


def _run_amixer(args: list[str]) -> subprocess.CompletedProcess[str]:
    amixer = shutil.which("amixer")

    if amixer is None:
        raise RuntimeError("amixer is not installed")

    return subprocess.run(
        [amixer, "-M", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _read_control_volume(control: str) -> int | None:
    try:
        result = _run_amixer(["sget", control])
    except (RuntimeError, subprocess.CalledProcessError):
        return None

    matches = re.findall(r"\[(\d{1,3})%\]", result.stdout)

    if not matches:
        return None

    return max(0, min(100, int(matches[0])))


def get_volume() -> int:
    for control in _configured_volume_controls():
        volume = _read_control_volume(control)

        if volume is not None:
            return volume

    return DEFAULT_VOLUME


def set_volume(volume: int) -> int:
    clamped_volume = max(0, min(100, int(volume)))

    for control in _configured_volume_controls():
        try:
            _run_amixer(["sset", control, f"{clamped_volume}%"])
            return get_volume()
        except subprocess.CalledProcessError:
            continue

    raise RuntimeError("No ALSA mixer control accepted the volume change")


def get_system_status() -> dict:
    now = datetime.now()

    return {
        "project": "MusicStreamer",
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "status": get_runtime_status(),
        "network": "Local",
        "volume": get_volume(),
    }
