from flask import Blueprint, jsonify, request

from services.system import get_system_status, set_audio_output, set_volume


system_api = Blueprint("system_api", __name__)


@system_api.get("/status")
def status():
    return jsonify(get_system_status())


@system_api.post("/volume")
def volume():
    payload = request.get_json(silent=True) or {}

    try:
        requested_volume = int(payload.get("volume"))
    except (TypeError, ValueError):
        return jsonify({"error": "volume must be an integer between 0 and 100"}), 400

    try:
        set_volume(requested_volume)
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503

    return jsonify(get_system_status())


@system_api.post("/audio-output")
def audio_output():
    payload = request.get_json(silent=True) or {}
    output_id = str(payload.get("output", "")).strip()

    try:
        set_audio_output(output_id)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(get_system_status())
