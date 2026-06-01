#!/bin/sh
set -e

echo "=== Mini Data Platform - Docker pipeline ==="
echo "Waiting for PostgreSQL at ${PGHOST}:${PGPORT}..."

python - <<'PY'
import os
import sys
import time

import psycopg2

host = os.environ["PGHOST"]
port = int(os.environ.get("PGPORT", "5432"))
user = os.environ.get("PGUSER", "postgres")
password = os.environ["PGPASSWORD"]

for attempt in range(1, 31):
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname="postgres",
            user=user,
            password=password,
            connect_timeout=3,
        )
        conn.close()
        print("PostgreSQL is ready.")
        sys.exit(0)
    except psycopg2.OperationalError as exc:
        print(f"  attempt {attempt}/30: {exc}")
        time.sleep(2)

print("PostgreSQL did not become ready in time.", file=sys.stderr)
sys.exit(1)
PY

echo "=== Generating CSV test data ==="
python jobs/generate_test_data.py

echo "=== Running full ETL pipeline ==="
python jobs/run_pipeline.py

echo ""
echo "============================================"
echo "  PIPELINE FINISHED"
echo "  Dashboard: reports/latest_dashboard.html"
echo "============================================"
