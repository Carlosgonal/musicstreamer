from flask import Blueprint, jsonify, request

from services.player import get_player_status
from services.radio import get_radio_status, play_station, stop_radio
from services.spotify import get_spotify_status, start_spotify, stop_spotify
from services.player import set_state


player_api = Blueprint("player_api", __name__)


@player_api.get("/", strict_slashes=False)
def status():
    return jsonify(get_player_status())


@player_api.post("/source")
def source():
    payload = request.get_json(silent=True) or {}
    source = str(payload.get("source", "")).strip().lower()
    station_id = str(payload.get("station_id", "")).strip() or None

    if source == "spotify":
        stop_radio()
        spotify_status = start_spotify()
        if not spotify_status.get("player"):
            set_state(source="spotify", state="idle", title="Spotify Ready", album=None, artist=None, artwork_url=None)
        return jsonify({
            "player": get_player_status(),
            "spotify": spotify_status if spotify_status else get_spotify_status(),
            "radio": get_radio_status(),
        })

    if source == "radio":
        stop_spotify()
        radio_status = play_station(station_id)
        return jsonify({
            "player": get_player_status(),
            "radio": radio_status,
            "spotify": get_spotify_status(),
        })

    return jsonify({"error": "unknown source"}), 400
