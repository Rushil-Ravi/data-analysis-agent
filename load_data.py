import glob, os, sqlite3
import pandas as pd

conn = sqlite3.connect("shop.db")

for path in sorted(glob.glob("data/*.csv")):
    name = os.path.basename(path)
    if "geolocation" in name:
        continue  # large and not needed for this project
    table = name.replace("olist_", "").replace("_dataset.csv", "").replace(".csv", "")
    pd.read_csv(path).to_sql(table, conn, if_exists="replace", index=False)
    print("loaded", table)

# Indexes make queries much faster
conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_id ON orders(order_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_cust ON orders(customer_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_items_order ON order_items(order_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_pay_order ON order_payments(order_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_rev_order ON order_reviews(order_id)")
conn.commit()

# Quick check
print(pd.read_sql("SELECT COUNT(*) AS orders FROM orders", conn))
print(pd.read_sql(
    "SELECT order_status, COUNT(*) AS n FROM orders GROUP BY order_status ORDER BY n DESC", conn))
conn.close()
