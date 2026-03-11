from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

from visiomap.database import init_db
from visiomap.api import locations_router, media_router, analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="visiomap",
    description=(
        "Location intelligence from visual media. "
        "Submit photos from open sources, run AI vision analysis, "
        "and get interactive crowd density heatmaps, age demographics, "
        "and mood analytics per location."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(locations_router)
app.include_router(media_router)
app.include_router(analytics_router)

# ── Static UI ─────────────────────────────────────────────────────────────────
_static_dir = pathlib.Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

    @app.get("/map", include_in_schema=False)
    async def map_ui():
        return FileResponse(str(_static_dir / "index.html"))


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": "1.0.0", "service": "visiomap"}
