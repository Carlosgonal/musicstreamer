import os
import sys
from pathlib import Path

from flask import Flask, Response

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from api.player import player_api
from api.logs import logs_api
from api.spotify import spotify_api
from api.radio import radio_api
from api.system import system_api
from services.logging import configure_logging


WEB_DIR = BASE_DIR.parent / "web"


def _asset_version() -> str:
    candidates = [
        WEB_DIR / "css" / "app.css",
        WEB_DIR / "css" / "admin.css",
        WEB_DIR / "js" / "app.js",
        WEB_DIR / "js" / "admin.js",
    ]
    stamp = max((path.stat().st_mtime_ns for path in candidates if path.exists()), default=0)
    return str(stamp)


def _serve_html(filename: str) -> Response:
    html = (WEB_DIR / filename).read_text(encoding="utf-8")
    html = html.replace("__ASSET_VERSION__", _asset_version())
    response = Response(html, content_type="text/html; charset=utf-8")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="/web")
    configure_logging(app.logger)
    app.logger.info("MusicStreamer app initialized")

    app.register_blueprint(player_api, url_prefix="/api/player")
    app.register_blueprint(logs_api, url_prefix="/api/logs")
    app.register_blueprint(system_api, url_prefix="/api/system")
    app.register_blueprint(radio_api, url_prefix="/api/radio")
    app.register_blueprint(spotify_api, url_prefix="/api/spotify")

    @app.get("/")
    def index():
        return _serve_html("index.html")

    @app.get("/admin", strict_slashes=False)
    def admin():
        return _serve_html("admin.html")

    return app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("MUSICSTREAMER_HOST", "0.0.0.0")
    port = int(os.getenv("MUSICSTREAMER_PORT", "8080"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    app.logger.info("Starting MusicStreamer on %s:%s", host, port)

    app.run(host=host, port=port, debug=debug)
