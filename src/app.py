from pathlib import Path
import os

from flask import Flask, send_from_directory

from api.radio import radio_api
from api.spotify import spotify_api
from api.system import system_api


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")

    app.register_blueprint(system_api, url_prefix="/api/system")
    app.register_blueprint(spotify_api, url_prefix="/api/spotify")
    app.register_blueprint(radio_api, url_prefix="/api/radio")

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/admin")
    def admin():
        return send_from_directory(STATIC_DIR, "admin.html")

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("MUSICSTREAMER_HOST", "0.0.0.0")
    port = int(os.getenv("MUSICSTREAMER_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    app.run(host=host, port=port, debug=debug)
