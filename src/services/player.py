from copy import deepcopy
from threading import Lock

from services.system import get_volume as get_system_volume, set_volume as set_system_volume


DEFAULT_PLAYER_STATUS = {
    "source": "spotify",
    "state": "idle",
    "artist": None,
    "title": "Spotify Ready",
    "album": None,
    "volume": 50,
    "artwork_url": None,
}

_lock = Lock()
_status = deepcopy(DEFAULT_PLAYER_STATUS)


def get_player_status() -> dict:
    with _lock:
        _status["volume"] = get_system_volume()
        return deepcopy(_status)


def set_volume(volume: int) -> dict:
    with _lock:
        _status["volume"] = set_system_volume(volume)
        return deepcopy(_status)


def set_state(
    *,
    source: str | None = None,
    state: str | None = None,
    artist: str | None = None,
    title: str | None = None,
    album: str | None = None,
    artwork_url: str | None = None,
) -> dict:
    with _lock:
        if source is not None:
            _status["source"] = source
        if state is not None:
            _status["state"] = state
        if artist is not None:
            _status["artist"] = artist
        if title is not None:
            _status["title"] = title
        if album is not None:
            _status["album"] = album
        if artwork_url is not None:
            _status["artwork_url"] = artwork_url

        return deepcopy(_status)


def reset_player() -> dict:
    with _lock:
        _status.clear()
        _status.update(deepcopy(DEFAULT_PLAYER_STATUS))
        return deepcopy(_status)
