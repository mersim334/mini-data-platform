"""Bronze data quality checks (roadmap koraci 24-27, 41).

Pronalazi probleme u sirovim podacima — ne zaustavlja pipeline jer loši
podaci u Bronze-u su očekivani.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.logging_config import log_structured, setup_logging  # noqa: E402

BRONZE_DB = "ecommerce_bronze"

CHECKS = {
    "duplicate_email_groups": """
        SELECT COUNT(*) FROM (
            SELECT LOWER(TRIM(email))
            FROM bronze.customers_raw
            WHERE email IS NOT NULL AND TRIM(email) <> ''
            GROUP BY LOWER(TRIM(email))
            HAVING COUNT(*) > 1
        ) dup
    """,
    "negative_prices": """
        SELECT COUNT(*)
        FROM bronze.products_raw
        WHERE TRIM(COALESCE(price, '')) <> ''
          AND TRIM(price) ~ '^-?[0-9]+(\\.[0-9]+)?$'
          AND price::numeric < 0
    """,
    "invalid_quantity": """
        SELECT COUNT(*)
        FROM bronze.orders_raw
        WHERE TRIM(COALESCE(quantity, '')) <> ''
          AND TRIM(quantity) ~ '^-?[0-9]+(\\.[0-9]+)?$'
          AND quantity::numeric <= 0
    """,
}


@dataclass
class CheckResult:
    name: str
    issue_count: int

    @property
    def detail(self) -> str:
        return f"{self.name}={self.issue_count}"


def run_bronze_checks() -> list[CheckResult]:
    results: list[CheckResult] = []
    with get_connection(BRONZE_DB) as conn:
        with conn.cursor() as cur:
            for name, sql in CHECKS.items():
                cur.execute(sql)
                count = cur.fetchone()[0]
                results.append(CheckResult(name=name, issue_count=count))
    return results


def main() -> int:
    logger = setup_logging("bronze_data_checks")
    logger.info("START bronze_data_checks")

    results = run_bronze_checks()
    summary = {r.name: r.issue_count for r in results}

    for check in results:
        logger.info("  CHECK %s — pronadjeno %s problema", check.name, check.issue_count)

    logger.info("SAZETAK bronze checks: %s", summary)
    log_structured("bronze_data_checks", summary, "bronze")

    logger.info("SUCCESS bronze_data_checks (informativno — loši podaci su ocekivani u Bronze)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
