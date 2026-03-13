# VisioMap — Architecture (v1.3.0)

## Overview
Location intelligence from visual media. AI-powered crowd density analysis, demographics, mood analytics, geofencing, and clustering.

## Stack
- FastAPI + aiosqlite + Pydantic v2
- Layered architecture: api/ → services/ → repositories/ → database

## Database Tables
- **locations** — name, lat/lng, radius_m, category, description
- **media** — source_url, source_type, tags, analysis_json
- **density_alerts** — threshold-based webhook alerts
- **geofences** — polygon zones for containment checks (v1.3.0)

## Key Features
- Location CRUD with category filtering
- Media upload and AI analysis (crowd density, demographics, mood)
- Heatmap generation with spatial distribution
- Density alerts with webhook notifications
- Location comparison and CSV export
- Geofencing with ray-casting containment (v1.3.0)
- Location clustering with haversine distance (v1.3.0)
- Score trend analysis with moving average (v1.3.0)

## API Structure
### Locations: POST/GET/GET/{id}/PATCH/DELETE /locations
### Media: POST/GET/GET/{id}/DELETE /media, POST/{id}/analyze
### Analytics: GET /locations/{id}/heatmap, GET /locations/{id}/analytics, GET /analytics/overview, GET /analytics/compare, GET /analytics/clusters (v1.3.0)
### Trend: GET /locations/{id}/analytics/trend (v1.3.0)
### Geofences (v1.3.0): POST/GET/GET/{id}/DELETE /geofences, POST /geofences/{id}/check
### Alerts: POST/GET/GET/{id}/PATCH/DELETE /alerts
### Export: GET /locations/{id}/analytics/export/csv
### Health: GET /health
### Map: GET /map
