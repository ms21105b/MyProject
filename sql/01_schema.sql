-- SQLite schema reference.
-- Build the actual database with:
-- python scripts/build_sqlite.py --input data/raw/EcommData_CSV.csv

DROP TABLE IF EXISTS transactions_clean;

CREATE TABLE transactions_clean (
    customer_id INTEGER,
    age INTEGER,
    gender TEXT,
    item_purchased TEXT,
    category TEXT,
    purchase_amount REAL,
    location TEXT,
    size TEXT,
    color TEXT,
    season TEXT,
    review_rating REAL,
    subscription_status INTEGER,
    payment_method TEXT,
    shipping_type TEXT,
    discount_applied INTEGER,
    promo_code_used INTEGER,
    previous_purchases INTEGER,
    preferred_payment_method TEXT,
    frequency_of_purchases TEXT,
    purchase_date TEXT,
    churn INTEGER,
    order_id INTEGER,
    purchase_month TEXT,
    purchase_quarter TEXT,
    promo_segment TEXT,
    first_observed_purchase_date TEXT,
    first_observed_purchase_month TEXT,
    first_purchase_date TEXT,
    first_purchase_month TEXT,
    cohort_index INTEGER
);
