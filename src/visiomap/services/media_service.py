from __future__ import annotations

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
