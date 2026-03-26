"""
Structured logging: JSON console output + file logging to logs/queries.log
"""
import json
import os
import logging
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "queries.log")

os.makedirs(LOG_DIR, exist_ok=True)

# File logger
file_logger = logging.getLogger("query_file_logger")
file_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(message)s"))
file_logger.addHandler(file_handler)
file_logger.propagate = False

# Console logger
console_logger = logging.getLogger("query_console_logger")
console_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(message)s"))
console_logger.addHandler(console_handler)
console_logger.propagate = False


def _log_json(data: dict):
    """Log a JSON object to both console and file."""
    json_str = json.dumps(data, default=str)
    console_logger.info(json_str)
    file_logger.info(json_str)


def log_chat_query(
    query: str,
    sql_generated: str | None,
    rows_returned: int,
    latency_ms: float,
    in_domain: bool,
    answer: str = ""
):
    """Log a chat query with full details."""
    _log_json({
        "event": "chat_query",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "sql_generated": sql_generated,
        "rows_returned": rows_returned,
        "latency_ms": round(latency_ms, 2),
        "in_domain": in_domain,
        "answer_preview": answer[:200] if answer else ""
    })


def log_startup_summary(summary: dict):
    """Log data summary on startup."""
    _log_json({
        "event": "startup_summary",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "table_counts": summary.get("table_counts", {}),
        "total_nodes": summary.get("total_nodes", 0),
        "broken_flows_count": summary.get("broken_flows_count", 0),
        "reason_summary": summary.get("reason_summary", {})
    })


def log_error(message: str, details: dict = None):
    """Log an error event."""
    _log_json({
        "event": "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "details": details or {}
    })


def get_recent_logs(n: int = 20) -> list[dict]:
    """Read the last n chat query log entries."""
    if not os.path.exists(LOG_FILE):
        return []
    
    entries = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("event") == "chat_query":
                    entries.append(entry)
            except json.JSONDecodeError:
                continue
    
    return entries[-n:]
