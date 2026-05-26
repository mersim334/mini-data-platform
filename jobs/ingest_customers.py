import csv
import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.logging_config import log_structured, setup_logging  # noqa: E402

DATA_DIR = BASE_DIR / "data"
CSV_FILE = DATA_DIR / "customers.csv"


def ingest_customers() -> int:
    logger = setup_logging("ingest_customers")
    logger.info("START ingest_customers")

    if not CSV_FILE.exists():
        logger.error("CSV fajl nije pronadjen: %s", CSV_FILE)
        raise FileNotFoundError(CSV_FILE)

    with CSV_FILE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    logger.info("Procitano %s redova iz %s", len(rows), CSV_FILE.name)

    insert_sql = """
        INSERT INTO bronze.customers_raw (
            customer_id, first_name, last_name, email, country,
            created_at, customer_type
        )
        VALUES (
            %(customer_id)s, %(first_name)s, %(last_name)s,
            %(email)s, %(country)s, %(created_at)s, %(customer_type)s
        )
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(insert_sql, rows)
        conn.commit()

    logger.info("SUCCESS: ubaceno %s redova u bronze.customers_raw", len(rows))
    log_structured("ingest_success", {"table": "customers_raw", "rows": len(rows)}, "ingest")
    return len(rows)


if __name__ == "__main__":
    try:
        ingest_customers()
    except Exception:
        logging.getLogger(__name__).exception("ERROR ingest_customers")
        sys.exit(1)
