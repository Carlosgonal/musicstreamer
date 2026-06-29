DEFAULT_STATIONS = [
    {
        "id": "ambient",
        "name": "Ambient Radio",
        "url": "",
    },
    {
        "id": "jazz",
        "name": "Jazz Radio",
        "url": "",
    },
]


def get_radio_status() -> dict:
    return {
        "available": True,
        "service": "Internet Radio",
        "state": "standby",
        "label": "Radio Ready",
    }


def list_stations() -> list[dict]:
    return DEFAULT_STATIONS
