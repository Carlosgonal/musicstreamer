from flask import Blueprint, jsonify, request

from services.player import get_player_status
from services.radio import get_radio_status, play_station, stop_radio
from services.spotify import get_spotify_status
from services.player import set_state
from services.spotify import stop_spotify


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
        spotify_status = get_spotify_status()
        spotify_player = spotify_status.get("player") or {}
        set_state(
            source="spotify",
            state="playing" if spotify_player.get("is_playing") else "idle",
            title=spotify_player.get("track") or "Spotify Ready",
            album=spotify_player.get("album"),
            artist=spotify_player.get("artist"),
            artwork_url=spotify_player.get("image"),
        )
        return jsonify({
            "player": get_player_status(),
            "spotify": spotify_status if spotify_status else get_spotify_status(),
            "radio": get_radio_status(),
        })

    if source == "radio":
        stop_spotify()
        try:
            radio_status = play_station(station_id)
        except RuntimeError as error:
            return jsonify({"error": str(error)}), 503
        current_station = radio_status.get("current_station") or {}
        set_state(
            source="radio",
            state="playing" if radio_status.get("state") == "playing" else "idle",
            title=current_station.get("name") or "Radio Ready",
            album="Internet Radio" if current_station else None,
            artist=current_station.get("frequency") or current_station.get("url"),
            artwork_url=None,
        )
        return jsonify({
            "player": get_player_status(),
            "radio": radio_status,
            "spotify": get_spotify_status(),
        })

    return jsonify({"error": "unknown source"}), 400
