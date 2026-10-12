import re

import streamlit as st

from agent import app as graph, MODEL

st.set_page_config(page_title="Data Analysis Assistant", layout="wide")
st.title("Agentic AI Data Analysis Assistant")
st.caption("Ask questions about the e-commerce database. The agent writes SQL, "
           "analyzes the results, and draws charts.")

with st.sidebar:
    st.subheader("Try asking")
    st.markdown(
        "- What percent of delivered orders were late?\n"
        "- Top 5 product categories by revenue\n"
        "- Plot monthly revenue\n"
        "- How many repeat customers are there?\n"
        "- Show a bar chart of orders by customer state"
    )
    st.caption(f"Model: {MODEL}")
    st.caption("Data: Olist Brazilian e-commerce dataset (public)")

if "history" not in st.session_state:
    st.session_state.history = []


def show_steps(steps):
    with st.expander("How the agent got this answer"):
        for s in steps:
            st.code(s, language="sql" if s.startswith("SQL") else None)


def run_agent(question):
    state = {"messages": [("user", question)], "errors": 0}
    final = None
    for step in graph.stream(state, stream_mode="values"):
        final = step
    msgs = final["messages"]
    steps, charts = [], []
    for m in msgs[1:]:
        if m.type == "ai" and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                args = tc["args"]
                if tc["name"] == "run_sql":
                    steps.append("SQL\n" + str(args.get("query", args)))
                else:
                    steps.append(f"TOOL {tc['name']}\n{args}")
        elif m.type == "tool":
            text = str(m.content)
            steps.append("RESULT\n" + text[:800])
            charts.extend(re.findall(r"Chart saved to (\S+\.png)", text))
    content = msgs[-1].content
    answer = content if isinstance(content, str) else str(content)
    answer = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", answer).strip()  # images are shown separately
    return answer, steps, charts


for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        for path in m.get("charts", []):
            st.image(path)
        if m.get("steps"):
            show_steps(m["steps"])

question = st.chat_input("Ask a question about the data...")
if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                answer, steps, charts = run_agent(question)
            except Exception as e:
                answer, steps, charts = f"Sorry, something went wrong: {e}", [], []
        st.markdown(answer)
        for path in charts:
            st.image(path)
        if steps:
            show_steps(steps)
    st.session_state.history.append(
        {"role": "assistant", "content": answer, "steps": steps, "charts": charts}
    )