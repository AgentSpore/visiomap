from __future__ import annotations

import json
from typing import Any

import aiosqlite


class LocationRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    # -- ensure category column exists (migration) ---
    async def _ensure_category(self) -> None:
        cursor = await self.db.execute("PRAGMA table_info(locations)")
        cols = [r[1] for r in await cursor.fetchall()]
        if "category" not in cols:
            await self.db.execute("ALTER TABLE locations ADD COLUMN category TEXT NOT NULL DEFAULT 'other'")
            await self.db.commit()

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_category()
        cursor = await self.db.execute(
            """INSERT INTO locations (name, lat, lng, radius_m, category, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (data["name"], data["lat"], data["lng"], data["radius_m"],
             data.get("category", "other"), data.get("description")),
        )
        await self.db.commit()
        return await self.get_by_id(cursor.lastrowid)

    async def get_by_id(self, location_id: int) -> dict[str, Any] | None:
        await self._ensure_category()
        cursor = await self.db.execute(
            """SELECT l.id, l.name, l.lat, l.lng, l.radius_m, l.category, l.description, l.created_at,
                      COUNT(m.id) AS media_count,
                      SUM(CASE WHEN m.analyzed = 1 THEN 1 ELSE 0 END) AS analyzed_count,
                      AVG(CASE WHEN m.analyzed = 1
                          THEN json_extract(m.analysis_json, '$.crowd_density') END) AS avg_density
               FROM locations l
               LEFT JOIN media m ON m.location_id = l.id
               WHERE l.id = ?
               GROUP BY l.id""",
            (location_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._to_dict(row)

    async def list_all(self, category: str | None = None) -> list[dict[str, Any]]:
        await self._ensure_category()
        query = """SELECT l.id, l.name, l.lat, l.lng, l.radius_m, l.category, l.description, l.created_at,
                      COUNT(m.id) AS media_count,
                      SUM(CASE WHEN m.analyzed = 1 THEN 1 ELSE 0 END) AS analyzed_count,
                      AVG(CASE WHEN m.analyzed = 1
                          THEN json_extract(m.analysis_json, '$.crowd_density') END) AS avg_density
               FROM locations l
               LEFT JOIN media m ON m.location_id = l.id"""
        params: list[Any] = []
        if category:
            query += " WHERE l.category = ?"
            params.append(category)
        query += " GROUP BY l.id ORDER BY l.created_at DESC"
        cursor = await self.db.execute(query, params)
        return [self._to_dict(r) for r in await cursor.fetchall()]

    async def update(self, location_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        existing = await self.get_by_id(location_id)
        if not existing:
            return None
        fields = {k: v for k, v in data.items() if v is not None}
        if not fields:
            return existing
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [location_id]
        await self.db.execute(f"UPDATE locations SET {sets} WHERE id = ?", vals)
        await self.db.commit()
        return await self.get_by_id(location_id)

    async def delete(self, location_id: int) -> bool:
        cursor = await self.db.execute("SELECT id FROM locations WHERE id = ?", (location_id,))
        if not await cursor.fetchone():
            return False
        await self.db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        await self.db.commit()
        return True

    async def exists(self, location_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM locations WHERE id = ?", (location_id,))
        return await cursor.fetchone() is not None

    async def get_busiest(self) -> str | None:
        cursor = await self.db.execute(
            """SELECT l.name
               FROM locations l
               JOIN media m ON m.location_id = l.id AND m.analyzed = 1
               GROUP BY l.id
               ORDER BY AVG(json_extract(m.analysis_json, '$.crowd_density')) DESC
               LIMIT 1"""
        )
        row = await cursor.fetchone()
        return row[0] if row else None

    async def get_summary(self) -> list[dict[str, Any]]:
        await self._ensure_category()
        cursor = await self.db.execute(
            """SELECT l.id, l.name, l.category,
                      COUNT(m.id) AS media_count,
                      SUM(CASE WHEN m.analyzed = 1 THEN 1 ELSE 0 END) AS analyzed_count,
                      AVG(CASE WHEN m.analyzed = 1
                          THEN json_extract(m.analysis_json, '$.crowd_density') END) AS avg_density
               FROM locations l
               LEFT JOIN media m ON m.location_id = l.id
               GROUP BY l.id
               ORDER BY avg_density DESC NULLS LAST"""
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "name": r[1],
                "category": r[2] or "other",
                "media_count": r[3] or 0,
                "analyzed_count": int(r[4] or 0),
                "avg_crowd_density": round(r[5], 2) if r[5] else None,
            }
            for r in rows
        ]

    @staticmethod
    def _to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "id": row[0],
            "name": row[1],
            "lat": row[2],
            "lng": row[3],
            "radius_m": row[4],
            "category": row[5] or "other",
            "description": row[6],
            "created_at": row[7],
            "media_count": row[8] or 0,
            "analyzed_count": int(row[9] or 0),
            "avg_crowd_density": round(row[10], 2) if row[10] else None,
        }
