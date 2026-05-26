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

VALID_STATUSES = {"completed", "pending", "cancelled", "shipped", "refunded"}


def clean_orders(
    rows: list[dict],
    valid_customers: set[int],
    valid_products: set[int],
    tracker: RejectionTracker,
) -> list[dict]:
    by_order_id: dict[int, dict] = {}

    for row in rows:
        order_id = parse_int(row.get("order_id", ""))
        customer_id = parse_int(row.get("customer_id", ""))
        product_id = parse_int(row.get("product_id", ""))
        quantity = parse_int(row.get("quantity", ""))
        order_amount = parse_decimal(row.get("order_amount", ""))
        order_date = (row.get("order_date") or "").strip()
        status = (row.get("status") or "").strip().lower()

        if order_id is None:
            tracker.reject(row.get("order_id"), "invalid_order_id", row)
            continue
        if order_id in by_order_id:
            tracker.reject(order_id, "duplicate_order_id", row)
            continue
        if customer_id not in valid_customers:
            tracker.reject(order_id, "invalid_customer_id", row)
            continue
        if product_id not in valid_products:
            tracker.reject(order_id, "invalid_product_id", row)
            continue
        if quantity is None or quantity <= 0:
            tracker.reject(order_id, "invalid_quantity", row)
            continue
        if order_amount is None or order_amount < 0:
            tracker.reject(order_id, "invalid_order_amount", row)
            continue
        if not order_date:
            tracker.reject(order_id, "missing_order_date", row)
            continue
        if status not in VALID_STATUSES:
            tracker.reject(order_id, "invalid_status", row)
            continue

        by_order_id[order_id] = {
            "order_id": order_id,
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "order_amount": order_amount,
            "order_date": order_date,
            "status": status,
            "transform_version": TRANSFORM_VERSION,
        }

    return list(by_order_id.values())


def transform_orders() -> int:
    logger = setup_logging("transform_orders")
    logger.info("START transform_orders v2")
    tracker = RejectionTracker("orders")

    valid_customers = load_valid_ids(SILVER_DB, "silver.customers", "customer_id")
    valid_products = load_valid_ids(SILVER_DB, "silver.products", "product_id")

    with get_connection(BRONZE_DB) as bronze_conn:
        with bronze_conn.cursor() as cur:
            cur.execute("SELECT * FROM bronze.orders_raw")
            columns = [desc[0] for desc in cur.description]
            rows = [row_to_dict(columns, row) for row in cur.fetchall()]

    logger.info("Ucitano %s redova iz bronze.orders_raw", len(rows))
    cleaned_rows = clean_orders(rows, valid_customers, valid_products, tracker)

    insert_sql = """
        INSERT INTO silver.orders (
            order_id, customer_id, product_id, quantity,
            order_amount, order_date, status, transform_version
        )
        VALUES (
            %(order_id)s, %(customer_id)s, %(product_id)s, %(quantity)s,
            %(order_amount)s, %(order_date)s, %(status)s, %(transform_version)s
        )
    """

    with get_connection(SILVER_DB) as silver_conn:
        with silver_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE silver.orders CASCADE")
            cur.executemany(insert_sql, cleaned_rows)
            tracker.flush(silver_conn)
        silver_conn.commit()

    tracker.log_summary(logger, len(rows), len(cleaned_rows))
    logger.info("SUCCESS: ubaceno %s redova u silver.orders", len(cleaned_rows))
    return len(cleaned_rows)


if __name__ == "__main__":
    try:
        transform_orders()
    except Exception:
        logging.getLogger(__name__).exception("ERROR transform_orders")
        sys.exit(1)
