from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from visiomap.database import get_db
from visiomap.repositories import LocationRepo, MediaRepo
from visiomap.schemas.analytics import (
    HeatmapResponse,
    LocationAnalytics,
    OverviewResponse,
)
from visiomap.services import AnalyticsService

router = APIRouter(tags=["analytics"])


def _service(db=Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(LocationRepo(db), MediaRepo(db))


@router.get("/locations/{location_id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap(location_id: int, svc: AnalyticsService = Depends(_service)):
    result = await svc.get_heatmap(location_id)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.get("/locations/{location_id}/analytics", response_model=LocationAnalytics)
async def get_analytics(location_id: int, svc: AnalyticsService = Depends(_service)):
    result = await svc.get_location_analytics(location_id)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.get("/analytics/overview", response_model=OverviewResponse)
async def get_overview(svc: AnalyticsService = Depends(_service)):
    return await svc.get_overview()
