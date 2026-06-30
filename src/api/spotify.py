from flask import Blueprint, jsonify, redirect, request

from services.spotify import (
    control_playback,
    get_admin_settings,
    get_authorize_url,
    get_spotify_status,
    handle_oauth_callback,
    save_admin_settings,
    start_spotify,
    stop_spotify,
)


spotify_api = Blueprint("spotify_api", __name__)


@spotify_api.get("/status")
def status():
    return jsonify(get_spotify_status())


@spotify_api.post("/start")
def start():
    return jsonify(start_spotify())


@spotify_api.post("/stop")
def stop():
    return jsonify(stop_spotify())


@spotify_api.get("/login")
def login():
    try:
        return redirect(get_authorize_url())
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 400


@spotify_api.get("/callback")
def callback():
    error = request.args.get("error")

    if error:
        return f"Spotify authorization failed: {error}", 400

    try:
        handle_oauth_callback(
            request.args.get("code", ""),
            request.args.get("state", ""),
        )
    except Exception as error:
        return f"Spotify authorization failed: {error}", 400

    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Spotify linked</title>
  <link rel="stylesheet" href="/web/css/app.css">
  <link rel="stylesheet" href="/web/css/admin.css">
</head>
<body>
  <main class="admin-shell">
    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="section-label">Spotify</p>
          <h1>Account linked</h1>
        </div>
        <span class="pill">linked</span>
      </div>
      <div class="actions">
        <a class="button primary" href="/">Back to streamer</a>
        <a class="button" href="/admin">Back to admin</a>
      </div>
    </section>
  </main>
</body>
</html>
"""


@spotify_api.post("/control/<action>")
def control(action: str):
    try:
        return jsonify(control_playback(action))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"error": str(error)}), 503


@spotify_api.get("/settings")
def settings():
    return jsonify(get_admin_settings())


@spotify_api.post("/settings")
def save_settings():
    payload = request.get_json(silent=True) or {}

    try:
        settings = save_admin_settings(payload)
    except (OSError, ValueError) as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(settings)
