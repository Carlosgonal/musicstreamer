from flask import Blueprint, jsonify

from services.system import get_system_status


system_api = Blueprint("system_api", __name__)


@system_api.get("/", strict_slashes=False)
def status():
    return jsonify(get_system_status())
