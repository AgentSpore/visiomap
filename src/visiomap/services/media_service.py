from __future__ import annotations

import json
import logging
from typing import Any

from visiomap.analyzer.vision import VisionAnalyzer
from visiomap.repositories.location_repo import LocationRepo
from visiomap.repositories.media_repo import MediaRepo

logger = logging.getLogger(__name__)


class MediaService:
    def __init__(
        self,
        media_repo: MediaRepo,
        location_repo: LocationRepo,
        analyzer: VisionAnalyzer,
    ) -> None:
        self.media_repo = media_repo
        self.location_repo = location_repo
        self.analyzer = analyzer

    async def submit(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if not await self.location_repo.exists(data["location_id"]):
            return None
        return await self.media_repo.create(data)

    async def submit_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for item in items:
            if not await self.location_repo.exists(item["location_id"]):
                continue
            media = await self.media_repo.create(item)
            results.append(media)
        return results

    async def get(self, media_id: int) -> dict[str, Any] | None:
        return await self.media_repo.get_by_id(media_id)

    async def list_all(
        self,
        location_id: int | None = None,
        analyzed: bool | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.media_repo.list_all(location_id, analyzed, limit, offset)

    async def delete(self, media_id: int) -> bool:
        return await self.media_repo.delete(media_id)

    async def analyze_one(self, media_id: int) -> dict[str, Any] | None:
        media = await self.media_repo.get_by_id(media_id)
        if not media:
            return None
        try:
            result = await self.analyzer.analyze(media["source_url"])
            await self.media_repo.save_analysis(media_id, result)
            return await self.media_repo.get_by_id(media_id)
        except Exception as e:
            logger.error("Analysis failed for media %d: %s", media_id, e)
            raise

    async def analyze_all(
        self, location_id: int | None = None
    ) -> dict[str, Any]:
        pending = await self.media_repo.get_pending(location_id)
        analyzed = 0
        failed = 0
        errors: list[str] = []

        for media in pending:
            try:
                result = await self.analyzer.analyze(media["source_url"])
                await self.media_repo.save_analysis(media["id"], result)
                analyzed += 1
            except Exception as e:
                failed += 1
                errors.append(f"media {media['id']}: {e}")
                logger.error("Analysis failed for media %d: %s", media["id"], e)

        return {"analyzed": analyzed, "failed": failed, "errors": errors}

    # -- v1.4.0: Media Search by Tags ---------------------------------------------

    async def search_by_tags(
        self,
        tags: list[str],
        source_type: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return await self.media_repo.search_by_tags(
            tags, source_type, from_date, to_date, limit,
        )

    # -- v1.5.0: Annotations -------------------------------------------------------

    async def create_annotation(self, media_id: int, text: str, author: str) -> dict[str, Any] | None:
        return await self.media_repo.create_annotation(media_id, text, author)

    async def list_annotations(self, media_id: int) -> list[dict[str, Any]] | None:
        return await self.media_repo.list_annotations(media_id)

    async def delete_annotation(self, annotation_id: int) -> bool:
        return await self.media_repo.delete_annotation(annotation_id)

    # -- v1.6.0: Media Auto-Tag Suggestions ----------------------------------------

    async def suggest_tags(self, media_id: int) -> dict[str, Any] | None:
        """Parse analysis results and suggest tags based on environment_tags,
        weather, dominant_mood, and time_of_day. Exclude already-applied tags.

        Returns:
            Tag suggestions dict or None if media not found / not analyzed.
        """
        media = await self.media_repo.get_by_id(media_id)
        if not media:
            return None

        analysis = media.get("analysis")
        if not analysis:
            return {
                "media_id": media_id,
                "suggestions": [],
                "auto_applicable_count": 0,
            }

        existing_tags = set(t.lower() for t in (media.get("tags") or []))

        suggestions = []

        # Source 1: environment_tags — high confidence
        for env_tag in analysis.get("environment_tags", []):
            tag_lower = env_tag.lower()
            if tag_lower not in existing_tags:
                suggestions.append({
                    "tag": tag_lower,
                    "source": "environment_tags",
                    "confidence": round(analysis.get("confidence", 0.8), 2),
                })

        # Source 2: weather
        weather = analysis.get("weather")
        if weather:
            tag_lower = weather.lower()
            if tag_lower not in existing_tags:
                suggestions.append({
                    "tag": tag_lower,
                    "source": "weather",
                    "confidence": round(min(analysis.get("confidence", 0.7), 0.9), 2),
                })

        # Source 3: dominant_mood
        mood = analysis.get("dominant_mood")
        if mood:
            tag_lower = f"mood:{mood.lower()}"
            if tag_lower not in existing_tags:
                suggestions.append({
                    "tag": tag_lower,
                    "source": "dominant_mood",
                    "confidence": round(min(analysis.get("confidence", 0.6), 0.85), 2),
                })

        # Source 4: time_of_day
        tod = analysis.get("time_of_day")
        if tod:
            tag_lower = tod.lower()
            if tag_lower not in existing_tags:
                suggestions.append({
                    "tag": tag_lower,
                    "source": "time_of_day",
                    "confidence": round(min(analysis.get("confidence", 0.7), 0.9), 2),
                })

        # Sort by confidence descending
        suggestions.sort(key=lambda s: s["confidence"], reverse=True)

        # Auto-applicable: confidence >= 0.7
        auto_applicable = sum(1 for s in suggestions if s["confidence"] >= 0.7)

        return {
            "media_id": media_id,
            "suggestions": suggestions,
            "auto_applicable_count": auto_applicable,
        }

    async def apply_tag_suggestions(self, media_id: int) -> dict[str, Any] | None:
        """Apply top tag suggestions (confidence >= 0.7) to the media's tags field.

        Returns:
            Updated media dict or None if media not found.
        """
        suggestions_result = await self.suggest_tags(media_id)
        if suggestions_result is None:
            return None

        media = await self.media_repo.get_by_id(media_id)
        if not media:
            return None

        current_tags = list(media.get("tags") or [])
        current_tags_lower = set(t.lower() for t in current_tags)

        applied = 0
        for suggestion in suggestions_result["suggestions"]:
            if suggestion["confidence"] >= 0.7 and suggestion["tag"] not in current_tags_lower:
                current_tags.append(suggestion["tag"])
                current_tags_lower.add(suggestion["tag"])
                applied += 1

        if applied > 0:
            await self.media_repo.update_tags(media_id, current_tags)

        return await self.media_repo.get_by_id(media_id)
