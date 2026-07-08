from sql_tool import run_text2sql
from state import AgentState

def sql_node(state: AgentState):

    sql_query, sql_result = run_text2sql(
        state["question"]
    )

    state["sql_query"] = sql_query
    state["sql_result"] = sql_result

    return state