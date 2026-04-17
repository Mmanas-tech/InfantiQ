from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from services.insights_service import ask_insights

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.post("/ask")
async def ask_insights_route(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail={"error": "Invalid request", "detail": "question is required"})

    context = payload.get("context", {})
    return ask_insights(question=question, context=context)
