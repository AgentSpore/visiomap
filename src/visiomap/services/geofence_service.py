from __future__ import annotations

import json
from typing import Any

import aiosqlite


class GeofenceService:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        polygon_json = json.dumps([{"lat": p["lat"], "lng": p["lng"]} for p in data["polygon"]])
        cursor = await self.db.execute(
            "INSERT INTO geofences (name, description, polygon) VALUES (?, ?, ?)",
            (data["name"], data.get("description"), polygon_json),
        )
        await self.db.commit()
        return await self.get(cursor.lastrowid)

    async def get(self, geofence_id: int) -> dict[str, Any] | None:
        cursor = await self.db.execute("SELECT * FROM geofences WHERE id = ?", (geofence_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return await self._to_dict(row)

    async def list_all(self) -> list[dict[str, Any]]:
        cursor = await self.db.execute("SELECT * FROM geofences ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [await self._to_dict(r) for r in rows]

    async def delete(self, geofence_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM geofences WHERE id = ?", (geofence_id,))
        if not await cursor.fetchone():
            return False
        await self.db.execute("DELETE FROM geofences WHERE id = ?", (geofence_id,))
        await self.db.commit()
        return True

    async def check_point(self, geofence_id: int, lat: float, lng: float) -> dict[str, Any] | None:
        fence = await self.get(geofence_id)
        if not fence:
            return None
        polygon = fence["polygon"]
        inside = self._point_in_polygon(lat, lng, polygon)
        return {
            "geofence_id": fence["id"],
            "geofence_name": fence["name"],
            "point": {"lat": lat, "lng": lng},
            "inside": inside,
        }

    async def get_locations_inside(self, geofence_id: int) -> list[dict[str, Any]]:
        cursor = await self.db.execute("SELECT polygon FROM geofences WHERE id = ?", (geofence_id,))
        row = await cursor.fetchone()
        if not row:
            return []
        polygon = json.loads(row["polygon"])
        loc_cursor = await self.db.execute("SELECT id, name, lat, lng FROM locations")
        results = []
        for loc in await loc_cursor.fetchall():
            if self._point_in_polygon(loc["lat"], loc["lng"], polygon):
                results.append({"id": loc["id"], "name": loc["name"], "lat": loc["lat"], "lng": loc["lng"]})
        return results

    @staticmethod
    def _point_in_polygon(lat: float, lng: float, polygon: list[dict]) -> bool:
        """Ray casting algorithm for point-in-polygon check."""
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            yi, xi = polygon[i]["lat"], polygon[i]["lng"]
            yj, xj = polygon[j]["lat"], polygon[j]["lng"]
            if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    async def _to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        polygon = json.loads(row["polygon"])
        locations_inside = await self._count_locations_inside(row["id"], polygon)
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "polygon": polygon,
            "vertex_count": len(polygon),
            "locations_inside": locations_inside,
            "created_at": row["created_at"],
        }

    async def _count_locations_inside(self, geofence_id: int, polygon: list[dict]) -> int:
        cursor = await self.db.execute("SELECT lat, lng FROM locations")
        count = 0
        for loc in await cursor.fetchall():
            if self._point_in_polygon(loc["lat"], loc["lng"], polygon):
                count += 1
        return count
