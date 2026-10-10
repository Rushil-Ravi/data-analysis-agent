import builtins
import contextlib
import io
import os
import re
import sqlite3
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # draw to files, not to a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from langchain_core.tools import tool

DB_PATH = "shop.db"
BLOCKED_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum)\b", re.I
)

# The most recent SQL result, shared by run_python and make_chart
STATE = {"df": None}


def _connect():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def get_schema():
    conn = _connect()
    tables = [
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    ]
    lines = []
    for t in tables:
        cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")').fetchall()]
        lines.append(f"{t}({', '.join(cols)})")
    conn.close()
    return "\n".join(lines)

@tool
def run_sql(query: str) -> str:
    """Run one read-only SQLite SELECT query on the shop database. Returns the first 50 rows.
    The full result is stored for run_python and make_chart. If the query fails, an error
    message is returned so you can fix the query."""
    q = query.strip().rstrip(";")
    if not re.match(r"^(select|with)\b", q, re.I) or BLOCKED_SQL.search(q) or ";" in q:
        return "ERROR: only a single read-only SELECT query is allowed."
    try:
        conn = _connect()
        cur = conn.execute(q)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(10001)
        conn.close()
    except Exception as e:
        return f"ERROR: {e}"

    df = pd.DataFrame(rows[:10000], columns=cols)
    STATE["df"] = df
    total = "10,000+" if len(rows) > 10000 else str(len(df))
    all_rows = rows[:10000]
    if len(all_rows) <= 20:
        shown = all_rows
        note = f"\n({total} rows returned; all shown; all stored for run_python and make_chart)"
    else:
        shown = all_rows[:15] + [tuple("..." for _ in cols)] + all_rows[-5:]
        note = (
            f"\n({total} rows returned; preview shows the first 15 and last 5; "
            "all rows are stored for run_python and make_chart)"
        )
    lines = ["\t".join(cols)] + ["\t".join(str(v) for v in r) for r in shown]
    return "\n".join(lines) + note


SAFE_NAMES = [
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "int", "len",
    "list", "map", "max", "min", "print", "range", "reversed", "round", "set", "sorted",
    "str", "sum", "tuple", "zip",
]
SAFE_BUILTINS = {n: getattr(builtins, n) for n in SAFE_NAMES}
BLOCKED_PY = re.compile(
    r"(__|\bimport\b|\bopen\b|\bexec\b|\beval\b|\bcompile\b|\bglobals\b|\blocals\b"
    r"|\bgetattr\b|\bsetattr\b|\binput\b|\bos\b|\bsys\b|\bsubprocess\b)"
)


@tool
def run_python(code: str) -> str:
    """Analyze the most recent SQL result with pandas. The data is a DataFrame named df
    (pd and np are available). Do not import anything. Put your final answer in a variable
    named result. Example: result = df['price'].describe()"""
    df = STATE["df"]
    if df is None:
        return "ERROR: run a SQL query first."
    if BLOCKED_PY.search(code):
        return "ERROR: that code is not allowed (no imports, file access, or double-underscore names)."
    scope = {"__builtins__": SAFE_BUILTINS, "pd": pd, "np": np, "df": df.copy()}
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            exec(code, scope)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
    result = scope.get("result")
    printed = buffer.getvalue().strip()
    text = (str(result) if result is not None else "") + ("\n" + printed if printed else "")
    return text.strip()[:3000] or "ERROR: no result. Assign your answer to a variable named result."


@tool
def make_chart(chart_type: str, x: str, y: str, title: str) -> str:
    """Make a chart from the most recent SQL result and save it as a PNG.
    chart_type must be 'bar', 'barh' (horizontal bars), or 'line'.
    x and y must be exact column names from that result; y must be numeric."""
    df = STATE["df"]
    if df is None:
        return "ERROR: run a SQL query first."
    if chart_type not in ("bar", "barh", "line"):
        return "ERROR: chart_type must be 'bar', 'barh', or 'line'."
    if x not in df.columns or y not in df.columns:
        return f"ERROR: x and y must be column names from the last query: {list(df.columns)}"

    data = df[[x, y]].copy()
    data[y] = pd.to_numeric(data[y], errors="coerce")
    data = data.dropna().head(30)
    if data.empty:
        return "ERROR: no numeric data to plot."

    fig, ax = plt.subplots(figsize=(9, 5))
    labels = data[x].astype(str)
    if chart_type == "bar":
        ax.bar(labels, data[y])
        plt.xticks(rotation=45, ha="right")
        ax.set_xlabel(x)
        ax.set_ylabel(y)
    elif chart_type == "barh":
        ax.barh(labels, data[y])
        ax.invert_yaxis()
        ax.set_xlabel(y)
        ax.set_ylabel(x)
    else:
        ax.plot(labels, data[y], marker="o")
        plt.xticks(rotation=45, ha="right")
        ax.set_xlabel(x)
        ax.set_ylabel(y)
    ax.set_title(title)
    fig.tight_layout()

    os.makedirs("charts", exist_ok=True)
    path = f"charts/chart_{datetime.now():%Y%m%d_%H%M%S}.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return f"Chart saved to {path}"