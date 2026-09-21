"""
tests/test_username.py -- editable @usernames for kids, parents and
therapists (app/breathquest_core/username.py + app/routers/username_routes.py).

Accounts are seeded straight into the test database and given real tokens,
rather than created through the register endpoints: those are gated behind
email-consent verification (see parental_consent.py), which is irrelevant to
what's under test here. Requests still go through the real routes and the
real get_current_* auth dependencies.
"""
import random
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from conftest import TestSessionLocal
from app.breathquest_core.security import (
    create_access_token, create_kid_token, create_parent_token,
    generate_unique_player_code, hash_password, hash_pin,
)
from app.breathquest_core.username import (
    normalize_username, validate_username_format,
)
from app.models.breathquest_models import BreathQuestPatient, Parent
from app.models.therapist import Therapist

KID = "/api/v1/breathquest/patients/me/username"
PARENT = "/api/v1/parent/username"
THERAPIST = "/api/v1/auth/therapist/username"
ROLES = [("kid", KID), ("parent", PARENT), ("therapist", THERAPIST)]


# ------------------------------------------------------------------ #
#  Seeding helpers                                                    #
# ------------------------------------------------------------------ #

async def _make_kid(player_code=None, pin="1234", username=None, first_name="Kiddo"):
    async with TestSessionLocal() as db:
        kid = BreathQuestPatient(
            first_name=first_name,
            pin_hash=hash_pin(pin),
            # Unique per call (player_code is UNIQUE, and a test may seed several kids).
            player_code=player_code or f"T{uuid.uuid4().hex[:8].upper()}",
            avatar="chick",
            username=username,
        )
        db.add(kid)
        await db.commit()
        return {"id": kid.id, "code": kid.player_code, "token": create_kid_token(str(kid.id))}


async def _make_parent(kid_id, email=None, password="parent-pass-123", username=None):
    async with TestSessionLocal() as db:
        parent = Parent(
            patient_id=kid_id,
            email=email or f"parent-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=hash_password(password),
            username=username,
        )
        db.add(parent)
        await db.commit()
        return {"id": parent.id, "email": parent.email, "token": create_parent_token(str(parent.id))}


async def _make_therapist(email=None, password="therapist-pass-123", username=None):
    async with TestSessionLocal() as db:
        therapist = Therapist(
            email=email or f"t-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password=hash_password(password),
            full_name="Dr. Test",
            username=username,
        )
        db.add(therapist)
        await db.commit()
        return {"id": therapist.id, "email": therapist.email, "token": create_access_token(str(therapist.id))}


async def _one_of_each():
    kid = await _make_kid()
    parent = await _make_parent(kid["id"])
    therapist = await _make_therapist()
    return {"kid": kid, "parent": parent, "therapist": therapist}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------ #
#  Pure format validation                                             #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("raw", [
    "sun", "sunny.otter", "sunny_otter", "otter99", "a1b", "x" * 20, "a.b.c", "_cool_", "@Sunny.Otter",
])
def test_valid_formats(raw):
    name, err = validate_username_format(raw)
    assert err is None
    assert name == raw.lstrip("@").lower()


@pytest.mark.parametrize("raw,fragment", [
    ("", "Pick a username"),
    ("   ", "Pick a username"),
    ("ab", "at least 3"),
    ("x" * 21, "20 characters or fewer"),
    ("has space", "no spaces"),
    ("emoji😀", "Only letters"),
    ("dash-name", "Only letters"),
    ("12345", "at least one letter"),
    (".lead", "start or end with a dot"),
    ("trail.", "start or end with a dot"),
    ("dou..ble", "two dots"),
    ("admin", "reserved"),
    ("Claude", "reserved"),
])
def test_invalid_formats(raw, fragment):
    _, err = validate_username_format(raw)
    assert err is not None and fragment in err


def test_normalize_strips_at_and_lowercases():
    assert normalize_username("  @Sunny.OTTER ") == "sunny.otter"
    assert normalize_username(None) == ""


# ------------------------------------------------------------------ #
#  Endpoints, per role                                                #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("role,base", ROLES)
async def test_get_is_null_until_set_then_persists(client, role, base):
    who = (await _one_of_each())[role]
    r = await client.get(base, headers=_auth(who["token"]))
    assert r.status_code == 200 and r.json() == {"username": None}

    r = await client.patch(base, json={"username": "@Sunny.Otter"}, headers=_auth(who["token"]))
    assert r.status_code == 200
    assert r.json() == {"username": "sunny.otter"}  # normalized

    r = await client.get(base, headers=_auth(who["token"]))
    assert r.json() == {"username": "sunny.otter"}


@pytest.mark.parametrize("role,base", ROLES)
async def test_bad_format_is_422_with_reason(client, role, base):
    who = (await _one_of_each())[role]
    r = await client.patch(base, json={"username": "no spaces!"}, headers=_auth(who["token"]))
    assert r.status_code == 422
    assert "Only letters" in r.json()["detail"]
    r = await client.patch(base, json={"username": "admin"}, headers=_auth(who["token"]))
    assert r.status_code == 422


@pytest.mark.parametrize("role,base", ROLES)
async def test_requires_auth(client, role, base):
    assert (await client.get(base)).status_code in (401, 403)
    assert (await client.patch(base, json={"username": "sunny"})).status_code in (401, 403)
    assert (await client.get(f"{base}/check?username=sunny")).status_code in (401, 403)
    bad = await client.get(base, headers=_auth("not-a-real-token"))
    assert bad.status_code == 401


async def test_a_token_only_works_on_its_own_role(client):
    """A kid's token must not be able to edit a parent's or therapist's handle."""
    a = await _one_of_each()
    assert (await client.patch(PARENT, json={"username": "hax0r"}, headers=_auth(a["kid"]["token"]))).status_code == 401
    assert (await client.patch(THERAPIST, json={"username": "hax0r"}, headers=_auth(a["kid"]["token"]))).status_code == 401
    assert (await client.patch(KID, json={"username": "hax0r"}, headers=_auth(a["parent"]["token"]))).status_code == 401


# ------------------------------------------------------------------ #
#  Uniqueness (across ALL THREE account types)                        #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("first_role,first_base", ROLES)
@pytest.mark.parametrize("second_role,second_base", ROLES)
async def test_unique_across_every_pair_of_roles(client, first_role, first_base, second_role, second_base):
    a = await _one_of_each()
    b = await _one_of_each()
    ok = await client.patch(first_base, json={"username": "sunny.otter"}, headers=_auth(a[first_role]["token"]))
    assert ok.status_code == 200

    clash = await client.patch(second_base, json={"username": "sunny.otter"}, headers=_auth(b[second_role]["token"]))
    assert clash.status_code == 409
    assert "already" in clash.json()["detail"]


async def test_uniqueness_is_case_insensitive(client):
    a = await _one_of_each()
    b = await _one_of_each()
    assert (await client.patch(KID, json={"username": "Sunny.Otter"}, headers=_auth(a["kid"]["token"]))).status_code == 200
    r = await client.patch(THERAPIST, json={"username": "SUNNY.otter"}, headers=_auth(b["therapist"]["token"]))
    assert r.status_code == 409


async def test_resaving_your_own_username_is_fine(client):
    who = await _one_of_each()
    h = _auth(who["parent"]["token"])
    assert (await client.patch(PARENT, json={"username": "my_name"}, headers=h)).status_code == 200
    assert (await client.patch(PARENT, json={"username": "my_name"}, headers=h)).status_code == 200
    # ...and a case-only change to your own handle is also not a clash
    assert (await client.patch(PARENT, json={"username": "My_Name"}, headers=h)).status_code == 200


async def test_changing_username_frees_the_old_one(client):
    a = await _one_of_each()
    b = await _one_of_each()
    await client.patch(KID, json={"username": "first_pick"}, headers=_auth(a["kid"]["token"]))
    await client.patch(KID, json={"username": "second_pick"}, headers=_auth(a["kid"]["token"]))
    r = await client.patch(THERAPIST, json={"username": "first_pick"}, headers=_auth(b["therapist"]["token"]))
    assert r.status_code == 200


async def test_cannot_take_someones_player_code(client):
    """kid-login accepts a username OR a player code, so the two namespaces
    must never overlap."""
    victim = await _make_kid(player_code="CHICK42")
    other = await _one_of_each()
    r = await client.patch(THERAPIST, json={"username": "chick42"}, headers=_auth(other["therapist"]["token"]))
    assert r.status_code == 409
    assert victim["code"] == "CHICK42"


async def test_generated_player_code_skips_existing_usernames(monkeypatch):
    await _make_kid(username="chick42", player_code="ZZZZZ99")
    rolls = iter([42, 43])
    monkeypatch.setattr(random, "randint", lambda a, b: next(rolls))
    async with TestSessionLocal() as db:
        code = await generate_unique_player_code(db, "chick")
    assert code == "CHICK43"


async def test_db_unique_index_backstops_within_a_table():
    await _make_kid(username="dupe_name", player_code="AAAAA11")
    with pytest.raises(IntegrityError):
        async with TestSessionLocal() as db:
            db.add(BreathQuestPatient(
                first_name="Other", pin_hash=hash_pin("1234"),
                player_code="BBBBB22", username="dupe_name",
            ))
            await db.commit()


# ------------------------------------------------------------------ #
#  Live availability check + suggestions                              #
# ------------------------------------------------------------------ #

async def test_check_reports_available_taken_and_invalid(client):
    a = await _one_of_each()
    b = await _one_of_each()
    await client.patch(KID, json={"username": "taken.name"}, headers=_auth(a["kid"]["token"]))
    h = _auth(b["therapist"]["token"])

    free = (await client.get(f"{THERAPIST}/check", params={"username": "@Free_Name"}, headers=h)).json()
    assert free == {"username": "free_name", "available": True, "reason": None}

    taken = (await client.get(f"{THERAPIST}/check", params={"username": "taken.name"}, headers=h)).json()
    assert taken["available"] is False and "already" in taken["reason"]

    bad = (await client.get(f"{THERAPIST}/check", params={"username": "x"}, headers=h)).json()
    assert bad["available"] is False and "at least 3" in bad["reason"]


async def test_check_treats_your_own_current_name_as_available(client):
    who = await _one_of_each()
    h = _auth(who["kid"]["token"])
    await client.patch(KID, json={"username": "mine_now"}, headers=h)
    r = (await client.get(f"{KID}/check", params={"username": "mine_now"}, headers=h)).json()
    assert r["available"] is True


@pytest.mark.parametrize("role,base", ROLES)
async def test_suggestions_are_valid_and_available(client, role, base):
    accts = await _one_of_each()
    other = await _one_of_each()
    r = await client.get(f"{base}/suggestions", headers=_auth(accts[role]["token"]))
    assert r.status_code == 200
    names = r.json()["suggestions"]
    assert 1 <= len(names) <= 4 and len(set(names)) == len(names)
    for n in names:
        assert validate_username_format(n)[1] is None
        # Every suggestion must actually be claimable right now.
        ok = await client.get(f"{THERAPIST}/check", params={"username": n}, headers=_auth(other["therapist"]["token"]))
        assert ok.json()["available"] is True


# ------------------------------------------------------------------ #
#  Kid login by username, and username on login responses             #
# ------------------------------------------------------------------ #

async def test_kid_login_accepts_username_and_at_sign(client):
    kid = await _make_kid(pin="4321")
    assert (await client.patch(KID, json={"username": "sunny.otter"}, headers=_auth(kid["token"]))).status_code == 200

    for ident in ("sunny.otter", "Sunny.Otter", "@sunny.otter"):
        r = await client.post("/api/v1/auth/kid-login", json={"player_code": ident, "pin": "4321"})
        assert r.status_code == 200, (ident, r.text)
        assert r.json()["username"] == "sunny.otter"
        assert r.json()["patient_id"] == str(kid["id"])

    # The player code keeps working exactly as before.
    r = await client.post("/api/v1/auth/kid-login", json={"player_code": kid["code"], "pin": "4321"})
    assert r.status_code == 200


async def test_kid_login_with_username_still_needs_the_right_pin(client):
    kid = await _make_kid(pin="4321")
    await client.patch(KID, json={"username": "sunny.otter"}, headers=_auth(kid["token"]))
    r = await client.post("/api/v1/auth/kid-login", json={"player_code": "sunny.otter", "pin": "0000"})
    assert r.status_code == 401
    assert "username" in r.json()["detail"]


async def test_login_responses_carry_username_or_null(client):
    kid = await _make_kid(pin="4321")
    parent = await _make_parent(kid["id"], password="pw-parent-123")
    therapist = await _make_therapist(password="pw-therapist-123")

    def logins():
        return [
            client.post("/api/v1/auth/kid-login", json={"player_code": kid["code"], "pin": "4321"}),
            client.post("/api/v1/auth/parent-login", json={"email": parent["email"], "password": "pw-parent-123"}),
            client.post("/api/v1/auth/login", json={"email": therapist["email"], "password": "pw-therapist-123"}),
        ]

    for coro in logins():
        r = await coro
        assert r.status_code == 200, r.text
        assert r.json()["username"] is None  # not chosen yet -> frontend shows the picker

    await client.patch(KID, json={"username": "kid_one"}, headers=_auth(kid["token"]))
    await client.patch(PARENT, json={"username": "parent_one"}, headers=_auth(parent["token"]))
    await client.patch(THERAPIST, json={"username": "therapist_one"}, headers=_auth(therapist["token"]))

    got = [(await c).json()["username"] for c in logins()]
    assert got == ["kid_one", "parent_one", "therapist_one"]
