-- Customer-level RFM base table. Scoring is implemented in Python because quantile
-- scoring is easier to reproduce there, but this SQL demonstrates the feature logic.

WITH customer_rfm AS (
    SELECT
        customer_id,
        CAST(julianday((SELECT MAX(purchase_date) FROM transactions_clean)) - julianday(MAX(purchase_date)) AS INTEGER) AS recency,
        COUNT(*) AS frequency,
        ROUND(SUM(purchase_amount), 2) AS monetary,
        ROUND(AVG(promo_code_used), 4) AS promo_usage_rate,
        MAX(previous_purchases) AS previous_purchases,
        MAX(churn) AS churn
    FROM transactions_clean
    GROUP BY customer_id
)
SELECT
    customer_id,
    recency,
    frequency,
    monetary,
    promo_usage_rate,
    previous_purchases,
    churn
FROM customer_rfm
ORDER BY monetary DESC
LIMIT 100;

-- Segment proxy summary using simple thresholds for SQL-only discussion.
WITH customer_rfm AS (
    SELECT
        customer_id,
        CAST(julianday((SELECT MAX(purchase_date) FROM transactions_clean)) - julianday(MAX(purchase_date)) AS INTEGER) AS recency,
        COUNT(*) AS frequency,
        SUM(purchase_amount) AS monetary,
        AVG(promo_code_used) AS promo_usage_rate,
        MAX(churn) AS churn
    FROM transactions_clean
    GROUP BY customer_id
),
promo_threshold AS (
    SELECT
        AVG(promo_usage_rate) AS high_promo_threshold
    FROM customer_rfm
    WHERE promo_usage_rate > 0
),
segmented AS (
    SELECT
        r.*,
        CASE
            WHEN frequency >= 4 AND monetary >= 250 AND recency <= 90 THEN 'High Value'
            WHEN frequency >= 3 AND recency <= 180 THEN 'Potential Loyalist'
            WHEN recency > 365 THEN 'Dormant / Churn Risk'
            ELSE 'Regular'
        END AS segment,
        CASE
            WHEN promo_usage_rate = 0 THEN 'No Promo'
            WHEN promo_usage_rate >= p.high_promo_threshold THEN 'High Promo'
            ELSE 'Moderate Promo'
        END AS promo_sensitivity
    FROM customer_rfm r
    CROSS JOIN promo_threshold p
)
SELECT
    segment,
    promo_sensitivity,
    COUNT(*) AS customers,
    ROUND(AVG(recency), 1) AS avg_recency,
    ROUND(AVG(frequency), 1) AS avg_frequency,
    ROUND(AVG(monetary), 2) AS avg_monetary,
    ROUND(AVG(promo_usage_rate), 4) AS promo_usage_rate,
    ROUND(AVG(churn), 4) AS churn_rate
FROM segmented
GROUP BY segment, promo_sensitivity
ORDER BY segment, customers DESC;
