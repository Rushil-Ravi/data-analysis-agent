from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from groq import BadRequestError

from tools import run_sql, run_python, make_chart, get_schema
from retriever import retrieve_context

load_dotenv()
MODEL = "openai/gpt-oss-120b"
MAX_RETRIES = 2  # after the first failed attempt, the agent may retry twice

SYSTEM_PROMPT = """You are a careful data analyst assistant for an e-commerce SQLite database.

Database schema:
{schema}

Business definitions (always follow these when they apply):
{context}

Tools:
- run_sql: get data with a read-only SELECT (SQLite SQL; use julianday() for date differences).
- run_python: analyze the result of the most recent run_sql with pandas. The data is a DataFrame named df. Do not import anything. Put the answer in a variable named result.
- make_chart: draw a chart from the most recent run_sql result. Use it only when the user asks for a chart, plot, or visual. The SQL result must have exactly the columns you pass as x and y.

Rules:
- Call one tool at a time and wait for its result before calling the next.
- If a tool returns an ERROR, read the message, fix the problem, and try again.
- Never guess numbers. Base your answer only on tool results.
- You only see a preview of large results. Do not describe rows you have not seen; use run_python for exact numbers such as min, max, or counts.
- Compute counts, sums, ratios, and percentages directly inside the SQL query, for example ROUND(100.0 * SUM(CASE WHEN ... THEN 1 ELSE 0 END) / COUNT(*), 2). Use run_python only when SQL cannot do it.
- Use plain text for math; do not use LaTeX.
- If the schema cannot answer the question, say so instead of guessing.
- Mention which definition you used. If you made a chart, give its file path."""


class AgentState(MessagesState):
    context: str
    errors: int


tools = [run_sql, run_python, make_chart]
tool_node = ToolNode(tools)
llm_with_tools = ChatGroq(model=MODEL, temperature=0).bind_tools(tools)


def retrieve(state: AgentState):
    question = state["messages"][-1].content
    return {"context": retrieve_context(question)}


def agent(state: AgentState):
    system = SystemMessage(
        content=SYSTEM_PROMPT.format(schema=get_schema(), context=state["context"])
    )
    nudge = HumanMessage(
        content="Your last reply was malformed. Either call a tool with valid "
        "arguments or answer in plain text."
    )
    for attempt in range(3):
        extra = [nudge] if attempt > 0 else []
        try:
            response = llm_with_tools.invoke([system] + state["messages"] + extra)
            return {"messages": [response]}
        except BadRequestError:
            continue  # the model produced unparseable output; try again with a nudge
    return {
        "messages": [
            AIMessage(
                content="The model returned an unusable response several times in a row. "
                "Please try rephrasing the question."
            )
        ]
    }

def run_tools(state: AgentState):
    result = tool_node.invoke(state)
    errors = state.get("errors", 0)
    if any(str(m.content).startswith("ERROR") for m in result["messages"]):
        errors += 1
    else:
        errors = 0  # a successful tool call resets the counter
    return {**result, "errors": errors}


def after_tools(state: AgentState):
    return "give_up" if state.get("errors", 0) > MAX_RETRIES else "agent"


def give_up(state: AgentState):
    last_error = state["messages"][-1].content
    msg = (
        f"I couldn't get a working result after {MAX_RETRIES + 1} attempts, "
        f"so I'm stopping here. Last error: {last_error}"
    )
    return {"messages": [AIMessage(content=msg)]}


graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve)
graph.add_node("agent", agent)
graph.add_node("tools", run_tools)
graph.add_node("give_up", give_up)

graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "agent")
graph.add_conditional_edges("agent", tools_condition)  # goes to "tools" or ends
graph.add_conditional_edges("tools", after_tools, {"agent": "agent", "give_up": "give_up"})
graph.add_edge("give_up", END)

app = graph.compile()