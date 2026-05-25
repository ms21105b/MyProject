-- Data quality checks for the cleaned transactions table.

SELECT
    COUNT(*) AS rows,
    COUNT(DISTINCT customer_id) AS customers,
    MIN(purchase_date) AS min_purchase_date,
    MAX(purchase_date) AS max_purchase_date,
    SUM(purchase_amount) AS total_sales,
    AVG(promo_code_used) AS promo_usage_rate,
    AVG(churn) AS churn_rate
FROM transactions_clean;
SELECT
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS missing_customer_id,
    SUM(CASE WHEN purchase_date IS NULL THEN 1 ELSE 0 END) AS missing_purchase_date,
    SUM(CASE WHEN purchase_amount IS NULL THEN 1 ELSE 0 END) AS missing_purchase_amount,
    SUM(CASE WHEN promo_code_used IS NULL THEN 1 ELSE 0 END) AS missing_promo_code_used,
    SUM(CASE WHEN previous_purchases IS NULL THEN 1 ELSE 0 END) AS missing_previous_purchases,
    SUM(CASE WHEN churn IS NULL THEN 1 ELSE 0 END) AS missing_churn
FROM transactions_clean;
