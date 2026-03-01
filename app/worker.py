import asyncio
import json
import logging
from typing import Any, Optional

import httpx

from app import db
from app.settings import settings


logger = logging.getLogger(__name__)


async def fetch_and_store() -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.status_url, timeout=10.0)
        resp.raise_for_status()

        content_type = (resp.headers.get("content-type") or "").lower()
        if "json" not in content_type:
            logger.warning("unexpected content-type=%s; skipping sample", content_type)
            return

        text = resp.text
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Icecast sometimes returns truncated/invalid JSON. Skip this tick.
            logger.warning("invalid JSON from icecast (len=%s); skipping sample", len(text))
            return

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
                k = k.strip().lower()
                v = v.strip()
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
    logger.info("inserted listeners=%s title=%s", listeners, title)


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
            logger.exception("error polling status")
        await asyncio.sleep(settings.poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(worker_loop())