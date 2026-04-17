from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parents[1]
LOCAL_ANALYSES_PATH = BASE_DIR / "data" / "local_analyses.jsonl"


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
        await analyses.create_index("baby_id")
        await model_runs.create_index([("started_at", -1)])
        await model_runs.create_index("run_id", unique=True)

    def _serialize_analysis(self, data: dict[str, Any]) -> dict[str, Any]:
        serialized: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
        return serialized

    def _write_local_analysis(self, data: dict[str, Any]) -> None:
        try:
            LOCAL_ANALYSES_PATH.parent.mkdir(parents=True, exist_ok=True)
            serialized = self._serialize_analysis(data)
            with LOCAL_ANALYSES_PATH.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(serialized, ensure_ascii=True) + "\n")
        except Exception as exc:
            logger.exception("Failed to write local analysis store: %s", exc)

    def _parse_timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        return datetime.min

    def _read_local_analyses(self) -> list[dict[str, Any]]:
        if not LOCAL_ANALYSES_PATH.exists():
            return []
        items: list[dict[str, Any]] = []
        try:
            with LOCAL_ANALYSES_PATH.open("r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                        items.append(payload)
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.exception("Failed to read local analysis store: %s", exc)
        return items

    def _filter_local_analyses(
        self,
        baby_id: str | None = None,
        since: datetime | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        items = self._read_local_analyses()
        filtered: list[dict[str, Any]] = []
        for item in items:
            if baby_id and item.get("baby_id") != baby_id:
                continue
            ts = self._parse_timestamp(item.get("timestamp"))
            if since and ts < since:
                continue
            filtered.append(item)

        filtered.sort(key=lambda x: self._parse_timestamp(x.get("timestamp")), reverse=True)
        return filtered[:limit]

    async def close(self) -> None:
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    async def save_analysis(self, data: dict[str, Any]) -> Optional[str]:
        self._write_local_analysis(data)
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
            return self._filter_local_analyses(limit=limit)
        try:
            cursor = self.db["analyses"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as exc:
            logger.exception("Failed to fetch recent analyses: %s", exc)
            return self._filter_local_analyses(limit=limit)

    async def get_analyses_for_baby(
        self,
        baby_id: str,
        limit: int = 200,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if self.db is None:
            return self._filter_local_analyses(baby_id=baby_id, since=since, limit=limit)

        query: dict[str, Any] = {"baby_id": baby_id}
        if since is not None:
            query["timestamp"] = {"$gte": since}

        try:
            cursor = self.db["analyses"].find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as exc:
            logger.exception("Failed to fetch analyses for baby %s: %s", baby_id, exc)
            return self._filter_local_analyses(baby_id=baby_id, since=since, limit=limit)

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


async def get_analyses_for_baby(
    baby_id: str,
    limit: int = 200,
    since: datetime | None = None,
) -> list[dict[str, Any]]:
    return await _db_service.get_analyses_for_baby(baby_id=baby_id, limit=limit, since=since)


def utcnow() -> datetime:
    return datetime.utcnow()
