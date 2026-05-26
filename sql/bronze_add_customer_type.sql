-- Pokreni na bazi ecommerce_bronze
ALTER TABLE bronze.customers_raw
ADD COLUMN IF NOT EXISTS customer_type TEXT;
