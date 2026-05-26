import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.transform_helpers import (  # noqa: E402
    BRONZE_DB,
    SILVER_DB,
    TRANSFORM_VERSION,
    RejectionTracker,
    load_valid_ids,
    parse_decimal,
    parse_int,
    row_to_dict,
    setup_logging,
)

VALID_STATUSES = {"success", "failed", "pending", "refunded"}


def clean_payments(
    rows: list[dict],
    valid_orders: set[int],
    tracker: RejectionTracker,
) -> list[dict]:
    by_payment_id: dict[int, dict] = {}

    for row in rows:
        payment_id = parse_int(row.get("payment_id", ""))
        order_id = parse_int(row.get("order_id", ""))
        amount = parse_decimal(row.get("amount", ""))
        payment_method = (row.get("payment_method") or "").strip()
        payment_date = (row.get("payment_date") or "").strip()
        status = (row.get("status") or "").strip().lower()

        if payment_id is None:
            tracker.reject(row.get("payment_id"), "invalid_payment_id", row)
            continue
        if payment_id in by_payment_id:
            tracker.reject(payment_id, "duplicate_payment_id", row)
            continue
        if order_id not in valid_orders:
            tracker.reject(payment_id, "invalid_order_id", row)
            continue
        if amount is None or amount < 0:
            tracker.reject(payment_id, "invalid_amount", row)
            continue
        if not payment_method:
            tracker.reject(payment_id, "missing_payment_method", row)
            continue
        if not payment_date:
            tracker.reject(payment_id, "missing_payment_date", row)
            continue
        if status not in VALID_STATUSES:
            tracker.reject(payment_id, "invalid_status", row)
            continue

        by_payment_id[payment_id] = {
            "payment_id": payment_id,
            "order_id": order_id,
            "payment_method": payment_method,
            "amount": amount,
            "payment_date": payment_date,
            "status": status,
            "transform_version": TRANSFORM_VERSION,
        }

    return list(by_payment_id.values())


def transform_payments() -> int:
    logger = setup_logging("transform_payments")
    logger.info("START transform_payments v2")
    tracker = RejectionTracker("payments")

    valid_orders = load_valid_ids(SILVER_DB, "silver.orders", "order_id")

    with get_connection(BRONZE_DB) as bronze_conn:
        with bronze_conn.cursor() as cur:
            cur.execute("SELECT * FROM bronze.payments_raw")
            columns = [desc[0] for desc in cur.description]
            rows = [row_to_dict(columns, row) for row in cur.fetchall()]

    logger.info("Ucitano %s redova iz bronze.payments_raw", len(rows))
    cleaned_rows = clean_payments(rows, valid_orders, tracker)

    insert_sql = """
        INSERT INTO silver.payments (
            payment_id, order_id, payment_method, amount,
            payment_date, status, transform_version
        )
        VALUES (
            %(payment_id)s, %(order_id)s, %(payment_method)s, %(amount)s,
            %(payment_date)s, %(status)s, %(transform_version)s
        )
    """

    with get_connection(SILVER_DB) as silver_conn:
        with silver_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE silver.payments")
            cur.executemany(insert_sql, cleaned_rows)
            tracker.flush(silver_conn)
        silver_conn.commit()

    tracker.log_summary(logger, len(rows), len(cleaned_rows))
    logger.info("SUCCESS: ubaceno %s redova u silver.payments", len(cleaned_rows))
    return len(cleaned_rows)


if __name__ == "__main__":
    try:
        transform_payments()
    except Exception:
        logging.getLogger(__name__).exception("ERROR transform_payments")
        sys.exit(1)
