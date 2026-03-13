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
"""


async def init_db() -> None:
    async with aiosqlite.connect(settings.database_url) as db:
        await db.executescript(_SCHEMA)
        # v1.5.0: ensure tags column on locations
        cursor = await db.execute("PRAGMA table_info(locations)")
        cols = [r[1] for r in await cursor.fetchall()]
        if "tags" not in cols:
            await db.execute("ALTER TABLE locations ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")
        await db.commit()


async def get_db():
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
