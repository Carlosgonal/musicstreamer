from flask import Blueprint, jsonify, request

from services.system import get_audio_status, get_system_status, get_volume, set_audio_output, set_volume
from services.spotify import set_spotify_volume


system_api = Blueprint("system_api", __name__)


@system_api.get("/", strict_slashes=False)
def status():
    return jsonify(get_system_status())


@system_api.get("/audio-output")
def audio_output_status():
    return jsonify(get_audio_status())


@system_api.post("/audio-output")
def audio_output_update():
    payload = request.get_json(silent=True) or {}
    output = str(payload.get("output", "")).strip()
    return jsonify(set_audio_output(output))


@system_api.get("/volume")
def volume_status():
    return jsonify({"volume": get_volume()})


@system_api.post("/volume")
def volume_update():
    payload = request.get_json(silent=True) or {}
    try:
        volume = int(payload.get("volume", 50))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid volume"}), 400

    system_volume = set_volume(volume)
    spotify_status = set_spotify_volume(system_volume)
    return jsonify({
        "volume": system_volume,
        "spotify": {
            "state": spotify_status.get("state"),
            "error": spotify_status.get("error"),
        },
    })
