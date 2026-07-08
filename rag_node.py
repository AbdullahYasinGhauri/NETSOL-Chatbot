from retriever import retrieve_context
from state import AgentState


def rag_node(state: AgentState):

    docs, context = retrieve_context(
        state["question"]
    )

    state["retrieved_docs"] = docs
    state["context"] = context

    return state