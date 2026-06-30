from flask import Blueprint, jsonify

from services.player import get_player_status


player_api = Blueprint("player_api", __name__)


@player_api.get("/", strict_slashes=False)
def status():
    return jsonify(get_player_status())
