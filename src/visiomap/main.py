from __future__ import annotations

import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from visiomap.api import analytics_router, locations_router, media_router
from visiomap.api.geofences import router as geofences_router
from visiomap.database import init_db

STATIC_DIR = pathlib.Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="visiomap",
    description=(
        "Location intelligence from visual media. "
        "AI-powered crowd density heatmaps, demographics, mood analytics, "
        "density alerts, location comparison, time-window filtering, CSV data export, "
        "geofencing, location clustering, and score trend analysis."
    ),
    version="1.3.0",
    lifespan=lifespan,
)

app.include_router(locations_router)
app.include_router(media_router)
app.include_router(analytics_router)
app.include_router(geofences_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.3.0"}


@app.get("/map")
async def map_page():
    from fastapi.responses import FileResponse
    return FileResponse(STATIC_DIR / "map.html")
