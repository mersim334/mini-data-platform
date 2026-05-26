-- Pokreni na bazi ecommerce_gold

CREATE SCHEMA IF NOT EXISTS gold;

DROP TABLE IF EXISTS gold.customer_kpi CASCADE;
DROP TABLE IF EXISTS gold.daily_sales_kpi CASCADE;

CREATE TABLE gold.daily_sales_kpi (
    order_date            DATE PRIMARY KEY,
    total_orders          INTEGER NOT NULL,
    revenue               NUMERIC(12, 2) NOT NULL,
    average_order_value   NUMERIC(12, 2) NOT NULL,
    loaded_at             TIMESTAMP NOT NULL DEFAULT NOW(),
    transform_version     VARCHAR(20) NOT NULL DEFAULT 'v1'
);

CREATE TABLE gold.customer_kpi (
    customer_id           INTEGER PRIMARY KEY,
    total_orders          INTEGER NOT NULL,
    total_spent           NUMERIC(12, 2) NOT NULL,
    last_order_date       DATE NOT NULL,
    loaded_at             TIMESTAMP NOT NULL DEFAULT NOW(),
    transform_version     VARCHAR(20) NOT NULL DEFAULT 'v1'
);
