from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import HTTPException

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def _build_system_prompt() -> str:
    return (
        "You are InfantiQ Insights Assistant. "
        "You help parents interpret baby-cry analysis outputs with practical, non-diagnostic advice. "
        "Do not claim medical diagnosis. Recommend pediatric consultation for emergencies or persistent distress. "
        "Keep responses concise, clear, and action-oriented."
    )


def ask_insights(question: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail={"error": "Insights unavailable", "detail": "GROQ_API_KEY is not configured"})

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    context = context or {}
    prediction = context.get("prediction")
    confidence = context.get("confidence")
    recommendation = context.get("recommendation")
    baby_id = context.get("baby_id")

    context_text = (
        f"analysis_context: prediction={prediction}, confidence={confidence}, recommendation={recommendation}, baby_id={baby_id}"
    )

    payload = {
        "model": model,
        "temperature": 0.3,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": f"{context_text}\n\nUser question: {question}"},
        ],
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "Insights request failed", "detail": str(exc)},
        ) from exc

    if response.status_code >= 400:
        detail = response.text
        raise HTTPException(
            status_code=502,
            detail={"error": "Insights provider error", "detail": detail[:500]},
        )

    data = response.json()
    content = ""
    try:
        content = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=502,
            detail={"error": "Invalid insights response", "detail": str(exc)},
        ) from exc

    return {
        "answer": content,
        "model": model,
    }
