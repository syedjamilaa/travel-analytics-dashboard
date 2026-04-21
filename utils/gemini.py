from google import genai
import pandas as pd
import os
import re
from dotenv import load_dotenv
from utils.db import SCHEMA_DESCRIPTION, run_query

load_dotenv()

# ── Configure Gemini (your working pattern) ──────────
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL  = "gemini-3.1-pro-preview"  # or gemini-2.0-flash for speed


def _call_gemini(prompt: str) -> str:
    """Single reusable wrapper for all Gemini calls."""
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    return response.text.strip()


# ════════════════════════════════════════════════════
# FUNCTION 1: Natural Language → SQL
# ════════════════════════════════════════════════════

def natural_language_to_sql(user_question: str) -> str:
    prompt = f"""
{SCHEMA_DESCRIPTION}

Convert this business question into a single valid SQLite SQL query:

QUESTION: {user_question}

RULES:
- Return ONLY the raw SQL query
- No markdown, no backticks, no explanation
- No triple quotes or code fences
- End the query with a semicolon
- Use only tables and columns defined in the schema above
"""
    raw = _call_gemini(prompt)

    # Belt-and-suspenders cleaning (in case of any fence)
    clean = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    clean = re.sub(r"```", "", clean).strip()

    # Extract from SELECT onward
    match = re.search(r"(SELECT\s.+)", clean, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else clean


# ════════════════════════════════════════════════════
# FUNCTION 2: Generate Business Insight
# ════════════════════════════════════════════════════

def generate_insight(
    user_question: str,
    sql_query: str,
    df: pd.DataFrame
) -> str:
    data_preview = df.head(10).to_string(index=False)

    prompt = f"""
You are a Senior Data Analyst at a travel company like Expedia.

A business user asked: "{user_question}"

The SQL query used was:
{sql_query}

The results returned were:
{data_preview}

Write a SHORT (3–4 sentences) business insight based on this data.

RULES:
- Write for a non-technical business audience (no SQL jargon)
- Mention specific numbers or percentages from the data
- End with ONE actionable recommendation
- Be direct and confident, not vague
- Do NOT say "the data shows" or "based on the results"
- Start directly with the insight
"""
    return _call_gemini(prompt)


# ════════════════════════════════════════════════════
# FUNCTION 3: Validate SQL Safety
# ════════════════════════════════════════════════════

def is_safe_sql(sql: str) -> bool:
    sql_upper = sql.strip().upper()
    dangerous  = ["DROP","DELETE","INSERT","UPDATE",
                  "ALTER","CREATE","TRUNCATE","REPLACE"]

    if "SELECT" not in sql_upper:
        return False
    for kw in dangerous:
        if kw in sql_upper:
            return False
    return True


# ════════════════════════════════════════════════════
# COMBINED PIPELINE: Question → SQL → Data → Insight
# ════════════════════════════════════════════════════

def run_ai_pipeline(user_question: str) -> dict:
    result = {
        "sql":       None,
        "dataframe": None,
        "insight":   None,
        "error":     None
    }

    # Step 1: Generate SQL
    sql = natural_language_to_sql(user_question)
    result["sql"] = sql

    # Step 2: Safety check
    if not is_safe_sql(sql):
        result["error"] = "⚠️ Could not generate a safe SELECT query. Please rephrase."
        return result

    # Step 3: Run query
    df = run_query(sql)
    if "error" in df.columns:
        result["error"] = f"⚠️ SQL Error: {df['error'][0]}"
        return result

    if df.empty:
        result["error"] = "⚠️ Query returned no results. Try rephrasing."
        return result

    result["dataframe"] = df

    # Step 4: Generate insight
    result["insight"] = generate_insight(user_question, sql, df)

    return result