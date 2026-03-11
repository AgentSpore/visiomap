import math
from typing import Optional

import aiosqlite
from fastapi import HTTPException

from visiomap.repositories import location_repo, media_repo
from visiomap.schemas.analytics import (
    HeatPoint, HeatmapResponse, LocationAnalytics, OverviewResponse,
    DailyTrendEntry, LocationSummary,
)


def _offset_coords(lat: float, lng: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    """Offset lat/lng by dx (east) and dy (north) in metres."""
    new_lat = lat + (dy_m / 111_320)
    new_lng = lng + (dx_m / (111_320 * math.cos(math.radians(lat))))
    return round(new_lat, 6), round(new_lng, 6)


def _build_heatmap(
    location: dict, raw_items: list[dict]
) -> HeatmapResponse:
    """
    Spread analyzed media into a spatial grid around the location center.
    Uses a deterministic scatter so the same media always lands at the same point.
    """
    import hashlib, random

    center_lat = location["lat"]
    center_lng = location["lng"]
    radius_m = location["radius_m"]

    if not raw_items:
        return HeatmapResponse(
            location_id=location["id"],
            location_name=location["name"],
            center_lat=center_lat,
            center_lng=center_lng,
            radius_m=radius_m,
            points=[],
            total_samples=0,
            max_density=0,
        )

    max_density = max(r["crowd_density"] or 0 for r in raw_items)
    points: list[HeatPoint] = []

    for item in raw_items:
        # Deterministic scatter based on URL
        h = int(hashlib.md5(item["source_url"].encode()).hexdigest(), 16)
        rng = random.Random(h)
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(0, radius_m * 0.9)
        dx = dist * math.cos(angle)
        dy = dist * math.sin(angle)
        lat, lng = _offset_coords(center_lat, center_lng, dx, dy)
        density = item["crowd_density"] or 0
        intensity = round(density / 10.0, 3)

        points.append(HeatPoint(
            lat=lat,
            lng=lng,
            intensity=intensity,
            crowd_density=density,
            sample_count=1,
        ))

    return HeatmapResponse(
        location_id=location["id"],
        location_name=location["name"],
        center_lat=center_lat,
        center_lng=center_lng,
        radius_m=radius_m,
        points=points,
        total_samples=len(points),
        max_density=round(max_density, 1),
    )


async def get_heatmap(db: aiosqlite.Connection, location_id: int) -> HeatmapResponse:
    loc = await location_repo.get_by_id(db, location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    raw = await media_repo.heatmap_data(db, location_id)
    return _build_heatmap(loc, raw)


async def get_location_analytics(
    db: aiosqlite.Connection, location_id: int
) -> LocationAnalytics:
    loc = await location_repo.get_by_id(db, location_id)
    if not loc:
        raise HTTPException(404, "Location not found")
    data = await media_repo.location_analytics_data(db, location_id)

    return LocationAnalytics(
        location_id=location_id,
        location_name=loc["name"],
        total_media=data["total"] or 0,
        analyzed_media=int(data["analyzed"] or 0),
        avg_crowd_density=round(data["avg_density"], 2) if data["avg_density"] else None,
        peak_crowd_density=round(data["peak_density"], 1) if data["peak_density"] else None,
        dominant_mood=data["dominant_mood"],
        top_environment_tags=data["top_tags"],
        age_distribution=data["age_distribution"],
        mood_distribution=data["mood_distribution"],
        weather_breakdown=data["weather_breakdown"],
        daily_trend=[
            DailyTrendEntry(**entry) for entry in data["daily_trend"]
        ],
    )


async def get_overview(db: aiosqlite.Connection) -> OverviewResponse:
    data = await media_repo.overview_data(db)
    locs_raw = await location_repo.list_all(db)

    locations = [
        LocationSummary(
            id=r["id"],
            name=r["name"],
            lat=r["lat"],
            lng=r["lng"],
            media_count=r["media_count"] or 0,
            avg_crowd_density=round(r["avg_crowd_density"], 2) if r["avg_crowd_density"] else None,
            dominant_mood=None,
        )
        for r in locs_raw
    ]

    # Enrich with dominant mood from overview data
    loc_map = {l["id"]: l for l in data["locations"]}
    for loc in locations:
        if loc.id in loc_map:
            loc.dominant_mood = loc_map[loc.id].get("dominant_mood")

    busiest = None
    if data["locations"]:
        b = max(data["locations"], key=lambda x: x.get("avg_density") or 0)
        busiest = b["name"] if b.get("avg_density") else None

    return OverviewResponse(
        total_locations=len(locs_raw),
        total_media=data["total_media"],
        analyzed_media=data["analyzed_media"],
        busiest_location=busiest,
        avg_crowd_density=round(data["avg_density"], 2) if data["avg_density"] else None,
        locations=locations,
    )
