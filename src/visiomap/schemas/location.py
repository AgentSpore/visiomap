from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["LocationCreate", "LocationUpdate", "LocationResponse"]


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    radius_m: int = Field(500, ge=50, le=50000, description="Monitoring radius in meters")
    description: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    radius_m: int | None = Field(None, ge=50, le=50000)
    description: str | None = None


class LocationResponse(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    radius_m: int
    description: str | None
    media_count: int = 0
    analyzed_count: int = 0
    avg_crowd_density: float | None = None
    created_at: str
