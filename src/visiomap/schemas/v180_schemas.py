"""Visiomap v1.8.0 schemas — Event Management, Occupancy Patterns, Location Groups."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


# --- Event Management ---


class EventCreate(BaseModel):
    location_id: int
    name: str
    description: Optional[str] = None
    event_type: str = "general"  # general, concert, sports, market, festival, conference
    expected_crowd: int = Field(default=100, ge=1)
    start_time: str
    end_time: str


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    expected_crowd: Optional[int] = Field(default=None, ge=1)
    actual_crowd: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None  # scheduled, active, completed, cancelled


class EventResponse(BaseModel):
    id: int
    location_id: int
    name: str
    description: Optional[str]
    event_type: str
    expected_crowd: int
    actual_crowd: Optional[int]
    status: str
    start_time: str
    end_time: str
    crowd_accuracy_pct: Optional[float]
    created_at: str


class EventImpact(BaseModel):
    event_id: int
    event_name: str
    location_name: str
    expected_crowd: int
    actual_crowd: Optional[int]
    avg_density_during: Optional[float]
    avg_density_before: Optional[float]
    density_increase_pct: Optional[float]


# --- Occupancy Patterns ---


class DayPattern(BaseModel):
    day_of_week: int  # 0=Sunday (SQLite strftime %w)
    day_name: str
    avg_density: float
    peak_hour: int
    media_count: int


class OccupancyPatternResponse(BaseModel):
    location_id: int
    location_name: str
    weekly_pattern: list[DayPattern]
    busiest_day: str
    quietest_day: str
    avg_weekly_density: float


class MonthlyTrend(BaseModel):
    month: str  # YYYY-MM
    avg_density: float
    media_count: int
    peak_day: Optional[str]


class SeasonalResponse(BaseModel):
    location_id: int
    location_name: str
    monthly_trends: list[MonthlyTrend]
    peak_month: str
    quietest_month: str


# --- Location Groups ---


class LocationGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    group_type: str = "district"  # district, zone, campus, custom


class LocationGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class LocationGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    group_type: str
    member_count: int
    created_at: str


class GroupAnalytics(BaseModel):
    group_id: int
    group_name: str
    total_locations: int
    total_media: int
    avg_density: Optional[float]
    busiest_location: Optional[str]
    locations: list[dict]


class GroupComparison(BaseModel):
    groups: list[GroupAnalytics]
