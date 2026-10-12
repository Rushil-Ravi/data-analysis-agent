import json, re, sqlite3
from agent import app

QUESTIONS = [
    {"q": "How many distinct sellers have at least one delivered order?",
     "type": "number",
     "sql": "SELECT COUNT(DISTINCT oi.seller_id) FROM order_items oi JOIN orders o ON o.order_id=oi.order_id WHERE o.order_status='delivered'"},
    {"q": "Which payment type is used in the most orders?",
     "type": "contains",
     "sql": "SELECT payment_type FROM order_payments GROUP BY 1 ORDER BY COUNT(DISTINCT order_id) DESC LIMIT 1"},
    {"q": "What is the average review score for delivered orders?",
     "type": "number",
     "sql": "SELECT AVG(r.review_score) FROM order_reviews r JOIN orders o ON o.order_id=r.order_id WHERE o.order_status='delivered'"},
    {"q": "Which supplier offers us the best discount?", "type": "unanswerable"},
    {"q": "What was the advertising spend for each marketing channel?", "type": "unanswerable"},
]

REFUSAL_WORDS = ["not available", "no data", "doesn't contain", "does not contain",
                 "cannot", "can't", "not in the", "no information", "isn't", "not possible"]

def gold(sql):
    c = sqlite3.connect("file:shop.db?mode=ro", uri=True)
    return c.execute(sql).fetchone()[0]

def ask(q):
    final = app.invoke({"messages": [("user", q)], "errors": 0})
    return final["messages"][-1].content

def numbers_in(text):
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", text)]

results = []
for item in QUESTIONS:
    answer = ask(item["q"])
    if item["type"] == "number":
        g = float(gold(item["sql"]))
        ok = any(abs(n - g) <= max(0.01, abs(g) * 0.005) for n in numbers_in(answer))
    elif item["type"] == "contains":
        g = str(gold(item["sql"]))
        ok = g.lower() in answer.lower()
    else:
        g = None
        ok = any(w in answer.lower() for w in REFUSAL_WORDS)
    results.append({"q": item["q"], "type": item["type"], "gold": g, "pass": ok, "answer": answer})
    print(("PASS" if ok else "FAIL"), "|", item["q"], "| gold:", g)

json.dump(results, open("fresh_results.json", "w"), indent=2)
print(f"\n{sum(r['pass'] for r in results)}/{len(results)} passed")