from state import AgentState
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("api_key")
client = genai.Client(api_key=api_key)

MODEL = "gemini-2.5-flash-lite"


def router_node(state: AgentState):

    prompt = f"""
You are a routing agent.

Choose ONLY one of these words:

rag
sql
both
chat

Examples:
What is Transcend? -> rag
Who has the highest salary? -> sql
Which employees work on Transcend? -> both
Hello -> chat

Question:
{state["question"]}

Return ONLY one word.
"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    
    state["route"] = response.text.strip().lower()
    print(f"Route: {state['route']}")
    return state