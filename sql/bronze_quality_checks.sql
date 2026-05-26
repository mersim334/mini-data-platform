-- Bronze quality checks (koraci 24-27 roadmapa)
-- Pokreni na bazi ecommerce_bronze nakon ingest-a
-- Cilj: PRONACI probleme — podaci u Bronze ostaju nepromijenjeni

-- ---------------------------------------------------------------------------
-- 25) Duplikat emailova (customers)
-- ---------------------------------------------------------------------------
SELECT
    LOWER(TRIM(email)) AS email,
    COUNT(*) AS broj_puta
FROM bronze.customers_raw
WHERE email IS NOT NULL AND TRIM(email) <> ''
GROUP BY LOWER(TRIM(email))
HAVING COUNT(*) > 1
ORDER BY broj_puta DESC;

-- ---------------------------------------------------------------------------
-- 26) Negativne cijene (products)
-- ---------------------------------------------------------------------------
SELECT
    product_id,
    product_name,
    price
FROM bronze.products_raw
WHERE TRIM(COALESCE(price, '')) <> ''
  AND TRIM(price) ~ '^-?[0-9]+(\.[0-9]+)?$'
  AND price::numeric < 0;

-- ---------------------------------------------------------------------------
-- 27) Quantity manje ili jednako nuli (orders)
-- ---------------------------------------------------------------------------
SELECT
    order_id,
    customer_id,
    product_id,
    quantity,
    order_amount,
    status
FROM bronze.orders_raw
WHERE TRIM(COALESCE(quantity, '')) <> ''
  AND TRIM(quantity) ~ '^-?[0-9]+(\.[0-9]+)?$'
  AND quantity::numeric <= 0;

-- ---------------------------------------------------------------------------
-- Sažetak (brojevi za brzu provjeru)
-- ---------------------------------------------------------------------------
SELECT 'duplicate_email_groups' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT LOWER(TRIM(email))
    FROM bronze.customers_raw
    WHERE email IS NOT NULL AND TRIM(email) <> ''
    GROUP BY LOWER(TRIM(email))
    HAVING COUNT(*) > 1
) dup

UNION ALL

SELECT 'negative_prices', COUNT(*)
FROM bronze.products_raw
WHERE TRIM(COALESCE(price, '')) <> ''
  AND TRIM(price) ~ '^-?[0-9]+(\.[0-9]+)?$'
  AND price::numeric < 0

UNION ALL

SELECT 'invalid_quantity', COUNT(*)
FROM bronze.orders_raw
WHERE TRIM(COALESCE(quantity, '')) <> ''
  AND TRIM(quantity) ~ '^-?[0-9]+(\.[0-9]+)?$'
  AND quantity::numeric <= 0;
