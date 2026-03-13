from __future__ import annotations

from typing import Any

from visiomap.repositories.location_repo import LocationRepo


class LocationService:
    def __init__(self, repo: LocationRepo) -> None:
        self.repo = repo

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        return await self.repo.create(data)

    async def get(self, location_id: int) -> dict[str, Any] | None:
        return await self.repo.get_by_id(location_id)

    async def list_all(self, category: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
        return await self.repo.list_all(category=category, tag=tag)

    async def update(self, location_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        return await self.repo.update(location_id, data)

    async def delete(self, location_id: int) -> bool:
        return await self.repo.delete(location_id)

    async def exists(self, location_id: int) -> bool:
        return await self.repo.exists(location_id)
