"""Unit tests for src/kamino/models.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.kamino.models import (
    Directive,
    DirectivePayload,
    DirectiveStatus,
    DirectiveType,
)


# ---------------------------------------------------------------------------
# DirectiveType enum
# ---------------------------------------------------------------------------

class TestDirectiveType:
    def test_all_seven_values_present(self):
        values = {e.value for e in DirectiveType}
        assert values == {
            "budget_reallocation",
            "market_tier_change",
            "channel_mix_adjustment",
            "life_event_toggle",
            "test_launch",
            "recovery_update",
            "offer_strategy",
        }

    def test_is_str_enum(self):
        assert isinstance(DirectiveType.budget_reallocation, str)
        assert DirectiveType.budget_reallocation == "budget_reallocation"


# ---------------------------------------------------------------------------
# DirectiveStatus enum & transitions
# ---------------------------------------------------------------------------

class TestDirectiveStatus:
    def test_valid_transition_pending_to_approved(self):
        result = DirectiveStatus.pending.transition_to(DirectiveStatus.approved)
        assert result == DirectiveStatus.approved

    def test_valid_transition_pending_to_cancelled(self):
        result = DirectiveStatus.pending.transition_to(DirectiveStatus.cancelled)
        assert result == DirectiveStatus.cancelled

    def test_valid_transition_approved_to_in_progress(self):
        result = DirectiveStatus.approved.transition_to(DirectiveStatus.in_progress)
        assert result == DirectiveStatus.in_progress

    def test_valid_transition_in_progress_to_completed(self):
        result = DirectiveStatus.in_progress.transition_to(DirectiveStatus.completed)
        assert result == DirectiveStatus.completed

    def test_valid_transition_in_progress_to_failed(self):
        result = DirectiveStatus.in_progress.transition_to(DirectiveStatus.failed)
        assert result == DirectiveStatus.failed

    def test_invalid_transition_pending_to_in_progress(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            DirectiveStatus.pending.transition_to(DirectiveStatus.in_progress)

    def test_invalid_transition_completed_to_pending(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            DirectiveStatus.completed.transition_to(DirectiveStatus.pending)

    def test_invalid_transition_failed_to_approved(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            DirectiveStatus.failed.transition_to(DirectiveStatus.approved)

    def test_terminal_statuses_allow_no_transitions(self):
        for terminal in (DirectiveStatus.completed, DirectiveStatus.failed, DirectiveStatus.cancelled):
            for target in DirectiveStatus:
                with pytest.raises(ValueError):
                    terminal.transition_to(target)


# ---------------------------------------------------------------------------
# DirectivePayload validation
# ---------------------------------------------------------------------------

VALID_PAYLOAD = dict(
    type=DirectiveType.budget_reallocation,
    parameters={"amount": 5000, "channel": "paid_search"},
    description="Reallocate budget to paid search",
    source_module="spend_allocation",
)


class TestDirectivePayload:
    def test_valid_payload_constructs(self):
        p = DirectivePayload(**VALID_PAYLOAD)
        assert p.type == DirectiveType.budget_reallocation
        assert p.source_module == "spend_allocation"

    def test_all_directive_types_accepted(self):
        for dt in DirectiveType:
            p = DirectivePayload(**{**VALID_PAYLOAD, "type": dt})
            assert p.type == dt

    def test_empty_parameters_rejected(self):
        with pytest.raises(ValidationError, match="parameters must be a non-empty dict"):
            DirectivePayload(**{**VALID_PAYLOAD, "parameters": {}})

    def test_invalid_source_module_rejected(self):
        with pytest.raises(ValidationError, match="source_module must be one of"):
            DirectivePayload(**{**VALID_PAYLOAD, "source_module": "unknown_module"})

    def test_missing_required_fields_rejected(self):
        with pytest.raises(ValidationError):
            DirectivePayload(type=DirectiveType.offer_strategy, parameters={"x": 1})

    def test_has_id_and_timestamps(self):
        p = DirectivePayload(**VALID_PAYLOAD)
        assert p.id is not None
        assert p.created_at is not None


# ---------------------------------------------------------------------------
# Directive model
# ---------------------------------------------------------------------------

class TestDirective:
    def _make_payload(self) -> DirectivePayload:
        return DirectivePayload(**VALID_PAYLOAD)

    def test_directive_defaults_to_pending(self):
        d = Directive(payload=self._make_payload())
        assert d.status == DirectiveStatus.pending

    def test_directive_accepts_explicit_status(self):
        d = Directive(payload=self._make_payload(), status=DirectiveStatus.approved)
        assert d.status == DirectiveStatus.approved

    def test_directive_optional_fields_default_none(self):
        d = Directive(payload=self._make_payload())
        assert d.approved_at is None
        assert d.started_at is None
        assert d.completed_at is None
        assert d.failed_at is None
        assert d.failure_reason is None
        assert d.kamino_job_id is None

    def test_directive_has_id_and_timestamps(self):
        d = Directive(payload=self._make_payload())
        assert d.id is not None
        assert d.created_at is not None

    def test_directive_missing_payload_rejected(self):
        with pytest.raises(ValidationError):
            Directive()

    def test_directive_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            Directive(payload=self._make_payload(), status="not_a_status")

    def test_directive_with_failure_info(self):
        from datetime import datetime
        d = Directive(
            payload=self._make_payload(),
            status=DirectiveStatus.failed,
            failed_at=datetime.utcnow(),
            failure_reason="Downstream timeout",
        )
        assert d.failure_reason == "Downstream timeout"
        assert d.failed_at is not None

    def test_directive_with_kamino_job_id(self):
        d = Directive(payload=self._make_payload(), kamino_job_id="job-abc-123")
        assert d.kamino_job_id == "job-abc-123"
