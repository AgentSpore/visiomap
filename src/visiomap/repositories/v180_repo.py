"""Visiomap v1.8.0 repositories — EventRepo, OccupancyRepo, LocationGroupRepo."""

from __future__ import annotations

from datetime import datetime, timedelta


class EventRepo:
    def __init__(self, db):
        self.db = db

    async def create(self, data: dict) -> dict | None:
        r = await self.db.execute(
            "INSERT INTO events (location_id, name, description, event_type, "
            "expected_crowd, start_time, end_time) VALUES (?,?,?,?,?,?,?)",
            (
                data["location_id"],
                data["name"],
                data.get("description"),
                data.get("event_type", "general"),
                data.get("expected_crowd", 100),
                data["start_time"],
                data["end_time"],
            ),
        )
        await self.db.commit()
        return await self.get_by_id(r.lastrowid)

    async def get_by_id(self, event_id: int) -> dict | None:
        r = await self.db.execute("SELECT * FROM events WHERE id=?", (event_id,))
        row = await r.fetchone()
        if not row:
            return None
        d = dict(row)
        if d["actual_crowd"] and d["expected_crowd"]:
            d["crowd_accuracy_pct"] = round(
                100 - abs(d["actual_crowd"] - d["expected_crowd"]) / d["expected_crowd"] * 100, 1
            )
        else:
            d["crowd_accuracy_pct"] = None
        return d

    async def list_all(
        self,
        location_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        clauses: list[str] = []
        vals: list = []
        if location_id is not None:
            clauses.append("location_id=?")
            vals.append(location_id)
        if status is not None:
            clauses.append("status=?")
            vals.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        r = await self.db.execute(
            f"SELECT * FROM events{where} ORDER BY start_time DESC LIMIT ? OFFSET ?",
            vals + [limit, offset],
        )
        results = []
        for row in await r.fetchall():
            d = dict(row)
            if d["actual_crowd"] and d["expected_crowd"]:
                d["crowd_accuracy_pct"] = round(
                    100 - abs(d["actual_crowd"] - d["expected_crowd"]) / d["expected_crowd"] * 100,
                    1,
                )
            else:
                d["crowd_accuracy_pct"] = None
            results.append(d)
        return results

    async def update(self, event_id: int, data: dict) -> dict | None:
        event = await self.get_by_id(event_id)
        if not event:
            return None
        allowed = {"name", "description", "expected_crowd", "actual_crowd", "status"}
        sets: list[str] = []
        vals: list = []
        for k, v in data.items():
            if k in allowed and v is not None:
                sets.append(f"{k}=?")
                vals.append(v)
        if not sets:
            return event
        vals.append(event_id)
        await self.db.execute(f"UPDATE events SET {','.join(sets)} WHERE id=?", vals)
        await self.db.commit()
        return await self.get_by_id(event_id)

    async def delete(self, event_id: int) -> bool:
        r = await self.db.execute("DELETE FROM events WHERE id=?", (event_id,))
        await self.db.commit()
        return r.rowcount > 0

    async def get_impact(self, event_id: int) -> dict | None:
        event = await self.get_by_id(event_id)
        if not event:
            return None
        # avg density during event
        r = await self.db.execute(
            """
            SELECT AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d
            FROM media WHERE location_id=? AND analyzed=1
              AND submitted_at BETWEEN ? AND ?
            """,
            (event["location_id"], event["start_time"], event["end_time"]),
        )
        during = await r.fetchone()
        # avg density 7 days before event
        before_start = (
            datetime.fromisoformat(event["start_time"]) - timedelta(days=7)
        ).isoformat()
        r2 = await self.db.execute(
            """
            SELECT AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d
            FROM media WHERE location_id=? AND analyzed=1
              AND submitted_at BETWEEN ? AND ?
            """,
            (event["location_id"], before_start, event["start_time"]),
        )
        before = await r2.fetchone()

        avg_during = round(during["avg_d"], 2) if during and during["avg_d"] else None
        avg_before = round(before["avg_d"], 2) if before and before["avg_d"] else None
        increase = None
        if avg_during is not None and avg_before is not None and avg_before > 0:
            increase = round((avg_during - avg_before) / avg_before * 100, 1)

        loc = await self.db.execute(
            "SELECT name FROM locations WHERE id=?", (event["location_id"],)
        )
        loc_row = await loc.fetchone()

        return {
            "event_id": event_id,
            "event_name": event["name"],
            "location_name": loc_row["name"] if loc_row else "Unknown",
            "expected_crowd": event["expected_crowd"],
            "actual_crowd": event["actual_crowd"],
            "avg_density_during": avg_during,
            "avg_density_before": avg_before,
            "density_increase_pct": increase,
        }


class OccupancyRepo:
    def __init__(self, db):
        self.db = db

    async def get_weekly_pattern(self, location_id: int) -> list[dict]:
        r = await self.db.execute(
            """
            SELECT CAST(strftime('%%w', submitted_at) AS INTEGER) as dow,
                   AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d,
                   COUNT(*) as cnt
            FROM media WHERE location_id=? AND analyzed=1
            GROUP BY dow ORDER BY dow
            """,
            (location_id,),
        )
        days = [
            "Sunday", "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday",
        ]
        patterns = []
        for row in await r.fetchall():
            hr = await self.db.execute(
                """
                SELECT CAST(strftime('%%H', submitted_at) AS INTEGER) as hour,
                       AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d
                FROM media WHERE location_id=? AND analyzed=1
                  AND CAST(strftime('%%w', submitted_at) AS INTEGER)=?
                GROUP BY hour ORDER BY avg_d DESC LIMIT 1
                """,
                (location_id, row["dow"]),
            )
            hr_row = await hr.fetchone()
            patterns.append(
                {
                    "day_of_week": row["dow"],
                    "day_name": days[row["dow"]],
                    "avg_density": round(row["avg_d"] or 0, 2),
                    "peak_hour": hr_row["hour"] if hr_row else 12,
                    "media_count": row["cnt"],
                }
            )
        return patterns

    async def get_monthly_trends(self, location_id: int, months: int = 12) -> list[dict]:
        r = await self.db.execute(
            """
            SELECT strftime('%%Y-%%m', submitted_at) as month,
                   AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d,
                   COUNT(*) as cnt
            FROM media WHERE location_id=? AND analyzed=1
            GROUP BY month ORDER BY month DESC LIMIT ?
            """,
            (location_id, months),
        )
        trends = []
        for row in await r.fetchall():
            peak_r = await self.db.execute(
                """
                SELECT strftime('%%Y-%%m-%%d', submitted_at) as day,
                       AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d
                FROM media WHERE location_id=? AND analyzed=1
                  AND strftime('%%Y-%%m', submitted_at)=?
                GROUP BY day ORDER BY avg_d DESC LIMIT 1
                """,
                (location_id, row["month"]),
            )
            peak_row = await peak_r.fetchone()
            trends.append(
                {
                    "month": row["month"],
                    "avg_density": round(row["avg_d"] or 0, 2),
                    "media_count": row["cnt"],
                    "peak_day": peak_row["day"] if peak_row else None,
                }
            )
        return list(reversed(trends))


class LocationGroupRepo:
    def __init__(self, db):
        self.db = db

    async def create(self, data: dict) -> dict | None:
        r = await self.db.execute(
            "INSERT INTO location_groups (name, description, group_type) VALUES (?,?,?)",
            (data["name"], data.get("description"), data.get("group_type", "district")),
        )
        await self.db.commit()
        return await self.get_by_id(r.lastrowid)

    async def get_by_id(self, group_id: int) -> dict | None:
        r = await self.db.execute("SELECT * FROM location_groups WHERE id=?", (group_id,))
        row = await r.fetchone()
        if not row:
            return None
        cnt = await self.db.execute(
            "SELECT COUNT(*) FROM location_group_members WHERE group_id=?", (group_id,)
        )
        count = (await cnt.fetchone())[0]
        d = dict(row)
        d["member_count"] = count
        return d

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[dict]:
        r = await self.db.execute(
            "SELECT * FROM location_groups ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        results = []
        for row in await r.fetchall():
            cnt = await self.db.execute(
                "SELECT COUNT(*) FROM location_group_members WHERE group_id=?",
                (row["id"],),
            )
            d = dict(row)
            d["member_count"] = (await cnt.fetchone())[0]
            results.append(d)
        return results

    async def update(self, group_id: int, data: dict) -> dict | None:
        g = await self.get_by_id(group_id)
        if not g:
            return None
        sets: list[str] = []
        vals: list = []
        if data.get("name"):
            sets.append("name=?")
            vals.append(data["name"])
        if "description" in data:
            sets.append("description=?")
            vals.append(data["description"])
        if not sets:
            return g
        vals.append(group_id)
        await self.db.execute(
            f"UPDATE location_groups SET {','.join(sets)} WHERE id=?", vals
        )
        await self.db.commit()
        return await self.get_by_id(group_id)

    async def delete(self, group_id: int) -> bool:
        r = await self.db.execute("DELETE FROM location_groups WHERE id=?", (group_id,))
        await self.db.commit()
        return r.rowcount > 0

    async def add_member(self, group_id: int, location_id: int) -> bool:
        try:
            await self.db.execute(
                "INSERT INTO location_group_members (group_id, location_id) VALUES (?,?)",
                (group_id, location_id),
            )
            await self.db.commit()
            return True
        except Exception:
            return False

    async def remove_member(self, group_id: int, location_id: int) -> bool:
        r = await self.db.execute(
            "DELETE FROM location_group_members WHERE group_id=? AND location_id=?",
            (group_id, location_id),
        )
        await self.db.commit()
        return r.rowcount > 0

    async def get_members(self, group_id: int) -> list[dict]:
        r = await self.db.execute(
            """
            SELECT l.*, lgm.added_at FROM locations l
            JOIN location_group_members lgm ON l.id = lgm.location_id
            WHERE lgm.group_id=? ORDER BY l.name
            """,
            (group_id,),
        )
        return [dict(row) for row in await r.fetchall()]

    async def get_group_analytics(self, group_id: int) -> dict | None:
        members = await self.get_members(group_id)
        if not members:
            return None
        location_ids = [m["id"] for m in members]
        placeholders = ",".join("?" * len(location_ids))
        r = await self.db.execute(
            f"""
            SELECT COUNT(*) as total_media,
                   AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d
            FROM media WHERE location_id IN ({placeholders}) AND analyzed=1
            """,
            location_ids,
        )
        agg = await r.fetchone()
        busiest = None
        max_density = 0.0
        locs = []
        for m in members:
            lr = await self.db.execute(
                """
                SELECT COUNT(*) as cnt,
                       AVG(json_extract(analysis_json, '$.crowd_density')) as avg_d
                FROM media WHERE location_id=? AND analyzed=1
                """,
                (m["id"],),
            )
            loc_agg = await lr.fetchone()
            avg_d = round(loc_agg["avg_d"] or 0, 2)
            if avg_d > max_density:
                max_density = avg_d
                busiest = m["name"]
            locs.append(
                {
                    "id": m["id"],
                    "name": m["name"],
                    "category": m["category"],
                    "avg_density": avg_d,
                    "media_count": loc_agg["cnt"],
                }
            )
        return {
            "total_locations": len(members),
            "total_media": agg["total_media"] or 0,
            "avg_density": round(agg["avg_d"] or 0, 2),
            "busiest_location": busiest,
            "locations": locs,
        }
