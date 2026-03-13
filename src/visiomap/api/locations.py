from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from visiomap.database import get_db
from visiomap.repositories import LocationRepo
from visiomap.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from visiomap.services import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])


def _service(db=Depends(get_db)) -> LocationService:
    return LocationService(LocationRepo(db))


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(body: LocationCreate, svc: LocationService = Depends(_service)):
    return await svc.create(body.model_dump())


@router.get("", response_model=list[LocationResponse])
async def list_locations(svc: LocationService = Depends(_service)):
    return await svc.list_all()


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(location_id: int, svc: LocationService = Depends(_service)):
    loc = await svc.get(location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    return loc


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int, body: LocationUpdate, svc: LocationService = Depends(_service)
):
    result = await svc.update(location_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.delete("/{location_id}", status_code=204)
async def delete_location(location_id: int, svc: LocationService = Depends(_service)):
    if not await svc.delete(location_id):
        raise HTTPException(404, "Location not found")
