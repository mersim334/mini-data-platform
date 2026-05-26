import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from utils.logging_config import log_structured, save_metrics, setup_logging  # noqa: E402
from utils.monitoring import (  # noqa: E402
    generate_html_report,
    notify_alert,
    run_health_checks,
)


def main() -> int:
    logger = setup_logging("health_check")
    logger.info("START health_check")

    report = run_health_checks()

    for check in report.checks:
        level = logger.info if check.passed else logger.error
        level("  [%s] %s — %s", "PASS" if check.passed else "FAIL", check.name, check.detail)

    logger.info("STATUS: %s", report.status)
    logger.info("Brojaci: %s", report.counts)

    html_path = generate_html_report(report)
    logger.info("Dashboard: %s", html_path)

    save_metrics({
        "type": "health_check",
        "status": report.status,
        "counts": report.counts,
        "checks_passed": sum(1 for c in report.checks if c.passed),
        "checks_total": len(report.checks),
    })
    log_structured("health_check", {"status": report.status, "counts": report.counts}, "monitoring")

    if not report.passed:
        notify_alert(
            "Pipeline health check FAIL",
            "\n".join(
                f"- {c.name}: {c.detail}" for c in report.checks if not c.passed
            ),
        )
        return 1

    logger.info("SUCCESS health_check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
