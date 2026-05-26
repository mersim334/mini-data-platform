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
    parse_int,
    row_to_dict,
    setup_logging,
)

VALID_STATUSES = {"delivered", "in_transit", "returned", "pending", "cancelled"}


def clean_shipments(
    rows: list[dict],
    valid_orders: set[int],
    tracker: RejectionTracker,
) -> list[dict]:
    by_shipment_id: dict[int, dict] = {}

    for row in rows:
        shipment_id = parse_int(row.get("shipment_id", ""))
        order_id = parse_int(row.get("order_id", ""))
        carrier = (row.get("carrier") or "").strip()
        tracking_number = (row.get("tracking_number") or "").strip()
        ship_date = (row.get("ship_date") or "").strip()
        delivery_date = (row.get("delivery_date") or "").strip()
        status = (row.get("status") or "").strip().lower()

        if shipment_id is None:
            tracker.reject(row.get("shipment_id"), "invalid_shipment_id", row)
            continue
        if shipment_id in by_shipment_id:
            tracker.reject(shipment_id, "duplicate_shipment_id", row)
            continue
        if order_id not in valid_orders:
            tracker.reject(shipment_id, "invalid_order_id", row)
            continue
        if not carrier:
            tracker.reject(shipment_id, "missing_carrier", row)
            continue
        if not ship_date:
            tracker.reject(shipment_id, "missing_ship_date", row)
            continue
        if status not in VALID_STATUSES:
            tracker.reject(shipment_id, "invalid_status", row)
            continue
        if status == "delivered" and not tracking_number:
            tracker.reject(shipment_id, "missing_tracking_for_delivered", row)
            continue
        if delivery_date and delivery_date < ship_date:
            tracker.reject(shipment_id, "delivery_before_ship", row)
            continue

        by_shipment_id[shipment_id] = {
            "shipment_id": shipment_id,
            "order_id": order_id,
            "carrier": carrier,
            "tracking_number": tracking_number or None,
            "ship_date": ship_date,
            "delivery_date": delivery_date or None,
            "status": status,
            "transform_version": TRANSFORM_VERSION,
        }

    return list(by_shipment_id.values())


def transform_shipments() -> int:
    logger = setup_logging("transform_shipments")
    logger.info("START transform_shipments v2")
    tracker = RejectionTracker("shipments")

    valid_orders = load_valid_ids(SILVER_DB, "silver.orders", "order_id")

    with get_connection(BRONZE_DB) as bronze_conn:
        with bronze_conn.cursor() as cur:
            cur.execute("SELECT * FROM bronze.shipments_raw")
            columns = [desc[0] for desc in cur.description]
            rows = [row_to_dict(columns, row) for row in cur.fetchall()]

    logger.info("Ucitano %s redova iz bronze.shipments_raw", len(rows))
    cleaned_rows = clean_shipments(rows, valid_orders, tracker)

    insert_sql = """
        INSERT INTO silver.shipments (
            shipment_id, order_id, carrier, tracking_number,
            ship_date, delivery_date, status, transform_version
        )
        VALUES (
            %(shipment_id)s, %(order_id)s, %(carrier)s, %(tracking_number)s,
            %(ship_date)s, %(delivery_date)s, %(status)s, %(transform_version)s
        )
    """

    with get_connection(SILVER_DB) as silver_conn:
        with silver_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE silver.shipments")
            cur.executemany(insert_sql, cleaned_rows)
            tracker.flush(silver_conn)
        silver_conn.commit()

    tracker.log_summary(logger, len(rows), len(cleaned_rows))
    logger.info("SUCCESS: ubaceno %s redova u silver.shipments", len(cleaned_rows))
    return len(cleaned_rows)


if __name__ == "__main__":
    try:
        transform_shipments()
    except Exception:
        logging.getLogger(__name__).exception("ERROR transform_shipments")
        sys.exit(1)
