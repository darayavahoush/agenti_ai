"""
tests/test_verify_request.py -- POST /verify/request's registration-only
"this account already exists" check (see VerifyRequestIn.purpose).

The rule under test: only the two registration screens send `purpose`, and
only they get a 409; forgot-password / forgot-PIN send no purpose and must
keep receiving codes for existing accounts.

Accounts are created through the real register endpoints with
AUTO_VERIFY_CONSENT switched on for the test (that flag is the documented
escape hatch in parental_consent.py), so no OTP round-trip is needed just
to set the scene. SMTP is unconfigured in tests, so send_otp_email takes its
dev-mode branch and only logs the code.
"""
import pytest

from app.breathquest_core import parental_consent


@pytest.fixture
def auto_consent(monkeypatch):
    monkeypatch.setattr(parental_consent, "AUTO_VERIFY_CONSENT", True)


async def _register_therapist(client, email):
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "correct-horse-battery-staple",
        "full_name": "Dr. Test Therapist",
    })
    assert resp.status_code == 201, resp.text


async def _register_kid(client, first_name, parent_email):
    resp = await client.post("/api/v1/auth/kid-register", json={
        "first_name": first_name,
        "avatar": "chick",
        "pin": "1234",
        "parent_email": parent_email,
    })
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_therapist_registration_refused_when_account_exists(client, auto_consent):
    await _register_therapist(client, "existing@example.com")

    resp = await client.post("/api/v1/verify/request", json={
        "email": "existing@example.com", "purpose": "register_therapist",
    })
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_therapist_check_ignores_email_case(client, auto_consent):
    await _register_therapist(client, "casey@example.com")

    resp = await client.post("/api/v1/verify/request", json={
        "email": "Casey@Example.com", "purpose": "register_therapist",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_therapist_registration_allowed_for_new_email(client):
    resp = await client.post("/api/v1/verify/request", json={
        "email": "brand-new@example.com", "purpose": "register_therapist",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_flow_still_sends_code_for_existing_account(client, auto_consent):
    # No `purpose` -> the forgot-password / forgot-PIN screens. They must
    # keep working for accounts that exist.
    await _register_therapist(client, "forgetful@example.com")

    resp = await client.post("/api/v1/verify/request", json={"email": "forgetful@example.com"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_existing_account_refusal_does_not_burn_the_resend_cooldown(client, auto_consent):
    # A refused request must not create a code record, or the person's next
    # legitimate request (e.g. the forgot-password flow they're sent to)
    # would hit the 60s "please wait" throttle for nothing.
    await _register_therapist(client, "cooldown@example.com")

    refused = await client.post("/api/v1/verify/request", json={
        "email": "cooldown@example.com", "purpose": "register_therapist",
    })
    assert refused.status_code == 409

    follow_up = await client.post("/api/v1/verify/request", json={"email": "cooldown@example.com"})
    assert follow_up.status_code == 200


@pytest.mark.asyncio
async def test_kid_registration_refused_when_kid_already_exists_for_email(client, auto_consent):
    await _register_kid(client, "Asha", "parent@example.com")

    resp = await client.post("/api/v1/verify/request", json={
        "email": "parent@example.com", "purpose": "register_kid", "first_name": " asha ",
    })
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_sibling_with_a_different_name_is_allowed(client, auto_consent):
    await _register_kid(client, "Asha", "family@example.com")

    resp = await client.post("/api/v1/verify/request", json={
        "email": "family@example.com", "purpose": "register_kid", "first_name": "Ravi",
    })
    assert resp.status_code == 200
