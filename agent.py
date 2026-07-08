from langgraph.graph import StateGraph, END

from state import AgentState
from router_node import router_node
from rag_node import rag_node
from sql_node import sql_node
from answer_node import answer_node


# --------------------------
# Routing Function
# --------------------------
def route_question(state: AgentState):

    return state["route"]


# --------------------------
# Build Graph
# --------------------------
builder = StateGraph(AgentState)

# Nodes
builder.add_node("router", router_node)
builder.add_node("rag", rag_node)
builder.add_node("sql", sql_node)
builder.add_node("answer", answer_node)

# Entry Point
builder.set_entry_point("router")

# Conditional Routing
builder.add_conditional_edges(
    "router",
    route_question,
    {
        "rag": "rag",
        "sql": "sql",
        "both": "rag",   # SQL will be called afterwards
        "chat": "answer"
    }
)

# Edges
builder.add_edge("rag", "sql")
builder.add_edge("sql", "answer")
builder.add_edge("answer", END)

# Compile
graph = builder.compile()


# --------------------------
# Test
# --------------------------
if __name__ == "__main__":

    result = graph.invoke(
        {
            "question": "What is the Transcend Platform?"
        }
    )

    print(result["answer"])