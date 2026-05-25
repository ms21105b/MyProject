-- Cohort retention by first observed purchase month.
-- Retention definition: a customer is retained in month N if they have any purchase N months after
-- first observed purchase inside this dataset. This is not necessarily lifetime first purchase.

WITH cohort_counts AS (
    SELECT
        first_observed_purchase_month,
        cohort_index,
        COUNT(DISTINCT customer_id) AS retained_customers
    FROM transactions_clean
    GROUP BY first_observed_purchase_month, cohort_index
),
cohort_sizes AS (
    SELECT
        first_observed_purchase_month,
        retained_customers AS cohort_size
    FROM cohort_counts
    WHERE cohort_index = 0
)
SELECT
    c.first_observed_purchase_month,
    c.cohort_index,
    c.retained_customers,
    s.cohort_size,
    ROUND(1.0 * c.retained_customers / s.cohort_size, 4) AS retention_rate
FROM cohort_counts c
JOIN cohort_sizes s USING (first_observed_purchase_month)
ORDER BY c.first_observed_purchase_month, c.cohort_index;

-- Promo vs non-promo first-observed-purchase cohorts.
WITH first_orders AS (
    SELECT
        customer_id,
        MIN(purchase_date) AS first_observed_purchase_date
    FROM transactions_clean
    GROUP BY customer_id
),
first_order_flags AS (
    SELECT
        t.customer_id,
        t.promo_code_used AS first_order_promo
    FROM transactions_clean t
    JOIN first_orders f
      ON t.customer_id = f.customer_id
     AND t.purchase_date = f.first_observed_purchase_date
),
cohort_counts AS (
    SELECT
        t.first_observed_purchase_month,
        f.first_order_promo,
        t.cohort_index,
        COUNT(DISTINCT t.customer_id) AS retained_customers
    FROM transactions_clean t
    JOIN first_order_flags f USING (customer_id)
    GROUP BY t.first_observed_purchase_month, f.first_order_promo, t.cohort_index
),
cohort_sizes AS (
    SELECT
        first_observed_purchase_month,
        first_order_promo,
        retained_customers AS cohort_size
    FROM cohort_counts
    WHERE cohort_index = 0
)
SELECT
    c.first_observed_purchase_month,
    CASE WHEN c.first_order_promo = 1 THEN 'Promo First Observed Order' ELSE 'No Promo First Observed Order' END AS cohort_type,
    c.cohort_index,
    c.retained_customers,
    s.cohort_size,
    ROUND(1.0 * c.retained_customers / s.cohort_size, 4) AS retention_rate
FROM cohort_counts c
JOIN cohort_sizes s USING (first_observed_purchase_month, first_order_promo)
ORDER BY c.first_observed_purchase_month, cohort_type, c.cohort_index;
