from visiomap.api.locations import router as locations_router
from visiomap.api.media import router as media_router
from visiomap.api.analytics import router as analytics_router
from visiomap.api.geofences import router as geofences_router
from visiomap.api.v170_routes import router as v170_router
from visiomap.api.v180_routes import router as v180_router

__all__ = [
    "locations_router",
    "media_router",
    "analytics_router",
    "geofences_router",
    "v170_router",
    "v180_router",
]
