#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime


PROJECT_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_DIR / "src" / "static"
RADIO_CONFIG_FILE = PROJECT_DIR / "config" / "radio.json"

state = {
    "volume": 50,
    "audio_output": "jack",
    "radio_state": "standby",
    "selected_station_id": "",
    "spotify_state": "auth",
}


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or 0)

    if length <= 0:
        return {}

    try:
        return json.loads(handler.rfile.read(length).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def radio_stations() -> list[dict]:
    try:
        with RADIO_CONFIG_FILE.open("r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}

    stations = data.get("stations", [])
    return stations if isinstance(stations, list) else []


def selected_station() -> dict | None:
    stations = radio_stations()

    if not stations:
        return None

    if not state["selected_station_id"]:
        state["selected_station_id"] = stations[0].get("id", "")

    for station in stations:
        if station.get("id") == state["selected_station_id"]:
            return station

    return stations[0]


def system_status() -> dict:
    now = datetime.now()

    return {
        "project": "MusicStreamer Dev",
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "status": "Frontend dev",
        "network": "Mock",
        "volume": state["volume"],
        "audio": {
            "output": state["audio_output"],
            "outputs": [
                {"id": "jack", "label": "Jack"},
                {"id": "hdmi", "label": "HDMI"},
            ],
        },
    }


def radio_status() -> dict:
    station = selected_station()
    label = "Playing" if state["radio_state"] == "playing" else "Ready"

    return {
        "state": state["radio_state"],
        "label": label,
        "error": "",
        "station": station,
    }


def spotify_status() -> dict:
    authenticated = state["spotify_state"] != "auth"
    playing = state["spotify_state"] == "playing"

    return {
        "available": True,
        "service": "Spotify Connect",
        "state": state["spotify_state"],
        "label": "On" if playing else ("Link account" if not authenticated else "Ready"),
        "error": None,
        "device_name": "MusicStreamer Dev",
        "authenticated": authenticated,
        "credentials_configured": True,
        "controls_available": authenticated,
        "player": {
            "is_playing": playing,
            "progress_ms": 58000,
            "duration_ms": 214000,
            "track": "Mock track",
            "artist": "Frontend dev",
            "album": "Local preview",
            "image": "",
        } if authenticated else None,
        "admin": {
            "enabled": True,
            "device_name": "MusicStreamer Dev",
            "bitrate": "320",
            "cache_dir": "",
            "client_id": "mock-client-id",
            "client_secret_set": True,
            "redirect_uri": "http://127.0.0.1:8080/api/spotify/callback",
            "linked": authenticated,
        },
    }


class FrontDevHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_json(self, payload: dict | list, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text: str, status: int = 200) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static(self, path: str) -> None:
        self._serve_static(path, include_body=True)

    def serve_static_head(self, path: str) -> None:
        self._serve_static(path, include_body=False)

    def _serve_static(self, path: str, include_body: bool) -> None:
        if path == "/":
            file_path = STATIC_DIR / "index.html"
        elif path == "/admin":
            file_path = STATIC_DIR / "admin.html"
        elif path.startswith("/static/"):
            file_path = STATIC_DIR / path.removeprefix("/static/")
        else:
            self.send_error(404)
            return

        try:
            resolved = file_path.resolve()
            resolved.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(403)
            return

        if not resolved.is_file():
            self.send_error(404)
            return

        body = resolved.read_bytes()
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        self.serve_static_head(path)

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/system/status":
            self.send_json(system_status())
        elif path == "/api/radio/status":
            self.send_json(radio_status())
        elif path == "/api/radio/stations":
            self.send_json({"stations": radio_stations()})
        elif path == "/api/spotify/status":
            self.send_json(spotify_status())
        elif path == "/api/spotify/settings":
            self.send_json(spotify_status()["admin"])
        elif path == "/api/spotify/login":
            state["spotify_state"] = "standby"
            self.send_text("<p>Mock Spotify linked. Return to MusicStreamer.</p>")
        else:
            self.serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        payload = read_json_body(self)

        if path == "/api/system/volume":
            state["volume"] = max(0, min(100, int(payload.get("volume", state["volume"]))))
            self.send_json(system_status())
        elif path == "/api/system/audio-output":
            output = str(payload.get("output", "jack"))
            state["audio_output"] = output if output in {"jack", "hdmi"} else "jack"
            self.send_json(system_status())
        elif path == "/api/radio/play":
            station_id = str(payload.get("station_id", ""))
            if station_id:
                state["selected_station_id"] = station_id
            state["radio_state"] = "playing"
            self.send_json(radio_status())
        elif path == "/api/radio/stop":
            state["radio_state"] = "standby"
            self.send_json(radio_status())
        elif path == "/api/radio/stations":
            self.send_json({"stations": radio_stations(), "station": selected_station()})
        elif path == "/api/spotify/start":
            state["spotify_state"] = "playing"
            self.send_json(spotify_status())
        elif path == "/api/spotify/stop":
            state["spotify_state"] = "standby"
            self.send_json(spotify_status())
        elif path.startswith("/api/spotify/control/"):
            state["spotify_state"] = "playing"
            self.send_json(spotify_status())
        elif path == "/api/spotify/settings":
            self.send_json(spotify_status()["admin"])
        else:
            self.send_error(404)


def main() -> None:
    host = os.getenv("MUSICSTREAMER_FRONT_DEV_HOST", "127.0.0.1")
    port = int(os.getenv("MUSICSTREAMER_FRONT_DEV_PORT", "49173"))
    server = ThreadingHTTPServer((host, port), FrontDevHandler)
    print(f"Frontend dev server: http://{host}:{port}")
    print("Serving static UI with mocked API responses.")
    server.serve_forever()


if __name__ == "__main__":
    main()
