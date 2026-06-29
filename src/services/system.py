from datetime import datetime
import os


def get_runtime_status() -> str:
    if os.getenv("FLASK_DEBUG", "0") == "1" or os.getenv("FLASK_ENV") == "development":
        return "Development mode"

    return "Ready"


def get_system_status() -> dict:
    now = datetime.now()

    return {
        "project": "MusicStreamer",
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "status": get_runtime_status(),
        "network": "Local",
        "volume": 50,
    }
