from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


DEFAULT_VOLUME = 50
VOLUME_CONTROLS = ("Headphone", "Master", "PCM")
PROJECT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG_DIR = PROJECT_DIR / "var" / "config"
AUDIO_CONFIG_FILE = RUNTIME_CONFIG_DIR / "audio.json"
LEGACY_AUDIO_CONFIG_FILE = PROJECT_DIR / "config" / "audio.json"


def get_runtime_status() -> str:
    if os.getenv("FLASK_DEBUG", "0") == "1" or os.getenv("FLASK_ENV") == "development":
        return "Development mode"

    return "Ready"


def _audio_outputs() -> list[dict]:
    jack_device = os.getenv(
        "MUSICSTREAMER_JACK_AUDIO_DEVICE",
        os.getenv("MUSICSTREAMER_MPV_AUDIO_DEVICE", "alsa/plughw:CARD=Headphones,DEV=0"),
    )
    hdmi_device = os.getenv("MUSICSTREAMER_HDMI_AUDIO_DEVICE", "alsa/hdmi:CARD=vc4hdmi0,DEV=0")

    return [
        {
            "id": "jack",
            "label": "Jack",
            "device": jack_device,
            "mixer_card": os.getenv("MUSICSTREAMER_JACK_ALSA_CARD", _alsa_card_from_device(jack_device)),
            "mixers": _split_controls(os.getenv("MUSICSTREAMER_JACK_ALSA_MIXER", "Headphone,Master,PCM")),
        },
        {
            "id": "hdmi",
            "label": "HDMI",
            "device": hdmi_device,
            "mixer_card": os.getenv("MUSICSTREAMER_HDMI_ALSA_CARD", _alsa_card_from_device(hdmi_device)),
            "mixers": _split_controls(os.getenv("MUSICSTREAMER_HDMI_ALSA_MIXER", "HDMI,PCM,Master")),
        },
    ]


def _split_controls(value: str) -> list[str]:
    return [control.strip() for control in value.split(",") if control.strip()]


def _alsa_card_from_device(device: str) -> str:
    match = re.search(r"(?:^|[:,])CARD=([^,]+)", device)
    return match.group(1) if match else ""


def _read_audio_config() -> dict:
    config_path = AUDIO_CONFIG_FILE if AUDIO_CONFIG_FILE.exists() else LEGACY_AUDIO_CONFIG_FILE

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

    return config if isinstance(config, dict) else {}


def _write_audio_config(config: dict) -> None:
    AUDIO_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with AUDIO_CONFIG_FILE.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)
        config_file.write("\n")


def _find_audio_output(output_id: str | None) -> dict | None:
    for output in _audio_outputs():
        if output["id"] == output_id:
            return output

    return None


def get_audio_output_id() -> str:
    config = _read_audio_config()
    configured = str(config.get("audio_output", "")).strip()

    if _find_audio_output(configured):
        return configured

    default_output = os.getenv("MUSICSTREAMER_AUDIO_OUTPUT", "jack").strip()

    if _find_audio_output(default_output):
        return default_output

    return "jack"


def set_audio_output(output_id: str) -> dict:
    output = _find_audio_output(output_id)

    if output is None:
        raise ValueError("unknown audio output")

    _write_audio_config({"audio_output": output["id"]})
    return output


def get_audio_device() -> str:
    output = _find_audio_output(get_audio_output_id())
    return output["device"] if output else ""


def get_audio_status() -> dict:
    selected_output = get_audio_output_id()

    return {
        "output": selected_output,
        "outputs": [
            {"id": output["id"], "label": output["label"]}
            for output in _audio_outputs()
        ],
    }


def _configured_volume_controls() -> tuple[list[str], str]:
    configured = os.getenv("MUSICSTREAMER_ALSA_MIXER", "").strip()

    if configured:
        return _split_controls(configured), os.getenv("MUSICSTREAMER_ALSA_CARD", "").strip()

    output = _find_audio_output(get_audio_output_id())

    if output is not None and output["mixers"]:
        return output["mixers"], output["mixer_card"]

    return list(VOLUME_CONTROLS), os.getenv("MUSICSTREAMER_ALSA_CARD", "").strip()


def _run_amixer(args: list[str], card: str = "") -> subprocess.CompletedProcess[str]:
    amixer = shutil.which("amixer")

    if amixer is None:
        raise RuntimeError("amixer is not installed")

    command = [amixer, "-M"]

    if card:
        command.extend(["-c", card])

    return subprocess.run(
        [*command, *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _read_control_volume(control: str, card: str = "") -> int | None:
    try:
        result = _run_amixer(["sget", control], card)
    except (RuntimeError, subprocess.CalledProcessError):
        return None

    matches = re.findall(r"\[(\d{1,3})%\]", result.stdout)

    if not matches:
        return None

    return max(0, min(100, int(matches[0])))


def get_volume() -> int:
    controls, card = _configured_volume_controls()

    for control in controls:
        volume = _read_control_volume(control, card)

        if volume is not None:
            return volume

    return DEFAULT_VOLUME


def set_volume(volume: int) -> int:
    clamped_volume = max(0, min(100, int(volume)))
    controls, card = _configured_volume_controls()

    for control in controls:
        try:
            _run_amixer(["sset", control, f"{clamped_volume}%"], card)
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
        "audio": get_audio_status(),
    }
