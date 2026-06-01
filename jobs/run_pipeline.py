"""
Glavni ETL pipeline: Bronze ingest -> checks -> Silver v2 -> Gold -> health check.

Pokretanje (vidi README.md — .env se ucitava automatski):
  python jobs/run_pipeline.py
"""

import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.db import get_connection  # noqa: E402
from utils.logging_config import log_structured, save_metrics, setup_logging  # noqa: E402
from utils.monitoring import generate_html_report, notify_alert, run_health_checks  # noqa: E402

LOG_DIR = BASE_DIR / "logs"
PYTHON = sys.executable
BRONZE_TABLES = [
    "bronze.customers_raw",
    "bronze.products_raw",
    "bronze.orders_raw",
    "bronze.payments_raw",
    "bronze.shipments_raw",
]


def truncate_bronze(logger: logging.Logger) -> None:
    logger.info("TRUNCATE bronze tabele prije ingest-a")
    tables = ", ".join(BRONZE_TABLES)
    with get_connection("ecommerce_bronze") as conn:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {tables}")
        conn.commit()


def run_step(logger: logging.Logger, label: str, script: str, metrics: dict) -> None:
    logger.info("START %s", label)
    start = time.time()
    result = subprocess.run(
        [PYTHON, str(BASE_DIR / "jobs" / script)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    elapsed = round(time.time() - start, 2)

    step_record = {"step": label, "script": script, "duration_sec": elapsed, "ok": result.returncode == 0}
    metrics["steps"].append(step_record)
    log_structured("pipeline_step", step_record, "pipeline")

    if result.stdout:
        logger.info(result.stdout.strip())
    if result.returncode != 0:
        logger.error("FAIL %s (%ss)", label, elapsed)
        if result.stderr:
            logger.error(result.stderr.strip())
        log_structured("pipeline_error", {"step": label, "stderr": result.stderr}, "pipeline")
        raise RuntimeError(f"Pipeline pao na koraku: {label}")

    logger.info("SUCCESS %s (%ss)", label, elapsed)


def run_pipeline() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logger = setup_logging("run_pipeline")
    pipeline_start = time.time()
    started_at = datetime.now().isoformat(timespec="seconds")

    metrics = {
        "started_at": started_at,
        "steps": [],
        "status": "running",
    }

    logger.info("========== PIPELINE START ==========")
    log_structured("pipeline_start", {"started_at": started_at}, "pipeline")

    try:
        truncate_bronze(logger)

        bronze_steps = [
            ("bronze ingest customers", "ingest_customers.py"),
            ("bronze ingest products", "ingest_products.py"),
            ("bronze ingest orders", "ingest_orders.py"),
            ("bronze ingest payments", "ingest_payments.py"),
            ("bronze ingest shipments", "ingest_shipments.py"),
        ]

        for label, script in bronze_steps:
            run_step(logger, label, script, metrics)

        run_step(logger, "bronze data checks", "bronze_data_checks.py", metrics)

        run_step(logger, "silver transform v2", "run_silver_v2.py", metrics)
        run_step(logger, "gold transform", "transform_gold.py", metrics)

        elapsed = round(time.time() - pipeline_start, 2)
        metrics["duration_sec"] = elapsed
        metrics["status"] = "success"

        logger.info("========== PIPELINE SUCCESS (%ss) ==========", elapsed)
        log_structured("pipeline_success", {"duration_sec": elapsed}, "pipeline")

        logger.info("START health_check")
        health = run_health_checks()
        metrics["health_status"] = health.status
        metrics["counts"] = health.counts

        for check in health.checks:
            msg = f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}"
            (logger.info if check.passed else logger.error)(msg)

        dashboard = generate_html_report(health, metrics)
        logger.info("Dashboard: %s", dashboard)

        save_metrics(metrics)

        if not health.passed:
            metrics["status"] = "health_fail"
            save_metrics(metrics)
            notify_alert(
                "Pipeline health check FAIL",
                "\n".join(c.detail for c in health.checks if not c.passed),
            )
            raise RuntimeError("Health check FAIL — pogledaj reports/latest_dashboard.html")

        logger.info("HEALTH CHECK PASS")

    except Exception as exc:
        elapsed = round(time.time() - pipeline_start, 2)
        metrics["duration_sec"] = elapsed
        metrics["status"] = "failed"
        metrics["error"] = str(exc)
        save_metrics(metrics)
        log_structured("pipeline_failed", metrics, "pipeline")
        notify_alert("Pipeline FAILED", str(exc))
        raise


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception:
        logging.getLogger(__name__).exception("PIPELINE ERROR")
        sys.exit(1)
