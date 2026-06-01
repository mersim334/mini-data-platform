-- Pokreni na bazi ecommerce_bronze
-- Dodaje kolonu customer_type (potrebno za Silver v2 company/individual pravila)
--
-- macOS / Linux:
--   psql -U postgres -h localhost -d ecommerce_bronze -f sql/bronze_add_customer_type.sql
-- Ili: python jobs/setup_silver_v2.py (pokreće i silver DDL)

ALTER TABLE bronze.customers_raw
ADD COLUMN IF NOT EXISTS customer_type TEXT;
