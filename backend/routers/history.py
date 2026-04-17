from __future__ import annotations

from fastapi import APIRouter

from services.db_service import get_recent_analyses

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def history() -> list[dict]:
    items = await get_recent_analyses(limit=20)
    return [
        {
            "prediction": item.get("prediction"),
            "confidence": item.get("confidence"),
            "timestamp": item.get("timestamp"),
            "analysis_id": item.get("analysis_id"),
        }
        for item in items
    ]
