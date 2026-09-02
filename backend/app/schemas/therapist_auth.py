from pydantic import BaseModel, validator


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


class TherapistResetPasswordRequest(BaseModel):
    """Password reset for a locked-out therapist, gated the same way
    register_therapist itself is gated -- a recently-verified email
    (see check_email_consent) -- rather than a mailed reset link/token,
    matching the pattern used for parent password reset."""
    email: str
    new_password: str

    @validator("new_password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class TherapistDeleteAccountRequest(BaseModel):
    """Re-auth for the irreversible delete-account action. current_password
    is required unless the account is Google-only (no password ever set --
    see Therapist.hashed_password's comment), in which case it's omitted
    entirely rather than asking for a password that was never created."""
    current_password: str | None = None


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
