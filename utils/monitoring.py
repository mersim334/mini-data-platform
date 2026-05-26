"""Health checkovi i alerti za monitoring pipeline-a."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from utils.db import get_connection
from utils.logging_config import BASE_DIR, LOG_DIR, REPORTS_DIR, log_structured

BRONZE_DB = "ecommerce_bronze"
SILVER_DB = "ecommerce_silver"
GOLD_DB = "ecommerce_gold"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class HealthReport:
    status: str = "FAIL"
    checks: list[CheckResult] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    top_rejects: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def _count(db: str, table: str) -> int:
    with get_connection(db) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]


def _fetchone(db: str, sql: str):
    with get_connection(db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()


def run_health_checks() -> HealthReport:
    report = HealthReport()
    checks: list[CheckResult] = []

    bronze_customers = _count(BRONZE_DB, "bronze.customers_raw")
    bronze_orders = _count(BRONZE_DB, "bronze.orders_raw")
    silver_customers = _count(SILVER_DB, "silver.customers")
    silver_products = _count(SILVER_DB, "silver.products")
    silver_orders = _count(SILVER_DB, "silver.orders")
    silver_payments = _count(SILVER_DB, "silver.payments")
    silver_shipments = _count(SILVER_DB, "silver.shipments")
    rejected = _count(SILVER_DB, "silver.rejected_records")

    report.counts = {
        "bronze_customers": bronze_customers,
        "bronze_orders": bronze_orders,
        "silver_customers": silver_customers,
        "silver_products": silver_products,
        "silver_orders": silver_orders,
        "silver_payments": silver_payments,
        "silver_shipments": silver_shipments,
        "rejected_records": rejected,
    }

    checks.append(CheckResult(
        "bronze_has_data",
        bronze_customers > 0 and bronze_orders > 0,
        f"bronze customers={bronze_customers}, orders={bronze_orders}",
    ))
    checks.append(CheckResult(
        "silver_has_data",
        silver_customers > 0 and silver_orders > 0,
        f"silver customers={silver_customers}, orders={silver_orders}",
    ))
    checks.append(CheckResult(
        "silver_less_than_bronze",
        silver_customers <= bronze_customers and silver_orders <= bronze_orders,
        "silver ne smije imati vise redova od bronze",
    ))
    checks.append(CheckResult(
        "orders_payments_shipments_match",
        silver_orders == silver_payments == silver_shipments,
        f"orders={silver_orders}, payments={silver_payments}, shipments={silver_shipments}",
    ))

    orphan_orders = _fetchone(SILVER_DB, """
        SELECT COUNT(*) FROM silver.orders o
        WHERE NOT EXISTS (SELECT 1 FROM silver.customers c WHERE c.customer_id = o.customer_id)
           OR NOT EXISTS (SELECT 1 FROM silver.products p WHERE p.product_id = o.product_id)
    """)[0]
    checks.append(CheckResult(
        "no_orphan_orders",
        orphan_orders == 0,
        f"orphan orders={orphan_orders}",
    ))

    gold_row = _fetchone(GOLD_DB, """
        SELECT
            (SELECT COALESCE(SUM(revenue), 0) FROM gold.daily_sales_kpi),
            (SELECT COALESCE(SUM(total_spent), 0) FROM gold.customer_kpi),
            (SELECT COUNT(*) FROM gold.daily_sales_kpi),
            (SELECT COUNT(*) FROM gold.customer_kpi)
    """)
    revenue, spent, days, customers_kpi = gold_row
    revenue = Decimal(revenue)
    spent = Decimal(spent)

    report.counts["gold_revenue"] = float(revenue)
    report.counts["gold_total_spent"] = float(spent)
    report.counts["gold_days"] = days
    report.counts["gold_customers_kpi"] = customers_kpi

    checks.append(CheckResult(
        "gold_revenue_matches_spent",
        revenue == spent and revenue > 0,
        f"revenue={revenue}, total_spent={spent}",
    ))
    checks.append(CheckResult(
        "gold_has_kpi_rows",
        days > 0 and customers_kpi > 0,
        f"daily_sales_kpi={days}, customer_kpi={customers_kpi}",
    ))

    if bronze_customers > 0:
        reject_rate = rejected / bronze_customers
        report.counts["reject_rate_approx"] = round(reject_rate, 4)
        checks.append(CheckResult(
            "reject_rate_sane",
            reject_rate < 0.5,
            f"rejected={rejected}, approx rate={reject_rate:.2%}",
        ))

    with get_connection(SILVER_DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source_table, reject_reason, COUNT(*) AS broj
                FROM silver.rejected_records
                GROUP BY 1, 2
                ORDER BY broj DESC
                LIMIT 10
            """)
            report.top_rejects = [
                {"source_table": r[0], "reject_reason": r[1], "count": r[2]}
                for r in cur.fetchall()
            ]

    report.checks = checks
    report.status = "PASS" if all(c.passed for c in checks) else "FAIL"
    return report


def write_alert(message: str) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    path = LOG_DIR / "ALERT.log"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")
    return path


def notify_alert(title: str, body: str) -> None:
    """Upozorenje u ALERT.log + opcionalni Slack webhook (SLACK_WEBHOOK_URL)."""
    text = f"{title}\n{body}"
    write_alert(text)
    log_structured("alert", {"title": title, "body": body}, "monitoring")

    webhook = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        return

    payload = json.dumps({"text": f"*{title}*\n{body}"}).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=10)
    except urllib.error.URLError:
        write_alert("Slack webhook nije poslan (URL ne radi ili nema mreze).")


def generate_html_report(report: HealthReport, metrics: dict | None = None) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / "latest_dashboard.html"

    checks_rows = "".join(
        f"<tr class='{'ok' if c.passed else 'fail'}'>"
        f"<td>{c.name}</td><td>{'PASS' if c.passed else 'FAIL'}</td><td>{c.detail}</td></tr>"
        for c in report.checks
    )
    reject_rows = "".join(
        f"<tr><td>{r['source_table']}</td><td>{r['reject_reason']}</td><td>{r['count']}</td></tr>"
        for r in report.top_rejects
    )
    metrics_block = json.dumps(metrics or {}, indent=2, ensure_ascii=False, default=str)

    html = f"""<!DOCTYPE html>
<html lang="bs"><head><meta charset="utf-8">
<title>Pipeline Monitoring Dashboard</title>
<style>
  body {{ font-family: Segoe UI, sans-serif; margin: 24px; background: #f5f5f5; }}
  h1, h2 {{ color: #222; }}
  .status {{ font-size: 1.4em; padding: 12px; border-radius: 8px; display: inline-block; }}
  .PASS {{ background: #d4edda; color: #155724; }}
  .FAIL {{ background: #f8d7da; color: #721c24; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; margin-bottom: 24px; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  th {{ background: #333; color: #fff; }}
  tr.ok {{ background: #f6fff8; }}
  tr.fail {{ background: #fff5f5; }}
  pre {{ background: #fff; padding: 12px; border: 1px solid #ddd; overflow-x: auto; }}
</style></head><body>
<h1>Mini Data Platform — Monitoring</h1>
<p class="status {report.status}">{report.status}</p>
<h2>Health checkovi</h2>
<table><tr><th>Check</th><th>Rezultat</th><th>Detalj</th></tr>{checks_rows}</table>
<h2>Brojaci</h2>
<pre>{json.dumps(report.counts, indent=2, ensure_ascii=False)}</pre>
<h2>Top odbijanja</h2>
<table><tr><th>Tabela</th><th>Razlog</th><th>Broj</th></tr>{reject_rows or '<tr><td colspan=3>Nema</td></tr>'}</table>
<h2>Metrike pipeline-a</h2>
<pre>{metrics_block}</pre>
</body></html>"""

    path.write_text(html, encoding="utf-8")
    return path
