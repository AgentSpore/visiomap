from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from visiomap.database import get_db
from visiomap.schemas.analytics import (
    GeofenceCreate,
    GeofenceResponse,
    GeofenceCheckRequest,
    GeofenceCheckResponse,
)
from visiomap.services.geofence_service import GeofenceService

router = APIRouter(prefix="/geofences", tags=["geofences"])


def _service(db=Depends(get_db)) -> GeofenceService:
    return GeofenceService(db)


@router.post("", response_model=GeofenceResponse, status_code=201)
async def create_geofence(body: GeofenceCreate, svc: GeofenceService = Depends(_service)):
    return await svc.create(body.model_dump())


@router.get("", response_model=list[GeofenceResponse])
async def list_geofences(svc: GeofenceService = Depends(_service)):
    return await svc.list_all()


@router.get("/{geofence_id}", response_model=GeofenceResponse)
async def get_geofence(geofence_id: int, svc: GeofenceService = Depends(_service)):
    fence = await svc.get(geofence_id)
    if not fence:
        raise HTTPException(404, "Geofence not found")
    return fence


@router.delete("/{geofence_id}", status_code=204)
async def delete_geofence(geofence_id: int, svc: GeofenceService = Depends(_service)):
    if not await svc.delete(geofence_id):
        raise HTTPException(404, "Geofence not found")


@router.post("/{geofence_id}/check", response_model=GeofenceCheckResponse)
async def check_geofence(
    geofence_id: int,
    body: GeofenceCheckRequest,
    svc: GeofenceService = Depends(_service),
):
    result = await svc.check_point(geofence_id, body.lat, body.lng)
    if result is None:
        raise HTTPException(404, "Geofence not found")
    return result
