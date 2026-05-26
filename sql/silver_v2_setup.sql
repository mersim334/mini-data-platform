-- Pokreni na bazi ecommerce_silver

DROP TABLE IF EXISTS silver.shipments CASCADE;
DROP TABLE IF EXISTS silver.payments CASCADE;
DROP TABLE IF EXISTS silver.orders CASCADE;
DROP TABLE IF EXISTS silver.products CASCADE;
DROP TABLE IF EXISTS silver.customers CASCADE;
DROP TABLE IF EXISTS silver.rejected_records CASCADE;

CREATE TABLE silver.rejected_records (
    id              SERIAL PRIMARY KEY,
    source_table    VARCHAR(100) NOT NULL,
    source_id       TEXT,
    reject_reason   VARCHAR(100) NOT NULL,
    raw_data        JSONB,
    rejected_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE silver.customers (
    customer_id       INTEGER PRIMARY KEY,
    customer_type     VARCHAR(20) NOT NULL
                      CHECK (customer_type IN ('individual', 'company')),
    first_name        VARCHAR(200) NOT NULL,
    last_name         VARCHAR(100),
    email             VARCHAR(255) NOT NULL UNIQUE,
    country           VARCHAR(100) NOT NULL,
    created_at        DATE,
    loaded_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    transform_version VARCHAR(20) NOT NULL DEFAULT 'v2'
);

CREATE TABLE silver.products (
    product_id        INTEGER PRIMARY KEY,
    product_name      VARCHAR(200) NOT NULL,
    category          VARCHAR(100) NOT NULL,
    price             NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    created_at        DATE,
    loaded_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    transform_version VARCHAR(20) NOT NULL DEFAULT 'v2'
);

CREATE TABLE silver.orders (
    order_id          INTEGER PRIMARY KEY,
    customer_id       INTEGER NOT NULL
                      REFERENCES silver.customers(customer_id),
    product_id        INTEGER NOT NULL
                      REFERENCES silver.products(product_id),
    quantity          INTEGER NOT NULL CHECK (quantity > 0),
    order_amount      NUMERIC(10, 2) NOT NULL CHECK (order_amount >= 0),
    order_date        DATE NOT NULL,
    status            VARCHAR(50) NOT NULL,
    loaded_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    transform_version VARCHAR(20) NOT NULL DEFAULT 'v2'
);

CREATE TABLE silver.payments (
    payment_id        INTEGER PRIMARY KEY,
    order_id          INTEGER NOT NULL
                      REFERENCES silver.orders(order_id),
    payment_method    VARCHAR(50) NOT NULL,
    amount            NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    payment_date      DATE NOT NULL,
    status            VARCHAR(50) NOT NULL,
    loaded_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    transform_version VARCHAR(20) NOT NULL DEFAULT 'v2'
);

CREATE TABLE silver.shipments (
    shipment_id       INTEGER PRIMARY KEY,
    order_id          INTEGER NOT NULL
                      REFERENCES silver.orders(order_id),
    carrier           VARCHAR(100) NOT NULL,
    tracking_number   VARCHAR(100),
    ship_date         DATE NOT NULL,
    delivery_date     DATE,
    status            VARCHAR(50) NOT NULL,
    loaded_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    transform_version VARCHAR(20) NOT NULL DEFAULT 'v2'
);

CREATE INDEX idx_customers_email ON silver.customers(email);
CREATE INDEX idx_orders_customer_id ON silver.orders(customer_id);
CREATE INDEX idx_orders_product_id ON silver.orders(product_id);
CREATE INDEX idx_orders_order_date ON silver.orders(order_date);
CREATE INDEX idx_payments_order_id ON silver.payments(order_id);
CREATE INDEX idx_shipments_order_id ON silver.shipments(order_id);
