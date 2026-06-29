from flask import Blueprint, jsonify, request

from services.radio import get_radio_status, list_stations, play_station, save_station, stop_radio


radio_api = Blueprint("radio_api", __name__)


@radio_api.get("/status")
def status():
    return jsonify(get_radio_status())


@radio_api.get("/stations")
def stations():
    return jsonify({"stations": list_stations()})


@radio_api.post("/stations")
def add_station():
    payload = request.get_json(silent=True) or {}

    try:
        station = save_station(payload)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify({"station": station, "stations": list_stations()})


@radio_api.post("/play")
def play():
    payload = request.get_json(silent=True) or {}
    return jsonify(play_station(payload.get("station_id")))


@radio_api.post("/stop")
def stop():
    return jsonify(stop_radio())
