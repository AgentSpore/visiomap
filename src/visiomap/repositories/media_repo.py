import json
from datetime import datetime
from collections import Counter
from typing import Optional

import aiosqlite

from visiomap.schemas.media import AnalysisResult


def _parse_row(row: aiosqlite.Row) -> dict:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    d["analyzed"] = bool(d.get("analyzed"))
    if d["analyzed"]:
        d["analysis"] = AnalysisResult(
            crowd_density=d["crowd_density"],
            crowd_count_estimate=d["crowd_count"] or 0,
            age_groups=json.loads(d["age_groups"] or "{}"),
            mood=json.loads(d["mood"] or "{}"),
            dominant_mood=d["dominant_mood"] or "",
            environment_tags=json.loads(d["env_tags"] or "[]"),
            weather=d["weather"] or "",
            time_of_day=d["time_of_day"] or "",
            confidence=d["confidence"] or 0,
            analysis_source=d["analysis_source"] or "unknown",
        )
    else:
        d["analysis"] = None
    return d


async def create(db: aiosqlite.Connection, data: dict) -> dict:
    now = datetime.utcnow().isoformat()
    cur = await db.execute(
        """INSERT INTO media
           (location_id, source_url, source_type, captured_at, tags, submitted_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data["location_id"], data["source_url"], data.get("source_type", "photo"),
         data.get("captured_at"), json.dumps(data.get("tags", [])), now),
    )
    await db.commit()
    return await get_by_id(db, cur.lastrowid)


async def get_by_id(db: aiosqlite.Connection, media_id: int) -> Optional[dict]:
    row = await (await db.execute(
        "SELECT * FROM media WHERE id=?", (media_id,)
    )).fetchone()
    return _parse_row(row) if row else None


async def list_by_location(
    db: aiosqlite.Connection,
    location_id: int,
    analyzed: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    if analyzed is None:
        rows = await (await db.execute(
            "SELECT * FROM media WHERE location_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (location_id, limit, offset),
        )).fetchall()
    else:
        rows = await (await db.execute(
            "SELECT * FROM media WHERE location_id=? AND analyzed=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (location_id, int(analyzed), limit, offset),
        )).fetchall()
    return [_parse_row(r) for r in rows]


async def list_all(
    db: aiosqlite.Connection,
    analyzed: Optional[bool] = None,
    limit: int = 100,
) -> list[dict]:
    if analyzed is None:
        rows = await (await db.execute(
            "SELECT * FROM media ORDER BY id DESC LIMIT ?", (limit,)
        )).fetchall()
    else:
        rows = await (await db.execute(
            "SELECT * FROM media WHERE analyzed=? ORDER BY id DESC LIMIT ?",
            (int(analyzed), limit),
        )).fetchall()
    return [_parse_row(r) for r in rows]


async def save_analysis(db: aiosqlite.Connection, media_id: int, result: AnalysisResult) -> dict:
    await db.execute(
        """UPDATE media SET
           analyzed=1, crowd_density=?, crowd_count=?, age_groups=?, mood=?,
           dominant_mood=?, env_tags=?, weather=?, time_of_day=?,
           confidence=?, analysis_source=?
           WHERE id=?""",
        (
            result.crowd_density, result.crowd_count_estimate,
            json.dumps(result.age_groups), json.dumps(result.mood),
            result.dominant_mood, json.dumps(result.environment_tags),
            result.weather, result.time_of_day,
            result.confidence, result.analysis_source,
            media_id,
        ),
    )
    await db.commit()
    return await get_by_id(db, media_id)


async def get_unanalyzed(db: aiosqlite.Connection, location_id: Optional[int] = None) -> list[dict]:
    if location_id:
        rows = await (await db.execute(
            "SELECT * FROM media WHERE analyzed=0 AND location_id=?", (location_id,)
        )).fetchall()
    else:
        rows = await (await db.execute(
            "SELECT * FROM media WHERE analyzed=0"
        )).fetchall()
    return [_parse_row(r) for r in rows]


# ── Analytics queries ─────────────────────────────────────────────────────────

async def heatmap_data(db: aiosqlite.Connection, location_id: int) -> list[dict]:
    """Aggregate analyzed media into heatmap points (group by URL hash bucket)."""
    rows = await (await db.execute(
        """SELECT source_url, crowd_density, confidence
           FROM media
           WHERE location_id=? AND analyzed=1
           ORDER BY id DESC""",
        (location_id,),
    )).fetchall()
    return [dict(r) for r in rows]


async def location_analytics_data(db: aiosqlite.Connection, location_id: int) -> dict:
    row = await (await db.execute(
        """SELECT
             COUNT(*)                AS total,
             SUM(analyzed)          AS analyzed,
             AVG(crowd_density)     AS avg_density,
             MAX(crowd_density)     AS peak_density
           FROM media WHERE location_id=?""",
        (location_id,),
    )).fetchone()
    base = dict(row)

    env_rows = await (await db.execute(
        "SELECT env_tags FROM media WHERE location_id=? AND analyzed=1",
        (location_id,),
    )).fetchall()
    all_tags: list[str] = []
    for r in env_rows:
        all_tags.extend(json.loads(r["env_tags"] or "[]"))
    top_tags = [t for t, _ in Counter(all_tags).most_common(6)]

    mood_rows = await (await db.execute(
        "SELECT dominant_mood FROM media WHERE location_id=? AND analyzed=1 AND dominant_mood IS NOT NULL",
        (location_id,),
    )).fetchall()
    mood_counter = Counter(r["dominant_mood"] for r in mood_rows)
    dominant_mood = mood_counter.most_common(1)[0][0] if mood_counter else None

    age_rows = await (await db.execute(
        "SELECT age_groups FROM media WHERE location_id=? AND analyzed=1",
        (location_id,),
    )).fetchall()
    age_agg: dict[str, list[float]] = {}
    for r in age_rows:
        for k, v in json.loads(r["age_groups"] or "{}").items():
            age_agg.setdefault(k, []).append(v)
    age_distribution = {k: round(sum(v) / len(v), 1) for k, v in age_agg.items()} if age_agg else None

    mood_full_rows = await (await db.execute(
        "SELECT mood FROM media WHERE location_id=? AND analyzed=1",
        (location_id,),
    )).fetchall()
    mood_agg: dict[str, list[float]] = {}
    for r in mood_full_rows:
        for k, v in json.loads(r["mood"] or "{}").items():
            mood_agg.setdefault(k, []).append(v)
    mood_distribution = {k: round(sum(v) / len(v), 1) for k, v in mood_agg.items()} if mood_agg else None

    weather_rows = await (await db.execute(
        "SELECT weather, COUNT(*) AS cnt FROM media WHERE location_id=? AND analyzed=1 AND weather IS NOT NULL GROUP BY weather",
        (location_id,),
    )).fetchall()
    weather_breakdown = {r["weather"]: r["cnt"] for r in weather_rows} if weather_rows else None

    trend_rows = await (await db.execute(
        """SELECT date(submitted_at) AS day,
                  COUNT(*)          AS sample_count,
                  AVG(crowd_density) AS avg_density,
                  (SELECT dominant_mood FROM media m2
                   WHERE m2.location_id=? AND date(m2.submitted_at)=date(m.submitted_at) AND m2.analyzed=1
                   GROUP BY dominant_mood ORDER BY COUNT(*) DESC LIMIT 1) AS top_mood
           FROM media m
           WHERE location_id=? AND analyzed=1
           GROUP BY date(submitted_at)
           ORDER BY day DESC
           LIMIT 30""",
        (location_id, location_id),
    )).fetchall()
    daily_trend = [
        {
            "day": r["day"],
            "sample_count": r["sample_count"],
            "avg_crowd_density": round(r["avg_density"] or 0, 1),
            "dominant_mood": r["top_mood"],
        }
        for r in trend_rows
    ]

    return {
        **base,
        "top_tags": top_tags,
        "dominant_mood": dominant_mood,
        "age_distribution": age_distribution,
        "mood_distribution": mood_distribution,
        "weather_breakdown": weather_breakdown,
        "daily_trend": daily_trend,
    }


async def overview_data(db: aiosqlite.Connection) -> dict:
    row = await (await db.execute(
        """SELECT COUNT(*) AS total_media, SUM(analyzed) AS analyzed,
                  AVG(crowd_density) AS avg_density FROM media"""
    )).fetchone()
    locs = await (await db.execute(
        """SELECT l.id, l.name, l.lat, l.lng,
                  COUNT(m.id) AS media_count,
                  AVG(m.crowd_density) AS avg_density,
                  (SELECT dominant_mood FROM media m2
                   WHERE m2.location_id=l.id AND m2.analyzed=1
                   GROUP BY dominant_mood ORDER BY COUNT(*) DESC LIMIT 1) AS dominant_mood
           FROM locations l
           LEFT JOIN media m ON m.location_id=l.id
           GROUP BY l.id
           ORDER BY avg_density DESC"""
    )).fetchall()
    return {
        "total_media": row["total_media"] or 0,
        "analyzed_media": row["analyzed"] or 0,
        "avg_density": row["avg_density"],
        "locations": [dict(r) for r in locs],
    }
