"""Tests for src/kamino/events.py.

Uses fakeredis (sync) for publish tests.
Uses AsyncMock for async subscriber tests — avoids the complexity of
running a real pub/sub loop in unit tests while still exercising the
message-parsing logic.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.kamino.events import (
    DIRECTIVE_EVENT_CHANNEL,
    DirectiveEvent,
    directive_event_subscriber,
    publish_directive_event,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _event(**kwargs) -> DirectiveEvent:
    defaults = dict(
        directive_id=uuid.uuid4(),
        event_type="created",
        status="active",
        occurred_at=datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc),
        title="Test Directive",
        owner="alice",
    )
    defaults.update(kwargs)
    return DirectiveEvent(**defaults)


def _make_message_payload(event: DirectiveEvent) -> str:
    return json.dumps(
        {
            "directive_id": str(event.directive_id),
            "event_type": event.event_type,
            "status": event.status,
            "occurred_at": event.occurred_at.isoformat(),
            "title": event.title,
            "owner": event.owner,
        }
    )


async def _async_gen_from(items):
    """Helper: yield items from a list as an async generator."""
    for item in items:
        yield item


# ---------------------------------------------------------------------------
# DirectiveEvent model
# ---------------------------------------------------------------------------


class TestDirectiveEventModel:
    def test_required_fields_present(self):
        event = _event()
        assert isinstance(event.directive_id, uuid.UUID)
        assert event.event_type == "created"
        assert event.status == "active"
        assert isinstance(event.occurred_at, datetime)

    def test_optional_fields_default_to_none(self):
        event = DirectiveEvent(
            directive_id=uuid.uuid4(),
            event_type="status_changed",
            status="cancelled",
            occurred_at=datetime.now(timezone.utc),
        )
        assert event.title is None
        assert event.owner is None

    def test_model_dump_json_produces_string_uuid_and_datetime(self):
        event = _event()
        raw = event.model_dump_json()
        data = json.loads(raw)
        assert isinstance(data["directive_id"], str)
        assert isinstance(data["occurred_at"], str)

    def test_round_trip_via_model_validate_json(self):
        event = _event()
        raw = event.model_dump_json()
        restored = DirectiveEvent.model_validate_json(raw)
        assert restored.directive_id == event.directive_id
        assert restored.event_type == event.event_type
        assert restored.status == event.status
        assert restored.title == event.title
        assert restored.owner == event.owner

    def test_channel_constant_value(self):
        assert DIRECTIVE_EVENT_CHANNEL == "apex:directives"


# ---------------------------------------------------------------------------
# publish_directive_event — sync Redis path
# ---------------------------------------------------------------------------


class TestPublishDirectiveEvent:
    def _fake_redis(self):
        import fakeredis
        return fakeredis.FakeRedis(decode_responses=True)

    def test_returns_true_on_success(self):
        r = self._fake_redis()
        with patch("src.kamino.events._get_sync_redis", return_value=r):
            assert publish_directive_event(_event()) is True

    def test_publishes_to_correct_channel(self):
        r = self._fake_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        pubsub.get_message()  # drain subscribe-ack

        with patch("src.kamino.events._get_sync_redis", return_value=r):
            publish_directive_event(_event())

        msg = pubsub.get_message(timeout=0.1)
        assert msg is not None
        assert msg["type"] == "message"
        assert msg["channel"] == DIRECTIVE_EVENT_CHANNEL

    def test_payload_is_valid_json_with_correct_fields(self):
        r = self._fake_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        pubsub.get_message()

        event = _event(event_type="created", status="active", title="Budget Shift")
        with patch("src.kamino.events._get_sync_redis", return_value=r):
            publish_directive_event(event)

        msg = pubsub.get_message(timeout=0.1)
        data = json.loads(msg["data"])
        assert data["event_type"] == "created"
        assert data["status"] == "active"
        assert data["title"] == "Budget Shift"
        assert data["directive_id"] == str(event.directive_id)

    def test_payload_occurred_at_is_string(self):
        r = self._fake_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        pubsub.get_message()

        with patch("src.kamino.events._get_sync_redis", return_value=r):
            publish_directive_event(_event())

        msg = pubsub.get_message(timeout=0.1)
        data = json.loads(msg["data"])
        assert isinstance(data["occurred_at"], str)

    def test_returns_false_when_redis_unavailable(self):
        with patch("src.kamino.events._get_sync_redis", return_value=None):
            assert publish_directive_event(_event()) is False

    def test_returns_false_on_publish_exception(self):
        mock_redis = MagicMock()
        mock_redis.publish.side_effect = ConnectionError("connection refused")
        with patch("src.kamino.events._get_sync_redis", return_value=mock_redis):
            assert publish_directive_event(_event()) is False

    def test_cancelled_event_type(self):
        r = self._fake_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        pubsub.get_message()

        event = _event(event_type="cancelled", status="cancelled")
        with patch("src.kamino.events._get_sync_redis", return_value=r):
            publish_directive_event(event)

        msg = pubsub.get_message(timeout=0.1)
        data = json.loads(msg["data"])
        assert data["event_type"] == "cancelled"
        assert data["status"] == "cancelled"

    def test_owner_field_included_when_set(self):
        r = self._fake_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        pubsub.get_message()

        event = _event(owner="bob")
        with patch("src.kamino.events._get_sync_redis", return_value=r):
            publish_directive_event(event)

        msg = pubsub.get_message(timeout=0.1)
        data = json.loads(msg["data"])
        assert data["owner"] == "bob"

    def test_optional_fields_null_in_payload_when_not_set(self):
        r = self._fake_redis()
        pubsub = r.pubsub()
        pubsub.subscribe(DIRECTIVE_EVENT_CHANNEL)
        pubsub.get_message()

        event = DirectiveEvent(
            directive_id=uuid.uuid4(),
            event_type="status_changed",
            status="completed",
            occurred_at=datetime.now(timezone.utc),
        )
        with patch("src.kamino.events._get_sync_redis", return_value=r):
            publish_directive_event(event)

        msg = pubsub.get_message(timeout=0.1)
        data = json.loads(msg["data"])
        assert data["title"] is None
        assert data["owner"] is None


# ---------------------------------------------------------------------------
# directive_event_subscriber — async path
# ---------------------------------------------------------------------------


class TestDirectiveEventSubscriber:
    def _mock_aioredis(self, messages: list[dict]) -> MagicMock:
        """Build a mock aioredis module whose pubsub.listen() yields *messages*."""
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.listen = lambda: _async_gen_from(messages)

        mock_r = MagicMock()
        mock_r.pubsub.return_value = mock_pubsub
        mock_r.aclose = AsyncMock()

        mock_aio = MagicMock()
        mock_aio.from_url.return_value = mock_r
        return mock_aio

    @pytest.mark.asyncio
    async def test_subscriber_yields_valid_event(self):
        event = _event(event_type="created", status="active")
        messages = [
            {"type": "subscribe", "channel": DIRECTIVE_EVENT_CHANNEL, "data": 1},
            {"type": "message", "channel": DIRECTIVE_EVENT_CHANNEL, "data": _make_message_payload(event)},
        ]
        mock_aio = self._mock_aioredis(messages)

        received = []
        with patch("src.kamino.events.aioredis", mock_aio):
            async for evt in directive_event_subscriber():
                received.append(evt)

        assert len(received) == 1
        assert received[0].directive_id == event.directive_id
        assert received[0].event_type == "created"
        assert received[0].status == "active"

    @pytest.mark.asyncio
    async def test_subscriber_skips_non_message_types(self):
        event = _event()
        messages = [
            {"type": "subscribe", "channel": DIRECTIVE_EVENT_CHANNEL, "data": 1},
            {"type": "psubscribe", "channel": DIRECTIVE_EVENT_CHANNEL, "data": 1},
            {"type": "message", "channel": DIRECTIVE_EVENT_CHANNEL, "data": _make_message_payload(event)},
        ]
        mock_aio = self._mock_aioredis(messages)

        received = []
        with patch("src.kamino.events.aioredis", mock_aio):
            async for evt in directive_event_subscriber():
                received.append(evt)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_subscriber_skips_malformed_json(self):
        valid_event = _event()
        messages = [
            {"type": "message", "channel": DIRECTIVE_EVENT_CHANNEL, "data": "not valid json"},
            {"type": "message", "channel": DIRECTIVE_EVENT_CHANNEL, "data": _make_message_payload(valid_event)},
        ]
        mock_aio = self._mock_aioredis(messages)

        received = []
        with patch("src.kamino.events.aioredis", mock_aio):
            async for evt in directive_event_subscriber():
                received.append(evt)

        assert len(received) == 1
        assert received[0].directive_id == valid_event.directive_id

    @pytest.mark.asyncio
    async def test_subscriber_yields_multiple_events(self):
        events = [_event(event_type="created"), _event(event_type="cancelled")]
        messages = [
            {"type": "message", "channel": DIRECTIVE_EVENT_CHANNEL, "data": _make_message_payload(e)}
            for e in events
        ]
        mock_aio = self._mock_aioredis(messages)

        received = []
        with patch("src.kamino.events.aioredis", mock_aio):
            async for evt in directive_event_subscriber():
                received.append(evt)

        assert len(received) == 2
        assert received[0].event_type == "created"
        assert received[1].event_type == "cancelled"

    @pytest.mark.asyncio
    async def test_subscriber_degrades_gracefully_when_redis_unavailable(self):
        mock_aio = MagicMock()
        mock_aio.from_url.side_effect = ConnectionError("Redis unavailable")

        received = []
        with patch("src.kamino.events.aioredis", mock_aio):
            async for evt in directive_event_subscriber():
                received.append(evt)

        assert received == []

    @pytest.mark.asyncio
    async def test_subscriber_unsubscribes_on_completion(self):
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.listen = lambda: _async_gen_from([])  # no messages

        mock_r = MagicMock()
        mock_r.pubsub.return_value = mock_pubsub
        mock_r.aclose = AsyncMock()

        mock_aio = MagicMock()
        mock_aio.from_url.return_value = mock_r

        with patch("src.kamino.events.aioredis", mock_aio):
            async for _ in directive_event_subscriber():
                pass

        mock_pubsub.unsubscribe.assert_awaited_once_with(DIRECTIVE_EVENT_CHANNEL)
        mock_r.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# Settings integration
# ---------------------------------------------------------------------------


class TestRedisUrlSetting:
    def test_redis_url_default(self, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        import importlib
        import src.config.settings as settings_mod

        importlib.reload(settings_mod)
        assert settings_mod.REDIS_URL == "redis://localhost:6379/0"

    def test_redis_url_env_override(self, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://redis.prod:6380/1")
        import importlib
        import src.config.settings as settings_mod

        importlib.reload(settings_mod)
        assert settings_mod.REDIS_URL == "redis://redis.prod:6380/1"
        monkeypatch.delenv("REDIS_URL")
        importlib.reload(settings_mod)
