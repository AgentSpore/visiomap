from typing import Optional
from fastapi import HTTPException

import aiosqlite

from visiomap.repositories import location_repo
from visiomap.schemas.location import LocationCreate, LocationUpdate, LocationResponse


def _to_response(row: dict) -> LocationResponse:
    return LocationResponse(
        id=row["id"],
        name=row["name"],
        lat=row["lat"],
        lng=row["lng"],
        radius_m=row["radius_m"],
        description=row["description"],
        media_count=row["media_count"] or 0,
        analyzed_count=int(row["analyzed_count"] or 0),
        avg_crowd_density=round(row["avg_crowd_density"], 2) if row["avg_crowd_density"] else None,
        created_at=row["created_at"],
    )


async def create(db: aiosqlite.Connection, body: LocationCreate) -> LocationResponse:
    try:
        row = await location_repo.create(db, body.model_dump())
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(409, f"Location '{body.name}' already exists")
        raise
    return _to_response(row)


async def get_or_404(db: aiosqlite.Connection, location_id: int) -> LocationResponse:
    row = await location_repo.get_by_id(db, location_id)
    if not row:
        raise HTTPException(404, "Location not found")
    return _to_response(row)


async def list_all(db: aiosqlite.Connection) -> list[LocationResponse]:
    rows = await location_repo.list_all(db)
    return [_to_response(r) for r in rows]


async def update(
    db: aiosqlite.Connection, location_id: int, body: LocationUpdate
) -> LocationResponse:
    row = await location_repo.update(db, location_id, body.model_dump(exclude_unset=True))
    if not row:
        raise HTTPException(404, "Location not found")
    return _to_response(row)


async def delete(db: aiosqlite.Connection, location_id: int) -> None:
    ok = await location_repo.delete(db, location_id)
    if not ok:
        raise HTTPException(404, "Location not found")
