#!/usr/bin/env python3
"""Smoke test: boots the app, creates data, runs analysis, checks heatmap."""

import asyncio
import sys

import httpx

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  OK  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} — {detail}")


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as c:
        # Health
        r = await c.get("/health")
        check("GET /health", r.status_code == 200 and r.json()["version"] == "1.0.0", str(r.text))

        # Create location
        r = await c.post("/locations", json={
            "name": "Times Square", "lat": 40.758, "lng": -73.985, "radius_m": 400
        })
        check("POST /locations", r.status_code == 201, str(r.text))
        loc_id = r.json()["id"]

        # List locations
        r = await c.get("/locations")
        check("GET /locations", r.status_code == 200 and len(r.json()) >= 1)

        # Get single location
        r = await c.get(f"/locations/{loc_id}")
        check("GET /locations/{id}", r.status_code == 200 and r.json()["name"] == "Times Square")

        # Submit media batch
        r = await c.post("/media/batch", json={"items": [
            {"location_id": loc_id, "source_url": "https://example.com/crowd1.jpg", "tags": ["outdoor"]},
            {"location_id": loc_id, "source_url": "https://example.com/crowd2.jpg", "tags": ["evening"]},
            {"location_id": loc_id, "source_url": "https://example.com/crowd3.jpg", "tags": ["market"]},
        ]})
        check("POST /media/batch", r.status_code == 201 and r.json()["created"] == 3, str(r.text))

        # Single media submit
        r = await c.post("/media", json={
            "location_id": loc_id, "source_url": "https://example.com/single.jpg"
        })
        check("POST /media", r.status_code == 201 and r.json()["analyzed"] is False)

        # List media
        r = await c.get("/media", params={"location_id": loc_id})
        check("GET /media", r.status_code == 200 and len(r.json()) == 4)

        # Analyze all
        r = await c.post("/media/analyze/all", params={"location_id": loc_id})
        check("POST /media/analyze/all", r.status_code == 200 and r.json()["analyzed"] == 4, str(r.text))
        check("  no failures", r.json()["failed"] == 0)

        # Heatmap
        r = await c.get(f"/locations/{loc_id}/heatmap")
        heat = r.json()
        check("GET /locations/{id}/heatmap", r.status_code == 200 and heat["total_samples"] == 4)
        check("  has points", len(heat["points"]) == 4)

        # Analytics
        r = await c.get(f"/locations/{loc_id}/analytics")
        a = r.json()
        check("GET /locations/{id}/analytics", r.status_code == 200)
        check("  has density", a["avg_crowd_density"] is not None and a["avg_crowd_density"] > 0)
        check("  has mood", a["dominant_mood"] is not None)
        check("  has age groups", a["age_distribution"] is not None)
        check("  has env tags", len(a["top_environment_tags"]) > 0)

        # Overview
        r = await c.get("/analytics/overview")
        check("GET /analytics/overview", r.status_code == 200 and r.json()["total_locations"] >= 1)

        # Map page
        r = await c.get("/map")
        check("GET /map", r.status_code == 200 and "visiomap" in r.text)

        # Cleanup
        r = await c.delete(f"/locations/{loc_id}")
        check("DELETE /locations/{id}", r.status_code == 204)

    print(f"\n{'='*40}")
    print(f"  {passed} passed, {failed} failed")
    print(f"{'='*40}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
