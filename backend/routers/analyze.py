from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from services.audio_processor import SUPPORTED_EXTENSIONS, process_audio_file
from services.db_service import save_analysis
from services.model_service import model_service

router = APIRouter(prefix="/api", tags=["analyze"])

RECOMMENDATIONS = {
    "hunger": "Your baby is likely hungry. Try feeding them now or within the next 10-15 minutes.",
    "pain": "Your baby may be in pain or discomfort. Check for gas, colic, or physical discomfort. Consult a pediatrician if crying persists.",
    "discomfort": "Your baby seems uncomfortable. Check their diaper, clothing, temperature, or positioning.",
    "sleepiness": "Your baby is sleepy. Try a calm environment, gentle rocking, or a lullaby to help them drift off.",
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

        analysis_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        prediction = result["prediction"]
        recommendation = RECOMMENDATIONS.get(prediction, "No recommendation available")

        response = {
            "prediction": prediction,
            "confidence": result["confidence"],
            "probabilities": result["probabilities"],
            "recommendation": recommendation,
            "analysis_id": analysis_id,
            "timestamp": now,
        }

        db_record = {
            "analysis_id": analysis_id,
            "timestamp": datetime.utcnow(),
            "prediction": prediction,
            "confidence": result["confidence"],
            "probabilities": result["probabilities"],
            "audio_duration_seconds": processed.duration_seconds,
            "audio_format": extension,
            "file_size_bytes": len(payload),
            "recommendation": recommendation,
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
