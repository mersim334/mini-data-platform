-- Monitoring upiti za pgAdmin (ecommerce_silver / ecommerce_gold)

-- 1) Broj redova po Silver tabelama
SELECT 'customers' AS tabela, COUNT(*) FROM silver.customers
UNION ALL SELECT 'products', COUNT(*) FROM silver.products
UNION ALL SELECT 'orders', COUNT(*) FROM silver.orders
UNION ALL SELECT 'payments', COUNT(*) FROM silver.payments
UNION ALL SELECT 'shipments', COUNT(*) FROM silver.shipments
UNION ALL SELECT 'rejected_records', COUNT(*) FROM silver.rejected_records;

-- 2) Top razlozi odbijanja
SELECT source_table, reject_reason, COUNT(*) AS broj
FROM silver.rejected_records
GROUP BY 1, 2
ORDER BY broj DESC
LIMIT 20;

-- 3) Gold konzistentnost (revenue vs total_spent)
SELECT
    (SELECT SUM(revenue) FROM gold.daily_sales_kpi) AS revenue,
    (SELECT SUM(total_spent) FROM gold.customer_kpi) AS total_spent;

-- 4) Orphan provjera (ne bi trebalo nista)
SELECT COUNT(*) AS orphan_orders
FROM silver.orders o
WHERE NOT EXISTS (SELECT 1 FROM silver.customers c WHERE c.customer_id = o.customer_id)
   OR NOT EXISTS (SELECT 1 FROM silver.products p WHERE p.product_id = o.product_id);
