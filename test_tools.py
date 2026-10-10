from tools import run_sql, run_python, make_chart

print(run_sql.invoke({"query": "SELECT order_status, COUNT(*) AS n FROM orders GROUP BY order_status"}))
print(run_python.invoke({"code": "result = df.sort_values('n', ascending=False).head(3)"}))
print(run_python.invoke({"code": "import os"}))
print(make_chart.invoke({"chart_type": "bar", "x": "order_status", "y": "n", "title": "Orders by status"}))