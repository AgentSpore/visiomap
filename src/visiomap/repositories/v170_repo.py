"""v1.7.0 repositories — Visitor Flows, Capacity, Zone Templates."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite


# ==============================================================================
# Flow Repository
# ==============================================================================

class FlowRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        recorded_at = data.get("recorded_at") or datetime.utcnow().isoformat()
        cursor = await self.db.execute(
            """INSERT INTO visitor_flows (from_location_id, to_location_id, visitor_count, recorded_at)
               VALUES (?, ?, ?, ?)""",
            (data["from_location_id"], data["to_location_id"],
             data["visitor_count"], recorded_at),
        )
        await self.db.commit()
        return await self.get_by_id(cursor.lastrowid)

    async def get_by_id(self, flow_id: int) -> dict[str, Any] | None:
        cursor = await self.db.execute(
            "SELECT * FROM visitor_flows WHERE id = ?", (flow_id,)
        )
        row = await cursor.fetchone()
        return self._to_dict(row) if row else None

    async def list_all(
        self,
        from_id: int | None = None,
        to_id: int | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM visitor_flows WHERE 1=1"
        params: list[Any] = []
        if from_id is not None:
            query += " AND from_location_id = ?"
            params.append(from_id)
        if to_id is not None:
            query += " AND to_location_id = ?"
            params.append(to_id)
        if since:
            query += " AND recorded_at >= ?"
            params.append(since)
        if until:
            query += " AND recorded_at <= ?"
            params.append(until + "T23:59:59")
        query += " ORDER BY recorded_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = await self.db.execute(query, params)
        return [self._to_dict(r) for r in await cursor.fetchall()]

    async def get_matrix(self) -> list[dict[str, Any]]:
        """Origin-destination matrix: aggregate total visitors per (from, to) pair."""
        cursor = await self.db.execute(
            """SELECT
                 vf.from_location_id,
                 lf.name AS from_name,
                 vf.to_location_id,
                 lt.name AS to_name,
                 SUM(vf.visitor_count) AS total_visitors,
                 COUNT(*) AS flow_count
               FROM visitor_flows vf
               JOIN locations lf ON lf.id = vf.from_location_id
               JOIN locations lt ON lt.id = vf.to_location_id
               GROUP BY vf.from_location_id, vf.to_location_id
               ORDER BY total_visitors DESC"""
        )
        return [
            {
                "from_location_id": r[0],
                "from_location_name": r[1],
                "to_location_id": r[2],
                "to_location_name": r[3],
                "total_visitors": r[4],
                "flow_count": r[5],
            }
            for r in await cursor.fetchall()
        ]

    async def get_top_routes(self, top_n: int = 10) -> list[dict[str, Any]]:
        """Top N busiest routes with average daily flow."""
        cursor = await self.db.execute(
            """SELECT
                 vf.from_location_id,
                 lf.name AS from_name,
                 vf.to_location_id,
                 lt.name AS to_name,
                 SUM(vf.visitor_count) AS total_visitors,
                 COUNT(*) AS flow_count,
                 COUNT(DISTINCT date(vf.recorded_at)) AS distinct_days
               FROM visitor_flows vf
               JOIN locations lf ON lf.id = vf.from_location_id
               JOIN locations lt ON lt.id = vf.to_location_id
               GROUP BY vf.from_location_id, vf.to_location_id
               ORDER BY total_visitors DESC
               LIMIT ?""",
            (top_n,),
        )
        return [
            {
                "from_location_id": r[0],
                "from_location_name": r[1],
                "to_location_id": r[2],
                "to_location_name": r[3],
                "total_visitors": r[4],
                "flow_count": r[5],
                "avg_daily_flow": round(r[4] / max(r[6], 1), 1),
            }
            for r in await cursor.fetchall()
        ]

    async def get_inbound(self, location_id: int) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            """SELECT
                 vf.from_location_id,
                 lf.name AS from_name,
                 SUM(vf.visitor_count) AS total_visitors,
                 COUNT(*) AS flow_count
               FROM visitor_flows vf
               JOIN locations lf ON lf.id = vf.from_location_id
               WHERE vf.to_location_id = ?
               GROUP BY vf.from_location_id
               ORDER BY total_visitors DESC""",
            (location_id,),
        )
        return [
            {
                "from_location_id": r[0],
                "from_location_name": r[1],
                "total_visitors": r[2],
                "flow_count": r[3],
            }
            for r in await cursor.fetchall()
        ]

    async def get_outbound(self, location_id: int) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            """SELECT
                 vf.to_location_id,
                 lt.name AS to_name,
                 SUM(vf.visitor_count) AS total_visitors,
                 COUNT(*) AS flow_count
               FROM visitor_flows vf
               JOIN locations lt ON lt.id = vf.to_location_id
               WHERE vf.from_location_id = ?
               GROUP BY vf.to_location_id
               ORDER BY total_visitors DESC""",
            (location_id,),
        )
        return [
            {
                "to_location_id": r[0],
                "to_location_name": r[1],
                "total_visitors": r[2],
                "flow_count": r[3],
            }
            for r in await cursor.fetchall()
        ]

    @staticmethod
    def _to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "from_location_id": row["from_location_id"],
            "to_location_id": row["to_location_id"],
            "visitor_count": row["visitor_count"],
            "recorded_at": row["recorded_at"],
            "created_at": row["created_at"],
        }


# ==============================================================================
# Capacity Repository
# ==============================================================================

class CapacityRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def _ensure_column(self) -> None:
        cursor = await self.db.execute("PRAGMA table_info(locations)")
        cols = [r[1] for r in await cursor.fetchall()]
        if "max_capacity" not in cols:
            await self.db.execute("ALTER TABLE locations ADD COLUMN max_capacity INTEGER")
            await self.db.commit()

    async def set_capacity(self, location_id: int, max_capacity: int) -> bool:
        await self._ensure_column()
        cursor = await self.db.execute("SELECT 1 FROM locations WHERE id = ?", (location_id,))
        if not await cursor.fetchone():
            return False
        await self.db.execute(
            "UPDATE locations SET max_capacity = ? WHERE id = ?",
            (max_capacity, location_id),
        )
        await self.db.commit()
        return True

    async def get_capacity(self, location_id: int) -> dict[str, Any] | None:
        await self._ensure_column()
        cursor = await self.db.execute(
            """SELECT l.id, l.name, l.max_capacity,
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
        max_cap = row[2]
        avg_density = row[3]
        if max_cap is not None and avg_density is not None:
            # crowd_density is on 0-10 scale; crowd_density_score = avg_density * 10
            current_estimate = round(avg_density * max_cap / 10.0, 1)
            utilization_pct = round(current_estimate / max_cap * 100, 1)
        else:
            current_estimate = None
            utilization_pct = None
        return {
            "location_id": row[0],
            "location_name": row[1],
            "max_capacity": max_cap,
            "current_crowd_estimate": current_estimate,
            "utilization_pct": utilization_pct,
        }

    async def get_all_with_capacity(self) -> list[dict[str, Any]]:
        """Return all locations that have max_capacity set, with utilization info."""
        await self._ensure_column()
        cursor = await self.db.execute(
            """SELECT l.id, l.name, l.category, l.max_capacity,
                      AVG(CASE WHEN m.analyzed = 1
                          THEN json_extract(m.analysis_json, '$.crowd_density') END) AS avg_density
               FROM locations l
               LEFT JOIN media m ON m.location_id = l.id
               WHERE l.max_capacity IS NOT NULL
               GROUP BY l.id
               ORDER BY l.id"""
        )
        results = []
        for row in await cursor.fetchall():
            max_cap = row[3]
            avg_density = row[4]
            if max_cap and avg_density is not None:
                current_estimate = round(avg_density * max_cap / 10.0, 1)
                utilization_pct = round(current_estimate / max_cap * 100, 1)
            else:
                current_estimate = 0.0
                utilization_pct = 0.0
            results.append({
                "location_id": row[0],
                "location_name": row[1],
                "category": row[2] or "other",
                "max_capacity": max_cap,
                "current_crowd_estimate": current_estimate,
                "utilization_pct": utilization_pct,
            })
        # Sort by utilization descending
        results.sort(key=lambda r: r["utilization_pct"], reverse=True)
        return results


# ==============================================================================
# Zone Template Repository
# ==============================================================================

class ZoneTemplateRepo:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow().isoformat()
        cursor = await self.db.execute(
            """INSERT INTO zone_templates (name, default_category, default_tags, analysis_config, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["name"],
                data.get("default_category", "other"),
                json.dumps(data.get("default_tags", [])),
                json.dumps(data.get("analysis_config", {})),
                now,
                now,
            ),
        )
        await self.db.commit()
        return await self.get_by_id(cursor.lastrowid)

    async def get_by_id(self, template_id: int) -> dict[str, Any] | None:
        cursor = await self.db.execute(
            "SELECT * FROM zone_templates WHERE id = ?", (template_id,)
        )
        row = await cursor.fetchone()
        return self._to_dict(row) if row else None

    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            "SELECT * FROM zone_templates ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [self._to_dict(r) for r in await cursor.fetchall()]

    async def update(self, template_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        existing = await self.get_by_id(template_id)
        if not existing:
            return None
        fields: dict[str, Any] = {}
        for k, v in data.items():
            if v is not None:
                if k == "default_tags":
                    fields[k] = json.dumps(v)
                elif k == "analysis_config":
                    fields[k] = json.dumps(v)
                else:
                    fields[k] = v
        if not fields:
            return existing
        fields["updated_at"] = datetime.utcnow().isoformat()
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [template_id]
        await self.db.execute(f"UPDATE zone_templates SET {sets} WHERE id = ?", vals)
        await self.db.commit()
        return await self.get_by_id(template_id)

    async def delete(self, template_id: int) -> bool:
        cursor = await self.db.execute(
            "SELECT 1 FROM zone_templates WHERE id = ?", (template_id,)
        )
        if not await cursor.fetchone():
            return False
        await self.db.execute("DELETE FROM zone_templates WHERE id = ?", (template_id,))
        await self.db.commit()
        return True

    async def count_applied_locations(self, template_id: int) -> int:
        cursor = await self.db.execute(
            "SELECT COUNT(*) FROM zone_template_locations WHERE template_id = ?",
            (template_id,),
        )
        return (await cursor.fetchone())[0]

    async def get_applied_locations(self, template_id: int) -> list[dict[str, Any]]:
        cursor = await self.db.execute(
            """SELECT l.id, l.name, l.lat, l.lng, l.category, l.tags, ztl.applied_at
               FROM zone_template_locations ztl
               JOIN locations l ON l.id = ztl.location_id
               WHERE ztl.template_id = ?
               ORDER BY ztl.applied_at DESC""",
            (template_id,),
        )
        return [
            {
                "id": r[0],
                "name": r[1],
                "lat": r[2],
                "lng": r[3],
                "category": r[4] or "other",
                "tags": json.loads(r[5]) if r[5] else [],
                "applied_at": r[6],
            }
            for r in await cursor.fetchall()
        ]

    async def apply_to_location(self, template_id: int, location_id: int) -> bool:
        """Link template to location (upsert). Returns True on success."""
        try:
            await self.db.execute(
                """INSERT OR REPLACE INTO zone_template_locations (template_id, location_id, applied_at)
                   VALUES (?, ?, datetime('now'))""",
                (template_id, location_id),
            )
            await self.db.commit()
            return True
        except Exception:
            return False

    async def is_applied_anywhere(self, template_id: int) -> bool:
        count = await self.count_applied_locations(template_id)
        return count > 0

    @staticmethod
    def _to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "default_category": row["default_category"],
            "default_tags": json.loads(row["default_tags"]) if row["default_tags"] else [],
            "analysis_config": json.loads(row["analysis_config"]) if row["analysis_config"] else {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
