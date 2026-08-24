from pydantic import BaseModel


class TherapistRegister(BaseModel):
    email: str
    password: str
    full_name: str
    clinic_name: str | None = None
    # Collected, not verified -- see Therapist.phone's comment.
    phone: str | None = None


class TherapistLogin(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    """The frontend gets this token directly from Google Identity
    Services and hands it to us as-is -- see google_oauth.py for the
    server-side verification. Nothing else needed: on first sign-in we
    pull full_name/email straight from the verified token."""
    id_token: str


class TherapistTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    therapist_id: str
    full_name: str
    email: str
    phone: str | None = None
