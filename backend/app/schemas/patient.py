from pydantic import BaseModel
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
    email: Optional[str] = None  # 'email' to match database

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