import re
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

DB_PATH = "programs.db"

SCHEMA = """
Table: programs
Columns:
  - filename (TEXT): source file name
  - title (TEXT): program name, e.g. 'Computer Science'
  - college (TEXT): one of 'Arts and Science', 'Engineering',
      'Agriculture and Bioresources', 'Education', 'Edwards School of Business',
      'Dentistry', 'Pharmacy and Nutrition', 'Medicine', 'Veterinary Medicine',
      'Nursing', 'Law', 'Kinesiology', 'School of Environment and Sustainability',
      'Graduate and Postdoctoral Studies'
  - level (TEXT): 'Undergraduate' or 'Graduate'
  - url (TEXT): link to the program page
"""

def generate_sql(question):
    """LLM CALL #1: turn the question into a single SQL SELECT statement."""
    prompt = f"""You are a SQL expert. Given this SQLite schema:
{SCHEMA}

Write ONE SQLite SELECT query that answers the question.
Rules:
- Only a SELECT statement. Never INSERT/UPDATE/DELETE/DROP.
- Return ONLY the SQL, no explanation, no markdown fences.

Question: {question}
SQL:"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    sql = resp.choices[0].message.content.strip()
    # strip accidental ```sql ``` fences if the model adds them
    sql = re.sub(r"^```(?:sql)?|```$", "", sql, flags=re.IGNORECASE).strip()
    return sql


# Validate the SQL query to ensure it only contains a single SELECT statement
def is_safe_select(sql):
    """GUARDRAIL: allow only a single read-only SELECT."""
    lowered = sql.lower().strip()
    if not lowered.startswith("select"):
        return False
    # block dangerous keywords even if they appear mid-string
    forbidden = ["insert", "update", "delete", "drop", "alter",
                 "create", "attach", "pragma", ";--", ";"]
    # allow a single trailing semicolon only
    if lowered.count(";") > 1 or (";" in lowered and not lowered.rstrip().endswith(";")):
        return False
    for word in forbidden:
        if word == ";":
            continue
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return False
    return True


def run_sql(sql):
    """Run the SELECT on a read-only connection, return rows."""
    # read-only: open in immutable/RO mode so writes are impossible
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()


def phrase_answer(question, sql, rows):
    """LLM CALL #2: turn raw rows into a natural-language answer."""
    prompt = f"""The user asked: "{question}"
We ran this SQL: {sql}
The result rows were: {rows}

Write a concise, natural answer to the user's question based on these results.
If the result is a count, state the number clearly. If it's a list, list the items."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

def answer_from_metadata(question):
    """Full SQL tool: generate SQL -> validate -> run -> phrase."""
    sql = generate_sql(question)
    if not is_safe_select(sql):
        return f"I couldn't safely answer that as a database query. (Generated: {sql})"
    try:
        rows = run_sql(sql)
    except Exception as e:
        return f"The query failed: {e}. (SQL: {sql})"
    return phrase_answer(question, sql, rows)

if __name__ == "__main__":
    for q in [
        "How many engineering programs are there?",
        "List all programs in the College of Law.",
        "How many graduate programs are there?",
        "How many programs are in Arts and Science?",
    ]:
        print("Q:", q)
        print("A:", answer_from_metadata(q))
        print("-" * 60)