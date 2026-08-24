import re
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from uuid import UUID
from datetime import datetime

class PatientLogin(BaseModel):
    name: str
    date_of_birth: str

class PatientCreate(BaseModel):
    name: str
    age: Optional[int] = None
    date_of_birth: Optional[str] = None  # String to match database VARCHAR
    language: Optional[str] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    therapist_name: Optional[str] = None
    parent_name: Optional[str] = None
    parent_contact: Optional[str] = None
    email: Optional[EmailStr] = None  # 'email' to match database

    # Mirrors the frontend's own validateContactNumber regex
    # (assessment/Assessment.jsx) so client and server enforce the same rule.
    @validator("parent_contact")
    def validate_parent_contact(cls, v):
        if v is not None and v != "" and not re.match(r"^[0-9]{10}$", v):
            raise ValueError("parent_contact must be exactly 10 digits")
        return v

class PatientOut(BaseModel):
    id: UUID
    name: str
    age: Optional[int] = None
    date_of_birth: Optional[str] = None  # String to match database VARCHAR
    language: Optional[str] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    therapist_name: Optional[str] = None
    parent_name: Optional[str] = None
    parent_contact: Optional[str] = None
    email: Optional[str] = None  # 'email' to match database
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None
    registered_therapist_id: Optional[UUID] = None

    class Config:
        from_attributes = True