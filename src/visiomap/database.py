from __future__ import annotations

import aiosqlite

from visiomap.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    lat         REAL    NOT NULL CHECK (lat BETWEEN -90 AND 90),
    lng         REAL    NOT NULL CHECK (lng BETWEEN -180 AND 180),
    radius_m    INTEGER NOT NULL DEFAULT 500 CHECK (radius_m BETWEEN 50 AND 50000),
    category    TEXT    NOT NULL DEFAULT 'other',
    description TEXT,
    tags        TEXT    NOT NULL DEFAULT '[]',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS media (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    source_url    TEXT    NOT NULL,
    source_type   TEXT    NOT NULL DEFAULT 'photo' CHECK (source_type IN ('photo','video','screenshot')),
    captured_at   TEXT,
    tags          TEXT    NOT NULL DEFAULT '[]',
    analyzed      INTEGER NOT NULL DEFAULT 0,
    analysis_json TEXT,
    submitted_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_media_location ON media(location_id);
CREATE INDEX IF NOT EXISTS idx_media_analyzed  ON media(analyzed);

CREATE TABLE IF NOT EXISTS density_alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    threshold     REAL    NOT NULL CHECK (threshold BETWEEN 0 AND 100),
    webhook_url   TEXT    NOT NULL,
    label         TEXT,
    fired_count   INTEGER NOT NULL DEFAULT 0,
    last_fired_at TEXT,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_alerts_location ON density_alerts(location_id);

CREATE TABLE IF NOT EXISTS geofences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    polygon     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS media_annotations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id    INTEGER NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    text        TEXT    NOT NULL,
    author      TEXT    NOT NULL DEFAULT 'reviewer',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_annotations_media ON media_annotations(media_id);

-- v1.7.0: Visitor Flows
CREATE TABLE IF NOT EXISTS visitor_flows (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    from_location_id  INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    to_location_id    INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    visitor_count     INTEGER NOT NULL CHECK (visitor_count >= 1),
    recorded_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_flows_from ON visitor_flows(from_location_id);
CREATE INDEX IF NOT EXISTS idx_flows_to   ON visitor_flows(to_location_id);
CREATE INDEX IF NOT EXISTS idx_flows_recorded ON visitor_flows(recorded_at);

-- v1.7.0: Zone Templates
CREATE TABLE IF NOT EXISTS zone_templates (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL,
    default_category  TEXT    NOT NULL DEFAULT 'other',
    default_tags      TEXT    NOT NULL DEFAULT '[]',
    analysis_config   TEXT    NOT NULL DEFAULT '{}',
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS zone_template_locations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id   INTEGER NOT NULL REFERENCES zone_templates(id) ON DELETE CASCADE,
    location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    applied_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(template_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_ztl_template ON zone_template_locations(template_id);
CREATE INDEX IF NOT EXISTS idx_ztl_location ON zone_template_locations(location_id);

-- v1.8.0: Events
CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id     INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    description     TEXT,
    event_type      TEXT    NOT NULL DEFAULT 'general',
    expected_crowd  INTEGER NOT NULL DEFAULT 100,
    actual_crowd    INTEGER,
    status          TEXT    NOT NULL DEFAULT 'scheduled',
    start_time      TEXT    NOT NULL,
    end_time        TEXT    NOT NULL,
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_location ON events(location_id);
CREATE INDEX IF NOT EXISTS idx_events_status   ON events(status);

-- v1.8.0: Location Groups
CREATE TABLE IF NOT EXISTS location_groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    group_type  TEXT    NOT NULL DEFAULT 'district',
    created_at  TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS location_group_members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    INTEGER NOT NULL REFERENCES location_groups(id) ON DELETE CASCADE,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    added_at    TEXT    DEFAULT (datetime('now')),
    UNIQUE(group_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_lgm_group    ON location_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_lgm_location ON location_group_members(location_id);
"""


async def init_db() -> None:
    async with aiosqlite.connect(settings.database_url) as db:
        await db.executescript(_SCHEMA)
        # v1.5.0: ensure tags column on locations
        cursor = await db.execute("PRAGMA table_info(locations)")
        cols = [r[1] for r in await cursor.fetchall()]
        if "tags" not in cols:
            await db.execute("ALTER TABLE locations ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")
        # v1.7.0: ensure max_capacity column on locations
        if "max_capacity" not in cols:
            await db.execute("ALTER TABLE locations ADD COLUMN max_capacity INTEGER")
        await db.commit()


async def get_db():
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
