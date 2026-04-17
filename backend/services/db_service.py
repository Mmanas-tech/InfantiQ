from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class DBService:
    def __init__(self) -> None:
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self, mongo_uri: str, db_name: str = "infant_cry_db") -> None:
        try:
            self.client = AsyncIOMotorClient(mongo_uri)
            self.db = self.client[db_name]
            await self._ensure_indexes()
            logger.info("Connected to MongoDB")
        except Exception as exc:
            logger.exception("MongoDB connection failed: %s", exc)
            self.client = None
            self.db = None

    async def _ensure_indexes(self) -> None:
        if self.db is None:
            return
        analyses = self.db["analyses"]
        model_runs = self.db["model_runs"]
        await analyses.create_index([("timestamp", -1)])
        await analyses.create_index("analysis_id", unique=True)
        await model_runs.create_index([("started_at", -1)])
        await model_runs.create_index("run_id", unique=True)

    async def close(self) -> None:
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    async def save_analysis(self, data: dict[str, Any]) -> Optional[str]:
        if self.db is None:
            return None
        try:
            result = await self.db["analyses"].insert_one(data)
            return str(result.inserted_id)
        except Exception as exc:
            logger.exception("Failed to save analysis: %s", exc)
            return None

    async def get_recent_analyses(self, limit: int = 20) -> list[dict[str, Any]]:
        if self.db is None:
            return []
        try:
            cursor = self.db["analyses"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as exc:
            logger.exception("Failed to fetch recent analyses: %s", exc)
            return []

    async def get_analysis_by_id(self, analysis_id: str) -> Optional[dict[str, Any]]:
        if self.db is None:
            return None
        try:
            return await self.db["analyses"].find_one({"analysis_id": analysis_id}, {"_id": 0})
        except Exception as exc:
            logger.exception("Failed to fetch analysis %s: %s", analysis_id, exc)
            return None

    async def save_model_run(self, data: dict[str, Any]) -> Optional[str]:
        if self.db is None:
            return None
        try:
            result = await self.db["model_runs"].insert_one(data)
            return str(result.inserted_id)
        except Exception as exc:
            logger.exception("Failed to save model run: %s", exc)
            return None

    async def update_model_run(self, run_id: str, update: dict[str, Any]) -> None:
        if self.db is None:
            return
        try:
            await self.db["model_runs"].update_one({"run_id": run_id}, {"$set": update})
        except Exception as exc:
            logger.exception("Failed to update model run %s: %s", run_id, exc)

    async def get_latest_model_run(self) -> Optional[dict[str, Any]]:
        if self.db is None:
            return None
        try:
            return await self.db["model_runs"].find_one({}, {"_id": 0}, sort=[("started_at", -1)])
        except Exception as exc:
            logger.exception("Failed to fetch latest model run: %s", exc)
            return None


_db_service = DBService()


async def connect_db(mongo_uri: str) -> None:
    await _db_service.connect(mongo_uri)


async def close_db() -> None:
    await _db_service.close()


async def save_analysis(data: dict[str, Any]) -> Optional[str]:
    return await _db_service.save_analysis(data)


async def get_recent_analyses(limit: int = 20) -> list[dict[str, Any]]:
    return await _db_service.get_recent_analyses(limit)


async def get_analysis_by_id(analysis_id: str) -> Optional[dict[str, Any]]:
    return await _db_service.get_analysis_by_id(analysis_id)


async def save_model_run(data: dict[str, Any]) -> Optional[str]:
    return await _db_service.save_model_run(data)


async def update_model_run(run_id: str, update: dict[str, Any]) -> None:
    await _db_service.update_model_run(run_id, update)


async def get_latest_model_run() -> Optional[dict[str, Any]]:
    return await _db_service.get_latest_model_run()


def utcnow() -> datetime:
    return datetime.utcnow()
