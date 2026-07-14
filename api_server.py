import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from mcp_client import invoke_tool

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if needed
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store — resets when api_server.py restarts.
# { thread_id: {"title": str, "messages": [(sender, text), ...]} }
sessions: dict[str, dict] = {}


class ChatRequest(BaseModel):
    thread_id: str
    question: str


def make_title(question: str) -> str:
    q = question.strip()
    return q[:40] + ("..." if len(q) > 40 else "")


def extract_text(mcp_content) -> str:
    """mcp_content is the list of content blocks returned by invoke_tool()."""
    parts = []
    for block in mcp_content:
        text = getattr(block, "text", None)
        parts.append(text if text is not None else str(block))
    return "\n".join(parts)


def route_and_answer(question: str) -> str:
    q = question.lower()
    sql_keywords = ["salary", "employee", "paid", "hired", "department", "manager", "staff"]

    if any(word in q for word in sql_keywords):
        result = invoke_tool("query_employee_database", question=question)
    else:
        result = invoke_tool("retrieve_context", question=question)

    return extract_text(result)


@app.post("/new_chat")
def new_chat():
    thread_id = str(uuid.uuid4())
    sessions[thread_id] = {"title": "New chat", "messages": []}
    return {"thread_id": thread_id}


@app.get("/sessions")
def list_sessions():
    return [
        {"thread_id": tid, "title": s["title"]}
        for tid, s in sessions.items()
    ]


@app.get("/messages/{thread_id}")
def get_messages(thread_id: str):
    if thread_id not in sessions:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    return sessions[thread_id]["messages"]


@app.post("/chat")
def chat(req: ChatRequest):
    if req.thread_id not in sessions:
        sessions[req.thread_id] = {"title": "New chat", "messages": []}

    session = sessions[req.thread_id]

    if not session["messages"]:
        session["title"] = make_title(req.question)

    answer = route_and_answer(req.question)

    session["messages"].append(("user", req.question))
    session["messages"].append(("bot", answer))

    return {"answer": answer}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)