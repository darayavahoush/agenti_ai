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


class TherapistTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    therapist_id: str
    full_name: str
    email: str
    phone: str | None = None
