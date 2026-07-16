from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class PatientCreate(BaseModel):
    name: str
    age: Optional[int] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    therapist_name: Optional[str] = None
    parent_contact: Optional[str] = None

class PatientOut(BaseModel):
    id: UUID
    name: str
    age: Optional[int] = None
    language: Optional[str] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    therapist_name: Optional[str] = None
    parent_contact: Optional[str] = None
    is_active: Optional[bool] = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True