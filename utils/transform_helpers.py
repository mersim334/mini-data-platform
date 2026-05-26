import logging
import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from psycopg2.extras import Json

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
BRONZE_DB = "ecommerce_bronze"
SILVER_DB = "ecommerce_silver"
TRANSFORM_VERSION = "v2"

NUMERIC_ONLY = re.compile(r"^\d+$")
COMPANY_HINT = re.compile(r"\b(d\.?o\.?o\.?|d\.?d\.?|j\.?d\.?o\.?|a\.?d\.?)\b", re.I)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

COUNTRY_MAP = {
    "bih": "Bosna i Hercegovina",
    "ba": "Bosna i Hercegovina",
}


def setup_logging(name: str) -> logging.Logger:
    from utils.logging_config import setup_logging as _setup

    return _setup(name)


def parse_decimal(value: str) -> Decimal | None:
    try:
        return Decimal((value or "").strip())
    except InvalidOperation:
        return None


def parse_int(value: str) -> int | None:
    try:
        return int((value or "").strip())
    except ValueError:
        return None


def normalize_country(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return "Nepoznato"
    return COUNTRY_MAP.get(cleaned.lower(), cleaned)


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))


class RejectionTracker:
    def __init__(self, source_table: str):
        self.source_table = source_table
        self.records: list[dict] = []
        self.counts: Counter = Counter()

    def reject(self, source_id: str | int | None, reason: str, raw_row: dict) -> None:
        self.counts[reason] += 1
        self.records.append(
            {
                "source_table": self.source_table,
                "source_id": str(source_id) if source_id is not None else None,
                "reject_reason": reason,
                "raw_data": Json(raw_row),
            }
        )

    def flush(self, conn) -> None:
        if not self.records:
            return
        sql = """
            INSERT INTO silver.rejected_records (
                source_table, source_id, reject_reason, raw_data
            )
            VALUES (
                %(source_table)s, %(source_id)s, %(reject_reason)s, %(raw_data)s
            )
        """
        with conn.cursor() as cur:
            cur.executemany(sql, self.records)

    def log_summary(self, logger: logging.Logger, loaded: int, accepted: int) -> None:
        rejected = loaded - accepted
        logger.info(
            "Sažetak %s: ucitano=%s | prihvaceno=%s | odbijeno=%s",
            self.source_table,
            loaded,
            accepted,
            rejected,
        )
        for reason, count in sorted(self.counts.items()):
            logger.info("  - %s: %s", reason, count)

        from utils.logging_config import log_structured

        log_structured(
            "transform_summary",
            {
                "source_table": self.source_table,
                "loaded": loaded,
                "accepted": accepted,
                "rejected": rejected,
                "reasons": dict(self.counts),
            },
            "transform",
        )


def load_valid_ids(dbname: str, table: str, column: str) -> set[int]:
    from utils.db import get_connection

    with get_connection(dbname) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {column} FROM {table}")
            return {row[0] for row in cur.fetchall()}


def row_to_dict(columns: list[str], row: tuple) -> dict:
    return dict(zip(columns, row))
