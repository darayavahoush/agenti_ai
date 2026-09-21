"""
tests/test_assessment_game_plan.py -- the game-prediction agent wired into
POST /assessment/complete and GET /assessment/me/game-plan
(routers/breathquest/assessment.py). Pure ranking logic lives in
test_game_predictor.py; these cover the endpoints. See conftest.py for setup.
"""
import pytest
from sqlalchemy import select

from app.models.breathquest_models import BreathQuestPatient
from app.breathquest_core.deps import get_current_patient
from app.main import app


def _m(expected, spoken=None):
    spoken = expected if spoken is None else spoken
    return {"expected": expected, "spoken": spoken, "correct": expected == spoken}


WORD_RESULTS = [
    {"targetWord": "rabbit", "accuracy": 70, "errorPatterns": [],
     "phonemeMatches": [_m("R", "W"), _m("AE1"), _m("B"), _m("IH0"), _m("T")]},
    {"targetWord": "rocket", "accuracy": 72, "errorPatterns": [],
     "phonemeMatches": [_m("R", "W"), _m("AA1"), _m("K"), _m("AH0"), _m("T")]},
    {"targetWord": "run", "accuracy": 68, "errorPatterns": [],
     "phonemeMatches": [_m("R", "W"), _m("AH1"), _m("N")]},
]


async def _seed(code):
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as db:
        patient = BreathQuestPatient(first_name="Ravi", avatar="chick", pin_hash="x", player_code=code)
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return patient.id


def _override_for(patient_id):
    from tests.conftest import TestSessionLocal

    async def _override():
        async with TestSessionLocal() as db:
            return (await db.execute(
                select(BreathQuestPatient).where(BreathQuestPatient.id == patient_id)
            )).scalar_one()
    return _override


@pytest.mark.asyncio
async def test_complete_stores_prediction_and_game_plan_returns_it(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pid = await _seed("GPL001")
    app.dependency_overrides[get_current_patient] = _override_for(pid)
    try:
        done = await client.post(
            "/api/v1/assessment/complete",
            json={"words_attempted": 3, "severity_classification": "Mild", "word_results": WORD_RESULTS},
        )
        assert done.status_code == 204          # unchanged contract

        resp = await client.get("/api/v1/assessment/me/game-plan")
    finally:
        app.dependency_overrides.pop(get_current_patient, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["words_analyzed"] == 3
    assert body["plan"][0]["id"] == "chime_r"
    assert body["plan"][0]["path"] == "/play/chime/lions-roar"


@pytest.mark.asyncio
async def test_game_plan_is_null_when_nothing_to_predict_from(client):
    pid = await _seed("GPL002")
    app.dependency_overrides[get_current_patient] = _override_for(pid)
    try:
        resp = await client.get("/api/v1/assessment/me/game-plan")
    finally:
        app.dependency_overrides.pop(get_current_patient, None)
    assert resp.status_code == 200
    assert resp.json() is None
