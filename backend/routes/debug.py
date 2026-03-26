from fastapi import APIRouter, Request
from logger import get_recent_logs

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/summary")
async def get_debug_summary(request: Request):
    """Return the database summary calculated at startup."""
    summary = getattr(request.app.state, "data_summary", {})
    return summary

@router.get("/logs")
async def get_debug_logs():
    """Return recent chat query logs with latency and SQL generated."""
    logs = get_recent_logs(n=20)
    return {"logs": logs}
