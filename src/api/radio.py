from flask import Blueprint, jsonify, request

from services.radio import get_radio_status, list_stations, play_station, save_station, stop_radio


radio_api = Blueprint("radio_api", __name__)


@radio_api.get("/status")
def status():
    try:
        return jsonify(get_radio_status())
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503


@radio_api.get("/stations")
def stations():
    try:
        return jsonify({"stations": list_stations()})
    except OSError as error:
        return jsonify({"error": str(error)}), 503


@radio_api.post("/stations")
def add_station():
    payload = request.get_json(silent=True) or {}

    try:
        station = save_station(payload)
    except (OSError, ValueError) as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"station": station, "stations": list_stations()})


@radio_api.post("/play")
def play():
    payload = request.get_json(silent=True) or {}

    try:
        return jsonify(play_station(payload.get("station_id")))
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503


@radio_api.post("/stop")
def stop():
    try:
        return jsonify(stop_radio())
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503
