from typing import Optional
from pydantic import BaseModel


class HeatPoint(BaseModel):
    lat: float
    lng: float
    intensity: float        # 0.0–1.0 normalized
    crowd_density: float    # raw 0–10
    sample_count: int


class HeatmapResponse(BaseModel):
    location_id: int
    location_name: str
    center_lat: float
    center_lng: float
    radius_m: int
    points: list[HeatPoint]
    total_samples: int
    max_density: float


class DailyTrendEntry(BaseModel):
    day: str
    sample_count: int
    avg_crowd_density: float
    dominant_mood: Optional[str]


class LocationAnalytics(BaseModel):
    location_id: int
    location_name: str
    total_media: int
    analyzed_media: int
    avg_crowd_density: Optional[float]
    peak_crowd_density: Optional[float]
    dominant_mood: Optional[str]
    top_environment_tags: list[str]
    age_distribution: Optional[dict[str, float]]
    mood_distribution: Optional[dict[str, float]]
    weather_breakdown: Optional[dict[str, int]]
    daily_trend: list[DailyTrendEntry]


class LocationSummary(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    media_count: int
    avg_crowd_density: Optional[float]
    dominant_mood: Optional[str]


class OverviewResponse(BaseModel):
    total_locations: int
    total_media: int
    analyzed_media: int
    busiest_location: Optional[str]
    avg_crowd_density: Optional[float]
    locations: list[LocationSummary]
