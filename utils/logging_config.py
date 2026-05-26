import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
STRUCTURED_DIR = LOG_DIR / "structured"
METRICS_DIR = LOG_DIR / "metrics"
REPORTS_DIR = BASE_DIR / "reports"

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """Centralni logging: konzola + rotirajuci fajl + JSON linija."""
    LOG_DIR.mkdir(exist_ok=True)
    STRUCTURED_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        LOG_DIR / f"{name}.log",
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def log_structured(event: str, payload: dict, logger_name: str = "structured") -> None:
    """Jedna JSON linija po dogadjaju (lakse parsiranje / monitoring)."""
    STRUCTURED_DIR.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        **payload,
    }
    path = STRUCTURED_DIR / f"{logger_name}.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def save_metrics(metrics: dict) -> Path:
    """Spremi metrike zadnjeg run-a i dodaj u historiju."""
    METRICS_DIR.mkdir(exist_ok=True)
    metrics["saved_at"] = datetime.now().isoformat(timespec="seconds")

    latest = METRICS_DIR / "latest.json"
    latest.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    history = METRICS_DIR / "history.jsonl"
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(metrics, ensure_ascii=False, default=str) + "\n")

    return latest
