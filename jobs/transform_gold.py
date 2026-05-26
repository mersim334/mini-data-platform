import logging
import sys
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.transform_helpers import SILVER_DB, setup_logging  # noqa: E402

GOLD_DB = "ecommerce_gold"
TRANSFORM_VERSION = "v1"


def setup_gold_schema() -> None:
    sql_path = BASE_DIR / "sql" / "gold_setup.sql"
    sql = sql_path.read_text(encoding="utf-8")
    with get_connection(GOLD_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def build_daily_sales_kpi(logger: logging.Logger) -> int:
    query = """
        SELECT
            order_date,
            COUNT(*) AS total_orders,
            SUM(order_amount) AS revenue,
            AVG(order_amount) AS average_order_value
        FROM silver.orders
        GROUP BY order_date
        ORDER BY order_date
    """

    with get_connection(SILVER_DB) as silver_conn:
        with silver_conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    insert_sql = """
        INSERT INTO gold.daily_sales_kpi (
            order_date, total_orders, revenue,
            average_order_value, transform_version
        )
        VALUES (%s, %s, %s, %s, %s)
    """

    payload = [
        (
            row[0],
            row[1],
            row[2],
            round(Decimal(row[3]), 2),
            TRANSFORM_VERSION,
        )
        for row in rows
    ]

    with get_connection(GOLD_DB) as gold_conn:
        with gold_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE gold.daily_sales_kpi")
            cur.executemany(insert_sql, payload)
        gold_conn.commit()

    logger.info("daily_sales_kpi: ubaceno %s redova", len(payload))
    return len(payload)


def build_customer_kpi(logger: logging.Logger) -> int:
    query = """
        SELECT
            customer_id,
            COUNT(*) AS total_orders,
            SUM(order_amount) AS total_spent,
            MAX(order_date) AS last_order_date
        FROM silver.orders
        GROUP BY customer_id
        ORDER BY customer_id
    """

    with get_connection(SILVER_DB) as silver_conn:
        with silver_conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    insert_sql = """
        INSERT INTO gold.customer_kpi (
            customer_id, total_orders, total_spent,
            last_order_date, transform_version
        )
        VALUES (%s, %s, %s, %s, %s)
    """

    payload = [
        (row[0], row[1], row[2], row[3], TRANSFORM_VERSION) for row in rows
    ]

    with get_connection(GOLD_DB) as gold_conn:
        with gold_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE gold.customer_kpi")
            cur.executemany(insert_sql, payload)
        gold_conn.commit()

    logger.info("customer_kpi: ubaceno %s redova", len(payload))
    return len(payload)


def transform_gold() -> None:
    logger = setup_logging("transform_gold")
    logger.info("START transform_gold")

    setup_gold_schema()
    daily_rows = build_daily_sales_kpi(logger)
    customer_rows = build_customer_kpi(logger)

    logger.info(
        "SUCCESS gold layer: daily_sales_kpi=%s, customer_kpi=%s",
        daily_rows,
        customer_rows,
    )


if __name__ == "__main__":
    try:
        transform_gold()
    except Exception:
        logging.getLogger(__name__).exception("ERROR transform_gold")
        sys.exit(1)
