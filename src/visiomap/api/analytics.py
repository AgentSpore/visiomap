from fastapi import APIRouter, Depends

from visiomap.database import get_db
from visiomap.schemas.analytics import HeatmapResponse, LocationAnalytics, OverviewResponse
from visiomap.services import analytics_service

router = APIRouter(tags=["Analytics"])


@router.get("/locations/{location_id}/heatmap", response_model=HeatmapResponse)
async def heatmap(location_id: int, db=Depends(get_db)):
    """
    Spatial heatmap data for a location.
    Each analyzed photo is scattered within the monitoring radius;
    intensity is normalized crowd_density / 10.
    Feed the points array to Leaflet.heat or any heatmap library.
    """
    return await analytics_service.get_heatmap(db, location_id)


@router.get("/locations/{location_id}/analytics", response_model=LocationAnalytics)
async def location_analytics(location_id: int, db=Depends(get_db)):
    """
    Full analytics for a location: crowd trends, mood distribution,
    age breakdown, weather, top environment tags, 30-day daily trend.
    """
    return await analytics_service.get_location_analytics(db, location_id)


@router.get("/analytics/overview", response_model=OverviewResponse)
async def overview(db=Depends(get_db)):
    """Cross-location overview: totals, busiest location, per-location summary."""
    return await analytics_service.get_overview(db)
