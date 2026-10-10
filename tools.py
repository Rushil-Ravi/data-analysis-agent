import re
import sqlite3
from langchain_core.tools import tool

DB_PATH = "shop.db"
BLOCKED = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum)\b", re.I
)


def _connect():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def get_schema():
    conn = _connect()
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"
    ).fetchall()
    conn.close()
    return "\n".join(r[0] for r in rows)


@tool
def run_sql(query: str) -> str:
    """Run one read-only SQLite SELECT query on the shop database and return up to 50 rows.
    If the query fails, an error message is returned so you can fix the query."""
    q = query.strip().rstrip(";")
    if not re.match(r"^(select|with)\b", q, re.I) or BLOCKED.search(q) or ";" in q:
        return "ERROR: only a single read-only SELECT query is allowed."
    try:
        conn = _connect()
        cur = conn.execute(q)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(51)
        conn.close()
    except Exception as e:
        return f"ERROR: {e}"
    note = "\n(showing first 50 rows)" if len(rows) > 50 else ""
    lines = ["\t".join(cols)] + ["\t".join(str(v) for v in r) for r in rows[:50]]
    return "\n".join(lines) + note