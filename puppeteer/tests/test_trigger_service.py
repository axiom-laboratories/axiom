"""
Tests for TriggerService.update_trigger and TriggerService.regenerate_token.
RED phase: these tests define the expected behaviour before implementation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

# These imports verify the model and service methods exist
from agent_service.models import TriggerUpdate
from agent_service.services.trigger_service import TriggerService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_trigger(trigger_id="t1", is_active=True, secret_token="trg_abc123"):
    t = MagicMock()
    t.id = trigger_id
    t.is_active = is_active
    t.secret_token = secret_token
    return t


async def _mock_db_with_trigger(trigger):
    """Return a mock AsyncSession that returns *trigger* on scalar_one_or_none."""
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = trigger
    db.execute = AsyncMock(return_value=scalar_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


async def _mock_db_no_trigger():
    """Return a mock AsyncSession that returns None (trigger not found)."""
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=scalar_result)
    return db


# ---------------------------------------------------------------------------
# update_trigger tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_trigger_sets_is_active_false():
    trigger = make_trigger(is_active=True)
    db = await _mock_db_with_trigger(trigger)

    result = await TriggerService.update_trigger("t1", is_active=False, db=db)

    assert trigger.is_active is False
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(trigger)
    assert result is trigger


@pytest.mark.asyncio
async def test_update_trigger_sets_is_active_true():
    trigger = make_trigger(is_active=False)
    db = await _mock_db_with_trigger(trigger)

    result = await TriggerService.update_trigger("t1", is_active=True, db=db)

    assert trigger.is_active is True
    db.commit.assert_awaited_once()
    assert result is trigger


@pytest.mark.asyncio
async def test_update_trigger_none_is_active_does_not_change():
    trigger = make_trigger(is_active=True)
    original_active = trigger.is_active
    db = await _mock_db_with_trigger(trigger)

    await TriggerService.update_trigger("t1", is_active=None, db=db)

    # is_active should not have been reassigned
    assert trigger.is_active == original_active


@pytest.mark.asyncio
async def test_update_trigger_not_found_raises_404():
    db = await _mock_db_no_trigger()

    with pytest.raises(HTTPException) as exc_info:
        await TriggerService.update_trigger("nonexistent", is_active=False, db=db)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# regenerate_token tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_regenerate_token_changes_token():
    original_token = "trg_originaltoken"
    trigger = make_trigger(secret_token=original_token)
    db = await _mock_db_with_trigger(trigger)

    result = await TriggerService.regenerate_token("t1", db=db)

    # Token must have changed
    assert trigger.secret_token != original_token
    # New token must use correct prefix
    assert trigger.secret_token.startswith("trg_")
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(trigger)
    assert result is trigger


@pytest.mark.asyncio
async def test_regenerate_token_not_found_raises_404():
    db = await _mock_db_no_trigger()

    with pytest.raises(HTTPException) as exc_info:
        await TriggerService.regenerate_token("nonexistent", db=db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_token_uses_trg_prefix_and_hex():
    """New token must follow the 'trg_' + secrets.token_hex(24) pattern."""
    import re
    trigger = make_trigger(secret_token="trg_old")
    db = await _mock_db_with_trigger(trigger)

    await TriggerService.regenerate_token("t1", db=db)

    # token_hex(24) produces 48 hex chars; total length = 4 + 48 = 52
    assert re.fullmatch(r"trg_[0-9a-f]{48}", trigger.secret_token), (
        f"Unexpected token format: {trigger.secret_token}"
    )


# ---------------------------------------------------------------------------
# TriggerUpdate model tests
# ---------------------------------------------------------------------------

def test_trigger_update_model_fields():
    """TriggerUpdate must have optional is_active and name fields."""
    # Both fields absent -> defaults to None
    u = TriggerUpdate()
    assert u.is_active is None
    assert u.name is None

    # Fields can be set
    u2 = TriggerUpdate(is_active=False, name="renamed")
    assert u2.is_active is False
    assert u2.name == "renamed"
