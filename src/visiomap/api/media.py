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
    AnnotationCreate,
    AnnotationResponse,
    TagSuggestionsResponse,
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


# -- v1.4.0: Media Tag Search -------------------------------------------------

@router.get("/search", response_model=list[MediaResponse])
async def search_media(
    tags: str = Query(..., description="Comma-separated tags to search for"),
    source_type: str | None = Query(None, description="Filter: photo|video|screenshot"),
    from_date: str | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500),
    svc: MediaService = Depends(_service),
):
    """Search media across all locations by tags, source type, and date range."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    if not tag_list:
        raise HTTPException(400, "Provide at least one tag")
    if source_type and source_type not in ("photo", "video", "screenshot"):
        raise HTTPException(422, "source_type must be photo, video, or screenshot")
    return await svc.search_by_tags(tag_list, source_type, from_date, to_date, limit)


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


# -- v1.5.0: Media Annotations ------------------------------------------------

@router.post("/{media_id}/annotations", response_model=AnnotationResponse, status_code=201)
async def add_annotation(media_id: int, body: AnnotationCreate, svc: MediaService = Depends(_service)):
    """Add a reviewer annotation to a media item."""
    result = await svc.create_annotation(media_id, body.text, body.author)
    if not result:
        raise HTTPException(404, "Media not found")
    return result


@router.get("/{media_id}/annotations", response_model=list[AnnotationResponse])
async def get_annotations(media_id: int, svc: MediaService = Depends(_service)):
    """Get all annotations for a media item, newest first."""
    result = await svc.list_annotations(media_id)
    if result is None:
        raise HTTPException(404, "Media not found")
    return result


@router.delete("/annotations/{annotation_id}", status_code=204)
async def remove_annotation(annotation_id: int, svc: MediaService = Depends(_service)):
    if not await svc.delete_annotation(annotation_id):
        raise HTTPException(404, "Annotation not found")


# -- v1.6.0: Media Auto-Tag Suggestions ---------------------------------------

@router.get("/{media_id}/tag-suggestions", response_model=TagSuggestionsResponse)
async def tag_suggestions(media_id: int, svc: MediaService = Depends(_service)):
    """Suggest tags for a media item based on its analysis results (environment_tags,
    weather, mood, time_of_day). Already-applied tags are excluded."""
    result = await svc.suggest_tags(media_id)
    if result is None:
        raise HTTPException(404, "Media not found")
    return result


@router.post("/{media_id}/apply-suggestions", response_model=MediaResponse)
async def apply_tag_suggestions(media_id: int, svc: MediaService = Depends(_service)):
    """Apply high-confidence tag suggestions (>= 0.7) to the media's tags field."""
    result = await svc.apply_tag_suggestions(media_id)
    if result is None:
        raise HTTPException(404, "Media not found")
    return result
