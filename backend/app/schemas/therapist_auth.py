from pydantic import BaseModel


class TherapistRegister(BaseModel):
    email: str
    password: str
    full_name: str
    clinic_name: str | None = None


class TherapistLogin(BaseModel):
    email: str
    password: str


class TherapistTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    therapist_id: str
    full_name: str
    email: str
