from agent import app

while True:
    q = input("\nQuestion (or 'quit'): ")
    if q.strip().lower() == "quit":
        break
    state = {"messages": [("user", q)], "errors": 0}
    for step in app.stream(state, stream_mode="values"):
        step["messages"][-1].pretty_print()