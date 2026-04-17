from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ml.train import run_training_pipeline
from routers.analyze import router as analyze_router
from routers.history import router as history_router
from services.db_service import (
    close_db,
    connect_db,
    get_latest_model_run,
    save_model_run,
    update_model_run,
)
from services.model_service import model_paths, model_service

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH, CLASSES_PATH, METADATA_PATH = model_paths(str(BASE_DIR))

app = FastAPI(title="Infant Cry Intelligence API", version="1.0.0")


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(history_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail), "detail": None}
    return JSONResponse(status_code=exc.status_code, content=detail)


async def _run_training_job(run_id: str) -> None:
    app.state.model_ready = False
    app.state.model_training = True

    started_at = datetime.utcnow()
    await save_model_run(
        {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": None,
            "status": "running",
            "accuracy": 0.0,
            "total_samples": 0,
            "epochs": 0,
            "error_message": None,
        }
    )

    try:
        metadata = await asyncio.to_thread(run_training_pipeline)
        model_service.load(MODEL_PATH, CLASSES_PATH, METADATA_PATH)
        app.state.model_ready = True
        await update_model_run(
            run_id,
            {
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "accuracy": metadata.get("accuracy", 0.0),
                "total_samples": metadata.get("total_samples", 0),
                "epochs": metadata.get("epochs_trained", 0),
                "error_message": None,
            },
        )
    except Exception as exc:
        logger.exception("Training failed: %s", exc)
        await update_model_run(
            run_id,
            {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error_message": str(exc),
            },
        )
    finally:
        app.state.model_training = False


@app.on_event("startup")
async def startup_event() -> None:
    app.state.mongodb_enabled = _env_bool("ENABLE_MONGODB", default=True)
    if app.state.mongodb_enabled:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/infant_cry_db")
        await connect_db(mongo_uri)
    else:
        logger.warning("MongoDB disabled via ENABLE_MONGODB=false")

    app.state.model_ready = model_service.load(MODEL_PATH, CLASSES_PATH, METADATA_PATH)
    app.state.model_training = False

    if not os.path.exists(MODEL_PATH):
        logger.warning("No model found. Starting automatic training pipeline...")
        run_id = str(uuid.uuid4())
        asyncio.create_task(_run_training_job(run_id))


@app.on_event("shutdown")
async def shutdown_event() -> None:
    if getattr(app.state, "mongodb_enabled", True):
        await close_db()


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "model_loaded": bool(model_service.ready())}


@app.get("/api/model/status")
async def model_status() -> dict:
    latest_run = await get_latest_model_run() if getattr(app.state, "mongodb_enabled", True) else None
    metadata = model_service.metadata
    return {
        "trained": model_service.ready(),
        "accuracy": float(metadata.get("accuracy", 0.0)),
        "classes": metadata.get("classes", ["belly_pain", "burping", "discomfort", "hungry", "tired"]),
        "total_samples": int(metadata.get("total_samples", 0)),
        "latest_run": latest_run,
        "training": bool(app.state.model_training),
    }


@app.post("/api/model/train")
async def model_train(background_tasks: BackgroundTasks) -> dict:
    if app.state.model_training:
        raise HTTPException(status_code=409, detail={"error": "Training already running", "detail": None})

    run_id = str(uuid.uuid4())

    async def kickoff() -> None:
        await _run_training_job(run_id)

    background_tasks.add_task(kickoff)
    return {"message": "Training started", "job_id": run_id}
