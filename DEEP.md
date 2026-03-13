# visiomap — Architecture

## Overview
Location intelligence from visual media. AI-powered crowd density heatmaps, demographics, mood analytics, density alerts, and CSV data export.

## Layered Architecture

```
api/            Controllers (FastAPI routers)
  locations.py  POST/GET/PATCH/DELETE /locations (?category= filter)
  media.py      POST/GET/DELETE /media, POST analyze
  analytics.py  GET heatmap, analytics, overview, CSV export, alerts CRUD

services/       Business logic
  location_service.py   Thin wrapper over repo
  media_service.py      Batch submit, analyze_one, analyze_all
  analytics_service.py  Heatmap generation, aggregation, CSV export
  alert_service.py      Density alerts CRUD, check_and_fire

repositories/   Data access (SQL)
  location_repo.py   CRUD + category filter + summary/busiest queries
  media_repo.py      CRUD + analysis storage + trend/heatmap queries

schemas/        Pydantic models
  location.py    LocationCreate/Update/Response, LocationCategory enum
  media.py       MediaCreate/BatchCreate/AnalysisResult/Response
  analytics.py   HeatPoint, HeatmapResponse, LocationAnalytics, AlertCreate/Response

analyzer/       AI analysis
  vision.py      VisionAnalyzer: OpenAI gpt-4o or SHA-256 deterministic mock
```

## Data Model

```
locations ──────────────────────────
  id, name, lat, lng, radius_m, category (mall/park/street/venue/transit/beach/other),
  description, created_at
  └── 1:N → media
  └── 1:N → density_alerts

media ──────────────────────────────
  id, location_id, source_url, source_type (photo/video/screenshot),
  captured_at, tags (JSON), analyzed, analysis_json, submitted_at
  INDEX: (location_id), (analyzed)

density_alerts ─────────────────────
  id, location_id, threshold (0-100), webhook_url, label,
  fired_count, last_fired_at, active, created_at
  INDEX: (location_id)
```

## Analysis Schema (analysis_json)

```json
{
  "crowd_density": 72.5,
  "dominant_mood": "relaxed",
  "age_groups": {"18-25": 30, "26-35": 40, "36-50": 20, "50+": 10},
  "mood": {"happy": 35, "neutral": 40, "relaxed": 20, "tense": 5},
  "environment_tags": ["outdoor", "sunny", "urban"],
  "estimated_count": 150
}
```

## Heatmap Generation

Golden angle scatter (137.508 degrees) distributes points evenly within location radius.
Each analyzed media item becomes one heat point at `(lat + offset, lng + offset)`.
Intensity normalized to `[0, 1]` by `density / max_density`.

## Density Alerts

```
POST /alerts {location_id, threshold, webhook_url, label}
  → INSERT into density_alerts

On media analysis (crowd_density computed):
  → AlertService.check_and_fire(location_id, density)
  → SELECT alerts WHERE threshold <= density AND active = 1
  → Increment fired_count, update last_fired_at
  → Return triggered alerts for webhook dispatch
```

## Key Decisions

### 1. Category as enum
7 values: mall, park, street, venue, transit, beach, other.
Stored as TEXT in SQLite for simplicity. Validated by Pydantic enum.
Migration: ALTER TABLE ADD COLUMN with DEFAULT for existing rows.

### 2. CSV export at service layer
AnalyticsService.export_analytics_csv() aggregates daily trends with mood/tag data.
Returns raw CSV string; controller wraps in StreamingResponse.

### 3. Alert check_and_fire pattern
Alerts are checked in-process after analysis. No background workers.
Webhook dispatch is responsibility of caller (media service).
Fired count provides audit trail without delivery logging.
