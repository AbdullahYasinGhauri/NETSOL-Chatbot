from fastmcp import FastMCP

from tools import rag_tool
from tools import sql_tool

mcp = FastMCP("NETSOL Tools")


@mcp.tool()
def retrieve_context(question: str):

    """
    Retrieve relevant NETSOL website context.
    """

    return rag_tool(question)


@mcp.tool()
def query_employee_database(question: str):

    """
    Query employee database using Text2SQL.
    """

    return sql_tool(question)

if __name__ == "__main__":
    """app = mcp.http_app()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
    """
    app = mcp.http_app()

    for route in app.routes:
        print(route.path)

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)