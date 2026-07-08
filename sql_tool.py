import sqlite3
from google import genai
import os
import re
from dotenv import load_dotenv

load_dotenv()  
api_key=os.getenv("api_key")
client=genai.Client(api_key=api_key)

model = ("gemini-2.5-flash")

def get_schema():

    conn = sqlite3.connect("employee_profiles.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table';
    """)

    tables = cursor.fetchall()

    schema = ""

    for (table,) in tables:

        cursor.execute(f"PRAGMA table_info({table});")
        cols = cursor.fetchall()

        schema += f"\nTable: {table}\n"

        for col in cols:
            schema += f"- {col[1]} ({col[2]})\n"

    conn.close()

    return schema


def run_text2sql(question):

    schema = get_schema()

    prompt = f"""
You are an expert SQLite assistant.

Database Schema:
{schema}

Generate ONLY a valid SQLite query.

Question:
{question}

Do not explain anything.
Return ONLY SQL.
"""
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    match = re.search(r"```(?:\w+)?\n(.*?)```", response.text, re.DOTALL)

    if match:
        sql_query = match.group(1).strip()
    else:
        sql_query = response.text.strip()

    conn = sqlite3.connect("employee_profiles.db")
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
        rows = cursor.fetchall()

    except Exception as e:
        rows = f"SQL Error: {e}"

    conn.close()

    return sql_query, str(rows)

if __name__ == "__main__":

    question = "How many employees are there?"

    sql_query, result = run_text2sql(question)

    print("\nGenerated SQL:")
    print(sql_query)

    print("\nResult:")
    print(result)