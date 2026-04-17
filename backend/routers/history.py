from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from services.db_service import get_analyses_for_baby, get_recent_analyses
from services.intelligence_service import build_timeline

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


@router.get("/history/{baby_id}")
async def baby_history(
    baby_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    days: int = Query(default=14, ge=1, le=90),
) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    items = await get_analyses_for_baby(baby_id=baby_id, limit=limit, since=since)
    return [
        {
            "prediction": item.get("prediction"),
            "confidence": item.get("confidence"),
            "timestamp": item.get("timestamp"),
            "analysis_id": item.get("analysis_id"),
            "recommendation": item.get("recommendation"),
            "baby_id": item.get("baby_id"),
        }
        for item in items
    ]


@router.get("/timeline")
async def timeline(
    baby_id: str = Query(..., min_length=1),
    days: int = Query(default=7, ge=1, le=30),
) -> dict:
    since = datetime.utcnow() - timedelta(days=days)
    items = await get_analyses_for_baby(baby_id=baby_id, limit=2000, since=since)
    return build_timeline(items, days=days)
