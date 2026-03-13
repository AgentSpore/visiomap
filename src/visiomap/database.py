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
    description TEXT,
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
"""


async def init_db() -> None:
    async with aiosqlite.connect(settings.database_url) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def get_db():
    async with aiosqlite.connect(settings.database_url) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
