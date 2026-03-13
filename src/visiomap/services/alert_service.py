from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiosqlite


class AlertService:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def _ensure_table(self) -> None:
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS density_alerts (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
                threshold     REAL    NOT NULL CHECK (threshold BETWEEN 0 AND 100),
                webhook_url   TEXT    NOT NULL,
                label         TEXT,
                fired_count   INTEGER NOT NULL DEFAULT 0,
                last_fired_at TEXT,
                active        INTEGER NOT NULL DEFAULT 1,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_table()
        loc = await self.db.execute("SELECT 1 FROM locations WHERE id = ?", (data["location_id"],))
        if not await loc.fetchone():
            raise ValueError("Location not found")
        cursor = await self.db.execute(
            "INSERT INTO density_alerts (location_id, threshold, webhook_url, label) VALUES (?,?,?,?)",
            (data["location_id"], data["threshold"], data["webhook_url"], data.get("label")),
        )
        await self.db.commit()
        return await self.get(cursor.lastrowid)

    async def get(self, alert_id: int) -> dict[str, Any] | None:
        await self._ensure_table()
        cursor = await self.db.execute("SELECT * FROM density_alerts WHERE id = ?", (alert_id,))
        row = await cursor.fetchone()
        return self._to_dict(row) if row else None

    async def list_all(self, location_id: int | None = None) -> list[dict[str, Any]]:
        await self._ensure_table()
        query = "SELECT * FROM density_alerts"
        params: list[Any] = []
        if location_id is not None:
            query += " WHERE location_id = ?"
            params.append(location_id)
        query += " ORDER BY created_at DESC"
        cursor = await self.db.execute(query, params)
        return [self._to_dict(r) for r in await cursor.fetchall()]

    async def update(self, alert_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        await self._ensure_table()
        existing = await self.get(alert_id)
        if not existing:
            return None
        fields = {k: v for k, v in updates.items() if v is not None}
        if "active" in fields:
            fields["active"] = int(fields["active"])
        if not fields:
            return existing
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [alert_id]
        await self.db.execute(f"UPDATE density_alerts SET {set_clause} WHERE id = ?", values)
        await self.db.commit()
        return await self.get(alert_id)

    async def delete(self, alert_id: int) -> bool:
        await self._ensure_table()
        cursor = await self.db.execute("SELECT 1 FROM density_alerts WHERE id = ?", (alert_id,))
        if not await cursor.fetchone():
            return False
        await self.db.execute("DELETE FROM density_alerts WHERE id = ?", (alert_id,))
        await self.db.commit()
        return True

    async def check_and_fire(self, location_id: int, density: float) -> list[dict]:
        await self._ensure_table()
        cursor = await self.db.execute(
            "SELECT * FROM density_alerts WHERE location_id = ? AND active = 1 AND threshold <= ?",
            (location_id, density),
        )
        triggered = []
        now = datetime.now(timezone.utc).isoformat()
        for row in await cursor.fetchall():
            await self.db.execute(
                "UPDATE density_alerts SET fired_count = fired_count + 1, last_fired_at = ? WHERE id = ?",
                (now, row["id"]),
            )
            triggered.append({
                "alert_id": row["id"],
                "webhook_url": row["webhook_url"],
                "threshold": row["threshold"],
                "actual_density": density,
            })
        if triggered:
            await self.db.commit()
        return triggered

    @staticmethod
    def _to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "location_id": row["location_id"],
            "threshold": row["threshold"],
            "webhook_url": row["webhook_url"],
            "label": row["label"],
            "fired_count": row["fired_count"],
            "last_fired_at": row["last_fired_at"],
            "active": bool(row["active"]),
            "created_at": row["created_at"],
        }
