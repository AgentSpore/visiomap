# visiomap — Development Log

## v1.0.0 — Initial Release (2026-03-13)

### Created
- Full layered architecture: api/ → services/ → repositories/ → schemas/
- VisionAnalyzer with OpenAI gpt-4o backend + deterministic mock fallback
- 13 API endpoints: locations CRUD, media CRUD+batch, analyze single/all, heatmap, analytics, overview
- Leaflet.js dark-theme UI at /map: heatmap overlay, mood bars, age chart, daily trend, overview mode
- SQLite with WAL mode, json_extract for analysis queries
- Smoke test with 19 assertions
- DEEP.md architecture docs

### Technical Notes
- Mock analyzer: SHA-256 hash → deterministic crowd_density, age, mood — same URL = same result
- Heatmap scatter: golden angle (137.508°) for even point distribution
- DB: analysis stored as JSON blob, queried with `json_extract()` in SQLite
- UI: no build step, CDN-loaded Leaflet + leaflet.heat, responsive

### File count
- 19 Python files across 6 packages
- 1 HTML file (UI)
- pyproject.toml (uv), Makefile, DEEP.md, MEMORY.md, README.md
