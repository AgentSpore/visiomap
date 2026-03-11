# visiomap — Architecture Deep Dive

## Concept

visiomap turns photos and videos from open sources into actionable location intelligence.
Businesses submit media URLs tagged to a geographic location; AI vision analysis extracts
crowd density, age distribution, mood, and environment context. The aggregated data is served
as spatial heatmap points and analytics for consumption by BI tools or the built-in Leaflet UI.

## Directory Structure

```
src/visiomap/
├── main.py              # FastAPI app, lifespan, router mounting
├── config.py            # pydantic-settings (DB path, OpenAI key, etc.)
├── database.py          # aiosqlite connection, schema init
│
├── api/                 # Controllers — HTTP routing only
│   ├── locations.py     # CRUD /locations
│   ├── media.py         # Media submit, list, analyze
│   └── analytics.py     # Heatmap, per-location analytics, overview
│
├── services/            # Business logic & orchestration
│   ├── location_service.py   # Validates, maps to schema, raises HTTP errors
│   ├── media_service.py      # Submit, batch, trigger analysis, idempotency
│   └── analytics_service.py  # Spatial scatter, heatmap build, aggregation
│
├── repositories/        # Data access — SQL only, no business logic
│   ├── location_repo.py      # Location CRUD + aggregate stats JOIN
│   └── media_repo.py         # Media CRUD + analytics queries
│
├── schemas/             # Pydantic v2 models (request + response)
│   ├── location.py
│   ├── media.py
│   └── analytics.py
│
├── analyzer/            # Vision AI module (pluggable)
│   └── vision.py             # OpenAI Vision API or deterministic mock
│
└── static/
    └── index.html       # Leaflet.js dark-theme heatmap viewer
```

## Layer Responsibilities

| Layer | Knows about | Does NOT know about |
|-------|-------------|---------------------|
| **api/** | HTTP (FastAPI), schemas, services | DB, SQL, AI |
| **services/** | Business rules, schemas, repos, analyzer | HTTP, SQL internals |
| **repositories/** | SQL, aiosqlite, raw dicts | HTTP, Pydantic, AI |
| **schemas/** | Pydantic validation | All layers |
| **analyzer/** | Vision AI API, HTTP | DB, FastAPI |

## Data Model

```
locations
├── id (PK)
├── name (UNIQUE)
├── lat / lng (WGS-84)
├── radius_m (monitoring radius)
├── description
└── created_at

media
├── id (PK)
├── location_id (FK → locations)
├── source_url
├── source_type (photo | video)
├── captured_at (optional, from EXIF or metadata)
├── tags (JSON array)
├── analyzed (bool)
│
│   ── Analysis fields (populated after analyze) ──
├── crowd_density (0–10 float)
├── crowd_count (estimated integer)
├── age_groups (JSON: child/young_adult/adult/senior → %)
├── mood (JSON: positive/neutral/negative → %)
├── dominant_mood
├── env_tags (JSON array)
├── weather
├── time_of_day
├── confidence (0–1)
├── analysis_source (openai | mock | mock_fallback)
└── submitted_at
```

Indexes: `(location_id)` and `(analyzed, location_id)` for efficient analytics queries.

## Heatmap Algorithm

Each analyzed photo is assigned a spatial point within the location's monitoring radius:

1. Hash the `source_url` with MD5 → deterministic seed
2. Generate a random angle (0–2π) and distance (0–0.9×radius)
3. Convert to lat/lng offset using flat-earth approximation (valid for radii < 50km)
4. Intensity = `crowd_density / 10` (normalized 0–1 for Leaflet.heat)

Same URL always produces the same point — consistent across requests.

## Vision Analysis

```
if OPENAI_API_KEY set:
    → POST gpt-4o with image_url (detail: low, ~$0.001/image)
    → Parse JSON response
    → On failure: fallback to mock
else:
    → Deterministic mock (URL hash-based, consistent)
```

The `AnalysisResult` Pydantic model validates the API response before storage,
preventing corrupt data from reaching the DB.

## API Reference

```
POST   /locations                       Create location
GET    /locations                       List locations + aggregate stats
GET    /locations/{id}                  Location detail
PATCH  /locations/{id}                  Update name/radius/description
DELETE /locations/{id}                  Delete location

POST   /media                           Submit single media URL
POST   /media/batch                     Submit up to 50 URLs
GET    /media                           List (?location_id, ?analyzed, ?limit, ?offset)
GET    /media/{id}                      Media detail + analysis
POST   /media/{id}/analyze              Trigger analysis (idempotent)
POST   /media/analyze/all               Batch analyze all unanalyzed (?location_id)

GET    /locations/{id}/heatmap          Spatial heatmap points (Leaflet.heat compatible)
GET    /locations/{id}/analytics        Full analytics: mood, age, env, weather, daily trend
GET    /analytics/overview              Cross-location summary

GET    /map                             Interactive Leaflet heatmap UI
GET    /health                          Health check
```

## Performance Notes

- WAL mode + foreign keys enabled at startup
- Analytics queries use GROUP BY on indexed columns
- `overview_data` is O(locations × media) — cache or paginate for >10k media
- OpenAI Vision uses `detail: low` to minimize cost (~$0.001 per image vs ~$0.01 high)
- Batch analysis runs sequentially (not concurrent) to avoid API rate limits
