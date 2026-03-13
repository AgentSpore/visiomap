# visiomap — Architecture

## Overview

Location intelligence platform that analyzes photos from open sources and generates interactive crowd density heatmaps with demographic and mood analytics.

## Architecture

```
┌──────────────┐    ┌─────────────────┐    ┌────────────────┐
│  Leaflet UI  │◄──►│  FastAPI (main)  │◄──►│   SQLite (WAL) │
│  /map        │    │  /locations      │    │   locations     │
│  index.html  │    │  /media          │    │   media         │
└──────────────┘    │  /analytics      │    └────────────────┘
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ VisionAnalyzer  │
                    │ OpenAI gpt-4o   │
                    │ or mock (hash)  │
                    └─────────────────┘
```

## Layered Architecture

```
api/          → HTTP controllers (routers). No business logic.
                Parse request, call service, return response.

services/     → Business logic and orchestration.
                Validates, coordinates across repos, calls analyzer.

repositories/ → Data access. Raw SQL via aiosqlite.
                Each repo owns its table(s). Returns dicts.

schemas/      → Pydantic models for request/response validation.
                Shared between api and services layers.

analyzer/     → Vision AI module. Pluggable backend.
                OpenAI Vision when key is set, deterministic mock otherwise.
```

## Key Decisions

### 1. Deterministic mock analyzer
Mock generates results from SHA-256 of URL → same URL always produces same analysis.
This enables: reproducible tests, CI without API keys, predictable demos.

### 2. Spatial scatter via golden angle
Heatmap points use golden angle distribution (137.508°) for even scatter within location radius.
No randomness → same data produces same heatmap every time.

### 3. SQLite with WAL mode
WAL enables concurrent reads during writes. PRAGMA foreign_keys=ON enforces CASCADE deletes.
Analysis stored as JSON blob in `analysis_json` column — queried via `json_extract()`.

### 4. Single-file UI
No build step. Vanilla JS + Leaflet + leaflet.heat plugin from CDN.
Served as static file via FastAPI `StaticFiles` mount. Responsive layout for mobile.

## Data Flow

```
POST /media → MediaService.submit() → MediaRepo.create() → media row (analyzed=0)
POST /media/{id}/analyze → MediaService.analyze_one()
  → VisionAnalyzer.analyze(url)
    → OpenAI Vision API or mock
  → MediaRepo.save_analysis(id, json)
GET /locations/{id}/heatmap → AnalyticsService.get_heatmap()
  → MediaRepo.get_heatmap_data() → all analysis JSONs
  → Golden angle scatter → list[HeatPoint]
GET /locations/{id}/analytics → AnalyticsService.get_location_analytics()
  → Aggregate: avg density, peak, mood distribution, age groups, tags, daily trend
```

## Analysis Schema

```json
{
  "crowd_density": 6.5,
  "crowd_count_estimate": 38,
  "age_groups": {"child": 8, "young_adult": 35, "adult": 42, "senior": 15},
  "mood": {"positive": 62, "neutral": 28, "negative": 10},
  "dominant_mood": "positive",
  "environment_tags": ["outdoor", "busy", "commercial"],
  "weather": "sunny",
  "time_of_day": "afternoon",
  "confidence": 0.82,
  "analysis_source": "openai"
}
```

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `VISIOMAP_DATABASE_URL` | `visiomap.db` | SQLite path |
| `VISIOMAP_OPENAI_API_KEY` | `None` | Set for real AI analysis |
| `VISIOMAP_OPENAI_MODEL` | `gpt-4o` | Vision model |
| `VISIOMAP_HOST` | `0.0.0.0` | Server host |
| `VISIOMAP_PORT` | `8000` | Server port |
