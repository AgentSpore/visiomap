from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "HeatPoint",
    "HeatmapResponse",
    "LocationAnalytics",
    "DailyTrend",
    "OverviewResponse",
    "LocationSummary",
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "ComparisonEntry",
    "ComparisonResponse",
    "GeofenceCreate",
    "GeofenceResponse",
    "GeofenceCheckRequest",
    "GeofenceCheckResponse",
    "ClusterEntry",
    "ClusterResponse",
    "TrendPoint",
    "ScoreTrendResponse",
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
    category: str
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


# -- Density Alerts ------------------------------------------------------------

class AlertCreate(BaseModel):
    location_id: int
    threshold: float = Field(..., ge=0, le=100, description="Crowd density threshold (0-100)")
    webhook_url: str = Field(..., min_length=1, description="URL to POST when threshold exceeded")
    label: str | None = Field(None, max_length=120)


class AlertUpdate(BaseModel):
    threshold: float | None = Field(None, ge=0, le=100)
    webhook_url: str | None = Field(None, min_length=1)
    label: str | None = None
    active: bool | None = None


class AlertResponse(BaseModel):
    id: int
    location_id: int
    threshold: float
    webhook_url: str
    label: str | None
    fired_count: int
    last_fired_at: str | None
    active: bool
    created_at: str


# -- Location Comparison -------------------------------------------------------

class ComparisonEntry(BaseModel):
    location_id: int
    location_name: str
    category: str
    total_media: int
    analyzed_media: int
    avg_crowd_density: float | None
    peak_crowd_density: float | None
    dominant_mood: str | None
    top_tags: list[str]


class ComparisonResponse(BaseModel):
    locations: list[ComparisonEntry]
    from_date: str | None
    to_date: str | None


# -- v1.3.0: Geofencing -------------------------------------------------------

class LatLng(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class GeofenceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    polygon: list[LatLng] = Field(
        ..., min_length=3, max_length=100,
        description="Polygon vertices as lat/lng pairs (minimum 3 points)",
    )


class GeofenceResponse(BaseModel):
    id: int
    name: str
    description: str | None
    polygon: list[LatLng]
    vertex_count: int
    locations_inside: int
    created_at: str


class GeofenceCheckRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class GeofenceCheckResponse(BaseModel):
    geofence_id: int
    geofence_name: str
    point: LatLng
    inside: bool


# -- v1.3.0: Clustering -------------------------------------------------------

class ClusterMember(BaseModel):
    location_id: int
    location_name: str
    lat: float
    lng: float
    category: str
    avg_crowd_density: float | None


class ClusterEntry(BaseModel):
    cluster_id: int
    center_lat: float
    center_lng: float
    member_count: int
    members: list[ClusterMember]
    avg_crowd_density: float | None
    categories: list[str]


class ClusterResponse(BaseModel):
    clusters: list[ClusterEntry]
    total_clusters: int
    unclustered_count: int
    radius_km: float


# -- v1.3.0: Score Trend ------------------------------------------------------

class TrendPoint(BaseModel):
    date: str
    avg_density: float
    media_count: int
    moving_avg: float | None
    direction: str


class ScoreTrendResponse(BaseModel):
    location_id: int
    location_name: str
    window_days: int
    points: list[TrendPoint]
    overall_trend: str
    latest_density: float | None
    latest_moving_avg: float | None
