from flask import Blueprint, jsonify

from services.radio import get_radio_status, list_stations


radio_api = Blueprint("radio_api", __name__)


@radio_api.get("/status")
def status():
    return jsonify(get_radio_status())


@radio_api.get("/stations")
def stations():
    return jsonify({"stations": list_stations()})
