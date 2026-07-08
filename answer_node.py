from state import AgentState
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

def answer_node(state: AgentState):

    prompt = f"""
Answer the user's question.

Question:
{state['question']}

Website Context:
{state.get("context","")}

SQL Result:
{state.get("sql_result","")}
"""

    state["answer"] = llm.invoke(prompt).content

    return state