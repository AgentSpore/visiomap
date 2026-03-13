from __future__ import annotations

import csv
import io
import math
from collections import Counter
from typing import Any

from visiomap.repositories.location_repo import LocationRepo
from visiomap.repositories.media_repo import MediaRepo


class AnalyticsService:
    def __init__(self, location_repo: LocationRepo, media_repo: MediaRepo) -> None:
        self.location_repo = location_repo
        self.media_repo = media_repo

    async def get_overview(self) -> dict[str, Any]:
        total_media = await self.media_repo.count_all()
        analyzed_media = await self.media_repo.count_analyzed()
        avg_density = await self.media_repo.get_avg_density()
        busiest = await self.location_repo.get_busiest()
        summary = await self.location_repo.get_summary()
        locations = await self.location_repo.list_all()
        return {
            "total_locations": len(locations),
            "total_media": total_media,
            "analyzed_media": analyzed_media,
            "busiest_location": busiest,
            "avg_crowd_density": avg_density,
            "locations_summary": summary,
        }

    async def get_location_analytics(self, location_id: int) -> dict[str, Any] | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        stats = await self.media_repo.get_location_analytics(location_id)
        analyses = await self.media_repo.get_analyzed_media(location_id)
        daily = await self.media_repo.get_daily_trend(location_id)
        age_agg: dict[str, float] = {}
        mood_agg: dict[str, float] = {}
        tag_counter: Counter[str] = Counter()
        mood_counter: Counter[str] = Counter()
        for a in analyses:
            for k, v in a.get("age_groups", {}).items():
                age_agg[k] = age_agg.get(k, 0) + v
            for k, v in a.get("mood", {}).items():
                mood_agg[k] = mood_agg.get(k, 0) + v
            tag_counter.update(a.get("environment_tags", []))
            mood_counter[a.get("dominant_mood", "neutral")] += 1
        n = len(analyses) or 1
        age_dist = {k: round(v / n, 1) for k, v in age_agg.items()} if age_agg else None
        mood_dist = {k: round(v / n, 1) for k, v in mood_agg.items()} if mood_agg else None
        dominant_mood = mood_counter.most_common(1)[0][0] if mood_counter else None
        return {
            "location_id": location["id"],
            "location_name": location["name"],
            "total_media": stats["total_media"],
            "analyzed_media": stats["analyzed_media"],
            "avg_crowd_density": stats["avg_crowd_density"],
            "peak_crowd_density": stats["peak_crowd_density"],
            "dominant_mood": dominant_mood,
            "top_environment_tags": [t for t, _ in tag_counter.most_common(5)],
            "age_distribution": age_dist,
            "mood_distribution": mood_dist,
            "daily_trend": daily,
        }

    async def export_analytics_csv(self, location_id: int) -> str | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        daily = await self.media_repo.get_daily_trend(location_id)
        analyses = await self.media_repo.get_analyzed_media(location_id)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "date", "avg_density", "media_count",
            "dominant_mood", "top_tag",
        ])
        daily_map: dict[str, dict] = {}
        for a in analyses:
            day = a.get("analyzed_at", "")[:10] if a.get("analyzed_at") else "unknown"
            if day not in daily_map:
                daily_map[day] = {"moods": Counter(), "tags": Counter(), "count": 0}
            daily_map[day]["moods"][a.get("dominant_mood", "neutral")] += 1
            daily_map[day]["tags"].update(a.get("environment_tags", []))
            daily_map[day]["count"] += 1
        for d in daily:
            date = d["date"]
            dm = daily_map.get(date, {})
            moods = dm.get("moods", Counter())
            tags = dm.get("tags", Counter())
            dominant = moods.most_common(1)[0][0] if moods else ""
            top_tag = tags.most_common(1)[0][0] if tags else ""
            writer.writerow([date, d["avg_density"], d["media_count"], dominant, top_tag])
        return buf.getvalue()

    async def get_heatmap(self, location_id: int) -> dict[str, Any] | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        analyses = await self.media_repo.get_heatmap_data(location_id)
        if not analyses:
            return {
                "location_id": location["id"],
                "location_name": location["name"],
                "center_lat": location["lat"],
                "center_lng": location["lng"],
                "radius_m": location["radius_m"],
                "points": [],
                "total_samples": 0,
            }
        points = []
        max_density = max(a.get("crowd_density", 0) for a in analyses)
        max_density = max_density or 1
        for i, a in enumerate(analyses):
            density = a.get("crowd_density", 0)
            angle = (i * 137.508) % 360
            dist_frac = ((i * 7 + 3) % 10) / 10.0
            r_deg = (location["radius_m"] / 111_000) * dist_frac
            lat_off = r_deg * math.cos(math.radians(angle))
            lng_off = r_deg * math.sin(math.radians(angle)) / max(
                math.cos(math.radians(location["lat"])), 0.01
            )
            points.append({
                "lat": round(location["lat"] + lat_off, 6),
                "lng": round(location["lng"] + lng_off, 6),
                "intensity": round(density / max_density, 3),
                "crowd_density": density,
                "sample_count": 1,
            })
        return {
            "location_id": location["id"],
            "location_name": location["name"],
            "center_lat": location["lat"],
            "center_lng": location["lng"],
            "radius_m": location["radius_m"],
            "points": points,
            "total_samples": len(points),
        }
