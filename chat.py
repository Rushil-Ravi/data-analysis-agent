from agent import app

while True:
    q = input("\nQuestion (or 'quit'): ")
    if q.strip().lower() == "quit":
        break
    for step in app.stream({"messages": [("user", q)]}, stream_mode="values"):
        step["messages"][-1].pretty_print()