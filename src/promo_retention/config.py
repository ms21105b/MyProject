"""Project paths and dataset field names."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURE_DIR = PROJECT_ROOT / "figures"

DEFAULT_RAW_FILE = RAW_DIR / "EcommData_CSV.csv"

RAW_COLUMNS = {
    "customer_id": "Customer ID",
    "age": "Age",
    "gender": "Gender",
    "item_purchased": "Item Purchased",
    "category": "Category",
    "purchase_amount": "Purchase Amount (USD)",
    "location": "Location",
    "size": "Size",
    "color": "Color",
    "season": "Season",
    "review_rating": "Review Rating",
    "subscription_status": "Subscription Status",
    "payment_method": "Payment Method",
    "shipping_type": "Shipping Type",
    "discount_applied": "Discount Applied",
    "promo_code_used": "Promo Code Used",
    "previous_purchases": "Previous Purchases",
    "preferred_payment_method": "Preferred Payment Method",
    "frequency_of_purchases": "Frequency of Purchases",
    "purchase_date": "Purchase Date",
    "churn": "Churn",
}
