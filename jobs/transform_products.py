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
    parse_decimal,
    parse_int,
    row_to_dict,
    setup_logging,
)


def clean_products(rows: list[dict], tracker: RejectionTracker) -> list[dict]:
    by_product_id: dict[int, dict] = {}

    for row in rows:
        product_id = parse_int(row.get("product_id", ""))
        product_name = (row.get("product_name") or "").strip()
        price = parse_decimal(row.get("price", ""))

        if product_id is None:
            tracker.reject(row.get("product_id"), "invalid_product_id", row)
            continue
        if not product_name:
            tracker.reject(product_id, "missing_product_name", row)
            continue
        if price is None or price <= 0:
            tracker.reject(product_id, "invalid_price", row)
            continue

        category = (row.get("category") or "").strip() or "Nepoznato"
        cleaned = {
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "price": price,
            "created_at": (row.get("created_at") or "").strip() or None,
            "transform_version": TRANSFORM_VERSION,
        }

        if product_id in by_product_id:
            tracker.reject(product_id, "duplicate_product_id", row)
            continue

        by_product_id[product_id] = cleaned

    return list(by_product_id.values())


def transform_products() -> int:
    logger = setup_logging("transform_products")
    logger.info("START transform_products v2")
    tracker = RejectionTracker("products")

    with get_connection(BRONZE_DB) as bronze_conn:
        with bronze_conn.cursor() as cur:
            cur.execute("SELECT * FROM bronze.products_raw")
            columns = [desc[0] for desc in cur.description]
            rows = [row_to_dict(columns, row) for row in cur.fetchall()]

    logger.info("Ucitano %s redova iz bronze.products_raw", len(rows))
    cleaned_rows = clean_products(rows, tracker)

    insert_sql = """
        INSERT INTO silver.products (
            product_id, product_name, category, price,
            created_at, transform_version
        )
        VALUES (
            %(product_id)s, %(product_name)s, %(category)s, %(price)s,
            %(created_at)s, %(transform_version)s
        )
    """

    with get_connection(SILVER_DB) as silver_conn:
        with silver_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE silver.products CASCADE")
            cur.executemany(insert_sql, cleaned_rows)
            tracker.flush(silver_conn)
        silver_conn.commit()

    tracker.log_summary(logger, len(rows), len(cleaned_rows))
    logger.info("SUCCESS: ubaceno %s redova u silver.products", len(cleaned_rows))
    return len(cleaned_rows)


if __name__ == "__main__":
    try:
        transform_products()
    except Exception:
        logging.getLogger(__name__).exception("ERROR transform_products")
        sys.exit(1)
