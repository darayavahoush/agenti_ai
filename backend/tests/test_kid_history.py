"""
tests/test_kid_history.py -- GET /me/history (routers/breathquest/kid_progress.py),
the kid's own combined assessment+game timeline. See conftest.py for fixture
setup.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.database import get_db, SessionLocal
from app.models.breathquest_models import BreathQuestPatient, GameSession
from app.models.voicehurdlerace_models import VoiceHurdleRaceSession
from app.models.vaakmirror_models import VaakMirrorSession, GameName
from app.models.flashcards_models import FlashcardAttempt
from app.models.patient import Patient as AssessmentPatient
from app.models.session import Session as AssessmentSession
from app.breathquest_core.deps import get_current_patient
from app.main import app


async def _seed_patient(db_session) -> BreathQuestPatient:
    patient = BreathQuestPatient(
        first_name="Ravi", avatar="chick", pin_hash="x", player_code="RAV123",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    return patient


@pytest.mark.asyncio
async def test_history_combines_and_sorts_all_sources(client, monkeypatch):
    # client fixture already overrides get_db with a fresh per-request
    # session bound to the test DB -- grab one of those to seed rows.
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as seed_db:
        patient = await _seed_patient(seed_db)

        now = datetime.now(timezone.utc)

        seed_db.add(GameSession(
            patient_id=patient.id, level_id="pinwheel",
            started_at=now - timedelta(days=1), completed=True, stars_earned=3,
        ))
        seed_db.add(VoiceHurdleRaceSession(
            patient_id=patient.id, level_id=1, level_name="Level 1",
            score=100, time_remaining=30.0, pitch_accuracy=0.8, loudness_accuracy=0.7,
            stars=2, created_at=now - timedelta(days=2),
        ))
        seed_db.add(VaakMirrorSession(
            patient_id=str(patient.id), game=GameName.mirror_mirror,
            started_at=now - timedelta(days=3), ended_at=now - timedelta(days=3),
        ))
        seed_db.add(FlashcardAttempt(
            patient_id=patient.id, session_id="sess-abc", theme_id="animals",
            target_word="cat", accuracy=0.9, composite_score=0.9,
            attempt_number=1, created_at=now - timedelta(days=4),
        ))

        # Assessment: needs an Assessment-side Patient row + a `sessions`
        # row (session_type="word_practice"), linked via
        # assessment_patient_id -- same shape as assessment.py's real flow.
        assessment_patient = AssessmentPatient(name="Ravi")
        seed_db.add(assessment_patient)
        await seed_db.commit()
        await seed_db.refresh(assessment_patient)

        patient.assessment_patient_id = assessment_patient.id
        seed_db.add(patient)
        await seed_db.commit()

        def _add_assessment_session():
            sync_db = SessionLocal()
            try:
                sync_db.add(AssessmentSession(
                    patient_id=assessment_patient.id, session_type="word_practice",
                    created_at=now - timedelta(hours=1),  # most recent of all entries
                    severity_classification="Mild Articulation Delay",
                ))
                sync_db.commit()
            finally:
                sync_db.close()

        import asyncio
        await asyncio.to_thread(_add_assessment_session)

    async def _override_patient():
        return patient
    app.dependency_overrides[get_current_patient] = _override_patient

    resp = await client.get("/api/v1/me/history")
    app.dependency_overrides.pop(get_current_patient, None)

    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 5

    kinds = [e["kind"] for e in entries]
    assert kinds.count("assessment") == 1
    assert kinds.count("game") == 4

    # Newest first: the assessment (1 hour ago) should be entry 0.
    assert entries[0]["kind"] == "assessment"
    assert entries[0]["title"] == "Pronunciation Assessment"
    # No clinical language leaked into the kid-facing response.
    assert "severity" not in entries[0]
    assert "Mild Articulation Delay" not in str(entries[0])

    games = [e for e in entries if e["kind"] == "game"]
    game_names = {g["game"] for g in games}
    assert game_names == {"BreathQuest", "VoiceHurdleRace", "VaakMirror", "Chime"}

    bq_entry = next(g for g in games if g["game"] == "BreathQuest")
    assert "Pinwheel Spin" in bq_entry["title"]
    assert "3 star" in bq_entry["detail"]

    # Chronological order overall (dates descending).
    dates = [e["date"] for e in entries]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_history_empty_for_new_patient(client):
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as seed_db:
        patient = await _seed_patient(seed_db)

    async def _override_patient():
        return patient
    app.dependency_overrides[get_current_patient] = _override_patient

    resp = await client.get("/api/v1/me/history")
    app.dependency_overrides.pop(get_current_patient, None)

    assert resp.status_code == 200
    assert resp.json() == []
