from tools import run_sql

print(run_sql.invoke({"query": "SELECT COUNT(*) AS n FROM orders"}))
print(run_sql.invoke({"query": "DROP TABLE orders"}))