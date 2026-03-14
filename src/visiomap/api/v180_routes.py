"""v1.8.0 API routes — Event Management, Occupancy Patterns, Location Groups."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from visiomap.database import get_db
from visiomap.repositories.v180_repo import EventRepo, OccupancyRepo, LocationGroupRepo
from visiomap.schemas.v180_schemas import (
    # Events
    EventCreate,
    EventUpdate,
    EventResponse,
    EventImpact,
    # Occupancy
    OccupancyPatternResponse,
    SeasonalResponse,
    # Location Groups
    LocationGroupCreate,
    LocationGroupUpdate,
    LocationGroupResponse,
    GroupAnalytics,
    GroupComparison,
)
from visiomap.services.v180_service import (
    EventService,
    OccupancyService,
    LocationGroupService,
)

router = APIRouter(tags=["v1.8.0"])


# ==============================================================================
# Dependency factories
# ==============================================================================

def _event_service(db=Depends(get_db)) -> EventService:
    return EventService(db)


def _occupancy_service(db=Depends(get_db)) -> OccupancyService:
    return OccupancyService(db)


def _group_service(db=Depends(get_db)) -> LocationGroupService:
    return LocationGroupService(db)


# ==============================================================================
# Event Management
# ==============================================================================

@router.post(
    "/locations/{location_id}/events",
    response_model=EventResponse,
    status_code=201,
)
async def create_event(
    location_id: int,
    body: EventCreate,
    svc: EventService = Depends(_event_service),
):
    """Create a scheduled event at a location."""
    data = body.model_dump()
    data["location_id"] = location_id
    return await svc.create(data)


@router.get("/locations/{location_id}/events", response_model=list[EventResponse])
async def list_events(
    location_id: int,
    upcoming_only: bool = Query(False, description="Show only upcoming/active events"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: EventService = Depends(_event_service),
):
    """List events at a location."""
    status = "scheduled" if upcoming_only else None
    return await svc.list_all(location_id=location_id, status=status, limit=limit, offset=offset)


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    svc: EventService = Depends(_event_service),
):
    """Get event details."""
    return await svc.get(event_id)


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    body: EventUpdate,
    svc: EventService = Depends(_event_service),
):
    """Update event (actual crowd, status, etc.)."""
    return await svc.update(event_id, body.model_dump(exclude_unset=True))


@router.get("/events/{event_id}/impact", response_model=EventImpact)
async def event_impact(
    event_id: int,
    svc: EventService = Depends(_event_service),
):
    """Impact analysis: expected vs actual crowd, density change."""
    return await svc.get_impact(event_id)


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    svc: EventService = Depends(_event_service),
):
    """Delete an event."""
    await svc.delete(event_id)


# ==============================================================================
# Occupancy Patterns
# ==============================================================================

@router.get(
    "/locations/{location_id}/occupancy/weekly",
    response_model=OccupancyPatternResponse,
)
async def weekly_occupancy(
    location_id: int,
    svc: OccupancyService = Depends(_occupancy_service),
):
    """Weekly occupancy pattern — average crowd density per day of week."""
    return await svc.get_weekly(location_id)


@router.get(
    "/locations/{location_id}/occupancy/monthly",
    response_model=SeasonalResponse,
)
async def monthly_occupancy(
    location_id: int,
    months: int = Query(12, ge=1, le=60, description="Number of months to include"),
    svc: OccupancyService = Depends(_occupancy_service),
):
    """Monthly occupancy pattern — density trends per month."""
    return await svc.get_seasonal(location_id, months)


@router.get(
    "/locations/{location_id}/occupancy/seasonal",
    response_model=SeasonalResponse,
)
async def seasonal_occupancy(
    location_id: int,
    months: int = Query(24, ge=1, le=60, description="Number of months for seasonal analysis"),
    svc: OccupancyService = Depends(_occupancy_service),
):
    """Seasonal trends — longer-range density patterns."""
    return await svc.get_seasonal(location_id, months)


@router.get("/locations/{location_id}/occupancy/peak-hours")
async def peak_hours_occupancy(
    location_id: int,
    svc: OccupancyService = Depends(_occupancy_service),
):
    """Peak hours analysis — extends existing peak hours with weekly breakdown."""
    weekly = await svc.get_weekly(location_id)
    peak_hours = []
    for day in weekly.get("weekly_pattern", []):
        peak_hours.append({
            "day_name": day["day_name"],
            "day_of_week": day["day_of_week"],
            "peak_hour": day["peak_hour"],
            "avg_density": day["avg_density"],
        })
    return {
        "location_id": location_id,
        "location_name": weekly.get("location_name", "Unknown"),
        "peak_hours_by_day": peak_hours,
        "overall_busiest_day": weekly.get("busiest_day", "N/A"),
        "avg_weekly_density": weekly.get("avg_weekly_density", 0.0),
    }


# ==============================================================================
# Location Groups
# ==============================================================================

@router.post("/location-groups", response_model=LocationGroupResponse, status_code=201)
async def create_group(
    body: LocationGroupCreate,
    svc: LocationGroupService = Depends(_group_service),
):
    """Create a location group for aggregate analytics."""
    return await svc.create(body.model_dump())


@router.get("/location-groups", response_model=list[LocationGroupResponse])
async def list_groups(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    svc: LocationGroupService = Depends(_group_service),
):
    """List all location groups."""
    return await svc.list_all(limit, offset)


@router.get("/location-groups/compare", response_model=GroupComparison)
async def compare_groups(
    group_ids: str = Query(..., description="Comma-separated group IDs to compare"),
    svc: LocationGroupService = Depends(_group_service),
):
    """Compare analytics across multiple location groups."""
    try:
        ids = [int(x.strip()) for x in group_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, "group_ids must be comma-separated integers")
    if len(ids) < 2:
        raise HTTPException(422, "Provide at least 2 group IDs to compare")
    return await svc.compare_groups(ids)


@router.get("/location-groups/{group_id}", response_model=LocationGroupResponse)
async def get_group(
    group_id: int,
    svc: LocationGroupService = Depends(_group_service),
):
    """Get group details with member count."""
    return await svc.get(group_id)


@router.put("/location-groups/{group_id}", response_model=LocationGroupResponse)
async def update_group(
    group_id: int,
    body: LocationGroupUpdate,
    svc: LocationGroupService = Depends(_group_service),
):
    """Update group name or description."""
    return await svc.update(group_id, body.model_dump(exclude_unset=True))


@router.delete("/location-groups/{group_id}", status_code=204)
async def delete_group(
    group_id: int,
    svc: LocationGroupService = Depends(_group_service),
):
    """Delete a location group."""
    await svc.delete(group_id)


@router.post("/location-groups/{group_id}/locations", status_code=201)
async def add_group_location(
    group_id: int,
    location_id: int = Query(..., description="Location ID to add to the group"),
    svc: LocationGroupService = Depends(_group_service),
):
    """Add a location to a group."""
    return await svc.add_member(group_id, location_id)


@router.delete(
    "/location-groups/{group_id}/locations/{location_id}",
    status_code=204,
)
async def remove_group_location(
    group_id: int,
    location_id: int,
    svc: LocationGroupService = Depends(_group_service),
):
    """Remove a location from a group."""
    await svc.remove_member(group_id, location_id)


@router.get("/location-groups/{group_id}/analytics", response_model=GroupAnalytics)
async def group_analytics(
    group_id: int,
    svc: LocationGroupService = Depends(_group_service),
):
    """Aggregate analytics across all locations in a group."""
    return await svc.get_analytics(group_id)
