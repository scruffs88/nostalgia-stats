import asyncpg
from typing import Any, Dict, List, Optional

from app.settings import settings

pool: Optional[asyncpg.pool.Pool] = None


async def init_db() -> None:
    """Create connection pool and ensure schema exists."""
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(str(settings.database_url))
    async with pool.acquire() as conn:
        # create table and index if they don't exist
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
              id SERIAL PRIMARY KEY,
              ts_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              listeners INTEGER,
              listener_peak INTEGER,
              title TEXT,
              bitrate INTEGER,
              samplerate INTEGER,
              channels INTEGER,
              listenurl TEXT,
              raw_json JSONB
            );
            CREATE INDEX IF NOT EXISTS idx_snapshots_ts_utc ON snapshots(ts_utc);
            """
        )


async def get_latest_snapshot() -> Optional[Dict[str, Any]]:
    async with pool.acquire() as conn:  # type: ignore
        row = await conn.fetchrow(
            "SELECT * FROM snapshots ORDER BY ts_utc DESC LIMIT 1"
        )
    return dict(row) if row else None


async def insert_snapshot(
    listeners: Optional[int],
    listener_peak: Optional[int],
    title: Optional[str],
    bitrate: Optional[int],
    samplerate: Optional[int],
    channels: Optional[int],
    listenurl: Optional[str],
    raw_json: Any,
) -> None:
    async with pool.acquire() as conn:  # type: ignore
        await conn.execute(
            """
            INSERT INTO snapshots(
                listeners, listener_peak, title, bitrate, samplerate, channels,
                listenurl, raw_json
            ) VALUES($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            listeners,
            listener_peak,
            title,
            bitrate,
            samplerate,
            channels,
            listenurl,
            raw_json,
        )


async def get_hourly_stats(days: int, tz: str) -> List[Dict[str, Any]]:
    async with pool.acquire() as conn:  # type: ignore
        records = await conn.fetch(
            """
            SELECT
              hour,
              ROUND(AVG(listeners)) AS avg_listeners,
              MAX(listeners) AS max_listeners,
              COUNT(*) AS samples
            FROM (
              SELECT
                EXTRACT(HOUR FROM (ts_utc AT TIME ZONE 'UTC' AT TIME ZONE $1))::int AS hour,
                listeners
              FROM snapshots
              WHERE ts_utc >= (now() AT TIME ZONE 'UTC') - ($2 * interval '1 day')
                AND listeners IS NOT NULL
            ) sub
            GROUP BY hour
            ORDER BY hour
            """,
            tz,
            days,
        )
    return [dict(r) for r in records]


async def get_hourly_stats_range(start_utc, end_utc, tz: str) -> List[Dict[str, Any]]:
    async with pool.acquire() as conn:  # type: ignore
        records = await conn.fetch(
            """
            SELECT
              hour,
              ROUND(AVG(listeners)) AS avg_listeners,
              MAX(listeners) AS max_listeners,
              COUNT(*) AS samples
            FROM (
              SELECT
                EXTRACT(HOUR FROM (ts_utc AT TIME ZONE 'UTC' AT TIME ZONE $1))::int AS hour,
                listeners
              FROM snapshots
              WHERE ts_utc >= $2
                AND ts_utc < $3
                AND listeners IS NOT NULL
            ) sub
            GROUP BY hour
            ORDER BY hour
            """,
            tz,
            start_utc,
            end_utc,
        )
    return [dict(r) for r in records]


async def get_today_stats(tz: str) -> Dict[str, Optional[float]]:
    async with pool.acquire() as conn:  # type: ignore
        record = await conn.fetchrow(
            """
            SELECT
              avg(listeners) AS avg_listeners,
              max(listeners) AS max_listeners
            FROM snapshots
            WHERE (ts_utc AT TIME ZONE 'UTC' AT TIME ZONE $1)::date =
                  (now() AT TIME ZONE 'UTC' AT TIME ZONE $1)::date
            """,
            tz,
        )
    return dict(record) if record else {}
