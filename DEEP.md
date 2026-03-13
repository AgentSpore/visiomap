# visiomap — Architecture (DEEP.md)

## Overview
Location intelligence platform that processes visual media (photos, videos, screenshots) through AI vision analysis to produce crowd density heatmaps, demographic breakdowns, mood analytics, and density alerts.

## Layered Architecture
```
API layer (FastAPI routers)
  ├── locations.py — CRUD with category filtering
  ├── media.py — upload, analyze, list with pagination
  └── analytics.py — heatmap, analytics, comparison, alerts, CSV export
Service layer (business logic)
  ├── LocationService — thin CRUD wrapper
  ├── AnalyticsService — aggregation, heatmap generation, comparison
  ├── MediaService — upload + trigger analysis
  └── AlertService — density threshold alerts with webhook
Repository layer (data access)
  ├── LocationRepo — locations table + summary queries
  └── MediaRepo — media table + analytics queries with time filtering
Database layer
  └── SQLite with WAL mode + foreign keys
```

## Data Model
- **locations** — name, lat/lng, radius_m, category (mall/park/street/venue/transit/beach/other)
- **media** — linked to location, source_url, type (photo/video/screenshot), analysis_json (AI output)
- **density_alerts** — threshold, webhook_url, label, active toggle, fired_count, last_fired_at

## Key Features
| Feature | Endpoint | Description |
|---------|----------|-------------|
| Heatmap | GET /locations/{id}/heatmap | Synthetic density points with golden-angle distribution |
| Analytics | GET /locations/{id}/analytics | Density, mood, demographics, daily trend |
| Comparison | GET /analytics/compare?ids=1,2,3 | Side-by-side location stats |
| Time filter | ?from_date=&to_date= | Filter analytics/heatmap by date range |
| Alerts | POST/GET/PATCH/DELETE /alerts | Density threshold monitoring with webhooks |
| CSV export | GET /locations/{id}/analytics/export/csv | Daily trend + mood/tag breakdown |
| AI analysis | POST /locations/{id}/media/{id}/analyze | Mock vision analysis pipeline |

## Key Decisions
- **SQLite + WAL**: single-file, zero-config; sufficient for moderate traffic
- **Synthetic heatmap**: golden-angle spiral distribution; real GPS coordinates deferred until media GPS EXIF is available
- **Mock AI**: vision.py returns plausible synthetic data; plug in real model (GPT-4V, Gemini) via config
- **Time filtering**: from_date/to_date flow through service → repo, applied at SQL level for performance
- **Alert toggle**: PATCH /alerts/{id} with active: true/false; threshold + label also updatable
- **Comparison cap**: max 10 locations per compare request to prevent slow queries
