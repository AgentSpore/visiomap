from fastapi import APIRouter, Depends, status

import aiosqlite

from visiomap.database import get_db
from visiomap.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from visiomap.services import location_service

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(body: LocationCreate, db=Depends(get_db)):
    """Register a new location to monitor."""
    return await location_service.create(db, body)


@router.get("", response_model=list[LocationResponse])
async def list_locations(db=Depends(get_db)):
    """List all monitored locations with aggregate stats."""
    return await location_service.list_all(db)


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(location_id: int, db=Depends(get_db)):
    """Get location detail with media count and average crowd density."""
    return await location_service.get_or_404(db, location_id)


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(location_id: int, body: LocationUpdate, db=Depends(get_db)):
    """Update location name, radius, or description."""
    return await location_service.update(db, location_id, body)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(location_id: int, db=Depends(get_db)):
    """Delete a location (media records are preserved)."""
    await location_service.delete(db, location_id)
