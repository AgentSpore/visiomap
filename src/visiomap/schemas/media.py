from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class AnalysisResult(BaseModel):
    crowd_density: float = Field(..., ge=0, le=10)
    crowd_count_estimate: int = Field(..., ge=0)
    age_groups: dict[str, int]   # child/young_adult/adult/senior → %
    mood: dict[str, int]          # positive/neutral/negative → %
    dominant_mood: str
    environment_tags: list[str]
    weather: str
    time_of_day: str
    confidence: float = Field(..., ge=0, le=1)
    analysis_source: str          # openai | mock | mock_fallback


class MediaSubmit(BaseModel):
    location_id: int
    source_url: str = Field(..., min_length=10)
    source_type: str = Field("photo", pattern="^(photo|video)$")
    captured_at: Optional[str] = None   # ISO 8601
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v: list[str]) -> list[str]:
        return [t.strip().lower() for t in v if t.strip()][:20]


class BatchSubmit(BaseModel):
    items: list[MediaSubmit] = Field(..., min_length=1, max_length=50)


class MediaResponse(BaseModel):
    id: int
    location_id: int
    source_url: str
    source_type: str
    captured_at: Optional[str]
    tags: list[str]
    analyzed: bool
    analysis: Optional[AnalysisResult]
    submitted_at: str


class BatchResult(BaseModel):
    submitted: int
    failed: int
    items: list[MediaResponse]
