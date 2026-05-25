-- Synthetic Control panel sketch for quasi A/B analysis.
-- The Python implementation in src/promo_retention/synthetic_control.py is the
-- canonical SCM runner. This SQL query mirrors the cutoff-safe panel idea for
-- SQL practice and inspection.

WITH params AS (
    SELECT '2024-01-01' AS treatment_start
),
pre_orders AS (
    SELECT t.*
    FROM transactions_clean t
    CROSS JOIN params p
    WHERE t.purchase_date < p.treatment_start
),
customer_pre AS (
    SELECT
        customer_id,
        location,
        COUNT(*) AS frequency,
        SUM(purchase_amount) AS monetary,
        AVG(purchase_amount) AS avg_order_value,
        AVG(promo_code_used) AS promo_usage_rate,
        MAX(purchase_date) AS last_purchase_date
    FROM pre_orders
    GROUP BY customer_id, location
),
rfm_scored AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY julianday(last_purchase_date)) AS r_score,
        NTILE(5) OVER (ORDER BY frequency) AS f_score,
        NTILE(5) OVER (ORDER BY monetary) AS m_score
    FROM customer_pre
),
customer_segments AS (
    SELECT
        customer_id,
        location,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'High Value'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Potential Loyalist'
            WHEN r_score <= 2 AND m_score >= 4 THEN 'At Risk High Spender'
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Dormant / Churn Risk'
            ELSE 'Regular'
        END AS segment
    FROM rfm_scored
),
unit_sizes AS (
    SELECT
        segment,
        location,
        COUNT(DISTINCT customer_id) AS unit_customers
    FROM customer_segments
    GROUP BY segment, location
),
monthly_activity AS (
    SELECT
        s.segment,
        s.location,
        t.purchase_month,
        COUNT(*) AS orders,
        COUNT(DISTINCT t.customer_id) AS active_customers,
        SUM(t.purchase_amount) AS sales,
        SUM(t.promo_code_used) AS promo_orders
    FROM transactions_clean t
    JOIN customer_segments s
      ON t.customer_id = s.customer_id
    GROUP BY s.segment, s.location, t.purchase_month
)
SELECT
    a.segment || ' | ' || a.location AS unit_id,
    a.segment,
    a.location,
    a.purchase_month,
    u.unit_customers,
    a.active_customers,
    a.orders,
    ROUND(1.0 * a.active_customers / u.unit_customers, 6) AS active_customer_rate,
    ROUND(1.0 * a.orders / u.unit_customers, 6) AS orders_per_customer,
    ROUND(1.0 * a.sales / u.unit_customers, 6) AS sales_per_customer,
    ROUND(1.0 * a.promo_orders / NULLIF(a.orders, 0), 6) AS promo_usage_rate
FROM monthly_activity a
JOIN unit_sizes u
  ON a.segment = u.segment
 AND a.location = u.location
ORDER BY a.segment, a.location, a.purchase_month;
