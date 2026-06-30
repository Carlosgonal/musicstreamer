import os
import sys
from pathlib import Path

from flask import Flask, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from api.player import player_api
from api.spotify import spotify_api
from api.radio import radio_api
from api.system import system_api


WEB_DIR = BASE_DIR.parent / "web"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/web")

    app.register_blueprint(player_api, url_prefix="/api/player")
    app.register_blueprint(system_api, url_prefix="/api/system")
    app.register_blueprint(radio_api, url_prefix="/api/radio")
    app.register_blueprint(spotify_api, url_prefix="/api/spotify")

    @app.get("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/admin", strict_slashes=False)
    def admin():
        return send_from_directory(WEB_DIR, "admin.html")

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("MUSICSTREAMER_HOST", "0.0.0.0")
    port = int(os.getenv("MUSICSTREAMER_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    app.run(host=host, port=port, debug=debug)
