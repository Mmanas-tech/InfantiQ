from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

CLASSES = ["belly_pain", "burping", "discomfort", "hungry", "tired"]


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        raw = datetime.fromisoformat(value)
        return _to_utc_naive(raw)
    except ValueError:
        return None


def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _to_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return _to_utc_naive(value)
    if isinstance(value, str):
        try:
            return _to_utc_naive(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def normalize_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    probs = {c: max(0.0, float(probabilities.get(c, 0.0))) for c in CLASSES}
    total = sum(probs.values())
    if total <= 1e-8:
        uniform = 1.0 / len(CLASSES)
        return {c: uniform for c in CLASSES}
    return {c: v / total for c, v in probs.items()}


def apply_personalization(
    probabilities: dict[str, float],
    baby_history: list[dict[str, Any]],
    now: datetime,
) -> tuple[dict[str, float], dict[str, Any]]:
    base = normalize_probabilities(probabilities)
    if len(baby_history) < 8:
        return base, {
            "enabled": False,
            "reason": "Not enough history yet",
            "history_count": len(baby_history),
        }

    count_prior = {c: 1.0 for c in CLASSES}
    hour_prior = {c: 1.0 for c in CLASSES}

    for item in baby_history:
        pred = str(item.get("prediction", ""))
        if pred not in count_prior:
            continue
        count_prior[pred] += 1.0

        ts = _to_dt(item.get("timestamp"))
        if ts is None:
            continue
        hour_distance = abs(ts.hour - now.hour)
        circular = min(hour_distance, 24 - hour_distance)
        weight = max(0.1, 1.0 - (circular / 12.0))
        hour_prior[pred] += weight

    count_total = sum(count_prior.values())
    hour_total = sum(hour_prior.values())

    blended: dict[str, float] = {}
    for cls in CLASSES:
        historical = count_prior[cls] / count_total
        circadian = hour_prior[cls] / hour_total
        personalized_prior = (0.65 * historical) + (0.35 * circadian)
        blended[cls] = (0.75 * base[cls]) + (0.25 * personalized_prior)

    normalized = normalize_probabilities(blended)
    personalized_prediction = max(normalized, key=normalized.get)
    return normalized, {
        "enabled": True,
        "history_count": len(baby_history),
        "personalized_prediction": personalized_prediction,
    }


def _hours_since(value: datetime | None, now: datetime) -> float | None:
    if value is None:
        return None
    return round(max(0.0, (now - value).total_seconds() / 3600.0), 2)


def infer_avatar_state(prediction: str) -> dict[str, str]:
    mapping = {
        "belly_pain": {"mood": "distressed", "emoji": "😣"},
        "burping": {"mood": "fussy", "emoji": "😗"},
        "discomfort": {"mood": "uneasy", "emoji": "😕"},
        "hungry": {"mood": "seeking_feed", "emoji": "😢"},
        "tired": {"mood": "sleepy", "emoji": "🥱"},
    }
    return mapping.get(prediction, {"mood": "neutral", "emoji": "🙂"})


def build_recommendation(
    prediction: str,
    confidence: float,
    now: datetime,
    last_feeding_at: datetime | None,
    last_sleep_at: datetime | None,
    baby_history: list[dict[str, Any]],
) -> dict[str, Any]:
    feeding_gap = _hours_since(last_feeding_at, now)
    sleep_gap = _hours_since(last_sleep_at, now)

    base_map = {
        "belly_pain": "Likely belly pain. Try upright hold, gentle tummy massage, and monitor for persistent crying.",
        "burping": "Likely needs burping. Hold upright and pat the back gently for a few minutes.",
        "discomfort": "Likely uncomfortable. Check diaper, clothing tightness, room temperature, and position.",
        "hungry": "Likely hungry.",
        "tired": "Likely tired. Reduce stimulation and start a soothing sleep routine.",
    }

    recommendation = base_map.get(prediction, "Keep monitoring and soothe your baby.")
    context_bits: list[str] = []

    if prediction == "hungry" and feeding_gap is not None:
        if feeding_gap >= 2.0:
            context_bits.append(f"Last feeding was {feeding_gap} hrs ago; feeding now is recommended")
        else:
            context_bits.append(f"Last feeding was {feeding_gap} hrs ago; offer comfort and reassess shortly")

    if prediction == "tired" and sleep_gap is not None:
        if sleep_gap >= 1.5:
            context_bits.append(f"Last sleep was {sleep_gap} hrs ago; a nap routine is recommended")

    confidence_pct = round(confidence * 100.0, 1)
    context_bits.append(f"Model confidence: {confidence_pct}%")

    timeline_hint = infer_cycle_hint(baby_history)
    if timeline_hint:
        context_bits.append(timeline_hint)

    return {
        "message": recommendation,
        "context": context_bits,
        "feeding_gap_hours": feeding_gap,
        "sleep_gap_hours": sleep_gap,
    }


def infer_cycle_hint(events: list[dict[str, Any]]) -> str:
    if len(events) < 6:
        return ""

    hourly = defaultdict(int)
    for item in events:
        ts = _to_dt(item.get("timestamp"))
        if ts is None:
            continue
        hourly[ts.hour] += 1

    if not hourly:
        return ""

    peak_hour = max(hourly, key=hourly.get)
    next_hour = (peak_hour + 1) % 24
    return f"Pattern learning: crying often occurs around {peak_hour:02d}:00-{next_hour:02d}:00"


def build_timeline(events: list[dict[str, Any]], days: int) -> dict[str, Any]:
    now = datetime.utcnow()
    since = now - timedelta(days=days)
    filtered = []
    for item in events:
        ts = _to_dt(item.get("timestamp"))
        if ts is None or ts < since:
            continue
        filtered.append((ts, str(item.get("prediction", ""))))

    hourly = {h: {"hour": h, "total": 0, **{c: 0 for c in CLASSES}} for h in range(24)}
    daily: dict[str, dict[str, Any]] = {}

    for ts, pred in filtered:
        if pred not in CLASSES:
            continue
        hourly[ts.hour]["total"] += 1
        hourly[ts.hour][pred] += 1

        day_key = ts.date().isoformat()
        if day_key not in daily:
            daily[day_key] = {"date": day_key, "total": 0, **{c: 0 for c in CLASSES}}
        daily[day_key]["total"] += 1
        daily[day_key][pred] += 1

    hourly_series = [hourly[h] for h in range(24)]
    trend_series = [daily[k] for k in sorted(daily.keys())]
    cycle_hint = infer_cycle_hint([{"timestamp": ts.isoformat(), "prediction": pred} for ts, pred in filtered])

    return {
        "days": days,
        "events": len(filtered),
        "time_vs_type": hourly_series,
        "frequency_trends": trend_series,
        "cycle_hint": cycle_hint,
    }
