from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from visiomap.database import get_db
from visiomap.repositories import LocationRepo, MediaRepo
from visiomap.schemas.analytics import (
    HeatmapResponse,
    LocationAnalytics,
    OverviewResponse,
    AlertCreate,
    AlertResponse,
)
from visiomap.services import AnalyticsService
from visiomap.services.alert_service import AlertService

router = APIRouter(tags=["analytics"])


def _service(db=Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(LocationRepo(db), MediaRepo(db))


def _alert_svc(db=Depends(get_db)) -> AlertService:
    return AlertService(db)


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


@router.get("/locations/{location_id}/analytics/export/csv")
async def export_analytics_csv(location_id: int, svc: AnalyticsService = Depends(_service)):
    data = await svc.export_analytics_csv(location_id)
    if data is None:
        raise HTTPException(404, "Location not found")
    return StreamingResponse(
        iter([data]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=location_{location_id}_analytics.csv"},
    )


@router.get("/analytics/overview", response_model=OverviewResponse)
async def get_overview(svc: AnalyticsService = Depends(_service)):
    return await svc.get_overview()


# -- Density Alerts ------------------------------------------------------------

@router.post("/alerts", response_model=AlertResponse, status_code=201)
async def create_alert(body: AlertCreate, svc: AlertService = Depends(_alert_svc)):
    return await svc.create(body.model_dump())


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    location_id: int | None = Query(None),
    svc: AlertService = Depends(_alert_svc),
):
    return await svc.list_all(location_id=location_id)


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, svc: AlertService = Depends(_alert_svc)):
    alert = await svc.get(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(alert_id: int, svc: AlertService = Depends(_alert_svc)):
    if not await svc.delete(alert_id):
        raise HTTPException(404, "Alert not found")
