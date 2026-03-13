from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from visiomap.analyzer import VisionAnalyzer
from visiomap.database import get_db
from visiomap.repositories import LocationRepo, MediaRepo
from visiomap.schemas.media import (
    AnalyzeAllResponse,
    MediaBatchCreate,
    MediaBatchResponse,
    MediaCreate,
    MediaResponse,
)
from visiomap.services import MediaService

router = APIRouter(prefix="/media", tags=["media"])

_analyzer = VisionAnalyzer()


def _service(db=Depends(get_db)) -> MediaService:
    return MediaService(MediaRepo(db), LocationRepo(db), _analyzer)


@router.post("", response_model=MediaResponse, status_code=201)
async def submit_media(body: MediaCreate, svc: MediaService = Depends(_service)):
    result = await svc.submit(body.model_dump())
    if not result:
        raise HTTPException(404, "Location not found")
    return result


@router.post("/batch", response_model=MediaBatchResponse, status_code=201)
async def submit_batch(body: MediaBatchCreate, svc: MediaService = Depends(_service)):
    items = await svc.submit_batch([i.model_dump() for i in body.items])
    return {"created": len(items), "items": items}


@router.get("", response_model=list[MediaResponse])
async def list_media(
    location_id: int | None = Query(None),
    analyzed: bool | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    svc: MediaService = Depends(_service),
):
    return await svc.list_all(location_id, analyzed, limit, offset)


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(media_id: int, svc: MediaService = Depends(_service)):
    media = await svc.get(media_id)
    if not media:
        raise HTTPException(404, "Media not found")
    return media


@router.delete("/{media_id}", status_code=204)
async def delete_media(media_id: int, svc: MediaService = Depends(_service)):
    if not await svc.delete(media_id):
        raise HTTPException(404, "Media not found")


@router.post("/{media_id}/analyze", response_model=MediaResponse)
async def analyze_media(media_id: int, svc: MediaService = Depends(_service)):
    try:
        result = await svc.analyze_one(media_id)
    except Exception as e:
        raise HTTPException(502, f"Analysis failed: {e}")
    if not result:
        raise HTTPException(404, "Media not found")
    return result


@router.post("/analyze/all", response_model=AnalyzeAllResponse)
async def analyze_all(
    location_id: int | None = Query(None),
    svc: MediaService = Depends(_service),
):
    return await svc.analyze_all(location_id)
