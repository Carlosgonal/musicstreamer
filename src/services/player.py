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
_UNSET = object()


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
    source: str | None | object = _UNSET,
    state: str | None | object = _UNSET,
    artist: str | None | object = _UNSET,
    title: str | None | object = _UNSET,
    album: str | None | object = _UNSET,
    artwork_url: str | None | object = _UNSET,
) -> dict:
    with _lock:
        if source is not _UNSET:
            _status["source"] = source
        if state is not _UNSET:
            _status["state"] = state
        if artist is not _UNSET:
            _status["artist"] = artist
        if title is not _UNSET:
            _status["title"] = title
        if album is not _UNSET:
            _status["album"] = album
        if artwork_url is not _UNSET:
            _status["artwork_url"] = artwork_url

        return deepcopy(_status)


def reset_player() -> dict:
    with _lock:
        _status.clear()
        _status.update(deepcopy(DEFAULT_PLAYER_STATUS))
        return deepcopy(_status)
