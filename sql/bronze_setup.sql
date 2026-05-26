-- Pokreni na bazi ecommerce_bronze
-- Kreira schema bronze i sve raw tabele (koraci 18-19 roadmapa)

CREATE SCHEMA IF NOT EXISTS bronze;

DROP TABLE IF EXISTS bronze.shipments_raw CASCADE;
DROP TABLE IF EXISTS bronze.payments_raw CASCADE;
DROP TABLE IF EXISTS bronze.orders_raw CASCADE;
DROP TABLE IF EXISTS bronze.products_raw CASCADE;
DROP TABLE IF EXISTS bronze.customers_raw CASCADE;

CREATE TABLE bronze.customers_raw (
    customer_id   TEXT,
    first_name    TEXT,
    last_name     TEXT,
    email         TEXT,
    country       TEXT,
    created_at    TEXT,
    customer_type TEXT
);

CREATE TABLE bronze.products_raw (
    product_id   TEXT,
    product_name TEXT,
    category     TEXT,
    price        TEXT,
    created_at   TEXT
);

CREATE TABLE bronze.orders_raw (
    order_id     TEXT,
    customer_id  TEXT,
    product_id   TEXT,
    quantity     TEXT,
    order_amount TEXT,
    order_date   TEXT,
    status       TEXT
);

CREATE TABLE bronze.payments_raw (
    payment_id     TEXT,
    order_id       TEXT,
    payment_method TEXT,
    amount         TEXT,
    payment_date   TEXT,
    status         TEXT
);

CREATE TABLE bronze.shipments_raw (
    shipment_id     TEXT,
    order_id        TEXT,
    carrier         TEXT,
    tracking_number TEXT,
    ship_date       TEXT,
    delivery_date   TEXT,
    status          TEXT
);
