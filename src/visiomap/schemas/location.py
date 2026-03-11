from typing import Optional
from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(500, ge=10, le=50_000)
    description: Optional[str] = Field(None, max_length=1000)


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    radius_m: Optional[int] = Field(None, ge=10, le=50_000)
    description: Optional[str] = None


class LocationResponse(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    radius_m: int
    description: Optional[str]
    media_count: int
    analyzed_count: int
    avg_crowd_density: Optional[float]
    created_at: str
