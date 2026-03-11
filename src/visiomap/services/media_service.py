from fastapi import HTTPException
from typing import Optional

import aiosqlite

from visiomap.analyzer import analyze
from visiomap.repositories import location_repo, media_repo
from visiomap.schemas.media import (
    MediaSubmit, BatchSubmit, MediaResponse, BatchResult, AnalysisResult,
)
from visiomap.config import settings


def _to_response(row: dict) -> MediaResponse:
    return MediaResponse(
        id=row["id"],
        location_id=row["location_id"],
        source_url=row["source_url"],
        source_type=row["source_type"],
        captured_at=row["captured_at"],
        tags=row["tags"],
        analyzed=row["analyzed"],
        analysis=row.get("analysis"),
        submitted_at=row["submitted_at"],
    )


async def submit(db: aiosqlite.Connection, body: MediaSubmit) -> MediaResponse:
    if not await location_repo.exists(db, body.location_id):
        raise HTTPException(404, "Location not found")
    row = await media_repo.create(db, body.model_dump())
    return _to_response(row)


async def submit_batch(db: aiosqlite.Connection, body: BatchSubmit) -> BatchResult:
    if len(body.items) > settings.max_batch_size:
        raise HTTPException(422, f"Batch size exceeds limit of {settings.max_batch_size}")

    results: list[MediaResponse] = []
    failed = 0
    for item in body.items:
        if not await location_repo.exists(db, item.location_id):
            failed += 1
            continue
        row = await media_repo.create(db, item.model_dump())
        results.append(_to_response(row))

    return BatchResult(submitted=len(results), failed=failed, items=results)


async def get_or_404(db: aiosqlite.Connection, media_id: int) -> MediaResponse:
    row = await media_repo.get_by_id(db, media_id)
    if not row:
        raise HTTPException(404, "Media not found")
    return _to_response(row)


async def list_media(
    db: aiosqlite.Connection,
    location_id: Optional[int] = None,
    analyzed: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[MediaResponse]:
    if location_id is not None:
        if not await location_repo.exists(db, location_id):
            raise HTTPException(404, "Location not found")
        rows = await media_repo.list_by_location(db, location_id, analyzed, limit, offset)
    else:
        rows = await media_repo.list_all(db, analyzed, limit)
    return [_to_response(r) for r in rows]


async def run_analysis(db: aiosqlite.Connection, media_id: int) -> MediaResponse:
    row = await media_repo.get_by_id(db, media_id)
    if not row:
        raise HTTPException(404, "Media not found")
    if row["analyzed"]:
        return _to_response(row)  # idempotent — return existing result
    result = await analyze(row["source_url"])
    updated = await media_repo.save_analysis(db, media_id, result)
    return _to_response(updated)


async def run_batch_analysis(
    db: aiosqlite.Connection, location_id: Optional[int] = None
) -> dict:
    """Analyze all unanalyzed media items."""
    pending = await media_repo.get_unanalyzed(db, location_id)
    processed, failed = 0, 0
    for item in pending:
        try:
            result = await analyze(item["source_url"])
            await media_repo.save_analysis(db, item["id"], result)
            processed += 1
        except Exception:
            failed += 1
    return {"processed": processed, "failed": failed, "total_pending": len(pending)}
