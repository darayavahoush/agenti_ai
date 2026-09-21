"""
tests/test_alphabet_endpoints.py -- Sound Check endpoints:
POST /assessment/alphabet/complete, GET /vaakmirror/me/params, and that a
word-assessment retake keeps the saved alphabet plan.
See conftest.py for setup; agent logic is covered by test_alphabet_agents.py.
"""
import pytest
from sqlalchemy import select

from app.models.breathquest_models import BreathQuestPatient
from app.models.vaakmirror_models import VaakMirrorRoundSizeSetting, GameName
from app.breathquest_core.deps import get_current_patient
from app.vaakmirror_auth import get_current_patient_id
from app.main import app


def _r(letter, correct, heard=None):
    return {"letter": letter, "correct": correct, "heard_as": heard}


TRICKY = [_r("B", True), _r("T", False, "D"), _r("K", False, "T"), _r("S", False, "TH")]


async def _seed(code):
    from tests.conftest import TestSessionLocal
    async with TestSessionLocal() as db:
        p = BreathQuestPatient(first_name="Ravi", avatar="chick", pin_hash="x", player_code=code)
        db.add(p)
        await db.commit()
        await db.refresh(p)
        return p.id


def _auth(patient_id):
    from tests.conftest import TestSessionLocal

    async def _patient():
        async with TestSessionLocal() as db:
            return (await db.execute(
                select(BreathQuestPatient).where(BreathQuestPatient.id == patient_id))).scalar_one()

    async def _pid():
        return str(patient_id)

    app.dependency_overrides[get_current_patient] = _patient
    app.dependency_overrides[get_current_patient_id] = _pid


def _unauth():
    app.dependency_overrides.pop(get_current_patient, None)
    app.dependency_overrides.pop(get_current_patient_id, None)


@pytest.mark.asyncio
async def test_complete_stores_plan_and_vaakmirror_reads_it(client):
    pid = await _seed("ALP001")
    _auth(pid)
    try:
        r = await client.post("/api/v1/assessment/alphabet/complete", json={"letter_results": TRICKY})
        assert r.status_code == 200
        assert r.json()["vaakmirror_params"]["round_size"] == 6

        p = (await client.get("/api/v1/vaakmirror/me/params")).json()
        assert p["has_plan"] is True and p["round_size"] == 6
        assert set(p["focus_sounds"][:3]) == {"t", "k", "s"}
        assert (await client.get("/api/v1/assessment/me/alphabet")).json()["plan"]["ready"] is True
    finally:
        _unauth()


@pytest.mark.asyncio
async def test_complete_only_sets_round_size_where_still_default(client):
    from tests.conftest import TestSessionLocal
    pid = await _seed("ALP002")
    async with TestSessionLocal() as db:   # a therapist already chose 14 for Mirror, Mirror
        db.add(VaakMirrorRoundSizeSetting(patient_id=str(pid), game=GameName.mirror_mirror, round_size=14))
        await db.commit()
    _auth(pid)
    try:
        assert (await client.post("/api/v1/assessment/alphabet/complete", json={"letter_results": TRICKY})).status_code == 200
    finally:
        _unauth()
    async with TestSessionLocal() as db:
        rows = {r.game: r.round_size for r in (await db.execute(
            select(VaakMirrorRoundSizeSetting).where(VaakMirrorRoundSizeSetting.patient_id == str(pid)))).scalars()}
    assert rows[GameName.mirror_mirror] == 14      # therapist's choice untouched
    assert rows[GameName.lip_sync_hero] == 6       # no row before -> agent set it


@pytest.mark.asyncio
async def test_too_few_letters_sets_nothing(client):
    pid = await _seed("ALP003")
    _auth(pid)
    try:
        await client.post("/api/v1/assessment/alphabet/complete", json={"letter_results": [_r("B", False, "P")]})
        assert (await client.get("/api/v1/vaakmirror/me/params")).json()["has_plan"] is False
    finally:
        _unauth()


@pytest.mark.asyncio
async def test_word_assessment_retake_keeps_alphabet_plan(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    pid = await _seed("ALP004")
    _auth(pid)
    try:
        await client.post("/api/v1/assessment/alphabet/complete", json={"letter_results": TRICKY})
        done = await client.post("/api/v1/assessment/complete",
                                 json={"words_attempted": 1, "severity_classification": "Mild", "word_results": []})
        assert done.status_code == 204
        assert (await client.get("/api/v1/vaakmirror/me/params")).json()["has_plan"] is True
    finally:
        _unauth()
