"""Redis pub/sub event publishing for Kamino directive events.

Channel: apex:directives

Sync path  — publish_directive_event() uses redis-py (blocking).
Async path — directive_event_subscriber() is an async generator using
             redis.asyncio.

Both paths degrade gracefully when Redis is unavailable: publish returns
False and logs a warning; the subscriber generator yields nothing.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from uuid import UUID

from pydantic import BaseModel

from src.config.settings import REDIS_URL

logger = logging.getLogger(__name__)

DIRECTIVE_EVENT_CHANNEL = "apex:directives"

# ---------------------------------------------------------------------------
# Optional Redis imports — module-level so tests can patch them
# ---------------------------------------------------------------------------

try:
    import redis as _redis_sync
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    _redis_sync = None  # type: ignore[assignment]
    aioredis = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class DirectiveEvent(BaseModel):
    directive_id: UUID
    event_type: str  # "created" | "cancelled" | "status_changed"
    status: str
    occurred_at: datetime
    title: Optional[str] = None
    owner: Optional[str] = None

    model_config = {}


# ---------------------------------------------------------------------------
# Sync publish
# ---------------------------------------------------------------------------


def _get_sync_redis():
    """Return a connected sync Redis client, or None on failure."""
    if _redis_sync is None:  # pragma: no cover
        return None
    try:
        client = _redis_sync.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        client.ping()
        return client
    except Exception as exc:
        logger.warning(
            "Redis unavailable — directive events will not be published: %s", exc
        )
        return None


def publish_directive_event(event: DirectiveEvent) -> bool:
    """Publish *event* to the apex:directives channel.

    Returns True if the message was published, False on any failure
    (including Redis being unavailable).
    """
    r = _get_sync_redis()
    if r is None:
        return False
    try:
        payload = json.loads(event.model_dump_json())
        # Ensure UUID and datetime are plain strings regardless of encoder config
        payload["directive_id"] = str(event.directive_id)
        payload["occurred_at"] = event.occurred_at.isoformat()
        r.publish(DIRECTIVE_EVENT_CHANNEL, json.dumps(payload))
        return True
    except Exception as exc:
        logger.warning("Failed to publish directive event: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Async subscriber
# ---------------------------------------------------------------------------


async def directive_event_subscriber() -> AsyncGenerator[DirectiveEvent, None]:
    """Async generator that yields DirectiveEvent objects from apex:directives.

    Degrades gracefully if Redis is unavailable — the generator simply
    returns without yielding anything.
    """
    if aioredis is None:  # pragma: no cover
        logger.warning("directive_event_subscriber: redis.asyncio not available")
        return

    try:
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = DirectiveEvent.model_validate_json(message["data"])
                    yield event
                except Exception as exc:
                    logger.warning("Failed to parse directive event message: %s", exc)
        finally:
            await pubsub.unsubscribe(DIRECTIVE_EVENT_CHANNEL)
            await r.aclose()
    except Exception as exc:
        logger.warning(
            "directive_event_subscriber: Redis unavailable, no events will be yielded: %s",
            exc,
        )
        return
