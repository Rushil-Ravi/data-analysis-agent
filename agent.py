from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from tools import run_sql, get_schema
from retriever import retrieve_context

load_dotenv()
MODEL = "openai/gpt-oss-safeguard-20b"

SYSTEM_PROMPT = """You are a careful data analyst assistant for an e-commerce SQLite database.

Database schema:
{schema}

Business definitions (always follow these when they apply):
{context}

Rules:
- Use the run_sql tool to get data. Write standard SQLite SQL (use julianday() for date differences).
- Only SELECT queries are allowed. If a query returns an ERROR, read the message, fix the query, and try again.
- Never guess numbers. Base your answer only on tool results.
- Answer clearly and mention which definition you used."""


class AgentState(MessagesState):
    context: str


tools = [run_sql]
llm_with_tools = ChatGroq(model=MODEL, temperature=0).bind_tools(tools)


def retrieve(state: AgentState):
    question = state["messages"][-1].content
    return {"context": retrieve_context(question)}


def agent(state: AgentState):
    system = SystemMessage(
        content=SYSTEM_PROMPT.format(schema=get_schema(), context=state["context"])
    )
    response = llm_with_tools.invoke([system] + state["messages"])
    return {"messages": [response]}


graph = StateGraph(AgentState)
graph.add_node("retrieve", retrieve)
graph.add_node("agent", agent)
graph.add_node("tools", ToolNode(tools))
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "agent")
graph.add_conditional_edges("agent", tools_condition)  # goes to "tools" or ends
graph.add_edge("tools", "agent")  # the loop: after tools, the agent reads the result

app = graph.compile()