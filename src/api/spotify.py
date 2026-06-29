from flask import Blueprint, jsonify

from services.spotify import get_spotify_status


spotify_api = Blueprint("spotify_api", __name__)


@spotify_api.get("/status")
def status():
    return jsonify(get_spotify_status())
