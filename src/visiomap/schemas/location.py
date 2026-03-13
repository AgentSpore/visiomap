from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

__all__ = ["LocationCategory", "LocationCreate", "LocationUpdate", "LocationResponse"]


class LocationCategory(str, Enum):
    mall = "mall"
    park = "park"
    street = "street"
    venue = "venue"
    transit = "transit"
    beach = "beach"
    other = "other"


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    radius_m: int = Field(500, ge=50, le=50000, description="Monitoring radius in meters")
    category: LocationCategory = LocationCategory.other
    description: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=20, description="Custom tags for filtering/grouping")


class LocationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    radius_m: int | None = Field(None, ge=50, le=50000)
    category: LocationCategory | None = None
    description: str | None = None
    tags: list[str] | None = Field(None, max_length=20)


class LocationResponse(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    radius_m: int
    category: str
    description: str | None
    tags: list[str] = []
    media_count: int = 0
    analyzed_count: int = 0
    avg_crowd_density: float | None = None
    created_at: str
