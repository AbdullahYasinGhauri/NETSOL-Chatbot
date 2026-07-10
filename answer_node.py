import os
from dotenv import load_dotenv
from state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    google_api_key=os.getenv("api_key")
)

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

    print("===== CONTEXT =====")
    print(state.get("context", "")[:1000])

    print("===== SQL =====")
    print(state.get("sql_result", ""))

    return state