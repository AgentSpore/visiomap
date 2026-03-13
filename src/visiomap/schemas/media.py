from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "MediaCreate",
    "MediaBatchCreate",
    "MediaBatchResponse",
    "AnalysisResult",
    "MediaResponse",
    "AnalyzeAllResponse",
]


class MediaCreate(BaseModel):
    location_id: int
    source_url: str = Field(..., min_length=1)
    source_type: str = Field("photo", pattern=r"^(photo|video|screenshot)$")
    captured_at: str | None = None
    tags: list[str] = Field(default_factory=list)


class MediaBatchCreate(BaseModel):
    items: list[MediaCreate] = Field(..., min_length=1, max_length=100)


class AnalysisResult(BaseModel):
    crowd_density: float = Field(..., ge=0, le=10)
    crowd_count_estimate: int = Field(..., ge=0)
    age_groups: dict[str, float]
    mood: dict[str, float]
    dominant_mood: str
    environment_tags: list[str]
    weather: str | None = None
    time_of_day: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    analysis_source: str


class MediaResponse(BaseModel):
    id: int
    location_id: int
    source_url: str
    source_type: str
    captured_at: str | None
    tags: list[str]
    analyzed: bool
    analysis: AnalysisResult | None = None
    submitted_at: str


class MediaBatchResponse(BaseModel):
    created: int
    items: list[MediaResponse]


class AnalyzeAllResponse(BaseModel):
    analyzed: int
    failed: int
    errors: list[str]
