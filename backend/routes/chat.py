"""
Chat route: POST /api/chat — LLM-powered text-to-SQL pipeline.
"""
import time
from fastapi import APIRouter
from pydantic import BaseModel
from llm import generate_response
from logger import log_chat_query, get_recent_logs

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


@router.post("/chat")
async def chat(request: ChatRequest):
    """Process a chat message through the text-to-SQL pipeline."""
    start_time = time.time()
    
    history_dicts = [{"role": m.role, "content": m.content} for m in request.history]
    
    result = await generate_response(request.message, history_dicts)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Log the query
    log_chat_query(
        query=request.message,
        sql_generated=result.get("sql"),
        rows_returned=result.get("rows_returned", 0),
        latency_ms=latency_ms,
        in_domain=result.get("in_domain", False),
        answer=result.get("answer", "")
    )
    
    return {
        "answer": result["answer"],
        "sql": result.get("sql"),
        "nodes_referenced": result.get("nodes_referenced", []),
        "in_domain": result.get("in_domain", True),
        "latency_ms": round(latency_ms, 2)
    }


@router.get("/debug/logs")
async def get_debug_logs():
    """Return recent query logs for debug panel."""
    return {"logs": get_recent_logs(20)}


@router.get("/debug/summary")
async def get_debug_summary():
    """Return data summary stats for debug panel."""
    from db import get_all_table_counts
    from validator import get_validation_summary
    
    summary = get_validation_summary()
    return {
        "table_counts": summary["table_counts"],
        "total_nodes": summary["total_nodes"],
        "broken_flows_count": summary["broken_flows_count"],
        "reason_summary": summary["reason_summary"]
    }
