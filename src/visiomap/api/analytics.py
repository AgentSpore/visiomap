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
    AlertUpdate,
    AlertResponse,
    ComparisonResponse,
    ClusterResponse,
    ScoreTrendResponse,
)
from visiomap.services import AnalyticsService
from visiomap.services.alert_service import AlertService

router = APIRouter(tags=["analytics"])


def _service(db=Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(LocationRepo(db), MediaRepo(db))


def _alert_svc(db=Depends(get_db)) -> AlertService:
    return AlertService(db)


@router.get("/locations/{location_id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    location_id: int,
    from_date: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    svc: AnalyticsService = Depends(_service),
):
    result = await svc.get_heatmap(location_id, from_date, to_date)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.get("/locations/{location_id}/analytics", response_model=LocationAnalytics)
async def get_analytics(
    location_id: int,
    from_date: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    svc: AnalyticsService = Depends(_service),
):
    result = await svc.get_location_analytics(location_id, from_date, to_date)
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


@router.get("/locations/{location_id}/analytics/trend", response_model=ScoreTrendResponse)
async def score_trend(
    location_id: int,
    window: int = Query(7, ge=2, le=30, description="Moving average window in days"),
    svc: AnalyticsService = Depends(_service),
):
    result = await svc.get_score_trend(location_id, window=window)
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.get("/analytics/overview", response_model=OverviewResponse)
async def get_overview(svc: AnalyticsService = Depends(_service)):
    return await svc.get_overview()


@router.get("/analytics/compare", response_model=ComparisonResponse)
async def compare_locations(
    ids: str = Query(..., description="Comma-separated location IDs (e.g. 1,2,3)"),
    from_date: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    svc: AnalyticsService = Depends(_service),
):
    try:
        location_ids = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(400, "ids must be comma-separated integers")
    if len(location_ids) < 2:
        raise HTTPException(400, "Provide at least 2 location IDs to compare")
    if len(location_ids) > 10:
        raise HTTPException(400, "Maximum 10 locations per comparison")
    entries = await svc.compare_locations(location_ids, from_date, to_date)
    return ComparisonResponse(locations=entries, from_date=from_date, to_date=to_date)


@router.get("/analytics/clusters", response_model=ClusterResponse)
async def cluster_locations(
    radius_km: float = Query(5.0, ge=0.5, le=100, description="Clustering radius in km"),
    svc: AnalyticsService = Depends(_service),
):
    return await svc.cluster_locations(radius_km=radius_km)


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


@router.patch("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    body: AlertUpdate,
    svc: AlertService = Depends(_alert_svc),
):
    result = await svc.update(alert_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, "Alert not found")
    return result


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(alert_id: int, svc: AlertService = Depends(_alert_svc)):
    if not await svc.delete(alert_id):
        raise HTTPException(404, "Alert not found")
