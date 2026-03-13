# visiomap — Development Log

## v1.1.0 (2026-03-13)
- **Location categories**: `category` field (mall/park/street/venue/transit/beach/other) with filter
- **GET /locations?category=** filter endpoint
- **GET /locations/{id}/analytics/export/csv** — daily trend CSV with mood and tag data
- **Density alerts**: POST/GET/DELETE /alerts, threshold-based with webhook_url
- AlertService.check_and_fire() — auto-trigger when crowd density exceeds threshold
- LocationSummary now includes category field
- Updated DEEP.md with alert architecture
- Bumped v1.1.0

## v1.0.0
- Initial release: layered architecture (api/services/repos/schemas/analyzer)
- Leaflet.js dark-theme heatmap UI with sidebar analytics
- VisionAnalyzer: OpenAI gpt-4o when API key set, SHA-256 deterministic mock otherwise
- 13 endpoints: locations CRUD, media CRUD + batch + analyze, heatmap, analytics, overview
- uv + pyproject.toml, Makefile, smoke tests
