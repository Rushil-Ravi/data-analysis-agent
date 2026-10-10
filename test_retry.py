import tools
from agent import app


def always_fail(query: str) -> str:
    return "ERROR: simulated database failure"


tools.run_sql.func = always_fail

state = {"messages": [("user", "How many orders are there?")], "errors": 0}
for step in app.stream(state, stream_mode="values"):
    step["messages"][-1].pretty_print()