#!/bin/bash
set -euo pipefail

echo "=== Docker init: creating ecommerce databases ==="

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
CREATE DATABASE ecommerce_bronze;
CREATE DATABASE ecommerce_silver;
CREATE DATABASE ecommerce_gold;
EOSQL

echo "=== Docker init: bronze schema ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d ecommerce_bronze -f /sql/bronze_setup.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d ecommerce_bronze -f /sql/bronze_add_customer_type.sql

echo "=== Docker init: silver schema ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d ecommerce_silver -f /sql/silver_v2_setup.sql

echo "=== Docker init: gold schema ==="
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d ecommerce_gold -f /sql/gold_setup.sql

echo "=== Docker init: done ==="
