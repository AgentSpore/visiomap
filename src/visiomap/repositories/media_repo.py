from __future__ import annotations

import json
from typing import Any

import aiosqlite


class MediaRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    # -- CRUD --

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        cursor = await self.db.execute(
            """INSERT INTO media (location_id, source_url, source_type, captured_at, tags)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data["location_id"],
                data["source_url"],
                data.get("source_type", "photo"),
                data.get("captured_at"),
                json.dumps(data.get("tags", [])),
            ),
        )
        await self.db.commit()
        return await self.get_by_id(cursor.lastrowid)

    async def get_by_id(self, media_id: int) -> dict[str, Any] | None:
        cursor = await self.db.execute(
            "SELECT * FROM media WHERE id = ?", (media_id,)
        )
        row = await cursor.fetchone()
        return self._to_dict(row) if row else None

    async def list_all(
        self,
        location_id: int | None = None,
        analyzed: bool | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM media WHERE 1=1"
        params: list[Any] = []
        if location_id is not None:
            query += " AND location_id = ?"
            params.append(location_id)
        if analyzed is not None:
            query += " AND analyzed = ?"
            params.append(1 if analyzed else 0)
        query += " ORDER BY submitted_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = await self.db.execute(query, params)
        return [self._to_dict(r) for r in await cursor.fetchall()]

    async def delete(self, media_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM media WHERE id = ?", (media_id,))
        if not await cursor.fetchone():
            return False
        await self.db.execute("DELETE FROM media_annotations WHERE media_id = ?", (media_id,))
        await self.db.execute("DELETE FROM media WHERE id = ?", (media_id,))
        await self.db.commit()
        return True

    # -- Analysis --

    async def get_pending(self, location_id: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM media WHERE analyzed = 0"
        params: list[Any] = []
        if location_id is not None:
            query += " AND location_id = ?"
            params.append(location_id)
        query += " ORDER BY submitted_at ASC"
        cursor = await self.db.execute(query, params)
        return [self._to_dict(r) for r in await cursor.fetchall()]

    async def save_analysis(self, media_id: int, analysis: dict[str, Any]) -> None:
        await self.db.execute(
            "UPDATE media SET analyzed = 1, analysis_json = ? WHERE id = ?",
            (json.dumps(analysis), media_id),
        )
        await self.db.commit()

    # -- Analytics queries --

    async def count_all(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) FROM media")
        return (await cursor.fetchone())[0]

    async def count_analyzed(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) FROM media WHERE analyzed = 1")
        return (await cursor.fetchone())[0]

    async def get_avg_density(self) -> float | None:
        cursor = await self.db.execute(
            "SELECT AVG(json_extract(analysis_json, '$.crowd_density')) FROM media WHERE analyzed = 1"
        )
        row = await cursor.fetchone()
        return round(row[0], 2) if row and row[0] else None

    async def get_location_analytics(
        self,
        location_id: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any]:
        query = """SELECT
                 COUNT(*) AS total,
                 SUM(CASE WHEN analyzed = 1 THEN 1 ELSE 0 END) AS analyzed_count,
                 AVG(CASE WHEN analyzed = 1
                     THEN json_extract(analysis_json, '$.crowd_density') END) AS avg_density,
                 MAX(CASE WHEN analyzed = 1
                     THEN json_extract(analysis_json, '$.crowd_density') END) AS peak_density
               FROM media
               WHERE location_id = ?"""
        params: list[Any] = [location_id]
        if from_date:
            query += " AND submitted_at >= ?"
            params.append(from_date)
        if to_date:
            query += " AND submitted_at <= ?"
            params.append(to_date + "T23:59:59")
        cursor = await self.db.execute(query, params)
        row = await cursor.fetchone()
        return {
            "total_media": row[0] or 0,
            "analyzed_media": int(row[1] or 0),
            "avg_crowd_density": round(row[2], 2) if row[2] else None,
            "peak_crowd_density": round(row[3], 2) if row[3] else None,
        }

    async def get_analyzed_media(
        self,
        location_id: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT analysis_json FROM media WHERE location_id = ? AND analyzed = 1"
        params: list[Any] = [location_id]
        if from_date:
            query += " AND submitted_at >= ?"
            params.append(from_date)
        if to_date:
            query += " AND submitted_at <= ?"
            params.append(to_date + "T23:59:59")
        cursor = await self.db.execute(query, params)
        results = []
        for row in await cursor.fetchall():
            if row[0]:
                results.append(json.loads(row[0]))
        return results

    async def get_daily_trend(
        self,
        location_id: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        query = """SELECT date(submitted_at) AS day,
                      AVG(json_extract(analysis_json, '$.crowd_density')) AS avg_density,
                      COUNT(*) AS media_count
               FROM media
               WHERE location_id = ? AND analyzed = 1"""
        params: list[Any] = [location_id]
        if from_date:
            query += " AND submitted_at >= ?"
            params.append(from_date)
        if to_date:
            query += " AND submitted_at <= ?"
            params.append(to_date + "T23:59:59")
        query += " GROUP BY day ORDER BY day DESC LIMIT 30"
        cursor = await self.db.execute(query, params)
        return [
            {"date": r[0], "avg_density": round(r[1], 2), "media_count": r[2]}
            for r in await cursor.fetchall()
        ]

    async def get_heatmap_data(
        self,
        location_id: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT analysis_json FROM media WHERE location_id = ? AND analyzed = 1"
        params: list[Any] = [location_id]
        if from_date:
            query += " AND submitted_at >= ?"
            params.append(from_date)
        if to_date:
            query += " AND submitted_at <= ?"
            params.append(to_date + "T23:59:59")
        cursor = await self.db.execute(query, params)
        return [json.loads(r[0]) for r in await cursor.fetchall() if r[0]]

    # -- v1.4.0: Tag Search --------------------------------------------------------

    async def search_by_tags(
        self,
        tags: list[str],
        source_type: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM media WHERE 1=1"
        params: list[Any] = []

        # Build tag filter using json_each for SQLite JSON arrays
        for tag in tags:
            query += " AND EXISTS (SELECT 1 FROM json_each(tags) WHERE json_each.value = ?)"
            params.append(tag)

        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        if from_date:
            query += " AND submitted_at >= ?"
            params.append(from_date)
        if to_date:
            query += " AND submitted_at <= ?"
            params.append(to_date + "T23:59:59")

        query += " ORDER BY submitted_at DESC LIMIT ?"
        params.append(limit)

        cursor = await self.db.execute(query, params)
        return [self._to_dict(r) for r in await cursor.fetchall()]

    # -- v1.5.0: Hourly Density ----------------------------------------------------

    async def get_hourly_density(self, location_id: int) -> list[dict[str, Any]]:
        """Aggregate crowd density by hour of day (from captured_at or submitted_at)."""
        cursor = await self.db.execute(
            """SELECT
                 CAST(strftime('%%H', COALESCE(captured_at, submitted_at)) AS INTEGER) as hour,
                 AVG(json_extract(analysis_json, '$.crowd_density')) as avg_density,
                 COUNT(*) as media_count,
                 AVG(json_extract(analysis_json, '$.crowd_count_estimate')) as avg_count,
                 analysis_json
               FROM media
               WHERE location_id = ? AND analyzed = 1
               GROUP BY hour
               ORDER BY hour""",
            (location_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            # Get dominant mood for each hour bucket
            mood_cursor = await self.db.execute(
                """SELECT json_extract(analysis_json, '$.dominant_mood') as mood, COUNT(*) as cnt
                   FROM media
                   WHERE location_id = ? AND analyzed = 1
                     AND CAST(strftime('%%H', COALESCE(captured_at, submitted_at)) AS INTEGER) = ?
                   GROUP BY mood
                   ORDER BY cnt DESC
                   LIMIT 1""",
                (location_id, r[0]),
            )
            mood_row = await mood_cursor.fetchone()
            dominant_mood = mood_row[0] if mood_row else None

            results.append({
                "hour": r[0],
                "avg_density": round(r[1], 2) if r[1] else 0.0,
                "media_count": r[2],
                "avg_crowd_count": int(r[3] or 0),
                "dominant_mood": dominant_mood,
            })
        return results

    # -- v1.5.0: Annotations -------------------------------------------------------

    async def create_annotation(self, media_id: int, text: str, author: str) -> dict[str, Any] | None:
        """Create a new annotation on a media item."""
        media = await self.get_by_id(media_id)
        if not media:
            return None
        cursor = await self.db.execute(
            "INSERT INTO media_annotations (media_id, text, author) VALUES (?, ?, ?)",
            (media_id, text, author),
        )
        await self.db.commit()
        return await self.get_annotation(cursor.lastrowid)

    async def get_annotation(self, annotation_id: int) -> dict[str, Any] | None:
        cursor = await self.db.execute(
            "SELECT * FROM media_annotations WHERE id = ?", (annotation_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "media_id": row["media_id"],
            "text": row["text"],
            "author": row["author"],
            "created_at": row["created_at"],
        }

    async def list_annotations(self, media_id: int) -> list[dict[str, Any]] | None:
        media = await self.get_by_id(media_id)
        if not media:
            return None
        cursor = await self.db.execute(
            "SELECT * FROM media_annotations WHERE media_id = ? ORDER BY created_at DESC",
            (media_id,),
        )
        return [
            {
                "id": r["id"],
                "media_id": r["media_id"],
                "text": r["text"],
                "author": r["author"],
                "created_at": r["created_at"],
            }
            for r in await cursor.fetchall()
        ]

    async def delete_annotation(self, annotation_id: int) -> bool:
        cursor = await self.db.execute("SELECT 1 FROM media_annotations WHERE id = ?", (annotation_id,))
        if not await cursor.fetchone():
            return False
        await self.db.execute("DELETE FROM media_annotations WHERE id = ?", (annotation_id,))
        await self.db.commit()
        return True

    async def count_annotations(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) FROM media_annotations")
        return (await cursor.fetchone())[0]

    # -- Private --

    @staticmethod
    def _to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        analysis = None
        if row["analysis_json"]:
            analysis = json.loads(row["analysis_json"])
        return {
            "id": row["id"],
            "location_id": row["location_id"],
            "source_url": row["source_url"],
            "source_type": row["source_type"],
            "captured_at": row["captured_at"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "analyzed": bool(row["analyzed"]),
            "analysis": analysis,
            "submitted_at": row["submitted_at"],
        }
