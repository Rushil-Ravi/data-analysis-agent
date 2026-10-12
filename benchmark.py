import glob
import json
import os
import re
import sqlite3
import time
import sys

from agent import app, MODEL

QUESTIONS = [
    {"q": "How many orders are there in total?", "type": "number",
     "gold_sql": "SELECT COUNT(*) FROM orders"},
    {"q": "How many delivered orders are there?", "type": "number",
     "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered'"},
    {"q": "How many unique customers are there?", "type": "number",
     "gold_sql": "SELECT COUNT(DISTINCT customer_unique_id) FROM customers"},
    {"q": "What is the total revenue from delivered orders?", "type": "number",
     "gold_sql": "SELECT ROUND(SUM(oi.price), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.order_status = 'delivered'"},
    {"q": "What is the average order value for delivered orders?", "type": "number",
     "gold_sql": "SELECT ROUND(SUM(oi.price) * 1.0 / COUNT(DISTINCT o.order_id), 2) FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.order_status = 'delivered'"},
    {"q": "What percent of delivered orders were delivered late?", "type": "number",
     "gold_sql": "SELECT ROUND(100.0 * SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) FROM orders WHERE order_status = 'delivered'"},
    {"q": "What is the average delivery time in days for delivered orders?", "type": "number",
     "gold_sql": "SELECT ROUND(AVG(julianday(order_delivered_customer_date) - julianday(order_purchase_timestamp)), 2) FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL"},
    {"q": "Which customer state has the most customers?", "type": "contains",
     "gold_sql": "SELECT customer_state FROM customers GROUP BY customer_state ORDER BY COUNT(DISTINCT customer_unique_id) DESC LIMIT 1"},
    {"q": "What are the top 5 product categories by revenue? Use the English names.", "type": "contains",
     "gold_sql": "SELECT t.product_category_name_english FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id JOIN product_category_name_translation t ON t.product_category_name = p.product_category_name WHERE o.order_status = 'delivered' GROUP BY t.product_category_name_english ORDER BY SUM(oi.price) DESC LIMIT 5"},
    {"q": "What is the average review score?", "type": "number",
     "gold_sql": "SELECT ROUND(AVG(review_score), 2) FROM order_reviews"},
    {"q": "How many reviews are unhappy (a score of 1 or 2)?", "type": "number",
     "gold_sql": "SELECT COUNT(*) FROM order_reviews WHERE review_score <= 2"},
    {"q": "What is the most common payment type by number of payments?", "type": "contains",
     "gold_sql": "SELECT payment_type FROM order_payments GROUP BY payment_type ORDER BY COUNT(*) DESC LIMIT 1"},
    {"q": "How many sellers are there?", "type": "number",
     "gold_sql": "SELECT COUNT(*) FROM sellers"},
    {"q": "What is the average freight value per order item?", "type": "number",
     "gold_sql": "SELECT ROUND(AVG(freight_value), 2) FROM order_items"},
    {"q": "How many repeat customers are there?", "type": "number",
     "gold_sql": "SELECT COUNT(*) FROM (SELECT c.customer_unique_id FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE o.order_status NOT IN ('canceled', 'unavailable') GROUP BY c.customer_unique_id HAVING COUNT(*) > 1)"},
    {"q": "What was the revenue in November 2017?", "type": "number",
     "gold_sql": "SELECT ROUND(SUM(oi.price), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.order_status = 'delivered' AND strftime('%Y-%m', o.order_purchase_timestamp) = '2017-11'"},
    {"q": "Plot the number of delivered orders per month.", "type": "chart"},
    {"q": "Show a bar chart of the top 5 customer states by number of delivered orders.", "type": "chart"},
    {"q": "What is the average salary of sellers?", "type": "unanswerable"},
    {"q": "What is the average age of customers?", "type": "unanswerable"},
]

HELDOUT = [
    {"q": "What is the average review score for customers in the state of SP?", "type": "number",
     "gold_sql": "SELECT ROUND(AVG(r.review_score), 2) FROM order_reviews r JOIN orders o ON o.order_id = r.order_id JOIN customers c ON c.customer_id = o.customer_id WHERE c.customer_state = 'SP'"},
    {"q": "What is the late delivery rate for delivered orders from customers in the state of RJ?", "type": "number",
     "gold_sql": "SELECT ROUND(100.0 * SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) / COUNT(*), 2) FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE o.order_status = 'delivered' AND c.customer_state = 'RJ'"},
    {"q": "Who are the top 3 sellers by revenue? Give their seller IDs.", "type": "contains",
     "gold_sql": "SELECT oi.seller_id FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.order_status = 'delivered' GROUP BY oi.seller_id ORDER BY SUM(oi.price) DESC LIMIT 3"},
    {"q": "What was the total revenue in 2017?", "type": "number",
     "gold_sql": "SELECT ROUND(SUM(oi.price), 2) FROM order_items oi JOIN orders o ON o.order_id = oi.order_id WHERE o.order_status = 'delivered' AND strftime('%Y', o.order_purchase_timestamp) = '2017'"},
    {"q": "What is the average number of installments for credit card payments?", "type": "number",
     "gold_sql": "SELECT ROUND(AVG(payment_installments), 2) FROM order_payments WHERE payment_type = 'credit_card'"},
    {"q": "What is the average number of items per delivered order?", "type": "number",
     "gold_sql": "SELECT ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT o.order_id), 2) FROM orders o JOIN order_items oi ON oi.order_id = o.order_id WHERE o.order_status = 'delivered'"},
    {"q": "Which product category sold the most items in delivered orders? Use the English name.", "type": "contains",
     "gold_sql": "SELECT t.product_category_name_english FROM order_items oi JOIN orders o ON o.order_id = oi.order_id JOIN products p ON p.product_id = oi.product_id JOIN product_category_name_translation t ON t.product_category_name = p.product_category_name WHERE o.order_status = 'delivered' GROUP BY t.product_category_name_english ORDER BY COUNT(*) DESC LIMIT 1"},
    {"q": "Compare the average review score of late delivered orders with on-time delivered orders.", "type": "numbers",
     "gold_sql": "SELECT ROUND(AVG(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN r.review_score END), 2), ROUND(AVG(CASE WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN r.review_score END), 2) FROM orders o JOIN order_reviews r ON r.order_id = o.order_id WHERE o.order_status = 'delivered'"},
    {"q": "Plot the average review score by customer state as a bar chart.", "type": "chart"},
    {"q": "What is the profit margin of the best-selling product category?", "type": "unanswerable"},
]

SET = "heldout" if len(sys.argv) > 1 and sys.argv[1] == "heldout" else "dev"
ITEMS = HELDOUT if SET == "heldout" else QUESTIONS
RESULTS_FILE = "heldout_results.json" if SET == "heldout" else "benchmark_results.json"
CANNOT = ["not contain", "does not", "doesn't", "no column","cannot","can't","couldn't", "not available", "no data", "isn't", "not possible", "unable"]


def gold_rows(sql):
    conn = sqlite3.connect("file:shop.db?mode=ro", uri=True)
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


def numbers_in(text):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def norm(s):
    return re.sub(r"[_\s]+", " ", str(s).lower()).strip()


def score(item, answer, new_charts):
    if answer.startswith("EXCEPTION"):
        return False, "the run crashed; rerun later"
    kind = item["type"]
    if kind == "number":
        gold = float(gold_rows(item["gold_sql"])[0][0])
        ok = any(abs(n - gold) <= max(0.01, 0.005 * abs(gold)) for n in numbers_in(answer))
        return ok, f"gold={gold}"
    
    if kind == "numbers":
        gold = [float(v) for v in gold_rows(item["gold_sql"])[0]]
        nums = numbers_in(answer)
        ok = all(any(abs(n - g) <= max(0.01, 0.005 * abs(g)) for n in nums) for g in gold)
        return ok, f"gold={gold}"
    if kind == "contains":
        gold = [norm(r[0]) for r in gold_rows(item["gold_sql"])]
        text = norm(answer)
        ok = all(re.search(r"\b" + re.escape(g) + r"\b", text) for g in gold)
        return ok, f"gold={gold}"
    if kind == "chart":
        return new_charts > 0, f"new charts={new_charts}"
    ok = any(p in answer.lower() for p in CANNOT)
    return ok, "expected: says it cannot be answered from the data"


results = json.load(open(RESULTS_FILE)) if os.path.exists(RESULTS_FILE) else {}

for i, item in enumerate(ITEMS, 1):
    key = str(i)
    if key in results and not results[key]["answer"].startswith("EXCEPTION"):
        continue  # already done; lets you resume after a rate limit
    before = len(glob.glob("charts/*.png"))
    answer = ""
    for attempt in range(3):
        try:
            out = app.invoke({"messages": [("user", item["q"])], "errors": 0})
            content = out["messages"][-1].content
            answer = content if isinstance(content, str) else str(content)
            break
        except Exception as e:
            answer = f"EXCEPTION: {str(e)[:200]}"
            time.sleep(60)
    new_charts = len(glob.glob("charts/*.png")) - before
    ok, detail = score(item, answer, new_charts)
    results[key] = {"question": item["q"], "type": item["type"], "model": MODEL,
                    "answer": answer, "correct": ok, "detail": detail}
    json.dump(results, open(RESULTS_FILE, "w"), indent=2)
    print(f"{i:>2}. {'PASS' if ok else 'FAIL'}  {item['q']}  ({detail})")
    time.sleep(3)

passed = sum(1 for r in results.values() if r["correct"])
print(f"\nAccuracy: {passed}/{len(ITEMS)} ({100 * passed / len(ITEMS):.0f}%) with model {MODEL}")