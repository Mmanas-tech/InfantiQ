from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field


class AnalyzeResponse(BaseModel):
    prediction: str
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: Dict[str, float]
    recommendation: str
    analysis_id: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class ModelStatusResponse(BaseModel):
    trained: bool
    accuracy: float
    classes: list[str]
    total_samples: int
