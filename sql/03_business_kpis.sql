-- Core business KPIs for README and interview discussion.

-- Monthly sales, active users, AOV, promo usage, and customer-level churn.
WITH monthly_base AS (
    SELECT
        purchase_month,
        COUNT(*) AS orders,
        COUNT(DISTINCT customer_id) AS active_customers,
        SUM(purchase_amount) AS sales,
        AVG(purchase_amount) AS avg_order_value,
        AVG(promo_code_used) AS promo_usage_rate
    FROM transactions_clean
    GROUP BY purchase_month
),
monthly_customer_churn AS (
    SELECT
        purchase_month,
        AVG(customer_churn) AS churn_rate
    FROM (
        SELECT
            purchase_month,
            customer_id,
            MAX(churn) AS customer_churn
        FROM transactions_clean
        GROUP BY purchase_month, customer_id
    )
    GROUP BY purchase_month
)
SELECT
    b.purchase_month,
    b.orders,
    b.active_customers,
    ROUND(b.sales, 2) AS sales,
    ROUND(b.avg_order_value, 2) AS avg_order_value,
    ROUND(b.promo_usage_rate, 4) AS promo_usage_rate,
    ROUND(c.churn_rate, 4) AS churn_rate
FROM monthly_base b
JOIN monthly_customer_churn c USING (purchase_month)
ORDER BY b.purchase_month;

-- Promo vs non-promo behavior comparison.
SELECT
    promo_segment,
    COUNT(*) AS orders,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(purchase_amount), 2) AS sales,
    ROUND(AVG(purchase_amount), 2) AS avg_order_value,
    ROUND(AVG(previous_purchases), 2) AS avg_previous_purchases,
    ROUND(AVG(churn), 4) AS churn_rate
FROM transactions_clean
GROUP BY promo_segment
ORDER BY orders DESC;

-- Category-level sales and promo usage.
SELECT
    category,
    COUNT(*) AS orders,
    ROUND(SUM(purchase_amount), 2) AS sales,
    ROUND(AVG(promo_code_used), 4) AS promo_usage_rate,
    ROUND(AVG(churn), 4) AS churn_rate
FROM transactions_clean
GROUP BY category
ORDER BY sales DESC;
