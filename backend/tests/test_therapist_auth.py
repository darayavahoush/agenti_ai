"""
tests/test_therapist_auth.py -- register/login/Google sign-in for
app/routers/therapist_auth.py. See conftest.py for fixture setup
(real Postgres test DB, one rolled-back transaction per test).
"""
import pytest

from app.breathquest_core.google_oauth import GoogleUser


def _register_payload(email="therapist@example.com", **overrides):
    payload = {
        "email": email,
        "password": "correct-horse-battery-staple",
        "full_name": "Dr. Test Therapist",
        "clinic_name": "Test Clinic",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_register_returns_tokens_and_profile(client):
    resp = await client.post("/api/v1/auth/register", json=_register_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "therapist@example.com"
    assert body["full_name"] == "Dr. Test Therapist"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["therapist_id"]


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(client):
    payload = _register_payload(email="dupe@example.com")
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_succeeds_with_correct_password(client):
    payload = _register_payload(email="login-ok@example.com")
    await client.post("/api/v1/auth/register", json=payload)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client):
    payload = _register_payload(email="login-bad@example.com")
    await client.post("/api/v1/auth/register", json=payload)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "not-the-password"},
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_rejects_unknown_email(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_locks_out_after_repeated_failures(client):
    """login_throttle.py's schedule locks an identifier out once 5 failed
    attempts land -- verify the 6th attempt gets 429 with Retry-After,
    even with a correct password, rather than a 5th 401."""
    payload = _register_payload(email="throttled@example.com")
    await client.post("/api/v1/auth/register", json=payload)

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": "wrong"},
        )
        assert resp.status_code == 401

    locked_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert locked_resp.status_code == 429
    assert "Retry-After" in locked_resp.headers


@pytest.mark.asyncio
async def test_google_login_registers_new_therapist(client, monkeypatch):
    """No existing account with this google_sub or email -> auto-register,
    per google_login_or_register_therapist's case 3."""
    fake_user = GoogleUser(
        sub="google-sub-new-123",
        email="new-via-google@example.com",
        email_verified=True,
        name="Google Therapist",
    )
    monkeypatch.setattr(
        "app.routers.therapist_auth.verify_google_id_token",
        lambda id_token: fake_user,
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "new-via-google@example.com"
    assert body["full_name"] == "Google Therapist"
    assert body["access_token"]


@pytest.mark.asyncio
async def test_google_login_rejects_unverified_email_for_new_account(client, monkeypatch):
    fake_user = GoogleUser(
        sub="google-sub-unverified",
        email="unverified@example.com",
        email_verified=False,
        name="Unverified Person",
    )
    monkeypatch.setattr(
        "app.routers.therapist_auth.verify_google_id_token",
        lambda id_token: fake_user,
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 403
    assert "not verified" in resp.json()["detail"].lower() or "email isn't verified" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_google_login_links_existing_password_account_by_verified_email(client, monkeypatch):
    """An existing password-based therapist signs in with Google for the
    first time using the same, verified email -> case 2: link google_sub
    onto the existing row instead of creating a duplicate account."""
    payload = _register_payload(email="link-me@example.com")
    register_resp = await client.post("/api/v1/auth/register", json=payload)
    original_id = register_resp.json()["therapist_id"]

    fake_user = GoogleUser(
        sub="google-sub-linking",
        email="link-me@example.com",
        email_verified=True,
        name="Link Me",
    )
    monkeypatch.setattr(
        "app.routers.therapist_auth.verify_google_id_token",
        lambda id_token: fake_user,
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    assert resp.json()["therapist_id"] == original_id


@pytest.mark.asyncio
async def test_google_login_refuses_to_link_on_unverified_email(client, monkeypatch):
    """Same existing account as above, but this time Google reports the
    email as unverified -- linking must be refused (anyone who controls
    an unverified address could otherwise hijack an existing account)."""
    payload = _register_payload(email="cant-link@example.com")
    await client.post("/api/v1/auth/register", json=payload)

    fake_user = GoogleUser(
        sub="google-sub-cant-link",
        email="cant-link@example.com",
        email_verified=False,
        name="Should Not Link",
    )
    monkeypatch.setattr(
        "app.routers.therapist_auth.verify_google_id_token",
        lambda id_token: fake_user,
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 403
