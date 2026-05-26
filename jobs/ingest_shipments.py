import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.logging_config import log_structured, setup_logging  # noqa: E402

DATA_DIR = BASE_DIR / "data"
CSV_FILE = DATA_DIR / "shipments.csv"


def ingest_shipments() -> int:
    logger = setup_logging("ingest_shipments")
    logger.info("START ingest_shipments")

    if not CSV_FILE.exists():
        logger.error("CSV fajl nije pronadjen: %s", CSV_FILE)
        raise FileNotFoundError(CSV_FILE)

    with CSV_FILE.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    logger.info("Procitano %s redova iz %s", len(rows), CSV_FILE.name)

    insert_sql = """
        INSERT INTO bronze.shipments_raw (
            shipment_id, order_id, carrier, tracking_number,
            ship_date, delivery_date, status
        )
        VALUES (
            %(shipment_id)s, %(order_id)s, %(carrier)s, %(tracking_number)s,
            %(ship_date)s, %(delivery_date)s, %(status)s
        )
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(insert_sql, rows)
        conn.commit()

    logger.info("SUCCESS: ubaceno %s redova u bronze.shipments_raw", len(rows))
    log_structured("ingest_success", {"table": "shipments_raw", "rows": len(rows)}, "ingest")
    return len(rows)


if __name__ == "__main__":
    try:
        ingest_shipments()
    except Exception:
        logging.getLogger(__name__).exception("ERROR ingest_shipments")
        sys.exit(1)
