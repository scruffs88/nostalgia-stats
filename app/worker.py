import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx

from app import db
from app.settings import settings


async def fetch_and_store() -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.status_url, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()

    stats = data.get("icestats", {})
    source = stats.get("source", {})
    if isinstance(source, list):
        source = source[0] if source else {}

    listeners = _safe_int(source.get("listeners"))
    listener_peak = _safe_int(source.get("listener_peak"))
    title = source.get("title")
    listenurl = source.get("listenurl")
    audio_info = source.get("audio_info", "")

    bitrate: Optional[int] = None
    samplerate: Optional[int] = None
    channels: Optional[int] = None
    if audio_info:
        for part in audio_info.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                if "bitrate" in k:
                    bitrate = _safe_int(v)
                elif "samplerate" in k:
                    samplerate = _safe_int(v)
                elif "channels" in k:
                    channels = _safe_int(v)

    await db.insert_snapshot(
        listeners,
        listener_peak,
        title,
        bitrate,
        samplerate,
        channels,
        listenurl,
        json.dumps(data),
    )
    logging.info(
        "inserted listeners=%s title=%s",
        listeners,
        title,
    )


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


async def worker_loop() -> None:
    await db.init_db()
    while True:
        try:
            await fetch_and_store()
        except Exception:
            logging.exception("error polling status")
        await asyncio.sleep(settings.poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(worker_loop())
