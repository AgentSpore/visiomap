from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from visiomap.database import get_db
from visiomap.schemas.media import MediaSubmit, BatchSubmit, MediaResponse, BatchResult
from visiomap.services import media_service

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def submit_media(body: MediaSubmit, db=Depends(get_db)):
    """Submit a photo/video URL for a location. Analysis runs separately."""
    return await media_service.submit(db, body)


@router.post("/batch", response_model=BatchResult, status_code=status.HTTP_201_CREATED)
async def submit_batch(body: BatchSubmit, db=Depends(get_db)):
    """Submit up to 50 media items in one request."""
    return await media_service.submit_batch(db, body)


@router.get("", response_model=list[MediaResponse])
async def list_media(
    location_id: Optional[int] = Query(None),
    analyzed: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    """List media. Filter by location and/or analysis status."""
    return await media_service.list_media(db, location_id, analyzed, limit, offset)


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(media_id: int, db=Depends(get_db)):
    """Get single media item with full analysis result."""
    return await media_service.get_or_404(db, media_id)


@router.post("/{media_id}/analyze", response_model=MediaResponse)
async def analyze_media(media_id: int, db=Depends(get_db)):
    """Trigger AI vision analysis for a single media item. Idempotent."""
    return await media_service.run_analysis(db, media_id)


@router.post("/analyze/all", status_code=status.HTTP_202_ACCEPTED)
async def analyze_all(
    location_id: Optional[int] = Query(None),
    db=Depends(get_db),
):
    """Trigger analysis for all unanalyzed media (optionally filtered by location)."""
    return await media_service.run_batch_analysis(db, location_id)
