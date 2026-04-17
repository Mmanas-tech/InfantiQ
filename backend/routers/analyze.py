from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from services.audio_processor import SUPPORTED_EXTENSIONS, process_audio_file
from services.cry_detector_service import cry_detector_service
from services.db_service import get_analyses_for_baby, save_analysis
from services.intelligence_service import (
    apply_personalization,
    build_recommendation,
    infer_avatar_state,
    parse_iso_datetime,
)
from services.model_service import model_service

router = APIRouter(prefix="/api", tags=["analyze"])

RECOMMENDATIONS = {
    "belly_pain": "Your baby may have belly pain. Try gentle burping, tummy massage, or comforting holds and monitor closely.",
    "burping": "Your baby likely needs burping. Hold upright and gently pat their back for a few minutes.",
    "discomfort": "Your baby seems uncomfortable. Check their diaper, clothing, temperature, or positioning.",
    "hungry": "Your baby is likely hungry. Try feeding them now or within the next 10-15 minutes.",
    "tired": "Your baby is likely tired. Try a calm environment, dim lights, and soothing rocking.",
}


def _safe_remove(path: str) -> None:
    if not path or not os.path.exists(path):
        return
    try:
        os.remove(path)
    except PermissionError:
        # Some Windows audio codecs can hold a temp file handle briefly.
        pass
    except OSError:
        pass


@router.post("/analyze")
async def analyze_audio(
    request: Request,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    baby_id: str | None = Form(default=None),
    last_feeding_at: str | None = Form(default=None),
    last_sleep_at: str | None = Form(default=None),
    parent_away: bool = Form(default=False),
):
    max_size_mb = float(os.getenv("MAX_AUDIO_SIZE_MB", "10"))
    max_size_bytes = int(max_size_mb * 1024 * 1024)

    extension = os.path.splitext(audio.filename or "")[-1].replace(".", "").lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": "Invalid audio format", "detail": "Supported: wav, mp3, ogg, m4a, webm"},
        )

    payload = await audio.read()
    if len(payload) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": "File too large", "detail": f"Max allowed size is {max_size_mb:.0f}MB"},
        )

    if not request.app.state.model_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Model not ready",
                "hint": "POST /api/model/train to train first",
            },
        )

    temp_input_path = ""
    processed = None
    try:
        fd, temp_input_path = tempfile.mkstemp(suffix=f".{extension}")
        os.close(fd)
        with open(temp_input_path, "wb") as output:
            output.write(payload)

        processed = process_audio_file(temp_input_path)

        is_baby_cry_signal, cry_signal_score = cry_detector_service.detect_baby_cry(
            processed.converted_path,
            feature_vector=processed.feature_vector,
        )

        analysis_id = str(uuid.uuid4())
        now_dt = datetime.utcnow()
        now = now_dt.isoformat()

        result = model_service.predict(
            features_dict={
                "mel_spec": processed.mel_spec,
                "feature_vector": processed.feature_vector,
            }
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "inference_failed", "detail": "Model inference failed"},
            )

        model_is_cry = bool(result.get("is_baby_cry", False))
        model_cry_score = float(result.get("baby_cry_score", 0.0))
        model_confidence = float(result.get("confidence", 0.0))

        # Accept if either detector says cry, model gate says cry, or model confidence is very strong.
        final_is_baby_cry = is_baby_cry_signal or model_is_cry or model_confidence >= 0.78
        final_cry_score = max(cry_signal_score, model_cry_score, model_confidence * 0.95)

        if not final_is_baby_cry:
            response = {
                "prediction": "non_baby_sound",
                "confidence": final_cry_score,
                "probabilities": {},
                "recommendation": "No baby cry detected. Please capture a clearer baby-cry sample and try again.",
                "recommendation_context": [
                    "Detected audio is likely background/environmental sound",
                    "Try moving closer to the baby and reducing TV/traffic noise",
                ],
                "analysis_id": analysis_id,
                "timestamp": now,
                "baby_id": baby_id,
                "is_baby_cry": False,
                "baby_cry_score": final_cry_score,
            }
            return response

        prediction = result["prediction"]
        confidence = float(result["confidence"])
        probabilities = result["probabilities"]

        baby_history: list[dict] = []
        personalization_meta = {"enabled": False, "reason": "baby_id not supplied", "history_count": 0}
        if baby_id:
            baby_history = await get_analyses_for_baby(baby_id=baby_id, limit=250)
            personalized_probs, personalization_meta = apply_personalization(
                probabilities=probabilities,
                baby_history=baby_history,
                now=now_dt,
            )
            probabilities = personalized_probs
            prediction = max(probabilities, key=probabilities.get)
            confidence = float(probabilities[prediction])

        recommendation_payload = build_recommendation(
            prediction=prediction,
            confidence=confidence,
            now=now_dt,
            last_feeding_at=parse_iso_datetime(last_feeding_at),
            last_sleep_at=parse_iso_datetime(last_sleep_at),
            baby_history=baby_history,
        )
        recommendation = recommendation_payload["message"]
        recommendation_context = recommendation_payload["context"]

        avatar_state = infer_avatar_state(prediction)
        alert = None
        if parent_away and confidence >= 0.55:
            alert = {
                "should_notify": True,
                "title": "InfantiQ Alert",
                "body": f"Baby seems {prediction.replace('_', ' ')} ({round(confidence * 100)}% confidence)",
            }

        response = {
            "prediction": prediction,
            "confidence": confidence,
            "probabilities": probabilities,
            "recommendation": recommendation,
            "recommendation_context": recommendation_context,
            "analysis_id": analysis_id,
            "timestamp": now,
            "baby_id": baby_id,
            "personalization": personalization_meta,
            "avatar": avatar_state,
            "alert": alert,
            "is_baby_cry": True,
            "baby_cry_score": float(final_cry_score),
        }

        db_record = {
            "analysis_id": analysis_id,
            "timestamp": now_dt,
            "prediction": prediction,
            "confidence": confidence,
            "probabilities": probabilities,
            "audio_duration_seconds": processed.duration_seconds,
            "audio_format": extension,
            "file_size_bytes": len(payload),
            "recommendation": recommendation,
            "recommendation_context": recommendation_context,
            "baby_id": baby_id,
            "last_feeding_at": last_feeding_at,
            "last_sleep_at": last_sleep_at,
            "parent_away": parent_away,
            "personalization": personalization_meta,
        }
        background_tasks.add_task(save_analysis, db_record)

        return response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "Invalid audio", "detail": str(exc)},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Audio processing failed",
                "detail": str(exc),
            },
        ) from exc
    finally:
        _safe_remove(temp_input_path)
        if processed:
            _safe_remove(processed.converted_path)
