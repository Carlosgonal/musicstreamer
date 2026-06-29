from datetime import datetime


def get_system_status() -> dict:
    now = datetime.now()

    return {
        "project": "MusicStreamer",
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "status": "Development mode",
        "network": "Local",
        "volume": 50,
    }
