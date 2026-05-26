import logging
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.transform_helpers import (  # noqa: E402
    BRONZE_DB,
    COMPANY_HINT,
    NUMERIC_ONLY,
    SILVER_DB,
    TRANSFORM_VERSION,
    RejectionTracker,
    is_valid_email,
    normalize_country,
    parse_int,
    row_to_dict,
    setup_logging,
)

VALID_TYPES = {"individual", "company"}


def clean_customers(rows: list[dict], tracker: RejectionTracker) -> list[dict]:
    by_email: dict[str, dict] = {}

    for row in rows:
        customer_id = parse_int(row.get("customer_id", ""))
        email = (row.get("email") or "").strip().lower()
        customer_type = (row.get("customer_type") or "individual").strip().lower()
        first_name = (row.get("first_name") or "").strip()
        last_name = (row.get("last_name") or "").strip()

        if customer_id is None:
            tracker.reject(row.get("customer_id"), "invalid_customer_id", row)
            continue
        if not email:
            tracker.reject(customer_id, "missing_email", row)
            continue
        if not is_valid_email(email):
            tracker.reject(customer_id, "invalid_email", row)
            continue
        if customer_type not in VALID_TYPES:
            tracker.reject(customer_id, "invalid_customer_type", row)
            continue

        if customer_type == "company":
            if not first_name:
                tracker.reject(customer_id, "company_missing_name", row)
                continue
        else:
            if not first_name:
                tracker.reject(customer_id, "missing_first_name", row)
                continue
            if NUMERIC_ONLY.match(first_name) or (last_name and NUMERIC_ONLY.match(last_name)):
                tracker.reject(customer_id, "numeric_name_not_company", row)
                continue
            if COMPANY_HINT.search(first_name):
                tracker.reject(customer_id, "company_name_without_legal_flag", row)
                continue

        cleaned = {
            "customer_id": customer_id,
            "customer_type": customer_type,
            "first_name": first_name,
            "last_name": last_name or None,
            "email": email,
            "country": normalize_country(row.get("country", "")),
            "created_at": (row.get("created_at") or "").strip() or None,
            "transform_version": TRANSFORM_VERSION,
        }

        if email not in by_email or customer_id < by_email[email]["customer_id"]:
            by_email[email] = cleaned
        else:
            tracker.reject(customer_id, "duplicate_email", row)

    return list(by_email.values())


def transform_customers() -> int:
    logger = setup_logging("transform_customers")
    logger.info("START transform_customers v2")
    tracker = RejectionTracker("customers")

    with get_connection(BRONZE_DB) as bronze_conn:
        with bronze_conn.cursor() as cur:
            cur.execute("SELECT * FROM bronze.customers_raw")
            columns = [desc[0] for desc in cur.description]
            rows = [row_to_dict(columns, row) for row in cur.fetchall()]

    logger.info("Ucitano %s redova iz bronze.customers_raw", len(rows))
    cleaned_rows = clean_customers(rows, tracker)

    insert_sql = """
        INSERT INTO silver.customers (
            customer_id, customer_type, first_name, last_name,
            email, country, created_at, transform_version
        )
        VALUES (
            %(customer_id)s, %(customer_type)s, %(first_name)s, %(last_name)s,
            %(email)s, %(country)s, %(created_at)s, %(transform_version)s
        )
    """

    with get_connection(SILVER_DB) as silver_conn:
        with silver_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE silver.customers CASCADE")
            cur.executemany(insert_sql, cleaned_rows)
            tracker.flush(silver_conn)
        silver_conn.commit()

    tracker.log_summary(logger, len(rows), len(cleaned_rows))
    logger.info("SUCCESS: ubaceno %s redova u silver.customers", len(cleaned_rows))
    return len(cleaned_rows)


if __name__ == "__main__":
    try:
        transform_customers()
    except Exception:
        logging.getLogger(__name__).exception("ERROR transform_customers")
        sys.exit(1)
