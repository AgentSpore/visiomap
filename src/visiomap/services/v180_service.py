"""Visiomap v1.8.0 services — EventService, OccupancyService, LocationGroupService."""

from __future__ import annotations

from fastapi import HTTPException

from visiomap.api.v180_repo import EventRepo, LocationGroupRepo, OccupancyRepo


class EventService:
    def __init__(self, db):
        self.repo = EventRepo(db)
        self.db = db

    async def _check_location(self, location_id: int) -> None:
        r = await self.db.execute("SELECT id FROM locations WHERE id=?", (location_id,))
        if not await r.fetchone():
            raise HTTPException(status_code=404, detail=f"Location {location_id} not found")

    async def create(self, data: dict) -> dict:
        await self._check_location(data["location_id"])
        result = await self.repo.create(data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create event")
        return result

    async def get(self, event_id: int) -> dict:
        result = await self.repo.get_by_id(event_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return result

    async def list_all(
        self,
        location_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        return await self.repo.list_all(location_id, status, limit, offset)

    async def update(self, event_id: int, data: dict) -> dict:
        result = await self.repo.update(event_id, data)
        if not result:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return result

    async def delete(self, event_id: int) -> dict:
        ok = await self.repo.delete(event_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return {"deleted": True, "event_id": event_id}

    async def get_impact(self, event_id: int) -> dict:
        result = await self.repo.get_impact(event_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
        return result


class OccupancyService:
    def __init__(self, db):
        self.repo = OccupancyRepo(db)
        self.db = db

    async def _get_location_name(self, location_id: int) -> str:
        r = await self.db.execute("SELECT name FROM locations WHERE id=?", (location_id,))
        row = await r.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Location {location_id} not found")
        return row["name"]

    async def get_weekly(self, location_id: int) -> dict:
        name = await self._get_location_name(location_id)
        patterns = await self.repo.get_weekly_pattern(location_id)
        if not patterns:
            return {
                "location_id": location_id,
                "location_name": name,
                "weekly_pattern": [],
                "busiest_day": "N/A",
                "quietest_day": "N/A",
                "avg_weekly_density": 0.0,
            }
        busiest = max(patterns, key=lambda p: p["avg_density"])
        quietest = min(patterns, key=lambda p: p["avg_density"])
        avg = round(sum(p["avg_density"] for p in patterns) / len(patterns), 2)
        return {
            "location_id": location_id,
            "location_name": name,
            "weekly_pattern": patterns,
            "busiest_day": busiest["day_name"],
            "quietest_day": quietest["day_name"],
            "avg_weekly_density": avg,
        }

    async def get_seasonal(self, location_id: int, months: int = 12) -> dict:
        name = await self._get_location_name(location_id)
        trends = await self.repo.get_monthly_trends(location_id, months)
        if not trends:
            return {
                "location_id": location_id,
                "location_name": name,
                "monthly_trends": [],
                "peak_month": "N/A",
                "quietest_month": "N/A",
            }
        peak = max(trends, key=lambda t: t["avg_density"])
        quietest = min(trends, key=lambda t: t["avg_density"])
        return {
            "location_id": location_id,
            "location_name": name,
            "monthly_trends": trends,
            "peak_month": peak["month"],
            "quietest_month": quietest["month"],
        }


class LocationGroupService:
    def __init__(self, db):
        self.repo = LocationGroupRepo(db)
        self.db = db

    async def create(self, data: dict) -> dict:
        result = await self.repo.create(data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create group")
        return result

    async def get(self, group_id: int) -> dict:
        result = await self.repo.get_by_id(group_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
        return result

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[dict]:
        return await self.repo.list_all(limit, offset)

    async def update(self, group_id: int, data: dict) -> dict:
        result = await self.repo.update(group_id, data)
        if not result:
            raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
        return result

    async def delete(self, group_id: int) -> dict:
        ok = await self.repo.delete(group_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
        return {"deleted": True, "group_id": group_id}

    async def add_member(self, group_id: int, location_id: int) -> dict:
        # check group exists
        await self.get(group_id)
        # check location exists
        r = await self.db.execute("SELECT id FROM locations WHERE id=?", (location_id,))
        if not await r.fetchone():
            raise HTTPException(status_code=404, detail=f"Location {location_id} not found")
        ok = await self.repo.add_member(group_id, location_id)
        if not ok:
            raise HTTPException(
                status_code=409, detail="Location already in group or constraint error"
            )
        return {"added": True, "group_id": group_id, "location_id": location_id}

    async def remove_member(self, group_id: int, location_id: int) -> dict:
        ok = await self.repo.remove_member(group_id, location_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Membership not found")
        return {"removed": True, "group_id": group_id, "location_id": location_id}

    async def get_analytics(self, group_id: int) -> dict:
        group = await self.get(group_id)
        analytics = await self.repo.get_group_analytics(group_id)
        if not analytics:
            return {
                "group_id": group_id,
                "group_name": group["name"],
                "total_locations": 0,
                "total_media": 0,
                "avg_density": None,
                "busiest_location": None,
                "locations": [],
            }
        analytics["group_id"] = group_id
        analytics["group_name"] = group["name"]
        return analytics

    async def compare_groups(self, group_ids: list[int]) -> dict:
        groups = []
        for gid in group_ids:
            analytics = await self.get_analytics(gid)
            groups.append(analytics)
        return {"groups": groups}
