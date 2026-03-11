"""Smoke tests for visiomap — validates layered architecture without external deps."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ["DB_PATH"] = "visiomap_test.db"

from visiomap.config import settings
settings.db_path = "visiomap_test.db"

import aiosqlite
from visiomap.database import init_db
from visiomap.repositories import location_repo, media_repo
from visiomap.analyzer.vision import _mock as mock_analyze
from visiomap.schemas.media import MediaSubmit


async def run():
    await init_db()

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row

        # 1. Create location
        loc = await location_repo.create(db, {
            "name": "Red Square", "lat": 55.7539, "lng": 37.6208,
            "radius_m": 300, "description": "Moscow city center",
        })
        assert loc["id"] == 1
        assert loc["name"] == "Red Square"
        print("[PASS] create location")

        # 2. Duplicate name → unique constraint
        try:
            await location_repo.create(db, {"name": "Red Square", "lat": 0, "lng": 0, "radius_m": 100})
            assert False, "Should have raised"
        except Exception as e:
            assert "UNIQUE" in str(e)
        print("[PASS] unique location name constraint")

        # 3. Submit media
        m = await media_repo.create(db, {
            "location_id": 1,
            "source_url": "https://example.com/photo1.jpg",
            "source_type": "photo",
            "tags": ["test", "outdoor"],
        })
        assert m["id"] == 1
        assert not m["analyzed"]
        print("[PASS] submit media")

        # 4. Mock analyzer
        result = mock_analyze("https://example.com/photo1.jpg")
        assert 0 <= result.crowd_density <= 10
        assert result.analysis_source == "mock"
        assert sum(result.age_groups.values()) > 0
        assert sum(result.mood.values()) > 0
        print("[PASS] mock analyzer (deterministic)")

        # 5. Same URL = same result
        r2 = mock_analyze("https://example.com/photo1.jpg")
        assert r2.crowd_density == result.crowd_density
        print("[PASS] mock analyzer deterministic consistency")

        # 6. Save analysis
        updated = await media_repo.save_analysis(db, 1, result)
        assert updated["analyzed"]
        assert updated["analysis"] is not None
        assert updated["analysis"].crowd_density == result.crowd_density
        print("[PASS] save analysis to repo")

        # 7. Location stats update
        loc2 = await location_repo.get_by_id(db, 1)
        assert loc2["media_count"] == 1
        assert loc2["analyzed_count"] == 1
        assert loc2["avg_crowd_density"] is not None
        print("[PASS] location aggregate stats")

        # 8. Heatmap data
        raw = await media_repo.heatmap_data(db, 1)
        assert len(raw) == 1
        assert raw[0]["crowd_density"] == result.crowd_density
        print("[PASS] heatmap data query")

        # 9. Analytics data
        analytics = await media_repo.location_analytics_data(db, 1)
        assert analytics["total"] == 1
        assert analytics["analyzed"] == 1
        assert analytics["avg_density"] is not None
        print("[PASS] analytics data query")

        # 10. Overview
        overview = await media_repo.overview_data(db)
        assert overview["total_media"] == 1
        assert overview["analyzed_media"] == 1
        print("[PASS] overview data query")

        # 11. Delete location
        ok = await location_repo.delete(db, 1)
        assert ok
        assert await location_repo.get_by_id(db, 1) is None
        print("[PASS] delete location")

    print("\n=== All smoke tests passed ===")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    finally:
        if os.path.exists("visiomap_test.db"):
            os.remove("visiomap_test.db")
