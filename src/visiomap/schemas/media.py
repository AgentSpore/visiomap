from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "MediaCreate",
    "MediaBatchCreate",
    "MediaBatchResponse",
    "AnalysisResult",
    "MediaResponse",
    "AnalyzeAllResponse",
    "AnnotationCreate",
    "AnnotationResponse",
    "TagSuggestion",
    "TagSuggestionsResponse",
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


# -- v1.5.0: Media Annotations ------------------------------------------------

class AnnotationCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Annotation text")
    author: str = Field("reviewer", max_length=100, description="Author name or role")


class AnnotationResponse(BaseModel):
    id: int
    media_id: int
    text: str
    author: str
    created_at: str


# -- v1.6.0: Media Auto-Tag Suggestions ---------------------------------------

class TagSuggestion(BaseModel):
    tag: str
    source: str
    confidence: float = Field(..., ge=0, le=1)


class TagSuggestionsResponse(BaseModel):
    media_id: int
    suggestions: list[TagSuggestion]
    auto_applicable_count: int
