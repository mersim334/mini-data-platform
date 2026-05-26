import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from jobs.transform_customers import transform_customers  # noqa: E402
from jobs.transform_orders import transform_orders  # noqa: E402
from jobs.transform_payments import transform_payments  # noqa: E402
from jobs.transform_products import transform_products  # noqa: E402
from jobs.transform_shipments import transform_shipments  # noqa: E402
from utils.db import get_connection  # noqa: E402
from utils.transform_helpers import setup_logging  # noqa: E402


def print_counts() -> None:
    tables = [
        "silver.customers",
        "silver.products",
        "silver.orders",
        "silver.payments",
        "silver.shipments",
        "silver.rejected_records",
    ]
    with get_connection("ecommerce_silver") as conn:
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                print(f"{table}: {cur.fetchone()[0]}")


if __name__ == "__main__":
    logger = setup_logging("run_silver_v2")
    start = time.time()
    logger.info("START silver v2 pipeline")

    with get_connection("ecommerce_silver") as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE silver.rejected_records")
        conn.commit()
    logger.info("TRUNCATE silver.rejected_records")

    steps = [
        ("customers", transform_customers),
        ("products", transform_products),
        ("orders", transform_orders),
        ("payments", transform_payments),
        ("shipments", transform_shipments),
    ]

    for name, fn in steps:
        logger.info("Korak: transform_%s", name)
        fn()

    elapsed = round(time.time() - start, 2)
    logger.info("GOTOVO silver v2 pipeline (%ss)", elapsed)
    print_counts()
