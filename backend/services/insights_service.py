from __future__ import annotations

from typing import Any

def _format_confidence(confidence: Any) -> str:
    try:
        value = float(confidence)
    except (TypeError, ValueError):
        return ""
    return f"{round(value * 100)}%"


def _local_insights_answer(question: str, context: dict[str, Any]) -> str:
    prediction = str(context.get("prediction") or "").strip().lower()
    confidence = _format_confidence(context.get("confidence"))
    recommendation = str(context.get("recommendation") or "").strip()

    opening = "Based on the current cry analysis"
    if prediction:
        opening += f" ({prediction.replace('_', ' ')})"
    if confidence:
        opening += f" with confidence {confidence}"
    opening += ", here is a practical plan:"

    class_specific = {
        "hungry": "Offer feeding if the last feed was more than 2 hours ago, then burp and reassess.",
        "tired": "Reduce noise/light and begin a consistent sleep routine (swaddle, rock, white noise).",
        "burping": "Hold baby upright and burp for a few minutes before laying down.",
        "discomfort": "Check diaper, clothing tightness, gas discomfort, and room temperature.",
        "belly_pain": "Try tummy comfort steps: upright hold, gentle circular tummy massage, and bicycle legs.",
    }

    generic_steps = [
        "Check immediate comfort needs first: diaper, temperature, clothing, and position.",
        "Try a short calming sequence: hold upright, gentle rocking, and low-stimulation environment.",
        "Track feeding, sleep, and crying timing to identify repeatable patterns.",
        "If crying is persistent, unusual, or includes fever/breathing concerns, contact a pediatrician promptly.",
    ]

    steps: list[str] = []
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
    context = context or {}
    return {
        "answer": _local_insights_answer(question=question, context=context),
        "model": "local-offline",
    }
