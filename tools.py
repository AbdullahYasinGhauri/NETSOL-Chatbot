from retriever import retrieve_context
from sql_tool import run_text2sql


def rag_tool(question: str):

    _, context = retrieve_context(question)

    return context


def sql_tool(question: str):

    sql_query, sql_result = run_text2sql(question)

    return {
        "sql": sql_query,
        "result": sql_result
    }