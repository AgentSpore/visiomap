import aiosqlite
from visiomap.config import settings


async def get_db():
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db() -> None:
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                lat         REAL    NOT NULL,
                lng         REAL    NOT NULL,
                radius_m    INTEGER NOT NULL DEFAULT 500,
                description TEXT,
                created_at  TEXT    NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id     INTEGER NOT NULL,
                source_url      TEXT    NOT NULL,
                source_type     TEXT    NOT NULL DEFAULT 'photo',
                captured_at     TEXT,
                tags            TEXT    DEFAULT '[]',
                analyzed        INTEGER NOT NULL DEFAULT 0,
                crowd_density   REAL,
                crowd_count     INTEGER,
                age_groups      TEXT,
                mood            TEXT,
                dominant_mood   TEXT,
                env_tags        TEXT,
                weather         TEXT,
                time_of_day     TEXT,
                confidence      REAL,
                analysis_source TEXT,
                submitted_at    TEXT    NOT NULL,
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_media_location
            ON media(location_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_media_analyzed
            ON media(analyzed, location_id)
        """)

        await db.commit()
