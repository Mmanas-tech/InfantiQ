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


def _local_insights_answer(question: str, context: dict[str, Any]) -> str:
    prediction = str(context.get("prediction") or "").strip().lower()
    confidence = context.get("confidence")
    recommendation = str(context.get("recommendation") or "").strip()

    opening = "Based on the current cry analysis"
    if prediction:
        opening += f" ({prediction.replace('_', ' ')})"
    if isinstance(confidence, (int, float)):
        opening += f" with confidence {round(float(confidence) * 100)}%"
    opening += ", here is a practical plan:"

    generic_steps = [
        "Check immediate comfort needs first: diaper, temperature, clothing, and position.",
        "Try a 5-10 minute calming sequence: hold upright, gentle rocking, and low-stimulation environment.",
        "Track timing between feeding, sleep, and crying to identify repeatable patterns.",
        "If crying is persistent, unusual, or accompanied by fever/breathing concerns, contact a pediatrician promptly.",
    ]

    class_specific = {
        "hungry": "Offer feeding if the last feed was more than 2 hours ago, then burp and reassess.",
        "tired": "Reduce noise/light and start a consistent sleep routine (swaddle, rock, white noise).",
        "burping": "Hold baby upright and burp for a few minutes before laying down.",
        "discomfort": "Check for wet diaper, tight clothing, gas discomfort, and room temperature.",
        "belly_pain": "Try tummy comfort strategies: upright hold, gentle circular tummy massage, and bicycle legs.",
    }

    steps = []
    if prediction in class_specific:
        steps.append(class_specific[prediction])
    if recommendation:
        steps.append(recommendation)
    steps.extend(generic_steps)

    user_focus = question.strip()
    if user_focus:
        steps.append(f"For your question ('{user_focus}'), start with the first two steps now and reassess in 10-15 minutes.")

    return opening + "\n- " + "\n- ".join(steps)


def ask_insights(question: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    context = context or {}

    if not api_key:
        return {
            "answer": _local_insights_answer(question, context),
            "model": "local-fallback",
        }

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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
        return {
            "answer": _local_insights_answer(question, context),
            "model": "local-fallback",
        }

    if response.status_code >= 400:
        return {
            "answer": _local_insights_answer(question, context),
            "model": "local-fallback",
        }

    data = response.json()
    content = ""
    try:
        content = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # pragma: no cover
        return {
            "answer": _local_insights_answer(question, context),
            "model": "local-fallback",
        }

    return {
        "answer": content,
        "model": model,
    }
