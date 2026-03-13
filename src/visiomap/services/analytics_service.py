from __future__ import annotations

import csv
import io
import math
from collections import Counter
from typing import Any

from visiomap.repositories.location_repo import LocationRepo
from visiomap.repositories.media_repo import MediaRepo


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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

    async def get_location_analytics(
        self,
        location_id: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any] | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        stats = await self.media_repo.get_location_analytics(location_id, from_date, to_date)
        analyses = await self.media_repo.get_analyzed_media(location_id, from_date, to_date)
        daily = await self.media_repo.get_daily_trend(location_id, from_date, to_date)
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

    async def compare_locations(
        self,
        location_ids: list[int],
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        results = []
        for loc_id in location_ids:
            location = await self.location_repo.get_by_id(loc_id)
            if not location:
                continue
            stats = await self.media_repo.get_location_analytics(loc_id, from_date, to_date)
            analyses = await self.media_repo.get_analyzed_media(loc_id, from_date, to_date)
            tag_counter: Counter[str] = Counter()
            mood_counter: Counter[str] = Counter()
            for a in analyses:
                tag_counter.update(a.get("environment_tags", []))
                mood_counter[a.get("dominant_mood", "neutral")] += 1
            dominant_mood = mood_counter.most_common(1)[0][0] if mood_counter else None
            results.append({
                "location_id": location["id"],
                "location_name": location["name"],
                "category": location.get("category", "other"),
                "total_media": stats["total_media"],
                "analyzed_media": stats["analyzed_media"],
                "avg_crowd_density": stats["avg_crowd_density"],
                "peak_crowd_density": stats["peak_crowd_density"],
                "dominant_mood": dominant_mood,
                "top_tags": [t for t, _ in tag_counter.most_common(5)],
            })
        return results

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

    async def get_heatmap(
        self,
        location_id: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict[str, Any] | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        analyses = await self.media_repo.get_heatmap_data(location_id, from_date, to_date)
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

    # -- v1.3.0: Clustering -------------------------------------------------------

    async def cluster_locations(self, radius_km: float = 5.0) -> dict[str, Any]:
        locations = await self.location_repo.list_all()
        if not locations:
            return {"clusters": [], "total_clusters": 0, "unclustered_count": 0, "radius_km": radius_km}

        assigned = set()
        clusters = []
        cluster_id = 0

        for loc in locations:
            if loc["id"] in assigned:
                continue
            cluster_id += 1
            members = [loc]
            assigned.add(loc["id"])
            for other in locations:
                if other["id"] in assigned:
                    continue
                dist = _haversine_km(loc["lat"], loc["lng"], other["lat"], other["lng"])
                if dist <= radius_km:
                    members.append(other)
                    assigned.add(other["id"])

            if len(members) < 2:
                assigned.discard(loc["id"])
                continue

            center_lat = sum(m["lat"] for m in members) / len(members)
            center_lng = sum(m["lng"] for m in members) / len(members)
            densities = [m["avg_crowd_density"] for m in members if m.get("avg_crowd_density") is not None]
            avg_density = round(sum(densities) / len(densities), 2) if densities else None
            categories = sorted(set(m.get("category", "other") for m in members))

            clusters.append({
                "cluster_id": cluster_id,
                "center_lat": round(center_lat, 6),
                "center_lng": round(center_lng, 6),
                "member_count": len(members),
                "members": [
                    {
                        "location_id": m["id"],
                        "location_name": m["name"],
                        "lat": m["lat"],
                        "lng": m["lng"],
                        "category": m.get("category", "other"),
                        "avg_crowd_density": m.get("avg_crowd_density"),
                    }
                    for m in members
                ],
                "avg_crowd_density": avg_density,
                "categories": categories,
            })

        unclustered = len(locations) - len(assigned)
        return {
            "clusters": clusters,
            "total_clusters": len(clusters),
            "unclustered_count": unclustered,
            "radius_km": radius_km,
        }

    # -- v1.3.0: Score Trend -------------------------------------------------------

    async def get_score_trend(
        self,
        location_id: int,
        window: int = 7,
    ) -> dict[str, Any] | None:
        location = await self.location_repo.get_by_id(location_id)
        if not location:
            return None
        daily = await self.media_repo.get_daily_trend(location_id)
        daily_sorted = sorted(daily, key=lambda d: d["date"])

        points = []
        densities = [d["avg_density"] for d in daily_sorted]

        for i, d in enumerate(daily_sorted):
            start = max(0, i - window + 1)
            window_vals = densities[start:i + 1]
            moving_avg = round(sum(window_vals) / len(window_vals), 2) if window_vals else None

            if i == 0:
                direction = "stable"
            elif densities[i] > densities[i - 1] * 1.1:
                direction = "rising"
            elif densities[i] < densities[i - 1] * 0.9:
                direction = "falling"
            else:
                direction = "stable"

            points.append({
                "date": d["date"],
                "avg_density": d["avg_density"],
                "media_count": d["media_count"],
                "moving_avg": moving_avg,
                "direction": direction,
            })

        if len(densities) >= 3:
            first_half = densities[:len(densities) // 2]
            second_half = densities[len(densities) // 2:]
            avg_first = sum(first_half) / len(first_half) if first_half else 0
            avg_second = sum(second_half) / len(second_half) if second_half else 0
            if avg_first > 0:
                ratio = avg_second / avg_first
                if ratio > 1.15:
                    overall = "rising"
                elif ratio < 0.85:
                    overall = "falling"
                else:
                    overall = "stable"
            else:
                overall = "stable"
        else:
            overall = "stable"

        latest_density = densities[-1] if densities else None
        latest_ma = points[-1]["moving_avg"] if points else None

        return {
            "location_id": location["id"],
            "location_name": location["name"],
            "window_days": window,
            "points": points,
            "overall_trend": overall,
            "latest_density": latest_density,
            "latest_moving_avg": latest_ma,
        }
