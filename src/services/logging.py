import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_DIR / "var" / "log"
LOG_FILE = LOG_DIR / "musicstreamer.log"


def configure_logging(app: logging.Logger) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", "") == str(LOG_FILE) for handler in root_logger.handlers):
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

    if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)
        root_logger.addHandler(stream_handler)

    app.setLevel(logging.INFO)
    app.handlers.clear()

    for handler in root_logger.handlers:
        app.addHandler(handler)


def tail_log_lines(limit: int = 200, query: str = "") -> list[str]:
    if not LOG_FILE.exists():
        return []

    try:
        with LOG_FILE.open("r", encoding="utf-8") as log_file:
            lines = log_file.readlines()
    except OSError:
        return []

    normalized_query = query.strip().lower()
    if normalized_query:
        lines = [line for line in lines if normalized_query in line.lower()]

    if limit <= 0:
        return []

    return [line.rstrip("\n") for line in lines[-limit:]]
