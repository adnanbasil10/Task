"""
LLM module: Groq API integration (Llama model) for text-to-SQL pipeline.
"""
import os
import re
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# In-domain keywords
DOMAIN_KEYWORDS = [
    "order", "delivery", "invoice", "payment", "customer", "product",
    "billing", "shipment", "material", "vendor", "plant", "flow",
    "document", "sales", "address", "amount", "total", "price",
    "tracking", "sku", "quantity", "item",
    "revenue", "pending", "overdue", "paid", "shipped", "cancelled",
    "supply", "chain", "erp", "broken"
]

SYSTEM_PROMPT = """You are a data analyst assistant for an ERP supply chain dataset.
You ONLY answer questions about: Orders, Deliveries, Invoices, Payments,
Customers, Products, and Addresses in this dataset.

If asked anything outside this domain, respond exactly with:
"This system is designed to answer questions related to the provided dataset only."

For valid questions:
1. Write a SQLite-compatible SQL query to retrieve the answer
2. Wrap it in <SQL></SQL> tags
3. After seeing results, write a clear natural language answer
4. If referencing specific entity IDs, list them as <NODES>id1,id2</NODES>

Rules:
- Only SELECT statements. Never INSERT, UPDATE, DELETE, DROP.
- If the SQL returns no rows, say so clearly.
- Be concise. No hallucination. Only what the data shows.
"""

OUT_OF_DOMAIN_MSG = "This system is designed to answer questions related to the provided dataset only."


def is_in_domain(message: str) -> bool:
    """Check if the user message is in-domain based on keyword matching."""
    msg_lower = message.lower()
    return any(keyword in msg_lower for keyword in DOMAIN_KEYWORDS)


def build_schema_context() -> str:
    """Build schema + sample data context for the LLM prompt."""
    from db import get_schema_ddl, get_sample_rows, TABLE_CSV_MAP

    context = "=== DATABASE SCHEMA ===\n"
    context += get_schema_ddl()
    context += "\n\n=== SAMPLE DATA ===\n"

    for table, _ in TABLE_CSV_MAP:
        try:
            samples = get_sample_rows(table, limit=3)
            if samples:
                context += f"\n-- {table} (sample rows):\n"
                for row in samples:
                    context += f"  {dict(row)}\n"
        except Exception:
            pass

    return context


def extract_sql(text: str) -> str | None:
    """Extract SQL from <SQL></SQL> tags in LLM response."""
    match = re.search(r"<SQL>(.*?)</SQL>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_nodes(text: str) -> list[str]:
    """Extract node IDs from <NODES></NODES> tags in LLM response."""
    match = re.search(r"<NODES>(.*?)</NODES>", text, re.DOTALL | re.IGNORECASE)
    if match:
        ids = match.group(1).strip()
        return [nid.strip() for nid in ids.split(",") if nid.strip()]
    return []


def _extract_entity_ids_from_results(results: list[dict]) -> list[str]:
    """Extract entity IDs from SQL query results."""
    ids = set()
    id_pattern = re.compile(r"^(ORD|DEL|INV|PAY|CUST|PROD|ADDR|OI|II)-\d+$")

    for row in results:
        for value in row.values():
            if isinstance(value, str) and id_pattern.match(value):
                ids.add(value)

    return list(ids)


def _call_groq(messages: list[dict], temperature: float = 0.1) -> str:
    """Make a synchronous call to Groq API."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(GROQ_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content


async def generate_response(message: str, history: list[dict] = None) -> dict:
    """
    Full text-to-SQL pipeline:
    1. Check domain
    2. Generate SQL via Groq
    3. Execute SQL
    4. Generate NL answer via Groq
    """
    from db import execute_readonly

    # Step 1: Domain check
    if not is_in_domain(message):
        return {
            "answer": OUT_OF_DOMAIN_MSG,
            "sql": None,
            "nodes_referenced": [],
            "in_domain": False,
            "rows_returned": 0
        }

    # Check API key
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return {
            "answer": "⚠️ Groq API key not configured. Please set GROQ_API_KEY in backend/.env",
            "sql": None,
            "nodes_referenced": [],
            "in_domain": True,
            "rows_returned": 0
        }

    schema_context = build_schema_context()

    # Step 2: Generate SQL
    sql_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""{schema_context}

User question: {message}

Generate a SQLite-compatible SQL query to answer this question. Wrap it in <SQL></SQL> tags. Do NOT use markdown code blocks. Only use <SQL></SQL> tags."""}
    ]

    # Add recent history for context
    if history:
        for h in history[-4:]:
            sql_messages.insert(-1, {"role": h.get("role", "user"), "content": h.get("content", "")})

    try:
        sql_query = None
        rows_returned = 0
        results = []
        
        # Self-correction loop: try up to 2 times
        for attempt in range(2):
            sql_text = _call_groq(sql_messages)
            sql_query = extract_sql(sql_text)
            
            if not sql_query:
                # Try to find SQL in code blocks as fallback
                code_match = re.search(r"```sql\s*(.*?)\s*```", sql_text, re.DOTALL | re.IGNORECASE)
                if code_match:
                    sql_query = code_match.group(1).strip()
                    
            if not sql_query:
                return {
                    "answer": "I couldn't generate a valid SQL query for that question. Could you rephrase it?",
                    "sql": None,
                    "nodes_referenced": [],
                    "in_domain": True,
                    "rows_returned": 0
                }

            # Execute SQL safely
            try:
                results = execute_readonly(sql_query)
                rows_returned = len(results)
                break  # Execution succeeded, break out of retry loop
                
            except ValueError as e:
                return {
                    "answer": f"The generated query was blocked for safety: {str(e)}",
                    "sql": sql_query,
                    "nodes_referenced": [],
                    "in_domain": True,
                    "rows_returned": 0
                }
            except Exception as e:
                # If it's the first attempt and an operational error occurs, ask the LLM to fix it
                if attempt == 0:
                    sql_messages.append({"role": "assistant", "content": sql_text})
                    sql_messages.append({"role": "user", "content": f"Your SQL query failed with this error: {str(e)}. Look closely at the exact database schema and correct the SQL query. Remember that order_items joins orders and products, and invoice_items joins invoices. Output ONLY the corrected SQL wrapped in <SQL></SQL> tags."})
                    continue
                else:
                    return {
                        "answer": f"SQL execution error: {str(e)} \n*(Auto-recovery failed after 2 attempts)*",
                        "sql": sql_query,
                        "nodes_referenced": [],
                        "in_domain": True,
                        "rows_returned": 0
                    }

        # Step 4: Generate NL answer
        display_results = results[:50] if len(results) > 50 else results

        answer_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""The SQL query:
{sql_query}

Returned {rows_returned} rows. Here are the results:
{json.dumps(display_results, default=str)}

Based on these results, provide a clear, concise natural language answer to the original question: "{message}"

If you reference specific entity IDs (like ORD-001, CUST-005, etc.), list them as <NODES>id1,id2</NODES>. Do not use markdown code blocks."""}
        ]

        answer_text = _call_groq(answer_messages)

        # Extract node references
        nodes = extract_nodes(answer_text)
        if not nodes:
            nodes = _extract_entity_ids_from_results(results[:20])

        # Clean answer text (remove tags)
        clean_answer = re.sub(r"<SQL>.*?</SQL>", "", answer_text, flags=re.DOTALL).strip()
        clean_answer = re.sub(r"<NODES>.*?</NODES>", "", clean_answer, flags=re.DOTALL).strip()

        return {
            "answer": clean_answer,
            "sql": sql_query,
            "nodes_referenced": nodes,
            "in_domain": True,
            "rows_returned": rows_returned
        }

    except httpx.HTTPStatusError as e:
        return {
            "answer": f"API error: {e.response.status_code} — {e.response.text[:200]}",
            "sql": None,
            "nodes_referenced": [],
            "in_domain": True,
            "rows_returned": 0
        }
    except Exception as e:
        return {
            "answer": f"Error communicating with LLM: {str(e)}",
            "sql": None,
            "nodes_referenced": [],
            "in_domain": True,
            "rows_returned": 0
        }
