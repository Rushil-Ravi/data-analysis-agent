import sqlite3

c = sqlite3.connect("file:shop.db?mode=ro", uri=True)

print("Q1 distinct sellers with a delivered order:", c.execute("""
    SELECT COUNT(DISTINCT oi.seller_id)
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
""").fetchone()[0])

print("Q2 top payment type (by orders):", c.execute("""
    SELECT payment_type, COUNT(DISTINCT order_id) AS n
    FROM order_payments
    GROUP BY payment_type
    ORDER BY n DESC
    LIMIT 1
""").fetchone())

print("Q3 avg review score, delivered orders:", c.execute("""
    SELECT AVG(r.review_score)
    FROM order_reviews r
    JOIN orders o ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
""").fetchone()[0])