from __future__ import annotations

from pydantic import BaseModel

__all__ = [
    "HeatPoint",
    "HeatmapResponse",
    "LocationAnalytics",
    "DailyTrend",
    "OverviewResponse",
    "LocationSummary",
]


class HeatPoint(BaseModel):
    lat: float
    lng: float
    intensity: float
    crowd_density: float
    sample_count: int


class HeatmapResponse(BaseModel):
    location_id: int
    location_name: str
    center_lat: float
    center_lng: float
    radius_m: int
    points: list[HeatPoint]
    total_samples: int


class DailyTrend(BaseModel):
    date: str
    avg_density: float
    media_count: int


class LocationAnalytics(BaseModel):
    location_id: int
    location_name: str
    total_media: int
    analyzed_media: int
    avg_crowd_density: float | None
    peak_crowd_density: float | None
    dominant_mood: str | None
    top_environment_tags: list[str]
    age_distribution: dict[str, float] | None
    mood_distribution: dict[str, float] | None
    daily_trend: list[DailyTrend]


class LocationSummary(BaseModel):
    id: int
    name: str
    media_count: int
    analyzed_count: int
    avg_crowd_density: float | None


class OverviewResponse(BaseModel):
    total_locations: int
    total_media: int
    analyzed_media: int
    busiest_location: str | None
    avg_crowd_density: float | None
    locations_summary: list[LocationSummary]
