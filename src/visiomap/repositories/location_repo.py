import json
from datetime import datetime
from typing import Optional

import aiosqlite


def _row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


async def create(db: aiosqlite.Connection, data: dict) -> dict:
    now = datetime.utcnow().isoformat()
    cur = await db.execute(
        """INSERT INTO locations (name, lat, lng, radius_m, description, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data["name"], data["lat"], data["lng"],
         data.get("radius_m", 500), data.get("description"), now),
    )
    await db.commit()
    return await get_by_id(db, cur.lastrowid)


async def get_by_id(db: aiosqlite.Connection, location_id: int) -> Optional[dict]:
    row = await (await db.execute(
        """SELECT l.*,
                  COUNT(m.id)         AS media_count,
                  SUM(m.analyzed)     AS analyzed_count,
                  AVG(m.crowd_density) AS avg_crowd_density
           FROM locations l
           LEFT JOIN media m ON m.location_id = l.id
           WHERE l.id = ?
           GROUP BY l.id""",
        (location_id,),
    )).fetchone()
    return _row_to_dict(row) if row else None


async def list_all(db: aiosqlite.Connection) -> list[dict]:
    rows = await (await db.execute(
        """SELECT l.*,
                  COUNT(m.id)          AS media_count,
                  SUM(m.analyzed)      AS analyzed_count,
                  AVG(m.crowd_density) AS avg_crowd_density
           FROM locations l
           LEFT JOIN media m ON m.location_id = l.id
           GROUP BY l.id
           ORDER BY l.id DESC"""
    )).fetchall()
    return [_row_to_dict(r) for r in rows]


async def update(db: aiosqlite.Connection, location_id: int, updates: dict) -> Optional[dict]:
    allowed = {"name", "radius_m", "description"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return await get_by_id(db, location_id)
    set_clause = ", ".join(f"{k}=?" for k in fields)
    cur = await db.execute(
        f"UPDATE locations SET {set_clause} WHERE id=?",
        [*fields.values(), location_id],
    )
    await db.commit()
    return await get_by_id(db, location_id) if cur.rowcount else None


async def delete(db: aiosqlite.Connection, location_id: int) -> bool:
    cur = await db.execute("DELETE FROM locations WHERE id=?", (location_id,))
    await db.commit()
    return cur.rowcount > 0


async def exists(db: aiosqlite.Connection, location_id: int) -> bool:
    row = await (await db.execute(
        "SELECT 1 FROM locations WHERE id=?", (location_id,)
    )).fetchone()
    return row is not None
