import sys
from pathlib import Path

from pyspark.sql import SparkSession

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.logging_config import log_structured, setup_logging  # noqa: E402

DATA_DIR = BASE_DIR / "data"
CSV_FILE = DATA_DIR / "orders.csv"


def read_orders_with_spark(csv_path: Path) -> list[dict]:
    spark = (
        SparkSession.builder.appName("ingest_orders")
        .master("local[*]")
        .getOrCreate()
    )

    try:
        df = spark.read.option("header", True).csv(str(csv_path))
        return [row.asDict() for row in df.collect()]
    finally:
        spark.stop()


def ingest_orders() -> int:
    logger = setup_logging("ingest_orders")
    logger.info("START ingest_orders")

    if not CSV_FILE.exists():
        logger.error("CSV fajl nije pronadjen: %s", CSV_FILE)
        raise FileNotFoundError(CSV_FILE)

    rows = read_orders_with_spark(CSV_FILE)
    logger.info("PySpark procitao %s redova iz %s", len(rows), CSV_FILE.name)

    insert_sql = """
        INSERT INTO bronze.orders_raw (
            order_id, customer_id, product_id, quantity,
            order_amount, order_date, status
        )
        VALUES (
            %(order_id)s, %(customer_id)s, %(product_id)s, %(quantity)s,
            %(order_amount)s, %(order_date)s, %(status)s
        )
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(insert_sql, rows)
        conn.commit()

    logger.info("SUCCESS: ubaceno %s redova u bronze.orders_raw", len(rows))
    log_structured("ingest_success", {"table": "orders_raw", "rows": len(rows), "engine": "pyspark"}, "ingest")
    return len(rows)


if __name__ == "__main__":
    try:
        ingest_orders()
    except Exception:
        logging.getLogger(__name__).exception("ERROR ingest_orders")
        sys.exit(1)
