"""
tests/test_assessment_retake.py -- POST /assessment/start,
POST /assessment/complete, GET /assessment/me/latest
(routers/breathquest/assessment.py), specifically the retake-with-
30-day-cooldown logic. See conftest.py for fixture setup.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.breathquest_models import BreathQuestPatient
from app.breathquest_core.deps import get_current_patient
from app.main import app


async def _seed_patient(db_session, **overrides) -> BreathQuestPatient:
    defaults = dict(first_name="Ravi", avatar="chick", pin_hash="x", player_code="RAV999")
    defaults.update(overrides)
    patient = BreathQuestPatient(**defaults)
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest.mark.asyncio
async def test_first_time_start_is_not_blocked(client):
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as seed_db:
        patient = await _seed_patient(seed_db)

    async def _override():
        return patient
    app.dependency_overrides[get_current_patient] = _override

    resp = await client.post("/api/v1/assessment/start")
    app.dependency_overrides.pop(get_current_patient, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["already_completed"] is False
    assert body["retake_available_at"] is None


@pytest.mark.asyncio
async def test_complete_then_immediate_restart_is_blocked_for_30_days(client):
    from tests.conftest import TestSessionLocal
    from sqlalchemy import select
    async with TestSessionLocal() as seed_db:
        patient = await _seed_patient(seed_db, player_code="RAV001")
    patient_id = patient.id

    # Re-fetches from the DB on every call, matching what the real
    # get_current_patient dependency does per-request -- unlike a plain
    # closure returning the same (increasingly stale) Python object,
    # which wouldn't see /complete's write when /start queries next.
    async def _override():
        async with TestSessionLocal() as db:
            return (await db.execute(
                select(BreathQuestPatient).where(BreathQuestPatient.id == patient_id)
            )).scalar_one()
    app.dependency_overrides[get_current_patient] = _override

    complete_resp = await client.post(
        "/api/v1/assessment/complete",
        json={"words_attempted": 10, "severity_classification": "Mild Delay"},
    )
    assert complete_resp.status_code == 204

    start_resp = await client.post("/api/v1/assessment/start")
    app.dependency_overrides.pop(get_current_patient, None)

    assert start_resp.status_code == 200
    body = start_resp.json()
    assert body["already_completed"] is True
    assert body["retake_available_at"] is not None

    retake_at = datetime.fromisoformat(body["retake_available_at"])
    now = datetime.now(timezone.utc)
    # Should be ~30 days out, not immediately available and not, say,
    # a year away -- catches an off-by-unit error (days vs seconds etc).
    assert timedelta(days=29) < (retake_at - now) < timedelta(days=31)


@pytest.mark.asyncio
async def test_start_allows_retake_once_cooldown_elapsed(client):
    """Same as above, but the completion happened 31 days ago -- cooldown
    should have lifted, and /start should behave like a first-timer
    again (already_completed=False) rather than staying blocked forever."""
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as seed_db:
        patient = await _seed_patient(
            seed_db, player_code="RAV002",
            assessment_completed=True,
            assessment_completed_at=datetime.now(timezone.utc) - timedelta(days=31),
        )

    async def _override():
        return patient
    app.dependency_overrides[get_current_patient] = _override

    resp = await client.post("/api/v1/assessment/start")
    app.dependency_overrides.pop(get_current_patient, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["already_completed"] is False
    assert body["retake_available_at"] is None


@pytest.mark.asyncio
async def test_legacy_completed_row_with_no_timestamp_is_eligible_immediately(client):
    """A row completed before assessment_completed_at existed
    (assessment_completed=True, assessment_completed_at=None) shouldn't
    be blocked forever just because we don't have the original
    timestamp -- see _retake_available_at's own note on this."""
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as seed_db:
        patient = await _seed_patient(
            seed_db, player_code="RAV003",
            assessment_completed=True,
            assessment_completed_at=None,
        )

    async def _override():
        return patient
    app.dependency_overrides[get_current_patient] = _override

    resp = await client.post("/api/v1/assessment/start")
    app.dependency_overrides.pop(get_current_patient, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["already_completed"] is False


@pytest.mark.asyncio
async def test_me_latest_carries_retake_available_at_while_on_cooldown(client):
    from tests.conftest import TestSessionLocal
    from app.models.patient import Patient as AssessmentPatient
    from app.models.session import Session as AssessmentSession
    from app.database import SessionLocal
    import asyncio as _asyncio

    async with TestSessionLocal() as seed_db:
        assessment_patient = AssessmentPatient(name="Ravi")
        seed_db.add(assessment_patient)
        await seed_db.commit()
        await seed_db.refresh(assessment_patient)

        patient = await _seed_patient(
            seed_db, player_code="RAV004",
            assessment_completed=True,
            assessment_completed_at=datetime.now(timezone.utc) - timedelta(days=5),
            assessment_patient_id=assessment_patient.id,
        )

        def _add_session():
            sync_db = SessionLocal()
            try:
                sync_db.add(AssessmentSession(
                    patient_id=assessment_patient.id, session_type="word_practice",
                    severity_classification="Mild Delay",
                ))
                sync_db.commit()
            finally:
                sync_db.close()
        await _asyncio.to_thread(_add_session)

    async def _override():
        return patient
    app.dependency_overrides[get_current_patient] = _override

    resp = await client.get("/api/v1/assessment/me/latest")
    app.dependency_overrides.pop(get_current_patient, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body is not None
    assert body["retake_available_at"] is not None
    retake_at = datetime.fromisoformat(body["retake_available_at"])
    # completed 5 days ago + 30 day cooldown => ~25 days still remaining
    remaining = retake_at - datetime.now(timezone.utc)
    assert timedelta(days=24) < remaining < timedelta(days=26)
