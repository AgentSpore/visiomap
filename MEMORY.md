# visiomap — Development Log (MEMORY.md)

## v1.0.0
- Locations CRUD (name, lat/lng, radius)
- Media upload with source type (photo/video/screenshot)
- AI vision analysis (crowd density, demographics, mood, environment tags)
- Heatmap generation with golden-angle point distribution
- Location analytics (daily trend, age/mood distributions)
- Analytics overview with busiest location
- Static map page

## v1.1.0 (2026-03-13)
- Location categories (mall/park/street/venue/transit/beach/other)
- Category filtering on list endpoint
- Density alerts with webhook notifications
- Alert CRUD (create/list/get/delete)
- check_and_fire for auto-triggering when density exceeds threshold
- CSV export for per-location analytics
- DEEP.md + MEMORY.md added

## v1.2.0 (2026-03-13)
- **Location comparison**: GET /analytics/compare?ids=1,2,3 — side-by-side stats for 2-10 locations
- **Time-window filtering**: from_date/to_date on analytics, heatmap endpoints; SQL-level filtering
- **Alert updates**: PATCH /alerts/{id} — toggle active state, update threshold/label/webhook
- Media repo methods extended with from_date/to_date params
- Analytics service passes time filters through to repo layer
