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
    "HealthScoreResponse",
    "HealthFactor",
    "AnomalyEntry",
    "AnomalyResponse",
    "PeakHourEntry",
    "PeakHoursResponse",
    "ForecastPoint",
    "ForecastResponse",
    "CategoryBenchmarkEntry",
    "CategoryBenchmarkResponse",
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


# -- v1.4.0: Location Health Score ---------------------------------------------

class HealthFactor(BaseModel):
    name: str
    score: float
    max_score: float
    details: str


class HealthScoreResponse(BaseModel):
    location_id: int
    location_name: str
    health_score: float
    max_score: float
    health_pct: float
    rating: str
    factors: list[HealthFactor]
    avg_crowd_density: float | None
    dominant_mood: str | None
    analysis_coverage_pct: float
    total_media: int
    analyzed_media: int


# -- v1.4.0: Crowd Density Anomalies ------------------------------------------

class AnomalyEntry(BaseModel):
    date: str
    avg_density: float
    baseline_avg: float
    deviation_ratio: float
    severity: str
    media_count: int


class AnomalyResponse(BaseModel):
    location_id: int
    location_name: str
    anomalies: list[AnomalyEntry]
    total_anomalies: int
    baseline_avg_daily: float
    analysis_period_days: int


# -- v1.5.0: Peak Hours Analysis -----------------------------------------------

class PeakHourEntry(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    avg_density: float
    media_count: int
    avg_crowd_count: int
    dominant_mood: str | None


class PeakHoursResponse(BaseModel):
    location_id: int
    location_name: str
    hours: list[PeakHourEntry]
    peak_hour: int
    quietest_hour: int
    peak_density: float
    quietest_density: float
    total_analyzed: int


# -- v1.6.0: Crowd Forecast ---------------------------------------------------

class ForecastPoint(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    predicted_density: float
    confidence: float = Field(..., ge=0, le=1)
    based_on_samples: int


class ForecastResponse(BaseModel):
    location_id: int
    location_name: str
    forecast_date: str
    points: list[ForecastPoint]
    avg_predicted_density: float
    peak_hour: int
    peak_density: float


# -- v1.6.0: Category Benchmarks ----------------------------------------------

class CategoryBenchmarkEntry(BaseModel):
    metric: str
    location_value: float
    category_avg: float
    percentile: float
    above_avg: bool


class CategoryBenchmarkResponse(BaseModel):
    location_id: int
    location_name: str
    category: str
    benchmarks: list[CategoryBenchmarkEntry]
    overall_percentile: float
