import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402


def run_sql_file(dbname: str, sql_path: Path) -> None:
    sql = sql_path.read_text(encoding="utf-8")
    with get_connection(dbname) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print(f"OK: {sql_path.name} -> {dbname}")


def refresh_bronze_customers() -> None:
    from jobs.ingest_customers import ingest_customers

    with get_connection("ecommerce_bronze") as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE bronze.customers_raw")
        conn.commit()

    ingest_customers()


if __name__ == "__main__":
    root = BASE_DIR / "sql"
    run_sql_file("ecommerce_bronze", root / "bronze_add_customer_type.sql")
    run_sql_file("ecommerce_silver", root / "silver_v2_setup.sql")
    refresh_bronze_customers()
    print("Silver v2 schema spremna. Pokreni: python jobs/run_silver_v2.py")
