from mcp_client import invoke_tool

print(
    invoke_tool(
        "retrieve_context",
        question="What is Transcend Platform?"
    )
)

print(
    invoke_tool(
        "query_employee_database",
        question="Who is the highest paid employee?"
    )
)