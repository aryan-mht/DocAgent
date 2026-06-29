from typing import TypedDict
from langgraph.graph import StateGraph, END
from openai import OpenAI
from dotenv import load_dotenv

from app.retrieval import answer_from_docs
from app.metadata import answer_from_metadata
from app.websearch import answer_from_web

load_dotenv()
client = OpenAI()

"""
                ┌─────────────┐
                │   router    │
                │ (LLM node)  │
                └─────┬───────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
   ┌────────┐   ┌────────┐   ┌────────┐
   │ vector │   │  sql   │   │  web   │
   │ node   │   │ node   │   │ node   │
   └────┬───┘   └────┬───┘   └────┬───┘
        │            │            │
        ▼            ▼            ▼
      ┌────────────────────────────┐
      │            END             │
      └────────────────────────────┘
"""

class State(TypedDict):
    """The state of the agent at any given time."""
    question: str    # the user's question (filled at start)
    route: str       # the router's decision: VECTOR / SQL / WEB
    answer: str      # the final answer (filled by a tool node)

def router(state: State):
    """Classify the question and decide which tool to use."""
    question = state["question"]
    prompt = f"""Classify the user's question into exactly one category:

- VECTOR: asks about the CONTENT or details of a program (what it covers,
    what you study, admission requirements, careers). 
    Example: "What does the Computer Science program involve?"

- SQL: asks about COUNTS, TOTALS, LISTS, or filtering across programs
    (how many, list all, which college, undergraduate vs graduate).
    Example: "How many engineering programs are there?"

- WEB: asks about CURRENT or EXTERNAL info not in a program catalogue
    (tuition costs, application deadlines, dates, news, rankings).
    Example: "What is the tuition for international students?"

Respond with ONLY one word: VECTOR, SQL, or WEB.

Question = {question}"""
    decision = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    ).choices[0].message.content.strip().upper()

    if decision not in ("VECTOR", "SQL", "WEB"):
        decision = "VECTOR"

    return {"route": decision}


def vector_node(state: State):
    answer, _sources = answer_from_docs(state["question"])
    return {"answer": answer}

def sql_node(state: State):
    answer = answer_from_metadata(state["question"])
    return {"answer": answer}

def web_node(state: State):
    answer = answer_from_web(state["question"])
    return {"answer": answer}

def pick_route(state: State):
    """Tells the conditional edge which branch to take."""
    return state["route"] # Why separate from the router node? The router makes and stores the decision; this reports it to the edge


# Wiring the graph together
graph = StateGraph(State)
graph.add_node("router", router)
graph.add_node("vector", vector_node)
graph.add_node("sql", sql_node)
graph.add_node("web", web_node)

# entry point: every question starts at the router
graph.set_entry_point("router")

# conditional edge: from router, branch based on pick_route's return
graph.add_conditional_edges(
    "router", # after router
    pick_route, # use this function to decide which branch to take
    {
        "VECTOR": "vector", # if pick_route returns "VECTOR", go to vector_node
        "SQL": "sql", # if pick_route returns "SQL", go to sql_node
        "WEB": "web", # if pick_route returns "WEB", go to web_node
    }
)

# after any tool node, the graph ends
graph.add_edge("vector", END)
graph.add_edge("sql", END)
graph.add_edge("web", END)

# compile into a runnable graph
app_graph = graph.compile()

def run_agent(question: str):
    """Run a question through the full agent graph, return the answer."""
    result = app_graph.invoke({"question": question})
    return result["answer"]

if __name__ == "__main__":
    questions = [
        # "What does the Computer Science program involve?",   # → VECTOR
        # "How many engineering programs are there?",          # → SQL
        "What is the tuition for international students?",    # → WEB
    ]
    for q in questions:
        print("Q:", q)
        print("A:", run_agent(q))
        print("-" * 60)